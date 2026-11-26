"""MCP capability bound at launch to one operator-selected historical finding."""
import os

from mcp.server.fastmcp import FastMCP

from .mcp_reader import community_graph
from .path_history import confidence, get_run
from .paths import graph_edges, query, registry

server = FastMCP("Purple finding review")


def selected():
    run = int(os.environ["APM_FINDING_RUN"])
    evidence, findings = get_run(run)
    key = os.environ["APM_FINDING_ID"]
    if evidence.get("unavailable") or key not in findings or findings[key]["state"] not in ("new", "persistent", "changed"):
        raise PermissionError("Finding has no observed path in this snapshot")
    asset = registry().get(evidence["asset"]["key"])
    if evidence["origin"] != "ce-sample" or asset != evidence["asset"] or query(asset) != evidence["query"]:
        raise PermissionError("Observation outside current sample catalog")
    return run, evidence, findings[key]


@server.tool()
async def path_evidence() -> dict:
    """Verify the selected path's directed membership edges and return citing object IDs."""
    run, e, finding = selected()
    graph = await community_graph(e["asset"]["key"], e["query"])
    current = set(graph_edges(graph))
    path = finding["path"]
    if not all(tuple(edge) in current for edge in path):
        raise ValueError("Live graph no longer corroborates the selected path")
    return {"reference": "E1", "run": run, "directed_edges": path, "confidence": confidence(e)}


@server.tool()
def collection_quality() -> dict:
    """Return collector freshness, completeness and provenance for the selected finding."""
    run, e, _ = selected()
    return {"reference": "E1", "run": run, "asset_id": e["asset"]["target"],
            "receipt": e["receipt"], "issues": e["issues"], "confidence": confidence(e)}


if __name__ == "__main__":
    server.run()
