#!/usr/bin/env python3
"""Local MIT/Apache Krilla extension: preserve normalized RGB/CMYK components."""
from pathlib import Path
import shutil,json,hashlib
from hayro_page_groups import patch as patch_page_groups
from krilla_cmyk import patch as patch_cmyk
root=Path(__file__).resolve().parents[2]
source=next((Path.home()/'.cargo/registry/src').glob('*/krilla-0.8.2'))
dest=root/'.build/krilla-vendor'
if dest.exists():raise SystemExit('Vendor directory exists; refusing overwrite')
shutil.copytree(source,dest)
p=dest/'src/graphics/color.rs';text=p.read_text();start=text.index('pub mod rgb {');end=text.index('/// Separation (spot) colors.',start)
s=text[start:end]
s=s.replace('pub struct Color(pub(crate) u8, pub(crate) u8, pub(crate) u8);','pub struct Color(u32, u32, u32);')
s=s.replace('Color(red, green, blue)','Self::new_normalized(red as f32 / 255.0, green as f32 / 255.0, blue as f32 / 255.0).unwrap()')
needle='        /// Create a new linear RGB color.'
s=s.replace(needle,'''        /// Create a color from finite normalized components without 8-bit quantization.
        pub fn new_normalized(red: f32, green: f32, blue: f32) -> Option<Self> {
            let bits = |v: f32| if v.is_finite() && (0.0..=1.0).contains(&v) {
                Some(if v == 0.0 { 0.0f32.to_bits() } else { v.to_bits() })
            } else { None };
            Some(Color(bits(red)?, bits(green)?, bits(blue)?))
        }

'''+needle)
for i in range(3):
 s=s.replace(f'            self.{i}\n',f'            (f32::from_bits(self.{i}) * 255.0).round() as u8\n')
 s=s.replace(f'self.{i} as f32 / 255.0',f'f32::from_bits(self.{i})')
p.write_text(patch_cmyk(text[:start]+s+text[end:]))
(dest/'PROVENANCE.json').write_text(json.dumps({'upstream':'krilla 0.8.2','license':'MIT OR Apache-2.0','source_sha256':hashlib.sha256((source/'src/graphics/color.rs').read_bytes()).hexdigest(),'patched_sha256':hashlib.sha256(p.read_bytes()).hexdigest()},indent=2)+'\n')

# Do not let another crate's flate2 features select a platform C compressor for PDFs.
manifest=dest/'Cargo.toml'
manifest.write_text(manifest.read_text().replace('[dependencies.flate2]\nversion = "1.1.0"','[dependencies.miniz_oxide]\nversion = "=0.8.9"'))
stream=dest/'src/stream.rs'
body=stream.read_text().replace('use flate2::write::ZlibEncoder;\n','').replace('use flate2::Compression;\n','')
a=body.index('    use std::io::Write;',body.index('pub(crate) fn deflate_encode('))
b=body.index('\n}',a)
body=body[:a]+'    miniz_oxide::deflate::compress_to_vec_zlib(data, 6)'+body[b:]
stream.write_text(body)


hayro_source=next((Path.home()/'.cargo/registry/src').glob('*/hayro-write-0.7.0'))
hayro=dest.parent/'hayro-write-vendor'
if hayro.exists():raise SystemExit('Hayro vendor directory exists; refusing overwrite')
shutil.copytree(hayro_source,hayro)
manifest=hayro/'Cargo.toml'
manifest.write_text(manifest.read_text().replace('[features]', '[features]\nxdvipdfmx-compatibility = []', 1).replace('[dependencies.flate2]\nversion = "1"','[dependencies.miniz_oxide]\nversion = "=0.8.9"'))
stream=hayro/'src/lib.rs'
body=stream.read_text().replace('use flate2::write::ZlibEncoder;\n','').replace('use flate2::Compression;\n','')
a=body.index('    use std::io::Write;',body.index('pub(crate) fn deflate_encode('));b=body.index('\n}',a)
stream.write_text(patch_page_groups(body[:a]+'    miniz_oxide::deflate::compress_to_vec_zlib(data, 6)'+body[b:]))
manifest=dest/'Cargo.toml'
manifest.write_text(manifest.read_text().replace('[dependencies.hayro-write]\nversion = "0.7.0"','[dependencies.hayro-write]\nversion = "0.7.0"\npath = "../hayro-write-vendor"\nfeatures = ["xdvipdfmx-compatibility"]'))
(hayro/'PROVENANCE.json').write_text(json.dumps({'upstream':'hayro-write 0.7.0','change':'Explicit miniz_oxide 0.8.9 level-6 compression; opt-in xdvipdfmx-compatible omission of imported page groups','source_sha256':hashlib.sha256((hayro_source/'src/lib.rs').read_bytes()).hexdigest(),'patched_sha256':hashlib.sha256(stream.read_bytes()).hexdigest()},indent=2)+'\n')

provenance=dest/'PROVENANCE.json'
record=json.loads(provenance.read_text())
record['additional_changes']={'src/stream.rs':'Explicit miniz_oxide 0.8.9 level-6 PDF stream compression; independent of flate2 feature unification','Cargo.toml':'Pinned miniz_oxide; Hayro xdvipdfmx-compatibility feature'}
record['patched_files_sha256']={f:hashlib.sha256((dest/f).read_bytes()).hexdigest() for f in ('src/graphics/color.rs','src/stream.rs','Cargo.toml')}
provenance.write_text(json.dumps(record,indent=2)+'\n')
print(dest)
