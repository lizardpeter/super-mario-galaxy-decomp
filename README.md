# super-mario-galaxy-decomp

Super Mario Galaxy (Wii), decompiled and running natively on PC.

- `decomp/`: the faithful decomp ([Petari](https://github.com/SMGCommunity/Petari)). Builds `main.dol` byte-identical
  to the North American disc with the original compilers.
- `port/`: the PC port ([Nebula](https://github.com/keepvaibin/nebula)): Windows (Direct3D 12, Vulkan, Direct3D 11)
  and Linux (Vulkan), plus macOS and Android.
- [STATUS.md](STATUS.md): what matches, measured on every push.

You need your own copy of the game. Nothing from the game is in this repository.

## Build for PC

Windows (Visual Studio 2022 C++ tools, Rust, Python 3):

```powershell
.\tools\build_pc.ps1 -Game D:\Games\SMG.rvz
& .\build\pc\windows\bin\Nebula.exe --pak .\build\pc\windows\content\game.pak --saves "$env:LOCALAPPDATA\Nebula\saves"
```

Linux: `tools/build_pc.sh -g ~/Games/SMG.rvz`. Details: [docs/pc-build.md](docs/pc-build.md).

## Check the decomp

```sh
python3 tools/fetch_originals.py RMGE01   # or put your own main.dol in decomp/orig/RMGE01/sys/
python3 tools/match.py RMGE01
```

[AGENTS.md](AGENTS.md) has the layout and rules; [docs/](docs) the rest.

## Licence

GPL-3.0-only ([LICENSE](LICENSE)), because the port is. `decomp/` is CC0-1.0. Not affiliated with Nintendo.
