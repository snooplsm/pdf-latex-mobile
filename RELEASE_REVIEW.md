# Release candidate 0.1.0-alpha.2

Sonatype deployment `78db58a1-8597-42ad-96ac-0ffa45795a17` is VALIDATED with no errors or warnings. Publication is pending.
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

- `tools/verify-source-provenance.py` reopens 103 pinned archives and verifies 330
  full-profile runtime files byte for byte, including PGF, LaTeX3, fontspec, Babel,
  graphics drivers and language patterns. Modified/generated files are explicitly
  reported separately; this source-identity check is not license clearance.

- `tools/verify-generated-bundle.py` reproduces all six converted fonts plus their
  encoding/provenance files from the pinned AMS archive byte for byte. It verifies
  the complete file inventory, hashes, payload totals, empty loader and excluded
  pattern files in all four refreshed bundles.

Final distribution checks:

- The refreshed balanced and full profiles pass four-way raw PDF equality
  (Android/iOS, two runs each), SHA-256
  `fa88fcb7566173b3c395683f8bfdab5c11b3e9d4ced4dd069ffa0c930355ccb7`.
  The language configuration reproduces from its retained public-domain source.
  Packaged notices and every bundle file match the verified inputs. All three
  native libraries match for every AAR; native source JAR contents match the repository.
  All 16 required Maven artifact signatures verify with the release public key.
- Source archive and profile-specific Swift packages are prepared for the GitHub
  prerelease. Maven Central publication and public download verification remain.

Runtime coverage is ARM64 Android emulator and iOS simulator. ARMv7/x86-64 Android
and physical iOS builds are verified as builds, not as physical-device runtime tests.
Original-backend raster comparisons are historical compatibility measurements;
current cross-platform invoice byte equality is independently verified.
