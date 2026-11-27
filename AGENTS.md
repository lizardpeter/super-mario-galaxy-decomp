# Working in super-mario-galaxy-decomp

Decompilation and PC port of Super Mario Galaxy (Wii). The target is the North American disc's `main.dol`
(`RMGE01`, `kind = "retail"` in `target.toml`). The layout and method follow `lizardpeter/black-ops-2-decomp`,
`ghosts-decomp` and `black-ops-3-decomp`, adapted to a game whose community decomp already byte-matches
(docs/upstreams.md).

## Three trees

| Path | What | Upstream (squashed git subtree) |
|---|---|---|
| `decomp/` | The **faithful** decomp: Petari, C/C++ that CodeWarrior compiles back to the original PowerPC code. Relinks `main.dol` byte for byte. | SMGCommunity/Petari (CC0-1.0) |
| `port/` | The **PC port**: Nebula, its host (renderers, audio, input, saves, mods), installer, importer, and its fork of Petari's game code compiled for x64/ARM64 (`port/native/petari/`). | keepvaibin/nebula (GPL-3.0-only) |
| everything else | This repo's own: records, analysis, tools, docs, CI. | — |

Changes to `decomp/` and `port/` are ordinary commits here; keep each one recorded (records/patches.tsv for the
port) so pulling a newer upstream (docs/upstreams.md) can be checked against them.

## The one rule: generated vs authored

| Kind | Where | Who writes it |
|---|---|---|
| **Generated** | `analysis/<build>/`, `analysis/graph/`, `analysis/tick/`, `STATUS.md` | Only `tools/match.py`, `tools/status.py`, `tools/graph/sync.py`, `tools/tick/inventory.py`. Never hand-edit. |
| **Authored** | `records/`, `docs/`, `tools/`, `.github/`, and code in `decomp/` and `port/` | People and agents. |

If a generated file is wrong, fix the script and re-run. CI (`decomp.yml`) fails if the committed generated files
are not what the commit produces.

## Addresses

Upper-case hexadecimal without `0x`, eight digits: `80030D0C`. DOL sections are absolute (no image base).

## Function status ladder

`located → named → typed → decompiled → compiles → matches → integrated`, computed per function by
`tools/match.py` from one build of `decomp/` (docs/verification.md):

- `located`: address and size in `decomp/config/<build>/symbols.txt`
- `named`: a real name, not an auto label
- `typed`: prototype known (mangled C++ signature, or its unit has source)
- `decompiled`: its unit has a source file in `decomp/src/`
- `compiles`: the compiled object contains it
- `matches`: objdiff finds it identical to the original (instructions and relocations). The relinked `main.dol` must
  also be byte-identical to the retail one, or the run fails.
- `integrated`: matches, and its source file is compiled into the PC build (`port/native/petari/`)

`records/functions.tsv` holds per-function notes and claims; `tools/check_records.py` fails if a claim is above the
evidence. Progress is tracked nowhere else than `analysis/` and `STATUS.md`.

## Faithful and enhanced

The faithful build is `decomp/`: original behaviour, bugs included, proven by the byte match. Never fix a bug there.
The enhanced build is the PC port: `port/` is Nebula's version of the game code plus its host, and every deliberate
change we make on top goes in `port/` with a row in `records/patches.tsv`. Anything in the original worth fixing or
improving goes in `records/bugs.tsv` first (kinds and priorities in `tools/check_records.py`). Planned work:
docs/roadmap.md.

## Building

- Faithful: `python3 tools/fetch_originals.py RMGE01` then `python3 tools/match.py RMGE01` (Linux or WSL; ~5 min).
- PC: `tools/build_pc.ps1` (Windows) or `tools/build_pc.sh` (Linux). docs/pc-build.md.

## Originals

Game files are never committed. `main.dol` and the disc's system files are in R2 under the keys in `target.toml`;
`tools/fetch_originals.py` verifies SHA-256 and SHA-1. The PC port imports the player's own disc or extracted folder
locally. Helpers for reading the bucket are not part of this repo.

## Graph

`python3 tools/graph/sync.py` writes `analysis/graph/` (MERGE-by-key, graph `re_smg`). Copy it to the Graph DB
import folder as `smg/` and load each manifest entry with `bulk_import_file`. No ad-hoc writes, no code text.
