#!/usr/bin/env python3
"""Run all existing wrapper tests after staging and the invoice parity check."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--android-serial',default='emulator-5554')
parser.add_argument('--ios-device',required=True)
parser.add_argument('--stage',type=Path)
parser.add_argument('--reference-pdf',type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parents[2];stage=(args.stage or root/'.build/replacement-harness').resolve()
out=stage/'wrapper-tests';out.mkdir(exist_ok=True)
(out/'result.json').unlink(missing_ok=True)
def run(name,command,success):
 with (out/(name+'.log')).open('w') as stream:
  result=subprocess.run(command,cwd=stage,stdout=stream,stderr=subprocess.STDOUT)
 text=(out/(name+'.log')).read_text()
 assert result.returncode==0 and success in text,(name,result.returncode,text[-3000:])
 print(name,success,flush=True)
sdk=Path(os.environ.get('ANDROID_HOME',str(Path.home()/'Library/Android/sdk')))
run('android',[str(sdk/'platform-tools/adb'),'-s',args.android_serial,'shell','am','instrument','-w','-r','-e','class','org.latexmobile.CompileTest','org.latexmobile.replacement.test/androidx.test.runner.AndroidJUnitRunner'],'OK (6 tests)')
run('ios',['xcodebuild','-project','ios/LaTeXMobileHarness.xcodeproj','-scheme','Harness','-destination',f'platform=iOS Simulator,id={args.ios_device}','-parallel-testing-enabled','NO','-only-testing:HarnessTests/CompileTests','test'],'Executed 4 tests, with 0 failures')
reports=sorted((stage/'dist/parity').glob('run-*/result.json'),key=lambda p:p.stat().st_mtime)
assert reports,'Run the invoice parity script first'
parity=json.loads(reports[-1].read_text())
expected=hashlib.sha256((args.reference_pdf or root/'.build/xdv-probe/invoice-krilla.pdf').read_bytes()).hexdigest()
assert all(h==expected for h in parity['hashes'].values()),parity
manifest=stage/'dist/bundles/full/texbundle/manifest.json'
features=json.loads(manifest.read_text())['features']
(out/'result.json').write_text(json.dumps({'fixture_features':features,'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'android_tests':6,'ios_tests':4,'invoice_sha256':expected,'parity_report':str(reports[-1]),'scope':'existing full-profile wrapper tests; ARM64 emulator/simulator'},indent=2)+'\n')
print('All wrapper tests and reference invoice hashes passed',flush=True)
