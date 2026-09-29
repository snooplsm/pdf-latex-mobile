"""Compare the TECkit-free host build with a preserved TECkit-enabled compiler."""
import argparse,json,subprocess,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline',type=Path,default=root/'.build/with-teckit/lm-compile')
args=parser.parse_args()
out=root/'.build/no-teckit-check';out.mkdir(exist_ok=True)
cases={p.stem:(p.read_text(),root/'examples'/(p.stem+'.assets')) for p in (root/'examples').glob('*.tex')}
preamble=r'\documentclass{article}\usepackage{fontspec}\setmainfont{lmroman10-regular.otf}'
for name,body in {'punctuation':"-- --- ---- ----- ------ `hello' ``hello'' !` ?` café e\u0301",'nfc':'\\XeTeXinputnormalization=1\n café e\u0301 Å A\u030a','nfd':'\\XeTeXinputnormalization=2\n café e\u0301 Å A\u030a'}.items():cases[name]=(preamble+'\n\\begin{document}\n'+body+'\n\\end{document}',None)
results=[]
for name,(source,assets) in cases.items():
 hashes=[]
 for label,binary in [('before',args.baseline.resolve()),('after',root/'target/release/lm-compile')]:
  pdf=out/(name+'-'+label+'.pdf');request={'source':source,'bundle_path':str(root/'.build/review-bundle-config-licensed'),'output_path':str(pdf)}
  if assets and assets.is_dir():request['asset_files']={p.name:str(p) for p in assets.iterdir() if p.is_file()}
  r=subprocess.run([str(binary)],input=json.dumps(request),text=True,capture_output=True);assert r.returncode==0,(name,label,r.stdout,r.stderr)
  hashes.append(hashlib.sha256(pdf.read_bytes()).hexdigest())
 record={'case':name,'hashes':hashes,'equal':hashes[0]==hashes[1]};results.append(record);print(name,record['equal'],flush=True)
(out/'result.json').write_text(json.dumps(results,indent=2)+'\n')
assert all(r['equal'] for r in results)

# Custom compiled mappings must fail rather than silently changing text.
request={'source':preamble.replace('lmroman10-regular.otf}', 'lmroman10-regular.otf}[Mapping=unsupported-custom]') + r'\begin{document}Hello\end{document}', 'bundle_path':str(root/'.build/review-bundle-config-licensed'), 'output_path':str(out/'rejected.pdf')}
r=subprocess.run([str(root/'target/release/lm-compile')],input=json.dumps(request),text=True,capture_output=True)
assert r.returncode != 0 and not json.loads(r.stdout)['ok'], r.stdout
assert not (out/'rejected.pdf').exists()
print('custom mapping rejected',flush=True)
