//! Experimental in-process LaTeX/XDV/PDF pipeline. Production APIs are unchanged.
use anyhow::{Context, Result, ensure};
use std::{
    collections::BTreeMap,
    io::{Cursor, Write},
    path::{Path, PathBuf},
    sync::Mutex,
};
use tectonic::driver::{OutputFormat, ProcessingSessionBuilder};
use tectonic_bundles::dir::DirBundle;
use tectonic_status_base::NoopStatusBackend;

static ENGINE: Mutex<()> = Mutex::new(());
const MAX_ASSET_BYTES: u64 = 256 * 1024 * 1024;

fn stage_assets(assets: &BTreeMap<String, PathBuf>, directory: &Path) -> Result<()> {
    ensure!(assets.len() <= 128, "too many assets");
    for (name, source) in assets {
        ensure!(
            !name.is_empty()
                && name != "."
                && name != ".."
                && !name.contains('/')
                && !name.contains('\\'),
            "invalid asset name"
        );
        let input = std::fs::File::open(source)?;
        ensure!(input.metadata()?.is_file(), "asset is not a regular file");
        let mut bounded = std::io::Read::take(input, MAX_ASSET_BYTES + 1);
        let mut output = std::fs::File::create(directory.join(name))?;
        ensure!(
            std::io::copy(&mut bounded, &mut output)? <= MAX_ASSET_BYTES,
            "asset exceeds size limit"
        );
    }
    Ok(())
}
fn xdv_in(source: &[u8], bundle: &Path, directory: &Path) -> Result<Vec<u8>> {
    ensure!(source.len() <= 4 * 1024 * 1024, "source exceeds size limit");
    let mut status = NoopStatusBackend::default();
    let mut builder = ProcessingSessionBuilder::new_with_security(
        tectonic_bridge_core::SecuritySettings::default(),
    );
    builder
        .primary_input_buffer(source)
        .tex_input_name("main.tex")
        .filesystem_root(directory)
        .format_cache_path(directory)
        .format_name("latex")
        .output_format(OutputFormat::Xdv)
        .do_not_write_output_files()
        .shell_escape_disabled()
        .bundle(Box::new(DirBundle::new(bundle)));
    let mut session = builder.create(&mut status)?;
    session.run(&mut status)?;
    let mut files = session.into_file_data();
    Ok(files.remove("main.xdv").context("missing XDV output")?.data)
}
/// Generate XDV with explicit file assets and no subprocess/network compilation.
pub fn compile_xdv(
    source: &[u8],
    bundle: &Path,
    assets: &BTreeMap<String, PathBuf>,
) -> Result<Vec<u8>> {
    let _guard = ENGINE
        .lock()
        .map_err(|_| anyhow::anyhow!("engine lock poisoned"))?;
    let scratch = tempfile::tempdir()?;
    stage_assets(assets, scratch.path())?;
    xdv_in(source, bundle, scratch.path())
}
/// Compile LaTeX through the replacement renderer and atomically write the PDF.
/// Assets are copied with bounded streams. XDV and PDF buffers remain in memory.
pub fn compile_pdf_file(
    source: &[u8],
    bundle: &Path,
    fonts: &Path,
    assets: &BTreeMap<String, PathBuf>,
    output: &Path,
) -> Result<()> {
    let _guard = ENGINE
        .lock()
        .map_err(|_| anyhow::anyhow!("engine lock poisoned"))?;
    let scratch = tempfile::tempdir()?;
    stage_assets(assets, scratch.path())?;
    let xdv = xdv_in(source, bundle, scratch.path())?;
    let pdf = krilla_xdv_probe::render(Cursor::new(xdv), fonts, Some(scratch.path()))?;
    let parent = output
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    let mut pending = tempfile::NamedTempFile::new_in(parent)?;
    pending.write_all(&pdf)?;
    pending.persist(output).map_err(|e| e.error)?;
    Ok(())
}
/// Collect a fixture's sibling asset directory without loading the files.
pub fn fixture_assets(source: &Path) -> Result<BTreeMap<String, PathBuf>> {
    let mut result = BTreeMap::new();
    let directory = source.with_extension("assets");
    if directory.is_dir() {
        for entry in std::fs::read_dir(directory)? {
            let entry = entry?;
            if entry.file_type()?.is_file() {
                result.insert(
                    entry
                        .file_name()
                        .into_string()
                        .map_err(|_| anyhow::anyhow!("non-UTF8 asset name"))?,
                    entry.path(),
                );
            }
        }
    }
    Ok(result)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn metadata_rejects_invalid_rasters_without_touching_output() {
        unsafe extern "C" {
            fn lm_probe_raster_size(data: *const u8, len: usize, output: *mut f64) -> i32;
        }
        for raw in [
            b"".as_slice(),
            b"not an image",
            &[0xff, 0xd8],
            &[0xff, 0xd8, 0xff, 0xe0, 0, 1],
        ] {
            let mut output = [123.0, 456.0];
            assert_eq!(
                unsafe { lm_probe_raster_size(raw.as_ptr(), raw.len(), output.as_mut_ptr()) },
                -1
            );
            assert_eq!(output, [123.0, 456.0]);
        }
        assert_eq!(
            unsafe { lm_probe_raster_size(std::ptr::null(), 10, std::ptr::null_mut()) },
            -1
        );
    }
    #[test]
    fn rejects_traversal_before_opening_asset() {
        let dir = tempfile::tempdir().unwrap();
        let mut assets = BTreeMap::new();
        assets.insert("../outside".into(), PathBuf::from("missing"));
        assert!(
            stage_assets(&assets, dir.path())
                .unwrap_err()
                .to_string()
                .contains("invalid asset name")
        );
        assert_eq!(std::fs::read_dir(dir.path()).unwrap().count(), 0);
    }
    #[test]
    fn copies_binary_assets_without_reencoding() {
        let source = tempfile::tempdir().unwrap();
        let dest = tempfile::tempdir().unwrap();
        let path = source.path().join("logo");
        std::fs::write(&path, [0, 255, 17, 128]).unwrap();
        stage_assets(&BTreeMap::from([("logo.png".into(), path)]), dest.path()).unwrap();
        assert_eq!(
            std::fs::read(dest.path().join("logo.png")).unwrap(),
            [0, 255, 17, 128]
        );
    }
    #[test]
    fn repeated_compilation_and_recovery_preserve_output() {
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
        let bundle = root.join("dist/bundles/full/texbundle");
        let fonts = root.join(".build/krilla-fonts");
        let dir = tempfile::tempdir().unwrap();
        let output = dir.path().join("result.pdf");
        let source = br"\documentclass{article}\begin{document}Repeated compilation.\end{document}";
        let assets = BTreeMap::new();
        compile_pdf_file(source, &bundle, &fonts, &assets, &output).unwrap();
        let first = std::fs::read(&output).unwrap();
        compile_pdf_file(source, &bundle, &fonts, &assets, &output).unwrap();
        assert_eq!(std::fs::read(&output).unwrap(), first);
        let invalid = br"\documentclass{article}\begin{document}\undefinedCommand\end{document}";
        assert!(compile_pdf_file(invalid, &bundle, &fonts, &assets, &output).is_err());
        assert_eq!(std::fs::read(&output).unwrap(), first);
        compile_pdf_file(source, &bundle, &fonts, &assets, &output).unwrap();
        assert_eq!(std::fs::read(&output).unwrap(), first);
    }
}
