#!/usr/bin/env python3
"""Run the experimental PDF backend as a simulator process, not the production app."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[2]
logs=root/'.build/krilla-ios'
logs.mkdir(parents=True,exist_ok=True)
target='aarch64-apple-ios-sim'
build=root/'.build/krilla-ios-target'
env=os.environ.copy()
env.update(CARGO_TARGET_DIR=str(build),IPHONEOS_DEPLOYMENT_TARGET='15.0')
with (logs/'build.log').open('w') as log:
    subprocess.run(['cargo','build','--locked','--release','--target',target,'--manifest-path',str(root/'experiments/krilla-xdv/Cargo.toml')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
binary=build/target/'release/krilla-xdv-probe'
devices=json.loads(subprocess.check_output(['xcrun','simctl','list','devices','booted','--json'],text=True))['devices']
udid=os.environ.get('IOS_SIMULATOR_UDID')
if not udid:
    ids=[d['udid'] for group in devices.values() for d in group if d['state']=='Booted']
    if not ids: raise RuntimeError('Boot an iOS simulator before this probe')
    udid=ids[0]
report=json.loads((root/'.build/xdv-probe/krilla-comparison.json').read_text())
results=[]
for case in report['results']:
    if not case['compiled']:continue
    name=case['example']
    original='invoice' if name=='invoice-png' else name
    hashes=[]
    for iteration in (1,2):
        dest=logs/f'{name}-{iteration}.pdf'
        run=subprocess.run(['xcrun','simctl','spawn',udid,str(binary),str(root/'.build/xdv-probe'/f'{name}.xdv'),str(root/'.build/krilla-fonts'),str(dest),str(root/'examples'/f'{original}.assets')],capture_output=True,text=True)
        if run.returncode:raise RuntimeError(f'{name}: {run.stderr}')
        hashes.append(hashlib.sha256(dest.read_bytes()).hexdigest())
    host=hashlib.sha256((root/'.build/xdv-probe'/f'{name}-krilla.pdf').read_bytes()).hexdigest()
    results.append({'example':name,'host_sha256':host,'ios_sha256':hashes,'match':host==hashes[0]==hashes[1]})
result={'scope':'PDF backend simulator process only: identical host-generated XDV/fonts','simulator':udid,'results':results}
(logs/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
if not all(r['match'] for r in results):raise SystemExit(1)
