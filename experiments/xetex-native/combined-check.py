#!/usr/bin/env python3
"""Compare the in-process native pipeline against the renderer references."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('platform',choices=('host','android','ios'))
parser.add_argument('--reference-dir',type=Path)
parser.add_argument('--include-jpeg',action='store_true')
parser.add_argument('--include-colors-and-pdf-pages',action='store_true')
args=parser.parse_args()
root=Path(__file__).resolve().parents[2];out=root/'.build/combined-pipeline'/args.platform;out.mkdir(parents=True,exist_ok=True)
(out/'result.json').unlink(missing_ok=True)
reference_dir=(args.reference_dir or root/'.build/xdv-probe').resolve()
reference=json.loads((reference_dir/'krilla-comparison.json').read_text())
required={'core','text','math','graphics','diagrams','fonts','languages','bibliography','invoice','invoice-png','multipage'}
cases={c['example']:c for c in reference['results']}
assert required<=cases.keys() and all(cases[n]['compiled'] for n in required)
stage=Path(tempfile.mkdtemp(prefix='stage-',dir=out))
sources={};references={}
shutil.copytree(root/'dist/bundles/full/texbundle',stage/'bundle',dirs_exist_ok=True)
shutil.copytree(root/'.build/krilla-fonts',stage/'fonts',dirs_exist_ok=True)
for name in sorted(required):
 source=root/'examples'/(name+'.tex')
 if name=='invoice-png':source=root/'.build/xdv-probe/invoice-png.tex'
 if not source.exists():source=root/'experiments/krilla-xdv/fixtures'/(name+'.tex')
 sources[name]=source
 references[name]=reference_dir/(name+'-krilla.pdf')
 shutil.copy2(source,stage/source.name)
 if source.with_suffix('.assets').is_dir():shutil.copytree(source.with_suffix('.assets'),stage/(name+'.assets'),dirs_exist_ok=True)

if args.include_jpeg:
 for case in ('default','dpi72','dpi300','asymmetric','progressive'):
  name='jpeg-'+case;required.add(name)
  source=root/'.build/jpeg-check'/(case+'.tex')
  sources[name]=source;references[name]=root/'.build/jpeg-check'/(case+'-replacement.pdf')
  shutil.copy2(source,stage/(name+'.tex'))
  shutil.copytree(source.with_suffix('.assets'),stage/(name+'.assets'))

if args.include_colors_and_pdf_pages:
 for prefix,folder,case_names in (
  ('color', 'color-check', ('named','fractional','nested','special-cmyk','special-rgb','multipage')),
  ('pdf-page', 'pdf-page-check', ('default','first','second','third','no-group','isolated','nonisolated','knockout')),
 ):
  fixture_dir=root/'.build'/folder
  fixture_report={r['case']:r for r in json.loads((fixture_dir/'result.json').read_text())}
  for case in case_names:
   row=fixture_report[case]
   assert row['repeat_hash_matches'] and row['xdv_matches']
   assert row.get('different_pixels_144dpi',0)==0
   assert all(n==0 for n in row.get('different_pixels_144dpi_per_page',[]))
   name=prefix+'-'+case;required.add(name)
   source=fixture_dir/(case+'.tex');reference_pdf=fixture_dir/(case+'-replacement.pdf')
   assert hashlib.sha256(reference_pdf.read_bytes()).hexdigest()==row['sha256'],(name,'stale reference')
   sources[name]=source;references[name]=reference_pdf
   shutil.copy2(source,stage/(name+'.tex'))
   assets=source.with_suffix('.assets')
   if assets.is_dir():shutil.copytree(assets,stage/(name+'.assets'))

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,**kw):return subprocess.run(list(map(str,cmd)),check=True,capture_output=True,text=True,timeout=120,**kw)
if args.platform=='android':
 sdk=Path(os.environ.get('ANDROID_HOME',str(Path.home()/'Library/Android/sdk')))
 adb=[sdk/'platform-tools/adb','-s',os.environ.get('ANDROID_SERIAL','emulator-5554')]
 assert run(adb+['shell','getprop','ro.product.cpu.abi']).stdout.strip()=='arm64-v8a'
 binary=root/'.build/xetex-native-target/aarch64-linux-android/release/compile-pdf'
 shutil.copy2(binary,stage/'compile-pdf');remote='/data/local/tmp/latex-mobile-combined-'+stage.name
 run(adb+['shell','mkdir','-p',remote+'/tmp']);run(adb+['push',str(stage)+'/.',remote+'/']);run(adb+['shell','chmod','755',remote+'/compile-pdf'])
 def compile(name,dest):
  result=remote+'/'+dest.name
  run(adb+['shell','env','TMPDIR='+remote+'/tmp',remote+'/compile-pdf',remote+'/bundle',remote+'/fonts',remote+'/'+name+'.tex',result])
  run(adb+['pull',result,dest])
elif args.platform=='ios':
 binary=root/'.build/xetex-native-ios-target/aarch64-apple-ios-sim/release/compile-pdf'
 devices=json.loads(run(['xcrun','simctl','list','devices','booted','--json']).stdout)['devices']
 udid=os.environ.get('IOS_SIMULATOR_UDID') or next(d['udid'] for group in devices.values() for d in group if d['state']=='Booted')
 def compile(name,dest):run(['xcrun','simctl','spawn',udid,binary,stage/'bundle',stage/'fonts',stage/(name+'.tex'),dest])
else:
 binary=root/'.build/xetex-native-target/release/compile-pdf'
 def compile(name,dest):run([binary,stage/'bundle',stage/'fonts',stage/(name+'.tex'),dest])
records=[]
for name in sorted(required):
 expected=digest(references[name]);hashes=[]
 for iteration in (1,2):
  dest=out/f'{name}-{iteration}.pdf';dest.unlink(missing_ok=True);compile(name,dest);hashes.append(digest(dest))
 record={'example':name,'source_sha256':digest(sources[name]),'asset_sha256':{p.name:digest(p) for p in sorted((stage/(name+'.assets')).glob('*')) if p.is_file()},'expected_sha256':expected,'actual_sha256':hashes,'match':all(h==expected for h in hashes)}
 records.append(record);print(name,record['match'],flush=True)
if args.platform=='host':
 # Compilation failure must not replace an existing destination.
 (stage/'invalid.tex').write_text('\\documentclass{article}\\begin{document}\\undefinedCommand\\end{document}')
 existing=out/'preserve.pdf';existing.write_bytes(b'unchanged output')
 try:compile('invalid',existing)
 except subprocess.CalledProcessError:pass
 else:raise AssertionError('Invalid LaTeX unexpectedly succeeded')
 assert existing.read_bytes()==b'unchanged output'
result={'scope':'in-process native library via CLI; not production app wrappers','platform':args.platform,'stage':str(stage),'reference_dir':str(reference_dir),'font_sha256':{p.name:digest(p) for p in sorted((stage/'fonts').glob('*')) if p.is_file()},'binary_sha256':digest(binary),'results':records,'atomic_output_failure_check':args.platform=='host'}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
assert all(c['match'] for c in records)
