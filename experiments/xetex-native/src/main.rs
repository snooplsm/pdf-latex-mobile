use anyhow::{Result, ensure};
use std::path::Path;
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args_os().collect();
    ensure!(
        args.len() == 4,
        "usage: xetex-native-probe BUNDLE INPUT.tex OUTPUT.xdv"
    );
    let source = Path::new(&args[2]);
    let data = xetex_native_probe::compile_xdv(
        &std::fs::read(source)?,
        Path::new(&args[1]),
        &xetex_native_probe::fixture_assets(source)?,
    )?;
    std::fs::write(&args[3], data)?;
    Ok(())
}
