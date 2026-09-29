#!/usr/bin/env python3
"""Compare explicit imported-PDF page selection and invalid-page failures."""
import hashlib,json,shutil,subprocess
from pathlib import Path
from PIL import Image,ImageChops
from pypdf import PdfReader,PdfWriter
from pypdf.generic import NameObject,DictionaryObject,BooleanObject,FloatObject,DecodedStreamObject
root=Path(__file__).resolve().parents[2];out=root/'.build/pdf-page-check';out.mkdir(exist_ok=True)
# Overlapping translucent shapes expose isolation/knockout changes. Keep an
# opaque colored backdrop outside the imported page to exercise blending.
fixtures={}
for group_name,isolated,knockout in [('no-group',None,None),('isolated',True,False),('nonisolated',False,False),('knockout',True,True)]:
 writer=PdfWriter();page=writer.add_blank_page(width=240,height=160)
 state=DictionaryObject({NameObject('/Type'):NameObject('/ExtGState'),NameObject('/ca'):FloatObject(.5),NameObject('/BM'):NameObject('/Multiply')})
 page[NameObject('/Resources')]=DictionaryObject({NameObject('/ExtGState'):DictionaryObject({NameObject('/Blend'):writer._add_object(state)})})
 stream=DecodedStreamObject();stream.set_data(b'q /Blend gs 1 0 0 rg 10 10 150 100 re f 0 0 1 rg 70 40 150 100 re f Q')
 page[NameObject('/Contents')]=writer._add_object(stream)
 if isolated is not None:
  group=DictionaryObject({NameObject('/Type'):NameObject('/Group'),NameObject('/S'):NameObject('/Transparency'),NameObject('/CS'):NameObject('/DeviceRGB'),NameObject('/I'):BooleanObject(isolated),NameObject('/K'):BooleanObject(knockout)})
  page[NameObject('/Group')]=writer._add_object(group)
 fixture=out/(group_name+'-source.pdf');writer.write(fixture);fixtures[group_name]=fixture
results=[]
cases=[('default',0,'First page'),('first',1,'First page'),('second',2,'Second page'),('third',3,'Third page'),('negative',-1,None),('out-of-range',4,None)]+[(name,1,'Selected page') for name in fixtures]
for name,page,title in cases:
 assets=out/(name+'.assets');assets.mkdir(exist_ok=True)
 shutil.copy2(fixtures.get(name,root/'.build/xdv-probe/multipage-baseline.pdf'),assets/'pages.pdf')
 source=out/(name+'.tex');source_text=(r'\documentclass{article}\usepackage{graphicx}\begin{document}Selected page\par\includegraphics[page='+str(page)+r',width=120pt]{pages.pdf}\end{document}')
 if name in fixtures:
  source_text=source_text.replace(r'\usepackage{graphicx}',r'\usepackage{graphicx}\usepackage{xcolor}').replace(r'\includegraphics',r'\colorbox[rgb]{1,1,0}{\includegraphics').replace(r'{pages.pdf}',r'{pages.pdf}}')
 source.write_text(source_text)
 xdvs=[]
 for label,binary in [('baseline',root/'.build/original-engine/xdv-probe'),('replacement',root/'.build/xetex-native-target/release/xetex-native-probe')]:
  xdv=out/(name+'-'+label+'.xdv')
  result=subprocess.run([str(binary),str(root/'.build/original-bundles/full/texbundle'),str(source),str(xdv)],capture_output=True,text=True)
  assert result.returncode==0,(name,label,result.stderr)
  xdvs.append(xdv)
 assert xdvs[0].read_bytes()==xdvs[1].read_bytes(),(name,'XDV mismatch')
 baseline=out/(name+'-baseline.pdf');candidate=out/(name+'-replacement.pdf')
 baseline.write_bytes(b'previous');candidate.write_bytes(b'previous')
 request={'source':source.read_text(),'bundle_path':str(root/'.build/original-bundles/full/texbundle'),'output_path':str(baseline),'asset_files':{'pages.pdf':str(assets/'pages.pdf')}}
 a=subprocess.run([str(root/'.build/original-engine/lm-compile')],input=json.dumps(request),text=True,capture_output=True)
 command=[str(root/'.build/krilla-xdv-target/release/krilla-xdv-probe'),str(xdvs[1]),str(root/'.build/krilla-fonts'),str(candidate),str(assets)]
 b=subprocess.run(command,text=True,capture_output=True)
 if title is None:
  assert a.returncode!=0 and b.returncode!=0,(name,a.stdout,b.stderr)
  assert baseline.read_bytes()==candidate.read_bytes()==b'previous'
  results.append({'case':name,'xdv_matches':True,'both_reject_and_preserve_output':True})
 else:
  assert a.returncode==b.returncode==0,(name,a.stdout,b.stderr)
  expected=hashlib.sha256(candidate.read_bytes()).hexdigest();subprocess.run(command,check=True)
  assert hashlib.sha256(candidate.read_bytes()).hexdigest()==expected
  readers=[PdfReader(path) for path in (baseline,candidate)]
  assert all(len(r.pages)==1 for r in readers)
  if name in fixtures:
   def group_values(group):
    return None if group is None else {str(k):str(v.get_object()) for k,v in group.get_object().items()}
   baseline_imports=list(readers[0].pages[0]['/Resources']['/XObject'].values())
   assert len(baseline_imports)==1
   expected_group=group_values(baseline_imports[0].get_object().get('/Group'))
   imported=list(readers[1].pages[0]['/Resources']['/XObject'].values())
   assert len(imported)==1
   assert group_values(imported[0].get_object().get('/Group'))==expected_group,(name,'Imported group differs from original backend')
  texts=[r.pages[0].extract_text() for r in readers]
  assert texts[0]==texts[1] and title in texts[1],(name,texts)
  images=[]
  for path in (baseline,candidate):
   subprocess.run(['pdftoppm','-r','144','-singlefile','-png',str(path),str(path.with_suffix(''))],check=True,capture_output=True)
   with Image.open(path.with_suffix('.png')) as im:images.append(im.convert('RGB'))
  assert images[0].size==images[1].size
  pixels=sum(v!=(0,0,0) for v in ImageChops.difference(*images).get_flattened_data())
  results.append({'case':name,'xdv_matches':True,'selected_page_text_matches':True,'repeat_hash_matches':True,'sha256':expected,'different_pixels_144dpi':pixels})
 print(results[-1],flush=True)
(out/'result.json').write_text(json.dumps(results,indent=2)+'\n')
assert all(r.get('different_pixels_144dpi',0)==0 for r in results),'Raster mismatch; see report'
