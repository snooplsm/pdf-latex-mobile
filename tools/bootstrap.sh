#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# macOS: brew install m4 pkg-config autoconf autoconf-archive automake libtool
# Linux: install the corresponding build-essential/pkg-config/autotools packages.
revision=b8b8df2201ad8509b81a830fe0957bcb98e06c27
if [[ ! -d .build/vcpkg/.git ]]; then
  git clone https://github.com/microsoft/vcpkg.git .build/vcpkg
fi
git -C .build/vcpkg checkout "$revision"
.build/vcpkg/bootstrap-vcpkg.sh -disableMetrics
.build/vcpkg/vcpkg install icu freetype graphite2 libpng --triplet "${VCPKGRS_TRIPLET:-arm64-osx}"
