#!/usr/bin/env python3
"""Inventory pinned dependencies and collect notices for review; does not certify release compliance."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.build/notices-audit'
OUT.mkdir(parents=True, exist_ok=True)
metadata = json.loads(subprocess.check_output(['cargo', 'metadata', '--locked', '--format-version', '1'], cwd=ROOT))
packages = {p['id']: p for p in metadata['packages']}
nodes = {n['id']: n for n in metadata['resolve']['nodes']}
seen = set()
def visit(key):
    if key in seen:
        return
    seen.add(key)
    for dependency in nodes[key]['deps']:
        visit(dependency['pkg'])
visit(next(k for k, p in packages.items() if p['name'] == 'latex-mobile'))
records = []
for key in sorted(seen):
    package = packages[key]
    if package['name'] == 'latex-mobile':
        continue
    source = Path(package['manifest_path']).parent
    target = OUT / 'rust' / f'{package["name"]}-{package["version"]}'
    found = []
    for file in source.rglob('*'):
        if file.is_file() and re.match(r'(?i)^(licen[cs]e|copying|copyright|notice)([._-]|$)', file.name):
            destination = target / file.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, destination)
            found.append(str(file.relative_to(source)))
    # Cargo license fields do not describe all vendored C/C++ files; preserve their headers.
    headers = []
    if package['name'].startswith('tectonic'):
        for file in source.rglob('*'):
            if file.is_file() and file.suffix in ('.c', '.h', '.cpp', '.hpp'):
                text = file.read_text(errors='replace')[:10000]
                if re.search(r'(?i)copyright|license|public domain', text):
                    headers.append(f'FILE: {file.relative_to(source)}\n{text}\n')
        if headers:
            target.mkdir(parents=True, exist_ok=True)
            (target / 'VENDORED-SOURCE-HEADERS.txt').write_text('\n'.join(headers))
    records.append({'name': package['name'], 'version': package['version'], 'declared_license': package['license'],
                    'source': package['source'], 'repository': package['repository'], 'notice_files': found})
for triplet in ('arm-android', 'arm64-android', 'x64-android', 'arm64-ios-release'):
    for file in (ROOT / '.build/vcpkg/installed' / triplet / 'share').glob('*/copyright'):
        target = OUT / 'native' / triplet / file.parent.name / 'copyright'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, target)
report = {'audit_status': 'needs-review', 'cargo_lock_sha256': hashlib.sha256((ROOT / 'Cargo.lock').read_bytes()).hexdigest(),
          'rust_dependencies_including_build_and_target_dependencies': records,
          'blockers': ['GPL-2.0-or-later headers in tectonic_pdf_io and tectonic_engine_xdvipdfmx',
                       'TECkit CPL/LGPL terms and corresponding-source requirements need review',
                       'TeX/font package notices and source obligations not yet complete']}
(OUT / 'INDEX.json').write_text(json.dumps(report, indent=2) + '\n')
print(f'Collected {len(records)} Rust dependency records and native notices in {OUT}; release audit is incomplete.')
