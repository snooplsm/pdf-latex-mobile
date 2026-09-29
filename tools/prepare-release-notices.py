#!/usr/bin/env python3
"""Assemble pinned notices and source evidence for a local release candidate."""
import hashlib,json,re,shutil,subprocess,zipfile
from urllib.request import urlopen
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.build/release-notices'
OUT.mkdir(parents=True,exist_ok=True)
index=json.loads((ROOT/'.build/notices-audit/INDEX.json').read_text())
entries=[]
def retain(source,label):
    data=source.read_bytes();digest=hashlib.sha256(data).hexdigest()
    dest=OUT/'texts'/f'{digest}.txt';dest.parent.mkdir(exist_ok=True);dest.write_bytes(data)
    entries.append({'component':label,'notice':str(dest.relative_to(OUT)),'sha256':digest})
for path in sorted((ROOT/'.build/notices-audit').rglob('*')):
    if path.is_file() and path.name not in ('INDEX.json','VENDORED-SOURCE-HEADERS.txt'):
        retain(path,str(path.relative_to(ROOT/'.build/notices-audit')))
# Some Tectonic crates distribute their MIT notice at the workspace root.
retain(ROOT/'vendor/tectonic/LICENSE','Tectonic workspace MIT notice')
retain(ROOT/'LICENSE','LaTeX Mobile MIT notice')
for name in ('AMSFonts-OFL.txt','UNICODE-LICENSE.txt','SLOVAK-MIT.txt','PROJECT-LICENSE-MIT.txt'):
    retain(ROOT/'experiments/licenses'/name,name)
for p in (ROOT/'notices').glob('*.txt'):retain(p,p.name)
for source in sorted((ROOT/'experiments/licenses').glob('*provenance.json')):
    if source.name != 'teckit-provenance.json':
        shutil.copyfile(source, OUT/source.name)
(OUT/'teckit-provenance.json').unlink(missing_ok=True)
# Pin the license text too; do not rely on a stale previous output directory.
mpl_url = 'https://www.mozilla.org/media/MPL/1.1/index.0c5913925d40.txt'
with urlopen(mpl_url, timeout=60) as response:
    mpl = response.read()
if hashlib.sha256(mpl).hexdigest() != 'f849fc26a7a99981611a3a370e83078deb617d12a45776d6c4cada4d338be469':
    raise ValueError('MPL 1.1 license text changed')
(OUT/'MPL-1.1.txt').write_bytes(mpl)
with zipfile.ZipFile(ROOT/'.build/license-sources/lm.zip') as z:
    for name in ['lm/doc/fonts/lm/GUST-FONT-LICENSE.TXT','lm/doc/fonts/lm/README-Latin-Modern.TXT']:
        dest=OUT/Path(name).name;dest.write_bytes(z.read(name))
    verified={}
    for p in (ROOT/'.build/review-bundle-config-licensed').glob('lm*.otf'):
        matches=[n for n in z.namelist() if n.endswith('/'+p.name)]
        assert len(matches)==1 and z.read(matches[0])==p.read_bytes(),p.name
        verified[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/'latin-modern-provenance.json').write_text(json.dumps({'source':'https://mirrors.ctan.org/fonts/lm.zip','archive_sha256':hashlib.sha256((ROOT/'.build/license-sources/lm.zip').read_bytes()).hexdigest(),'identical_fonts':verified},indent=2)+'\n')
# Distribute the exact, unmodified MPL Rust source with the notices themselves.
option=next((Path.home()/'.cargo/registry/src').glob('*/option-ext-0.2.0'))
shutil.copytree(option,OUT/'sources/option-ext-0.2.0',dirs_exist_ok=True)
with zipfile.ZipFile(ROOT/'.build/license-sources/latex-2021-11-15-PL1/latex-base-ctan.zip') as z:
    lppl=next(n for n in z.namelist() if n.endswith('/lppl.txt'))
    (OUT/'LPPL.txt').write_bytes(z.read(lppl))
(OUT/'INDEX.json').write_text(json.dumps({'scope':'Conservative dependency notice inventory; includes build/target dependencies not necessarily linked. Not a release clearance assertion.','cargo_lock_sha256':hashlib.sha256((ROOT/'Cargo.lock').read_bytes()).hexdigest(),'notices':entries,'dependency_licenses':index['rust_dependencies_including_build_and_target_dependencies']},indent=2)+'\n')
print(OUT)
