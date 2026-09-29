#!/usr/bin/env python3
"""Compare precise page origins against existing original-engine baselines."""
import hashlib,json,subprocess
from pathlib import Path
from PIL import Image,ImageChops
from pypdf import PdfReader
root=Path(__file__).resolve().parents[2]
out=root/'.build/page-geometry';out.mkdir(exist_ok=True)
backend=root/'.build/krilla-xdv-target/release/krilla-xdv-probe'
results=[]
for name in ('multipage','core','invoice'):
 pdf=out/(name+'.pdf')
 subprocess.run([str(backend),str(root/'.build/xdv-probe'/(name+'.xdv')),str(root/'.build/krilla-fonts'),str(pdf),str(root/'examples'/(name+'.assets'))],check=True)
 baseline=root/'.build/xdv-probe'/(name+'-baseline.pdf')
 a,b=PdfReader(baseline),PdfReader(pdf)
 assert [list(p.mediabox) for p in a.pages]==[list(p.mediabox) for p in b.pages]
 # The original uses a one-inch translated origin; the replacement flips Y.
 # Compare their actual drawing origins independently of rounded MediaBox values.
 for original,replacement in zip(a.pages,b.pages):
  old=next(args for args,op in original.get_contents().operations if op==b'cm')
  new=next(args for args,op in replacement.get_contents().operations if op==b'cm' and list(args[:4])==[1,0,0,-1])
  assert abs(float(old[5])+72.0-float(new[5]))<0.0001,(name,old,new)
 pages=[]
 for i in range(len(a.pages)):
  images=[]
  for label,path in [('baseline',baseline),('candidate',pdf)]:
   prefix=out/f'{name}-{label}-{i+1}'
   subprocess.run(['pdftoppm','-r','144','-f',str(i+1),'-l',str(i+1),'-singlefile','-png',str(path),str(prefix)],check=True,capture_output=True)
   with Image.open(str(prefix)+'.png') as im:images.append(im.convert('RGB'))
  assert images[0].size==images[1].size
  difference=ImageChops.difference(*images)
  pages.append({'page':i+1,'different_pixels':sum(v!=(0,0,0) for v in difference.get_flattened_data()),'bbox':difference.getbbox()})
 results.append({'case':name,'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'pages':pages,'exact_text':[p.extract_text() for p in a.pages]==[p.extract_text() for p in b.pages]})
report={'backend_sha256':hashlib.sha256(backend.read_bytes()).hexdigest(),'results':results}
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
