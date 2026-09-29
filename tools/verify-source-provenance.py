#!/usr/bin/env python3
"""Recheck pinned archives and byte-identical runtime mappings (not license clearance)."""
import argparse
import hashlib
import json
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / '.build/license-sources'
RECORDS = ROOT / 'experiments/licenses'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(bundle):
    checked = {}
    archives = set()

    def check_archive(path, expected):
        if digest(path.read_bytes()) != expected:
            raise ValueError(f'Archive hash mismatch: {path}')
        archives.add(str(path.relative_to(SOURCES)))

    def check_files(path, entries):
        if path.suffix == '.zip':
            archive = zipfile.ZipFile(path)
            read = archive.read
        else:
            archive = tarfile.open(path)
            read = lambda name: archive.extractfile(name).read()
        with archive:
            for entry in entries:
                name = entry['file']
                upstream = read(entry.get('archive_path', entry.get('upstream_path')))
                expected = entry.get('sha256', entry.get('upstream_sha256'))
                if digest(upstream) != expected:
                    raise ValueError(f'Upstream member mismatch: {name}')
                target = bundle / name
                if not target.exists():
                    continue  # Smaller profiles deliberately omit package files.
                if target.read_bytes() != upstream:
                    raise ValueError(f'Runtime source mismatch: {name}')
                checked[name] = expected

    for record, folder in [
        ('texlive-2021-package-provenance.json', 'texlive-2021-final'),
        ('texlive-2022-package-provenance.json', 'texlive-2022-final'),
        ('pattern-package-provenance.json', 'texlive-2021-patterns'),
    ]:
        for package in json.loads((RECORDS / record).read_text()):
            for archive in package['archives']:
                check_archive(SOURCES / folder / archive['file'], archive['sha256'])
            check_files(SOURCES / folder / (package['package'] + '.tar.xz'), package['exact_files'])

    pgf = json.loads((RECORDS / 'pgf-provenance.json').read_text())
    path = SOURCES / 'pgf-3.1.9a/pgf.tds.zip'
    check_archive(path, pgf['archive_sha256'])
    check_files(path, pgf['exact_files'])
    for package in json.loads((RECORDS / 'latex3-provenance.json').read_text()):
        path = SOURCES / ('latex3-' + package['release']) / (package['package'] + '.tds.zip')
        check_archive(path, package['archive_sha256'])
        check_files(path, package['exact_files'])

    base = json.loads((RECORDS / 'latex-base-provenance.json').read_text())
    packages = [dict(base, exact_files=[e for e in base['files'] if e['identical']])]
    packages += json.loads((RECORDS / 'latex-package-provenance.json').read_text())['packages']
    for package in packages:
        for archive in package['archives']:
            path = SOURCES / 'latex-2021-11-15-PL1' / archive['name']
            check_archive(path, archive['sha256'])
            if archive['name'].endswith('.tds.zip'):
                check_files(path, package['exact_files'])

    transformed = {}
    for record, key in [('hyphenation-provenance.json', 'overrides'),
                        ('configuration-overrides.json', 'overrides')]:
        for name, entry in json.loads((RECORDS / record).read_text())[key].items():
            target = bundle / name
            if target.exists():
                if digest(target.read_bytes()) != entry['sha256']:
                    raise ValueError(f'Override mismatch: {name}')
                transformed[name] = entry['sha256']
    header = b'% LaTeX Mobile modified distribution: see LATEX-MODIFICATIONS.txt.\n'
    for name, expected, old, new in [
        ('latex.ltx', '70ba1d0d113a986e4966e5a7ebb5afa3fbb17843ec4395bd0187d2aa266b5646',
         b'LaTeX Mobile modified \\fmtname', b'\\fmtname'),
        ('l3backend-xetex.def', '47e2f4fc8bda65ba3f5d295145da3f7bb783b71f2a07f11a4038e84b2fd5cd13',
         b'LaTeX Mobile modified L3 backend support: XeTeX', b'L3 backend support: XeTeX'),
    ]:
        target = bundle / name
        if target.exists():
            data = target.read_bytes()
            if not data.startswith(header) or digest(data[len(header):].replace(old, new)) != expected:
                raise ValueError(f'Modified distribution identification/hash mismatch: {name}')
            transformed[name] = digest(data)
    for name, source in [('AMSFonts-OFL.txt', RECORDS / 'AMSFonts-OFL.txt'),
                         ('LATEX-MODIFICATIONS.txt', ROOT / 'notices/LATEX-MODIFICATIONS.txt')]:
        target = bundle / name
        if target.exists():
            if target.read_bytes() != source.read_bytes():
                raise ValueError(f'Notice mismatch: {name}')
            transformed[name] = digest(target.read_bytes())

    # Report everything outside the exact-match scope explicitly; never silently
    # equate generated or modified files with a verified upstream original.
    remaining = sorted(p.name for p in bundle.iterdir() if p.is_file() and p.name not in checked and p.name not in transformed)
    return {'bundle': str(bundle), 'verified_archives': sorted(archives),
            'exact_runtime_files': checked, 'verified_overrides_and_notices': transformed, 'requires_transformation_or_project_evidence': remaining,
            'scope': 'Exact source identity only; modified/generated files and license obligations require separate evidence.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=ROOT / 'dist/bundles/full/texbundle')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = verify(args.bundle)
    data = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data)
    print(json.dumps({'exact_runtime_files': len(result['exact_runtime_files']),
                      'verified_archives': len(result['verified_archives']),
                      'requires_transformation_or_project_evidence': result['requires_transformation_or_project_evidence']}, indent=2))
