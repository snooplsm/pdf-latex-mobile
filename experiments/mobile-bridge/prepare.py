#!/usr/bin/env python3
"""Build an isolated copy of the existing public bridge with the replacement renderer."""
import hashlib,json,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[2]
source=root/'crates/latex-mobile';dest=root/'.build/mobile-bridge'
if dest.exists():raise SystemExit('Bridge directory exists; refusing overwrite')
(dest/'src').mkdir(parents=True)
original=(source/'src/lib.rs').read_text()
patched=original.replace('.output_format(OutputFormat::Pdf)','.output_format(OutputFormat::Xdv)')
old='''        let pdf = output
            .remove("main.pdf")
            .ok_or("engine did not produce main.pdf")?
            .data;'''
new='''        let xdv = output
            .remove("main.xdv")
            .ok_or("engine did not produce main.xdv")?
            .data;
        let pdf = krilla_xdv_probe::render(
            std::io::Cursor::new(xdv), &request.bundle_path, Some(scratch.path()),
        ).map_err(|e| format!("replacement renderer: {e:#}"))?;'''
assert patched.count(old)==1 and original.count('.output_format(OutputFormat::Pdf)')==1
patched=patched.replace(old,new);(dest/'src/lib.rs').write_text(patched)
manifest=(source/'Cargo.toml').read_text()+'''
[workspace]
[dependencies.krilla-xdv-probe]
path = "../../experiments/krilla-xdv"
[patch.crates-io]
tectonic = {path = "../xetex-native-vendor/tectonic"}
tectonic_engine_xetex = {path = "../xetex-native-vendor/engine"}
tectonic_xetex_layout = {path = "../xetex-native-vendor/layout"}
'''
manifest += '\n[profile.release]' + (root/'Cargo.toml').read_text().split('[profile.release]',1)[1]
(dest/'Cargo.toml').write_text(manifest)
shutil.copy2(root/'experiments/mobile-bridge/Cargo.lock',dest/'Cargo.lock')
shutil.copy2(root/'experiments/xetex-native/build.rs',dest/'build.rs')
(dest/'PROVENANCE.json').write_text(json.dumps({'source':'crates/latex-mobile/src/lib.rs','source_sha256':hashlib.sha256(original.encode()).hexdigest(),'patched_sha256':hashlib.sha256(patched.encode()).hexdigest(),'changes':['OutputFormat::Xdv','Render XDV through Krilla using fonts from bundle_path'],'scope':'experimental copy; production unchanged'},indent=2)+'\n')
print(dest)
