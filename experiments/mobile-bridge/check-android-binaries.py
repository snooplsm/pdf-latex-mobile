#!/usr/bin/env python3
"""Inspect replacement Android ELF artifacts; does not claim runtime verification."""
import hashlib,json,os,re,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sdk=Path(os.environ.get('ANDROID_HOME',str(Path.home()/'Library/Android/sdk')))
ndk=Path(os.environ.get('ANDROID_NDK_HOME',str(sdk/'ndk/29.0.14206865')))
readelf=ndk/'toolchains/llvm/prebuilt/darwin-x86_64/bin/llvm-readelf'
results=[]
for abi,target,machine in [('arm64-v8a','aarch64-linux-android','AArch64'),('armeabi-v7a','armv7-linux-androideabi','ARM'),('x86_64','x86_64-linux-android','Advanced Micro Devices X86-64')]:
 path=root/'.build/mobile-bridge-target'/target/'release/liblatex_mobile.so'
 info=subprocess.check_output([str(readelf),'-h','-l','-d','--dyn-syms',str(path)],text=True)
 assert re.search(r'Machine:\s+'+re.escape(machine)+r'\s*\n',info),(abi,'machine')
 loads=[line for line in info.splitlines() if line.strip().startswith('LOAD ')]
 assert loads and all(int(line.split()[-1],16)>=16384 for line in loads),(abi,'segment alignment')
 for name in ('lm_compile','lm_string_free','Java_org_latexmobile_LatexMobile_compileNative'):
  assert any(line.split()[-1:]==[name] and ' UND ' not in line for line in info.splitlines()),(abi,name)
 needed=re.findall(r'\(NEEDED\).*\[([^]]+)\]',info)
 assert set(needed)<= {'libc.so','libm.so','libdl.so','liblog.so'},(abi,needed)
 results.append({'abi':abi,'machine':machine,'load_alignment_at_least_16kb':True,'public_entry_points':True,'needed':needed,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'runtime_verified':False})
report={'scope':'ELF structure, exported entry points, alignment and external shared libraries only','results':results}
out=root/'.build/mobile-bridge-android-binaries.json';out.write_text(json.dumps(report,indent=2)+'\n')
print(out)
