# Library sizes

XeTeX + Krilla, without TECkit. Measurements include packaged dependency notices.

## Android

Measured compressed AAR downloads, in MB (decimal). Included CPU builds: arm64-v8a, armeabi-v7a, x86_64.

| Variant | All CPUs | ARMv7 | ARM64 | x86-64 |
|---|---:|---:|---:|---:|
| tiny | 16.09 | 5.90 | 6.36 | 6.65 |
| small | 16.31 | 6.12 | 6.59 | 6.87 |
| balanced | 16.75 | 6.57 | 7.03 | 7.32 |
| full | 34.95 | 13.99 | 14.45 | 14.74 |

CPU columns are measured single-architecture AAR builds, including the shared TeX assets and wrapper code. They are not APK split sizes or measured app download increases. A dash means that build has not been measured.

Maven artifacts include all CPUs. Single-CPU builds are generated only for this comparison with `python3 tools/split-sizes.py`; the TeX assets are included once in each build.

With Android App Bundle delivery or ABI splits, each device receives only its CPU build. The universal AAR download above is not the per-device app size. Android also copies the TeX assets to app storage on first use.

Choose one feature variant. `full` covers the included examples, not all of TeX Live. Tiny, small, and balanced use compact ICU data; full also includes ICU encoding tables and line-break data.

## iOS

Measured growth over the same app without LaTeX, in MB. ARM64 device Release builds; simulator code excluded.

| Variant | Compressed app increase (MB) | Uncompressed app increase (MB) |
|---|---:|---:|
| tiny | 6.82 | 22.20 |
| small | 7.05 | 22.66 |
| balanced | 7.50 | 23.67 |
| full | 14.94 | 39.18 |

Baseline: 0.02 MB compressed, 0.09 MB uncompressed.

Local unsigned builds with dead-code stripping. Compressed values use ZIP compression; uncompressed values sum app file sizes. These are measured build comparisons, not App Store download sizes or filesystem allocation. Signing, Apple processing, and app contents can change delivery sizes. See [Apple’s app-size measurement guidance](https://developer.apple.com/documentation/Xcode/reducing-your-app-s-size).

Reproduce with `python3 tools/ios-sizes.py --version VERSION` (Xcode and XcodeGen required). The probe links and calls the compiler; the baseline uses the same UI without the library. Results include each profile’s TeX assets.
