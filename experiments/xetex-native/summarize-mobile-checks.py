#!/usr/bin/env python3
"""Require complete matching native-process results on host, Android and iOS."""
import argparse,hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];folder=root/'.build/combined-pipeline'
required={'core','text','math','graphics','diagrams','fonts','languages','bibliography','invoice','invoice-png','multipage'}|{'jpeg-'+n for n in ('default','dpi72','dpi300','asymmetric','progressive')}
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--include-colors-and-pdf-pages',action='store_true')
args=parser.parse_args()
if args.include_colors_and_pdf_pages:
 required|={'color-'+n for n in ('named','fractional','nested','special-cmyk','special-rgb','multipage')}
 required|={'pdf-page-'+n for n in ('default','first','second','third','no-group','isolated','nonisolated','knockout')}
reports={platform:json.loads((folder/platform/'result.json').read_text()) for platform in ('host','android','ios')}
reference=None
for platform,report in reports.items():
 rows={r['example']:r for r in report['results']}
 assert set(rows)==required,(platform,'incomplete cases')
 assert all(r['match'] and r['actual_sha256']==[r['expected_sha256']]*2 for r in rows.values()),platform
 inputs={name:(r['source_sha256'],r['asset_sha256'],r['expected_sha256']) for name,r in rows.items()}
 if reference is None:reference=(inputs,report['font_sha256'])
 assert reference==(inputs,report['font_sha256']),(platform,'inputs/references differ')
 assert not any(n.startswith('LMProbe-') for n in report['font_sha256']),(platform,'obsolete font identity')
assert reports['host']['atomic_output_failure_check']
summary={'scope':'ARM64 native processes, not Kotlin/Swift wrappers or original-engine pixel parity','documents_per_platform':len(required),'runs_per_document':2,'matching_pdf_hashes':len(required)*2*len(reports),'reports':{p:hashlib.sha256((folder/p/'result.json').read_bytes()).hexdigest() for p in reports}}
(folder/'latest-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
