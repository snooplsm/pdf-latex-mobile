#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${VCPKG_ROOT:=$PWD/.build/vcpkg}"
export VCPKG_ROOT TECTONIC_DEP_BACKEND=vcpkg
case "${1:-}" in
  host)
    export VCPKGRS_TRIPLET="${VCPKGRS_TRIPLET:-arm64-osx}"
    cargo build --locked --release -p latex-mobile
    ;;
  android)
    : "${ANDROID_NDK_HOME:?Set ANDROID_NDK_HOME to Android NDK r29}"
    host=darwin-x86_64
    [[ $(uname) == Linux ]] && host=linux-x86_64
    toolchain="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/$host/bin"
    export PATH="$toolchain:$PATH"
    for abi in ${ABIS:-arm64-v8a}; do
      case "$abi" in
        arm64-v8a) target=aarch64-linux-android; triplet=arm64-android; clang=aarch64-linux-android28-clang ;;
        x86_64) target=x86_64-linux-android; triplet=x64-android; clang=x86_64-linux-android28-clang ;;
        *) echo "Unsupported ABI: $abi" >&2; exit 1 ;;
      esac
      export VCPKGRS_TRIPLET="$triplet"
      "$VCPKG_ROOT/vcpkg" install icu freetype graphite2 libpng "fontconfig[core]" --triplet "$triplet"
      rustup target add "$target"
      for native_profile in ${NATIVE_PROFILES:-compact full}; do
      python3 tools/prune-icu.py "$triplet" --profile "$native_profile" --target "$target"
      cargo clean -p latex-mobile --release --target "$target"
      target_env=$(echo "$target" | tr '[:lower:]-' '[:upper:]_')
      env "CARGO_TARGET_${target_env}_LINKER=$clang" CC="$clang" CXX="${clang}++" AR=llvm-ar CXXSTDLIB=c++_static \
        RUSTFLAGS='-C link-arg=-Wl,-z,max-page-size=16384 -C link-arg=-Wl,-z,common-page-size=16384 -C link-arg=-lc++_static -C link-arg=-lc++abi' \
        cargo build --locked --release -p latex-mobile --lib --target "$target"
      destination="dist/native/android/$native_profile/$abi"
      mkdir -p "$destination"
      cp "target/$target/release/liblatex_mobile.so" "$destination/"
      llvm-strip --strip-unneeded "$destination/liblatex_mobile.so"
      done
    done
    ;;
  ios)
    export VCPKG_OVERLAY_TRIPLETS="$PWD/tools/triplets"
    export IPHONEOS_DEPLOYMENT_TARGET=15.0
    for pair in aarch64-apple-ios:arm64-ios-release aarch64-apple-ios-sim:arm64-ios-simulator-release; do
      target=${pair%%:*}; triplet=${pair#*:}
      export VCPKGRS_TRIPLET="$triplet"
      "$VCPKG_ROOT/vcpkg" install icu freetype graphite2 libpng "fontconfig[core]" --triplet "$triplet"
      rustup target add "$target"
      for native_profile in ${NATIVE_PROFILES:-compact full}; do
        python3 tools/prune-icu.py "$triplet" --profile "$native_profile" --target "$target"
        cargo clean -p latex-mobile --release --target "$target"
        cargo build --locked --release -p latex-mobile --lib --target "$target"
        destination="dist/native/ios/$native_profile/$target"
        mkdir -p "$destination"
        # vcpkg emits external link directives, so its archives must be merged for Swift consumers.
        libraries=()
        for library in brotlicommon brotlidec brotlienc bz2 expat fontconfig freetype graphite2 icudata icui18n icuio icuuc png16 uuid z; do
          libraries+=("$VCPKG_ROOT/installed/$triplet/lib/lib$library.a")
        done
        xcrun libtool -static -o "$destination/liblatex_mobile.a" \
          "target/$target/release/liblatex_mobile.a" "${libraries[@]}"
      done
    done
    headers="$PWD/.build/ios-headers"
    mkdir -p "$headers"
    cp include/latex_mobile.h "$headers/"
    printf 'module CLatexMobile { header "latex_mobile.h" export * }\n' > "$headers/module.modulemap"
    for native_profile in ${NATIVE_PROFILES:-compact full}; do
      native_root="$PWD/dist/native/ios/$native_profile"
      output="$native_root/CLatexMobile.xcframework"
      if [[ -d "$output" ]]; then rm -r "$output"; fi
      xcodebuild -create-xcframework \
        -library "$native_root/aarch64-apple-ios/liblatex_mobile.a" -headers "$headers" \
        -library "$native_root/aarch64-apple-ios-sim/liblatex_mobile.a" -headers "$headers" \
        -output "$output"
    done
    ;;
  *) echo "Usage: tools/build-native.sh host|android|ios" >&2; exit 1 ;;
esac
