use base64::Engine as _;
use serde::{Deserialize, Serialize};
use std::{
    collections::{BTreeMap, BTreeSet},
    ffi::{CStr, CString},
    os::raw::c_char,
    path::{Component, Path, PathBuf},
    sync::{Arc, Mutex},
    time::Instant,
};
use tectonic::driver::{OutputFormat, ProcessingSessionBuilder};
use tectonic_bridge_core::SecuritySettings;
use tectonic_bundles::{dir::DirBundle, Bundle};
use tectonic_io_base::{digest::DigestData, InputHandle, IoProvider, OpenResult};
use tectonic_status_base::{MessageKind, StatusBackend};

// Tectonic's native engines share process-global state. Serialize all callers.
static ENGINE: Mutex<()> = Mutex::new(());

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Request {
    pub source: String,
    pub bundle_path: PathBuf,
    pub output_path: PathBuf,
    #[serde(default)]
    pub assets: BTreeMap<String, String>,
    #[serde(default)]
    pub asset_files: BTreeMap<String, PathBuf>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Response {
    pub ok: bool,
    pub error: Option<String>,
    pub log: String,
    pub pdf_bytes: usize,
    pub elapsed_ms: u128,
    pub files: Vec<String>,
}
impl Response {
    fn error(error: impl ToString) -> Self {
        Self {
            ok: false,
            error: Some(error.to_string()),
            log: String::new(),
            pdf_bytes: 0,
            elapsed_ms: 0,
            files: vec![],
        }
    }
}

#[derive(Default)]
struct Log(String);
impl StatusBackend for Log {
    fn report(
        &mut self,
        kind: MessageKind,
        args: std::fmt::Arguments,
        error: Option<&tectonic_errors::Error>,
    ) {
        self.0.push_str(&format!("{kind:?}: {args}\n"));
        if let Some(error) = error {
            self.0.push_str(&format!("{error:#}\n"));
        }
    }
    fn dump_error_logs(&mut self, output: &[u8]) {
        self.0.push_str(&String::from_utf8_lossy(output));
    }
}

struct TracedBundle {
    inner: Box<dyn Bundle>,
    files: Arc<Mutex<BTreeSet<String>>>,
}
impl IoProvider for TracedBundle {
    fn input_open_name(
        &mut self,
        name: &str,
        status: &mut dyn StatusBackend,
    ) -> OpenResult<InputHandle> {
        let result = self.inner.input_open_name(name, status);
        if matches!(result, OpenResult::Ok(_)) {
            self.files.lock().unwrap().insert(name.to_owned());
        }
        result
    }
    fn input_open_name_with_abspath(
        &mut self,
        name: &str,
        status: &mut dyn StatusBackend,
    ) -> OpenResult<(InputHandle, Option<PathBuf>)> {
        match self.input_open_name(name, status) {
            OpenResult::Ok(h) => OpenResult::Ok((h, None)),
            OpenResult::NotAvailable => OpenResult::NotAvailable,
            OpenResult::Err(e) => OpenResult::Err(e),
        }
    }
}
impl Bundle for TracedBundle {
    fn get_digest(&mut self) -> tectonic_errors::Result<DigestData> {
        self.inner.get_digest()
    }
    fn all_files(&self) -> Vec<String> {
        self.inner.all_files()
    }
}

fn validate_asset_name(name: &str) -> Result<(), Box<dyn std::error::Error>> {
    let path = Path::new(name);
    if name.is_empty()
        || name.contains('\\')
        || name.contains(':')
        || name.contains('\0')
        || name
            .split('/')
            .any(|part| part.is_empty() || part == "." || part == "..")
        || !path
            .components()
            .all(|part| matches!(part, Component::Normal(_)))
        || ["main.tex", "main.pdf"].contains(&name)
    {
        return Err(format!("invalid asset path: {name}").into());
    }
    Ok(())
}

fn copy_asset_files(
    root: &Path,
    files: &BTreeMap<String, PathBuf>,
    inline: &BTreeMap<String, String>,
) -> Result<(), Box<dyn std::error::Error>> {
    use std::io::Read;
    if files.len() + inline.len() > 128 {
        return Err("too many assets (maximum 128)".into());
    }
    let mut remaining = 256 * 1024 * 1024_u64;
    for (name, source) in files {
        validate_asset_name(name)?;
        if inline.contains_key(name) {
            return Err(format!("duplicate asset: {name}").into());
        }
        let input = std::fs::File::open(source)?;
        if !input.metadata()?.is_file() {
            return Err("asset source must be a regular file".into());
        }
        let destination = root.join(name);
        std::fs::create_dir_all(destination.parent().unwrap())?;
        let mut output = std::fs::File::create(destination)?;
        let copied = std::io::copy(&mut input.take(remaining + 1), &mut output)?;
        if copied > remaining {
            return Err("file assets exceed 256 MiB".into());
        }
        remaining -= copied;
    }
    Ok(())
}

fn write_assets(
    root: &Path,
    assets: &BTreeMap<String, String>,
) -> Result<(), Box<dyn std::error::Error>> {
    if assets.len() > 128 || assets.values().map(String::len).sum::<usize>() > 24 * 1024 * 1024 {
        return Err("too many assets or encoded assets exceed 24 MiB".into());
    }
    let mut total = 0;
    for (name, encoded) in assets {
        validate_asset_name(name)?;
        let path = Path::new(name);
        let bytes = base64::engine::general_purpose::STANDARD.decode(encoded)?;
        total += bytes.len();
        if total > 16 * 1024 * 1024 {
            return Err("decoded assets exceed 16 MiB".into());
        }
        let destination = root.join(path);
        std::fs::create_dir_all(destination.parent().unwrap())?;
        std::fs::write(destination, bytes)?;
    }
    Ok(())
}

pub fn compile(request: Request) -> Response {
    if !request.bundle_path.join("SHA256SUM").is_file() {
        return Response::error("bundle is missing SHA256SUM; run tools/pack.py");
    }
    let bundle = Box::new(DirBundle::new(&request.bundle_path));
    compile_with_bundle(request, bundle)
}

// Also used by the host-only bundle collector. Mobile callers use compile().
pub fn compile_with_bundle(request: Request, bundle: Box<dyn Bundle>) -> Response {
    let started = Instant::now();
    let files = Arc::new(Mutex::new(BTreeSet::new()));
    let mut log = Log::default();
    let result = (|| -> Result<usize, Box<dyn std::error::Error>> {
        if request.source.len() > 4 * 1024 * 1024 {
            return Err("source exceeds 4 MiB".into());
        }
        let _guard = ENGINE
            .lock()
            .map_err(|_| "engine lock poisoned; restart the host")?;
        let scratch = tempfile::tempdir()?;
        copy_asset_files(scratch.path(), &request.asset_files, &request.assets)?;
        write_assets(scratch.path(), &request.assets)?;
        // A fresh format cache also records every dependency needed to initialize LaTeX.
        let mut builder = ProcessingSessionBuilder::new_with_security(SecuritySettings::default());
        builder
            .primary_input_buffer(request.source.as_bytes())
            .tex_input_name("main.tex")
            .filesystem_root(scratch.path())
            .format_cache_path(scratch.path())
            .format_name("latex")
            .output_format(OutputFormat::Xdv)
            .do_not_write_output_files()
            .shell_escape_disabled()
            .bundle(Box::new(TracedBundle {
                inner: bundle,
                files: files.clone(),
            }));
        let mut session = builder.create(&mut log)?;
        session.run(&mut log)?;
        let mut output = session.into_file_data();
        let xdv = output
            .remove("main.xdv")
            .ok_or("engine did not produce main.xdv")?
            .data;
        let (pdf, renderer_files) = latex_mobile_xdv::render_with_files(
            std::io::Cursor::new(xdv),
            &request.bundle_path,
            Some(scratch.path()),
        )
        .map_err(|e| format!("PDF renderer: {e:#}"))?;
        files
            .lock()
            .map_err(|_| "bundle trace lock poisoned")?
            .extend(renderer_files);
        if !pdf.starts_with(b"%PDF-") {
            return Err("engine returned an invalid PDF header".into());
        }
        let parent = request
            .output_path
            .parent()
            .filter(|p| !p.as_os_str().is_empty())
            .unwrap_or(Path::new("."));
        let mut pending = tempfile::NamedTempFile::new_in(parent)?;
        std::io::Write::write_all(&mut pending, &pdf)?;
        pending.persist(&request.output_path)?;
        Ok(pdf.len())
    })();
    let mut response = match result {
        Ok(bytes) => Response {
            ok: true,
            error: None,
            log: String::new(),
            pdf_bytes: bytes,
            elapsed_ms: 0,
            files: vec![],
        },
        Err(error) => Response::error(format!("{error:#}")),
    };
    response.log = log.0;
    response.elapsed_ms = started.elapsed().as_millis();
    response.files = files.lock().unwrap().iter().cloned().collect();
    response
}

pub fn compile_json(json: &str) -> String {
    let response = std::panic::catch_unwind(|| match serde_json::from_str(json) {
        Ok(request) => compile(request),
        Err(error) => Response::error(format!("invalid request: {error}")),
    })
    .unwrap_or_else(|_| Response::error("native engine panicked"));
    serde_json::to_string(&response).unwrap()
}

/// # Safety
/// `request` must be null or a valid NUL-terminated UTF-8 string for the duration of the call.
/// Free the returned allocation exactly once with `lm_string_free`.
#[no_mangle]
pub unsafe extern "C" fn lm_compile(request: *const c_char) -> *mut c_char {
    let json = if request.is_null() {
        serde_json::to_string(&Response::error("null request")).unwrap()
    } else {
        match CStr::from_ptr(request).to_str() {
            Ok(request) => compile_json(request),
            Err(_) => serde_json::to_string(&Response::error("request is not UTF-8")).unwrap(),
        }
    };
    CString::new(json).unwrap().into_raw()
}

/// # Safety
/// `value` must be null or an unfreed pointer returned by `lm_compile`.
#[no_mangle]
pub unsafe extern "C" fn lm_string_free(value: *mut c_char) {
    if !value.is_null() {
        drop(CString::from_raw(value));
    }
}

#[cfg(target_os = "android")]
mod android {
    use jni::{
        objects::{JClass, JString},
        sys::jstring,
        JNIEnv,
    };
    #[no_mangle]
    pub extern "system" fn Java_org_latexmobile_LatexMobile_compileNative(
        mut env: JNIEnv,
        _: JClass,
        request: JString,
    ) -> jstring {
        let result = match env.get_string(&request) {
            Ok(value) => super::compile_json(&String::from(value)),
            Err(_) => return std::ptr::null_mut(),
        };
        env.new_string(result)
            .map(|s| s.into_raw())
            .unwrap_or(std::ptr::null_mut())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn malformed_requests_return_errors() {
        for request in ["{}", "null", "not json"] {
            assert!(
                !serde_json::from_str::<Response>(&compile_json(request))
                    .unwrap()
                    .ok
            );
        }
    }
    #[test]
    fn missing_bundle_does_not_replace_output() {
        let temp = tempfile::tempdir().unwrap();
        let output = temp.path().join("existing.pdf");
        std::fs::write(&output, "previous").unwrap();
        let result = compile(Request {
            source: "hello".into(),
            bundle_path: temp.path().join("missing"),
            output_path: output.clone(),
            assets: BTreeMap::new(),
            asset_files: BTreeMap::new(),
        });
        assert!(!result.ok);
        assert_eq!(std::fs::read_to_string(output).unwrap(), "previous");
    }
    #[test]
    fn asset_paths_and_encoding_are_checked() {
        let temp = tempfile::tempdir().unwrap();
        for name in [
            "../escape",
            "/absolute",
            "nested/../../escape",
            "main.tex",
            "",
            "C:\\escape",
        ] {
            assert!(write_assets(
                temp.path(),
                &BTreeMap::from([(name.into(), "aGVsbG8=".into())])
            )
            .is_err());
        }
        assert!(write_assets(
            temp.path(),
            &BTreeMap::from([("logo.png".into(), "bad base64!".into())])
        )
        .is_err());
        write_assets(
            temp.path(),
            &BTreeMap::from([("images/logo.png".into(), "aGVsbG8=".into())]),
        )
        .unwrap();
        assert_eq!(
            std::fs::read(temp.path().join("images/logo.png")).unwrap(),
            b"hello"
        );
    }

    #[test]
    fn file_assets_copy_and_reject_conflicts() {
        let temp = tempfile::tempdir().unwrap();
        let source = temp.path().join("original");
        std::fs::write(&source, b"asset content").unwrap();
        let scratch = temp.path().join("scratch");
        let files = BTreeMap::from([("images/logo.pdf".into(), source.clone())]);
        copy_asset_files(&scratch, &files, &BTreeMap::new()).unwrap();
        assert_eq!(
            std::fs::read(scratch.join("images/logo.pdf")).unwrap(),
            b"asset content"
        );
        assert_eq!(std::fs::read(&source).unwrap(), b"asset content");
        assert!(copy_asset_files(
            &scratch,
            &files,
            &BTreeMap::from([("images/logo.pdf".into(), String::new())])
        )
        .is_err());
        for name in [
            "../escape",
            "images/./logo.pdf",
            "images//logo.pdf",
            "main.pdf",
        ] {
            assert!(copy_asset_files(
                &scratch,
                &BTreeMap::from([(name.into(), source.clone())]),
                &BTreeMap::new()
            )
            .is_err());
        }
        assert!(copy_asset_files(
            &scratch,
            &BTreeMap::from([("dir".into(), temp.path().to_path_buf())]),
            &BTreeMap::new()
        )
        .is_err());
    }

    #[test]
    fn c_ownership_and_null_request() {
        unsafe {
            let result = lm_compile(std::ptr::null());
            assert!(
                !serde_json::from_str::<Response>(CStr::from_ptr(result).to_str().unwrap())
                    .unwrap()
                    .ok
            );
            lm_string_free(result);
            lm_string_free(std::ptr::null_mut());
        }
    }
}
