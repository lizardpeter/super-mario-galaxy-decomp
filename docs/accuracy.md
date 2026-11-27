# Accuracy: where the PC build differs from the console

Known places where the PC build (`port/`, the single executable) does not reproduce the Wii exactly. Each says what
differs, why, how large it is, and what fixing it would take. Bugs in the original game are not here: they are in
`records/bugs.tsv` (the faithful decomp keeps them; the enhanced build may fix them).

## CMPR textures are sampled as BC1

**What:** CMPR, the Wii's compressed texture format, is stored in `game.pak` as its raw 4x4 blocks, in BC1's layout
(the importer: `port/crates/nebula-import/src/cook/texture.rs` `block4_level`). Where the GPU samples BC1, the renderer
uploads them as BC1 (`port/runtime/src/render/texture_store.cpp`, `NEBULA_TEXTURE_BLOCK4` -> `TexelFormat::Bc1`), so the
GPU decodes them.

**The difference:** the two in-between colours of a four-colour block. The Wii's GPU makes them 5/8 c0 + 3/8 c1 and
3/8 c0 + 5/8 c1; BC1 hardware makes them 2/3 + 1/3. An in-between texel is off by 1/24 of the distance between the
block's two colours (about 4% of it), per channel. The two end colours, three-colour blocks (their average, transparent
black) and every other texture format are exact.

**Fix, when wanted:** expand CMPR to RGBA8 on upload with the Wii's arithmetic, which `texture_store.cpp` already does
for GPUs without BC1 (its RGBA8 path). `game.pak` does not change. Cost: CMPR textures take 8x the video memory (32 bits
per texel against BC1's 4): tens to low hundreds of MB for a galaxy, and more bytes uploaded at load. Frame time should
not move measurably (the game's textures fit the GPU's caches either way); measure with `--benchmark 1` before and after.
An exact path that stays at 4 bits per texel would decode the blocks in the shader, which then has to filter and pick
mip levels by hand: worth it only for a memory-starved target such as a weak GPU in the web build.

**Decision:** left as BC1 for now.
