#!/usr/bin/env python3
"""Run unchanged feature inputs against an already-built rtex CLI.

Exit zero from rtex only means it emitted something, not rendering parity.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
binary = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / '.build/rtex-target/release/rtex'
out = root / '.build/rtex-probe-results'
out.mkdir(parents=True, exist_ok=True)
features = json.loads((root / 'profiles/features.json').read_text())['features']
results = []
for feature, sources in features.items():
    for source in sources:
        src = root / source
        case = out / src.stem
        case.mkdir(exist_ok=True)
        shutil.copy2(src, case / src.name)
        assets = src.with_suffix('.assets')
        if assets.is_dir():
            shutil.copytree(assets, case, dirs_exist_ok=True)
        pdf = case / 'output.pdf'
        try:
            run = subprocess.run([str(binary), src.name, '-o', str(pdf), '--no-incremental'], cwd=case, capture_output=True, text=True, timeout=60)
            (case / 'compile.log').write_text(run.stdout + run.stderr)
            result = {'feature': feature, 'input_sha256': hashlib.sha256(src.read_bytes()).hexdigest(), 'exit_code': run.returncode, 'emitted_pdf': pdf.exists(), 'parity': 'unverified'}
        except subprocess.TimeoutExpired:
            result = {'feature': feature, 'timeout': True, 'parity': 'failed'}
        results.append(result)
(out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
