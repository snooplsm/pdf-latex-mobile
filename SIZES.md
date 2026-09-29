# AAR sizes

Measured compressed AAR downloads, in MB (decimal). Included CPU builds: arm64-v8a, armeabi-v7a, x86_64.

| Variant | All CPUs | ARMv7 | ARM64 | x86-64 |
|---|---:|---:|---:|---:|
| tiny | 12.73 | 4.50 | 4.86 | 5.03 |
| small | 12.96 | 4.72 | 5.08 | 5.25 |
| balanced | 13.49 | 5.26 | 5.62 | 5.79 |
| full | 31.74 | 12.73 | 13.09 | 13.26 |

CPU columns are measured single-architecture AAR builds, including the shared TeX assets and wrapper code. They are not APK split sizes or measured app download increases. A dash means that build has not been measured.

Maven artifacts include all CPUs. Single-CPU builds are generated only for this comparison with `python3 tools/split-sizes.py`; the TeX assets are included once in each build.

With Android App Bundle delivery or ABI splits, each device receives only its CPU build. The universal AAR download above is not the per-device app size. Android also copies the TeX assets to app storage on first use.

Choose one feature variant. `full` covers the included examples, not all of TeX Live. Tiny, small, and balanced use compact ICU data; full also includes ICU encoding tables and line-break data.
