"""Trust gate: may this enrolled node take this kind of work right now?

Haven does not verify devices itself. The owner's separate trust-management
model decides, and TSZ (ops/tsz) records its approved-node export in
`<tsz state>/inventory.json` (`fleet.py sync-approved`). This module only
*consumes* that state, intersected with Haven's own enrollment:

  eligible = Haven enrollment with a pinned host key (fleet.py)
           AND an owner binding  node.tsz_node_id -> TSZ approved node
           AND that approval is unexpired and grants the needed TSZ role
           AND the bound discovery record does not contradict the node address

Configured by ~/.config/haven-engineer/trust.json (a file no agent can write):

  {"source": "tsz", "tsz_state_dir": "~/.local/state/haven-tsz"}

Without that file the source is "enrollment": Haven's enrollment alone, as before
TSZ, and every decision says so. A broken or unreadable TSZ state denies all
work (fail closed) rather than falling back.
"""
from __future__ import annotations

import importlib.util
import ipaddress
import json
import os
import pathlib
import time

CONFIG = pathlib.Path(os.environ.get("HAVEN_ENGINEER_CONFIG", pathlib.Path.home() / ".config/haven-engineer"))
REPO = pathlib.Path(__file__).resolve().parents[2]

# Haven job role -> the TSZ role an approval must grant. Training has no Haven job role yet.
ROLE_MAP = {"tools": "engineering", "build": "engineering", "inference": "inference",
            "inference-cpu": "inference", "inference-gpu": "inference", "observe": "inventory"}


def _tsz():
    spec = importlib.util.spec_from_file_location("tsz_fleet", REPO / "ops" / "tsz" / "fleet.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def config():
    p = CONFIG / "trust.json"
    if not p.exists():
        return {"source": "enrollment"}
    cfg = json.loads(p.read_text())
    if cfg.get("source") not in ("tsz", "enrollment"):
        raise ValueError("trust.json source must be 'tsz' or 'enrollment'")
    return cfg


class Gate:
    """One snapshot of trust inputs; decide() is pure over it."""

    def __init__(self, cfg=None, tsz_state=None, now=None):
        self.cfg = cfg if cfg is not None else config()
        self.now = int(now if now is not None else time.time())
        self.error = None
        self.state = tsz_state
        if self.cfg["source"] == "tsz" and self.state is None:
            try:
                tsz = _tsz()
                d = pathlib.Path(os.path.expanduser(self.cfg.get("tsz_state_dir", "~/.local/state/haven-tsz")))
                self.state = tsz.read_state(d)
            except Exception as e:  # noqa: BLE001 - any failure closes the gate
                self.error = f"TSZ state unreadable: {type(e).__name__}: {e}"[:300]

    def decide(self, node, role):
        """-> {"ok": bool, "reason": str, "source": ..., evidence...}"""
        base = {"source": self.cfg["source"], "node": node.get("name"), "role": role}
        if node.get("kind") == "ssh" and not node.get("host_fingerprint"):
            return {**base, "ok": False, "reason": "node has no pinned host key"}
        if role not in (node.get("roles") or []) and not (role == "build" and "tools" in (node.get("roles") or [])):
            return {**base, "ok": False, "reason": f"Haven enrollment does not grant role {role}"}
        if self.cfg["source"] == "enrollment":
            return {**base, "ok": True, "reason": "Haven enrollment only (no external trust source configured)"}
        if self.error:
            return {**base, "ok": False, "reason": self.error}
        tsz_id = node.get("tsz_node_id")
        if not tsz_id:
            return {**base, "ok": False, "reason": "node is not bound to a TSZ identity (fleet.py bind)"}
        approved = (self.state.get("nodes") or {}).get(tsz_id)
        if not approved:
            return {**base, "ok": False, "reason": f"no current approval for {tsz_id} (absent or revoked)",
                    "tsz_node_id": tsz_id, "generation": self.state.get("generation")}
        ev = {"tsz_node_id": tsz_id, "candidate_id": approved.get("candidate_id"),
              "approved_until": approved.get("approved_until"), "generation": self.state.get("generation")}
        until = approved.get("approved_until")
        if type(until) is not int or until <= self.now:
            return {**base, **ev, "ok": False, "reason": "approval expired"}
        need = ROLE_MAP.get(role)
        if need is None or need not in (approved.get("roles") or []):
            return {**base, **ev, "ok": False, "reason": f"approval does not grant TSZ role {need or '(none)'}"}
        cand = (self.state.get("candidates") or {}).get(approved.get("candidate_id")) or {}
        addr = node.get("address")
        if addr and cand.get("addresses") and _is_ip(addr) and addr not in cand["addresses"]:
            return {**base, **ev, "ok": False,
                    "reason": "bound discovery record never saw this node's address; binding looks wrong"}
        return {**base, **ev, "ok": True, "reason": f"approved by external trust model until {until}"}


def _is_ip(s):
    try:
        ipaddress.ip_address(s)
        return True
    except ValueError:
        return False
