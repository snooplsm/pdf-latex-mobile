#!/usr/bin/env python3
"""python3 tools/invoice.py --bundle dist/bundles/balanced/texbundle"""
import argparse
import json
from pathlib import Path
from pack import ROOT, run, example_assets
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--bundle", type=Path, default=ROOT / "dist/bundles/balanced/texbundle")
parser.add_argument("--output", type=Path, default=ROOT / "output/pdf/northstar-invoice.pdf")
args = parser.parse_args()
args.output.parent.mkdir(parents=True, exist_ok=True)
fixture = ROOT / "examples/invoice.tex"
result = run(ROOT / "target/release/lm-compile", fixture.read_text(), args.bundle.resolve(), args.output.resolve(), example_assets(fixture))
print(json.dumps({"pdf": str(args.output), "bytes": result["pdf_bytes"], "elapsed_ms": result["elapsed_ms"]}, indent=2))
