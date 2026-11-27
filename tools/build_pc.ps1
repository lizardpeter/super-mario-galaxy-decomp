<#
.SYNOPSIS
Builds the game for Windows as one self-contained executable: build\pc\windows\SMG\smg.exe. It reads only game.pak
beside itself and writes only into its own folder (saves\, data\). Vulkan; no mods. Linux: tools/build_pc.sh.

.DESCRIPTION
  .\tools\build_pc.ps1 [-Out build\pc\windows] [-Game <game folder or disc image>]

  -Game  also make <Out>\SMG\game.pak from your game: the folder holding DATA and UPDATE (or DATA itself), or a disc
         image (ISO, RVZ, WIA, WBFS, CISO, GCZ) of RMGE01, RMGP01 or RMGJ01. Needed once.

The game is <Out>\SMG (smg.exe, then game.pak, saves\ and data\ beside it): move that folder anywhere. The importer that
makes game.pak is <Out>\importer\nebula-import.exe, a tool of its own; the game never runs it.

Needs Visual Studio 2022 with the C++ tools and a Windows SDK (it brings CMake and Ninja), Rust stable with the MSVC
target, Python 3 and Git. LLVM 22.1.6 is downloaded once into .cache\ (its release archive: the game's one-object
build needs opt and llvm-link, which LLVM's installer leaves out). Nothing is installed system-wide and no environment
variable outlives this session.
#>
param(
    [string]$Out = "build\pc\windows",
    [string]$Game = ""
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$port = Join-Path $root "port"
$LlvmVersion = "22.1.6"
if (-not [System.IO.Path]::IsPathRooted($Out)) { $Out = Join-Path $root $Out }
New-Item -ItemType Directory -Force -Path $Out | Out-Null

function Invoke-Checked([string]$exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { throw "$exe failed ($LASTEXITCODE)" }
}

. (Join-Path $port "tools\enter_msvc_environment.ps1") | Out-Null

# LLVM: the release archive, pinned.
$name = "clang+llvm-$LlvmVersion-x86_64-pc-windows-msvc"
$llvm = Join-Path $root ".cache\$name"
if (-not (Test-Path (Join-Path $llvm "bin\opt.exe"))) {
    Write-Host "Downloading LLVM $LlvmVersion (once, into .cache\)"
    New-Item -ItemType Directory -Force -Path (Join-Path $root ".cache") | Out-Null
    Invoke-Checked "curl.exe" @("-fL", "--retry", "3", "-o", "$llvm.tar.xz",
        "https://github.com/llvm/llvm-project/releases/download/llvmorg-$LlvmVersion/$name.tar.xz")
    New-Item -ItemType Directory -Force -Path $llvm | Out-Null
    # Git's tar reads .xz (Windows' own tar.exe may not); relative paths, since it reads "D:\..." as a host.
    $tar = Join-Path $env:ProgramFiles "Git\usr\bin\tar.exe"
    if (-not (Test-Path $tar)) { $tar = "tar.exe" }
    Push-Location (Join-Path $root ".cache")
    try { Invoke-Checked $tar @("-xJf", "$name.tar.xz", "-C", $name, "--strip-components=1") } finally { Pop-Location }
    Remove-Item "$llvm.tar.xz"
}
$llvmBin = (Join-Path $llvm "bin").Replace("\", "/")

# 1. The game: one object (port\native, NEBULA_GAME_STATIC), built with clang.
$gameBuild = Join-Path $Out "game"
Invoke-Checked "cmake" @("-S", (Join-Path $port "native"), "-B", $gameBuild, "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release",
    "-DCMAKE_C_COMPILER=$llvmBin/clang.exe", "-DCMAKE_CXX_COMPILER=$llvmBin/clang++.exe", "-DCMAKE_RC_COMPILER=$llvmBin/llvm-rc.exe",
    "-DNEBULA_MODS=OFF", "-DNEBULA_LUMA_HOOKS=OFF", "-DNEBULA_GAME_STATIC=ON", "-DNEBULA_CPU_LEVEL=x86-64-v3")
Invoke-Checked "cmake" @("--build", $gameBuild, "--target", "smg_game_static")

# 2. The executable: the Vulkan host with the game inside (port, NEBULA_GAME_OBJECT), built with MSVC.
$hostBuild = Join-Path $Out "host"
Invoke-Checked "cmake" @("-S", $port, "-B", $hostBuild, "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release",
    "-DNEBULA_VULKAN=ON", "-DNEBULA_D3D11=OFF", "-DNEBULA_MODS=OFF", "-DNEBULA_GAME_OBJECT=$($gameBuild.Replace('\', '/'))")
Invoke-Checked "cmake" @("--build", $hostBuild, "--target", "NebulaVk")
$smg = Join-Path $Out "SMG"
New-Item -ItemType Directory -Force -Path $smg | Out-Null
Copy-Item (Join-Path $hostBuild "smg.exe") $smg -Force

# 3. The importer, a tool of its own.
$cargoTarget = Join-Path $Out "cargo"
Push-Location $port
try { Invoke-Checked "cargo" @("build", "--release", "--locked", "-p", "nebula-import", "--bin", "nebula-import", "--target-dir", $cargoTarget) }
finally { Pop-Location }
$importer = Join-Path $Out "importer"
New-Item -ItemType Directory -Force -Path $importer | Out-Null
Copy-Item (Join-Path $cargoTarget "release\nebula-import.exe") $importer -Force

if ($Game) {
    Invoke-Checked (Join-Path $importer "nebula-import.exe") @("identify", $Game)
    # The importer writes into a folder that must not exist yet (it refuses one that does), then game.pak moves beside
    # the game.
    $import = Join-Path $Out "import"
    if (Test-Path $import) { Remove-Item -Recurse -Force $import }
    Invoke-Checked (Join-Path $importer "nebula-import.exe") @("import", $Game, "--output", $import)
    Move-Item -Force (Join-Path $import "game.pak") (Join-Path $smg "game.pak")
    Remove-Item $import
}

Write-Host ""
Write-Host "The game: $smg\smg.exe (with game.pak beside it). Move the SMG folder anywhere."
