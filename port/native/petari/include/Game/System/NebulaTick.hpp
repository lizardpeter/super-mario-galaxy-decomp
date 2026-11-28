#pragma once

// The fixed tick (docs/fixed-tick.md in the repository root): the game runs k ticks for each step of 1/60 s it was
// authored for. A nerve's counter counts ticks; the game's own numbers ("after 30 steps") stay in authored steps and are
// compared here, once for every caller. At k = 1 every function below is the original arithmetic.

#include "Game/System/NebulaFrameClock.hpp"
#include <math.h>

namespace NebulaTick {
    // k: ticks per authored step (1, 2, 4 or 8), fixed for the run.
    inline s32 multiplier() {
        return static_cast< s32 >(NebulaFrameClock::tickMultiplier());
    }

    // The authored step a tick count falls in (rounded down, also below 0: tick -1, a new nerve, is step -1).
    inline s32 stepOfTick(s32 tick) {
        const s32 k = multiplier();
        if (k == 1) {
            return tick;
        }
        return tick >= 0 ? tick / k : -((-tick + k - 1) / k);
    }

    // Authored steps as ticks.
    inline s32 ticksOfSteps(s32 steps) {
        return steps * multiplier();
    }

    // The tick that begins authored step `step`: true on one tick only, as the step was one step only.
    inline bool isStep(s32 tick, s32 step) {
        return tick == ticksOfSteps(step);
    }

    // Every `step` authored steps, on the tick each begins (0: only the first tick).
    inline bool isIntervalStep(s32 tick, s32 step) {
        return (step != 0 ? tick % ticksOfSteps(step) : tick) == 0;
    }

    // tick / (stepMax steps), not clamped: smooth at every tick rather than held for k ticks.
    inline f32 rateOfSteps(s32 tick, s32 stepMax) {
        return static_cast< f32 >(tick) / ticksOfSteps(stepMax);
    }

    // An amount added every authored step (a speed added to a position, an acceleration to a speed), for one tick:
    // x / k. Exactly x at k = 1.
    inline f32 perTick(f32 x) {
        const s32 k = multiplier();
        return k == 1 ? x : x / static_cast< f32 >(k);
    }

    // The same for a vector, in place (anything with scale(f32)).
    template < class V >
    inline void scalePerTick(V* pVec) {
        const s32 k = multiplier();
        if (k != 1) {
            pVec->scale(1.0f / static_cast< f32 >(k));
        }
    }

    // A factor applied every authored step (friction v *= f, a decay), for one tick: f^(1/k), so k ticks apply f once.
    // Exactly f at k = 1.
    inline f32 decayPerTick(f32 factor) {
        const s32 k = multiplier();
        return k == 1 ? factor : powf(factor, 1.0f / static_cast< f32 >(k));
    }
}  // namespace NebulaTick
