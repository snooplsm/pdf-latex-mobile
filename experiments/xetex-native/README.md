# Experimental in-process LaTeX/PDF library

XeTeX produces XDV and Krilla generates PDF in the same process. The two original GPL PDF crates are removed; the remaining license review is incomplete. Production artifacts are unchanged.

```rust
let assets = std::collections::BTreeMap::from([
    ("logo.pdf".into(), std::path::PathBuf::from("invoice.assets/logo.pdf")),
]);
xetex_native_probe::compile_pdf_file(
    latex.as_bytes(),
    std::path::Path::new("texbundle"),
    std::path::Path::new("fonts"),
    &assets,
    std::path::Path::new("invoice.pdf"),
)?;
```

```sh
python3 experiments/xetex-native/prepare.py
python3 experiments/xetex-native/prepare-layout.py
# Prepare renderer/fonts using ../krilla-xdv/README.md.
python3 experiments/xetex-native/build.py host
python3 experiments/xetex-native/build.py android
python3 experiments/xetex-native/build.py ios

.build/xetex-native-target/release/compile-pdf \
  dist/bundles/full/texbundle .build/krilla-fonts \
  examples/invoice.tex .build/invoice-combined.pdf
```

Preparation refuses to overwrite existing vendor directories. File assets use bounded copies; XDV and PDF construction still use memory buffers. Compiles are serialized and replace the output atomically.

```sh
# These host checks require Pillow, pypdf and pdftoppm.
python3 experiments/krilla-xdv/compare.py --output-dir .build/page-groups-regression
python3 experiments/xetex-native/check-jpeg.py
python3 experiments/xetex-native/check-pdf-pages.py
python3 experiments/xetex-native/check-colors.py

# Thirty documents, twice per platform, with matching source/asset/font hashes.
python3 experiments/xetex-native/combined-check.py host --reference-dir .build/page-groups-regression --include-jpeg --include-colors-and-pdf-pages
python3 experiments/xetex-native/combined-check.py android --reference-dir .build/page-groups-regression --include-jpeg --include-colors-and-pdf-pages
python3 experiments/xetex-native/combined-check.py ios --reference-dir .build/page-groups-regression --include-jpeg --include-colors-and-pdf-pages
python3 experiments/xetex-native/summarize-mobile-checks.py --include-colors-and-pdf-pages
```

The broad host comparison still fails on existing original-engine differences; its report preserves those failures. Cross-platform checks compare replacement outputs, using ARM64 native processes rather than Kotlin/Swift wrappers. Reports are in `.build/combined-pipeline/{host,android,ios}/result.json` and `latest-summary.json`.

Imported PDFs use explicit xdvipdfmx compatibility: source page transparency groups are omitted, matching the original backend. This can differ from the source PDF's own transparency semantics. Page selection supports default page 0 and positive page numbers, with cropbox and identity image matrices. Broader PDF transforms, EXIF density/orientation and streaming image metadata remain unsupported. The three newer CMYK path cases pass on host; they are not yet part of the thirty-document mobile run.
