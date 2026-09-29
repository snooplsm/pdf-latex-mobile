//! Local diagnostic for assessing replacement PDF backends. Still links Tectonic.
use std::path::PathBuf;
use tectonic::driver::{OutputFormat, ProcessingSessionBuilder};
use tectonic_bundles::dir::DirBundle;
use tectonic_status_base::NoopStatusBackend;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 4 {
        return Err("usage: xdv-probe BUNDLE INPUT.tex OUTPUT.xdv".into());
    }
    let source = PathBuf::from(&args[2]);
    let scratch = tempfile::tempdir()?;
    let assets = source.with_extension("assets");
    if assets.is_dir() {
        for entry in std::fs::read_dir(assets)? {
            let entry = entry?;
            if entry.file_type()?.is_file() {
                std::fs::copy(entry.path(), scratch.path().join(entry.file_name()))?;
            }
        }
    }
    let input = std::fs::read(&source)?;
    let mut status = NoopStatusBackend::default();
    let mut builder = ProcessingSessionBuilder::new_with_security(
        tectonic_bridge_core::SecuritySettings::default(),
    );
    builder
        .primary_input_buffer(&input)
        .tex_input_name("main.tex")
        .filesystem_root(scratch.path())
        .format_cache_path(scratch.path())
        .format_name("latex")
        .output_format(OutputFormat::Xdv)
        .do_not_write_output_files()
        .shell_escape_disabled()
        .bundle(Box::new(DirBundle::new(&args[1])));
    let mut session = builder.create(&mut status)?;
    session.run(&mut status)?;
    let mut files = session.into_file_data();
    let data = files.remove("main.xdv").ok_or("missing XDV output")?.data;
    std::fs::write(&args[3], data)?;
    Ok(())
}
