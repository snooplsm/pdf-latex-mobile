#!/usr/bin/env python3
"""Build-time Type 1 -> CFF OpenType conversion (fonttools 4.60.2).

Preserves cubic outlines but does not preserve Type 1 hints. No runtime Python.
Generated fonts have distinct names; original notices stay in the provenance.
"""
import argparse,hashlib,json,shutil,re
from pathlib import Path
from fontTools import t1Lib,agl
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.boundsPen import BoundsPen

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source",type=Path,required=True)
parser.add_argument("--output",type=Path,required=True)
args=parser.parse_args();source=args.source.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
renames=json.loads((root/'crates/xdv-renderer/font-renames.json').read_text())
licenses=root/'experiments/licenses'
reserved=re.findall(r'"([^"]+)" is a Reserved Font Name', (licenses/'AMSFonts-OFL.txt').read_text())
assert all(not any(r.lower() in name.lower() for r in reserved) for name in renames.values())
provenance=json.loads((licenses/'amsfonts-provenance.json').read_text())
shutil.copy2(licenses/'AMSFonts-OFL.txt',out/'AMSFonts-OFL.txt')
for ext in ('*.otf','*.tfm'):
    for p in source.glob(ext):
        if p.resolve() != (out/p.name).resolve():shutil.copy2(p,out/p.name)
for path in sorted(source.glob('*.pfb')):
    if hashlib.sha256(path.read_bytes()).hexdigest()!=provenance['verified_identical_files'].get(path.name):
        raise ValueError(f'{path.name}: source differs from the verified AMSFonts distribution')
    font=t1Lib.T1Font(str(path));font.parse()
    if font['FontMatrix'] != [.001,0,0,.001,0,0]:raise ValueError('Unsupported font matrix')
    glyphs=font['CharStrings'];order=['.notdef']+sorted(n for n in glyphs if n!='.notdef')
    charstrings={};metrics={}
    for name in order:
        cs=glyphs[name];bounds=BoundsPen(glyphs);cs.draw(bounds)
        pen=T2CharStringPen(cs.width,glyphs,roundTolerance=0)
        cs.draw(pen);charstrings[name]=pen.getCharString()
        metrics[name]=(round(cs.width),round(bounds.bounds[0]) if bounds.bounds else 0)
    mapping=[];cmap={}
    for code,name in enumerate(font['Encoding']):
        if name=='.notdef':continue
        text=agl.toUnicode(name)
        if not text:
            for suffix in ('display','text'):
                if name.endswith(suffix):text=agl.toUnicode(name[:-len(suffix)])
        mapping.append({'code':code,'gid':order.index(name),'text':text})
        if len(text)==1:cmap.setdefault(ord(text),name)
    fb=FontBuilder(1000,isTTF=False);fb.setupGlyphOrder(order);fb.setupCharacterMap(cmap)
    psname=renames[path.stem]
    fb.setupCFF(psname,{'FullName':psname,'FamilyName':psname,'Weight':'Regular','Notice':font['FontInfo'].get('Notice','')},charstrings,{})
    fb.setupHorizontalMetrics(metrics)
    bbox=font['FontBBox'];asc=max(0,bbox[3]);desc=min(0,bbox[1])
    fb.setupHorizontalHeader(ascent=asc,descent=desc)
    fb.setupNameTable({'familyName':psname,'styleName':'Regular','psName':psname,'fullName':psname,'uniqueFontIdentifier':psname,'version':'Version 0.1','copyright':font['FontInfo'].get('Notice','')})
    fb.font['name'].setName('Licensed under the SIL Open Font License 1.1. See accompanying AMSFonts-OFL.txt.',13,3,1,0x409)
    fb.font['name'].setName('https://openfontlicense.org/open-font-license-official-text/',14,3,1,0x409)
    fb.setupOS2(sTypoAscender=asc,sTypoDescender=desc,usWinAscent=asc,usWinDescent=-desc)
    fb.setupPost();fb.font['head'].created=fb.font['head'].modified=2082844800
    fb.font.recalcTimestamp=False
    fb.save(out/(psname+'.otf'))
    (out/(path.stem+'.encoding.json')).write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
    (out/(path.stem+'.provenance.json')).write_text(json.dumps({'source':path.name,'generated_font_name':psname,'license':'OFL-1.1','sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'font_info':font['FontInfo'],'conversion':'fonttools 4.60.2; cubic outlines, no Type 1 hints'},indent=2)+'\n')
    # Remove the obsolete experimental name so it cannot enter a new bundle.
    (out/('LMProbe-'+path.stem+'.otf')).unlink(missing_ok=True)
    print(path.name,'->',psname+'.otf')
