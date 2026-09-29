# Existing-engine XDV inventory

Diagnostic only: this still links the current Tectonic build and is not a license-cleared replacement.

```sh
PATH="$PWD/.build/host/bin:$PATH" VCPKG_ROOT="$PWD/.build/vcpkg" \
TECTONIC_DEP_BACKEND=vcpkg VCPKGRS_TRIPLET=arm64-osx \
cargo build --locked --release -p latex-mobile --example xdv-probe
mkdir -p .build/xdv-probe
target/release/examples/xdv-probe dist/bundles/full/texbundle \
  examples/invoice.tex .build/xdv-probe/invoice.xdv
python3 experiments/xdv-probe/inspect.py .build/xdv-probe/invoice.xdv
```

All nine existing feature sources successfully generated one-page XDV outputs locally. Inventory in `.build/xdv-probe/inventory.json`.

The unchanged invoice uses four native OpenType font names, 13 distinct specials including color stacks, transforms, page dimensions, and embedded PDF images. The math example uses seven font names and includes traditional TeX font definitions. TikZ emits 35 distinct specials. A new backend must implement their semantics, including font metrics/encodings and graphics state; skipping unknown instructions would silently corrupt output.

The existing `tectonic_xdv` decoder currently discards traditional font definitions and does not provide positions for traditional character runs. It can handle the positioned native glyphs in most examples, but is not sufficient as-is for the traditional fonts in the math example. Our inventory decoder deliberately reports opcodes and rejects unknown ones; it does not pretend to render them.

Removing `engine_xdvipdfmx` alone also leaves `tectonic_pdf_io` in XeTeX: `xetex-pic.c` uses it for image/PDF information and `xetex-ini.c` calls its lifecycle functions. Those need an independently implemented replacement before a binary can be considered free of those GPL components.
