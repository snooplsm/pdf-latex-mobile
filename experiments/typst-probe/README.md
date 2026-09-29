# Typst size and compatibility probe

Isolated experiment; production artifacts still use Tectonic. Typst accepts `.typ`, not `.tex`. Invoice rendering alone does not establish LaTeX or full feature parity.

```sh
CARGO_TARGET_DIR="$PWD/.build/typst-probe-target" cargo build --release --manifest-path experiments/typst-probe/Cargo.toml
.build/typst-probe-target/release/typst-mobile-probe \
  experiments/typst-probe/invoice.typ .build/typst-invoice.pdf \
  .build/tex/lmsans10-regular.otf .build/tex/lmsans10-bold.otf
```

Uses explicit fonts and assets, with no system font discovery or network fetching. Current probe loads those files into memory; streaming remains unimplemented. The C entry point only supports a single font and no assets, and is not a production API.

Before recommending adoption: measure Android ARMv7/ARM64/x86-64 and iOS device builds, reproduce exact hashes across simulator/emulator, check the feature corpus, inspect rendering, and audit transitive source/font licenses. Declared Cargo licenses are only an initial screen.

Initial macOS ARM64 measurement (not an Android/iOS delivery estimate): compiled dylib 40.87 MB, ZIP level 6 12.92 MB, excluding fonts. Release settings above. Two calls through the C ABI generated matching raw PDF hashes for a basic text document. The translated invoice with SVG rendered cleanly on the host and repeated raw PDF hashes matched (`0b80877c81b1ba54f429108078b1d1ad4670d84bddbc21460e134481f8af8a6b`). This does not establish matching LaTeX layout or mobile parity; mobile and feature-profile sizes remain unmeasured. Scratch measurements are in `.build/typst-probe-size.json`.

Android ARM64 API 28 release library built successfully with NDK 29.0.14206865. After `llvm-strip --strip-unneeded`: 28.57 MB raw, 11.32 MB ZIP level 6, excluding fonts and wrapper/resources. This is the actual target `.so`, not an AAR or measured app download. Device execution and cross-platform PDF hashes remain unverified. Measurement: `.build/typst-android-size.json`.
