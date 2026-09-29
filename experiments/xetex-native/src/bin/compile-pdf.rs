use anyhow::{Result, ensure};
use std::path::Path;
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args_os().collect();
    ensure!(
        args.len() == 5,
        "usage: compile-pdf BUNDLE FONT_DIRECTORY INPUT.tex OUTPUT.pdf"
    );
    let source = Path::new(&args[3]);
    xetex_native_probe::compile_pdf_file(
        &std::fs::read(source)?,
        Path::new(&args[1]),
        Path::new(&args[2]),
        &xetex_native_probe::fixture_assets(source)?,
        Path::new(&args[4]),
    )
}
