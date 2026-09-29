#!/usr/bin/env python3
"""Inventory exact embedded TECkit sources and their integration dependencies."""
import hashlib,json,re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
registry=Path.home()/'.cargo/registry/src'
engine=root/'.build/xetex-native-vendor/engine'
upstream=next(registry.glob('*/tectonic_engine_xetex-0.5.3'))
provenance=json.loads((root/'experiments/licenses/teckit-provenance.json').read_text())
expected={r['vendored'] for r in provenance['source_comparisons']}
actual={p.name for p in (engine/'xetex').glob('teckit-*') if p.is_file()}
assert actual==expected,('TECkit file set changed',sorted(actual^expected))
records=[]
for name in sorted(actual):
 p=engine/'xetex'/name;data=p.read_bytes();original=upstream/'xetex'/name
 records.append({'path':'xetex/'+name,'sha256':hashlib.sha256(data).hexdigest(),'identical_to_published_xetex_crate':data==original.read_bytes(),'local_includes':re.findall(r'^\s*#include\s*"([^"]+)"',data.decode(),re.M)})
assert all(r['identical_to_published_xetex_crate'] for r in records),'New TECkit modification needs attribution'
build=(engine/'build.rs').read_text();assert 'xetex/teckit-Engine.cpp' in build
bridges=[]
for name,version in [('tectonic_bridge_core','0.5.3'),('tectonic_bridge_flate','0.1.10')]:
 source=next(registry.glob('*/'+name+'-'+version))
 header=next(source.rglob(name+'.h'))
 bridges.append({'crate':name,'version':version,'header':str(header.relative_to(source)),'sha256':hashlib.sha256(header.read_bytes()).hexdigest()})
result={'scope':'Source inventory and CPL distribution preparation; not legal clearance or a final binary link-map audit','license_options':'CPL-0.5-or-later OR LGPL-2.1-or-later','evaluated_path':'CPL 0.5, permitted by the pinned upstream licensing statement; final release choice pending','sources':records,'integration_dependencies':bridges,'cpl_distribution_work':{'retain_copyright_and_license':'Included in review archive','provide_exact_source':'Included in review archive; public versioned release attachment still required','identify_changes':'Embedded TECkit files are unchanged from published XeTeX crate; upstream adaptations recorded separately','object_code_terms':'Release notice/license terms still need integration and review against section 3','commercial_distribution':'Section 4 obligations still need review','program_boundary':'Embedded integration and scope of covered contributions remain to be reviewed; do not infer closed-source clearance from archive presence'}}
out=root/'experiments/licenses/teckit-distribution-review.json';out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'teckit_files':len(records),'unchanged_from_xetex':True,'bridge_crates':len(bridges),'report':str(out)}))
