# LaTeX Mobile

Offline Tectonic library with Android/Kotlin and iOS/Swift harnesses. MIT project code. Only compile trusted LaTeX; shell escape and HTTP are disabled, but this is not a filesystem or CPU sandbox.

```kotlin
// Choose exactly ONE artifact from the Maven Central after publication; local staging is dist/maven.
implementation("io.github.snooplsm:latex-mobile-tiny:0.1.0")
// implementation("io.github.snooplsm:latex-mobile-small:0.1.0")
// implementation("io.github.snooplsm:latex-mobile-balanced:0.1.0")
// implementation("io.github.snooplsm:latex-mobile-full:0.1.0")

// On a worker thread:
val result = LatexMobile.compile(context,
    """\documentclass{article}\begin{document}Hello!\end{document}""",
    File(context.filesDir, "hello.pdf"))
```

```swift
let result = try await LaTeXMobile.compile(
    #"\documentclass{article}\begin{document}Hello!\end{document}"#,
    to: FileManager.default.temporaryDirectory.appendingPathComponent("hello.pdf"))
```

| Variant | Example-backed features |
|---|---|
| tiny | Basic article, English hyphenation |
| small | tiny + headings, bold, italic |
| balanced | small + AMS math, graphics, color, logo invoice |
| full | balanced + TikZ, OpenType font, languages, BibTeX |

Actual AAR measurements: [SIZES.md](SIZES.md). `full` means all included examples, not all TeX Live. Add representative documents for your packages. Exclusions remove unique data dependencies; tiny/small/balanced also omit ICU legacy encoding tables and native Unicode line-breaking data. Full retains those features. Image and other input files can be passed in the `assets` map (relative filenames to bytes). See `examples/invoice.tex` and `examples/invoice.assets/logo.pdf`.

```sh
# macOS build prerequisites: Rust, Xcode, JDK 17+, Android SDK/NDK r29,
# brew install m4 pkg-config autoconf autoconf-archive automake libtool xcodegen
./tools/bootstrap.sh
export VCPKG_ROOT="$PWD/.build/vcpkg" TECTONIC_DEP_BACKEND=vcpkg VCPKGRS_TRIPLET=arm64-osx
cargo run --locked -p bundle-fetch -- \
  https://data1.fullyjustified.net/tlextras-2022.0r0.tar .build/tex examples/*.tex
./tools/build-native.sh host

# Each bundle is recompiled offline after pruning. Optional custom corpus:
python3 tools/pack.py --source .build/tex --preset full --exclude diagrams \
  --exclude languages --example examples/math.tex --output dist/custom

export ANDROID_HOME="$HOME/Library/Android/sdk"
export ANDROID_NDK_HOME="$ANDROID_HOME/ndk/29.0.14206865"
./tools/build-native.sh android
python3 tools/release.py --source .build/tex --version 0.1.0
# dist/aar, dist/maven, dist/sizes.json, SIZES.md (local staging; no upload)
android/gradlew -p android :harness:installTinyDebug :library:connectedTinyDebugAndroidTest

./tools/build-native.sh ios
python3 tools/prepare-ios.py tiny
(cd ios && xcodegen generate)
xcodebuild -project ios/LaTeXMobileHarness.xcodeproj -scheme Harness \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' test

cargo test --locked -p latex-mobile
python3 -m unittest discover -s tools -p 'test_*.py'
```

See [THIRD_PARTY.md](THIRD_PARTY.md) before distributing binaries. The host-only bundle collector has network access; mobile builds must select `-p latex-mobile`, not `--workspace`.

```sh
# Maven Central: verify io.github.snooplsm using GitHub login in central.sonatype.com.
# Store the portal token as {"username":"...","password":"..."} outside the repo:
chmod 600 "$HOME/.config/latex-mobile/central.json"
export MAVEN_SIGNING_KEY_FILE="$HOME/.config/latex-mobile/signing.asc"
# Set MAVEN_SIGNING_PASSWORD for an encrypted PGP key; publish its public key to a keyserver.
python3 tools/release.py --source .build/tex --notices .build/notices
python3 tools/central.py upload
python3 tools/central.py status
python3 tools/central.py publish  # after VALIDATED; verify PUBLISHED with status
# GitHub releases are also created locally, with gh; no GitHub Actions.
```

```sh
# Invoice example with an embedded vector PDF logo (PNG alternative also included).
python3 tools/invoice.py
# output/pdf/northstar-invoice.pdf; source: examples/invoice.tex
# SVG is a design source; convert it to PDF before using it with includegraphics.
```

```sh
# Run the invoice sample apps, then select Invoice · PDF logo or Invoice · PNG logo.
android/gradlew -p android :harness:installBalancedDebug
python3 tools/prepare-ios.py balanced
(cd ios && xcodegen generate)
open ios/LaTeXMobileHarness.xcodeproj  # Run the Harness scheme on a simulator.
```
