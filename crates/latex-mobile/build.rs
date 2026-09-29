fn main() {
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("ios") {
        // HarfBuzz enables its CoreText shaper on Apple platforms.
        for framework in ["CoreText", "CoreGraphics", "CoreFoundation"] {
            println!("cargo:rustc-link-lib=framework={framework}");
        }
    }
}
