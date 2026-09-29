#!/usr/bin/env python3
"""python3 tools/pack.py --source .build/tex --preset balanced --exclude graphics --output dist/texbundle"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def select(config, preset, include=(), exclude=()):
    known = set(config["features"])
    unknown = (set(include) | set(exclude)) - known
    if unknown:
        raise ValueError(f"unknown features: {sorted(unknown)}")
    selected = (set(config["presets"][preset]) | set(include)) - set(exclude)
    if "core" not in selected:
        raise ValueError("core is the required base feature")
    return sorted(selected)


def safe_file(root, name):
    if not name or Path(name).name != name or name in (".", "..") or "\\" in name:
        raise ValueError(f"invalid bundle filename: {name!r}")
    path = root / name
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"not a regular bundle file: {path}")
    return path


def example_assets(fixture):
    folder = fixture.with_suffix(".assets")
    if not folder.is_dir():
        return {}
    return {file.name: base64.b64encode(safe_file(folder, file.name).read_bytes()).decode()
            for file in sorted(folder.iterdir())}


def run(compiler, source, bundle, output, assets=None):
    result = subprocess.run([str(compiler)], input=json.dumps({
        "source": source, "bundle_path": str(bundle), "output_path": str(output), "assets": assets or {}
    }), text=True, capture_output=True, timeout=180)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    response = json.loads(result.stdout)
    if not response["ok"] or not output.read_bytes().startswith(b"%PDF-"):
        raise RuntimeError(f"compile failed: {response}")
    return response


def pack(source, output, config, selected, compiler, extra_examples=(), notices=None):
    source, output, compiler = source.resolve(), output.resolve(), compiler.resolve()
    if output.exists():
        raise ValueError(f"output already exists: {output}; choose a new directory")
    fixtures = sorted({ROOT / p for name in selected for p in config["features"][name]} | set(extra_examples))
    with tempfile.TemporaryDirectory(prefix="lm-probe-") as scratch:
        scratch = Path(scratch)
        prepared = scratch / "source"
        shutil.copytree(source, prepared)
        if "languages" not in selected:
            (prepared / "language.dat").write_text("english hyphen.tex\n=usenglish\n=USenglish\n=american\n")
        used = set()
        by_example = {}
        for fixture in fixtures:
            response = run(compiler, fixture.read_text(), prepared, scratch / "probe.pdf", example_assets(fixture))
            used.update(response["files"])
            by_example[str(fixture.relative_to(ROOT)) if fixture.is_relative_to(ROOT) else fixture.name] = response["files"]
        used.discard("SHA256SUM")
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output.parent, prefix=".pack-") as stage:
            stage = Path(stage)
            # Retain map entries only for the Type 1 fonts actually opened.
            if "pdftex.map" in used:
                fonts = {name for name in used if name.endswith(".pfb")}
                lines = (prepared / "pdftex.map").read_text().splitlines()
                import re
                lines = [line for line in lines if any(
                    token.lstrip("<[") in fonts for token in re.findall(r"[^\s]+", line))]
                (prepared / "pdftex.map").write_text("\n".join(lines) + "\n")
            records = []
            for name in sorted(used):
                file = safe_file(prepared, name)
                data = file.read_bytes()
                shutil.copyfile(file, stage / name)
                records.append({"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
            fingerprint = hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            (stage / "SHA256SUM").write_text(fingerprint + "\n")
            # Verify the exact trimmed bundle, with a fresh format cache for each document.
            for fixture in fixtures:
                run(compiler, fixture.read_text(), stage, scratch / "verify.pdf", example_assets(fixture))
            if notices:
                shutil.copytree(notices, stage / "licenses", symlinks=False)
            manifest = {"schema": 1, "features": selected, "bundle_sha256": fingerprint,
                        "payload_bytes": sum(r["bytes"] for r in records), "files": records,
                        "examples": by_example}
            if (source / "SOURCE.json").is_file():
                manifest["source"] = json.loads((source / "SOURCE.json").read_text())
            (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            shutil.copytree(stage, output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preset", choices=["tiny", "small", "balanced", "full"], default="balanced")
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--example", action="append", type=Path, default=[])
    parser.add_argument("--notices", type=Path)
    parser.add_argument("--compiler", type=Path, default=ROOT / "target/release/lm-compile")
    args = parser.parse_args()
    config = json.loads((ROOT / "profiles/features.json").read_text())
    selected = select(config, args.preset, args.include, args.exclude)
    manifest = pack(args.source, args.output, config, selected, args.compiler,
                    [p.resolve() for p in args.example], args.notices)
    print(json.dumps({"features": selected, "files": len(manifest["files"]),
                      "payload_bytes": manifest["payload_bytes"], "output": str(args.output)}, indent=2))

if __name__ == "__main__":
    main()
