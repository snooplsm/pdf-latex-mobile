#!/usr/bin/env python3
"""Build an isolated native frontend using already-installed project toolchains."""
import argparse
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument('platform',choices=('host','android','ios'))
parser.add_argument('--bridge',action='store_true',help='Build the isolated copy of the existing mobile C/JNI bridge')
parser.add_argument('--android-abi',choices=('arm64-v8a','armeabi-v7a','x86_64'),default='arm64-v8a')
parser.add_argument('--ios-device',action='store_true',help='Build for a physical iOS device instead of the simulator')
args=parser.parse_args()
if args.ios_device and args.platform!='ios':parser.error('--ios-device requires ios')
root=Path(__file__).resolve().parents[2]
env=os.environ.copy()
env.update(VCPKG_ROOT=str(root/'.build/vcpkg'),TECTONIC_DEP_BACKEND='vcpkg')
env['PATH']=str(root/'.build/host/bin')+os.pathsep+env['PATH']
target=None
if args.platform=='host':
    env.update(VCPKGRS_TRIPLET='arm64-osx',CARGO_TARGET_DIR=str(root/'.build/xetex-native-target'))
elif args.platform=='android':
    sdk=Path(env.get('ANDROID_HOME',str(Path.home()/'Library/Android/sdk')))
    ndk=Path(env.get('ANDROID_NDK_HOME',str(sdk/'ndk/29.0.14206865')))
    cc=ndk/'toolchains/llvm/prebuilt/darwin-x86_64/bin'
    target,triplet,compiler={
        'arm64-v8a':('aarch64-linux-android','arm64-android','aarch64-linux-android28-clang'),
        'armeabi-v7a':('armv7-linux-androideabi','arm-android','armv7a-linux-androideabi28-clang'),
        'x86_64':('x86_64-linux-android','x64-android','x86_64-linux-android28-clang'),
    }[args.android_abi]
    env.update(VCPKGRS_TRIPLET=triplet,CARGO_TARGET_DIR=str(root/'.build/xetex-native-target'),CC=compiler,CXX=compiler+'++',CXXSTDLIB='c++_static',AR='llvm-ar',RUSTFLAGS='-C link-arg=-Wl,-z,max-page-size=16384 -C link-arg=-Wl,-z,common-page-size=16384')
    env['CARGO_TARGET_'+target.upper().replace('-','_')+'_LINKER']=compiler
    env['PATH']=str(cc)+os.pathsep+env['PATH']
else:
    env.update(VCPKGRS_TRIPLET=('arm64-ios-release' if args.ios_device else 'arm64-ios-simulator-release'),CARGO_TARGET_DIR=str(root/'.build/xetex-native-ios-target'),IPHONEOS_DEPLOYMENT_TARGET='15.0')
    target='aarch64-apple-ios' if args.ios_device else 'aarch64-apple-ios-sim'
if args.bridge:
    env['CARGO_TARGET_DIR']=str(root/('.build/mobile-bridge-ios-target' if args.platform=='ios' else '.build/mobile-bridge-target'))
manifest=root/('.build/mobile-bridge/Cargo.toml' if args.bridge else 'experiments/xetex-native/Cargo.toml')
command=['cargo','build','--locked','--release','--manifest-path',str(manifest)]
if target:command+=['--target',target]
label=args.platform + ('-device' if args.ios_device else '') + ('-'+args.android_abi if args.platform=='android' and args.android_abi!='arm64-v8a' else '')
log=root/'.build'/(('mobile-bridge-' if args.bridge else 'xetex-native-')+label+'-build.log')
with log.open('w') as stream:
    result=subprocess.run(command,env=env,stdout=stream,stderr=subprocess.STDOUT)
print(f'{args.platform}: exit {result.returncode}; log {log}')
raise SystemExit(result.returncode)
