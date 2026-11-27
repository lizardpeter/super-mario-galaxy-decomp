# Verification

## Faithful build: byte match

`tools/match.py <build>` runs Petari's own build in `decomp/`:

1. `configure.py --version <build>` downloads the pinned toolchain (decomp-toolkit, objdiff, the Metrowerks
   CodeWarrior compilers, PowerPC binutils, wibo to run the Windows compilers on Linux; tags in
   `analysis/<build>/summary.json`) and writes the ninja build.
2. `ninja` compiles every source file with the compiler version and flags of its original library, links
   `main.dol` (units not yet linkable from source come from the split original) and checks the result's SHA-1
   against the retail disc's. `tools/match.py` checks it again against `target.toml` and fails on any difference.
3. `ninja build/<build>/report.json`: objdiff compares each function compiled from source with the original:
   instructions and relocations. 100% is `matches`.

Measured on RMGE01 at decomp `f7ada3c` (STATUS.md has the current numbers): relinked `main.dol` identical;
41,976 of 41,997 functions and 99.91% of code bytes match; 1,606 of 2,206 units are complete (code and data match and
the unit is linked from source). The functions not matching are listed in STATUS.md: a few partial matches in
`Game/Screen`, and the Revolution SDK's audio sequencer/synth (`SYN*`, `SEQ*`, `MIX*`) and one `NET` function, which
have no source yet.

Why not differential tests under an emulator, as in the PC decomps: a byte-identical relink is a stronger proof than
behavioural equivalence, and it is what the original toolchain gives here.

## PC build

`pc.yml` builds the port with the same scripts a person runs (docs/pc-build.md) on Windows and Linux and starts
every program without game data (`--start-check 300`: window, renderer, 300 frames shown) on software renderers
(WARP for Direct3D, Mesa lavapipe for Vulkan). Nebula's own test suite (`port/tools/gate/gate.py`, unit tests,
sanitizers, replays with game data) lives in `port/` and runs as Nebula documents it.
