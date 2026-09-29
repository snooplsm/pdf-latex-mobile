use anyhow::{Result, bail};
use std::path::Path;

fn main() -> Result<()> {
    let args: Vec<_> = std::env::args_os().collect();
    if args.len() != 4 && args.len() != 5 {
        bail!("usage: krilla-xdv-probe INPUT.xdv FONT_DIRECTORY OUTPUT.pdf [ASSET_DIRECTORY]");
    }
    let pdf = krilla_xdv_probe::render(
        std::fs::File::open(&args[1])?,
        Path::new(&args[2]),
        args.get(4).map(Path::new),
    )?;
    std::fs::write(&args[3], pdf)?;
    Ok(())
}
