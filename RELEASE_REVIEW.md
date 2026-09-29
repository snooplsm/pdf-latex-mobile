# Release candidate 0.1.0-alpha.2

Local candidate only; not uploaded or published to Maven Central.
Original project code remains MIT. Dependency choices are in
[notices/DEPENDENCY-LICENSE-CHOICES.txt](notices/DEPENDENCY-LICENSE-CHOICES.txt).

Completed:

- Production XeTeX + Krilla build excludes TECkit and the old PDF backend crates.
- All three Android ABIs, compact/full native profiles, and iOS device/simulator build.
- All six Android native libraries export the compiler and have 16 KB load alignment;
  none exports TECkit symbols.
- Czech, Indonesian, Macedonian, Latvian and Armenian automatic patterns are excluded.
  Language identifiers remain; explicit hyphenation hints and Unicode text still work.
- All four AARs contain notices, modification identification and MPL option-ext source.
- Latin Modern font files match the upstream archive byte for byte; GUST license retained.
  Converted AMS fonts retain OFL notices and distinct names.
- `balanced` and `full` Android/iOS invoices have identical raw hashes across repeat runs.
- Ibycus 3.0 is byte-matched to its source archive and first-party metadata identifies
  the legacy file as LPPL. All nine quote-pattern derivatives match their identified
  base patterns; see `experiments/licenses/legacy-pattern-provenance.json`.
- Legacy dummy/empty loaders are replaced by the project empty loader. The diagnostic
  dummy language no longer loads dummy test patterns.
- Custom asset-font loading passes the updated full-profile suites: 7 Android tests
  and 5 iOS tests. Earlier all-profile Android suites passed; invoice tests are
  skipped only for tiny/small, which do not include the invoice feature.
- Current AAR/ABI and iOS size measurements are in [SIZES.md](SIZES.md).
- Maven source JARs include production crates, vendored sources and build inputs.
  A separate local source archive includes upstream LaTeX/font archives and all bundles.

Remaining distribution review:

- Finish file-level source/version coverage for remaining TeX packages beyond the
  verified LaTeX base, AMS math, graphics, firstaid and fonts. Preserve their original
  notices and source retrieval information with the final source distribution.
- Confirm final source archive, notices and signed Maven artifacts all correspond
  to the final committed revision before publication.

Runtime coverage is ARM64 Android emulator and iOS simulator. ARMv7/x86-64 Android
and physical iOS builds are verified as builds, not as physical-device runtime tests.
Original-backend raster comparisons are historical compatibility measurements;
current cross-platform invoice byte equality is independently verified.
