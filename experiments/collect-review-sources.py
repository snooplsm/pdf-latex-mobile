#!/usr/bin/env python3
"""Reproducible review archive for remaining source-distribution obligations.

This is not a complete release source distribution or legal-clearance gate.
"""
import gzip,hashlib,io,json,tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
files={}
engine=root/'.build/xetex-native-vendor/engine'
for p in engine.rglob('*'):
 if p.is_file() and not any(x in ('.git','target') for x in p.relative_to(engine).parts):
  files['tectonic_engine_xetex-0.5.3/'+str(p.relative_to(engine))]=p.read_bytes()
files['tectonic_engine_xetex-0.5.3/TECTONIC-LICENSE']= (root/'.build/xetex-native-vendor/tectonic/LICENSE').read_bytes()
# TECkit calls into these bridge crates; retain the actual pinned integration
# sources rather than distributing only the seven embedded TECkit files.
for name,version in [('tectonic_bridge_core','0.5.3'),('tectonic_bridge_flate','0.1.10')]:
 source=next((Path.home()/'.cargo/registry/src').glob('*/'+name+'-'+version))
 for p in source.rglob('*'):
  if p.is_file():files[name+'-'+version+'/'+str(p.relative_to(source))]=p.read_bytes()
 files[name+'-'+version+'/TECTONIC-LICENSE']=(root/'.build/xetex-native-vendor/tectonic/LICENSE').read_bytes()
for name in ('prepare.py','prepare-layout.py','picture_helpers.c','picture_metadata.rs','Cargo.toml','Cargo.lock','build.py'):
 files['experiment/xetex-native/'+name]=(root/'experiments/xetex-native'/name).read_bytes()
files['experiment/vendor-PROVENANCE.json']=(root/'.build/xetex-native-vendor/PROVENANCE.json').read_bytes()
files['experiment/review-teckit.py']=(root/'experiments/review-teckit.py').read_bytes()
option=next((Path.home()/'.cargo/registry/src').glob('*/option-ext-0.2.0'))
for p in option.rglob('*'):
 if p.is_file():files['option-ext-0.2.0/'+str(p.relative_to(option))]=p.read_bytes()
for p in (root/'experiments/licenses').rglob('*'):
 if p.is_file():files['notices/'+str(p.relative_to(root/'experiments/licenses'))]=p.read_bytes()
latex_record=json.loads((root/'experiments/licenses/latex-base-provenance.json').read_text())
latex_source=next(r for r in latex_record['archives'] if r['name']=='latex-base-ctan.zip')
p=root/'.build/license-sources/latex-2021-11-15-PL1'/latex_source['name']
assert hashlib.sha256(p.read_bytes()).hexdigest()==latex_source['sha256']
files['latex-base-2021-11-15-PL1/upstream-ctan.zip']=p.read_bytes()
kernel=root/'dist/bundles/full/texbundle/latex.ltx'
expected_kernel=next(r['bundled_sha256'] for r in latex_record['files'] if r['file']=='latex.ltx')
assert hashlib.sha256(kernel.read_bytes()).hexdigest()==expected_kernel
files['latex-base-2021-11-15-PL1/bundled-latex.ltx']=kernel.read_bytes()
package_record=json.loads((root/'experiments/licenses/latex-package-provenance.json').read_text())
for package in package_record['packages']:
 archive=next(a for a in package['archives'] if a['name'].endswith('-ctan.zip'))
 p=root/'.build/license-sources/latex-2021-11-15-PL1'/archive['name']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==archive['sha256']
 files['latex-packages-2021-11-15-PL1/'+archive['name']]=p.read_bytes()
files['README.txt']=b'''Experimental source review collection; not a complete release distribution.
The XeTeX crate contains MIT material and separately licensed TECkit files.
TECkit is offered under CPL-0.5-or-later OR LGPL-2.1-or-later; see notices.
The retained TECkit files include Tectonic's upstream changes. Our experiment
changes the XeTeX image adapter and build dependencies; see experiment/.
The seven TECkit files are unchanged from tectonic_engine_xetex 0.5.3.
Pinned core/flate bridge sources and experiment preparation inputs are included.
This remains incomplete as a full reproducible build/source distribution.
option-ext 0.2.0 is retained unchanged under MPL-2.0, including its license.
Matching LaTeX base upstream archive and the exact modified kernel are included.
The kernel patch and provenance are recorded under notices/latex-base-*.
A final source offer, license choice, notices and full build inputs still need
to be assembled with the release. Do not treat this archive as certification.
'''
manifest={name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())}
files['SHA256.json']=(json.dumps(manifest,indent=2)+'\n').encode()
stream=io.BytesIO()
with tarfile.open(fileobj=stream,mode='w',format=tarfile.PAX_FORMAT) as tar:
 for name,data in sorted(files.items()):
  entry=tarfile.TarInfo(name);entry.size=len(data);entry.mode=0o644;entry.mtime=0
  tar.addfile(entry,io.BytesIO(data))
out=root/'.build/replacement-license-audit/review-sources.tar.gz';out.parent.mkdir(exist_ok=True)
with out.open('wb') as dest:
 with gzip.GzipFile(fileobj=dest,mode='wb',filename='',mtime=0) as gz:gz.write(stream.getvalue())
with tarfile.open(out) as tar:
 for name,digest in manifest.items():
  assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==digest,name
print(json.dumps({'files':len(files),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'mb':round(out.stat().st_size/1e6,2),'path':str(out)}))
