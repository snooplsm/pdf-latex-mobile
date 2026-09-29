#!/usr/bin/env python3
"""Check JPEG sizing/XDV and PDF output against the original engine."""
import hashlib,json,subprocess
from pathlib import Path
from PIL import Image,ImageChops
from pypdf import PdfReader
root=Path(__file__).resolve().parents[2];out=root/'.build/jpeg-check';out.mkdir(exist_ok=True)
results=[]
for name,dpi,progressive in [('default',None,False),('dpi72',(72,72),False),('dpi300',(300,300),False),('asymmetric',(144,72),False),('progressive',(96,96),True)]:
 assets=out/(name+'.assets');assets.mkdir(exist_ok=True)
 image=Image.new('RGB',(96,48));image.putdata([(x*255//95,y*255//47,128) for y in range(48) for x in range(96)])
 options={'quality':90,'progressive':progressive}
 if dpi:options['dpi']=dpi
 image.save(assets/'picture.jpg',**options)
 source=out/(name+'.tex');source.write_text(r'\documentclass{article}\usepackage{graphicx}\begin{document}JPEG test\par\includegraphics{picture.jpg}\end{document}')
 paths=[]
 for label,binary in [('baseline',root/'target/release/examples/xdv-probe'),('replacement',root/'.build/xetex-native-target/release/xetex-native-probe')]:
  xdv=out/(name+'-'+label+'.xdv');subprocess.run([str(binary),str(root/'dist/bundles/full/texbundle'),str(source),str(xdv)],check=True,capture_output=True)
  paths.append(xdv)
 assert paths[0].read_bytes()==paths[1].read_bytes(),(name,'XDV differs')
 baseline=out/(name+'-baseline.pdf')
 request={'source':source.read_text(),'bundle_path':str(root/'dist/bundles/full/texbundle'),'output_path':str(baseline),'asset_files':{'picture.jpg':str(assets/'picture.jpg')}}
 subprocess.run([str(root/'target/release/lm-compile')],input=json.dumps(request),text=True,check=True,capture_output=True)
 pdf=out/(name+'-replacement.pdf');hashes=[]
 for _ in range(2):
  subprocess.run([str(root/'.build/krilla-xdv-target/release/krilla-xdv-probe'),str(paths[1]),str(root/'.build/krilla-fonts'),str(pdf),str(assets)],check=True)
  hashes.append(hashlib.sha256(pdf.read_bytes()).hexdigest())
 assert hashes[0]==hashes[1]
 a,b=PdfReader(baseline),PdfReader(pdf)
 assert len(a.pages)==len(b.pages)==1
 assert a.pages[0].extract_text()==b.pages[0].extract_text()
 assert list(a.pages[0].mediabox)==list(b.pages[0].mediabox)
 images=[]
 for path in (baseline,pdf):
  subprocess.run(['pdftoppm','-r','144','-singlefile','-png',str(path),str(path.with_suffix(''))],check=True,capture_output=True)
  with Image.open(path.with_suffix('.png')) as im:images.append(im.convert('RGB'))
 difference=ImageChops.difference(*images)
 pixels=sum(v!=(0,0,0) for v in difference.get_flattened_data())
 results.append({'case':name,'xdv_matches':True,'repeat_hash_matches':True,'pdf_sha256':hashes[0],'different_pixels_144dpi':pixels})
 print(results[-1],flush=True)
(out/'result.json').write_text(json.dumps(results,indent=2)+'\n')
assert all(r['different_pixels_144dpi']==0 for r in results),'Raster difference; see report'
