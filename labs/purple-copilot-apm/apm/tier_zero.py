"""Tier Zero control findings over BloodHound's own attack-path model.

A finding is one directed attack edge from a non-Tier Zero object into an object that
BloodHound CE tags as Tier Zero (``Tag_Tier_Zero``). CE decides which relationships are
traversable through its ``AD_ATTACK_PATHS`` and ``AZ_ATTACK_PATHS`` edge sets, which are the
same sets the SpecterOps query library uses. This module does not maintain a second list.

Exposure is computed locally and exactly. A reverse breadth-first expansion fetches only the
edges that point into objects able to reach a boundary source, never the whole graph. Each
source's exposure counts the non-Tier Zero objects that reach it without first passing through
Tier Zero. The deterministic priority is the number of identities (users, computers and
workloads, including the source when it is one) able to gain that control. The model has no
scoring or state-transition role.
"""
import argparse
import fcntl
import hashlib
import json
import re
from collections import Counter, defaultdict, deque
from time import perf_counter

from .graph import _signed, verify_reader
from .local import now
from .path_history import get_run, record_paths
from .paths import digest
from .samples import FILES, ROOT, read

PLATFORMS = {"ad": ("Base", "AD_ATTACK_PATHS"), "entra": ("AZBase", "AZ_ATTACK_PATHS")}
BOUNDARY_LIMIT = 5000
EXPANSION_LIMIT = 100000
BATCH = 500
OBJECT_ID = re.compile(r"[A-Za-z0-9@._/()-]{1,400}")  # Quotes and backslashes never pass.
CLASSES = {
    "users": {"User", "AZUser"},
    "computers": {"Computer", "AZDevice"},
    "workloads": {"AZServicePrincipal", "AZApp", "AZManagedIdentity", "AZAutomationAccount",
                  "AZLogicApp", "AZFunctionApp", "AZWebApp"},
    "groups": {"Group", "AZGroup", "ADLocalGroup"},
}
IDENTITY = ("users", "computers", "workloads")


class Budget(ValueError):
    """A bounded read exceeded its limit. The observation is reported as unavailable."""


def asset(platform):
    return {"key": f"tier-zero-{platform}", "platform": platform, "target": "TAG-TIER-ZERO",
            "sensitivity": "critical", "privileged": True}


def boundary_query(platform):
    base, edges = PLATFORMS[platform]
    return (f"MATCH p=(s:{base})-[:{edges}]->(t:{base}) WHERE NOT (s:Tag_Tier_Zero) "
            f"AND (t:Tag_Tier_Zero) RETURN p LIMIT {BOUNDARY_LIMIT + 1}")


def expansion_query(platform, ids):
    base, edges = PLATFORMS[platform]
    for value in ids:
        if not OBJECT_ID.fullmatch(value):
            raise ValueError("Object ID outside the permitted character set")
    listed = ", ".join(f"'{value}'" for value in ids)
    return (f"MATCH p=(a:{base})-[:{edges}]->(b:{base}) WHERE b.objectid IN [{listed}] "
            f"AND NOT (a:Tag_Tier_Zero) RETURN p LIMIT {EXPANSION_LIMIT + 1}")


def cypher(text):
    """CE answers an empty result with HTTP 404. Every other failure propagates."""
    try:
        return _signed("POST", "/api/v2/graphs/cypher",
                       json.dumps({"query": text, "include_properties": False}).encode())["data"]
    except RuntimeError as exc:
        if str(exc).endswith("returned HTTP 404"):
            return {"nodes": {}, "edges": []}
        raise


def triples(graph):
    nodes = graph.get("nodes") or {}
    out = []
    for edge in graph.get("edges") or []:
        source, target = nodes[str(edge["source"])], nodes[str(edge["target"])]
        if not source.get("objectId") or not target.get("objectId"):
            raise ValueError("Graph edge without stable object IDs")
        out.append((source["objectId"], edge["kind"], target["objectId"]))
    return out, {n["objectId"]: n for n in nodes.values() if n.get("objectId")}


def classify(kind):
    return next((name for name, kinds in CLASSES.items() if kind in kinds), "other")


