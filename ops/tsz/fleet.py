"""Trusted Slink Zone discovery controller (passive, local, stdlib-only).

The trust/attestation engine is EXTERNAL to this module. It owns its decisions.
This controller consumes a materialized owner-controlled approved-nodes snapshot,
without implementing a second verification workflow.

No active probes, SSH, remote code execution, service installation, port listeners
or credentials. Output is fleet state and inert enrollment work orders.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

try:
    from . import private_io
except ImportError:  # direct CLI invocation
    import private_io

SCHEMA = "tsz-fleet-v1"
DECISION_SCHEMA = "tsz-approved-nodes-v1"
ROLES = frozenset({"inventory", "inference", "engineering", "training"})
MAC = re.compile(r"^(?:[0-9a-fA-F]{1,2}:){5}[0-9a-fA-F]{1,2}$")
ARP = re.compile(r"\(([^)]+)\)\s+at\s+(\S+)\s+on\s+([A-Za-z0-9._:-]+)")
ID = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")
INTERFACE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


class FleetError(ValueError):
    pass


def normalize_mac(value: str) -> str:
    if not isinstance(value, str) or not MAC.fullmatch(value):
        raise FleetError("invalid MAC")
    return ":".join(x.lower().zfill(2) for x in value.split(":"))


def candidate_id(interface: str, mac: str) -> str:
    """Opaque discovery handle, not device identity or authorization."""
    if not isinstance(interface, str) or not INTERFACE.fullmatch(interface):
        raise FleetError("invalid interface")
    payload = interface + "\0" + normalize_mac(mac)
    return "neighbor-" + hashlib.sha256(payload.encode("ascii")).hexdigest()[:24]


def observation(ip: str, mac: str, interface: str, origin: str) -> dict | None:
    try:
        address = str(ipaddress.ip_address(ip.split("%", 1)[0]))
        normalized = normalize_mac(mac)
        cid = candidate_id(interface, normalized)
    except (FleetError, AttributeError, ValueError):
        return None
    return {"candidate_id": cid, "interface": interface,
            "mac": normalized, "address": address, "origin": origin}


def parse_linux(text: str, interfaces: set[str]) -> list[dict]:
    raw = json.loads(text)
    if not isinstance(raw, list):
        raise FleetError("Linux neighbor output is not a list")
    result = []
    for entry in raw:
        if (not isinstance(entry, dict) or not isinstance(entry.get("dev"), str)
                or entry["dev"] not in interfaces):
            continue
        if any(s in str(entry.get("state", "")).upper() for s in ("FAILED", "INCOMPLETE")):
            continue
        seen = observation(entry.get("dst"), entry.get("lladdr"),
                           entry["dev"], "linux-neighbor-cache")
        if seen:
            result.append(seen)
    return result


def parse_macos(text: str, interfaces: set[str]) -> list[dict]:
    result = []
    for match in ARP.finditer(text):
        address, mac, iface = match.groups()
        if iface not in interfaces:
            continue
        seen = observation(address, mac, iface, "macos-arp-cache")
        if seen:
            result.append(seen)
    return result


def observe(interfaces: set[str]) -> list[dict]:
    """No active traffic: only reads caches already held by the OS."""
    if not interfaces or any(not INTERFACE.fullmatch(i) for i in interfaces):
        raise FleetError("specify one or more interfaces")
    system = platform.system()
    if system == "Linux":
        cmd, parser = ["ip", "-j", "neigh", "show"], parse_linux
    elif system == "Darwin":
        cmd, parser = ["arp", "-an"], parse_macos
    else:
        raise FleetError("unsupported host OS")
    output = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=8)
    return parser(output.stdout, interfaces)


def empty_state() -> dict:
    return {"schema": SCHEMA, "candidates": {}, "nodes": {}, "generation": 0}


def update_candidates(state: dict, observations: list[dict], now: int) -> int:
    if not isinstance(observations, list):
        raise FleetError("observations must be a list")
    # Validate the batch before mutating state. Preserve the source capture time.
    for item in observations:
        if (not isinstance(item, dict) or observation(item.get("address"), item.get("mac"),
                item.get("interface"), item.get("origin")) is None):
            raise FleetError("malformed observation")
        captured = item.get("observed_at", now)
        if type(captured) is not int or captured < 0 or captured > now:
            raise FleetError("invalid observation time")
        if item.get("candidate_id") != candidate_id(item["interface"], item["mac"]):
            raise FleetError("inconsistent discovery record")
    created = 0
    for item in observations:
        cid = candidate_id(item["interface"], item["mac"])
        captured = item.get("observed_at", now)
        if cid not in state["candidates"]:
            state["candidates"][cid] = {
                "interface": item["interface"], "mac": item["mac"],
                "first_seen": captured, "last_seen": captured,
                "addresses": [item["address"]], "state": "DISCOVERED_UNVERIFIED",
            }
            created += 1
        else:
            record = state["candidates"][cid]
            record["last_seen"] = max(record["last_seen"], captured)
            record["addresses"] = sorted(set(record["addresses"] + [item["address"]]))[-16:]
    state["generation"] += 1
    return created


def load_approved_file(path: Path) -> dict:
    """Read a local, owner-controlled export from the *external* trust engine.

    Its decisions are authoritative to this controller. This module does not
    request proofs, issue approvals, or check attestation receipts.
    """
    try:
        raw = private_io.read_json(path)
    except ValueError as exc:
        raise FleetError(str(exc)) from exc
    if not isinstance(raw, dict) or raw.get("schema") != DECISION_SCHEMA:
        raise FleetError("unknown approved-node export schema")
    return raw


def reconcile_approved(state: dict, export: dict, now: int) -> dict:
    """Consume approved-node eligibility, never treat sightings as grants.

    Decisions can originate from an owner-verification model or management
    policy. That producer must control and attest its own inputs independently.
    """
    if not isinstance(export, dict) or export.get("schema") != DECISION_SCHEMA:
        raise FleetError("malformed approved-node export")
    expiry = export.get("expires_at")
    if type(expiry) is not int or expiry <= now or expiry > now + 86400:
        raise FleetError("export expired or TTL exceeds 24 hours")
    revision = export.get("revision")
    previous = state.get("approval_revision")
    digest = hashlib.sha256(json.dumps(export, sort_keys=True, allow_nan=False).encode()).hexdigest()
    if revision is not None or previous is not None:
        if type(revision) is not int or revision < 0:
            raise FleetError("approval revision must be a nonnegative integer; downgrade forbidden")
        if previous is not None and (revision < previous or (
                revision == previous and digest != state.get("approval_digest"))):
            raise FleetError("stale or conflicting approval revision")
    decisions = export.get("nodes")
    if not isinstance(decisions, list) or len(decisions) > 10000:
        raise FleetError("invalid node decisions")
    snapshot = {}
    candidate_ids = set()
    for item in decisions:
        if not isinstance(item, dict):
            raise FleetError("invalid node entry")
        node_id, cid, roles = item.get("node_id"), item.get("candidate_id"), item.get("roles")
        if not isinstance(node_id, str) or not ID.fullmatch(node_id):
            raise FleetError("invalid node ID")
        if not isinstance(cid, str) or cid not in state["candidates"]:
            raise FleetError("approved node references an unknown discovery candidate")
        if not isinstance(roles, list) or not roles or any(not isinstance(r, str) for r in roles):
            raise FleetError("invalid roles")
        if not set(roles) <= ROLES or len(set(roles)) != len(roles):
            raise FleetError("unknown or repeated roles")
        if node_id in snapshot or cid in candidate_ids:
            raise FleetError("duplicate node or discovery binding")
        existing = state.get("bindings", {}).get(node_id) or state["nodes"].get(node_id, {}).get("candidate_id")
        if existing is not None and existing != cid:
            raise FleetError("node ID cannot be silently rebound to another device")
        candidate_ids.add(cid)
        snapshot[node_id] = {
            "candidate_id": cid, "roles": sorted(roles),
            "approved_until": expiry,
            "state": "APPROVED_AWAITING_USERSPACE_WORKER",
        }
    # Snapshot semantics: missing nodes are no longer eligible.
    state.setdefault("bindings", {}).update({n: v["candidate_id"] for n, v in state["nodes"].items()})
    state["bindings"].update({n: v["candidate_id"] for n, v in snapshot.items()})
    if revision is not None:
        state["approval_revision"] = revision
        state["approval_digest"] = digest
    state["nodes"] = snapshot
    state["generation"] += 1
    return {"approved_nodes": len(snapshot), "generation": state["generation"]}


def work_orders(state: dict, now: int) -> list[dict]:
    """Output intent, never a connection URL, command, or installer."""
    return [
        {"node_id": node_id, "roles": node["roles"], "candidate_id": node["candidate_id"],
         "action": "PREPARE_USERSPACE_WORKER", "state": node["state"]}
        for node_id, node in sorted(state["nodes"].items())
        if node["approved_until"] > now
    ]


def private_dir(directory: Path) -> Path:
    try:
        return private_io.private_dir(directory)
    except ValueError as exc:
        raise FleetError(str(exc)) from exc


fleet_lock = private_io.lock


def read_state(directory: Path) -> dict:
    try:
        state = private_io.read_json(directory / "inventory.json")
    except FileNotFoundError:
        return empty_state()
    if (state.get("schema") != SCHEMA or not isinstance(state.get("nodes"), dict)
            or not isinstance(state.get("candidates"), dict)
            or type(state.get("generation")) is not int or state["generation"] < 0):
        raise FleetError("invalid TSZ state")
    if "approval_revision" in state and (type(state["approval_revision"]) is not int
            or state["approval_revision"] < 0 or not isinstance(state.get("approval_digest"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", state["approval_digest"])):
        raise FleetError("invalid approval revision state")
    bindings = state.get("bindings", {})
    if not isinstance(bindings, dict):
        raise FleetError("invalid historical bindings")
    for node_id, cid in bindings.items():
        if not ID.fullmatch(node_id) or not isinstance(cid, str) or cid not in state["candidates"]:
            raise FleetError("invalid historical node binding")
    for cid, candidate in state["candidates"].items():
        if (not isinstance(candidate, dict) or not isinstance(candidate.get("interface"), str)
                or not isinstance(candidate.get("mac"), str)
                or candidate_id(candidate["interface"], candidate["mac"]) != cid
                or not isinstance(candidate.get("addresses"), list)
                or any(not isinstance(a, str) for a in candidate["addresses"])
                or type(candidate.get("first_seen")) is not int
                or type(candidate.get("last_seen")) is not int):
            raise FleetError("invalid candidate state")
    for node_id, node in state["nodes"].items():
        if (not ID.fullmatch(node_id) or not isinstance(node, dict)
                or not isinstance(node.get("candidate_id"), str) or node["candidate_id"] not in state["candidates"]
                or type(node.get("approved_until")) is not int
                or not isinstance(node.get("roles"), list) or not node["roles"]
                or any(not isinstance(r, str) or r not in ROLES for r in node["roles"])
                or len(set(node["roles"])) != len(node["roles"])
                or node.get("state") != "APPROVED_AWAITING_USERSPACE_WORKER"):
            raise FleetError("invalid approved node state")
    return state


def write_state(directory: Path, state: dict) -> None:
    private_io.write_json(directory / "inventory.json", state)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, default=Path("~/.local/state/haven-tsz"))
    sub = parser.add_subparsers(dest="action", required=True)
    discovery = sub.add_parser("discover")
    discovery.add_argument("--interface", action="append", required=True)
    imported = sub.add_parser("discover-import", help="Import owner-controlled network inventory; do not probe")
    imported.add_argument("--file", type=Path, required=True)
    imported.add_argument("--interface", action="append", required=True)
    approvals = sub.add_parser("sync-approved")
    approvals.add_argument("--file", type=Path, required=True)
    sub.add_parser("inventory")
    sub.add_parser("plan")
    args = parser.parse_args()
    state_dir = private_dir(args.state_dir)
    with fleet_lock(state_dir):
        state = read_state(state_dir)
        now = int(time.time())
        if args.action == "discover":
            observations = observe(set(args.interface))
            added = update_candidates(state, observations, now)
            write_state(state_dir, state)
            result = {"seen": len(observations), "new_candidates": added, "generation": state["generation"]}
        elif args.action == "discover-import":
            try:
                from .import_source import read_owner_inventory, parse_network_inventory
            except ImportError:
                from import_source import read_owner_inventory, parse_network_inventory
            observations = parse_network_inventory(read_owner_inventory(args.file.expanduser()),
                                                   set(args.interface), now)
            added = update_candidates(state, observations, now)
            write_state(state_dir, state)
            result = {"source": "owner-network-inventory", "seen": len(observations),
                      "new_candidates": added, "generation": state["generation"]}
        elif args.action == "sync-approved":
            result = reconcile_approved(state, load_approved_file(args.file), now)
            write_state(state_dir, state)
        elif args.action == "inventory":
            result = state
        else:
            result = work_orders(state, now)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (FleetError, ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"TSZ controller: {error}", file=sys.stderr)
        sys.exit(2)
