# Replacement-engine license evidence

```sh
python3 experiments/audit-licenses.py
python3 experiments/review-teckit.py
python3 experiments/review-latex-base.py
python3 experiments/review-latex-packages.py
python3 experiments/collect-review-sources.py
```

The inventory covers resolved normal/build Cargo dependencies across targets and installed native notices. It is broader than a final link map and is not release clearance. Results go to `.build/replacement-license-audit`.

- Neither removed GPL PDF crate is in the replacement dependency graph.
- XeTeX still embeds modified TECkit sources. The pinned 2016 upstream terms offer CPL-0.5-or-later or LGPL-2.1-or-later. Source comparisons are recorded in `teckit-provenance.json`; these are not unmodified upstream files. Exact shipped sources are included in the reproducible review archive.
- `option-ext` 0.2.0 is MPL-2.0 and appears in the Android dependency tree through `directories`. Its original source and license are included in the review archive.
- All six PFB inputs match the AMS archive byte-for-byte. Their OFL-1.1 text and verified hashes are retained here. Generated fonts use the shared `font-renames.json` map with no reserved-name substrings in their identities. Copyright and license metadata are retained; conversion rejects unverified source hashes. `check-fonts.py` verifies all six font identities and can compare outlines/metrics with a prior conversion.
- Some other dependencies offer multiple licenses. A GPL/LGPL alternative in an `OR` expression does not by itself mean that alternative is selected.

Still required: final license choices and notices, source-distribution/offer integration, review of TeX packages and other font/native dependencies, and a link-map check against actual release artifacts. The review archive is not a complete release source distribution.

Sources: [TECkit licensing](https://github.com/silnrsi/teckit/blob/41c20be2793e1afcbb8de6339af89d1eeab84fe8/license/LICENSING.txt), [AMS distribution](https://ctan.org/tex-archive/fonts/amsfonts).

`tex-file-review.json` records hashes and header evidence for seven bundled files whose catalogue mappings were ambiguous or overly broad. These file-level findings do not resolve distribution obligations or clear the entire TeX bundle. Font renaming follows [OFL reserved-name guidance](https://openfontlicense.org/ofl-reserved-font-names/).

UnicodeData.txt and SpecialCasing.txt are verified byte-for-byte against the official Unicode 14.0.0 files; hashes and upstream URLs are in `unicode-provenance.json`, with the current Unicode license notice retained. Four previously unmapped German pattern/wrapper files have explicit MIT or free-use/modify/distribute headers, recorded in `tex-file-review.json`.

The pinned upstream Slovak file in `bundle-overrides/` declares MIT and has exactly the same non-comment tokens as the older bundled GPL file. `hyphenation-provenance.json` records both hashes. The reviewed overlay is composed by `python3 experiments/prepare-review-bundle.py .build/review-bundle`, and `python3 experiments/check-review-bundle.py` compares PDFs before/after, including a Slovak hyphenation fixture. This is an isolated full bundle, not a production release.

Actual GPL-only declarations remain in Czech, Indonesian and Macedonian pattern files; Latvian offers LGPL/GPL alternatives. These are not resolved by the PDF-backend replacement. Do not describe the bundle as wholly permissive or cleared for release.

Alternative pattern review: the MIT Czech/Czechoslovak patterns used by Hypher were tested against the selected Czech data at four column widths. Every resulting layout differed, including hyphenation points; no substitution was adopted. Results are in `czech-alternative-results.json`. The JavaScript hyphen package also retains GPL source declarations for Indonesian and Macedonian; provenance is recorded in `pattern-alternatives.json`. Repository-level licenses must not be substituted for the pattern files' own terms.

`teckit-distribution-review.json` checks all seven embedded TECkit files against the published XeTeX crate and records their two bridge dependencies. The source collection includes those bridge crates and preparation inputs. It evaluates the CPL distribution path but leaves release terms, source publication, covered-program scope and commercial-distribution review unresolved.
