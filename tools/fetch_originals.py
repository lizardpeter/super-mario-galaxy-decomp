#!/usr/bin/env python3
"""Download one build's originals from R2 and verify their hashes.

    python3 tools/fetch_originals.py <build> [--dest DIR] [--only dol]

Default destination is decomp/orig/<build>/sys/, where Petari's build expects main.dol (decomp/config/<build>/
config.yml). Files already there with the right hash are kept.
"""
import argparse
import hashlib
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from model import ROOT, build, config

NAMES = {"dol": "main.dol", "boot": "boot.bin", "bi2": "bi2.bin", "apploader": "apploader.img", "fst": "fst.bin"}


def digest(path, algo):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("build")
    ap.add_argument("--dest", type=Path)
    ap.add_argument("--only", action="append", choices=sorted(NAMES))
    a = ap.parse_args()
    b, cfg = build(a.build), config()
    dest = a.dest or ROOT / "decomp" / "orig" / a.build / "sys"
    dest.mkdir(parents=True, exist_ok=True)
    for role, name in NAMES.items():
        if role not in b or (a.only and role not in a.only):
            continue
        spec, out = b[role], dest / name
        if not (out.is_file() and digest(out, "sha256") == spec["sha256"]):
            url = cfg["r2_public"] + urllib.parse.quote(spec["key"])
            req = urllib.request.Request(url, headers={"User-Agent": "super-mario-galaxy-decomp/fetch"})
            with urllib.request.urlopen(req) as r, open(out, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
        for algo in ("sha256", "sha1"):
            if algo in spec and digest(out, algo) != spec[algo]:
                out.unlink()
                sys.exit(f"{algo} mismatch for {spec['key']}")
        print(f"{role}: {out} ok")


if __name__ == "__main__":
    main()
