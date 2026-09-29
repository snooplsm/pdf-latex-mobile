#!/usr/bin/env python3
"""Verify pinned source archives and exact runtime matches for LaTeX packages."""
from pathlib import Path
import hashlib,json,urllib.request,zipfile
root=Path(__file__).resolve().parents[1]
record=json.loads((root/'experiments/licenses/latex-package-provenance.json').read_text())
folder=root/'.build/license-sources/latex-2021-11-15-PL1';folder.mkdir(parents=True,exist_ok=True)
count=0
for package in record['packages']:
 for archive in package['archives']:
  path=folder/archive['name']
  if not path.exists():path.write_bytes(urllib.request.urlopen(archive['url'],timeout=120).read())
  assert hashlib.sha256(path.read_bytes()).hexdigest()==archive['sha256'],path.name
 with zipfile.ZipFile(folder/('latex-'+package['name']+'.tds.zip')) as z:
  for row in package['exact_files']:
   actual=(root/'dist/bundles/full/texbundle'/row['file']).read_bytes()
   assert actual==z.read(row['upstream_path']) and hashlib.sha256(actual).hexdigest()==row['sha256'],row['file']
   count+=1
 with zipfile.ZipFile(folder/('latex-'+package['name']+'-ctan.zip')) as z:
  assert any(n.endswith('.dtx') for n in z.namelist()),'Source files missing'
print(json.dumps({'verified_packages':len(record['packages']),'exact_runtime_files':count}))
