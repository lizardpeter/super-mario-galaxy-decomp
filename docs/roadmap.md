# Roadmap

Each item says what must exist first.

1. **Port divergence ledger.** A generated `analysis/port/` listing, per function, whether Nebula's
   `port/native/petari/` code equals Petari at the fork base (`86ae7a3`), and what kind each change is (byte
   order, pointer width, host call, gameplay). Gameplay-visible changes become `records/patches.tsv` rows. Needs: a
   tool that fetches Petari at the base commit and diffs per function.
2. **Close the faithful gaps.** The functions STATUS.md lists as not matching (two `THPSimplePlayerWrapper`
   partials, `StarPointerFunction::forceOutsideScreenEdge`, the SDK's `SYN`/`SEQ`/`MIX` sequencer and `NET`), and
   the 600 units whose data does not match yet so they are linked from the split original.
3. **Update channel.** Point the port's update check at this repo's releases (with our own signing key) or remove
   it (docs/pc-build.md). Needs: a release workflow here.
4. **Other regions** (docs/builds.md): RMGP01 and RMGJ01 `main.dol` in R2.
5. **Bug ledger.** File what Nebula's ledger (`port/docs/plan/ledger.tsv`) and audits found in the original game
   code as `records/bugs.tsv` rows with evidence.
6. **Exact CMPR textures** (docs/accuracy.md): expand to RGBA8 with the Wii's colour arithmetic on upload instead of
   sampling as BC1. Measure frame time before and after.
7. **Fixed tick** (docs/fixed-tick.md): the game simulated at 60 x k ticks a second, k chosen to match the display,
   with the game's speed unchanged and k = 1 bit-identical to the original. Inventory: `analysis/tick/summary.md`.
   Then late input reading and the camera's late latch.
8. **Discord rich presence** (branding/README.md): the status already names the galaxy, the star and the Power Star
   count. To add, over the same local pipe: art for each galaxy (images uploaded to the application, named by key),
   elapsed time, the current mission's icon. No SDK.
9. **Smaller exe, faster loading, web-ready data.** The Linux exe is 206 MB, of which about 168 MB is shader SPIR-V
   built in (`.rodata` 171 MB; code `.text` 24 MB).
   - Shaders move into `game.pak`: compressed, debug info stripped, duplicates merged, loaded on first use. The
     startup pipeline build and the driver cache are unchanged, so no new stutter. Expected exe: about 35-40 MB.
   - Linker trimming: `--gc-sections`, identical-code folding (`/OPT:ICF`, `--icf=all`), and no unused Nebula
     extras linked (crypto remnants, unused upscalers), each measured before it is cut. Smaller relocation tables
     on Linux.
   - Static C++ runtime on Windows (`/MT` for the host and the game object): no Visual C++ Redistributable
     needed (VCRUNTIME140/MSVCP140), about 1 MB more.
   - Web: the importer writes WGSL beside SPIR-V, so the exe carries neither. The pak is split into chunks a browser
     fetches separately (title and first galaxy first, the rest in the background), kept in browser storage after
     the first visit, and ordered by first use (recorded once from a play-through), which also helps native loads.
     The wasm module is compiled while it streams in and served compressed.
