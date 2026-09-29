#!/usr/bin/env python3
"""Stage unchanged mobile wrappers with experimental native libraries, without replacing release artifacts."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--destination',type=Path,default=root/'.build/replacement-harness')
parser.add_argument('--extended-fixtures',action='store_true')
parser.add_argument('--include-device',action='store_true')
parser.add_argument('--final-fixtures',action='store_true')
args=parser.parse_args()
stage=args.destination.resolve()
if stage.exists():
    raise SystemExit(f'Refusing to overwrite {stage}')
ignore=shutil.ignore_patterns('build','.gradle','.kotlin','*.xcodeproj','DerivedData','Artifacts','Resources')
for name in ('android','ios','examples','include'):
    shutil.copytree(root/name,stage/name,ignore=ignore)
(stage/'tools').mkdir()
for name in ('mobile-parity.py','prepare-ios.py'):
    shutil.copy2(root/'tools'/name,stage/'tools'/name)
bundle=stage/'dist/bundles/full/texbundle'
shutil.copytree(root/'dist/bundles/full/texbundle',bundle)
shutil.copytree(root/'.build/krilla-fonts',bundle,dirs_exist_ok=True)
manifest=json.loads((bundle/'manifest.json').read_text())
if args.extended_fixtures:
    for name in ('default','dpi72','dpi300','asymmetric','progressive'):
        label='jpeg-'+name
        shutil.copy2(root/'.build/jpeg-check'/(name+'.tex'),stage/'examples'/(label+'.tex'))
        shutil.copytree(root/'.build/jpeg-check'/(name+'.assets'),stage/'examples'/(label+'.assets'))
        manifest['features'].append(label)
    shutil.copy2(root/'experiments/krilla-xdv/fixtures/multipage.tex',stage/'examples/multipage.tex')
    manifest['features'].append('multipage')
if args.final_fixtures:
    for prefix,folder,names in (
        ('color','color-check',('named','fractional','nested','special-cmyk','special-rgb','multipage','path-fill','path-stroke','path-nested')),
        ('pdf-page','pdf-page-check',('default','first','second','third','no-group','isolated','nonisolated','knockout')),
    ):
        fixture_dir=root/'.build'/folder
        for name in names:
            label=prefix+'-'+name
            shutil.copy2(fixture_dir/(name+'.tex'),stage/'examples'/(label+'.tex'))
            assets=fixture_dir/(name+'.assets')
            if assets.is_dir():shutil.copytree(assets,stage/'examples'/(label+'.assets'))
            manifest['features'].append(label)
records=[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(bundle.iterdir()) if p.is_file() and p.name not in ('SHA256SUM','manifest.json')]
fingerprint=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
(bundle/'SHA256SUM').write_text(fingerprint+'\n')
manifest.update(files=records,bundle_sha256=fingerprint,payload_bytes=sum(r['bytes'] for r in records))
(bundle/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
android=stage/'dist/native/android/full/arm64-v8a'
android.mkdir(parents=True)
shutil.copy2(root/'.build/mobile-bridge-target/aarch64-linux-android/release/liblatex_mobile.so',android)
headers=stage/'native-headers';headers.mkdir()
shutil.copy2(root/'include/latex_mobile.h',headers)
(headers/'module.modulemap').write_text('module CLatexMobile { header "latex_mobile.h" export * }\n')
framework=stage/'dist/native/ios/full/CLatexMobile.xcframework'
framework.parent.mkdir(parents=True)
# vcpkg archives are external to Cargo's static library; Swift consumers need them merged.
merged=framework.parent/'liblatex_mobile.a'
names='brotlicommon brotlidec brotlienc bz2 expat fontconfig freetype graphite2 icudata icui18n icuio icuuc png16 uuid z'.split()
libs=[root/'.build/vcpkg/installed/arm64-ios-simulator-release/lib'/f'lib{name}.a' for name in names]
subprocess.run(['xcrun','libtool','-static','-o',str(merged),str(root/'.build/mobile-bridge-ios-target/aarch64-apple-ios-sim/release/liblatex_mobile.a'),*[str(p) for p in libs]],check=True)
framework_command=['xcodebuild','-create-xcframework','-library',str(merged),'-headers',str(headers)]
if args.include_device:
    device=framework.parent/'device/liblatex_mobile.a';device.parent.mkdir()
    device_libs=[root/'.build/vcpkg/installed/arm64-ios-release/lib'/f'lib{name}.a' for name in names]
    subprocess.run(['xcrun','libtool','-static','-o',str(device),str(root/'.build/mobile-bridge-ios-target/aarch64-apple-ios/release/liblatex_mobile.a'),*[str(p) for p in device_libs]],check=True)
    framework_command+=['-library',str(device),'-headers',str(headers)]
subprocess.run(framework_command+['-output',str(framework)],check=True)
for name in ('ios/project.yml','tools/mobile-parity.py'):
    p=stage/name;p.write_text(p.read_text().replace('org.latexmobile.harness','org.latexmobile.harness.replacement'))
p=stage/'android/library/build.gradle.kts'
p.write_text(p.read_text().replace('minSdk = 28','minSdk = 28\n        testApplicationId = "org.latexmobile.replacement.test"'))
p=stage/'android/harness/build.gradle.kts'
p.write_text(p.read_text().replace('applicationId = "org.latexmobile.harness"','applicationId = "org.latexmobile.harness.replacement"'))
checks={}
for pattern in ('android/library/src/**/*.kt','ios/LaTeXMobile/Sources/**/*.swift','ios/HarnessTests/*.swift'):
    for source in root.glob(pattern):
        relative=source.relative_to(root)
        checks[str(relative)]=(stage/relative).read_bytes()==source.read_bytes()
assert all(checks.values()),checks
(stage/'provenance.json').write_text(json.dumps({
    'unchanged_wrapper_and_test_sources':checks,
    'fixture_features':manifest['features'],
    'android_native_sha256':hashlib.sha256((android/'liblatex_mobile.so').read_bytes()).hexdigest(),
    'ios_native_sha256':hashlib.sha256(merged.read_bytes()).hexdigest(),
},indent=2)+'\n')
print(stage)
