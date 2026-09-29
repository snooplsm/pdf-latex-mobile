#!/usr/bin/env python3
"""Verify converted font identities, notices, and optional pre-rename outlines."""
import argparse,hashlib,json,re
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
parser=argparse.ArgumentParser()
parser.add_argument('--previous-dir',type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parents[2];out=root/'.build/krilla-fonts'
renames=json.loads((Path(__file__).parent/'font-renames.json').read_text())
license_text=(root/'experiments/licenses/AMSFonts-OFL.txt').read_text()
reserved=re.findall(r'"([^"]+)" is a Reserved Font Name',license_text)
assert (out/'AMSFonts-OFL.txt').read_text()==license_text
results=[]
for original,name in renames.items():
 path=out/(name+'.otf');font=TTFont(path)
 names=[r.toUnicode() for r in font['name'].names if r.nameID in (1,3,4,6,16,17,18,21,22)]
 cff=font['CFF '].cff;top=cff.topDictIndex[0]
 names+=list(cff.fontNames)+[top.FullName,top.FamilyName]
 assert all(not any(r.lower() in n.lower() for r in reserved) for n in names),(original,names)
 assert font['name'].getDebugName(0) and 'Open Font License' in font['name'].getDebugName(13)
 assert 'openfontlicense.org' in font['name'].getDebugName(14)
 assert not (out/('LMProbe-'+original+'.otf')).exists()
 if args.previous_dir:
  old=TTFont(args.previous_dir/('LMProbe-'+original+'.otf'))
  assert old.getGlyphOrder()==font.getGlyphOrder()
  assert old.getBestCmap()==font.getBestCmap()
  assert old['hmtx'].metrics==font['hmtx'].metrics
  before,after=old.getGlyphSet(),font.getGlyphSet()
  for gid in font.getGlyphOrder():
   a,b=RecordingPen(),RecordingPen();before[gid].draw(a);after[gid].draw(b)
   assert a.value==b.value,(original,gid)
 results.append({'source':original,'name':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'reserved_names_absent_from_identity':True,'notices_present':True,'outlines_cmap_metrics_unchanged':bool(args.previous_dir)})
(root/'.build/converted-font-check.json').write_text(json.dumps(results,indent=2)+'\n')
print(f'{len(results)} converted fonts verified')
