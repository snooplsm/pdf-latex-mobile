#!/usr/bin/env python3
"""Verify the reviewed data/notice overlay does not change generated PDFs."""
import argparse,hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bundle',type=Path,default=root/'.build/review-bundle');parser.add_argument('--output-dir',type=Path,default=root/'.build/review-bundle-check');args=parser.parse_args()
out=args.output_dir.resolve();out.mkdir(exist_ok=True)
(out/'result.json').unlink(missing_ok=True)
cli=root/'.build/xetex-native-target/release/compile-pdf'
source=out/'slovak.tex'
source.write_text(r'''\documentclass{article}
\begin{document}
\makeatletter\language=\l@slovak\makeatother
\hsize=80pt
Slovenského slovenskými najrozšírenejšieho rozdelenie jednoducho
slovenského slovenskými najrozšírenejšieho rozdelenie jednoducho.
\end{document}
''')
sources=list(sorted((root/'examples').glob('*.tex')))+[root/'experiments/krilla-xdv/fixtures/multipage.tex',source]
results=[]
for src in sources:
 hashes=[]
 for label,bundle in [('before',root/'dist/bundles/full/texbundle'),('reviewed',args.bundle.resolve())]:
  pdf=out/(src.stem+'-'+label+'.pdf')
  run=subprocess.run([str(cli),str(bundle),str(root/'.build/krilla-fonts'),str(src),str(pdf)],capture_output=True,text=True)
  assert run.returncode==0,(src,run.stdout,run.stderr)
  hashes.append(hashlib.sha256(pdf.read_bytes()).hexdigest())
 assert hashes[0]==hashes[1],src
 results.append({'case':src.stem,'sha256':hashes[0],'unchanged':True});print(src.stem,True,flush=True)
(out/'result.json').write_text(json.dumps(results,indent=2)+'\n')
