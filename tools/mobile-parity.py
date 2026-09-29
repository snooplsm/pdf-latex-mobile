#!/usr/bin/env python3
"""Build both mobile targets, compile the same invoice twice, and compare raw PDF SHA-256."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

def run(command, *, env=None, log=None):
    result = subprocess.run([str(x) for x in command], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if log:
        Path(log).write_bytes(result.stdout)
    if result.returncode:
        raise RuntimeError(f'Command failed: {command}\n{result.stdout.decode(errors="replace")[-5000:]}')
    return result.stdout.decode()

def compare(paths):
    hashes = {}
    for name, path in paths.items():
        data = path.read_bytes()
        if not data.startswith(b'%PDF-') or not data.rstrip().endswith(b'%%EOF'):
            raise ValueError(f'{name}: missing or invalid PDF')
        hashes[name] = hashlib.sha256(data).hexdigest()
    if len(hashes) != 4 or len(set(hashes.values())) != 1:
        raise ValueError('PDF hashes differ: ' + json.dumps(hashes, indent=2))
    return hashes

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ios-device', help='Simulator UDID; defaults to a booted iPhone or first available iPhone')
    parser.add_argument('--android-serial', help='Emulator serial; defaults to a running emulator')
    parser.add_argument('--avd', help='AVD to boot if no emulator is running')
    parser.add_argument('--profile', choices=['balanced', 'full'], default='balanced')
    parser.add_argument('--skip-native-build', action='store_true', help='Reuse already-built native libraries')
    args = parser.parse_args()
    env = os.environ.copy()
    sdk = Path(env.get('ANDROID_HOME', Path.home() / 'Library/Android/sdk'))
    env['ANDROID_HOME'] = str(sdk)
    env.setdefault('ANDROID_NDK_HOME', str(sdk / 'ndk/29.0.14206865'))
    env['PATH'] = str(ROOT / '.build/host/bin') + os.pathsep + env['PATH']
    adb = sdk / 'platform-tools/adb'
    destination = ROOT / 'dist/parity'
    destination.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='run-', dir=destination))
    print(f'Artifacts and logs: {output}', flush=True)
    emulator = None
    booted_ios = False
    ios = None
    try:
        devices = json.loads(run(['xcrun', 'simctl', 'list', 'devices', 'available', '--json']))['devices']
        phones = [d for group in devices.values() for d in group if 'iPhone' in d['name']]
        selected = next((d for d in phones if d['udid'] == args.ios_device), None) if args.ios_device else next((d for d in phones if d['state'] == 'Booted'), phones[0] if phones else None)
        if selected is None:
            raise RuntimeError('No matching iPhone simulator; install an iOS runtime in Xcode')
        ios = selected['udid']
        if selected['state'] != 'Booted':
            run(['xcrun', 'simctl', 'boot', ios])
            booted_ios = True
        run(['xcrun', 'simctl', 'bootstatus', ios, '-b'], log=output / 'ios-boot.log')
        serial = args.android_serial
        if not serial:
            serial = next((line.split()[0] for line in run([adb, 'devices']).splitlines()[1:]
                           if line.startswith('emulator-') and line.split()[-1] == 'device'), None)
        if not serial:
            avds = run([sdk / 'emulator/emulator', '-list-avds']).splitlines()
            avd = args.avd or (avds[0] if avds else None)
            if not avd:
                raise RuntimeError('No Android AVD; create one in Android Studio or pass --avd')
            serial = 'emulator-5580'
            emulator = subprocess.Popen([str(sdk / 'emulator/emulator'), '-avd', avd, '-port', '5580', '-no-window', '-no-audio', '-no-snapshot-save'], stdout=(output / 'android-boot.log').open('wb'), stderr=subprocess.STDOUT)
        if not serial.startswith('emulator-'):
            raise RuntimeError('Use an Android emulator, not a physical device')
        deadline = time.monotonic() + 180
        while True:
            ready = subprocess.run([str(adb), '-s', serial, 'shell', 'getprop', 'sys.boot_completed'], capture_output=True)
            if ready.stdout.strip() == b'1':
                break
            if time.monotonic() >= deadline:
                raise RuntimeError('Android emulator boot timed out')
            time.sleep(2)
        abi = run([adb, '-s', serial, 'shell', 'getprop', 'ro.product.cpu.abi']).strip()
        native = 'full' if args.profile == 'full' else 'compact'
        if not args.skip_native_build:
            print(f'Building native libraries ({abi}, iOS; {native})…', flush=True)
            run(['bash', 'tools/build-native.sh', 'android'], env={**env, 'ABIS': abi, 'NATIVE_PROFILES': native}, log=output / 'android-native.log')
            run(['bash', 'tools/build-native.sh', 'ios'], env={**env, 'NATIVE_PROFILES': native}, log=output / 'ios-native.log')
        print('Building and testing Android invoice…', flush=True)
        run(['android/gradlew', '-p', 'android', f'-Pabis={abi}', f':library:assemble{args.profile.capitalize()}DebugAndroidTest'], env=env, log=output / 'android-build.log')
        apk = ROOT / f'android/library/build/outputs/apk/androidTest/{args.profile}/debug/library-{args.profile}-debug-androidTest.apk'
        run([adb, '-s', serial, 'install', '-r', apk], log=output / 'android-install.log')
        manifests = list((ROOT / 'android/library/build/intermediates').glob(f'**/{args.profile}DebugAndroidTest/**/AndroidManifest.xml'))
        manifest = next(ET.parse(p).getroot() for p in manifests if ET.parse(p).getroot().find('instrumentation') is not None)
        package = manifest.attrib['package']
        namespace = '{http://schemas.android.com/apk/res/android}'
        runner = manifest.find('instrumentation').attrib[namespace + 'name']
        result = run([adb, '-s', serial, 'shell', 'am', 'instrument', '-w', '-r', '-e', 'class', 'org.latexmobile.CompileTest#exportsParityInvoice', f'{package}/{runner}'], log=output / 'android-test.log')
        if 'OK (1 test)' not in result or 'FAILURES' in result:
            raise RuntimeError('Android invoice test failed; see android-test.log')
        paths = {}
        for index in (1, 2):
            path = output / f'android-{index}.pdf'
            with path.open('wb') as stream:
                subprocess.run([str(adb), '-s', serial, 'exec-out', 'run-as', package, 'cat', f'files/parity/invoice-{index}.pdf'], stdout=stream, check=True)
            paths[f'android-{index}'] = path
        print('Building and testing iOS invoice…', flush=True)
        run(['python3', 'tools/prepare-ios.py', args.profile], log=output / 'ios-prepare.log')
        xcodegen = shutil.which('xcodegen') or ROOT / '.build/xcodegen/bin/xcodegen'
        run([xcodegen, 'generate', '--spec', 'ios/project.yml'], log=output / 'ios-project.log')
        ios_result = run(['xcodebuild', '-project', 'ios/LaTeXMobileHarness.xcodeproj', '-scheme', 'Harness',
             '-destination', f'platform=iOS Simulator,id={ios}', '-parallel-testing-enabled', 'NO',
             '-only-testing:HarnessTests/CompileTests/testExportsParityInvoice', 'test'], log=output / 'ios-test.log')
        if 'Executed 1 test' not in ios_result or 'testExportsParityInvoice' not in ios_result:
            raise RuntimeError('iOS parity test did not run; see ios-test.log')
        container = Path(run(['xcrun', 'simctl', 'get_app_container', ios, 'org.latexmobile.harness', 'data']).strip())
        for index in (1, 2):
            path = output / f'ios-{index}.pdf'
            shutil.copyfile(container / f'Documents/parity/invoice-{index}.pdf', path)
            paths[f'ios-{index}'] = path
        hashes = compare(paths)
        report = {'profile': args.profile, 'android_abi': abi, 'ios_device': ios, 'hashes': hashes,
                  'source_sha256': hashlib.sha256((ROOT / 'examples/invoice.tex').read_bytes()).hexdigest(),
                  'logo_sha256': hashlib.sha256((ROOT / 'examples/invoice.assets/logo.pdf').read_bytes()).hexdigest()}
        (output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
        print('PASS: all four raw PDF hashes match: ' + next(iter(hashes.values())), flush=True)
    finally:
        if emulator:
            subprocess.run([str(adb), '-s', 'emulator-5580', 'emu', 'kill'], capture_output=True)
        if booted_ios:
            subprocess.run(['xcrun', 'simctl', 'shutdown', ios], capture_output=True)

if __name__ == '__main__':
    main()
