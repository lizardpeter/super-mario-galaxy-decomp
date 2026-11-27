# Builds

## RMGE01 (target)

Super Mario Galaxy, North America, revision 0. The disc's system area is in R2 under
`super-mario-galaxy/DATA/sys/` (an extracted disc; `files/` beside it holds the game data).

| file | SHA-256 | notes |
|---|---|---|
| `main.dol` | `2c680585…a50a93c09` | SHA-1 `9a71008a…f0e895dd`, the hash Petari's `config/RMGE01/build.sha1` pins |
| `boot.bin` | `6e9f22d2…059617db6d95` | disc header, game id `RMGE01` |
| `bi2.bin`, `apploader.img`, `fst.bin` | in `target.toml` | |

There is no symbol build here. Every name comes from Petari's `symbols.txt`, the community's identifications;
the byte match proves the code, not the names.

## Other regions

Petari configures RMGJ01, RMGP01, RMGK01 and SHIELD (the NVIDIA Shield TV China release). Nebula runs RMGE01,
RMGP01 and RMGJ01. To add one: put its `main.dol` in R2, add a `[[build]]` with its hashes (Petari's
`decomp/config/<id>/build.sha1` must agree), add the id to `decomp.yml`'s matrix, run `tools/match.py <id>`.
