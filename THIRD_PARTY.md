Project code: MIT. Engine: [Tectonic](https://github.com/tectonic-typesetting/tectonic), with its upstream third-party components and notices. TeX packages and fonts retain their individual licenses; the project MIT license does not relicense them.

`Cargo.lock` pins Rust dependencies. `tools/bootstrap.sh` pins vcpkg. Before public binary distribution, collect the corresponding native, Rust, TeX, and font license/source notices and pass their directory via `tools/release.py --notices DIRECTORY`; it is copied into each artifact. Local staging is not a public release.
