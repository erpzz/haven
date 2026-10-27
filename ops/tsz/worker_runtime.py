"""TSZ owner-invoked, unprivileged worker and deterministic job-placement plan.

No server, socket, SSH, shell subprocess, model inference, daemon management,
remote installation or network discovery. Enrollment decisions live in fleet.py
and originate from an external owner-controlled trust engine.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import stat
import sys
import time

ID = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")
ROLES = frozenset({"inventory", "inference", "engineering", "training"})
MAX_HEARTBEAT_AGE = 90
SCHEMA = "tsz-worker-heartbeat-v1"


class WorkerError(ValueError):
    pass


def private_dir(directory: Path) -> Path:
    directory = directory.expanduser()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
        raise WorkerError("worker directory must be an owner-private directory")
    return directory


def read_private_json(path: Path) -> dict:
    """Limit stale links and world-readable input in an owner-managed runtime."""
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
        raise WorkerError("private JSON must be an owner-owned, private regular file")
    if info.st_size > 1024 * 1024:
        raise WorkerError("JSON input exceeds the allowed limit")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise WorkerError("expected JSON object")
    return data


def write_private_json(path: Path, document: dict) -> None:
    """Atomic mode-0600 local file replacement, no network communication."""
    directory = private_dir(path.parent)
    if path.exists() and (path.is_symlink() or path.stat().st_uid != os.getuid()):
        raise WorkerError("refusing to overwrite untrusted file")
    tmp = directory / (".tsz-" + str(os.getpid()) + "-" + path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(document, out, indent=2, sort_keys=True)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def stage_local_worker(fleet: dict, node_id: str, workdir: Path, now: int) -> dict:
    """Prepare local worker state only after upstream approval is present.

    This is an owner-invoked local operation, not a remote bootstrap or
    autonomous node enrollment mechanism.
    """
    if not isinstance(node_id, str) or not ID.fullmatch(node_id):
        raise WorkerError("invalid node ID")
    node = fleet.get("nodes", {}).get(node_id)
    if not isinstance(node, dict) or node.get("approved_until", 0) <= now:
        raise WorkerError("node is not currently approved")
    roles = node.get("roles", [])
    candidate = node.get("candidate_id")
    if (not isinstance(roles, list) or not roles or not set(roles) <= ROLES
            or not isinstance(candidate, str) or not candidate.startswith("neighbor-")):
        raise WorkerError("invalid approved-node metadata")
    workdir = private_dir(workdir)
    destination = workdir / "worker.json"
    if destination.exists():
        old = read_private_json(destination)
        if old.get("node_id") != node_id or old.get("candidate_id") != candidate:
            raise WorkerError("worker binding differs from previously staged identity")
    state = {"schema": "tsz-local-worker-v1", "node_id": node_id,
             "candidate_id": candidate, "roles": sorted(roles),
             "approved_until": node["approved_until"], "staged_at": now}
    write_private_json(destination, state)
    return state


def parse_vm_stat(text: str) -> int | None:
    """Conservative approximation from macOS page counters, not a free-memory guarantee."""
    import re
    page = re.search(r"page size of (\d+) bytes", text)
    if not page:
        return None
    counters = {}
    for line in text.splitlines():
        match = re.match(r"Pages (free|speculative|inactive):\s*(\d+)\.", line.strip())
        if match:
            counters[match.group(1)] = int(match.group(2))
    if "free" not in counters:
        return None
    # Inactive memory may be reclaimable, but isn't necessarily instantly free.
    # Use only free + speculative pages for conservative planning.
    pages = counters["free"] + counters.get("speculative", 0)
    return (pages * int(page.group(1))) // (1024 * 1024)


def available_memory_mib() -> int | None:
    system = platform.system()
    if system == "Darwin":
        try:
            report = subprocess.run(["vm_stat"], capture_output=True, text=True,
                                    timeout=5, check=True)
            return parse_vm_stat(report.stdout)
        except (OSError, subprocess.SubprocessError):
            return None
    if system != "Linux":
        return None
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def create_local_heartbeat(config: dict, workdir: Path, now: int) -> dict:
    if config.get("schema") != "tsz-local-worker-v1" or config.get("approved_until", 0) <= now:
        raise WorkerError("worker is not approved or its approval has expired")
    total, used, free = shutil.disk_usage(workdir)
    return {"schema": SCHEMA, "node_id": config["node_id"],
            "candidate_id": config["candidate_id"], "roles": config["roles"],
            "recorded_at": now, "cpu_cores": os.cpu_count(),
            "ram_available_mib": available_memory_mib(),
            "disk_free_mib": free // (1024 * 1024),
            "architecture": platform.machine(),
            "gpu_free_mib": None, "inference_runtime_ready": False,
            "memory_estimate": "macos-free-and-speculative-pages" if platform.system() == "Darwin" else "linux-memavailable" if platform.system() == "Linux" else "unknown",
            "source": "owner-invoked-local-probe"}


def emit_heartbeat(workdir: Path, now: int) -> dict:
    workdir = private_dir(workdir)
    config = read_private_json(workdir / "worker.json")
    heartbeat = create_local_heartbeat(config, workdir, now)
    write_private_json(workdir / "heartbeat.json", heartbeat)
    return heartbeat


def usable_heartbeat(fleet: dict, node_id: str, heartbeat: dict, now: int) -> bool:
    node = fleet.get("nodes", {}).get(node_id)
    if not isinstance(node, dict) or node.get("approved_until", 0) <= now:
        return False
    if heartbeat.get("schema") != SCHEMA or heartbeat.get("node_id") != node_id:
        return False
    if heartbeat.get("candidate_id") != node.get("candidate_id"):
        return False
    captured = heartbeat.get("recorded_at")
    if type(captured) is not int or captured > now or now - captured > MAX_HEARTBEAT_AGE:
        return False
    return set(heartbeat.get("roles", [])) <= set(node.get("roles", []))


def place_jobs(fleet: dict, heartbeats: dict, jobs: list[dict], now: int) -> list[dict]:
    """Deterministic placement proposals; this function NEVER executes jobs.

    Only uses previously approved nodes, fresh local heartbeat observations,
    and explicit work requests. Fairly spreads workload by reserving a slot
    for a node before considering it again. No extrapolated free GPU resources.
    """
    remaining = {}
    for node_id, telemetry in heartbeats.items():
        if not usable_heartbeat(fleet, node_id, telemetry, now):
            continue
        cores = telemetry.get("cpu_cores")
        memory = telemetry.get("ram_available_mib")
        if type(cores) is not int or cores < 1:
            continue
        if memory is not None and (type(memory) is not int or memory < 0):
            continue
        remaining[node_id] = {"cores": cores, "memory": memory, "used": 0}

    results = []
    for job in jobs:
        name, role, cpus, mib = (job.get("id"), job.get("role"),
                                 job.get("cpu_cores"), job.get("memory_mib"))
        if not isinstance(name, str) or not ID.fullmatch(name):
            raise WorkerError("job ID is invalid")
        if role not in ROLES:
            raise WorkerError("job role not recognized")
        if type(cpus) is not int or not (1 <= cpus <= 256):
            raise WorkerError("invalid requested CPU capacity")
        if type(mib) is not int or not (0 <= mib <= 1_048_576):
            raise WorkerError("invalid requested memory")
        choices = []
        for node_id, capacity in remaining.items():
            telemetry = heartbeats[node_id]
            if role not in fleet["nodes"][node_id]["roles"]:
                continue
            if (capacity["cores"] < cpus or capacity["memory"] is None
                    or capacity["memory"] < mib):
                continue
            if role == "inference" and telemetry.get("inference_runtime_ready") is not True:
                continue
            choices.append((capacity["used"], -capacity["memory"], node_id))
        if not choices:
            results.append({"job_id": name, "status": "NO_ELIGIBLE_CAPACITY"})
            continue
        _, _, chosen = min(choices)
        remaining[chosen]["cores"] -= cpus
        remaining[chosen]["memory"] -= mib
        remaining[chosen]["used"] += 1
        results.append({"job_id": name, "status": "PLANNED_ONLY", "node_id": chosen})
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker-dir", type=Path, default=Path("~/.local/state/haven-tsz/worker"))
    actions = parser.add_subparsers(dest="action", required=True)
    stage = actions.add_parser("stage-local")
    stage.add_argument("--fleet", type=Path, required=True)
    stage.add_argument("--node-id", required=True)
    actions.add_parser("heartbeat")
    plan = actions.add_parser("plan-jobs", help="Plan jobs from already-collected private telemetry")
    plan.add_argument("--fleet", type=Path, required=True)
    plan.add_argument("--heartbeats-dir", type=Path, required=True)
    plan.add_argument("--jobs", type=Path, required=True)
    args = parser.parse_args()
    now = int(time.time())
    if args.action == "stage-local":
        fleet = read_private_json(args.fleet.expanduser())
        result = stage_local_worker(fleet, args.node_id, args.worker_dir, now)
    elif args.action == "plan-jobs":
        fleet = read_private_json(args.fleet.expanduser())
        job_doc = read_private_json(args.jobs.expanduser())
        if not isinstance(job_doc.get("jobs"), list):
            raise WorkerError("job document must contain a list of jobs")
        telemetry_dir = private_dir(args.heartbeats_dir)
        heartbeats = {}
        for node_id in fleet.get("nodes", {}):
            if not ID.fullmatch(node_id):
                raise WorkerError("malformed fleet node ID")
            file = telemetry_dir / (node_id + ".json")
            if file.exists():
                heartbeats[node_id] = read_private_json(file)
        result = place_jobs(fleet, heartbeats, job_doc["jobs"], now)
    else:
        result = emit_heartbeat(args.worker_dir, now)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (WorkerError, ValueError, OSError) as exc:
        print("TSZ worker:", exc, file=sys.stderr)
        sys.exit(2)
