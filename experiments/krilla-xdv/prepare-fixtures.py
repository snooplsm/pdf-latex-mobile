#!/usr/bin/env python3
"""Build reference XDV for extended backend fixtures using the original engine."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[2]
output=root/'.build/xdv-probe';output.mkdir(exist_ok=True)
for source in sorted((root/'experiments/krilla-xdv/fixtures').glob('*.tex')):
 subprocess.run([str(root/'target/release/examples/xdv-probe'),str(root/'dist/bundles/full/texbundle'),str(source),str(output/(source.stem+'.xdv'))],check=True,timeout=60)
