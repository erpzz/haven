"""Offline Trusted Slink Zone pipeline-placement feasibility probe.

No network access, device enrollment, installations or inference.
Authentication and grants MUST be established outside this offline planner.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path


def _number(value, field: str, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError(f"{field} must be a finite {'positive' if positive else 'nonnegative'} number")
    return float(value)


def plan(manifest: dict) -> dict:
    """Estimate uniform contiguous pipeline-layer capacity; never deploys.

    Not a proof of runtime fit: real layer sizes, backend compatibility, host
    memory overhead and synchronization are not modeled.
    """
    if not isinstance(manifest, dict) or not isinstance(manifest.get("model"), dict):
        raise ValueError("manifest and model must be objects")
    model = manifest["model"]
    layers = model.get("layers")
    if isinstance(layers, bool) or not isinstance(layers, int) or layers <= 0:
        raise ValueError("model.layers must be a positive integer")
    weights = _number(model.get("weights_mib"), "weights_mib", positive=True)
    kv = _number(model.get("kv_mib"), "kv_mib")
    boundary_kib = _number(model.get("boundary_activation_kib", 0), "boundary_activation_kib")
    nodes = manifest.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("nodes must be a list")
    eligible, ignored, seen = [], [], set()
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("node must be an object")
        identity = node.get("id")
        if not isinstance(identity, str) or not identity or identity in seen:
            raise ValueError("node IDs must be unique nonempty strings")
        seen.add(identity)
        # Flags here are inputs, NOT independently verified identity/grants.
        if not all(node.get(field) is True for field in ("enrolled", "online", "inference_grant")):
            ignored.append(identity)
            continue
        free = _number(node.get("accelerator_free_mib"), f"{identity}.accelerator_free_mib")
        bandwidth = _number(node.get("fabric_mbps"), f"{identity}.fabric_mbps", positive=True)
        backend = node.get("backend", "unknown")
        if not isinstance(backend, str) or not backend:
            raise ValueError("backend must be a nonempty string")
        eligible.append({"id": identity, "free": free, "bandwidth": bandwidth, "backend": backend})
    eligible.sort(key=lambda n: (-n["free"], n["id"]))
    if not eligible:
        return {"status": "NO_ENROLLED_READY_INFERENCE_NODES", "assignments": [], "ignored_nodes": sorted(ignored)}
    total = _number(weights + kv, "total memory", positive=True)
    for node in eligible:
        if node["free"] >= total:
            return {
                "status": "ESTIMATED_SINGLE_NODE_FIT",
                "assignments": [{"node_id": node["id"], "start_layer": 0, "end_layer_exclusive": layers, "backend": node["backend"]}],
                "ignored_nodes": sorted(ignored), "cross_node_boundaries": 0, "transfer_floor_ms_per_token": 0.0,
                "warnings": ["Memory estimate only: architecture, runtime and overhead are not verified."]
            }
    try:
        per_layer = _number(total / layers, "per-layer memory", positive=True)
    except OverflowError as exc:
        raise ValueError("layer count exceeds supported numeric range") from exc
    remaining, assignments = layers, []
    for node in eligible:
        count = min(remaining, math.floor(node["free"] / per_layer))
        if count:
            start = layers - remaining
            assignments.append({"node_id": node["id"], "start_layer": start,
                                "end_layer_exclusive": start + count, "backend": node["backend"]})
            remaining -= count
        if not remaining:
            break
    if remaining:
        return {"status": "INSUFFICIENT_AGGREGATE_ACCELERATOR_MEMORY",
                "assignments": [], "ignored_nodes": sorted(ignored), "unplaced_layers": remaining,
                "warnings": ["CPU/RAM MoE offload or smaller quantization requires separate evaluation."]}
    by_id = {node["id"]: node for node in eligible}
    floor_ms = sum((boundary_kib / 1024) * 8000 /
                   min(by_id[a["node_id"]]["bandwidth"], by_id[b["node_id"]]["bandwidth"])
                   for a, b in zip(assignments, assignments[1:]))
    return {"status": "ESTIMATED_PIPELINE_FIT", "assignments": assignments,
            "ignored_nodes": sorted(ignored), "cross_node_boundaries": len(assignments) - 1,
            "transfer_floor_ms_per_token": round(floor_ms, 4),
            "warnings": ["No inference performed. Verify real layer memory, cross-backend RPC support and network latency.",
                         "Transfer lower bound excludes protocol, synchronization, compute and return traffic."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Private or synthetic JSON capabilities manifest")
    args = parser.parse_args()
    print(json.dumps(plan(json.loads(args.manifest.read_text(encoding="utf-8"))), indent=2))


if __name__ == "__main__":
    main()
