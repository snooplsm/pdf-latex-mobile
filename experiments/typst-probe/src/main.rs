fn main() {
    let args: Vec<String> = std::env::args().collect();
    assert!(
        args.len() >= 4,
        "usage: typst-mobile-probe input.typ output.pdf font.otf [font.otf ...]"
    );
    let source = std::fs::read_to_string(&args[1]).unwrap();
    let fonts = args[3..]
        .iter()
        .map(std::path::PathBuf::from)
        .collect::<Vec<_>>();
    let pdf = typst_mobile_probe::compile(
        &source,
        &fonts,
        &[("logo.svg".into(), "examples/invoice-logo.svg".into())],
    )
    .unwrap();
    std::fs::write(&args[2], pdf).unwrap();
}
