# AAR sizes

Measured compressed AAR downloads, in MB (decimal). Included CPU builds: arm64-v8a, armeabi-v7a, x86_64.

| Variant | Download (MB) | Features |
|---|---:|---|
| tiny | 12.73 | core |
| small | 12.96 | core, text |
| balanced | 13.49 | core, graphics, invoice, math, text |
| full | 31.74 | bibliography, core, diagrams, fonts, graphics, invoice, languages, math, text |

The default universal AARs contain three native builds. Earlier measurements contained only ARM64, so they were smaller. The TeX assets are shared once per AAR.

With Android App Bundle delivery or ABI splits, each device receives only its CPU build. The universal AAR download above is not the per-device app size. Android also copies the TeX assets to app storage on first use.

Choose one feature variant. `full` covers the included examples, not all of TeX Live. Tiny, small, and balanced use compact ICU data; full also includes ICU encoding tables and line-break data.
