#!/usr/bin/env python3
"""Build and measure single-ABI AARs without changing Maven publications."""
import argparse
from pathlib import Path
import shutil
import subprocess
from sizes import write_report

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version', default='0.1.0')
args = parser.parse_args()
variants = ('tiny', 'small', 'balanced', 'full')
for abi in ('armeabi-v7a', 'arm64-v8a', 'x86_64'):
    subprocess.run([str(ROOT / 'android/gradlew'), '-p', str(ROOT / 'android'),
                    f'-Pabis={abi}', f'-PreleaseVersion={args.version}',
                    *[f':library:assemble{variant.capitalize()}Release' for variant in variants]], check=True)
    destination = ROOT / 'dist/aar-splits' / abi
    destination.mkdir(parents=True, exist_ok=True)
    for variant in variants:
        shutil.copyfile(ROOT / f'android/library/build/outputs/aar/library-{variant}-release.aar',
                        destination / f'latex-mobile-{variant}-{args.version}.aar')
write_report([ROOT / f'dist/aar/latex-mobile-{variant}-{args.version}.aar' for variant in variants],
             ROOT / 'SIZES.md', ROOT / 'dist/sizes.json', ROOT / 'dist/aar-splits')
