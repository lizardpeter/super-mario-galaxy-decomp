// SPDX-License-Identifier: GPL-3.0-only
// The self-contained executable on Linux (NEBULA_SELF_CONTAINED, x86-64) is built for x86-64-v3 (AVX2) only, like the
// Windows one (host_entry_win32.cpp). This file is compiled for the baseline x86-64 (platform/sdl/CMakeLists.txt) and
// tests the CPU in the first constructor that runs, before any code that may use AVX2: on a CPU without it the
// program says so and stops, instead of ending on an illegal instruction.
#if defined(__x86_64__) && !defined(__ANDROID__)
#include <cstdio>
#include <cstdlib>

namespace {

__attribute__((constructor(101))) void require_x86_64_v3() {
    __builtin_cpu_init();
    if (!__builtin_cpu_supports("x86-64-v3")) {
        std::fputs("This game needs a CPU with AVX2 (x86-64-v3): Intel Haswell (2013) or AMD Excavator (2015) or later.\n",
                   stderr);
        std::_Exit(1);
    }
}

}  // namespace
#endif
