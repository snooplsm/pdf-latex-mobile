#!/usr/bin/env python3
"""Create isolated patched sources from exact downloaded registry versions.

Does not modify the Cargo registry or production workspace. This is a research
build, not a completed licensing audit or releasable replacement.
"""
from pathlib import Path
import re
import shutil

root=Path(__file__).resolve().parents[2]
here=Path(__file__).resolve().parent
registry=Path.home()/'.cargo/registry/src'
out=root/'.build/xetex-native-vendor'
for version,destination in [('tectonic-0.17.0','tectonic'),('tectonic_engine_xetex-0.5.3','engine')]:
    matches=list(registry.glob('*/'+version))
    if len(matches)!=1: raise RuntimeError(f'Expected one registry source for {version}')
    dest=out/destination
    if dest.exists():raise RuntimeError(f'{dest} already exists; inspect before recreating')
    shutil.copytree(matches[0],dest)

def change(path,old,new):
    p=out/path;s=p.read_text()
    if old not in s:raise RuntimeError(f'Patch anchor absent in {path}: {old[:50]}')
    p.write_text(s.replace(old,new))
def dependency(path,name):
    p=out/path;s=p.read_text()
    s,n=re.subn(r'\[dependencies\.'+re.escape(name)+r'\]\n.*?(?=\n\[|\Z)','',s,flags=re.S)
    if n!=1:raise RuntimeError(f'Expected dependency {name}')
    p.write_text(s)

dependency('tectonic/Cargo.toml','tectonic_engine_xdvipdfmx')
dependency('engine/Cargo.toml','tectonic_pdf_io')
change('tectonic/src/lib.rs','pub use crate::engines::xdvipdfmx::XdvipdfmxEngine;','')
change('tectonic/src/engines/mod.rs','pub mod xdvipdfmx;','')
change('tectonic/src/engines/mod.rs',', xdvipdfmx::XdvipdfmxEngine','')
change('tectonic/src/driver.rs',', XdvipdfmxEngine','')
p=out/'tectonic/src/driver.rs';s=p.read_text()
a=s.index('    fn xdvipdfmx_pass(');b=s.index('    fn spx2html_pass(',a)
s=s[:a]+'''    fn xdvipdfmx_pass(&mut self, _status: &mut dyn StatusBackend) -> Result<i32> {
        Err(Error::msg("legacy PDF backend removed; request XDV and render separately"))
    }

'''+s[b:];p.write_text(s)
change('engine/build.rs','    let pdfio_include_path = env::var("DEP_TECTONIC_PDF_IO_INCLUDE_PATH").unwrap();','')
change('engine/build.rs','''    for item in pdfio_include_path.split(';') {
        c_cfg.include(item);
        cxx_cfg.include(item);
    }
''','')
change('engine/src/lib.rs','    use tectonic_pdf_io as clipyrenamehack1;','    use crate::picture_metadata as clipyrenamehack1;')
with (out/'engine/src/lib.rs').open('a') as f:f.write('\nmod picture_metadata;\n')
shutil.copy2(here/'picture_metadata.rs',out/'engine/src/picture_metadata.rs')
with (out/'engine/Cargo.toml').open('a') as f:f.write('\n[dependencies.hayro-syntax]\nversion = "=0.7.2"\n\n[dependencies.png]\nversion = "=0.18.1"\n\n[dependencies.zune-jpeg]\nversion = "=0.5.15"\n')
p=out/'engine/xetex/xetex-ini.c';s=p.read_text();s=re.sub(r'^#include "dpx-pdfobj.h".*\n','',s,flags=re.M).replace('pdf_files_init();','/* Image metadata parser is stateless. */').replace('pdf_files_close();','/* Image metadata parser is stateless. */');p.write_text(s)
p=out/'engine/xetex/xetex-pic.c';s=p.read_text();s=re.sub(r'^#include "dpx-[^"\n]+"\n','',s,flags=re.M)
a=s.index('int\ncount_pdf_file_pages');b=s.index('/*\n  pdfBoxType',a)
s=s[:a]+(here/'picture_helpers.c').read_text()+'\n'+s[b:];p.write_text(s)
print(out)

# Record provenance and exact local modifications without changing upstream notices.
import hashlib
import json
provenance={'upstream':{'tectonic':'0.17.0','tectonic_engine_xetex':'0.5.3'},'patch_sha256':{}}
for filename in ('prepare.py','picture_helpers.c','picture_metadata.rs'):
    provenance['patch_sha256'][filename]=hashlib.sha256((here/filename).read_bytes()).hexdigest()
(out/'PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n')
