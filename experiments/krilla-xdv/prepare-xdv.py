#!/usr/bin/env python3
"""Create a local MIT XDV parser fork with positioned traditional characters."""
from pathlib import Path
import hashlib
import json
import shutil

root=Path(__file__).resolve().parents[2]
src=next((Path.home()/'.cargo/registry/src').glob('*/tectonic_xdv-0.3.0'))
dest=root/'.build/xdv-parser-vendor'
if dest.exists():raise SystemExit('Vendor directory exists; refusing overwrite')
shutil.copytree(src,dest)
p=dest/'src/lib.rs';s=p.read_text()
def replace(old,new):
    global s
    if s.count(old)!=1:raise RuntimeError(f'Patch context count {s.count(old)}: {old[:60]}')
    s=s.replace(old,new)
replace('    /// Handle a sequence of characters without intervening commands', '''    /// Define a traditional TeX font with its scaled size in DVI units.
    fn handle_define_font(&mut self, _number: i32, _checksum: u32, _size: u32,
        _design: u32, _area: &str, _name: &str) -> Result<(), Self::Error> { Ok(()) }

    /// Render a traditional character at its baseline; return its TFM advance.
    fn handle_character(&mut self, font: i32, character: i32, _x: i32, _y: i32)
        -> Result<i32, Self::Error> {
        self.handle_char_run(font, &[character])?;
        Ok(0)
    }

    /// Handle a sequence of characters without intervening commands''')
start=s.index('        let _font_num =',s.index('    fn do_define_font('))
end=s.index('        Ok(())',start)
s=s[:start]+'''        let font_num = cursor.get_compact_i32_smpos(opcode - Opcode::DefineFont1 as u8)?;
        let checksum = cursor.get_u32()?;
        let scale = cursor.get_u32()?;
        let design = cursor.get_u32()?;
        let area_len = cursor.get_u8()?;
        let name_len = cursor.get_u8()?;
        let area = cursor.get_slice(area_len as usize)?.to_vec();
        let name = cursor.get_slice(name_len as usize)?.to_vec();
        let area = std::str::from_utf8(&area).map_err(|_| XdvError::FromUTF8(cursor.global_offset()).into_internal())?;
        let name = std::str::from_utf8(&name).map_err(|_| XdvError::FromUTF8(cursor.global_offset()).into_internal())?;
        self.events.handle_define_font(font_num, checksum, scale, design, area, name)?;
''' +s[end:]
replace('        self.cur_char_run.push(i32::from(char_num));','        self.positioned_character(i32::from(char_num), cursor)?;')
replace('        self.cur_char_run.push(char_num);','        self.positioned_character(char_num, cursor)?;')
needle='    fn do_set_glyphs('
replace(needle,'''    fn positioned_character(&mut self, character: i32, cursor: &Cursor<T>) -> InternalResult<(), T::Error> {
        let state = self.stack.last_mut().unwrap();
        let advance = self.events.handle_character(self.cur_font_num, character, state.h, state.v)?;
        state.h = state.h.checked_add(advance)
            .ok_or_else(|| XdvError::Malformed(cursor.global_offset()).into_internal())?;
        Ok(())
    }

'''+needle)
p.write_text(s)
(dest/'PROVENANCE.json').write_text(json.dumps({'upstream':'tectonic_xdv 0.3.0','license':'MIT','original_sha256':hashlib.sha256((src/'src/lib.rs').read_bytes()).hexdigest(),'patched_sha256':hashlib.sha256(p.read_bytes()).hexdigest()},indent=2)+'\n')
print(dest)
