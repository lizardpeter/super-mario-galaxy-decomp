# Fixed tick: the game simulated at the display's rate

Goal: every frame the player sees is a real simulation step. The game's logic and physics run at a fixed tick rate
the player chooses (or that follows the display), with the game's speed in real time the same at every rate. No
in-between pictures blended or predicted; nothing above the tick rate is wasted. Late input and the camera's late
latch come after, on top of this.

Today (Nebula): the game steps 60 times a second; at higher refresh rates the renderer blends between the last two
steps, which costs one step of delay plus a wait Nebula's own audit calls unnecessary (about 40 ms input to display at
240 Hz; port/docs/audit-2026-11-17/F-interpolation-and-frame-unlock.md).

## Rules

1. **The tick is T = 60 x k steps a second, k a whole number** (60, 120, 180, 240, 300, 360, 480, 600...). Then every
   duration the game was authored with ("after 30 steps") is exactly 30 x k ticks: no rounding anywhere. A display
   whose rate is not a multiple of 60 (144, 165 Hz) takes the next multiple above it with VSync off, or the one below.
2. **k = 1 is the original game, bit for bit.** Every converted code path reduces to the original arithmetic at k = 1
   (where a formula would not be bit-identical, e.g. `powf(f, 1.0f)`, the k = 1 path is the original expression). The
   proof is Nebula's step-hash recordings (`port/tests/replays`: the hash of every live actor after every step, 20
   galaxies): they must still match.
3. **Values keep their authored units.** Speeds stay "units per 60 Hz step", timers "60 Hz steps", factors "per 60 Hz
   step", as the game's code and data (BCSV tables, archives) say them. The conversion happens where a value is
   applied, once per tick: data and most code stay as written.
4. **The simulation is deterministic and reads no real-world clock.** Time inside the game is the tick count. That
   keeps replays exact at every k, and is what netcode needs later (rollback or server-authoritative).
5. **The clock is real time.** The tick runs on the host's clock, not the display's: Nebula's rule that lets the game's
   speed follow a display within 1 % of a multiple of 60 does not apply.

## How each kind of code converts

`tools/tick/inventory.py` finds the sites (`analysis/tick/summary.md`): 6,643 lines in 787 files, 1,120 of them already
written in seconds (Nebula's `stepsOfSeconds`), which convert by themselves.

| Kind | Per 60 Hz step today | Per tick (k ticks per 60 Hz step) |
|---|---|---|
| Nerve timers (`MR::isStep(this, n)`, `isGreaterStep`, `calcNerveRate`...) | the nerve's step count vs n | the count counts ticks; n is compared as n x k, in `NerveUtil.cpp` for every caller. Code reading `getNerveStep()` as a number divides by k |
| Durations in seconds (`stepsOfSeconds`) | seconds x 60 | seconds x T (NebulaFrameClock's steps per second becomes T) |
| Position from velocity (`LiveActor::movement`) | p += v | p += v / k |
| Acceleration, gravity, impulses added to a velocity | v += a | v += a / k (an impulse, a one-off change, stays whole) |
| Decay, friction (`v *= 0.9`) | x f | x f^(1/k), worked out once per value |
| Approach a target by a fraction (`x += (t - x) * 0.1`) | fraction f | 1 - (1 - f)^(1/k) |
| Hand-kept counters (`mTimer++`, `> 30`) | counts steps | counts ticks with limits x k, or counts time |
| Animation (`J3DFrameCtrl`, rates) | frame += rate | frame += rate / k |
| A chance each step (`MR::isHalfProbability`) | p per step | drawn once per 60 Hz step (on ticks divisible by k), so the random sequence and its odds are unchanged |
| An explicit 60 in arithmetic | 60 | T |
| Collision | one check per step | one per tick: finer, so less tunnelling; never worse |

A site that cannot be made rate-independent, or whose result drifts at high k (float precision: millions of tiny
additions), is recorded in `records/bugs.tsv` (`precision`, `limit`) with what it does.

## How we know a subsystem is converted

1. **k = 1:** the step-hash recordings match, every step of all 20 (`port/tools/gate/replays_software.py`,
   `port/tools/verify/step_hash.py`). They run as a code mod, so on a test build with mods (the same game code);
   later also a step-hash hook in the single executable's test build.
2. **k > 1:** scripted input plays at 60 Hz and at T compared at the same moments in real time (every k-th tick against
   every step): positions, velocities, nerve changes, jump heights, timer lengths, camera paths, within tolerances
   written per subsystem. A difference is either a missed conversion (fixed) or a ledger row.
3. Until a subsystem passes, the game stays at k = 1 for players; higher rates unlock when all of it passes.

## Order

0. The loop: the host runs the game at T with k passed to the game; renders each tick as it is made (no in-between
   pictures); input read once per tick. Everything unconverted runs k times too fast: the visible to-do list.
1. Central helpers: `NerveUtil.cpp`, `LiveActor::movement`, the velocity helpers (`ActorMovementUtil.cpp`), animation
   frame control, NebulaFrameClock. Converts a large share of every subsystem's sites at once.
2. Player (Mario): the most hand-written physics (224 counters, 71 decays, 291 velocity sites).
3. Camera.
4. Enemy, MapObj, Boss, NPC, Ride, Map.
5. Screen and layouts (2D timers and animations), effects and particles, demos.
6. Sound timing that counts steps (the mixer itself already runs on its own real-time clock).
