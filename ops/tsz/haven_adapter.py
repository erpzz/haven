"""TSZ admission/accounting adapter for Haven's existing engineering system.

Caller supplies Haven fleet module and Executor; this module creates neither.
All coordinator writers share the private TSZ directory and its fleet lock.
Only a bounded list_dir diagnostic is dispatchable in this first slice.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import uuid

try:
    from . import fleet, private_io, worker_runtime as worker
except ImportError:
    import fleet
    import private_io
    import worker_runtime as worker

ROLE_MAP = {"inventory": "tools", "engineering": "tools", "inference": "inference"}
ACTIVE = {"RESERVED", "RUNNING", "UNKNOWN"}
FINAL = {"succeeded", "failed", "refused"}


class AdmissionError(ValueError):
    pass


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def approved_view(state, registry, bindings, now):
    """Intersect external approvals and existing Haven enrollment; never enroll.

    bindings: node_id -> {candidate_id, haven_name, kind, ssh?, host_fingerprint?}.
    A local binding must be installed by the owner on the corresponding host.
    Neither ARP nor an observed address is used to choose an SSH destination.
    """
    if (not isinstance(state, dict) or not isinstance(state.get("nodes"), dict)
            or type(state.get("approval_revision")) is not int
            or not isinstance(bindings, dict) or not isinstance(registry, dict)
            or not isinstance(registry.get("nodes"), list)):
        raise AdmissionError("versioned approvals, explicit bindings and Haven nodes are required")
    enrolled = {}
    for node in registry["nodes"]:
        if not isinstance(node, dict) or not isinstance(node.get("name"), str) or node["name"] in enrolled:
            raise AdmissionError("malformed or duplicate Haven node")
        enrolled[node["name"]] = node
    result, used = {}, set()
    for node_id, node in state["nodes"].items():
        if not worker.valid_node(node, now):
            continue
        binding = bindings.get(node_id)
        if not isinstance(binding, dict) or binding.get("candidate_id") != node["candidate_id"]:
            continue
        if not isinstance(binding.get("haven_name"), str):
            continue
        host = enrolled.get(binding["haven_name"])
        if not host or binding.get("kind") != host.get("kind"):
            continue
        roles = host.get("roles")
        if not isinstance(roles, list) or any(not isinstance(r, str) for r in roles):
            continue
        kind = host["kind"]
        if kind == "ssh":
            alias = host.get("ssh")
            pin = host.get("host_fingerprint")
            if (not isinstance(alias, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", alias)
                    or not isinstance(pin, str) or not pin.startswith("SHA256:")
                    or binding.get("ssh") != alias or binding.get("host_fingerprint") != pin
                    or host.get("trust") != "OWNER_SSH"):
                continue
        elif kind != "local" or host.get("trust") != "LOCAL_HOST":
            continue
        identity = (kind, host.get("host_fingerprint") if kind == "ssh" else "local")
        if identity in used:
            raise AdmissionError("multiple TSZ identities refer to the same Haven host")
        used.add(identity)
        permitted = [r for r in node["roles"] if ROLE_MAP.get(r) in roles]
        if permitted:
            result[node_id] = {**node, "roles": permitted, "haven": copy.deepcopy(host),
                               "binding_digest": _digest(binding)}
    return {"nodes": result}


def collect(state, registry, bindings, haven_fleet, now=None):
    """Explicit caller-invoked probes via Haven's authenticated observer methods.

    Bypasses fleet.observe's cache and implicit local fallback. Failed observations
    are omissions, never zero/free capacity. No training or inference readiness.
    """
    now = int(time.time()) if now is None else now
    view = approved_view(state, registry, bindings, now)
    reports = {}
    for node_id, node in view["nodes"].items():
        host = node["haven"]
        try:
            obs = haven_fleet.observe_local() if host["kind"] == "local" else haven_fleet.observe_ssh(host)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, KeyError, TypeError, IndexError):
            continue
        if not isinstance(obs, dict) or obs.get("status", "ONLINE") != "ONLINE":
            continue
        cores, memory = obs.get("cores"), obs.get("mem_avail")
        if type(cores) is not int or cores < 1 or type(memory) is not int or memory < 0:
            continue
        # Haven's macOS estimate includes reclaimable pages. For the local Mac,
        # use TSZ's stricter free+speculative estimate; remote OS memory must be
        # Linux MemAvailable until a conservative remote Mac probe is integrated.
        if host["kind"] == "local" and worker.platform.system() == "Darwin":
            memory_mib = worker.available_memory_mib()
            if memory_mib is None:
                continue
        elif str(obs.get("os", "")).startswith("Linux"):
            memory_mib = memory // (1024 * 1024)
        else:
            continue
        reports[node_id] = {"schema": worker.SCHEMA, "node_id": node_id,
                           "candidate_id": node["candidate_id"], "roles": node["roles"],
                           "recorded_at": now, "cpu_cores": cores, "ram_available_mib": memory_mib,
                           "inference_runtime_ready": False, "gpu_free_mib": None,
                           "binding_digest": node["binding_digest"],
                           "source": "haven-authenticated-fleet-observer"}
    return reports


class Coordinator:
    """Serialized reservations and at-most-once handoff for a single coordinator.

    A RUNNING/UNKNOWN reservation NEVER expires automatically: a crash is not
    proof that a job stopped. Completed job IDs remain tombstones. No retry of
    an uncertain handoff; the integration owner must reconcile its real receipt.
    Capacity here is admission accounting, not an OS CPU/RAM limit.
    """
    def __init__(self, directory, registry, bindings, clock=time.time):
        self.directory = private_io.private_dir(directory)
        # Providers must read current owner state, not capture a cached snapshot.
        self.registry, self.bindings, self.clock = registry, bindings, clock

    def _inputs(self, now):
        state = fleet.read_state(self.directory)
        return approved_view(state, self.registry(), self.bindings(), now)

    def _load(self):
        try:
            data = private_io.read_json(self.directory / "reservations.json")
        except FileNotFoundError:
            return {"schema": "tsz-reservations-v1", "jobs": {}}
        if data.get("schema") != "tsz-reservations-v1" or not isinstance(data.get("jobs"), dict):
            raise AdmissionError("invalid reservation state")
        for key, rec in data["jobs"].items():
            if (not isinstance(rec, dict) or rec.get("status") not in ACTIVE | {"DONE", "CANCELLED"}
                    or not isinstance(rec.get("job"), dict) or rec["job"].get("id") != key
                    or type(rec.get("expires_at")) is not int or not isinstance(rec.get("node_id"), str)
                    or type(rec["job"].get("cpu_cores")) is not int or rec["job"]["cpu_cores"] < 1
                    or type(rec["job"].get("memory_mib")) is not int or rec["job"]["memory_mib"] < 0):
                raise AdmissionError("malformed reservation; refusing to reset accounting")
        return data

    def _save(self, data):
        private_io.write_json(self.directory / "reservations.json", data)

    @staticmethod
    def _job(job):
        # No shell, inference, writes, model loads or unconstrained tool selection.
        if (not isinstance(job, dict) or set(job) != {"id", "role", "cpu_cores", "memory_mib", "tool", "args"}
                or job.get("role") not in ("inventory", "engineering")
                or job.get("tool") != "list_dir" or job.get("args") != {"path": ".", "depth": 1}
                or type(job.get("cpu_cores")) is not int or job["cpu_cores"] != 1
                or type(job.get("memory_mib")) is not int or not 16 <= job["memory_mib"] <= 256):
            raise AdmissionError("slice accepts only list_dir('.', depth=1), one CPU and 16..256 MiB")
        # Reuse planner validation of ID and resource/role types, with no eligible nodes.
        worker.place_jobs({"nodes": {}}, {}, [job], 0)

    def reserve(self, job, reports, ttl=30):
        self._job(job)
        if type(ttl) is not int or not 1 <= ttl <= 60:
            raise AdmissionError("reservation TTL must be 1..60 seconds")
        with private_io.lock(self.directory):
            now = int(self.clock())
            view, data = self._inputs(now), self._load()
            if not isinstance(reports, dict):
                raise AdmissionError("reports must be an object")
            if job["id"] in data["jobs"]:
                raise AdmissionError("job ID already exists; replay is forbidden")
            available = copy.deepcopy(reports)
            for node_id, hb in list(available.items()):
                node = view["nodes"].get(node_id)
                if not isinstance(hb, dict) or not node or hb.get("binding_digest") != node["binding_digest"]:
                    del available[node_id]
            for rec in data["jobs"].values():
                if rec["status"] == "RESERVED" and rec["expires_at"] <= now:
                    rec["status"] = "CANCELLED"
                if rec["status"] in ACTIVE and rec["node_id"] in available:
                    hb = available[rec["node_id"]]
                    # Subtract all live reservations even from a newer observation.
                    # This can double-count measured usage, deliberately conservative.
                    for field, cost in (("cpu_cores", "cpu_cores"), ("ram_available_mib", "memory_mib")):
                        if type(hb.get(field)) is int:
                            hb[field] = max(0, hb[field] - rec["job"][cost])
            placed = worker.place_jobs(view, available, [job], now)[0]
            if placed["status"] != "PLANNED_ONLY":
                self._save(data)
                return placed
            node_id = placed["node_id"]
            node = view["nodes"][node_id]
            rec = {"job": copy.deepcopy(job), "node_id": node_id, "status": "RESERVED",
                   "token": uuid.uuid4().hex, "binding_digest": node["binding_digest"],
                   "candidate_id": node["candidate_id"],
                   "expires_at": min(now + ttl, node["approved_until"], reports[node_id]["recorded_at"] + 90)}
            data["jobs"][job["id"]] = rec
            self._save(data)
            return copy.deepcopy(rec)

    def cancel(self, job_id, token):
        with private_io.lock(self.directory):
            data = self._load()
            rec = self._record(data, job_id, token)
            if rec["status"] != "RESERVED":
                raise AdmissionError("only an unstarted reservation can be cancelled")
            rec["status"] = "CANCELLED"
            self._save(data)

    @staticmethod
    def _record(data, job_id, token):
        rec = data["jobs"].get(job_id)
        if not rec or not isinstance(token, str) or rec.get("token") != token:
            raise AdmissionError("unknown reservation/token")
        return rec

    def dispatch_local(self, job_id, token, executor, haven_fleet):
        # Re-probe and re-admit at dispatch. Hold the shared lock through this one
        # fixed read call so an approval update cannot linearize before dispatch.
        # No arbitrary command can hold the lock waiting on a model/owner prompt.
        with private_io.lock(self.directory):
            now = int(self.clock())
            data = self._load()
            rec = self._record(data, job_id, token)
            self._job(rec["job"])
            if rec["status"] != "RESERVED" or rec["expires_at"] <= now:
                raise AdmissionError("reservation expired or already handed off")
            state, registry, bindings = fleet.read_state(self.directory), self.registry(), self.bindings()
            view = approved_view(state, registry, bindings, now)
            node = view["nodes"].get(rec["node_id"])
            if (not node or node["binding_digest"] != rec["binding_digest"]
                    or node["candidate_id"] != rec["candidate_id"]):
                raise AdmissionError("approval or binding revoked")
            if node["haven"]["kind"] != "local":
                raise AdmissionError("remote Executor transport is not integrated; refusing local fallback")
            # Probe only the chosen host; do not contact unrelated approved nodes.
            reports = collect(state, registry, {rec["node_id"]: bindings[rec["node_id"]]}, haven_fleet, now)
            current = int(self.clock())
            # Probe latency must not carry a job across its approval/lease expiry.
            if current >= rec["expires_at"]:
                raise AdmissionError("reservation expired during telemetry refresh")
            # Providers can change while a probe is in flight. Re-read before
            # handoff; integration writers must also use this coordinator lock.
            view = self._inputs(current)
            node = view["nodes"].get(rec["node_id"])
            if not node or node["binding_digest"] != rec["binding_digest"]:
                raise AdmissionError("binding changed during telemetry refresh")
            hb = reports.get(rec["node_id"])
            if not hb:
                raise AdmissionError("no current telemetry")
            for other in data["jobs"].values():
                if other is rec or other["node_id"] != rec["node_id"]:
                    continue
                if other["status"] in {"RUNNING", "UNKNOWN"} or (
                        other["status"] == "RESERVED" and other["expires_at"] > current):
                    hb["cpu_cores"] -= other["job"]["cpu_cores"]
                    hb["ram_available_mib"] -= other["job"]["memory_mib"]
            if worker.place_jobs(view, reports, [rec["job"]], current)[0]["status"] != "PLANNED_ONLY":
                raise AdmissionError("capacity or role no longer eligible")
            rec["status"] = "RUNNING"
            self._save(data)  # Durable before calling the existing executor.
            try:
                result = executor.call(rec["job"]["tool"], rec["job"]["args"])
            except BaseException:
                rec["status"] = "UNKNOWN"
                self._save(data)
                raise
            known = (isinstance(result, dict) and result.get("status") in FINAL
                     and isinstance(result.get("receipt"), str) and bool(result["receipt"]))
            rec["status"] = "DONE" if known else "UNKNOWN"
            # Keep only receipt references here; private output remains in Haven's ledger.
            if isinstance(result, dict):
                rec["executor_receipt"] = result.get("receipt")
                rec["executor_status"] = result.get("status")
            self._save(data)
            return result
