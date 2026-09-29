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
        native_hashes = {}
        for entry in native:
            abi = entry.filename.split("/")[1]
            abi_bytes[abi] = abi_bytes.get(abi, 0) + entry.file_size
            native_hashes[entry.filename] = hashlib.sha256(aar.read(entry)).hexdigest()
        return {
            "artifact": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "aar_bytes": path.stat().st_size,
            "uncompressed_bytes": sum(f.file_size for f in entries),
            "native_bytes_by_abi": abi_bytes,
            "native_sha256": native_hashes,
            "tex_asset_bytes": sum(f.file_size for f in entries if f.filename.startswith("assets/texbundle/")),
            "features": manifest["features"],
            "native_profile": "full" if "-full-" in path.name else "compact",
            "bundle_sha256": manifest["bundle_sha256"],
        }


def write_report(artifacts, markdown, json_path, split_root=Path("dist/aar-splits"), ios_report=Path("dist/ios-sizes.json")):
    if not artifacts:
        raise ValueError("no AAR artifacts found; build them before measuring")
    order = {name: i for i, name in enumerate(("tiny", "small", "balanced", "full"))}
    records = [measure(p) for p in sorted(artifacts, key=lambda p: next((i for name, i in order.items() if f"-{name}-" in p.name), 99))]
    abis = sorted({abi for r in records for abi in r["native_bytes_by_abi"]})
    split_records = {}
    for r in records:
        split_records[r["artifact"]] = {}
        for abi in abis:
            path = split_root / abi / r["artifact"]
            if path.is_file():
                split = measure(path)
                if set(split["native_bytes_by_abi"]) != {abi} or split["bundle_sha256"] != r["bundle_sha256"]:
                    raise ValueError(f"{path}: split ABI or TeX bundle does not match universal AAR")
                if any(r["native_sha256"].get(name) != digest for name, digest in split["native_sha256"].items()):
                    raise ValueError(f"{path}: native libraries do not match universal AAR")
                split_records[r["artifact"]][abi] = split
    lines = ["# Library sizes", "", "XeTeX + Krilla, without TECkit. Measurements include packaged dependency notices.", "", "## Android", "",
             "Measured compressed AAR downloads, in MB (decimal). Included CPU builds: " + ", ".join(abis) + ".", "",
             "| Variant | All CPUs | ARMv7 | ARM64 | x86-64 |", "|---|---:|---:|---:|---:|"]
    for r in records:
        variant = next((name for name in order if f"-{name}-" in r["artifact"]), r["artifact"])
        cells = [f'{split_records[r["artifact"]][abi]["aar_bytes"] / 1_000_000:.2f}' if abi in split_records[r["artifact"]] else "—" for abi in ("armeabi-v7a", "arm64-v8a", "x86_64")]
        lines.append(f'| {variant} | {r["aar_bytes"] / 1_000_000:.2f} | {" | ".join(cells)} |')
    lines += ["",
              "CPU columns are measured single-architecture AAR builds, including the shared TeX assets and wrapper code. They are not APK split sizes or measured app download increases. A dash means that build has not been measured.", "",
              "Maven artifacts include all CPUs. Single-CPU builds are generated only for this comparison with `python3 tools/split-sizes.py`; the TeX assets are included once in each build.", "",
              "With Android App Bundle delivery or ABI splits, each device receives only its CPU build. The universal AAR download above is not the per-device app size. Android also copies the TeX assets to app storage on first use.", "",
              "Choose one feature variant. `full` covers the included examples, not all of TeX Live. Tiny, small, and balanced use compact ICU data; full also includes ICU encoding tables and line-break data.", ""]
    if ios_report.is_file():
        ios = json.loads(ios_report.read_text())
        baseline = ios["records"][0]
        lines += ["## iOS", "", "Measured growth over the same app without LaTeX, in MB. ARM64 device Release builds; simulator code excluded.", "",
                  "| Variant | Compressed app increase (MB) | Uncompressed app increase (MB) |", "|---|---:|---:|"]
        for r in ios["records"][1:]:
            lines.append(f'| {r["profile"]} | {r["zip_increase_bytes"] / 1_000_000:.2f} | {r["app_increase_bytes"] / 1_000_000:.2f} |')
        lines += ["", f'Baseline: {baseline["zip_bytes"] / 1_000_000:.2f} MB compressed, {baseline["app_bytes"] / 1_000_000:.2f} MB uncompressed.', "",
                  "Local unsigned builds with dead-code stripping. Compressed values use ZIP compression; uncompressed values sum app file sizes. These are measured build comparisons, not App Store download sizes or filesystem allocation. Signing, Apple processing, and app contents can change delivery sizes. See [Apple’s app-size measurement guidance](https://developer.apple.com/documentation/Xcode/reducing-your-app-s-size).", "",
                  "Reproduce with `python3 tools/ios-sizes.py` (Xcode and XcodeGen required). The probe links and calls the compiler; the baseline uses the same UI without the library. Results include each profile’s TeX assets.", ""]
    markdown.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text("\n".join(lines))
    json_path.write_text(json.dumps({"schema": 2, "artifacts": records, "single_abi_artifacts": split_records}, indent=2) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", nargs="*", type=Path)
    parser.add_argument("--markdown", type=Path, default=Path("SIZES.md"))
    parser.add_argument("--json", type=Path, default=Path("dist/sizes.json"))
    args = parser.parse_args()
    write_report(args.artifacts or list(Path("dist/aar").glob("*.aar")), args.markdown, args.json)
