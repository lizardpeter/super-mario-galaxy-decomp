#!/usr/bin/env python3
"""Check records/ against the evidence in analysis/. CI runs this; it exits 1 on any problem.

- records/functions.tsv: per-function notes and claims. A claimed status may not be above the status the evidence
  gives (analysis/<build>/functions.tsv); a function kept below `matches` on purpose says why in `note`.
- records/bugs.tsv and records/patches.tsv: well-formed ids, kinds, priorities, known addresses.
"""
import re
import sys

from model import LADDER, ROOT, config, load, read_tsv

KINDS = {"security", "crash", "hang", "logic", "ub", "robustness", "limit", "precision", "performance", "quality"}
PATCH_KINDS = {"bugfix", "security", "modernize", "feature"}


def main():
    errors = []
    builds = {b["id"]: load(b["id"]) for b in config()["build"]}
    for i, r in enumerate(read_tsv(ROOT / "records" / "functions.tsv"), 2):
        fns = builds.get(r["build"])
        if fns is None:
            errors.append(f"functions.tsv:{i}: unknown build {r['build']}")
            continue
        f = fns.get(r["va"])
        if f is None:
            errors.append(f"functions.tsv:{i}: {r['va']} is not a function in {r['build']}")
        elif r["status"] not in LADDER:
            errors.append(f"functions.tsv:{i}: unknown status {r['status']}")
        elif LADDER.index(r["status"]) > LADDER.index(f.status):
            errors.append(f"functions.tsv:{i}: claims {r['status']} for {f.name}; the evidence shows {f.status}")
    for i, r in enumerate(read_tsv(ROOT / "records" / "bugs.tsv"), 2):
        if not re.fullmatch(r"B\d{4}", r["id"]):
            errors.append(f"bugs.tsv:{i}: bad id {r['id']}")
        if r["kind"] not in KINDS:
            errors.append(f"bugs.tsv:{i}: bad kind {r['kind']}")
        if r["priority"] not in ("high", "medium", "low"):
            errors.append(f"bugs.tsv:{i}: bad priority {r['priority']}")
        if r["build"] in builds and r["va"] and r["va"] not in builds[r["build"]]:
            errors.append(f"bugs.tsv:{i}: {r['va']} is not a function in {r['build']}")
        if not re.fullmatch(r"planned|keep|fixed P\d{4}", r["enhanced"]):
            errors.append(f"bugs.tsv:{i}: enhanced must be planned, keep or fixed P<nnnn>")
    for i, r in enumerate(read_tsv(ROOT / "records" / "patches.tsv"), 2):
        if not re.fullmatch(r"P\d{4}", r["id"]) or r["kind"] not in PATCH_KINDS:
            errors.append(f"patches.tsv:{i}: bad id or kind")
    if errors:
        sys.exit("\n".join(errors))
    print("records ok")


if __name__ == "__main__":
    main()
