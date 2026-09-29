# Replacement-engine probes

Selected backend: **XeTeX + Krilla**, as requested by the user. Further work targets integrating this backend rather than selecting another engine. Production migration and release acceptance are still incomplete.

The latest native-process check covers 30 documents twice on host, Android ARM64 emulator and iOS ARM64 simulator: all 180 PDF hashes match. This does not establish exact original-engine rendering parity or complete license clearance. See `xetex-native/mobile-results.json`.

Acceptance requires offline Android ARMv7/ARM64/x86-64 and iOS support; feature coverage for tiny/small/balanced/full; invoice assets and layout; deterministic raw PDF hashes across Android/iOS; file/stream asset APIs; measured per-platform sizes; and a complete dependency/font license review. Retaining `.tex` compatibility is distinct from translating our examples to another syntax.

| Candidate | Evidence | Remaining gap |
|---|---|---|
| Patched XeTeX frontend | Removes both GPL PDF crate dependencies; all ten XDV outputs match on host/Android/iOS; ten end-to-end PDF outputs also match. | Prototype metadata support is limited; full license audit and production integration remain. |
| Krilla 0.8.2 + XDV adapter | Ten cases, including traditional math, TikZ and both invoice logos, compile; text and page boxes match; repeat hashes match. Four pixel-identical, six have small raster differences. Host backend CLI ZIP 1.16 MB, excluding engine/fonts. | Backend hashes match across host/Android/iOS; broader graphics/font coverage and production integration incomplete. A separate patched frontend removes the two GPL PDF crates. |
| Typst 0.15.1 | Host invoice with SVG visually inspected; repeated raw PDF hashes match. Host dylib ZIP 12.92 MB; stripped Android ARM64 library ZIP 11.32 MB before fonts. | Different language; mobile size/parity, feature corpus, streaming and full license audit unverified. |
| rtex 32ac01c0b754e10111f24f81c7932cf5ccd0a247 | Apache-2.0 declared; built and ran unchanged corpus. Invoice PDF image failed; existing PNG variant also failed. Diagram returned success but rendered blank. | Upstream documents no TikZ/PGF execution and no full package execution. |
| RusTeX (FlexiFormal), `0812d88f7e5269cf2487018c187d0f7ac2e4b9ce` | Inspected current `tex_engine` and `rustex_lib` manifests: GPL-3.0-or-later. HTML output. | Does not resolve the licensing requirement or provide native PDF output. |
| Texcraft | MIT/Apache-2.0; upstream explicitly says PDF/DVI output is not implemented. | Not a usable full-document PDF replacement today. |

Sources: [Typst](https://github.com/typst/typst), [rtex limitations](https://github.com/yingkitw/rtex/blob/32ac01c0b754e10111f24f81c7932cf5ccd0a247/docs/KNOWN_LIMITATIONS.md), [Texcraft](https://github.com/jamespfennell/texcraft).

A smaller PDF-writing library alone does not replace the LaTeX compiler. Keeping XeTeX while changing the PDF writer also requires removing `tectonic_pdf_io` from XeTeX's PDF image handling, not just changing the final XDV conversion call.

The additional three-page A5 fixture passes cross-platform hashes (88 total XDV/PDF checks across eleven fixtures). It exposed RGB quantization and page-box precision issues, now fixed. Its remaining extracted-spacing mismatch keeps the baseline comparison gate failing; see `krilla-xdv/README.md`. The renderer now exposes a Rust library entry point for eventual frontend integration.

The frontend and renderer now run in one Rust library (`xetex_native_probe::compile_pdf_file`). All 66 combined-pipeline hashes match the standalone references across host/Android/iOS. Integration exposed flate2 feature-dependent compression; the Krilla and embedded-PDF writer patches now explicitly use the same pinned encoder. Production wrappers remain unchanged.
