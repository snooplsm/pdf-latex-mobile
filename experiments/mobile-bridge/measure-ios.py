#!/usr/bin/env python3
"""Reuse the production size probe against an isolated replacement framework/bundle."""
import argparse,os,shutil,subprocess
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--stage',type=Path,required=True);args=parser.parse_args()
root=Path(__file__).resolve().parents[2];stage=args.stage.resolve()
source=(root/'tools/ios-sizes.py').read_text()
needle="for profile in ('baseline', 'tiny', 'small', 'balanced', 'full'):"
assert source.count(needle)==1
source=source.replace(needle,"for profile in ('baseline', 'full'):")
# Keep measurements within the staged tree and omit the aggregate release report.
source=source[:source.index('\nwrite_report(')]+'\n'
(stage/'tools/ios-sizes.py').write_text(source)
shutil.copy2(root/'tools/sizes.py',stage/'tools/sizes.py')
env=os.environ.copy();env['PATH']=str(Path.home()/'.local/bin')+os.pathsep+env['PATH']
subprocess.run(['python3',str(stage/'tools/ios-sizes.py')],env=env,check=True)
