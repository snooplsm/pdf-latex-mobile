#!/usr/bin/env python3
"""Build/run the experimental backend on an ARM64 Android emulator.

This is backend parity on identical XDV inputs, not end-to-end LaTeX parity.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

root=Path(__file__).resolve().parents[2]
sdk=Path(os.environ.get('ANDROID_HOME',str(Path.home()/'Library/Android/sdk')))
ndk=Path(os.environ.get('ANDROID_NDK_HOME',str(sdk/'ndk/29.0.14206865')))
cc=ndk/'toolchains/llvm/prebuilt/darwin-x86_64/bin'
adb=str(sdk/'platform-tools/adb')
serial=os.environ.get('ANDROID_SERIAL','emulator-5554')
target='aarch64-linux-android'
build=root/'.build/krilla-android-target'
logs=root/'.build/krilla-android'
logs.mkdir(parents=True,exist_ok=True)
env=os.environ.copy()
env.update(CARGO_TARGET_DIR=str(build),CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER=str(cc/'aarch64-linux-android28-clang'),CC_aarch64_linux_android=str(cc/'aarch64-linux-android28-clang'),AR_aarch64_linux_android=str(cc/'llvm-ar'))
with (logs/'build.log').open('w') as log:
    subprocess.run(['cargo','build','--locked','--release','--target',target,'--manifest-path',str(root/'experiments/krilla-xdv/Cargo.toml')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
binary=build/target/'release/krilla-xdv-probe'
subprocess.run([str(cc/'llvm-strip'),'--strip-unneeded',str(binary)],check=True)
def device(*args, **kwargs):
    return subprocess.run([adb,'-s',serial,*args],check=True,capture_output=True,**kwargs)
abi=device('shell','getprop','ro.product.cpu.abi',text=True).stdout.strip()
if abi!='arm64-v8a': raise RuntimeError(f'Expected ARM64 emulator, got {abi}')
stage=logs/'stage'
stage.mkdir(exist_ok=True)
shutil.copy2(binary,stage/'backend')
for p in (root/'.build/krilla-fonts').iterdir():
    if p.is_file():shutil.copy2(p,stage/p.name)
for p in (root/'examples/invoice.assets').iterdir():
    if p.is_file():shutil.copy2(p,stage/p.name)
report=json.loads((root/'.build/xdv-probe/krilla-comparison.json').read_text())
for case in report['results']:
    if case['compiled']:shutil.copy2(root/'.build/xdv-probe'/f"{case['example']}.xdv",stage)
remote='/data/local/tmp/latex-mobile-krilla-probe'
device('shell','mkdir','-p',remote)
device('push',str(stage)+'/.',remote+'/')
device('shell','chmod','755',remote+'/backend')
results=[]
for case in report['results']:
    if not case['compiled']:continue
    name=case['example']
    hashes=[]
    for iteration in (1,2):
        dest=f'{remote}/{name}-{iteration}.pdf'
        device('shell',remote+'/backend',f'{remote}/{name}.xdv',remote,dest,remote)
        local=logs/f'{name}-{iteration}.pdf'
        device('pull',dest,str(local))
        hashes.append(hashlib.sha256(local.read_bytes()).hexdigest())
    host=hashlib.sha256((root/'.build/xdv-probe'/f'{name}-krilla.pdf').read_bytes()).hexdigest()
    results.append({'example':name,'host_sha256':host,'android_sha256':hashes,'match':host==hashes[0]==hashes[1]})
result={'scope':'PDF backend only: identical host-generated XDV and fonts','abi':abi,'results':results}
(logs/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
if not all(r['match'] for r in results):raise SystemExit(1)
