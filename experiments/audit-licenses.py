#!/usr/bin/env python3
"""Collect replacement-engine license evidence. Never labels a scan as clearance."""
import hashlib,json,re,shutil,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'.build/replacement-license-audit';out.mkdir(exist_ok=True)
records=[];forbidden=[]
projects={name:root/'experiments'/name/'Cargo.toml' for name in ('xetex-native','krilla-xdv')}
projects['mobile-bridge']=root/'.build/mobile-bridge/Cargo.toml'
for project,manifest in projects.items():
 meta=json.loads(subprocess.check_output(['cargo','metadata','--locked','--format-version','1','--manifest-path',str(manifest)],text=True))
 packages={p['id']:p for p in meta['packages']};nodes={n['id']:n for n in meta['resolve']['nodes']};seen=set()
 def visit(key):
  if key in seen:return
  seen.add(key)
  for dep in nodes[key]['deps']:
   if any(k['kind']!='dev' for k in dep['dep_kinds']):visit(dep['pkg'])
 visit(meta['resolve']['root'])
 for key in sorted(seen):
  p=packages[key];source=Path(p['manifest_path']).parent
  if p['name'] in ('tectonic_pdf_io','tectonic_engine_xdvipdfmx'):forbidden.append(p['name'])
  dest=out/project/(p['name']+'-'+p['version']);notices=[];headers=[]
  for f in source.rglob('*'):
   if not f.is_file():continue
   rel=f.relative_to(source)
   if any(part in ('target','.git') for part in rel.parts):continue
   if re.match(r'(?i)^(licen[cs]e|copying|copyright|notice)([._-]|$)',f.name):
    to=dest/rel;to.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,to)
    notices.append({'path':str(rel),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
   if f.suffix in ('.c','.cpp','.h','.hpp','.rs'):
    # Preserve potentially restrictive notices even when the Cargo field says MIT.
    lines=f.read_text(errors='replace').splitlines()[:180]
    hits=[{'line':i+1,'text':line.strip()} for i,line in enumerate(lines)
          if re.search(r'GNU (?:Lesser |Library )?General Public License|Common Public License|Mozilla Public License|SPDX-License-Identifier:.*(?:GPL|CPL|MPL)',line,re.I)]
    if hits:headers.append({'path':str(rel),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'matches':hits})
  records.append({'project':project,'name':p['name'],'version':p['version'],'declared_license':p['license'],'manifest_sha256':hashlib.sha256(Path(p['manifest_path']).read_bytes()).hexdigest(),'source':p['source'],'notices':notices,'source_header_review':headers})
native=[]
for triplet in ('arm-android','arm64-android','x64-android','arm64-ios-release','arm64-ios-simulator-release'):
 for f in (root/'.build/vcpkg/installed'/triplet/'share').glob('*/copyright'):
  dest=out/'native'/triplet/f.parent.name/'copyright';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
  native.append({'triplet':triplet,'package':f.parent.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
report={'status':'review-incomplete','scope':'Resolved normal/build Cargo dependency graph across targets; native notices include installed packages, not proof of linked code. Header matches require human/source review.','lockfiles':{project:hashlib.sha256(manifest.with_name('Cargo.lock').read_bytes()).hexdigest() for project,manifest in projects.items()},'forbidden_pdf_crates':sorted(set(forbidden)),'rust':records,'native_notice_inventory':native,'remaining':['TECkit exact source correspondence and chosen-license obligations','source review beyond automatic header scan','TeX/font package notices and distribution requirements','link-map verification of actual native dependencies','notices and source offer/source archive in final release artifacts']}
(out/'INDEX.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'dependency_records':len(records),'source_header_review_files':sum(len(r['source_header_review']) for r in records),'forbidden_pdf_crates':report['forbidden_pdf_crates'],'output':str(out/'INDEX.json')},indent=2))
if forbidden:raise SystemExit(1)
