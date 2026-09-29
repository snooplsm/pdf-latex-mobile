#!/usr/bin/env python3
"""Measure release AAR files, never substitute an estimate for a missing artifact."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def measure(path):
    with zipfile.ZipFile(path) as aar:
        entries = aar.infolist()
        native = [f for f in entries if f.filename.startswith("jni/") and f.filename.endswith(".so")]
        if not native:
            raise ValueError(f"{path}: no native libraries")
        manifest = json.loads(aar.read("assets/texbundle/manifest.json"))
        abi_bytes = {}
        for entry in native:
            abi = entry.filename.split("/")[1]
            abi_bytes[abi] = abi_bytes.get(abi, 0) + entry.file_size
        return {
            "artifact": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "aar_bytes": path.stat().st_size,
            "uncompressed_bytes": sum(f.file_size for f in entries),
            "native_bytes_by_abi": abi_bytes,
            "tex_asset_bytes": sum(f.file_size for f in entries if f.filename.startswith("assets/texbundle/")),
            "features": manifest["features"],
            "native_profile": "full" if "-full-" in path.name else "compact",
            "bundle_sha256": manifest["bundle_sha256"],
        }


def write_report(artifacts, markdown, json_path):
    if not artifacts:
        raise ValueError("no AAR artifacts found; build them before measuring")
    order = {name: i for i, name in enumerate(("tiny", "small", "balanced", "full"))}
    records = [measure(p) for p in sorted(artifacts, key=lambda p: next((i for name, i in order.items() if f"-{name}-" in p.name), 99))]
    abis = sorted({abi for r in records for abi in r["native_bytes_by_abi"]})
    lines = ["# AAR sizes", "",
             "Measured compressed AAR downloads, in MB (decimal). Included CPU builds: " + ", ".join(abis) + ".", "",
             "| Variant | Download (MB) | Features |", "|---|---:|---|"]
    for r in records:
        variant = next((name for name in order if f"-{name}-" in r["artifact"]), r["artifact"])
        lines.append(f'| {variant} | {r["aar_bytes"] / 1_000_000:.2f} | {", ".join(r["features"])} |')
    lines += ["",
              "The default universal AARs contain three native builds. Earlier measurements contained only ARM64, so they were smaller. The TeX assets are shared once per AAR.", "",
              "With Android App Bundle delivery or ABI splits, each device receives only its CPU build. The universal AAR download above is not the per-device app size. Android also copies the TeX assets to app storage on first use.", "",
              "Choose one feature variant. `full` covers the included examples, not all of TeX Live. Tiny, small, and balanced use compact ICU data; full also includes ICU encoding tables and line-break data.", ""]
    markdown.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text("\n".join(lines))
    json_path.write_text(json.dumps({"schema": 1, "artifacts": records}, indent=2) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", nargs="*", type=Path)
    parser.add_argument("--markdown", type=Path, default=Path("SIZES.md"))
    parser.add_argument("--json", type=Path, default=Path("dist/sizes.json"))
    args = parser.parse_args()
    write_report(args.artifacts or list(Path("dist/aar").glob("*.aar")), args.markdown, args.json)
