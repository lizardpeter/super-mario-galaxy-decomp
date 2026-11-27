# Building and running on PC

The game builds as **one self-contained executable**: `smg.exe` on Windows, `smg` on Linux. It is Nebula's Vulkan host
with the decomp's game code linked inside it (no `smg_game.dll`), no mods, and no update check. It reads only
`game.pak` beside itself and writes only into its own folder:

```
SMG\
  smg.exe      the game (Windows; `smg` on Linux)
  game.pak     your game's files, converted once by the importer
  saves\       made on first run
  data\        settings, logs, crash reports, the shader cache
```

Move or copy the `SMG` folder anywhere. Nothing is read from or written to anywhere else, with one exception the game
cannot control: GPU drivers keep their own shader cache for every Vulkan program (NVIDIA's under `%LOCALAPPDATA%`).

## Windows

Install once: Visual Studio 2022 (Desktop development with C++, with a Windows SDK), Rust stable (`rustup`, MSVC
target), Python 3, Git.

```powershell
git clone https://github.com/lizardpeter/super-mario-galaxy-decomp
cd super-mario-galaxy-decomp
.\tools\build_pc.ps1 -Game D:\Games\SMG       # the folder holding DATA and UPDATE, or a disc image
.\build\pc\windows\SMG\smg.exe
```

`-Game` makes `game.pak` once (about a minute); leave it out on later builds. The importer is
`build\pc\windows\importer\nebula-import.exe` if you want to make a `game.pak` yourself:

```powershell
.\build\pc\windows\importer\nebula-import.exe import D:\Games\SMG --output .\build\pc\windows\SMG
```

## Linux

```sh
sudo apt-get install -y ninja-build cmake pkg-config curl git python3 \
  libx11-dev libxext-dev libxrandr-dev libxcursor-dev libxi-dev libxss-dev libxfixes-dev libxtst-dev \
  libxkbcommon-dev libwayland-dev wayland-protocols libegl-dev libdecor-0-dev \
  libasound2-dev libpulse-dev libdbus-1-dev libudev-dev libdrm-dev libgbm-dev
# plus Rust stable (rustup)
tools/build_pc.sh -g ~/Games/SMG
build/pc/linux/SMG/smg
```

## What the game accepts

Super Mario Galaxy revision 0: North America (RMGE01), Europe (RMGP01) or Japan (RMGJ01), as the extracted folder
Dolphin makes (the folder holding `DATA` and `UPDATE`, or `DATA` itself) or a disc image (ISO, RVZ, WIA, WBFS, CISO,
GCZ). Only `DATA` is used.

## How the single executable is built

1. **The game, as one object.** `port/native` with `NEBULA_GAME_STATIC` compiles every game source to LLVM bitcode;
   `port/native/tools/game_object.py` joins them into one module, makes every name internal except the 46 entry
   points the host calls, optimizes the whole game at once and compiles it to `smg_game_static.o`. That is why the
   game can live inside the host: its own C library and math (the same results on every platform) and its thousands of
   Wii-era names cannot collide with the host's. The tool fails the build if any other name stays visible.
2. **The host**, built with the object and `NEBULA_GAME_STATIC` + `NEBULA_SELF_CONTAINED`: the entry points come from
   the table the tool writes instead of `GetProcAddress`/`dlsym`, the data folder is `data\` beside the program
   (`galaxy/platform_paths.h`), `game.pak` and `saves\` default to beside it (`host_main.cpp`), SDL is linked in on
   Linux, and the update check is left out.
3. **The importer**, `nebula-import`, a separate Rust program that converts your game into `game.pak` once (textures,
   audio, models, collision, text and the render pipelines into the forms the PC renderer reads).

The scripts pin LLVM 22.1.6's release archive (it has `opt` and `llvm-link`, which LLVM's Windows installer leaves
out) and download it once into `.cache/`. The game is built with clang; the Windows host with MSVC (the game's object
asks for the same C runtime, `/MD`).
