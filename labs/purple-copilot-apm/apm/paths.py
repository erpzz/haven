"""Directed, bounded membership reviews of configured synthetic assets."""
import hashlib
import io
import json
import os
import re
import zipfile
from collections import defaultdict
from pathlib import Path

from .graph import _signed, verify_reader
from .local import now
from .samples import FILES, checked, read

PLATFORMS = {"ad": ("Group", "MemberOf"), "entra": ("AZGroup", "AZMemberOf")}
MAX_PATHS = 128
MAX_HOPS = 4


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def registry():
    file = Path(os.getenv("APM_ASSETS", Path(__file__).resolve().parents[1] / "assets.json"))
    assets = {}
    for a in json.loads(file.read_text()):
        if (set(a) != {"key", "platform", "target", "sensitivity", "privileged"}
                or not re.fullmatch(r"[a-z0-9-]{1,48}", a["key"]) or a["key"] in assets
                or a["platform"] not in PLATFORMS or a["sensitivity"] not in ("high", "critical")
                or type(a["privileged"]) is not bool
                or not re.fullmatch(r"[A-Z0-9.-]{1,128}", a["target"])):
            raise ValueError("Invalid asset registry")
        assets[a["key"]] = a
    return assets


def query(asset):
    label, kind = PLATFORMS[asset["platform"]]
    target = asset["target"]
    if not re.fullmatch(r"[A-Z0-9.-]{1,128}", target):
        raise ValueError("Invalid object ID")
    return (f"MATCH p=(a)-[:{kind}*1..{MAX_HOPS}]->(b:{label} {{objectid: '{target}'}}) "
            f"RETURN p LIMIT {MAX_PATHS + 1}")


def enumerate_paths(asset, edges):
    """Paths are ordered source-to-target edge tuples. Cycles never confer extra evidence."""
    incoming = defaultdict(set)
    kind = PLATFORMS[asset["platform"]][1]
    for source, relation, target in edges:
        if relation == kind:
            incoming[target].add(source)
    paths = []

    def visit(node, suffix, seen):
        if len(suffix) >= MAX_HOPS:
            return
        for source in sorted(incoming[node] - seen):
            route = ((source, kind, node),) + suffix
            paths.append(route)
            if len(paths) > MAX_PATHS:
                raise ValueError("Path budget exceeded")
            visit(source, route, seen | {source})

    visit(asset["target"], (), {asset["target"]})
    return sorted(paths)


def graph_edges(graph):
    nodes = graph["nodes"]
    return sorted({(nodes[str(e["source"])]["objectId"], e["kind"], nodes[str(e["target"])]["objectId"])
                   for e in graph["edges"]})


def source_inventory(platform):
    name = platform + "_sampledata.zip"
    archive = zipfile.ZipFile(io.BytesIO(checked(name)))
    edges, groups, issues, files = [], set(), [], []
    with archive:
        for filename in archive.namelist():
            if platform == "ad" and not filename.endswith("_groups.json"):
                continue
            payload = json.loads(archive.read(filename))
            files.append(filename)
            if payload["meta"]["count"] != len(payload["data"]):
                issues.append("Archive record count mismatch: " + filename)
            for row in payload["data"]:
                if platform == "ad":
                    group = row["ObjectIdentifier"]
                    groups.add(group)
                    edges.extend((m["ObjectIdentifier"], "MemberOf", group) for m in row["Members"])
                elif row["kind"] == "AZGroupMember":
                    data = row["data"]
                    if data["members"] is not None:
                        groups.add(data["groupId"])
                        edges.extend((m["member"]["id"], "AZMemberOf", data["groupId"]) for m in data["members"])
    return groups, edges, files, issues


def sample_scan(asset, inventories=None):
    platform = asset["platform"]
    source = platform + "_sampledata.zip"
    inventories = {} if inventories is None else inventories
    if platform not in inventories:
        inventories[platform] = source_inventory(platform)
    groups, edges, files, inventory_issues = inventories[platform]
    if asset["target"] not in groups:
        raise ValueError("Asset absent from pinned group membership inventory")
    expected = enumerate_paths(asset, edges)
    issues = list(inventory_issues)
    verify_reader()
    cypher = query(asset)
    graph = _signed("POST", "/api/v2/graphs/cypher", json.dumps({
        "query": cypher, "include_properties": False}).encode())["data"]
    routes = enumerate_paths(asset, graph_edges(graph))
    if routes != expected:
        issues.append("Graph disagrees with source paths")
    ingest = read("ingest.json")
    status = ingest["status"]
    if (ingest["archives"] != FILES or status["status"] != 2 or status["total_files"] != 32
            or status["failed_files"] or status["partial_failed_files"]):
        issues.append("Incomplete sample ingest")
    return dict(asset=asset, origin="ce-sample", observed=now(), paths=routes, issues=issues,
                query=cypher, graph=graph, source_files=files, archive=FILES[source],
                receipt=dict(collector="official-archive", run=None, completed=None, complete=False,
                             ingest_job=status["id"], ingested=status["end_time"]), removals=[])
