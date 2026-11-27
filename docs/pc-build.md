# Building and running on PC

The PC port is Nebula (`port/`): the decomp's game code compiled natively for x64 (and ARM64), with a host that
replaces the Wii's hardware and SDK (Direct3D 12, Vulkan and Direct3D 11 renderers, audio, input, saves, mods).
You need your own copy of the game: a disc image (ISO, RVZ, WIA, WBFS, CISO, GCZ) or an extracted folder of
RMGE01, RMGP01 or RMGJ01, revision 0.

## Windows

Install once: Visual Studio 2022 (Desktop development with C++, with a Windows SDK), Rust stable
(`rustup`, MSVC target), Python 3, Git. LLVM is downloaded by the script if `C:\Program Files\LLVM` has none.

```powershell
git clone https://github.com/lizardpeter/super-mario-galaxy-decomp
cd super-mario-galaxy-decomp
.\tools\build_pc.ps1 -Game D:\Games\SMG.rvz
& .\build\pc\windows\bin\Nebula.exe --pak .\build\pc\windows\content\game.pak --saves "$env:LOCALAPPDATA\Nebula\saves"
```

`-Game` imports the game once into `content\game.pak`; leave it out on later builds. `-Baseline` adds the programs
for CPUs without AVX2. `Nebula.exe` is Direct3D 12; `NebulaVk.exe` Vulkan; `NebulaD11.exe` Direct3D 11 (or
**Renderer** in the settings, F1). No environment variable is set beyond the PowerShell session.

## Linux

```sh
sudo apt-get install -y ninja-build cmake pkg-config curl python3 \
  libx11-dev libxext-dev libxrandr-dev libxcursor-dev libxi-dev libxss-dev libxfixes-dev libxtst-dev \
  libxkbcommon-dev libwayland-dev wayland-protocols libegl-dev libdecor-0-dev \
  libasound2-dev libpulse-dev libdbus-1-dev libudev-dev libdrm-dev libgbm-dev
# plus Rust stable (rustup)
tools/build_pc.sh -g ~/Games/SMG.rvz
build/pc/linux/bin/nebula --pak build/pc/linux/content/game.pak --saves ~/.local/share/Nebula/saves
```

The script downloads LLVM 22.1.6 into `.cache/` unless `-l` or `NEBULA_LLVM` names one (21 or later), and Nebula's
pinned dependencies (SDL3, glslang, Vulkan headers, volk, VMA) into `.cache/deps/`.

## What the scripts run

They are thin wrappers over Nebula's own build (port/README.md): the CMake host build, `port/native/build.ps1` or
`port/platform/linux/build_linux.sh` for the game module, and `cargo build -p nebula-import`. AMD FSR 3 is left out
unless its shader headers are supplied (Nebula's `NEBULA_REQUIRE_FSR3`); macOS and Android: port/README.md.

## Known differences from Nebula's releases

- Nebula's update check (`port/runtime/src/update/update.cpp`) asks keepvaibin/nebula's GitHub releases, so a
  build from this repo offers Nebula's official updates. Turn it off in **Settings > SYSTEM > UPDATES**
  (**Check at start**); pointing it at this repo, or removing it, is on the roadmap.
- Source builds have no diagnostics upload endpoint (`diag_endpoint.h` is empty), so nothing is sent anywhere.
