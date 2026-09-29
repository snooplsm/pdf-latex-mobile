#!/usr/bin/env python3
"""Host backend comparison. Requires Pillow, pypdf and pdftoppm.

Measurements are evidence, not a full replacement acceptance gate.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile
from PIL import Image, ImageChops
from pypdf import PdfReader

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path, default=root / '.build/xdv-probe')
args = parser.parse_args()
xdv_dir = root / '.build/xdv-probe'
out = args.output_dir.resolve()
out.mkdir(parents=True, exist_ok=True)
backend = root / '.build/krilla-xdv-target/release/krilla-xdv-probe'
results = []
# Keep accepted coverage explicit: a newly failing case must not silently vanish
# from the downstream mobile checks, which consume the successful case list.
required_cases = {'core', 'text', 'math', 'fonts', 'languages', 'bibliography', 'graphics',
                  'diagrams', 'invoice', 'invoice-png', 'multipage'}
(out/"krilla-comparison.json").unlink(missing_ok=True)
for xdv in sorted(xdv_dir.glob('*.xdv')):
    name = xdv.stem
    source_name = "invoice" if name == "invoice-png" else name
    source = root/'examples'/(source_name+'.tex')
    if not source.exists(): source = root/'experiments/krilla-xdv/fixtures'/(source_name+'.tex')
    candidate = out / (name + '-krilla.pdf')
    candidate.unlink(missing_ok=True)
    cmd = [str(backend), str(xdv), str(root/'.build/krilla-fonts'), str(candidate), str(root/"examples"/(source_name+".assets"))]
    run = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    record = {'example': name, 'xdv_sha256': hashlib.sha256(xdv.read_bytes()).hexdigest(), 'compiled': run.returncode == 0}
    if run.returncode:
        record['error'] = run.stderr.strip()
        results.append(record)
        continue
    first = hashlib.sha256(candidate.read_bytes()).hexdigest()
    subprocess.run(cmd, check=True, timeout=60)
    record['repeat_hash_matches'] = first == hashlib.sha256(candidate.read_bytes()).hexdigest()
    baseline = out / (name + '-baseline.pdf')
    request = {'source': source.read_text(), 'bundle_path': str(root/'dist/bundles/full/texbundle'), 'output_path': str(baseline)}
    if name == "invoice-png": request["source"] = request["source"].replace("logo.pdf","logo.png")
    assets = root/"examples"/(source_name+".assets")
    if assets.is_dir(): request["asset_files"] = {p.name:str(p) for p in assets.iterdir() if p.is_file()}
    baseline_run = subprocess.run([str(root/'target/release/lm-compile')], input=json.dumps(request), text=True, capture_output=True, timeout=60)
    if baseline_run.returncode: raise RuntimeError(f"{name}: {baseline_run.stdout} {baseline_run.stderr}")
    a,b = PdfReader(baseline),PdfReader(candidate)
    record['page_count_matches'] = len(a.pages) == len(b.pages)
    record['text_matches'] = [p.extract_text() for p in a.pages] == [p.extract_text() for p in b.pages]
    record['page_boxes_match'] = [list(p.mediabox) for p in a.pages] == [list(p.mediabox) for p in b.pages]
    record['baseline_page_count'] = len(a.pages)
    record['candidate_page_count'] = len(b.pages)
    record['raster_pages'] = []
    record['raster_dimensions_match'] = record['page_count_matches']
    for page in range(min(len(a.pages),len(b.pages))):
        images = []
        for path in (baseline,candidate):
            prefix = str(path.with_suffix('')) + (f'-page-{page+1}' if len(a.pages)>1 else '')
            subprocess.run(['pdftoppm','-r','144','-f',str(page+1),'-l',str(page+1),'-singlefile','-png',str(path),prefix],check=True,capture_output=True,timeout=60)
            with Image.open(prefix+'.png') as image: images.append(image.convert('RGB'))
        dimensions_match = images[0].size == images[1].size
        entry = {'page':page+1,'dimensions_match':dimensions_match}
        record['raster_dimensions_match'] &= dimensions_match
        if dimensions_match:
            delta=ImageChops.difference(*images)
            entry.update(different_pixels_144dpi=sum(v != (0,0,0) for v in delta.get_flattened_data()),
                         total_pixels=images[0].width*images[0].height,difference_bbox=delta.getbbox())
        record['raster_pages'].append(entry)
    if record['raster_dimensions_match']:
        record['different_pixels_144dpi']=sum(p['different_pixels_144dpi'] for p in record['raster_pages'])
        record['total_pixels']=sum(p['total_pixels'] for p in record['raster_pages'])
        if len(record['raster_pages'])==1:record['difference_bbox']=record['raster_pages'][0]['difference_bbox']
    results.append(record)
buffer=io.BytesIO()
with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    z.write(backend,backend.name)
report={'backend_sha256':hashlib.sha256(backend.read_bytes()).hexdigest(),'platform':'macOS ARM64 backend CLI only; excludes XeTeX and fonts', 'binary_mb':round(backend.stat().st_size/1e6,2),'zip_mb':round(len(buffer.getvalue())/1e6,2),'results':results}
(out/'krilla-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
by_name = {case['example']: case for case in results}
checks = ('compiled', 'repeat_hash_matches', 'page_count_matches',
          'text_matches', 'page_boxes_match', 'raster_dimensions_match')
failures = [name for name in sorted(required_cases)
            if not all(by_name.get(name, {}).get(check, False) for check in checks)]
# Exact raster parity has been established for these cases; preserve it.
failures += [name for name in ('bibliography', 'languages', 'diagrams', 'math')
             if by_name.get(name, {}).get('different_pixels_144dpi') != 0]
if failures:
    raise SystemExit('Backend regression: ' + ', '.join(sorted(set(failures))))
