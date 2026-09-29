#!/usr/bin/env python3
"""Evaluate an MIT Czech pattern candidate without changing the selected bundle."""
import hashlib,json,shutil,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'.build/czech-alternative';out.mkdir(exist_ok=True)
candidate=root/'.build/license-sources/hyph-cs-sojka.tex'
expected='ed9da95124ba7127cc559ffefa432916dd882d392c3fba9633dcac9ba12b3018'
assert hashlib.sha256(candidate.read_bytes()).hexdigest()==expected
bundle=out/'bundle'
if not bundle.exists():shutil.copytree(root/'.build/review-bundle',bundle)
shutil.copy2(candidate,bundle/'hyph-cs.tex')
# Cache identity is separate from the retained control bundle.
records=[{'name':str(p.relative_to(bundle)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(bundle.rglob('*')) if p.is_file() and p.name not in ('SHA256SUM','manifest.json')]
fingerprint=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
manifest=json.loads((bundle/'manifest.json').read_text());manifest.update(files=records,bundle_sha256=fingerprint,payload_bytes=sum(r['bytes'] for r in records))
(bundle/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(bundle/'SHA256SUM').write_text(fingerprint+'\n')
words='československého nejpravděpodobnější nejneobhospodařovávatelnějšími počítačového programování automatického rozdělování hyphenace zpracování přesvědčivějšího odpovědnosti mezinárodního spolupráce nejvýznamnější skutečnostmi prostřednictvím bezprostředního současnosti jednotlivými přirozeného organizace přístupnosti charakteristického technologického knihovnictví zemědělského pravděpodobnosti uživatelského prostředí'.split()
rows=[]
for width in (55,70,90,120):
 source=out/f'width-{width}.tex'
 source.write_text('\\documentclass{article}\\begin{document}\\makeatletter\\language=\\l@czech\\makeatother\n'+f'\\hsize={width}pt\\emergencystretch=10pt\n'+' '.join(words*3)+'\n\\end{document}\n')
 hashes=[]
 for label,path in [('baseline',root/'.build/review-bundle'),('alternative',bundle)]:
  pdf=out/f'{width}-{label}.pdf'
  result=subprocess.run([str(root/'.build/xetex-native-target/release/compile-pdf'),str(path),str(root/'.build/krilla-fonts'),str(source),str(pdf)],capture_output=True,text=True)
  assert result.returncode==0,(width,label,result.stdout,result.stderr)
  hashes.append(hashlib.sha256(pdf.read_bytes()).hexdigest())
 rows.append({'column_width_pt':width,'baseline_sha256':hashes[0],'candidate_sha256':hashes[1],'bytes_match':hashes[0]==hashes[1]})
 print(rows[-1],flush=True)
(out/'result.json').write_text(json.dumps({'candidate_sha256':expected,'license_declaration':'MIT','source':'https://github.com/typst/hypher/blob/d81cc506416bffef2a75ee2dc969d4b41bc36613/patterns/hyph-cs-sojka.tex','scope':f'{len(words)} words repeated in four column widths; not a complete language corpus','cases':rows},indent=2)+'\n')
