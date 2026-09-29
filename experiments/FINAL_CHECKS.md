# Historical XeTeX + Krilla experiment checks

This records the pre-integration experiment. Current production release evidence
and remaining checks are in [RELEASE_REVIEW.md](../RELEASE_REVIEW.md).

**Result: not ready to publish.** Selected-backend checks are complete enough to identify failing and unverified release requirements; they do not certify full parity or licensing clearance.

| Check | Result |
|---|---|
| Latest invoice: Android/iOS, twice each | All four raw PDF hashes match |
| Full-profile app wrappers, 33 document variants | 6 Android tests and 4 iOS tests pass |
| Android ARMv7/ARM64/x86-64 | Builds, public symbols and 16 KB ELF alignment pass; only ARM64 runtime tested |
| iOS ARM64 | Device and simulator libraries build; simulator wrapper tests pass |
| Original renderer comparison | 4/11 exact raster matches; 7 retain differences; multipage text differs |
| Dependency graph | Removed GPL PDF crates absent from 879 dependency records; not full license clearance |
| Production integration and all four profiles | Incomplete |

## Release blockers

- Seven of eleven original-renderer cases retain raster differences; multipage text extraction differs.
- GPL-declared Czech, Indonesian, Macedonian and Slovak patterns remain in the tested app bundle; Latvian has LGPL/GPL alternatives.
- Reviewed Slovak/configuration/license overlays are not integrated into the tested app bundle.
- TECkit CPL/LGPL distribution path, covered-work scope and notices/source publication remain unresolved.
- LPPL modified-work identification and remaining TeX/font/native license review are incomplete.
- Final binary link-map/license mapping and complete release notices/source distribution are not established.
- Replacement tiny/small/balanced profiles and their current sizes are not verified.
- ARMv7/x86-64 Android and physical iOS runtime coverage is missing; builds/structure alone do not prove runtime behavior.
- Production crates/latex-mobile still uses the original Tectonic PDF backend; migration is not complete.
- Expanded 33-document wrapper checks validate generation/readability; fresh raw cross-platform hash equality was checked for the invoice, not every one of those 33 documents.

## Original-renderer raster comparison

| Document | Different pixels at 144 DPI |
|---|---:|
| bibliography | 0 |
| core | 100 |
| diagrams | 0 |
| fonts | 66 |
| graphics | 63 |
| invoice-png | 901 |
| invoice | 901 |
| languages | 0 |
| math | 0 |
| multipage | 134 |
| text | 51 |

Evidence and hashes: `final-readiness.json`. No release was published.
