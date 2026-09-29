# rtex probe

Tested revision `32ac01c0b754e10111f24f81c7932cf5ccd0a247` from https://github.com/yingkitw/rtex (declares Apache-2.0). Source is staged in `.build/candidates/rtex` with an empty `[workspace]` appended for isolated building. This is not a completed transitive license audit.

```sh
CARGO_TARGET_DIR="$PWD/.build/rtex-target" \
CARGO_PROFILE_RELEASE_LTO=true CARGO_PROFILE_RELEASE_CODEGEN_UNITS=1 \
CARGO_PROFILE_RELEASE_OPT_LEVEL=s CARGO_PROFILE_RELEASE_STRIP=debuginfo \
cargo build --release --manifest-path .build/candidates/rtex/Cargo.toml --bin rtex
python3 experiments/rtex-probe/run.py
```

Results are in `.build/rtex-probe-results`:

- Eight non-invoice inputs emitted PDFs, but this does not establish parity.
- The unchanged invoice failed to load `logo.pdf`.
- Changing only the asset reference to our existing `logo.png` also failed: PNG embedding rejects four color components.
- The diagrams input returned success, but rendering showed a blank page with a page number instead of the two nodes and arrow.

Rejected as a drop-in replacement on these observed failures. Upstream also documents unsupported TikZ and full TeX package execution. Other emitted PDFs have not been accepted on visual or semantic grounds.