def observe(platform, run=cypher):
    """Read the Tier Zero boundary and its upstream attack graph with bounded queries."""
    start = perf_counter()
    graph = run(boundary_query(platform))
    if len(graph.get("edges") or []) > BOUNDARY_LIMIT:
        raise Budget("Tier Zero boundary exceeds the read budget")
    boundary, nodes = triples(graph)
    if any(nodes[t].get("isTierZero") is False or nodes[s].get("isTierZero") for s, _, t in boundary):
        raise ValueError("Boundary edge disagrees with Tier Zero tagging")
    kinds = {oid: n.get("kind") for oid, n in nodes.items()}
    sources = {s for s, _, _ in boundary}
    seen, frontier, upstream, calls = set(sources), sorted(sources), set(), 1
    while frontier:
        found = set()
        for i in range(0, len(frontier), BATCH):
            part = run(expansion_query(platform, frontier[i:i + BATCH]))
            calls += 1
            if len(part.get("edges") or []) > EXPANSION_LIMIT:
                raise Budget("Upstream attack graph exceeds the read budget")
            edges, more = triples(part)
            for oid, n in more.items():
                if n.get("isTierZero"):
                    raise ValueError("Expansion returned a Tier Zero source")
                kinds.setdefault(oid, n.get("kind"))
            upstream.update(edges)
            found.update(s for s, _, _ in edges if s not in seen)
        seen |= found
        frontier = sorted(found)
    return dict(boundary=sorted(set(boundary)), nodes=nodes, kinds=kinds, upstream=sorted(upstream),
                calls=calls, seconds=round(perf_counter() - start, 3))


def exposure(sources, upstream, kinds):
    """Exact count, per source, of non-Tier Zero objects that can reach it."""
    incoming = defaultdict(set)
    for s, _, t in upstream:
        incoming[t].add(s)
    result, everyone = {}, set(sources)
    for source in sorted(sources):
        reached, queue = set(), deque([source])
        while queue:
            for parent in incoming[queue.popleft()] - reached - {source}:
                reached.add(parent)
                queue.append(parent)
        everyone |= reached
        counts = Counter(classify(kinds.get(oid)) for oid in reached)
        factors = {name: counts.get(name, 0) for name in (*CLASSES, "other")}
        factors["source_is_identity"] = classify(kinds.get(source)) in IDENTITY
        result[source] = factors
    population = Counter(classify(kinds.get(oid)) for oid in everyone)
    return result, {name: population.get(name, 0) for name in (*CLASSES, "other")}


def identity_sets(sources, upstream, kinds):
    """For each source, the identities (including itself) that can gain its Tier Zero control."""
    incoming = defaultdict(set)
    for s, _, t in upstream:
        incoming[t].add(s)
    out = {}
    for source in sorted(sources):
        reached, queue = set(), deque([source])
        while queue:
            for parent in incoming[queue.popleft()] - reached - {source}:
                reached.add(parent)
                queue.append(parent)
        out[source] = frozenset(x for x in reached | {source} if classify(kinds.get(x)) in IDENTITY)
    return out


def remediation_plan(sets, edges_by_source, steps=10):
    """Greedy order of fixes that cuts identity exposure fastest.

    Sources that expose exactly the same identities form one step: fixing only some of them removes
    nothing, because the identities keep a route through the rest. Each step removes every direct
    Tier Zero control edge of its sources. Identities removed are those left with no route at all.
    """
    groups = defaultdict(list)
    for source, ids in sets.items():
        if ids:
            groups[ids].append(source)
    remaining = {ids: sorted(srcs) for ids, srcs in groups.items()}
    exposed = set().union(*remaining) if remaining else set()
    plan = []
    while remaining and exposed and len(plan) < steps:
        def after(ids):
            return set().union(*(other for other in remaining if other != ids)) if len(remaining) > 1 else set()
        ranked = sorted(remaining, key=lambda ids: (-len(exposed - after(ids)),
                                                    sum(edges_by_source[x] for x in remaining[ids]), remaining[ids]))
        best = ranked[0]
        left = after(best)
        removed = len(exposed - left)
        if removed == 0:
            break
        plan.append({"sources": remaining.pop(best), "identities_removed": removed,
                     "identities_still_exposed": len(left),
                     "control_edges": sum(edges_by_source[x] for x in groups[best])})
        exposed = left
    return plan


