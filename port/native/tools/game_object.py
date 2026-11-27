#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Make the whole game one object file for a single-executable build (NEBULA_GAME_STATIC).

    game_object.py --objects <list file> --sources <game src folder> --llvm <LLVM bin folder> --out <game.o>
                   --table <table.c>

The game is otherwise a shared library (smg_game.dll / libsmg_game.so) because it carries its own C library and
math (math/src: memcpy, malloc, sinf..., the same results on every platform) and thousands of Wii-era global names.
Linked straight into the host those would collide with the host's. Here every game object is LLVM bitcode:

  1. llvm-link joins them into one module;
  2. opt internalizes every definition except the host's entry points (the functions the game's sources define with
     NEBULA_GAME_API), so nothing else is visible outside the object and nothing can collide, then runs the
     link-time optimization pipeline over the whole game;
  3. clang compiles that module to one native object.

The game's own C library (its objects under static_runtime/) survives step 2 whole: every function it defines is put
in llvm.compiler.used before optimization, so none is dropped as unused, and the code generator's own calls to
memcpy, sinf and the like, made after optimization, bind to the game's definitions in the same object, never the
host's.

--table writes the C file the host links beside the object: name -> address of every entry point that is defined,
which the host's find_symbol reads in place of GetProcAddress/dlsym.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path


def run(cmd):
    p = subprocess.run([str(c) for c in cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode:
        sys.stdout.write(p.stdout)
        sys.exit(f"game_object.py: {Path(cmd[0]).name} failed ({p.returncode})")
    return p.stdout


def json_name(name):
    """An LLVM IR global name: bare when it is a plain identifier, else quoted."""
    return name if re.fullmatch(r"[A-Za-z_.$][\w.$]*", name) else '"' + name.replace('"', '\\22') + '"'


def tool(llvm, name):
    for candidate in (llvm / name, llvm / f"{name}.exe"):
        if candidate.is_file():
            return candidate
    sys.exit(f"game_object.py: no {name} in {llvm} (the LLVM release archive has it; an installer's LLVM may not)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--objects", type=Path, required=True)
    ap.add_argument("--sources", type=Path, required=True)
    ap.add_argument("--llvm", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--table", type=Path, required=True)
    ap.add_argument("--opt-level", default="2")
    a = ap.parse_args()

    objects = [line.strip() for line in a.objects.read_text().splitlines() if line.strip()]
    # Every NEBULA_GAME_API definition: `NEBULA_GAME_API <type> <name>(`, possibly after extern "C".
    define = re.compile(r'NEBULA_GAME_API\s+[\w\s\*]*?\b(\w+)\s*\(')
    api = sorted({m.group(1) for f in a.sources.rglob("*") if f.suffix in (".c", ".cpp")
                  for m in define.finditer(f.read_text(errors="replace"))})
    work = a.out.with_suffix("")
    linked, optimized = Path(f"{work}.linked.bc"), Path(f"{work}.opt.bc")

    # 1. One module. Every input must be bitcode: a native object here would leave its symbols outside the module.
    for obj in objects:
        with open(obj, "rb") as f:
            magic = f.read(4)
        if magic not in (b"BC\xc0\xde", b"\xde\xc0\x17\x0b"):
            sys.exit(f"game_object.py: {obj} is not LLVM bitcode (every game source must be compiled with -flto)")
    rsp = Path(f"{work}.objects.rsp")
    rsp.write_text("\n".join(f'"{o}"' for o in objects) + "\n")
    # The game's C library: every function it defines is kept (a module of its own, llvm.compiler.used).
    runtime = [o for o in objects if "static_runtime" in Path(o).parts]
    if not runtime:
        sys.exit("game_object.py: no static_runtime/ objects (the game's C library) among the objects")
    keep = set()
    for obj in runtime:
        out = run([tool(a.llvm, "llvm-nm"), "--defined-only", "--extern-only", "--format=posix", obj])
        keep |= {line.split()[0] for line in out.splitlines() if len(line.split()) >= 2 and line.split()[1] in "TtWw"}
    triple = next((l.split('"')[1] for l in run([tool(a.llvm, "llvm-dis"), runtime[0], "-o", "-"]).splitlines()
                   if l.startswith("target triple")), None)
    keep_ll = Path(f"{work}.keep.ll")
    names = sorted(keep)
    keep_ll.write_text(
        (f'target triple = "{triple}"\n' if triple else "")
        + "".join(f"declare void @{json_name(n)}()\n" for n in names)
        + f"@llvm.compiler.used = appending global [{len(names)} x ptr] ["
        + ", ".join(f"ptr @{json_name(n)}" for n in names) + '], section "llvm.metadata"\n')
    rsp.write_text(rsp.read_text() + f'"{keep_ll}"\n')
    run([tool(a.llvm, "llvm-link"), f"@{rsp}", "-o", linked])

    # 2. Only the entry points stay visible; then whole-game optimization.
    api_file = Path(f"{work}.api.txt")
    api_file.write_text("\n".join(api) + "\n")
    run([tool(a.llvm, "opt"), linked, "-o", optimized,
         f"--internalize-public-api-file={api_file}",
         f"-passes=internalize,lto<O{a.opt_level}>"])

    # 3. One native object for the target and CPU level recorded in the bitcode.
    run([tool(a.llvm, "clang"), "-c", f"-O{a.opt_level}", optimized, "-o", a.out, "-Wno-unused-command-line-argument"])

    # What stayed external and defined: the entry points the table may name.
    nm = run([tool(a.llvm, "llvm-nm"), "--defined-only", "--extern-only", "--format=just-symbols", a.out])
    defined = {s.strip() for s in nm.splitlines()}
    # COFF x86 would prefix '_'; x64 and ELF do not.
    exported = [n for n in api if n in defined]
    stray = sorted(s for s in defined if s not in set(api) and not re.match(r"^(\.|__real@|__xmm@|__ymm@|_tls_|\?\?_C@)", s))
    if stray:
        sys.exit("game_object.py: names left visible besides the entry points (they could collide with the host's):\n  "
                 + "\n  ".join(stray[:50]))
    lines = ["/* Generated by native/tools/game_object.py: the game's entry points in this executable. */",
             "#include <stddef.h>", ""]
    lines += [f"extern char {n}[];" for n in exported]
    lines += ["", "struct NebulaStaticSymbol { const char* name; void* address; };",
              "const struct NebulaStaticSymbol nebula_game_static_symbols[] = {"]
    lines += [f'    {{"{n}", (void*){n}}},' for n in exported]
    lines += ["    {NULL, NULL},", "};", ""]
    a.table.write_text("\n".join(lines))
    print(f"game_object.py: {len(objects)} objects -> {a.out.name} ({a.out.stat().st_size // 1024} KiB), "
          f"{len(exported)} entry points")


if __name__ == "__main__":
    main()
