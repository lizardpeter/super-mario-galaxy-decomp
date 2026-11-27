"""Shared model: config, status ladder, TSV helpers, the function inventory."""
import csv
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LADDER = ["located", "named", "typed", "decompiled", "compiles", "matches", "integrated"]


def config():
    return tomllib.loads((ROOT / "target.toml").read_text())


def build(build_id):
    return next(b for b in config()["build"] if b["id"] == build_id)


def read_tsv(path):
    path = Path(path)
    if not path.is_file():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


def write_tsv(path, fields, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fields, delimiter="\t", quoting=csv.QUOTE_NONE, escapechar="\\", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def va(n):
    """The repo's one address format: upper-case hex, 8 digits, no 0x (80030D0C)."""
    return f"{int(n):08X}"


@dataclass
class Function:
    build: str
    va: str
    size: int
    name: str
    unit: str
    source: str
    fuzzy: float
    in_port: bool
    status: str
    subsystem: str


def load(build_id):
    """analysis/<build>/functions.tsv as {va: Function}."""
    out = {}
    for r in read_tsv(ROOT / "analysis" / build_id / "functions.tsv"):
        out[r["va"]] = Function(build_id, r["va"], int(r["size"]), r["name"], r["unit"], r["source"],
                                float(r["fuzzy"]), r["in_port"] == "1", r["status"], r["subsystem"])
    return out