def priority(factors):
    score = sum(factors[name] for name in IDENTITY) + int(factors["source_is_identity"])
    return {"score": score, "basis": "identities able to gain this Tier Zero control", "factors": factors}


def ingest_issues():
    ingest = read("ingest.json")
    status = ingest["status"]
    if (ingest["archives"] != FILES or status["status"] != 2 or status["total_files"] != 32
            or status["failed_files"] or status["partial_failed_files"]):
        return ["Incomplete sample ingest"], status
    return [], status


def evidence(platform, run=cypher):
    issues, status = ingest_issues()
    verify_reader()
    o = observe(platform, run)
    sources = {s for s, _, _ in o["boundary"]}
    per_source, population = exposure(sources, o["upstream"], o["kinds"])
    edges_by_source = Counter(s for s, _, _ in o["boundary"])
    plan = remediation_plan(identity_sets(sources, o["upstream"], o["kinds"]), edges_by_source)
    paths = [[list(edge)] for edge in o["boundary"]]
    involved = {oid for edge in o["boundary"] for oid in (edge[0], edge[2])}
    unresolved = sorted(s for s in per_source if o["kinds"].get(s) == "Base")
    return dict(
        asset=asset(platform), origin="ce-sample-tier-zero", observed=now(), paths=paths, issues=issues,
        query=boundary_query(platform), expansion=expansion_query(platform, ["OBJECT-ID"]),
        nodes={oid: {"label": o["nodes"][oid].get("label"), "kind": o["nodes"][oid].get("kind"),
                     "tier_zero": bool(o["nodes"][oid].get("isTierZero"))} for oid in sorted(involved)},
        exposure=per_source, population=population, remediation=plan,
        upstream={"edges": len(o["upstream"]), "objects": len({s for s, _, _ in o["upstream"]}),
                  "digest": hashlib.sha256(json.dumps(o["upstream"]).encode()).hexdigest(),
                  "calls": o["calls"], "seconds": o["seconds"]},
        notes=[f"{len(unresolved)} boundary sources are unresolved objects (kind Base)"] if unresolved else [],
        rank={digest(path): priority(per_source[path[0][0]]) for path in paths},
        receipt=dict(collector="official-archive", run=None, completed=None, complete=False,
                     ingest_job=status["id"], ingested=status["end_time"]), removals=[])


def unavailable(platform, exc):
    return dict(asset=asset(platform), origin="ce-sample-tier-zero", observed=now(), paths=[],
                query=boundary_query(platform), unavailable=True, issues=[str(exc)], removals=[], rank={},
                receipt=dict(collector="official-archive", run=None, completed=None, complete=False))


def summary(run_id):
    e, findings = get_run(run_id)
    states = Counter(f.get("observation") or f["state"] for f in findings.values())
    principals = {f["path"][0][0] for f in findings.values()
                  if (f.get("observation") or f["state"]) in ("new", "persistent", "changed")}
    exposed = e.get("population") or {}
    return dict(run=run_id, platform=e["asset"]["platform"], principals=len(principals),
                edges=sum(states[s] for s in ("new", "persistent", "changed")), states=dict(states),
                exposed_identities=sum(exposed.get(k, 0) for k in IDENTITY), issues=e["issues"],
                upstream=e.get("upstream"))


def scan(run=cypher):
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    healthy = True
    with (ROOT / "tier-zero-scan.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for platform in PLATFORMS:
            try:
                e = evidence(platform, run)
            except (OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
                e = unavailable(platform, exc)
            print(json.dumps(summary(record_paths(e))))
            healthy &= not e["issues"]
    return healthy


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--show", type=int, metavar="RUN")
    args = p.parse_args()
    if args.show:
        print(json.dumps(get_run(args.show), indent=2))
    else:
        raise SystemExit(0 if scan() else 2)
