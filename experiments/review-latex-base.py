#!/usr/bin/env python3
"""Match bundled LaTeX base files to the exact upstream release and retain changes."""
from pathlib import Path
import difflib,hashlib,json,urllib.request,zipfile
root=Path(__file__).resolve().parents[1]
folder=root/'.build/license-sources/latex-2021-11-15-PL1';folder.mkdir(parents=True,exist_ok=True)
release='release-2021-11-15-PL1'
expected={'latex-base-ctan.zip':'6cf4bd15187ae9c3d430e95376b8fc360eed85985e2bab00b5a85a9f109e0e61','latex-base.tds.zip':'b3c42666960317d5389fb40d197bec93ad5694a60e308d1b3ec267244cfcbc10'}
archives=[]
for name,digest in expected.items():
 path=folder/name;url='https://github.com/latex3/latex2e/releases/download/'+release+'/'+name
 if not path.exists():path.write_bytes(urllib.request.urlopen(url,timeout=120).read())
 assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,(name,'Archive checksum changed')
 archives.append({'name':name,'url':url,'sha256':digest})
records=[];modified=[]
with zipfile.ZipFile(folder/'latex-base.tds.zip') as z:
 for name in sorted(z.namelist()):
  p=root/'dist/bundles/full/texbundle'/Path(name).name
  if not name.startswith('tex/latex/base/') or not p.is_file():continue
  original=z.read(name);actual=p.read_bytes();equal=original==actual
  records.append({'file':p.name,'upstream_path':name,'upstream_sha256':hashlib.sha256(original).hexdigest(),'bundled_sha256':hashlib.sha256(actual).hexdigest(),'identical':equal})
  if not equal:
   modified.append(p.name)
   patch=''.join(difflib.unified_diff(original.decode().splitlines(True),actual.decode().splitlines(True),fromfile='upstream/'+p.name,tofile='bundled/'+p.name))
   (root/'experiments/licenses'/('latex-base-'+p.name+'.patch')).write_text(patch)
assert modified==['latex.ltx'],('Unexpected changes require review',modified)
assert any(r['file']=='fonttext.cfg' and r['identical'] for r in records)
with zipfile.ZipFile(folder/'latex-base-ctan.zip') as z:
 for name in ('manifest.txt','legal.txt','lppl.txt','fontdef.dtx','ltfiles.dtx'):assert 'latex-base/'+name in z.namelist(),name
result={'scope':'Matched LaTeX base distribution and bundled kernel patch; not full TeX bundle clearance','release':release,'commit':'6c71902738ec896e508cb580bb2b3152b7ad8bec','archives':archives,'files':records,'modified_kernel':{'file':'latex.ltx','patch':'latex-base-latex.ltx.patch','description':'Tectonic-labeled missing-file handler replaces interactive filename prompting with a fatal error','attribution_evidence':'Comment in bundled file identifies Tectonic; historical patch commit not yet identified'},'distribution_remaining':['Include versioned upstream source archive and exact modified kernel with release source distribution','Review modified-work identification, change notices and support attribution under LPPL','Review remaining TeX packages separately']}
out=root/'experiments/licenses/latex-base-provenance.json';out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'exact_files':sum(r['identical'] for r in records),'modified':modified,'report':str(out)}))
