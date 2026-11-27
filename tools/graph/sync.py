#!/usr/bin/env python3
"""Generate the graph import set for re_smg from analysis/ and records/.

    python3 tools/graph/sync.py

Writes analysis/graph/:
  *.jsonl         one JSON object per row; a table over 40 MB is split into <name>.part-NN.jsonl
  manifest.json   ordered list of {file, sha256, rows, cypher}; each cypher has one {{ROWS}} placeholder

To load: copy the folder into the Graph DB server's import directory as smg/ and run every manifest entry, in
order, with the bulk_import_file tool (graph = target.toml `graph`). Every statement is MERGE-by-key, so re-running
is safe and the graph can be dropped and rebuilt at any time.

Schema (the whole of it; change it only here):
  (:Build {id, region, dol_sha256})
  (:Subsystem {name})
  (:SourceFile {path, in_port})-[:PART_OF]->(:Subsystem)
  (:Function {key, name})                      key = mangled symbol (build-independent across regions)
  (:Function)-[:DEFINED_IN]->(:SourceFile)
  (:FunctionInstance {id, build, va, size, status, match})-[:INSTANCE_OF]->(:Function)
  (:FunctionInstance)-[:IN_BUILD]->(:Build)
  (:Bug {id, kind, priority, enhanced})-[:IN]->(:FunctionInstance)
No code text is ever stored in the graph.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model import ROOT, config, load, read_tsv  # noqa: E402

OUT = ROOT / "analysis" / "graph"
PART_BYTES = 40 << 20

SCHEMA = [
    "CREATE INDEX FOR (n:Build) ON (n.id)",
    "CREATE INDEX FOR (n:Subsystem) ON (n.name)",
    "CREATE INDEX FOR (n:SourceFile) ON (n.path)",
    "CREATE INDEX FOR (n:Function) ON (n.key)",
    "CREATE INDEX FOR (n:FunctionInstance) ON (n.id)",
    "CREATE INDEX FOR (n:Bug) ON (n.id)",
]

CYPHER = {
    "builds": "UNWIND {{ROWS}} AS r MERGE (b:Build {id:r.id}) SET b.region=r.region, b.dol_sha256=r.dol_sha256",
    "sourcefiles": "UNWIND {{ROWS}} AS r MERGE (s:Subsystem {name:r.subsystem}) "
                   "MERGE (f:SourceFile {path:r.path}) SET f.in_port=r.in_port MERGE (f)-[:PART_OF]->(s)",
    "functions": "UNWIND {{ROWS}} AS r MATCH (b:Build {id:r.build}) "
                 "MERGE (fn:Function {key:r.key}) SET fn.name=r.name "
                 "MERGE (fi:FunctionInstance {id:r.id}) SET fi.build=r.build, fi.va=r.va, fi.size=r.size, "
                 "fi.status=r.status, fi.match=r.match "
                 "MERGE (fi)-[:INSTANCE_OF]->(fn) MERGE (fi)-[:IN_BUILD]->(b) "
                 "WITH fn, r WHERE r.source <> '' "
                 "MATCH (sf:SourceFile {path:r.source}) MERGE (fn)-[:DEFINED_IN]->(sf)",
    "bugs": "UNWIND {{ROWS}} AS r MERGE (g:Bug {id:r.id}) SET g.kind=r.kind, g.priority=r.priority, "
            "g.enhanced=r.enhanced WITH g, r MATCH (fi:FunctionInstance {id:r.fn}) MERGE (g)-[:IN]->(fi)",
}


def write_jsonl(name, rows):
    lines = [json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows]
    parts, cur, size = [], [], 0
    for line in lines:
        n = len(line.encode())
        if cur and size + n > PART_BYTES:
            parts.append(cur)
            cur, size = [], 0
        cur.append(line)
        size += n
    parts.append(cur)
    out = []
    for i, part in enumerate(parts):
        path = OUT / (f"{name}.jsonl" if len(parts) == 1 else f"{name}.part-{i:02d}.jsonl")
        data = "".join(part).encode()
        path.write_bytes(data)
        out.append({"file": f"smg/{path.name}", "sha256": hashlib.sha256(data).hexdigest(), "rows": len(part),
                    "cypher": CYPHER[name.split("-")[0]]})
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.jsonl"):
        old.unlink()
    cfg = config()
    manifest = {"graph": cfg["graph"], "schema": SCHEMA, "imports": []}
    builds, files, per_build = [], {}, {}
    for b in cfg["build"]:
        fns = load(b["id"])
        if not fns:
            continue
        per_build[b["id"]] = fns
        builds.append({"id": b["id"], "region": b["region"], "dol_sha256": b["dol"]["sha256"]})
        for f in fns.values():
            if f.source:
                files[f.source] = (f.subsystem, f.in_port)
    manifest["imports"] += write_jsonl("builds", builds)
    manifest["imports"] += write_jsonl("sourcefiles", [{"path": p, "subsystem": s, "in_port": ip}
                                                       for p, (s, ip) in sorted(files.items())])
    for bid, fns in per_build.items():
        manifest["imports"] += write_jsonl(f"functions-{bid}", [
            {"id": f"{bid}:{f.va}", "build": bid, "va": f.va, "size": f.size, "status": f.status, "match": f.fuzzy,
             "key": f.name, "name": f.name, "source": f.source} for f in sorted(fns.values(), key=lambda f: f.va)])
    bugs = [{"id": r["id"], "kind": r["kind"], "priority": r["priority"], "enhanced": r["enhanced"],
             "fn": f"{r['build']}:{r['va']}"} for r in read_tsv(ROOT / "records" / "bugs.tsv")]
    if bugs:
        manifest["imports"] += write_jsonl("bugs", bugs)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for m in manifest["imports"]:
        print(f"{m['rows']:>8}  {m['file']}")


if __name__ == "__main__":
    main()
