#!/usr/bin/env python3
"""Compare LaTeX CMYK and nested color stacks against the original backend."""
import hashlib,json,subprocess
from pathlib import Path
from PIL import Image,ImageChops
from pypdf import PdfReader
root=Path(__file__).resolve().parents[2];out=root/'.build/color-check';out.mkdir(exist_ok=True)
(out/'result.json').unlink(missing_ok=True)
cases={
 'named':r'{\color{cyan}\rule{45pt}{20pt}}{\color{magenta}\rule{45pt}{20pt}}{\color{yellow}\rule{45pt}{20pt}}',
 'fractional':r'{\color[cmyk]{0.12345,0.23456,0.34567,0.45678}\rule{90pt}{30pt}}',
 'nested':r'{\color[cmyk]{0.2,0.3,0.4,0.1}\rule{30pt}{20pt}{\color[rgb]{0.5,0.2,0.7}\rule{30pt}{20pt}}\rule{30pt}{20pt}}\rule{30pt}{20pt}',
 'special-cmyk':r'\special{pdf:bcolor [0.12345 0.23456 0.34567 0.45678]}\rule{90pt}{30pt}\special{pdf:ecolor}',
 'special-rgb':r'\special{pdf:bcolor [0.12345 0.23456 0.34567]}\rule{90pt}{30pt}\special{pdf:ecolor}',
 'multipage':r'{\color[cmyk]{0.2,0.3,0.4,0.1}\rule{45pt}{20pt}\newpage\rule{45pt}{20pt}}\rule{45pt}{20pt}',
 'path-fill':r'\special{pdf:bcontent}\special{pdf:code q 0.12345 0.23456 0.34567 0.45678 k 0 0 90 30 re f Q}\special{pdf:econtent}\hbox{}',
 'path-stroke':r'\special{pdf:bcontent}\special{pdf:code q 0.12345 0.23456 0.34567 0.45678 K 3 w 0 0 m 90 30 l S Q}\special{pdf:econtent}\hbox{}',
 'path-nested':r'\special{pdf:bcontent}\special{pdf:code q 0.2 0.3 0.4 0.1 k 0 0 30 20 re f q 0.5 0.2 0.7 rg 30 0 30 20 re f Q 60 0 30 20 re f Q}\special{pdf:econtent}\hbox{}',
}
results=[]
for name,body in cases.items():
 source=out/(name+'.tex');source.write_text(r'\documentclass{article}\usepackage{xcolor}\pagestyle{empty}\begin{document}\noindent '+body+r'\end{document}')
 xdvs=[]
 for label,binary in [('baseline',root/'target/release/examples/xdv-probe'),('replacement',root/'.build/xetex-native-target/release/xetex-native-probe')]:
  xdv=out/(name+'-'+label+'.xdv');subprocess.run([str(binary),str(root/'dist/bundles/full/texbundle'),str(source),str(xdv)],check=True,capture_output=True,timeout=120);xdvs.append(xdv)
 assert xdvs[0].read_bytes()==xdvs[1].read_bytes(),name
 baseline=out/(name+'-baseline.pdf');candidate=out/(name+'-replacement.pdf')
 req={'source':source.read_text(),'bundle_path':str(root/'dist/bundles/full/texbundle'),'output_path':str(baseline)}
 subprocess.run([str(root/'target/release/lm-compile')],input=json.dumps(req),text=True,capture_output=True,check=True,timeout=120)
 cmd=[str(root/'.build/krilla-xdv-target/release/krilla-xdv-probe'),str(xdvs[1]),str(root/'.build/krilla-fonts'),str(candidate)]
 subprocess.run(cmd,check=True,capture_output=True);first=candidate.read_bytes();subprocess.run(cmd,check=True,capture_output=True);assert candidate.read_bytes()==first
 readers=[PdfReader(path) for path in (baseline,candidate)];assert len(readers[0].pages)==len(readers[1].pages)
 page_results=[]
 for page in range(len(readers[0].pages)):
  images=[]
  for path in (baseline,candidate):
   prefix=str(path.with_suffix(''))+'-'+str(page+1)
   subprocess.run(['pdftoppm','-r','144','-f',str(page+1),'-l',str(page+1),'-singlefile','-png',str(path),prefix],check=True,capture_output=True)
   images.append(Image.open(prefix+'.png').convert('RGB'))
  assert images[0].size==images[1].size
  page_results.append(sum(p!=(0,0,0) for p in ImageChops.difference(*images).get_flattened_data()))
 record={'case':name,'xdv_matches':True,'repeat_hash_matches':True,'sha256':hashlib.sha256(first).hexdigest(),'different_pixels_144dpi_per_page':page_results}
 results.append(record);print(record,flush=True)
(out/'result.json').write_text(json.dumps(results,indent=2)+'\n')
assert all(all(n==0 for n in r['different_pixels_144dpi_per_page']) for r in results),'Color raster mismatch'
