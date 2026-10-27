"""Trusted Slink Zone: passive discovery and receipt-gated enrollment.

Python standard library only. No active network probes, remote access, installers,
SSH commands, daemon spawning, or model-controlled authorization.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import time

MAC_RE = re.compile(r"^[0-9a-fA-F]{1,2}(?::[0-9a-fA-F]{1,2}){5}$")
ARP_RE = re.compile(r"\(([^)]+)\)\s+at\s+(\S+)\s+on\s+(\S+)")
ALLOWED_SCOPES = frozenset({"inventory", "inference", "engineering", "training"})


class EnrollmentError(ValueError):
    """An untrusted, expired or inconsistent enrollment request."""


def normalize_mac(value: str) -> str:
    if not isinstance(value, str) or not MAC_RE.fullmatch(value):
        raise ValueError("invalid link-layer address")
    return ":".join(part.zfill(2).lower() for part in value.split(":"))


def candidate_id(interface: str, mac: str) -> str:
    """A discovery label, NOT a cryptographic device identity."""
    return "neighbor-" + hashlib.sha256((interface + "\0" + normalize_mac(mac)).encode()).hexdigest()[:24]


def _observation(ip: str, mac: str, interface: str, origin: str):
    try:
        address = str(ipaddress.ip_address(ip.split("%", 1)[0]))
        normalized_mac = normalize_mac(mac)
    except (ValueError, AttributeError):
        return None
    if not interface or not isinstance(interface, str):
        return None
    return {"candidate_id": candidate_id(interface, normalized_mac),
            "address": address, "mac": normalized_mac, "interface": interface,
            "origin": origin}


def parse_linux_neighbors(text: str, allowed_interfaces: set[str]) -> list[dict]:
    items = json.loads(text)
    if not isinstance(items, list):
        raise ValueError("expected Linux neighbor JSON list")
    found = []
    for item in items:
        if not isinstance(item, dict) or item.get("dev") not in allowed_interfaces:
            continue
        if str(item.get("state", "")).upper() in {"FAILED", "INCOMPLETE"}:
            continue
        observation = _observation(item.get("dst"), item.get("lladdr"),
                                   item["dev"], "linux-neighbor-cache")
        if observation:
            found.append(observation)
    return found


def parse_macos_arp(text: str, allowed_interfaces: set[str]) -> list[dict]:
    found = []
    for match in ARP_RE.finditer(text):
        ip, mac, interface = match.groups()
        if interface not in allowed_interfaces:
            continue
        observation = _observation(ip, mac, interface, "macos-arp-cache")
        if observation:
            found.append(observation)
    return found


def passive_observe(allowed_interfaces: set[str]) -> list[dict]:
    """Read local OS cache only. No ping, broadcast, multicast or host connection."""
    if not allowed_interfaces or any(not re.fullmatch(r"[a-zA-Z0-9._:-]{1,64}", i) for i in allowed_interfaces):
        raise ValueError("specify valid interface names explicitly")
    system = platform.system()
    if system == "Linux":
        command, parser = ["ip", "-j", "neigh", "show"], parse_linux_neighbors
    elif system == "Darwin":
        command, parser = ["arp", "-an"], parse_macos_arp
    else:
        raise RuntimeError("unsupported OS; import a synthetic observation fixture instead")
    result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=8)
    return parser(result.stdout, allowed_interfaces)


def new_state() -> dict:
    return {"schema": 1, "candidates": {}, "nodes": {}, "used_nonces": []}


def record_observations(state: dict, observations: list[dict], now: int) -> int:
    added = 0
    for observation in observations:
        cid = observation["candidate_id"]
        if cid != candidate_id(observation["interface"], observation["mac"]):
            raise EnrollmentError("invalid discovery candidate ID")
        if cid not in state["candidates"]:
            state["candidates"][cid] = {"first_seen": now, "last_seen": now,
                "mac": observation["mac"], "interface": observation["interface"],
                "addresses": [observation["address"]], "origin": observation["origin"],
                "trust": "UNVERIFIED"}
            added += 1
        else:
            candidate = state["candidates"][cid]
            candidate["last_seen"] = now
            addresses = set(candidate["addresses"])
            addresses.add(observation["address"])
            candidate["addresses"] = sorted(addresses)[-16:]
    return added


def _canonical(envelope: dict) -> bytes:
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def verify_receipt(envelope: dict, key: bytes, expected_kind: str, now: int) -> dict:
    """Verify owner-managed signed receipt. Controller never issues approvals."""
    if not isinstance(envelope, dict):
        raise EnrollmentError("receipt must be an object")
    data = {k: v for k, v in envelope.items() if k != "signature"}
    signature = envelope.get("signature", "")
    if not isinstance(signature, str) or not re.fullmatch("[0-9a-f]{64}", signature):
        raise EnrollmentError("receipt has no valid signature")
    if data.get("kind") != expected_kind:
        raise EnrollmentError("wrong receipt kind")
    expires = data.get("expires_at")
    if type(expires) is not int or expires <= now or expires > now + 86400:
        raise EnrollmentError("expired receipt or excessive validity period")
    nonce = data.get("nonce")
    if not isinstance(nonce, str) or not re.fullmatch("[0-9a-f]{32,128}", nonce):
        raise EnrollmentError("receipt nonce missing or malformed")
    expected = hmac.new(key, _canonical(data), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise EnrollmentError("receipt signature does not match")
    return data


def _consume_nonce(state: dict, receipt: dict) -> None:
    # A nonce is never reused across approval/attestation/revocation paths.
    nonce = receipt["nonce"]
    if nonce in state["used_nonces"]:
        raise EnrollmentError("receipt replay")
    state["used_nonces"].append(nonce)


def approve(state: dict, envelope: dict, approval_key: bytes, now: int) -> dict:
    receipt = verify_receipt(envelope, approval_key, "tsz-approval-v1", now)
    cid, node_id = receipt.get("candidate_id"), receipt.get("node_id")
    fingerprint = receipt.get("device_key_sha256")
    scopes = receipt.get("scopes")
    if not isinstance(cid, str) or cid not in state["candidates"]:
        raise EnrollmentError("candidate has not been observed")
    if not isinstance(node_id, str) or not re.fullmatch("[a-zA-Z0-9._-]{1,80}", node_id):
        raise EnrollmentError("invalid node ID")
    if not isinstance(fingerprint, str) or not re.fullmatch("[0-9a-f]{64}", fingerprint):
        raise EnrollmentError("missing device public-key fingerprint")
    if (not isinstance(scopes, list) or not scopes or not all(isinstance(s, str) for s in scopes)
        or len(scopes) != len(set(scopes)) or not set(scopes) <= ALLOWED_SCOPES):
        raise EnrollmentError("invalid worker scope")
    if node_id in state["nodes"]:
        raise EnrollmentError("node already registered; never overwrite its trust record")
    if any(n["device_key_sha256"] == fingerprint for n in state["nodes"].values()):
        raise EnrollmentError("device key is already bound to another node")
    if any(n["candidate_id"] == cid and n["status"] != "REVOKED" for n in state["nodes"].values()):
        raise EnrollmentError("candidate already approved as a different node")
    _consume_nonce(state, receipt)
    record = {"candidate_id": cid, "device_key_sha256": fingerprint,
              "scopes": sorted(scopes), "approval_nonce": receipt["nonce"],
              "approval_expires_at": receipt["expires_at"],
              "status": "AWAITING_EXTERNAL_ATTESTATION"}
    state["nodes"][node_id] = record
    return record


def attest(state: dict, envelope: dict, attestor_key: bytes, now: int) -> dict:
    """Accept independently signed attestation from owner's verifier.

    The external verifier, NOT this controller, must establish actual device
    identity, key possession, management rights and allowed resource scopes.
    """
    receipt = verify_receipt(envelope, attestor_key, "tsz-attestation-v1", now)
    node_id = receipt.get("node_id")
    node = state["nodes"].get(node_id) if isinstance(node_id, str) else None
    if node is None or node["status"] != "AWAITING_EXTERNAL_ATTESTATION":
        raise EnrollmentError("node is not awaiting attestation")
    if receipt.get("device_key_sha256") != node["device_key_sha256"]:
        raise EnrollmentError("device identity mismatch")
    if receipt.get("approval_nonce") != node["approval_nonce"]:
        raise EnrollmentError("attestation is not bound to approved receipt")
    if node["approval_expires_at"] <= now:
        raise EnrollmentError("approval has expired")
    _consume_nonce(state, receipt)
    node["attestation_nonce"] = receipt["nonce"]
    node["attestation_expires_at"] = receipt["expires_at"]
    node["status"] = "AUTHORIZED_PENDING_DEPLOYMENT"
    return node


def revoke(state: dict, envelope: dict, approval_key: bytes, now: int) -> dict:
    receipt = verify_receipt(envelope, approval_key, "tsz-revocation-v1", now)
    node_id = receipt.get("node_id")
    node = state["nodes"].get(node_id) if isinstance(node_id, str) else None
    if node is None or node["status"] == "REVOKED":
        raise EnrollmentError("no active matching node")
    if receipt.get("device_key_sha256") != node["device_key_sha256"]:
        raise EnrollmentError("revocation device mismatch")
    _consume_nonce(state, receipt)
    node["status"] = "REVOKED"
    return node


def deployment_plan(state: dict, now: int) -> list[dict]:
    """Generate inert work orders, never commands or network destinations."""
    result = []
    for node_id, node in sorted(state["nodes"].items()):
        if (node["status"] == "AUTHORIZED_PENDING_DEPLOYMENT"
            and node["approval_expires_at"] > now
            and node["attestation_expires_at"] > now):
            result.append({"node_id": node_id, "candidate_id": node["candidate_id"],
                           "scopes": node["scopes"], "action": "WAIT_FOR_AUTHORIZED_DEPLOYER"})
    return result


def _read_secret(filename: Path) -> bytes:
    s = filename.stat()
    if not stat.S_ISREG(s.st_mode) or s.st_mode & 0o077:
        raise PermissionError("verification key must be a private regular file (mode 0600)")
    key = filename.read_bytes()
    if len(key) < 32:
        raise ValueError("verification key must contain at least 32 random bytes")
    return key


@contextmanager
def locked_state(root: Path):
    root = root.expanduser()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    mode = root.stat().st_mode
    if not stat.S_ISDIR(mode) or mode & 0o077:
        raise PermissionError("private state directory must be accessible to owner only (0700)")
    lock_fd = os.open(root / ".lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        target = root / "fleet.json"
        state = json.loads(target.read_text()) if target.exists() else new_state()
        if state.get("schema") != 1:
            raise ValueError("unknown TSZ state schema")
        yield state
        # Persist only when the caller used a mutating command.
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def save_state(root: Path, state: dict) -> None:
    target = root.expanduser() / "fleet.json"
    temporary = root.expanduser() / (".fleet-" + str(os.getpid()) + ".tmp")
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(state, out, indent=2, sort_keys=True)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--state-dir", type=Path, default=Path("~/.local/state/haven-tsz"))
    commands = cli.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("discover", help="Read current local neighbor cache; no network scanning")
    scan.add_argument("--interface", action="append", required=True)
    for command in ("approve", "attest", "revoke"):
        sub = commands.add_parser(command)
        sub.add_argument("--receipt", type=Path, required=True)
        sub.add_argument("--verification-key", type=Path, required=True)
    commands.add_parser("inventory")
    commands.add_parser("plan")
    args = cli.parse_args()
    now = int(time.time())
    with locked_state(args.state_dir) as state:
        if args.command == "discover":
            observed = passive_observe(set(args.interface))
            newly_seen = record_observations(state, observed, now)
            save_state(args.state_dir, state)
            print(json.dumps({"observed": len(observed), "new_candidates": newly_seen}, indent=2))
        elif args.command in ("approve", "attest", "revoke"):
            receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
            key = _read_secret(args.verification_key)
            action = {"approve": approve, "attest": attest, "revoke": revoke}[args.command]
            record = action(state, receipt, key, now)
            save_state(args.state_dir, state)
            print(json.dumps({"status": record["status"]}, indent=2))
        elif args.command == "inventory":
            # Full inventory remains local; never uploaded to the public repository.
            print(json.dumps({"candidates": state["candidates"], "nodes": state["nodes"]}, indent=2))
        else:
            print(json.dumps(deployment_plan(state, now), indent=2))


if __name__ == "__main__":
    try:
        main()
    except (EnrollmentError, PermissionError, ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"TSZ: {exc}", file=sys.stderr)
        sys.exit(2)
