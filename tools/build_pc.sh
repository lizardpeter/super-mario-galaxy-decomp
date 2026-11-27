#!/bin/sh
# Builds the game for Linux as one self-contained executable: build/pc/linux/SMG/smg. It reads only game.pak beside
# itself and writes only into its own folder (saves/, data/). Vulkan; no mods. Windows: tools/build_pc.ps1.
#
#   tools/build_pc.sh [-l <LLVM folder>] [-o <output folder>] [-g <game folder or disc image>] [-j <jobs>]
#
#   -l  LLVM 21 or later, a release archive's folder (it has opt and llvm-link). Default: $NEBULA_LLVM, else LLVM
#       22.1.6 downloaded once into .cache/.
#   -o  output folder (default build/pc/linux). The game lands in <output>/SMG, the importer in <output>/importer.
#   -g  also make <output>/SMG/game.pak from your game: the folder holding DATA and UPDATE (or DATA itself), or a disc
#       image (ISO, RVZ, WIA, WBFS, CISO, GCZ) of RMGE01, RMGP01 or RMGJ01. Needed once.
#
# Needs cmake 3.24+, ninja, python3, curl, tar, git, cargo (Rust stable) and SDL's system development packages (the
# apt line is in docs/pc-build.md). Nothing is installed system-wide.
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
mkdir -p "$out"
out=$(cd "$out" && pwd)

if [ -z "$llvm" ]; then
    case "$(uname -m)" in
    x86_64) asset=LLVM-$LLVM_VERSION-Linux-X64 ;;
    aarch64) asset=LLVM-$LLVM_VERSION-Linux-ARM64 ;;
    *) echo "build_pc.sh: no pinned LLVM for $(uname -m); pass -l" >&2; exit 2 ;;
    esac
    llvm=$root/.cache/$asset
    if [ ! -x "$llvm/bin/opt" ]; then
        echo "Downloading LLVM $LLVM_VERSION (once, into .cache/)"
        mkdir -p "$root/.cache"
        curl -fL --retry 3 -o "$root/.cache/$asset.tar.xz" \
            "https://github.com/llvm/llvm-project/releases/download/llvmorg-$LLVM_VERSION/$asset.tar.xz"
        rm -rf "$llvm" && mkdir -p "$llvm"
        tar -xJf "$root/.cache/$asset.tar.xz" -C "$llvm" --strip-components=1
        rm "$root/.cache/$asset.tar.xz"
    fi
fi
for tool in clang clang++ ld.lld opt llvm-link llvm-nm llvm-dis; do
    [ -x "$llvm/bin/$tool" ] || { echo "build_pc.sh: no $tool in $llvm/bin (use an LLVM release archive)" >&2; exit 2; }
done
export NEBULA_LLVM="$llvm"
toolchain="-DCMAKE_TOOLCHAIN_FILE=$root/port/platform/linux/llvm-toolchain.cmake"
parallel=${jobs:+-j$jobs}

sh "$root/port/tools/fetch_build_deps.sh" "$root/.cache/deps"

# 1. The game: one object (port/native, NEBULA_GAME_STATIC).
cmake -S "$root/port/native" -B "$out/game" -G Ninja -DCMAKE_BUILD_TYPE=Release $toolchain \
    -DNEBULA_MODS=OFF -DNEBULA_LUMA_HOOKS=OFF -DNEBULA_GAME_STATIC=ON -DNEBULA_CPU_LEVEL=x86-64-v3
cmake --build "$out/game" --target smg_game_static -- $parallel

# 2. The executable: the SDL host with the game inside (port/platform/sdl, NEBULA_GAME_OBJECT).
cmake -S "$root/port/platform/sdl" -B "$out/host" -G Ninja -DCMAKE_BUILD_TYPE=Release $toolchain \
    "-DNEBULA_DEPS=$root/.cache/deps" -DNEBULA_MODS=OFF "-DNEBULA_GAME_OBJECT=$out/game"
cmake --build "$out/host" --target main -- $parallel
mkdir -p "$out/SMG"
cp "$out/host/smg" "$out/SMG/smg"

# 3. The importer, a tool of its own: it makes game.pak once; the game never runs it.
(cd "$root/port" && CARGO_TARGET_DIR="$out/cargo" cargo build --release --locked -p nebula-import --bin nebula-import)
mkdir -p "$out/importer"
cp "$out/cargo/release/nebula-import" "$out/importer/"

if [ -n "$game" ]; then
    "$out/importer/nebula-import" identify "$game"
    # The importer writes into a folder that must not exist yet (it refuses one that does), then game.pak moves beside
    # the game.
    rm -rf "$out/import"
    "$out/importer/nebula-import" import "$game" --output "$out/import"
    mv -f "$out/import/game.pak" "$out/SMG/game.pak"
    rmdir "$out/import"
fi
echo
echo "The game: $out/SMG/smg (with game.pak beside it). Move the SMG folder anywhere."
