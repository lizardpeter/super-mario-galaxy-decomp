#!/usr/bin/env python3
"""Inventory every place the game's code assumes 60 steps a second (docs/fixed-tick.md).

    python3 tools/tick/inventory.py

Reads the PC build's game code (port/native/petari/src and include) and writes:
  analysis/tick/sites.tsv   one row per matching line: subsystem, file, line, function, category, central, the line
  analysis/tick/summary.md  counts per category and per subsystem, and the central functions

It is a search, not a proof: a pattern finds the usual ways the code says "per step", and the conversion reads every
site it names. A row is `timed` when its line already names its duration in time (Nebula's stepsOfSeconds /
stepsOfMilliseconds): it converts by itself once NebulaFrameClock's steps per second is the tick rate. A site is
`central` when it is the definition of a helper that the rest of the game calls (converting
it converts its callers); its callers are counted as `via-helper` and need no change of their own unless they pass a
step count, which their own row says.
"""
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / "port" / "native" / "petari"
OUT = ROOT / "analysis" / "tick"

# category -> (pattern, what converting it means)
CATEGORIES = {
    "nerve-step": (r"\bMR::is(?:Greater|Less|GreaterEqual|LessEqual|Interval)?Step\s*\(|\bgetNerveStep\s*\(\s*\)\s*[<>=!]=?",
                   "a duration in steps: compared against the nerve's step count, which counts ticks; the count it is "
                   "compared with is scaled by ticks per 60 Hz step (exact when the tick is a multiple of 60)"),
    "nerve-rate": (r"\bMR::calcNerve\w*\s*\(",
                   "a ramp over N steps: same scaling of N"),
    "velocity": (r"\bmVelocity\b|\bMR::\w*Velocity\w*\s*\(",
                 "a velocity in units per 60 Hz step: applied as velocity / k per tick; changes to it (acceleration, "
                 "gravity) likewise per tick"),
    "position-step": (r"\bmPosition\s*[+-]=|\bmPosition\.(?:add|sub)\s*\(",
                      "a position moved by a per-step amount"),
    "decay": (r"\*=\s*\(?\s*0\.\d+f?\b|\.(?:scale|mult)\s*\(\s*0\.\d+f?\s*[,)]",
              "a factor applied each step (friction, damping): becomes factor^(1/k) per tick"),
    "approach": (r"\(\s*[\w.\[\]>:-]+\s*-\s*[\w.\[\]>:-]+\s*\)\s*\*\s*0\.\d+f?|\b0\.\d+f?\s*\*\s*\(\s*[\w.\[\]>:-]+\s*-\s*[\w.\[\]>:-]+\s*\)"
                 r"|\bMR::(?:lerp|vecBlend\w*|blendVec\w*|getEaseIn\w*|getEaseOut\w*|turnVec\w*|rotateVec\w*)\s*\(",
                 "a step toward a target by a fraction each step: the fraction becomes 1-(1-f)^(1/k) per tick"),
    "counter": (r"\bm\w*(?:Timer|Time|Count|Counter|Frame|Step|Wait|Delay|Interval)\w*\s*(?:\+\+|--|[+-]=)"
                r"|(?:\+\+|--)\s*m\w*(?:Timer|Time|Count|Counter|Frame|Step|Wait|Delay|Interval)\w*\b",
                "a hand-kept counter of steps: counts ticks and its limits scale, or counts time"),
    "anim-rate": (r"\b(?:setRate|setFrame|getFrame|getRate|setSpeed|setPlaySpeed)\s*\(|\bJ3DFrameCtrl\b",
                  "animation advanced by a rate per step: the frame control advances rate / k per tick"),
    "random": (r"\bMR::(?:getRandom\w*|isHalfProbability|isRandom\w*)\s*\(",
               "a chance taken each step: per tick it becomes 1-(1-p)^(1/k), or the draw happens once per 60 Hz step"),
    "literal-60": (r"[*/]\s*60(?:\.0)?f?\b|\b60(?:\.0)?f?\s*[*/]",
                   "an explicit 60 (steps per second) in arithmetic"),
    "frame-clock": (r"\bstepsOf\w+\s*\(|\bsecondsOfSteps\s*\(|\bcStepsPerSecond\b|\bNebulaFrameClock::count\s*\(",
                    "a duration Nebula already wrote in seconds or milliseconds (stepsOfSeconds): converts by itself "
                    "once steps per second is the tick rate"),
}
COMPILED = {name: re.compile(pattern) for name, (pattern, _) in CATEGORIES.items()}
# Helpers whose definitions carry the timing for every caller.
CENTRAL_FILES = {"src/Game/Util/NerveUtil.cpp", "src/Game/Util/ActorMovementUtil.cpp", "src/Game/LiveActor/LiveActor.cpp",
                 "src/Game/System/NebulaFrameClock.cpp", "src/Game/System/GameSystem.cpp"}
