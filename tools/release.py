#!/usr/bin/env python3
"""python3 tools/release.py --source .build/tex --version 0.1.0"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from pack import ROOT, pack, select
from sizes import write_report

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--version", default="0.1.0")
parser.add_argument("--abis", default="arm64-v8a")
parser.add_argument("--notices", type=Path)
args = parser.parse_args()
config = json.loads((ROOT / "profiles/features.json").read_text())
for preset in config["presets"]:
    generated = ROOT / f"dist/bundles/{preset}/texbundle"
    if generated.exists():
        shutil.rmtree(generated)
    pack(args.source, ROOT / f"dist/bundles/{preset}/texbundle", config,
         select(config, preset), ROOT / "target/release/lm-compile", notices=args.notices)
subprocess.run([str(ROOT / "android/gradlew"), "-p", str(ROOT / "android"),
                ":library:publishAllPublicationsToStagingRepository",
                f"-PreleaseVersion={args.version}", f"-Pabis={args.abis}"], check=True)
artifacts = []
for preset in config["presets"]:
    artifact = ROOT / f"dist/aar/latex-mobile-{preset}-{args.version}.aar"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / f"android/library/build/outputs/aar/library-{preset}-release.aar", artifact)
    artifacts.append(artifact)
write_report(artifacts, ROOT / "SIZES.md", ROOT / "dist/sizes.json")
print((ROOT / "SIZES.md").read_text())
