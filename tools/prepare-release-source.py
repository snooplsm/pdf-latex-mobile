#!/usr/bin/env python3
"""Collect production sources and pinned license evidence; never includes credentials."""
import gzip,hashlib,json,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/release-source';OUT.mkdir(parents=True,exist_ok=True)
files={}
# Only repository-visible files, not ignored build trees or local credentials.
paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
for name in paths:
    p=ROOT/name
    if not name or not p.is_file() or p.is_symlink():continue
    files['project/'+name]=p
for p in (ROOT/'.build/release-notices').rglob('*'):
    if p.is_file():files['notices/'+str(p.relative_to(ROOT/'.build/release-notices'))]=p
for p in (ROOT/'.build/license-sources/latex-2021-11-15-PL1').glob('*-ctan.zip'):
    files['upstream/'+p.name]=p
for name in ['lm.zip','amsfonts.zip','ibycus-babel.zip','hyph-utf8.zip','hyphen-base.tar.xz']:
    files['upstream/'+name]=ROOT/'.build/license-sources'/name
for profile in ['tiny','small','balanced','full']:
    for p in (ROOT/'dist/bundles'/profile/'texbundle').rglob('*'):
        if p.is_file():files[f'bundles/{profile}/'+str(p.relative_to(ROOT/'dist/bundles'/profile/'texbundle'))]=p
manifest={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in sorted(files.items())}
(OUT/'SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')
files['SHA256.json']=OUT/'SHA256.json'
archive=OUT/'latex-mobile-0.1.0-alpha.2-sources.tar.gz'
with archive.open('wb') as raw, gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0) as gz, tarfile.open(fileobj=gz,mode='w|') as tar:
    for name,p in sorted(files.items()):
        info=tarfile.TarInfo(name);info.size=p.stat().st_size;info.mode=0o644;info.mtime=0
        with p.open('rb') as source:tar.addfile(info,source)
with tarfile.open(archive) as tar:
    for name,digest in manifest.items():
        assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==digest,name
print(json.dumps({'archive':str(archive),'files':len(files),'mb':round(archive.stat().st_size/1e6,2),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},indent=2))
