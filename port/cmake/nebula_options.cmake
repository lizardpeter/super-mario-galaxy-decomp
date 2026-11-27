# SPDX-License-Identifier: GPL-3.0-only
# The two inputs of a release build every top-level project (the root, platform/sdl, platform/apple, native) reads the
# same way. Each is given as a CMake variable (-DNEBULA_VERSION_SUFFIX=-beta.1 -DNEBULA_MODS=OFF) or as the environment
# variable of the same name (a workflow or a script sets it once for every build it starts); the variable wins.
#
#   NEBULA_VERSION_SUFFIX  "" (a release) or "-beta.<n>": the pre-release label after the project's MAJOR.MINOR.PATCH.
#                          NEBULA_VERSION, which the title screen shows and the update check compares, is both.
#   NEBULA_PRODUCT_VERSION "" (Nebula's MAJOR.MINOR.PATCH, the root project's) or another product's MAJOR.MINOR.PATCH
#                          in its place: the single executable's (the repository's VERSION file). NEBULA_GAME_VERSION is
#                          the one in force.
#   NEBULA_MODS            ON (default): mods are supported. OFF: a build with no mod support (runtime/include/galaxy/
#                          mod_support.h): NEBULA_NO_MODS is defined for every program.
include_guard(GLOBAL)

if(NOT DEFINED NEBULA_PRODUCT_VERSION AND DEFINED ENV{NEBULA_PRODUCT_VERSION})
    set(NEBULA_PRODUCT_VERSION "$ENV{NEBULA_PRODUCT_VERSION}")
endif()
set(NEBULA_PRODUCT_VERSION "${NEBULA_PRODUCT_VERSION}" CACHE STRING "Another product's version (MAJOR.MINOR.PATCH) in place of Nebula's" FORCE)
if(NEBULA_PRODUCT_VERSION)
    if(NOT NEBULA_PRODUCT_VERSION MATCHES "^[0-9]+\\.[0-9]+\\.[0-9]+$")
        message(FATAL_ERROR "NEBULA_PRODUCT_VERSION must be MAJOR.MINOR.PATCH, not \"${NEBULA_PRODUCT_VERSION}\"")
    endif()
    set(NEBULA_GAME_VERSION "${NEBULA_PRODUCT_VERSION}")
else()
    file(STRINGS "${CMAKE_CURRENT_LIST_DIR}/../CMakeLists.txt" nebula_options_project_line REGEX "^project\\(Nebula VERSION ")
    string(REGEX MATCH "[0-9]+\\.[0-9]+\\.[0-9]+" NEBULA_GAME_VERSION "${nebula_options_project_line}")
endif()

if(NOT DEFINED NEBULA_VERSION_SUFFIX)
    set(nebula_suffix_default "")
    if(DEFINED ENV{NEBULA_VERSION_SUFFIX})
        set(nebula_suffix_default "$ENV{NEBULA_VERSION_SUFFIX}")
    endif()
    set(NEBULA_VERSION_SUFFIX "${nebula_suffix_default}" CACHE STRING "A pre-release label after the version: empty or -beta.<n>")
endif()
if(NOT NEBULA_VERSION_SUFFIX MATCHES "^(-beta\.[0-9]+)?$")
    message(FATAL_ERROR "NEBULA_VERSION_SUFFIX is empty or -beta.<n>, not '${NEBULA_VERSION_SUFFIX}'")
endif()

if(NOT DEFINED NEBULA_MODS)
    set(nebula_mods_default ON)
    if(DEFINED ENV{NEBULA_MODS})
        set(nebula_mods_default "$ENV{NEBULA_MODS}")
    endif()
    set(NEBULA_MODS "${nebula_mods_default}" CACHE BOOL "Support mods (OFF: a build with no mod support, galaxy/mod_support.h)")
endif()
if(NOT NEBULA_MODS)
    add_compile_definitions(NEBULA_NO_MODS=1)
endif()

# NEBULA_REQUIRE_FSR3 is set by a build that makes a package (the release workflow's and the check workflow's Windows, Linux and
# Android jobs; not the Mac's, whose upscaler is MetalFX). OFF (default): a build may leave AMD's FSR 3 out and says so once.
# ON: leaving it out stops the configure with the reason (cmake/fidelityfx_vk_shaders.cmake, nebula_fsr3_left_out).
if(NOT DEFINED NEBULA_REQUIRE_FSR3)
    set(nebula_require_fsr3_default OFF)
    if(DEFINED ENV{NEBULA_REQUIRE_FSR3})
        set(nebula_require_fsr3_default "$ENV{NEBULA_REQUIRE_FSR3}")
    endif()
    set(NEBULA_REQUIRE_FSR3 "${nebula_require_fsr3_default}" CACHE BOOL "A package build: leaving FSR 3 out is an error")
endif()
