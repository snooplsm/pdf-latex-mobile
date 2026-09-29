#!/usr/bin/env python3
"""Reset per-engine font-id caches under Tectonic's global execution lock."""
import hashlib,json,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[2]
source=next((Path.home()/'.cargo/registry/src').glob('*/tectonic_xetex_layout-0.3.4'))
dest=root/'.build/xetex-native-vendor/layout'
if dest.exists():raise SystemExit('Layout vendor directory exists; refusing overwrite')
shutil.copytree(source,dest)
p=dest/'src/c_api.rs';p.write_text(p.read_text()+'''
/// Clear data indexed by TeX font numbers, which are reused by every engine run.
pub(crate) fn reset_engine_caches() {
    GLYPH_BOXES.lock().unwrap().clear();
    LEFT_PROT.lock().unwrap().clear();
    RIGHT_PROT.lock().unwrap().clear();
}
''')
p=dest/'src/lib.rs';p.write_text(p.read_text()+'''
/// Reset caches for a new XeTeX run. Call only while holding the engine global lock.
pub fn reset_engine_caches() { c_api::reset_engine_caches(); }
''')
engine=root/'.build/xetex-native-vendor/engine/src/lib.rs';s=engine.read_text()
needle='        launcher.with_global_lock(|state| {'
assert s.count(needle)==1
s=s.replace(needle,needle+'\n            tectonic_xetex_layout::reset_engine_caches();')
engine.write_text(s)
(dest/'PROVENANCE.json').write_text(json.dumps({'upstream':'tectonic_xetex_layout 0.3.4','license':'MIT','change':'Clear font-id indexed glyph bounds and protrusion caches before every XeTeX run; invoked under global lock','original_c_api_sha256':hashlib.sha256((source/'src/c_api.rs').read_bytes()).hexdigest(),'patched_c_api_sha256':hashlib.sha256((dest/'src/c_api.rs').read_bytes()).hexdigest(),'patched_engine_sha256':hashlib.sha256(engine.read_bytes()).hexdigest()},indent=2)+'\n')
print(dest)
