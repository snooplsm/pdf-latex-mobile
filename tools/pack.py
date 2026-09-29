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


DISABLED_HYPHENATION = {"czech": "cs", "indonesian": "id", "macedonian": "mk", "latvian": "lv", "armenian": "hy"}


def disable_restricted_hyphenation(bundle):
    """Keep language identifiers, but load no automatic patterns for these languages."""
    config = bundle / "language.dat"
    if not config.is_file():
        return
    lines = []
    for line in config.read_text().splitlines():
        fields = line.split()
        if fields and (fields[0] in DISABLED_HYPHENATION or
                       (len(fields) > 1 and fields[1] in ("dumyhyph.tex", "zerohyph.tex"))):
            line = fields[0] + " lm-nohyphen.tex"
        lines.append(line)
    config.write_text("\n".join(lines) + "\n")
    (bundle / "lm-nohyphen.tex").write_text(
        "% Copyright 2026 LaTeX Mobile contributors. SPDX-License-Identifier: MIT\n"
        "% Automatic hyphenation intentionally disabled; explicit hints remain available.\n"
        "\\endinput\n")
    for name in ("dumyhyph.tex", "zerohyph.tex"):
        (bundle / name).unlink(missing_ok=True)
    for code in DISABLED_HYPHENATION.values():
        for pattern in (f"hyph-{code}.*", f"loadhyph-{code}.*"):
            for path in bundle.glob(pattern):
                path.unlink()


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
        disable_restricted_hyphenation(prepared)
        if "languages" not in selected:
            (prepared / "language.dat").write_text("english hyphen.tex\n=usenglish\n=USenglish\n=american\n")
        used = set()
        by_example = {}
        for fixture in fixtures:
            response = run(compiler, fixture.read_text(), prepared, scratch / "probe.pdf", example_assets(fixture))
            used.update(response["files"])
            by_example[str(fixture.relative_to(ROOT)) if fixture.is_relative_to(ROOT) else fixture.name] = response["files"]
        # Converted fonts retain their own license and source/conversion notice.
        encodings = [name for name in used if name.endswith(".encoding.json")]
        if encodings:
            used.add("AMSFonts-OFL.txt")
            for name in encodings:
                used.add(name.removesuffix(".encoding.json") + ".provenance.json")
        if "latex.ltx" in used:
            kernel = prepared / "latex.ltx"
            header = b"% LaTeX Mobile modified distribution: see LATEX-MODIFICATIONS.txt.\n"
            data = kernel.read_bytes()
            original = data.removeprefix(header).replace(b"LaTeX Mobile modified \\fmtname", b"\\fmtname")
            if hashlib.sha256(original).hexdigest() != "70ba1d0d113a986e4966e5a7ebb5afa3fbb17843ec4395bd0187d2aa266b5646":
                raise ValueError("latex.ltx changed: update its modification notice and source review")
            kernel.write_bytes(header + original.replace(b"{\\fmtname", b"{LaTeX Mobile modified \\fmtname"))
            shutil.copyfile(ROOT / "notices/LATEX-MODIFICATIONS.txt", prepared / "LATEX-MODIFICATIONS.txt")
            used.add("LATEX-MODIFICATIONS.txt")
        if "l3backend-xetex.def" in used:
            backend = prepared / "l3backend-xetex.def"
            header = b"% LaTeX Mobile modified distribution: see LATEX-MODIFICATIONS.txt.\n"
            original = backend.read_bytes().removeprefix(header).replace(
                b"LaTeX Mobile modified L3 backend support: XeTeX", b"L3 backend support: XeTeX")
            if hashlib.sha256(original).hexdigest() != "47e2f4fc8bda65ba3f5d295145da3f7bb783b71f2a07f11a4038e84b2fd5cd13":
                raise ValueError("l3backend-xetex.def changed: update its source review and modification notice")
            backend.write_bytes(header + original.replace(
                b"L3 backend support: XeTeX", b"LaTeX Mobile modified L3 backend support: XeTeX"))
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
            if notices:
                shutil.copytree(notices, stage / "licenses", symlinks=False)
                for file in sorted((stage / "licenses").rglob("*")):
                    if file.is_file():
                        data = file.read_bytes()
                        records.append({"name": str(file.relative_to(stage)), "bytes": len(data),
                                        "sha256": hashlib.sha256(data).hexdigest()})
            fingerprint = hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            (stage / "SHA256SUM").write_text(fingerprint + "\n")
            # Verify the exact trimmed bundle, with a fresh format cache for each document.
            for fixture in fixtures:
                run(compiler, fixture.read_text(), stage, scratch / "verify.pdf", example_assets(fixture))
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
