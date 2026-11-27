// SPDX-License-Identifier: GPL-3.0-only
// The program's name where the player sees it: the window's title (and so the taskbar's), its message boxes. The
// self-contained executable (NEBULA_SELF_CONTAINED: smg.exe) is the game itself, Super Mario Galaxy; Nebula's own
// programs are Nebula.
#pragma once

namespace galaxy {

#if defined(NEBULA_SELF_CONTAINED)
inline constexpr char kProductName[] = "Super Mario Galaxy";
inline constexpr wchar_t kProductNameWide[] = L"Super Mario Galaxy";
#else
inline constexpr char kProductName[] = "Nebula";
inline constexpr wchar_t kProductNameWide[] = L"Nebula";
#endif

}  // namespace galaxy
