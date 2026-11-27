# Upstreams

Both are squashed git subtrees: their files are ordinary files here (one commit per import), so the repo builds
from a plain clone and local changes are normal commits. `target.toml` `[upstream.*]` records the imported commit.

## decomp/ — Petari

<https://github.com/SMGCommunity/Petari>, CC0-1.0. SMGCommunity's matching decompilation: `config/<version>/`
(symbols, splits), `src/` and `include/`, `configure.py` (decomp-toolkit template). Petari does not accept
AI-generated contributions, so nothing from this repo is sent upstream.

```sh
git subtree pull --prefix=decomp https://github.com/SMGCommunity/Petari main --squash
python3 tools/match.py RMGE01 && python3 tools/status.py && python3 tools/graph/sync.py
```

then update `[upstream.decomp].commit` and commit the regenerated analysis.

## port/ — Nebula

<https://github.com/keepvaibin/nebula>, GPL-3.0-only. Its `native/petari/` is Nebula's fork of Petari (based on
Petari `86ae7a3`, 2026-10-17): only the files the game module compiles, changed for a 64-bit little-endian host
(byte order of data read from the disc, pointer widths, the SDK replaced by the host). `decomp/` is newer; the
difference between `port/native/petari/` and `decomp/` is upstream progress plus Nebula's port changes.

```sh
git subtree pull --prefix=port https://github.com/keepvaibin/nebula main --squash
```

## Licence

The repo as a whole is GPL-3.0-only (`LICENSE`), because `port/` is. `decomp/` stays CC0 (its own `LICENSE`), and
Nebula's third-party code keeps its licences (`port/THIRD-PARTY-NOTICES.md`).
