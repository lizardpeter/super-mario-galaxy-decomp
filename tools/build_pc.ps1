<#
.SYNOPSIS
Builds the PC port (port/, Nebula) for Windows in one command: Nebula.exe (Direct3D 12), NebulaVk.exe (Vulkan),
NebulaD11.exe (Direct3D 11), the game module compiled from the decomp (smg_game.dll) and the game importer, all in
one folder ready to run. Linux: tools/build_pc.sh.

.DESCRIPTION
  .\tools\build_pc.ps1 [-Out build\pc\windows] [-Llvm <LLVM bin folder>] [-Game <disc image or game folder>]
                       [-Baseline]

  -Llvm      LLVM 21 or later. Default: C:\Program Files\LLVM\bin if it has clang-cl.exe, else a pinned LLVM
             downloaded once into .cache\ (docs/pc-build.md).
  -Game      also import the game into <Out>\content\game.pak (RMGE01, RMGP01 or RMGJ01; ISO, RVZ, WIA, WBFS, CISO,
             GCZ or an extracted folder).
  -Baseline  also build the x86-64-v2 programs, for CPUs without AVX2.

Needs Visual Studio 2022 with the C++ tools and a Windows SDK (it brings CMake and Ninja), Rust stable with the
MSVC target, and Python 3. Nothing is installed system-wide and no environment variable outlives this session.
#>
param(
    [string]$Out = "build\pc\windows",
    [string]$Llvm = "",
    [string]$Game = "",
    [switch]$Baseline
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$port = Join-Path $root "port"
$LlvmVersion = "22.1.6"
if (-not [System.IO.Path]::IsPathRooted($Out)) { $Out = Join-Path $root $Out }

function Invoke-Checked([string]$exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { throw "$exe failed ($LASTEXITCODE)" }
}

. (Join-Path $port "tools\enter_msvc_environment.ps1") | Out-Null

if (-not $Llvm) {
    $default = "C:\Program Files\LLVM\bin"
    if (Test-Path (Join-Path $default "clang-cl.exe")) {
        $Llvm = $default
    } else {
        $folder = Join-Path $root ".cache\clang+llvm-$LlvmVersion-x86_64-pc-windows-msvc"
        if (-not (Test-Path (Join-Path $folder "bin\clang-cl.exe"))) {
            Write-Host "Downloading LLVM $LlvmVersion (once, into .cache\)"
            New-Item -ItemType Directory -Force -Path (Join-Path $root ".cache") | Out-Null
            $archive = "$folder.tar.xz"
            Invoke-Checked "curl.exe" @("-fL", "--retry", "3", "-o", $archive,
                "https://github.com/llvm/llvm-project/releases/download/llvmorg-$LlvmVersion/clang+llvm-$LlvmVersion-x86_64-pc-windows-msvc.tar.xz")
            New-Item -ItemType Directory -Force -Path $folder | Out-Null
            Invoke-Checked "tar.exe" @("-xJf", $archive, "-C", $folder, "--strip-components=1")
            Remove-Item $archive
        }
        $Llvm = Join-Path $folder "bin"
    }
}

# The host: three renderers.
$hostBuild = Join-Path $Out "host"
Push-Location $port
try {
    Invoke-Checked "cmake" @("-S", ".", "-B", $hostBuild, "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release",
        "-DNEBULA_VULKAN=ON", "-DNEBULA_D3D11=ON")
    Invoke-Checked "cmake" @("--build", $hostBuild, "--target", "Nebula", "NebulaVk", "NebulaD11")
    if ($Baseline) {
        $baseBuild = Join-Path $Out "host-x86-64-v2"
        Invoke-Checked "cmake" @("-S", ".", "-B", $baseBuild, "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release",
            "-DNEBULA_VULKAN=ON", "-DNEBULA_D3D11=ON", "-DNEBULA_HOST_BASELINE=ON")
        Invoke-Checked "cmake" @("--build", $baseBuild, "--target", "Nebula", "NebulaVk", "NebulaD11")
    }

    # The game module: the decomp's game code (port/native/petari) compiled with clang for x64.
    $gameBuild = Join-Path $Out "game"
    $gameArgs = @("-Petari", "native\petari", "-Build", $gameBuild, "-Llvm", $Llvm, "-Target", "all")
    if (-not $Baseline) { $gameArgs += "-NoBaseline" }
    & (Join-Path $port "native\build.ps1") @gameArgs
    if ($LASTEXITCODE -ne 0) { throw "native\build.ps1 failed ($LASTEXITCODE)" }

    # The importer.
    $cargoTarget = Join-Path $Out "cargo"
    Invoke-Checked "cargo" @("build", "--release", "--locked", "-p", "nebula-import", "--target-dir", $cargoTarget)
} finally {
    Pop-Location
}

# One folder to run from.
$bin = Join-Path $Out "bin"
New-Item -ItemType Directory -Force -Path $bin | Out-Null
foreach ($name in "Nebula.exe", "NebulaVk.exe", "NebulaD11.exe") { Copy-Item (Join-Path $hostBuild $name) $bin -Force }
foreach ($sub in "D3D12", "glslang") {
    $from = Join-Path $hostBuild $sub
    if (Test-Path $from) { Copy-Item $from $bin -Recurse -Force }
}
if ($Baseline) {
    foreach ($name in "Nebula-x86-64-v2.exe", "NebulaVk-x86-64-v2.exe", "NebulaD11-x86-64-v2.exe") {
        Copy-Item (Join-Path $baseBuild $name) $bin -Force
    }
}
foreach ($name in "smg_game.dll", "smg_game_plain.dll") {
    $from = Join-Path $gameBuild $name
    if (Test-Path $from) { Copy-Item $from $bin -Force }
}
if ($Baseline) { Copy-Item (Join-Path $gameBuild "x86-64-v2") $bin -Recurse -Force }
Copy-Item (Join-Path $cargoTarget "release\nebula-import.exe") $bin -Force

if ($Game) {
    $content = Join-Path $Out "content"
    Invoke-Checked (Join-Path $bin "nebula-import.exe") @("identify", $Game)
    Invoke-Checked (Join-Path $bin "nebula-import.exe") @("import", $Game, "--output", $content)
}

Write-Host ""
Write-Host "Built: $bin"
Write-Host "Run:   & '$bin\Nebula.exe' --pak '$Out\content\game.pak' --saves `"`$env:LOCALAPPDATA\Nebula\saves`""
