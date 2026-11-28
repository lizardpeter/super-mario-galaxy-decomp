# Fixed tick: the game simulated at a fixed rate, independent of the display

Goal: the game's logic and physics run at a fixed tick rate T, chosen in the settings (120, 240 or 480 a second; 60 is
the original game), on the real-time clock. The display, the GPU and the frame rate never change what the simulation
does: the game's speed, jump heights and timings are the same at 30 fps or 1,000. Rendering is uncapped and separate.

Today (Nebula): the game steps 60 times a second; at higher refresh rates the renderer blends between the last two
steps. Nebula's audit measured 38-42 ms from input to display with VSync on, 30-34 ms off, on a 240 Hz display
(port/docs/audit-2026-11-17/F-interpolation-and-frame-unlock.md), and a game step costing about 0.65 ms of CPU.

## The loop

- **Simulation:** an accumulator on the real-time clock runs as many ticks as are due (none, one, or several after a
  slow frame, up to a cap), each advancing the game by exactly 1/T second. Input is read once per tick.
- **Rendering:** every frame is drawn at the current real time, as fast as the display and GPU allow.
  - Objects: drawn between the last two ticks at the frame's moment (interpolation, a setting: on by default). Off,
    objects show the newest tick: no extra delay, but they move in T Hz steps between frames when fps > T.
  - Camera: rotation from the newest mouse and stick input every frame (late latch), so turning shows on the next
    frame and never waits for a tick. The simulation keeps its own camera, updated each tick from the same input,
    because Mario's movement is relative to the camera: the per-frame view is the tick's camera plus the rotation
    input has added since that tick, which the next tick then takes in. The simulation never reads the per-frame view.
- **Present:** immediate flip with VSync off (tearing), mailbox as the no-tearing choice, FIFO with VSync on; the CPU
  waits for the GPU before reading input for a frame, so no frame queue builds up.
- **Later upgrade, speculative step:** each frame, copy the game state, run one tick ahead with the current input, draw
  between the real state and that tick, restore. Shows the present instead of one tick behind, using the real
  simulation; needs a whole-state snapshot, so only if the remaining tick of delay matters after measurement.

## Rules

1. **T = 60 x k, k a whole number** (120, 240, 480). Then every duration the game was authored with ("after 30 steps")
   is exactly 30 x k ticks: no rounding anywhere. T is chosen for latency and CPU cost, not to match the display.
2. **k = 1 is the original game, bit for bit.** Every converted code path reduces to the original arithmetic at k = 1
   (where a formula would not be bit-identical, e.g. `powf(f, 1.0f)`, the k = 1 path is the original expression). The
   proof is Nebula's step-hash recordings (`port/tests/replays`: the hash of every live actor after every step, 20
   galaxies): they must still match.
3. **Values keep their authored units.** Speeds stay "units per 60 Hz step", timers "60 Hz steps", factors "per 60 Hz
   step", as the game's code and data (BCSV tables, archives) say them. The conversion happens where a value is
   applied, once per tick: data and most code stay as written.
4. **The simulation is deterministic and reads no real-world clock.** Time inside the game is the tick count. That
   keeps replays exact at every k, and is what netcode needs later (rollback or server-authoritative).
5. **The clock is real time.** The tick runs on the host's clock, never the display's.

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

0. The loop: the host steps the game at T on the real-time clock (accumulator) with k passed to the game, input read
   per tick, rendering per frame from the newest tick (interpolation and the per-frame camera come in step 7).
   Everything unconverted runs k times too fast: the visible to-do list. k = 1 stays the default.
1. Central helpers: `NerveUtil.cpp`, `LiveActor::movement`, the velocity helpers (`ActorMovementUtil.cpp`), animation
   frame control, NebulaFrameClock. Converts a large share of every subsystem's sites at once.
2. Player (Mario): the most hand-written physics (224 counters, 71 decays, 291 velocity sites).
3. Camera.
4. Enemy, MapObj, Boss, NPC, Ride, Map.
5. Screen and layouts (2D timers and animations), effects and particles, demos.
6. Sound timing that counts steps (the mixer itself already runs on its own real-time clock).
7. Rendering: interpolation between ticks (on/off), the per-frame camera, present modes and the GPU wait.
8. Later: the speculative step, if measurement says the remaining tick of delay matters.
