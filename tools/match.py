#!/usr/bin/env python3
"""Build the faithful decomp (decomp/, Petari) for one disc, compare it with the original, write analysis/<build>/.

    python3 tools/match.py <build> [--no-build]

1. Verifies the original main.dol (tools/fetch_originals.py puts it in decomp/orig/<build>/sys/).
2. Runs Petari's own build: `configure.py --version <build>` then `ninja`, which compiles every source file with
   the original CodeWarrior compilers, relinks main.dol and checks its SHA-1 against the retail disc
   (decomp/config/<build>/build.sha1), then `ninja build/<build>/report.json` (objdiff: every function of the
   compiled objects compared with the original's).
3. Writes, from those results only:
     analysis/<build>/summary.json   what the build proved: relinked main.dol hash, toolchain tags, objdiff measures
     analysis/<build>/units.tsv      one row per translation unit
     analysis/<build>/functions.tsv  one row per function in decomp/config/<build>/symbols.txt, with its status

--no-build reuses decomp/build/<build>/ from an earlier run (it must exist).

Function status (the ladder in AGENTS.md), each step from evidence in this run:
  located     in symbols.txt with an address and size
  named       its symbol is a real name, not an auto label (fn_/func_/lbl_)
  typed       its prototype is known: a mangled C++ signature, or its unit has source
  decompiled  its unit has a source file in decomp/src/
  compiles    the compiled object contains it (objdiff found it: match > 0%)
  matches     objdiff: 100% identical instructions and relocations to the original
  integrated  matches, and its source file is compiled into the PC build (port/native/petari/)
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from model import ROOT, build, va, write_tsv

DECOMP = ROOT / "decomp"
PORT_PETARI = ROOT / "port" / "native" / "petari"
AUTO = re.compile(r"^(fn|func|lbl|sub|zz)_[0-9A-Fa-f]+")
SYMBOL = re.compile(r"^(\S+) = (\.[\w.]+):0x([0-9A-Fa-f]+); // (.*)$")
SPLIT_UNIT = re.compile(r"^(\S.*):\s*$")
SPLIT_SECTION = re.compile(r"^\s+(\.\w+)\s+start:0x([0-9A-Fa-f]+) end:0x([0-9A-Fa-f]+)")


def sha1(path):
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()


def run(cmd, log):
    print("+", " ".join(map(str, cmd)), flush=True)
    with open(log, "a", encoding="utf-8") as f:
        p = subprocess.run(cmd, cwd=DECOMP, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        f.write(p.stdout)
    if p.returncode:
        sys.stdout.write(p.stdout[-4000:])
        sys.exit(f"{cmd[0]} failed ({p.returncode}); full log in {log}")
    return p.stdout


def functions_from_symbols(version):
    out = []
    for line in (DECOMP / "config" / version / "symbols.txt").read_text().splitlines():
        m = SYMBOL.match(line)
        if not m or "type:function" not in m.group(4):
            continue
        size = re.search(r"size:0x([0-9A-Fa-f]+)", m.group(4))
        out.append((int(m.group(3), 16), int(size.group(1), 16) if size else 0, m.group(1), m.group(2)))
    return out


def text_ranges(version):
    """[(start, end, unit source path)] for every code section in splits.txt."""
    ranges, unit = [], None
    for line in (DECOMP / "config" / version / "splits.txt").read_text().splitlines():
        if m := SPLIT_UNIT.match(line):
            unit = None if m.group(1) == "Sections" else m.group(1)
        elif unit and (m := SPLIT_SECTION.match(line)) and m.group(1) in (".text", ".init"):
            ranges.append((int(m.group(2), 16), int(m.group(3), 16), unit))
    return sorted(ranges)


def subsystem(path):
    parts = path.split("/")
    if parts[0] == "src":
        parts = parts[1:]
    return "/".join(parts[:2]) if parts and parts[0] == "Game" else (parts[0] if parts else "_unsplit")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("build")
    ap.add_argument("--no-build", action="store_true")
    a = ap.parse_args()
    b = build(a.build)
    v = a.build
    orig = DECOMP / "orig" / v / "sys" / "main.dol"
    if not orig.is_file() or sha1(orig) != b["dol"]["sha1"]:
        sys.exit(f"{orig} missing or wrong; run: python3 tools/fetch_originals.py {v}")
    out = ROOT / "analysis" / v
    (out / "logs").mkdir(parents=True, exist_ok=True)
    log = out / "logs" / "build.log"
    bdir = DECOMP / "build" / v
    if not a.no_build:
        log.write_text("")
        run([sys.executable, "configure.py", "--version", v], log)
        run(["ninja"], log)  # the default target relinks main.dol and checks build.sha1
        run(["ninja", f"build/{v}/report.json"], log)
    relinked = bdir / "main.dol"
    if not relinked.is_file():
        sys.exit(f"{relinked} missing: the build did not finish")
    relinked_sha1 = sha1(relinked)
    report = json.loads((bdir / "report.json").read_text())
    tags = {k: re.search(rf'config\.{k} = "([^"]+)"', (DECOMP / "configure.py").read_text()).group(1)
            for k in ("dtk_tag", "objdiff_tag", "compilers_tag", "binutils_tag")}

    # Units
    units, by_va = [], {}
    for u in report["units"]:
        meta = u.get("metadata", {})
        src = meta.get("source_path", "")
        m = u.get("measures", {})
        in_port = bool(src) and (PORT_PETARI / src).is_file()
        units.append({
            "unit": u["name"], "source": src, "complete": int(bool(meta.get("complete"))),
            "in_port": int(in_port),
            "functions": m.get("total_functions", 0), "matched_functions": m.get("matched_functions", 0),
            "code": m.get("total_code", 0), "matched_code": m.get("matched_code", 0),
            "fuzzy": round(m.get("fuzzy_match_percent", 0.0), 3),
        })
        for f in u.get("functions", []):
            addr = int(f.get("metadata", {}).get("virtual_address", -1))
            if addr >= 0:
                by_va[addr] = (u["name"], src, float(f.get("fuzzy_match_percent", 0.0)), in_port)

    # Functions
    ranges = text_ranges(v)
    starts = [r[0] for r in ranges]
    rows = []
    import bisect
    for addr, size, name, section in functions_from_symbols(v):
        unit, src, fuzzy, in_port = by_va.get(addr, ("", "", 0.0, False))
        if not unit:
            i = bisect.bisect_right(starts, addr) - 1
            if i >= 0 and ranges[i][0] <= addr < ranges[i][1]:
                unit = "main/" + re.sub(r"\.(c|cpp|s)$", "", ranges[i][2])
        has_src = bool(src) and (DECOMP / src).is_file()
        mangled = "__" in name and re.search(r"F[A-Za-z0-9]*$", name.split("__", 1)[1] if "__" in name else "")
        steps = [True, not AUTO.match(name), bool(mangled) or has_src, has_src, has_src and fuzzy > 0,
                 has_src and fuzzy >= 100.0, has_src and fuzzy >= 100.0 and in_port]
        status = "located"
        for s, ok in zip(["located", "named", "typed", "decompiled", "compiles", "matches", "integrated"], steps):
            if not ok:
                break
            status = s
        rows.append({"va": va(addr), "size": size, "section": section, "name": name, "unit": unit, "source": src,
                     "fuzzy": f"{fuzzy:.2f}".rstrip("0").rstrip("."), "in_port": int(in_port), "status": status,
                     "subsystem": subsystem(src or unit.removeprefix("main/"))})

    write_tsv(out / "units.tsv", list(units[0]), sorted(units, key=lambda r: r["unit"]))
    write_tsv(out / "functions.tsv", list(rows[0]), rows)
    summary = {
        "build": v,
        "original_sha1": b["dol"]["sha1"],
        "relinked_sha1": relinked_sha1,
        "relinked_identical": relinked_sha1 == b["dol"]["sha1"],
        "decomp_commit": __import__("model").config()["upstream"]["decomp"]["commit"],
        "toolchain": tags,
        "measures": report["measures"],
        "categories": {c["id"]: c["measures"] for c in report.get("categories", [])},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("relinked_identical", "relinked_sha1")}),
          f"{report['measures']['matched_functions']}/{report['measures']['total_functions']} functions match")
    if not summary["relinked_identical"]:
        sys.exit("relinked main.dol differs from the original")


if __name__ == "__main__":
    main()
