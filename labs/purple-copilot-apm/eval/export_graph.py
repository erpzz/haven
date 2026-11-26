"""Export BloodHound CE's graph as plain CSV files for the stock-Hermes comparison arm.

The stock arm receives the same BloodHound data the Purple Copilot tools read, without Haven's
analysis: every object with its name, kind and Tier Zero tag, and every traversable attack-path
edge (CE's AD_ATTACK_PATHS and AZ_ATTACK_PATHS sets).
Run from the lab directory: APM_STATE=... python3 eval/export_graph.py OUT_DIR
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apm.graph import _signed, verify_reader  # noqa: E402

PAGE = 100000
SETS = {"ad": ("Base", "AD_ATTACK_PATHS"), "entra": ("AZBase", "AZ_ATTACK_PATHS")}
GENERIC = {"Base", "AZBase"}


def rows(query, width):
    values = [x["value"] for x in _signed("POST", "/api/v2/graphs/cypher", json.dumps(
        {"query": query, "include_properties": False}).encode())["data"].get("literals") or []]
    return [values[i:i + width] for i in range(0, len(values), width)]


def paged(query, width):
    out, skip = [], 0
    while True:
        page = rows(f"{query} SKIP {skip} LIMIT {PAGE}", width)
        out += page
        if len(page) < PAGE:
            return out
        skip += PAGE


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    verify_reader()
    manifest = {}
    for platform, (base, edges) in SETS.items():
        nodes = paged(f"MATCH (n:{base}) RETURN n.objectid AS id, n.name AS name, labels(n) AS kinds ORDER BY id", 3)
        node_file = out / f"{platform}_nodes.csv"
        with node_file.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["objectid", "name", "kind", "tier_zero"])
            for oid, name, kinds in nodes:
                kinds = kinds or []
                specific = [k for k in kinds if k not in GENERIC and not k.startswith("Tag_")]
                w.writerow([oid, name or "", specific[0] if specific else base, "Tag_Tier_Zero" in kinds])
        links = paged(f"MATCH (a:{base})-[r:{edges}]->(b:{base}) RETURN a.objectid AS s, type(r) AS k, "
                      f"b.objectid AS t ORDER BY s, k, t", 3)
        edge_file = out / f"{platform}_edges.csv"
        with edge_file.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["source", "relationship", "target"])
            w.writerows(links)
        manifest[platform] = {"nodes": len(nodes), "edges": len(links)}
        for file in (node_file, edge_file):
            manifest[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
    (out / "README.txt").write_text(
        "BloodHound CE 9.10.1 export of the SpecterOps public sample environment (PhantomCorp).\n"
        "ad_* covers Active Directory and entra_* covers Entra ID (Azure).\n"
        "*_nodes.csv: objectid, name, kind, tier_zero (True when BloodHound tags the object Tier Zero).\n"
        "*_edges.csv: source objectid, relationship, target objectid. These are BloodHound's traversable\n"
        "attack-path relationships: control of the source lets an attacker gain the target.\n")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
