#!/usr/bin/env python3
"""Build a target-specific ICU data archive containing only the selected runtime data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("triplet")
parser.add_argument("--profile", choices=["compact", "full"], required=True)
parser.add_argument("--target", required=True)
args = parser.parse_args()
vcpkg = Path(os.environ.get("VCPKG_ROOT", ROOT / ".build/vcpkg"))
host = "arm64-osx" if os.uname().machine == "arm64" else "x64-osx"
if os.uname().sysname == "Linux":
    host = "x64-linux"
tools = vcpkg / f"installed/{host}/tools/icu/bin"
sources = sorted((vcpkg / "buildtrees/icu/src").glob("*/source/data/in/icudt*l.dat"))
if len(sources) != 1:
    raise SystemExit("Expected one pinned ICU source data package")
source = sources[0]
symbol = source.stem[:-1]  # icudt78l -> icudt78
work = ROOT / f".build/icu/{args.triplet}/{args.profile}"
work.mkdir(parents=True, exist_ok=True)
items = subprocess.check_output([str(tools / "icupkg"), "-l", str(source)], text=True).splitlines()
if args.profile == "compact":
    # Built-in Unicode/ASCII/Latin-1 converters; no legacy encoding tables or ICU line breaking.
    keep = ["cnvalias.icu"]
else:
    # XeTeX uses conversion and break iteration, not calendars, collation, or locale formatting.
    keep = [name for name in items if name.startswith("brkitr/") or name.endswith(".cnv") or
            ("/" not in name and (name.endswith((".icu", ".nrm")) or name in ("root.res", "pool.res", "res_index.res")))]
listing = work / "keep.txt"
listing.write_text("\n".join(keep) + "\n")
subprocess.run([str(tools / "icupkg"), "-x", str(listing), "-d", str(work), str(source)], check=True)
data = work / source.name
subprocess.run([str(tools / "icupkg"), "-c", "-a", str(listing), "-s", str(work), "new", str(data)], check=True)
assembly = "gcc-darwin" if "apple" in args.target else "gcc"
subprocess.run([str(tools / "genccode"), "-a", assembly, "-e", symbol, "-d", str(work), str(data)], check=True)
obj = work / "icudata.o"
if "android" in args.target:
    ndk = Path(os.environ["ANDROID_NDK_HOME"])
    platform = "darwin-x86_64" if os.uname().sysname == "Darwin" else "linux-x86_64"
    binary = ndk / f"toolchains/llvm/prebuilt/{platform}/bin"
    compiler = [str(binary / f"{args.target}28-clang")]
    ar = str(binary / "llvm-ar")
else:
    sdk = "iphonesimulator" if args.target.endswith("-sim") else "iphoneos"
    target = "arm64-apple-ios15.0-simulator" if sdk == "iphonesimulator" else "arm64-apple-ios15.0"
    compiler = ["xcrun", "--sdk", sdk, "clang", "-target", target]
    ar = "ar"
subprocess.run(compiler + ["-c", str(work / (source.stem + "_dat.S")), "-o", str(obj)], check=True)
archive = work / "libicudata.a"
archive.unlink(missing_ok=True)
subprocess.run([ar, "rcs", str(archive), str(obj)], check=True)
installed = vcpkg / f"installed/{args.triplet}/lib/libicudata.a"
# Atomic replacement breaks vcpkg's hard link, preserving its original package/cache archive.
replacement = installed.with_suffix(".replacement")
replacement.write_bytes(archive.read_bytes())
replacement.replace(installed)
record = {"profile": args.profile, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
          "data_bytes": data.stat().st_size, "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "items": keep}
(work / "manifest.json").write_text(json.dumps(record, indent=2) + "\n")
print(f"ICU {args.profile}: {source.stat().st_size:,} -> {data.stat().st_size:,} data bytes")
