#!/usr/bin/env python3
"""Compose an experimental full bundle with verified overrides and available notices.

This does not complete the license audit or certify distribution readiness.
"""
import argparse,hashlib,json,re,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);args=parser.parse_args()
out=args.output.resolve()
if out.exists():raise SystemExit('Refusing to overwrite '+str(out))
source=root/'dist/bundles/full/texbundle';licenses=root/'experiments/licenses'
sha=lambda b:hashlib.sha256(b).hexdigest()
x=json.loads((licenses/'hyphenation-provenance.json').read_text())
x['overrides'].update(json.loads((licenses/'configuration-overrides.json').read_text())['overrides'])
for name,record in x['overrides'].items():
 old=(source/name).read_bytes();new=(licenses/'bundle-overrides'/name).read_bytes()
 assert sha(old)==record['replaces_sha256'] and sha(new)==record['sha256'],name
 tokens=lambda b:re.sub(r'%[^\n]*','',b.decode()).split()
 assert tokens(old)==tokens(new),name
unicode=json.loads((licenses/'unicode-provenance.json').read_text())
for name,digest in unicode['files'].items():assert sha((source/name).read_bytes())==digest,name
assert sha((licenses/'UNICODE-LICENSE.txt').read_bytes())==unicode['license_sha256']
shutil.copytree(source,out)
shutil.copytree(root/'.build/krilla-fonts',out,dirs_exist_ok=True)
for name in x['overrides']:shutil.copy2(licenses/'bundle-overrides'/name,out/name)
notices=out/'licenses/replacement';notices.mkdir(parents=True)
for name in ('UNICODE-LICENSE.txt','unicode-provenance.json','SLOVAK-MIT.txt','hyphenation-provenance.json','AMSFonts-OFL.txt','configuration-overrides.json','PROJECT-LICENSE-MIT.txt'):
 shutil.copy2(licenses/name,notices/name)
records=[{'name':str(p.relative_to(out)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(out.rglob('*')) if p.is_file() and p.name not in ('manifest.json','SHA256SUM')]
fingerprint=sha(json.dumps(records,sort_keys=True,separators=(',',':')).encode())
manifest=json.loads((out/'manifest.json').read_text());manifest.update(files=records,bundle_sha256=fingerprint,payload_bytes=sum(r['bytes'] for r in records))
manifest['experimental_license_review']='incomplete'
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(out/'SHA256SUM').write_text(fingerprint+'\n')
print(out)
