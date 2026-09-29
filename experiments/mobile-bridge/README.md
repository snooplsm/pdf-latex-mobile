# Experimental mobile bridge

Build the replacement behind the existing C, Kotlin and Swift APIs. Requires the renderer/font preparation in `../krilla-xdv/README.md` and the original full bundle.

```sh
python3 experiments/xetex-native/prepare.py
python3 experiments/xetex-native/prepare-layout.py
python3 experiments/mobile-bridge/prepare.py
python3 experiments/xetex-native/build.py host --bridge
python3 experiments/xetex-native/build.py android --bridge
python3 experiments/xetex-native/build.py android --bridge --android-abi armeabi-v7a
python3 experiments/xetex-native/build.py android --bridge --android-abi x86_64
python3 experiments/mobile-bridge/check-android-binaries.py
python3 experiments/xetex-native/build.py ios --bridge
python3 experiments/mobile-bridge/check.py
python3 experiments/mobile-bridge/stage-harness.py
PATH="$HOME/.local/bin:$PATH" python3 .build/replacement-harness/tools/mobile-parity.py \
  --profile full --skip-native-build
python3 experiments/mobile-bridge/check-harness.py --ios-device YOUR_SIMULATOR_UDID
```

Preparation scripts refuse to overwrite existing copies. The staged mobile projects use separate application IDs. The Android ARM64 emulator and iOS ARM64 simulator run the existing invoice tests twice and compare raw PDF hashes. Production sources and release artifacts remain unchanged.

The layout patch clears font-number caches under the engine lock before every XeTeX run. Without it, compiling different documents in one process can reuse glyph metrics from a previous document.

This remains experimental: original-backend rendering differences, broader feature/ABI coverage and the complete dependency/font/TeX license review are unresolved. Matching mobile hashes alone does not establish original-backend parity.

Verified locally: six existing Android tests and four existing iOS tests pass. The invoice generated twice on each platform has the same raw hash as the host replacement reference. The full ARM64 AAR is 9.59 MB, including assets (current production comparison: 13.09 MB); this is not an app-download measurement. Reports are under `.build/replacement-harness/` (`wrapper-tests/result.json`, `dist/parity/run-*/result.json`, `aar-size.json`).

Current extended wrapper run:

```sh
python3 experiments/xetex-native/build.py ios --bridge --ios-device
python3 experiments/mobile-bridge/stage-harness.py --destination .build/replacement-harness-current --extended-fixtures --include-device
PATH="$HOME/.local/bin:$PATH" python3 .build/replacement-harness-current/tools/mobile-parity.py --profile full --skip-native-build
python3 experiments/mobile-bridge/check-harness.py --stage .build/replacement-harness-current --reference-pdf .build/jpeg-regression-probe/invoice-krilla.pdf --ios-device YOUR_SIMULATOR_UDID
python3 experiments/mobile-bridge/measure-ios.py --stage .build/replacement-harness-current
```

All six Android and four Swift wrapper tests pass with the five JPEG fixtures and multi-page fixture added to the staged manifest (sixteen document variants total, including the PNG invoice). Invoice raw hashes match across platforms. The combined device/simulator XCFramework links successfully in an unsigned ARM64 device Release app; no physical-device runtime claim is made.

The same production size probe measures the experimental full iOS library at 9.20 MB compressed app increase and 28.19 MB uncompressed, compared with the existing production measurements of 13.27 MB and 33.68 MB. This is an unsigned local ZIP comparison, not an App Store download prediction. Reports: `.build/replacement-harness-current/wrapper-tests/result.json` and `dist/ios-sizes.json` within that staged tree.
