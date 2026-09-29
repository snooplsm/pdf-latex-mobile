# Krilla XDV backend probe

Experimental Krilla 0.8.2 PDF backend with a local MIT `tectonic_xdv` 0.3.0 parser extension. Production is unchanged. The separate `../xetex-native` frontend removes the two GPL PDF crates; source, dependency, TeX-package and font license review remains incomplete.

```sh
python3 experiments/krilla-xdv/prepare-xdv.py # once; refuses to overwrite
python3 experiments/krilla-xdv/prepare-krilla.py # once; normalized RGB and deterministic compression
python3 -m venv .build/fonttools-venv
.build/fonttools-venv/bin/pip install fonttools==4.60.2
.build/fonttools-venv/bin/python experiments/krilla-xdv/convert-fonts.py
CARGO_TARGET_DIR="$PWD/.build/krilla-xdv-target" cargo build --release --manifest-path experiments/krilla-xdv/Cargo.toml
CARGO_TARGET_DIR="$PWD/.build/krilla-xdv-target" cargo test --release --manifest-path experiments/krilla-xdv/Cargo.toml
.build/krilla-xdv-target/release/krilla-xdv-probe \
  .build/xdv-probe/math.xdv .build/krilla-fonts .build/xdv-probe/math-krilla.pdf
python3 experiments/krilla-xdv/prepare-fixtures.py # original xdv-probe must be built
python3 experiments/krilla-xdv/compare.py # Pillow, pypdf, pdftoppm
python3 experiments/krilla-xdv/android.py # running ARM64 emulator
python3 experiments/krilla-xdv/ios.py # booted ARM64 iOS simulator
```

All ten current fixtures compile: core, text, math, fonts, languages, bibliography, graphics, diagrams, invoice, and PNG-logo invoice. Text extraction, page counts and page boxes match the baseline; repeated raw PDF hashes match. All ten backend PDFs also match between host, Android ARM64 and iOS ARM64, twice on each mobile platform. These backend checks consume identical host-generated XDV. Full source-to-PDF checks are separate (`../xetex-native/mobile.py`).

At 144 DPI, math, diagrams, languages and bibliography are pixel-identical to Tectonic. Core differs by 100 pixels, fonts by 66, text by 51, graphics by 63, and each invoice by 901, out of 1,938,816 pixels per page. Math also matches exactly at 300 DPI, with one differing pixel at both 72 and 96 DPI. This is not complete visual parity across renderers and resolutions. `compare.py` fails on lost compilation, determinism, text, page-count or page-box parity, and preserves exact pixels for the four identical cases.

Traditional fonts use TFM widths and explicit character positions from the patched parser. `convert-fonts.py` converts the six bundled Type 1 fonts to distinctly named CFF OpenType fonts at build time, retaining source notices and SHA-256 provenance. Cubic outlines are retained, Type 1 hints are not. Repeated conversion hashes match; the six generated fonts total 0.109 MB uncompressed. This is not a general Type 1/virtual-font implementation or a completed font-license review. Conversion now verifies the original PFB hashes against the AMS distribution and copies its OFL notice alongside the generated fonts. No Python runtime is needed on mobile.

Unsupported operations fail. Remaining coverage includes more TikZ operators, native font effects, text-and-glyph commands, virtual fonts, general Unicode mappings, image transformations/page boxes and more multi-page behavior. Nine Rust tests cover graphics-state cleanup, malformed operators, content nesting, TFM widths/validation, positioned traditional characters across stack operations malformed font names, fractional RGB and page-size precision.

Host backend CLI: 2.76 MB raw / 1.16 MB ZIP, excluding the frontend/fonts/assets/wrappers. Not an AAR or app-size estimate. Evidence: `.build/xdv-probe/krilla-comparison.json`, `.build/krilla-{android,ios}/result.json`. Rebuilding reference XDV is documented in `../xdv-probe/README.md`.

The full native frontend/backend check passed all ten LaTeX fixtures on both mobile platforms, twice each: 80 intermediate XDV and final PDF hash comparisons matched the host. This does not exercise the production Kotlin/Swift wrappers.

Extended fixture: `fixtures/multipage.tex` spans three A5 pages, retaining/restoring color and reusing native and traditional fonts. All pages are raster-compared. The normalized-RGB extension and page-box rounding reduced its differences from 5,724 pixels to 134; page boxes now match. Exact extracted text still differs around commas after font changes, so `compare.py` intentionally returns a failing status for this fixture. Android/iOS backend hashes match for all eleven cases. The original ten fixtures retain their prior baseline checks.

The renderer is also available as a Rust library (the CLI calls the same function):

```rust
let pdf = krilla_xdv_probe::render(
    std::io::Cursor::new(xdv_bytes),
    std::path::Path::new("fonts"),
    Some(std::path::Path::new("assets")),
)?;
std::fs::write("invoice.pdf", pdf)?;
```

XDV can come from a file or an in-memory cursor. PDF construction still returns a `Vec<u8>`; this does not claim streaming PDF output.

The local Krilla and hayro-write patches use pinned miniz_oxide 0.8.9 for PDF stream encoding. Otherwise, linking the LaTeX frontend changes flate2 feature selection and therefore raw PDF bytes, even when decoded page streams match. This keeps standalone and integrated renderer compression consistent.

Page-geometry regression: `check-page-geometry.py` (Pillow + pypdf runtime) compares drawing origins separately from rounded page boxes. The A5 surface now retains precise dimensions while MediaBox retains the original hundredth-point rounding. Ten renderer tests pass; the strict eleven-fixture comparison still fails on multi-page extracted spacing. Raster differences remain 134 pixels for that fixture at 144 DPI. The corrected multi-page PDF has a new hash; earlier mobile reports predate this change and require rebuilding/rechecking before acceptance.

Converted fonts now use names from `font-renames.json` without the original reserved-name substrings. Verify with `.build/fonttools-venv/bin/python experiments/krilla-xdv/check-fonts.py`; optional `--previous-dir` compares old `LMProbe-*.otf` outlines, cmap and metrics. Six fonts pass identity/notice checks and deterministic regeneration. The isolated eleven-fixture comparison in `.build/renamed-fonts-probe` retains the same raster/text results, including the unresolved multi-page failure. Renaming changes PDF bytes; rebuild mobile libraries/bundles and regenerate references before new cross-platform hash verification. Older mobile reports predate this change.
