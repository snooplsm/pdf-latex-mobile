#!/usr/bin/env python3
"""Run the experimental LaTeX frontend and backend on Android and iOS.

Requires both frontend builds and the prior backend mobile probes. Does not
exercise the production Kotlin/Swift wrappers or establish release readiness.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

root=Path(__file__).resolve().parents[2]
out=root/'.build/xetex-native-mobile'
out.mkdir(parents=True,exist_ok=True)
(out/'result.json').unlink(missing_ok=True)
report=json.loads((root/'.build/xetex-native-results/result.json').read_text())
serial=os.environ.get('ANDROID_SERIAL','emulator-5554')
sdk=Path(os.environ.get('ANDROID_HOME',str(Path.home()/'Library/Android/sdk')))
adb=str(sdk/'platform-tools/adb')
def device(*args):
    return subprocess.run([adb,'-s',serial,*args],check=True,capture_output=True,text=True)
if device('shell','getprop','ro.product.cpu.abi').stdout.strip()!='arm64-v8a':raise RuntimeError('ARM64 emulator required')
remote='/data/local/tmp/latex-mobile-native-probe'
stage=out/'stage'
stage.mkdir(exist_ok=True)
shutil.copy2(root/'.build/xetex-native-target/aarch64-linux-android/release/xetex-native-probe',stage/'frontend')
shutil.copy2(root/'.build/krilla-android-target/aarch64-linux-android/release/krilla-xdv-probe',stage/'backend')
shutil.copytree(root/'dist/bundles/full/texbundle',stage/'bundle',dirs_exist_ok=True)
shutil.copytree(root/'.build/krilla-fonts',stage/'bundle',dirs_exist_ok=True)
for case in report['results']:
    name=case['example']
    src=root/'examples'/(name+'.tex') if name!='invoice-png' else root/'.build/xdv-probe/invoice-png.tex'
    if not src.exists():src=root/'experiments/krilla-xdv/fixtures'/(name+'.tex')
    shutil.copy2(src,stage/src.name)
    if src.with_suffix('.assets').is_dir():shutil.copytree(src.with_suffix('.assets'),stage/(name+'.assets'),dirs_exist_ok=True)
device('shell','mkdir','-p',remote+'/tmp')
device('push',str(stage)+'/.',remote+'/')
device('shell','chmod','755',remote+'/frontend',remote+'/backend')
devices=json.loads(subprocess.check_output(['xcrun','simctl','list','devices','booted','--json'],text=True))['devices']
udid=os.environ.get('IOS_SIMULATOR_UDID') or next((d['udid'] for group in devices.values() for d in group if d['state']=='Booted'),None)
if not udid:raise RuntimeError('Booted iOS simulator required')
ios_front=root/'.build/xetex-native-ios-target/aarch64-apple-ios-sim/release/xetex-native-probe'
ios_back=root/'.build/krilla-ios-target/aarch64-apple-ios-sim/release/krilla-xdv-probe'
def sim(*args):
    p=subprocess.run(['xcrun','simctl','spawn',udid,*map(str,args)],capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr)

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
results=[]
for case in report['results']:
    name=case['example'];record={'example':name,'runs':[]}
    for iteration in (1,2):
        suffix=f'{name}-{iteration}'
        ax=f'{remote}/{suffix}.xdv'; al=out/(suffix+'-android.xdv'); ix=out/(suffix+'-ios.xdv')
        device('shell','env','TMPDIR='+remote+'/tmp',remote+'/frontend',remote+'/bundle',remote+'/'+name+'.tex',ax)
        device('pull',ax,str(al))
        sim(ios_front,stage/'bundle',stage/(name+'.tex'),ix)
        run={'xdv_android_matches_host':digest(al)==case['xdv_sha256'],'xdv_ios_matches_host':digest(ix)==case['xdv_sha256']}
        if 'pdf_sha256' in case:
            ap=f'{remote}/{suffix}.pdf'; alp=out/(suffix+'-android.pdf'); ip=out/(suffix+'-ios.pdf')
            device('shell',remote+'/backend',ax,remote+'/bundle',ap,remote+'/'+name+'.assets')
            device('pull',ap,str(alp))
            sim(ios_back,ix,stage/'bundle',ip,stage/(name+'.assets'))
            run.update(pdf_android_matches_host=digest(alp)==case['pdf_sha256'],pdf_ios_matches_host=digest(ip)==case['pdf_sha256'],android_pdf_sha256=digest(alp),ios_pdf_sha256=digest(ip))
        record['runs'].append(run)
    results.append(record)
    print(name,record,flush=True)
result={'scope':'experimental native frontend+backend processes; not app wrapper tests','android_serial':serial,'ios_simulator':udid,'results':results}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if not all(v for r in results for run in r['runs'] for k,v in run.items() if k.endswith('_matches_host')):raise SystemExit(1)
