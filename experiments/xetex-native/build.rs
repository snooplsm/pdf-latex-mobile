fn main() {
    match std::env::var("CARGO_CFG_TARGET_OS").as_deref() {
        Ok("android") => {
            println!("cargo:rustc-link-arg=-lc++_static");
            println!("cargo:rustc-link-arg=-lc++abi");
        }
        Ok("ios") => {
            for name in ["CoreText", "CoreGraphics", "Foundation"] {
                println!("cargo:rustc-link-lib=framework={name}");
            }
        }
        _ => {}
    }
}
