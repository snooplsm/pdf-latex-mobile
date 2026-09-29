#!/usr/bin/env python3
"""python3 tools/prepare-ios.py balanced"""
from pathlib import Path
import shutil
import sys
root = Path(__file__).resolve().parents[1]
preset = sys.argv[1] if len(sys.argv) > 1 else "balanced"
if preset not in ("tiny", "small", "balanced", "full"):
    raise SystemExit("choose tiny, small, balanced, or full")
source = root / f"dist/bundles/{preset}/texbundle"
if not (source / "manifest.json").is_file():
    raise SystemExit("Build the selected bundle with tools/pack.py first")
destination = root / "ios/LaTeXMobile/Sources/LaTeXMobile/Resources/texbundle"
if destination.exists():
    shutil.rmtree(destination)
shutil.copytree(source, destination)

native_profile = "full" if preset == "full" else "compact"
native = root / f"dist/native/ios/{native_profile}/CLatexMobile.xcframework"
if not native.is_dir():
    raise SystemExit("Run tools/build-native.sh ios to create the native frameworks")
framework = root / "ios/LaTeXMobile/Artifacts/CLatexMobile.xcframework"
if framework.exists():
    shutil.rmtree(framework)
shutil.copytree(native, framework)
