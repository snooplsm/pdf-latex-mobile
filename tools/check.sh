#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cargo fmt --all --check
cargo test --locked -p latex-mobile -p latex-mobile-xdv
python3 -m unittest discover -s tools -p 'test_*.py'
