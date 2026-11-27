#!/bin/sh
# Builds the PC port (port/, Nebula) for Linux in one command: the host with the Vulkan renderer, the game module
# compiled from the decomp, and the game importer. Windows: tools/build_pc.ps1.
#
#   tools/build_pc.sh [-l <LLVM folder>] [-o <output folder>] [-g <disc image or extracted game folder>] [-j <jobs>]
#
#   -l  LLVM 21 or later (clang, clang++, ld.lld, libclang). Default: $NEBULA_LLVM, else a pinned LLVM downloaded
#       once into .cache/ (docs/pc-build.md).
#   -o  output folder (default build/pc/linux). The programs land in <output>/bin.
#   -g  also import the game into <output>/content/game.pak (RMGE01, RMGP01 or RMGJ01; ISO, RVZ, WIA, WBFS, CISO,
#       GCZ or an extracted folder).
#
# Needs cmake 3.24+, ninja, python3, curl, tar, cargo (Rust stable) and SDL's system development packages (the apt
# line is in docs/pc-build.md). Nothing is installed system-wide.
set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
LLVM_VERSION=22.1.6
llvm=${NEBULA_LLVM:-}
out=$root/build/pc/linux
game=
jobs=
while getopts "l:o:g:j:" option; do
    case "$option" in
    l) llvm=$OPTARG ;;
    o) out=$OPTARG ;;
    g) game=$OPTARG ;;
    j) jobs=$OPTARG ;;
    *) sed -n '5,13p' "$0" >&2; exit 2 ;;
    esac
done
for tool in cmake ninja python3 cargo curl tar; do
    command -v "$tool" >/dev/null || { echo "build_pc.sh: $tool is not on PATH (docs/pc-build.md)" >&2; exit 2; }
done

if [ -z "$llvm" ]; then
    case "$(uname -m)" in
    x86_64) asset=LLVM-$LLVM_VERSION-Linux-X64 ;;
    aarch64) asset=LLVM-$LLVM_VERSION-Linux-ARM64 ;;
    *) echo "build_pc.sh: no pinned LLVM for $(uname -m); pass -l" >&2; exit 2 ;;
    esac
    llvm=$root/.cache/$asset
    if [ ! -x "$llvm/bin/clang" ]; then
        echo "Downloading LLVM $LLVM_VERSION (once, into .cache/)"
        mkdir -p "$root/.cache"
        curl -fL --retry 3 -o "$root/.cache/$asset.tar.xz" \
            "https://github.com/llvm/llvm-project/releases/download/llvmorg-$LLVM_VERSION/$asset.tar.xz"
        rm -rf "$llvm" && mkdir -p "$llvm"
        tar -xJf "$root/.cache/$asset.tar.xz" -C "$llvm" --strip-components=1
        rm "$root/.cache/$asset.tar.xz"
    fi
fi

sh "$root/port/tools/fetch_build_deps.sh" "$root/.cache/deps"
set -- -d "$root/.cache/deps" -l "$llvm" -w "$out"
[ -n "$jobs" ] && set -- "$@" -j "$jobs"
(cd "$root/port" && sh platform/linux/build_linux.sh "$@")

if [ -n "$game" ]; then
    "$out/bin/nebula-import" identify "$game"
    "$out/bin/nebula-import" import "$game" --output "$out/content"
fi
echo
echo "Built: $out/bin"
echo "Run:   $out/bin/nebula --pak $out/content/game.pak --saves ~/.local/share/Nebula/saves"
