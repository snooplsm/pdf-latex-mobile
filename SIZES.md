# Library sizes

XeTeX + Krilla, without TECkit. Measurements include packaged dependency notices.

## Android

Measured compressed AAR downloads, in MB (decimal). Included CPU builds: arm64-v8a, armeabi-v7a, x86_64.

| Variant | All CPUs | ARMv7 | ARM64 | x86-64 |
|---|---:|---:|---:|---:|
| tiny | 12.73 | 4.50 | 4.86 | 5.03 |
| tiny | 16.04 | 5.85 | 6.31 | 6.60 |
| small | 12.96 | 4.72 | 5.08 | 5.25 |
| small | 16.26 | 6.07 | 6.54 | 6.83 |
| balanced | 16.71 | 6.52 | 6.98 | 7.27 |
| balanced | 13.49 | 5.26 | 5.62 | 5.79 |
| full | 31.74 | 12.73 | 13.09 | 13.26 |
| full | 34.90 | 13.94 | 14.40 | 14.69 |

CPU columns are measured single-architecture AAR builds, including the shared TeX assets and wrapper code. They are not APK split sizes or measured app download increases. A dash means that build has not been measured.

Maven artifacts include all CPUs. Single-CPU builds are generated only for this comparison with `python3 tools/split-sizes.py`; the TeX assets are included once in each build.

With Android App Bundle delivery or ABI splits, each device receives only its CPU build. The universal AAR download above is not the per-device app size. Android also copies the TeX assets to app storage on first use.

Choose one feature variant. `full` covers the included examples, not all of TeX Live. Tiny, small, and balanced use compact ICU data; full also includes ICU encoding tables and line-break data.

## iOS

Measured growth over the same app without LaTeX, in MB. ARM64 device Release builds; simulator code excluded.

| Variant | Compressed app increase (MB) | Uncompressed app increase (MB) |
|---|---:|---:|
| tiny | 6.78 | 22.03 |
| small | 7.00 | 22.49 |
| balanced | 7.45 | 23.50 |
| full | 14.89 | 39.01 |

Baseline: 0.02 MB compressed, 0.09 MB uncompressed.

Local unsigned builds with dead-code stripping. Compressed values use ZIP compression; uncompressed values sum app file sizes. These are measured build comparisons, not App Store download sizes or filesystem allocation. Signing, Apple processing, and app contents can change delivery sizes. See [Apple’s app-size measurement guidance](https://developer.apple.com/documentation/Xcode/reducing-your-app-s-size).

Reproduce with `python3 tools/ios-sizes.py` (Xcode and XcodeGen required). The probe links and calls the compiler; the baseline uses the same UI without the library. Results include each profile’s TeX assets.
