Project code: MIT. Engine: the XeTeX frontend from [Tectonic](https://github.com/tectonic-typesetting/tectonic), with [Krilla](https://github.com/LaurenzV/krilla) for PDF output. The production graph excludes `tectonic_pdf_io` and `tectonic_engine_xdvipdfmx`. Vendored sources and changes are recorded in `vendor/PROVENANCE.json`; upstream components retain their notices. TeX packages and fonts retain their individual licenses; the project MIT license does not relicense them.

`Cargo.lock` pins Rust dependencies. `tools/bootstrap.sh` pins vcpkg. Before public binary distribution, collect the corresponding native, Rust, TeX, and font license/source notices and pass their directory via `tools/release.py --notices DIRECTORY`; it is copied into each artifact. Local staging is not a public release.

Current release evidence and outstanding checks are recorded in [release review](RELEASE_REVIEW.md). Historic experiment reports describe earlier artifacts.

Project licensing policy: retain MIT for original project code and select
permissive alternatives where upstream explicitly offers them. Third-party
licenses are not replaced by the project license. Full-profile GPL-only
language data cannot be changed to a weaker license by this project; it must
be distributed under its existing terms or replaced/omitted. LGPL alternatives
are available only where the individual component explicitly grants them.

The packer includes [the LaTeX modification notice](notices/LATEX-MODIFICATIONS.txt)
and a reference in the modified kernel itself, and rejects an unreviewed kernel
hash rather than attaching a potentially inaccurate notice.

The current source removes embedded TECkit implementation files and uses ICU for
normalization plus project-authored TeX punctuation mapping. Historical TECkit
notices remain as provenance. The current candidate mobile libraries have been rebuilt without TECkit.
