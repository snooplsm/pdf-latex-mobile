use base64::Engine as _;
use std::{
    io::{Cursor, Read},
    path::{Path, PathBuf},
};
use tectonic_bundles::Bundle;
use tectonic_io_base::{digest::DigestData, InputHandle, InputOrigin, IoProvider, OpenResult};
use tectonic_status_base::StatusBackend;
struct Collector {
    inner: Box<dyn Bundle>,
    output: PathBuf,
}
impl IoProvider for Collector {
    fn input_open_name(
        &mut self,
        name: &str,
        status: &mut dyn StatusBackend,
    ) -> OpenResult<InputHandle> {
        // Flattened bundles are keyed by filename. Never let a requested path escape output.
        if Path::new(name).components().count() != 1 || name == ".." || name == "." {
            return OpenResult::NotAvailable;
        }
        match self.inner.input_open_name(name, status) {
            OpenResult::Ok(mut input) => {
                let mut bytes = Vec::new();
                if let Err(error) = input.read_to_end(&mut bytes) {
                    return OpenResult::Err(error.into());
                }
                if let Err(error) = std::fs::write(self.output.join(name), &bytes) {
                    return OpenResult::Err(error.into());
                }
                OpenResult::Ok(InputHandle::new(
                    name,
                    Cursor::new(bytes),
                    InputOrigin::Other,
                ))
            }
            OpenResult::NotAvailable => OpenResult::NotAvailable,
            OpenResult::Err(error) => OpenResult::Err(error),
        }
    }
}
impl Bundle for Collector {
    fn all_files(&self) -> Vec<String> {
        self.inner.all_files()
    }
    fn get_digest(&mut self) -> tectonic_errors::Result<DigestData> {
        self.inner.get_digest()
    }
}
fn read_assets(
    root: PathBuf,
) -> Result<std::collections::BTreeMap<String, String>, Box<dyn std::error::Error>> {
    let mut assets = std::collections::BTreeMap::new();
    if root.is_dir() {
        // Example assets are flat; the mobile API also accepts safe nested relative paths.
        for entry in std::fs::read_dir(root)? {
            let entry = entry?;
            if !entry.file_type()?.is_file() {
                return Err("example assets must be regular files".into());
            }
            assets.insert(
                entry
                    .file_name()
                    .to_str()
                    .ok_or("non-UTF8 asset name")?
                    .to_owned(),
                base64::engine::general_purpose::STANDARD.encode(std::fs::read(entry.path())?),
            );
        }
    }
    Ok(assets)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 4 {
        return Err("usage: bundle-fetch BUNDLE_URL OUTPUT_DIRECTORY EXAMPLE.tex [...]".into());
    }
    let output = PathBuf::from(&args[2]);
    std::fs::create_dir_all(&output)?;
    for fixture in &args[3..] {
        let bundle = tectonic_bundles::detect_bundle(args[1].clone(), false, None)?
            .ok_or("unsupported bundle URL")?;
        let result = latex_mobile::compile_with_bundle(
            latex_mobile::Request {
                asset_files: Default::default(),
                source: std::fs::read_to_string(fixture)?,
                assets: read_assets(Path::new(fixture).with_extension("assets"))?,
                bundle_path: output.clone(),
                output_path: output.join("probe.pdf"),
            },
            Box::new(Collector {
                inner: bundle,
                output: output.clone(),
            }),
        );
        if !result.ok {
            return Err(format!("{fixture}: {:?}\n{}", result.error, result.log).into());
        }
        eprintln!("{fixture}: {} PDF bytes", result.pdf_bytes);
    }
    std::fs::remove_file(output.join("probe.pdf"))?;
    use sha2::{Digest, Sha256};
    let mut paths: Vec<_> = std::fs::read_dir(&output)?
        .map(|entry| entry.map(|e| e.path()))
        .collect::<Result<_, _>>()?;
    paths.sort();
    let mut hash = Sha256::new();
    for path in paths {
        if !path.is_file()
            || matches!(
                path.file_name().and_then(|n| n.to_str()),
                Some("SHA256SUM" | "SOURCE.json")
            )
        {
            continue;
        }
        let name = path.file_name().unwrap().to_string_lossy();
        let bytes = std::fs::read(&path)?;
        hash.update((name.len() as u64).to_le_bytes());
        hash.update(name.as_bytes());
        hash.update((bytes.len() as u64).to_le_bytes());
        hash.update(bytes);
    }
    std::fs::write(
        output.join("SHA256SUM"),
        hash.finalize()
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect::<String>(),
    )?;
    std::fs::write(
        output.join("SOURCE.json"),
        serde_json::to_vec_pretty(
            &serde_json::json!({"bundle_url": args[1], "examples": args[3..]}),
        )?,
    )?;
    Ok(())
}