TIMED = re.compile(r"\bstepsOf\w+\s*\(|\bsecondsOfSteps\s*\(")
FUNC = re.compile(r"^\s*(?:[\w:<>,*&\s]+?\s)?([\w:~]+)\s*\([^;]*\)\s*(?:const\s*)?\{\s*$")


def subsystem(rel):
    parts = Path(rel).parts
    if len(parts) >= 3 and parts[1] == "Game":
        return f"Game/{parts[2]}"
    return parts[1] if len(parts) > 1 else rel


def strip_comment(line):
    i = line.find("//")
    return line if i < 0 else line[:i]


def main():
    rows = []
    for path in sorted(p for p in GAME.rglob("*") if p.suffix in (".cpp", ".c", ".hpp", ".h")):
        rel = path.relative_to(GAME).as_posix()
        if not (rel.startswith("src/") or rel.startswith("include/")):
            continue
        function = ""
        in_block_comment = False
        for number, raw in enumerate(path.read_text(errors="replace").splitlines(), 1):
            line = raw
            if in_block_comment:
                if "*/" not in line:
                    continue
                line, in_block_comment = line.split("*/", 1)[1], False
            if "/*" in line and "*/" not in line.split("/*", 1)[1]:
                line, in_block_comment = line.split("/*", 1)[0], True
            line = strip_comment(line)
            if m := FUNC.match(line):
                function = m.group(1)
            for name, rx in COMPILED.items():
                if rx.search(line):
                    rows.append({"subsystem": subsystem(rel), "file": rel, "line": number, "function": function,
                                 "category": name, "central": "central" if rel in CENTRAL_FILES else "",
                                 "timed": "timed" if TIMED.search(line) else "",
                                 "text": line.strip()[:160].replace("\t", " ")})
    OUT.mkdir(parents=True, exist_ok=True)
    fields = ["subsystem", "file", "line", "function", "category", "central", "timed", "text"]
    with open(OUT / "sites.tsv", "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(fields) + "\n")
        for r in rows:
            f.write("\t".join(str(r[k]) for k in fields) + "\n")

    by_cat = Counter(r["category"] for r in rows)
    files_by_cat = defaultdict(set)
    for r in rows:
        files_by_cat[r["category"]].add(r["file"])
    by_sub = defaultdict(Counter)
    for r in rows:
        by_sub[r["subsystem"]][r["category"]] += 1
    files_total = len({r["file"] for r in rows})
    cats = list(CATEGORIES)
    out = ["# Fixed-tick inventory", "",
           "_Generated by `tools/tick/inventory.py` from `port/native/petari`. Do not edit._", "",
           f"{len(rows):,} matching lines in {files_total:,} files. A search, not a proof: each site is read when its "
           "subsystem is converted (docs/fixed-tick.md).", "",
           f"{sum(1 for r in rows if r['timed']):,} of them already name their duration in time (`timed`: converts by "
           f"itself); {sum(1 for r in rows if not r['timed']):,} need reading.", "",
           "## By category", "", "| category | lines | already timed | files | converting it |", "|---|---:|---:|---:|---|"]
    timed_by_cat = Counter(r["category"] for r in rows if r["timed"])
    for c in cats:
        out.append(f"| `{c}` | {by_cat[c]:,} | {timed_by_cat[c]:,} | {len(files_by_cat[c]):,} | {CATEGORIES[c][1]} |")
    out += ["", "## By subsystem", "",
            "| subsystem | total | " + " | ".join(f"`{c}`" for c in cats) + " |",
            "|---|---:|" + "---:|" * len(cats)]
    for sub, cc in sorted(by_sub.items(), key=lambda kv: -sum(kv[1].values())):
        out.append(f"| `{sub}` | {sum(cc.values()):,} | " + " | ".join(f"{cc[c]:,}" if cc[c] else "" for c in cats) + " |")
    central = sorted({(r["file"], r["function"]) for r in rows if r["central"] and r["function"]})
    out += ["", "## Central functions (their callers convert with them)", ""]
    out += [f"- `{fn}` ({f})" for f, fn in central]
    out.append("")
    (OUT / "summary.md").write_text("\n".join(out))
    print("\n".join(out[:22]))


if __name__ == "__main__":
    main()
