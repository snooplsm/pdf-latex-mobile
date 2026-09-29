#!/usr/bin/env python3
"""Measure unsigned arm64 iOS Release app growth against the same UI without LaTeX."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from sizes import write_report

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.build/ios-size-probe'
DIST = ROOT / 'dist/ios-size-probe'
WORK.mkdir(parents=True, exist_ok=True)
DIST.mkdir(parents=True, exist_ok=True)
xcodegen = shutil.which('xcodegen') or str(ROOT / '.build/xcodegen/bin/xcodegen')
records = []
for profile in ('baseline', 'tiny', 'small', 'balanced', 'full'):
    work = WORK / profile
    work.mkdir(parents=True, exist_ok=True)
    spec = {
        'name': 'SizeProbe', 'options': {'deploymentTarget': {'iOS': '15.0'}},
        'settings': {'base': {'SWIFT_VERSION': '5.9', 'GENERATE_INFOPLIST_FILE': 'YES',
                              'CODE_SIGNING_ALLOWED': 'NO', 'DEAD_CODE_STRIPPING': 'YES',
                              'STRIP_INSTALLED_PRODUCT': 'YES', 'COPY_PHASE_STRIP': 'YES',
                              'SWIFT_OPTIMIZATION_LEVEL': '-O', 'ARCHS': 'arm64'}},
        'targets': {'SizeProbe': {'type': 'application', 'platform': 'iOS',
                    'sources': [str(ROOT / 'ios/SizeProbe')],
                    'settings': {'base': {'PRODUCT_BUNDLE_IDENTIFIER': 'org.latexmobile.sizeprobe',
                                         'INFOPLIST_KEY_UILaunchScreen_Generation': 'YES'}}}}
    }
    if profile != 'baseline':
        # Isolated package copies keep the developer's selected harness profile unchanged.
        package = work / 'LaTeXMobile'
        if package.exists():
            shutil.rmtree(package)
        shutil.copytree(ROOT / 'ios/LaTeXMobile', package,
                        ignore=shutil.ignore_patterns('Artifacts', 'Resources', '.build', '.swiftpm'))
        native = 'full' if profile == 'full' else 'compact'
        shutil.copytree(ROOT / f'dist/native/ios/{native}/CLatexMobile.xcframework',
                        package / 'Artifacts/CLatexMobile.xcframework')
        shutil.copytree(ROOT / f'dist/bundles/{profile}/texbundle',
                        package / 'Sources/LaTeXMobile/Resources/texbundle')
        spec['packages'] = {'LaTeXMobile': {'path': str(package)}}
        spec['targets']['SizeProbe']['dependencies'] = [{'package': 'LaTeXMobile'}]
        spec['targets']['SizeProbe']['settings']['base']['SWIFT_ACTIVE_COMPILATION_CONDITIONS'] = 'WITH_LATEX'
    config = work / 'project.json'
    config.write_text(json.dumps(spec, indent=2))
    with (work / 'build.log').open('w') as log:
        subprocess.run([xcodegen, 'generate', '--spec', str(config)], check=True, stdout=log, stderr=log)
        subprocess.run(['xcodebuild', '-project', str(work / 'SizeProbe.xcodeproj'), '-scheme', 'SizeProbe',
                        '-configuration', 'Release', '-sdk', 'iphoneos', '-destination', 'generic/platform=iOS',
                        '-derivedDataPath', str(work / 'DerivedData'), 'build'], check=True, stdout=log, stderr=log)
    app = work / 'DerivedData/Build/Products/Release-iphoneos/SizeProbe.app'
    executable = app / 'SizeProbe'
    # Match the stripped executable shipped in an app, rather than debug/link symbols.
    subprocess.run(['xcrun', 'strip', '-S', str(executable)], check=True)
    assert subprocess.check_output(['xcrun', 'lipo', '-archs', str(executable)], text=True).strip() == 'arm64'
    files = sorted(p for p in app.rglob('*') if p.is_file())
    archive = DIST / f'{profile}.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for file in files:
            info = zipfile.ZipInfo('Payload/SizeProbe.app/' + file.relative_to(app).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            with file.open('rb') as source, output.open(info, 'w') as target:
                shutil.copyfileobj(source, target, 64 * 1024)
    record = {'profile': profile, 'app_bytes': sum(p.stat().st_size for p in files),
              'zip_bytes': archive.stat().st_size, 'executable_bytes': executable.stat().st_size,
              'zip_sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
    if profile != 'baseline':
        record['app_increase_bytes'] = record['app_bytes'] - records[0]['app_bytes']
        record['zip_increase_bytes'] = record['zip_bytes'] - records[0]['zip_bytes']
    records.append(record)
    print(profile, record, flush=True)
metadata = {'schema': 1, 'xcode': subprocess.check_output(['xcodebuild', '-version'], text=True).strip(),
            'architecture': 'arm64', 'configuration': 'Release', 'signed': False, 'records': records}
(ROOT / 'dist/ios-sizes.json').write_text(json.dumps(metadata, indent=2) + '\n')
write_report(list((ROOT / 'dist/aar').glob('*.aar')), ROOT / 'SIZES.md', ROOT / 'dist/sizes.json',
             ROOT / 'dist/aar-splits', ROOT / 'dist/ios-sizes.json')
