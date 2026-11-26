"""Answer key for the head-to-head, computed only from the exported BloodHound CSV files.

Independent of apm/: plain Python over the CE export. Exposure questions use reachability over
BloodHound's attack-path edges. The Entra fix question is brute-forced: for every non-Tier Zero
principal holding an edge into Tier Zero, remove its edges into Tier Zero and recount.
Run: python3 eval/gold.py EXPORT_DIR > eval/gold.json
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

IDENTITY = {"User", "Computer", "AZUser", "AZDevice", "AZServicePrincipal", "AZApp", "AZManagedIdentity",
            "AZAutomationAccount", "AZLogicApp", "AZFunctionApp", "AZWebApp"}


def load(root, platform):
    nodes = {r["objectid"]: r for r in csv.DictReader(open(root / f"{platform}_nodes.csv"))}
    edges = [(r["source"], r["relationship"], r["target"]) for r in csv.DictReader(open(root / f"{platform}_edges.csv"))]
    return nodes, edges


def t0(nodes, oid):
    return nodes.get(oid, {}).get("tier_zero") == "True"


def can_reach_t0(nodes, edges, skip=frozenset()):
    """Non-Tier Zero objects with any attack path into Tier Zero, ignoring boundary edges in skip."""
    incoming = defaultdict(set)
    for s, k, t in edges:
        if t0(nodes, s):
            continue  # a path that has already entered Tier Zero adds nothing
        if t0(nodes, t) and (s, k, t) in skip:
            continue
        incoming[t].add(s)
    frontier = [oid for oid in nodes if t0(nodes, oid)]
    seen = set()
    while frontier:
        nxt = []
        for t in frontier:
            for s in incoming[t]:
                if s not in seen:
                    seen.add(s)
                    nxt.append(s)
        frontier = nxt
    return seen


def name(nodes, oid):
    return nodes[oid]["name"] or oid


def main(root):
    root = Path(root)
    ad_nodes, ad_edges = load(root, "ad")
    az_nodes, az_edges = load(root, "entra")
    key = {}
    sessions = sorted({(name(ad_nodes, t), name(ad_nodes, s)) for s, k, t in ad_edges
                       if k == "HasSession" and not t0(ad_nodes, s) and t0(ad_nodes, t)})
    key["t0-sessions"] = {"tier_zero_users": sorted({u for u, _ in sessions}), "pairs": sessions}
    key["dcsync"] = {"principals": sorted({name(ad_nodes, s) for s, k, t in ad_edges
                                           if k == "DCSync" and not t0(ad_nodes, s)})}
    df = next(o for o, n in ad_nodes.items() if n["name"] == "DF-WIN10-DEV01.PHANTOM.CORP")
    key["df-win10"] = {"tier_zero_gained": sorted({f"{k} {name(ad_nodes, t)}" for s, k, t in ad_edges
                                                   if s == df and t0(ad_nodes, t)})}
    du = next(o for o, n in ad_nodes.items() if n["name"] == "DOMAIN USERS@PHANTOM.CORP")
    key["domain-users"] = {"reaches_tier_zero": du in can_reach_t0(ad_nodes, ad_edges),
                           "direct_edges_into_tier_zero": sorted({f"{k} {name(ad_nodes, t)}" for s, k, t in ad_edges
                                                                  if s == du and t0(ad_nodes, t)})}
    broad = {"EVERYONE@PHANTOM.CORP", "AUTHENTICATED USERS@PHANTOM.CORP", "DOMAIN USERS@PHANTOM.CORP",
             "DOMAIN COMPUTERS@PHANTOM.CORP"}
    key["ad-fix-first"] = {"broad_group_edges_into_tier_zero": sorted(
        {f"{name(ad_nodes, s)} {k} {name(ad_nodes, t)}" for s, k, t in ad_edges
         if name(ad_nodes, s) in broad and t0(ad_nodes, t)})}
    reach = can_reach_t0(az_nodes, az_edges)
    key["entra-users"] = {"users_reaching_tier_zero": sum(az_nodes[o]["kind"] == "AZUser" for o in reach),
                          "identities_reaching_tier_zero": sum(az_nodes[o]["kind"] in IDENTITY for o in reach)}
    boundary = defaultdict(set)
    for s, k, t in az_edges:
        if not t0(az_nodes, s) and t0(az_nodes, t):
            boundary[s].add((s, k, t))
    base = sum(az_nodes[o]["kind"] in IDENTITY for o in reach)
    results = []
    for source, owned in boundary.items():
        left = sum(az_nodes[o]["kind"] in IDENTITY for o in can_reach_t0(az_nodes, az_edges, frozenset(owned)))
        results.append((base - left, name(az_nodes, source)))
    results.sort(reverse=True)
    key["entra-fix"] = {"best_single_principal": results[0][1], "identities_removed": results[0][0],
                        "runner_up": results[1][1], "runner_up_removed": results[1][0], "identities_before": base}
    print(json.dumps(key, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
