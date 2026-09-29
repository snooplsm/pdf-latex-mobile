#!/usr/bin/env python3
"""Reproduce converted fonts and validate generated bundle metadata for every profile."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    provenance = json.loads((ROOT/'experiments/licenses/amsfonts-provenance.json').read_text())
    archive = ROOT/'.build/license-sources/amsfonts.zip'
    assert sha(archive.read_bytes()) == provenance['archive_sha256']
    with tempfile.TemporaryDirectory(prefix='lm-font-verification-') as temp:
        source = Path(temp)/'source'
        output = Path(temp)/'output'
        source.mkdir()
        with zipfile.ZipFile(archive) as z:
            for name, expected in provenance['verified_identical_files'].items():
                members = [n for n in z.namelist() if n.endswith('/'+name)]
                assert len(members) == 1, name
                data = z.read(members[0])
                assert sha(data) == expected, name
                (source/name).write_bytes(data)
        subprocess.run([sys.executable, str(ROOT/'tools/prepare-fonts.py'),
                        '--source', str(source), '--output', str(output)], check=True)
        for profile in ('tiny','small','balanced','full'):
            bundle = ROOT/'dist/bundles'/profile/'texbundle'
            manifest = json.loads((bundle/'manifest.json').read_text())
            records = manifest['files']
            names = [r['name'] for r in records]
            assert len(names) == len(set(names)), 'Duplicate manifest entries'
            actual = {str(p.relative_to(bundle)) for p in bundle.rglob('*') if p.is_file()}
            assert actual == set(names) | {'SHA256SUM','manifest.json'}, profile
            for record in records:
                data = (bundle/record['name']).read_bytes()
                assert len(data) == record['bytes'] and sha(data) == record['sha256'], record['name']
            fingerprint = sha(json.dumps(records, sort_keys=True, separators=(',',':')).encode())
            assert fingerprint == manifest['bundle_sha256'] == (bundle/'SHA256SUM').read_text().strip()
            assert sum(r['bytes'] for r in records) == manifest['payload_bytes']
            fonts = []
            for candidate in output.iterdir():
                target = bundle/candidate.name
                if target.exists():
                    assert target.read_bytes() == candidate.read_bytes(), target
                    fonts.append(candidate.name)
            # Check disabled language behavior and absence of restricted inputs.
            from pack import DISABLED_HYPHENATION
            for code in DISABLED_HYPHENATION.values():
                assert not list(bundle.glob(f'hyph-{code}.*'))
                assert not list(bundle.glob(f'loadhyph-{code}.*'))
            config_provenance = json.loads((ROOT/'experiments/licenses/language-config-provenance.json').read_text())
            original_config = ROOT/'experiments/licenses'/config_provenance['source_file']
            assert sha(original_config.read_bytes()) == config_provenance['sha256']
            with tempfile.TemporaryDirectory(prefix='lm-config-verification-') as config_temp:
                config_dir = Path(config_temp)
                (config_dir/'language.dat').write_bytes(original_config.read_bytes())
                from pack import disable_restricted_hyphenation
                disable_restricted_hyphenation(config_dir)
                if 'languages' not in manifest['features']:
                    (config_dir/'language.dat').write_text('english hyphen.tex\n=usenglish\n=USenglish\n=american\n')
                assert (bundle/'language.dat').read_bytes() == (config_dir/'language.dat').read_bytes()
            lines = (bundle/'language.dat').read_text().splitlines()
            for line in lines:
                fields = line.split()
                if fields and fields[0] in DISABLED_HYPHENATION:
                    assert fields[1:] == ['lm-nohyphen.tex'], line
            empty = bundle/'lm-nohyphen.tex'
            if empty.exists():
                assert empty.read_text() == (
                    '% Copyright 2026 LaTeX Mobile contributors. SPDX-License-Identifier: MIT\n'
                    '% Automatic hyphenation intentionally disabled; explicit hints remain available.\n'
                    '\\endinput\n')
            print(json.dumps({'profile':profile,'manifest_files':len(records),
                              'reproduced_font_files':len(fonts),'bundle_sha256':fingerprint}))

if __name__ == '__main__':
    main()
