#pragma once

// The game's fixed tick (docs/fixed-tick.md in the repository root): its simulation runs T = 60 x k ticks a second on the
// real-time clock, whatever the display's rate. k is chosen once at start (config.ini tick_rate: 60, 120, 240 or 480)
// and never changes while the game runs; the renderer presents each tick or interpolates between them.
//
// The game was authored for 60 steps a second (nebula_game_api.h NEBULA_STEPS_PER_SECOND, checked equal by the host):
// its durations, speeds and factors stay in those units and are converted where they are applied (k = 1 is the original
// game, bit for bit).

#include <atomic>
#include <cstdint>

namespace galaxy {

// The rate the game was written for: its own numbers count steps of 1/60 s.
inline constexpr int kAuthoredStepsPerSecond = 60;
// The tick multipliers a player can choose (config.ini tick_rate = 60 x k).
inline constexpr int kTickMultipliers[] = {1, 2, 4, 8};
inline constexpr int kMostTickMultiplier = 8;

namespace detail {
inline std::atomic<int> g_tick_multiplier{1};
}

// Ticks per authored step: set once at start, before the game, the renderer or the pacing read it.
[[nodiscard]] inline int game_tick_multiplier() noexcept {
    return detail::g_tick_multiplier.load(std::memory_order_relaxed);
}
// k as chosen (a value not in kTickMultipliers is 1).
inline void set_game_tick_multiplier(int k) noexcept {
    bool known = false;
    for (const int m : kTickMultipliers) known = known || m == k;
    detail::g_tick_multiplier.store(known ? k : 1, std::memory_order_relaxed);
}
// The tick rate T: ticks a second.
[[nodiscard]] inline int game_steps_per_second() noexcept {
    return kAuthoredStepsPerSecond * game_tick_multiplier();
}
[[nodiscard]] inline double game_step_rate() noexcept {
    return static_cast<double>(game_steps_per_second());
}
// One tick in nanoseconds (rounded down: a due time is kept as tick count x 1e9 / T where it accumulates).
[[nodiscard]] inline std::int64_t game_step_ns() noexcept {
    return 1000000000ll / game_steps_per_second();
}

}  // namespace galaxy
