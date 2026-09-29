#!/usr/bin/env python3
"""Exercise the existing C JSON ABI against the experimental replacement library."""
import base64,ctypes,hashlib,json,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[2];out=root/'.build/mobile-bridge-check';out.mkdir(exist_ok=True)
(out/'result.json').unlink(missing_ok=True)
bundle=out/'bundle'
shutil.copytree(root/'dist/bundles/full/texbundle',bundle,dirs_exist_ok=True)
shutil.copytree(root/'.build/krilla-fonts',bundle,dirs_exist_ok=True)
records=[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(bundle.iterdir()) if p.is_file() and p.name!='SHA256SUM']
(bundle/'SHA256SUM').write_text(hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()+'\n')
path=root/'.build/mobile-bridge-target/release/liblatex_mobile.dylib';lib=ctypes.CDLL(str(path))
lib.lm_compile.argtypes=[ctypes.c_char_p];lib.lm_compile.restype=ctypes.c_void_p
lib.lm_string_free.argtypes=[ctypes.c_void_p];lib.lm_string_free.restype=None

def call(raw):
 p=lib.lm_compile(raw)
 assert p,'null response'
 try:return json.loads(ctypes.string_at(p))
 finally:lib.lm_string_free(p)
def request(source,dest,**assets):return call(json.dumps({'source':source,'bundle_path':str(bundle),'output_path':str(dest),**assets}).encode())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
results=[]
for name in ('core','text','math','graphics','diagrams','fonts','languages','bibliography','invoice','invoice-png','multipage'):
 source=root/'examples'/(name+'.tex')
 if name=='invoice-png':source=root/'.build/xdv-probe/invoice-png.tex'
 if not source.exists():source=root/'experiments/krilla-xdv/fixtures'/(name+'.tex')
 assets={p.name:str(p) for p in source.with_suffix('.assets').glob('*') if p.is_file()}
 expected=sha(root/'.build/xdv-probe'/(name+'-krilla.pdf'))
 hashes=[]
 for iteration in (1,2):
  dest=out/(name+'.pdf');result=request(source.read_text(),dest,asset_files=assets)
  assert result['ok'],(name,result['error'],result['log'])
  assert result['pdf_bytes']==dest.stat().st_size and result['files']
  hashes.append(sha(dest))
 assert hashes==[expected,expected],name
 results.append({'case':name,'sha256':expected,'repeat_matches':True});print(name,True,flush=True)
source=(root/'examples/invoice.tex').read_text();logo=root/'examples/invoice.assets/logo.pdf';expected=sha(root/'.build/xdv-probe/invoice-krilla.pdf')
for name,latex,assets in (
 ('inline',source,{'assets':{'logo.pdf':base64.b64encode(logo.read_bytes()).decode()}}),
 ('nested',source.replace('{logo.pdf}','{images/logo.pdf}'),{'asset_files':{'images/logo.pdf':str(logo)}})):
 dest=out/(name+'.pdf');result=request(latex,dest,**assets);assert result['ok'],result
 assert sha(dest)==expected,name
 results.append({'case':name,'sha256':expected});print(name,True,flush=True)
for raw in (None,b'not JSON',b'\xff'):
 assert not call(raw)['ok']
lib.lm_string_free(None)
dest=out/'preserve.pdf';dest.write_bytes(b'keep me')
for assets in ({'asset_files':{'../escape':str(logo)}},{'assets':{'logo.pdf':'invalid!'}},{'asset_files':{'logo.pdf':str(logo)},'assets':{'logo.pdf':''}}):
 result=request(source,dest,**assets);assert not result['ok'];assert dest.read_bytes()==b'keep me'
result=request('\\documentclass{article}\\begin{document}\\undefinedCommand\\end{document}',dest)
assert not result['ok'] and result['log'] and dest.read_bytes()==b'keep me'
# Recover after engine failure in this same process.
result=request((root/'examples/core.tex').read_text(),dest);assert result['ok'],result
assert sha(dest)==sha(root/'.build/xdv-probe/core-krilla.pdf')
report={'scope':'host C ABI using unchanged request/response schema and allocation API','library_sha256':sha(path),'cases':results,'invalid_inputs_and_output_preservation':True,'engine_error_log_and_recovery':True}
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print('ABI validation passed',flush=True)
