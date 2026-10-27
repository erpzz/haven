#!/usr/bin/env python3
"""Durable job scheduler for enrolled nodes: the one fleet controller.

Jobs are files; a crash or restart of this process loses nothing. Each tick,
under one lock: re-check trust and telemetry, start queued jobs on an eligible
node, poll running ones, cancel what the owner cancelled or the trust model
revoked, and reconcile anything left uncertain. Every job has one signed
receipt in the scheduler ledger: proposed (submitted) -> authorized (trust
decision) -> executed (handed to a node's worker) -> succeeded / failed /
unknown (a runner that vanished is unknown, never success).

Placement needs, per node: Haven enrollment and the trust gate for the job's
role (trust.py, which consumes the external trust model's TSZ approvals), a
fresh ONLINE observation with the pinned host key, and CPU/RAM headroom after
subtracting the other jobs this scheduler has running there. GPU jobs are not
placed: the GPU belongs to whoever holds the Model Lab lease.

Workers are user-space (worker.py) and reached over the node's pinned SSH
alias (remote.py); the local host runs the same worker directly.

  scheduler.py submit --repo REPO --command CMD [--node N] [--cpu 1] [--mem-mib 512] [--timeout 600]
  scheduler.py tick | serve [--interval 5] | list | show ID | cancel ID
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import uuid

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fleet  # noqa: E402
import trust  # noqa: E402
from ledger import Ledger  # noqa: E402
from session import STATE  # noqa: E402

TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED", "TIMED_OUT", "LOST", "REFUSED"}
ACTIVE = {"STARTING", "RUNNING", "CANCEL_REQUESTED"}
MiB = 1024 * 1024
STALE_OBS_S = 60


class SchedError(RuntimeError):
    pass


# ---- transports --------------------------------------------------------------

class LocalTransport:
    def __init__(self, node):
        self.node = node

    def worker(self, *args, stdin=None):
        r = subprocess.run([sys.executable, "-I", str(HERE / "worker.py"), *args], capture_output=True, text=True,
                           timeout=60, input=stdin)
        if r.returncode:
            raise SchedError(f"local worker: {r.stderr.strip()[-300:]}")
        return r.stdout

    def workspace(self, repo, name):
        dest = pathlib.Path.home() / ".local/share/haven-workspaces" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", str(repo), str(dest)], check=True, capture_output=True)
        return str(dest)


class SSHTransport:
    def __init__(self, node):
        import remote
        self.node, self.remote = node, remote
        self.rt = remote.stage(node)  # re-checks the pinned host key

    def worker(self, *args, stdin=None):
        import shlex
        r = self.remote.run(self.node, f"python3 -I {self.rt}/worker.py " + " ".join(shlex.quote(a) for a in args),
                            timeout=60)
        if r.returncode:
            raise SchedError(f"{self.node['name']} worker: {r.stderr.strip()[-300:]}")
        return r.stdout

    def workspace(self, repo, name):
        return self.remote.push_workspace(self.node, repo, name)["path"]


def transport(node):
    return LocalTransport(node) if node["kind"] == "local" else SSHTransport(node)


# ---- store -------------------------------------------------------------------

class Store:
    def __init__(self, root=None):
        self.root = pathlib.Path(root or STATE / "sched")
        (self.root / "jobs").mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        self._ledger = None

    @property
    def ledger(self):
        """The ledger as of now. Several processes (serve, submit, cancel) append to it, so it is
        re-read on every locked operation; a stale copy would chain from an old hash."""
        return self._ledger or Ledger(self.root / "ledger.jsonl", session="scheduler")

    @contextlib.contextmanager
    def lock(self):
        fd = os.open(self.root / ".lock", os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            self._ledger = Ledger(self.root / "ledger.jsonl", session="scheduler")
            yield
        finally:
            self._ledger = None
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def path(self, jid):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", jid):
            raise SchedError(f"bad job id {jid!r}")
        return self.root / "jobs" / f"{jid}.json"

    def load(self, jid):
        return json.loads(self.path(jid).read_text())

    def save(self, job):
        p = self.path(job["id"])
        tmp = p.with_name(p.name + ".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(job, f, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)

    def jobs(self):
        return sorted((json.loads(p.read_text()) for p in (self.root / "jobs").glob("*.json")),
                      key=lambda j: j["created"])

    def event(self, job, kind, **data):
        job.setdefault("history", []).append({"t": round(time.time(), 3), "event": kind, **data})
        line = json.dumps({"t": round(time.time(), 3), "job": job["id"], "event": kind, **data}) + "\n"
        fd = os.open(self.root / "events.jsonl", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as f:
            f.write(line)


# ---- scheduler -----------------------------------------------------------------

def validate(spec):
    if not isinstance(spec.get("command"), str) or not spec["command"].strip():
        raise SchedError("command is required")
    if bool(spec.get("repo")) == bool(spec.get("workspace")):
        raise SchedError("give exactly one of repo (local git repo to clone) or workspace (path on the node)")
    for k, lo, hi in (("cpu", 1, 64), ("mem_mib", 16, 256 * 1024), ("timeout_s", 1, 24 * 3600)):
        if type(spec.get(k)) is not int or not lo <= spec[k] <= hi:
            raise SchedError(f"{k} must be an integer in {lo}..{hi}")
    if spec.get("gpu"):
        raise SchedError("GPU jobs are not scheduled here; the Model Lab lease owns the GPU")
    if spec.get("role", "tools") not in ("tools", "build"):
        raise SchedError("role must be tools or build")
    return {**spec, "role": spec.get("role", "tools"), "network": bool(spec.get("network"))}


class Scheduler:
    def __init__(self, store=None, *, nodes=None, observe=None, gate=None, transport_for=None, clock=time.time):
        self.store = store or Store()
        self.nodes = nodes or (lambda: fleet.load()["nodes"])
        self.observe = observe or (lambda: {n["name"]: n["observation"] for n in fleet.observe(cache_s=10)["nodes"]})
        self.gate = gate or (lambda: trust.Gate())
        self.transport_for = transport_for or transport
        self.clock = clock
        self._transports = {}

    def submit(self, spec, jid=None):
        spec = validate(spec)
        jid = jid or time.strftime("j%Y%m%dT%H%M%S-") + uuid.uuid4().hex[:6]
        with self.store.lock():
            if self.store.path(jid).exists():
                raise SchedError(f"job {jid} already exists")
            rid = self.store.ledger.propose(f"job:{spec['role']}", spec, agent="scheduler", mode="worker",
                                            klass="job", summary=f"$ {spec['command'][:200]}")
            job = {"id": jid, "spec": spec, "state": "QUEUED", "created": self.clock(), "receipt": rid}
            self.store.event(job, "submitted", receipt=rid)
            self.store.save(job)
        return job

    def cancel(self, jid):
        with self.store.lock():
            job = self.store.load(jid)
            if job["state"] == "QUEUED":
                self._finish(job, "CANCELLED", reason="cancelled by owner before start", refused=True)
            elif job["state"] in ("STARTING", "RUNNING"):
                job["state"] = "CANCEL_REQUESTED"
                self.store.event(job, "cancel_requested")
            self.store.save(job)
            return job

    # -- one pass ------------------------------------------------------------------

    def tick(self):
        with self.store.lock():
            nodes = {n["name"]: n for n in self.nodes()}
            gate = self.gate()
            jobs = self.store.jobs()
            obs, obs_error = {}, None
            if any(j["state"] == "QUEUED" for j in jobs):  # probe the fleet only when something needs placing
                try:
                    obs = self.observe()
                except Exception as e:  # noqa: BLE001 - no telemetry means no new placements this tick
                    obs_error = f"{type(e).__name__}: {e}"
            for job in jobs:
                if job["state"] in ACTIVE:
                    self._poll(job, nodes, gate)
            for job in jobs:
                if job["state"] == "QUEUED":
                    self._place(job, nodes, gate, obs, jobs, obs_error)
            return [{"id": j["id"], "state": j["state"], "node": j.get("node")} for j in jobs]

    def _tr(self, node):
        if node["name"] not in self._transports:
            self._transports[node["name"]] = self.transport_for(node)
        return self._transports[node["name"]]

    def _place(self, job, nodes, gate, obs, jobs, obs_error):
        spec = job["spec"]
        reasons = {}
        best = None
        for name, node in nodes.items():
            if spec.get("node") and name != spec["node"]:
                continue
            d = gate.decide(node, spec["role"])
            if not d["ok"]:
                reasons[name] = d["reason"]
                continue
            o = obs.get(name)
            if not o or o.get("status") != "ONLINE":
                reasons[name] = (o or {}).get("error") or obs_error or "no current observation"
                continue
            if self.clock() - (o.get("observed_at") or 0) > STALE_OBS_S:
                reasons[name] = "observation is stale"
                continue
            mine = [j for j in jobs if j.get("node") == name and j["state"] in ACTIVE]
            load1 = (o.get("load") or [0])[0] or 0
            free_cpu = (o.get("cores") or 0) - load1 - sum(j["spec"]["cpu"] for j in mine)
            free_mem = (o.get("mem_avail") or 0) // MiB - sum(j["spec"]["mem_mib"] for j in mine)
            if free_cpu < spec["cpu"] or free_mem < spec["mem_mib"]:
                reasons[name] = f"no headroom (cpu {free_cpu:.1f}, mem {free_mem} MiB after {len(mine)} jobs)"
                continue
            if best is None or free_cpu > best[1]:
                best = (node, free_cpu, d)
        if best is None:
            if job.get("waiting") != reasons:
                job["waiting"] = reasons
                self.store.event(job, "waiting", reasons=reasons)
                self.store.save(job)
            return
        node, _, decision = best
        job.update(state="STARTING", node=node["name"], trust=decision, placed_at=self.clock())
        job.pop("waiting", None)
        if self.store.ledger.get(job["receipt"])["status"] == "proposed":  # a requeued job is already authorized
            self.store.ledger.transition(job["receipt"], "authorized", decided_by=f"trust:{decision['source']}",
                                         reason=decision["reason"][:300], node=node["name"])
        self.store.event(job, "placed", node=node["name"], trust=decision["reason"])
        self.store.save(job)  # durable before any remote side effect
        self._start(job, node)

    def _start(self, job, node):
        spec = job["spec"]
        try:
            tr = self._tr(node)
            if "node_workspace" not in job:
                job["node_workspace"] = spec.get("workspace") or tr.workspace(spec["repo"], job["id"])
                self.store.save(job)
            wspec = {"command": spec["command"], "workspace": job["node_workspace"], "timeout_s": spec["timeout_s"],
                     "network": spec["network"]}
            st = json.loads(tr.worker("start", job["id"], "--spec", json.dumps(wspec)))
        except Exception as e:  # noqa: BLE001 - uncertain: reconcile on the next tick by asking the worker
            job["start_error"] = f"{type(e).__name__}: {e}"[:300]
            self.store.event(job, "start_uncertain", error=job["start_error"])
            self.store.save(job)
            return
        self._absorb(job, st, node)

    def _absorb(self, job, st, node):
        state = st.get("state")
        if state in ("RUNNING", "STARTING", "CANCELLING"):
            if job["state"] == "STARTING":
                job["state"] = "RUNNING"
                self.store.ledger.transition(job["receipt"], "executed", node=node["name"],
                                             sandbox=st.get("sandbox") or "pending")
                self.store.event(job, "running", node=node["name"], runner_pid=st.get("runner_pid"))
            job["worker"] = st
        elif state in TERMINAL:
            if job["state"] == "STARTING":  # finished before we saw it run
                self.store.ledger.transition(job["receipt"], "executed", node=node["name"],
                                             sandbox=st.get("sandbox") or "unknown")
            job["worker"] = st
            try:
                job["output_tail"] = self._tr(node).worker("tail", job["id"], "--bytes", "4000")
            except Exception:  # noqa: BLE001
                pass
            self._finish(job, state, exit_code=st.get("exit_code"), output_sha256=st.get("output_sha256"),
                         reason=st.get("error"))
        self.store.save(job)

    def _poll(self, job, nodes, gate):
        node = nodes.get(job.get("node"))
        if node is None:
            self.store.event(job, "node_removed")
            job["node_problem"] = "node is no longer enrolled; job state on it is unknown"
            self.store.save(job)
            return
        d = gate.decide(node, job["spec"]["role"])
        if not d["ok"] and job["state"] != "CANCEL_REQUESTED":
            job["state"] = "CANCEL_REQUESTED"
            job["revoked"] = d["reason"]
            self.store.event(job, "trust_revoked", reason=d["reason"])
        try:
            tr = self._tr(node)
            if job["state"] == "CANCEL_REQUESTED":
                st = json.loads(tr.worker("cancel", job["id"]))
            else:
                st = json.loads(tr.worker("status", job["id"]))[0]
        except Exception as e:  # noqa: BLE001 - unreachable node: keep the job, never guess its outcome
            job["node_problem"] = f"{type(e).__name__}: {e}"[:300]
            self.store.event(job, "poll_failed", error=job["node_problem"])
            self.store.save(job)
            return
        job.pop("node_problem", None)
        if st.get("state") == "ABSENT":
            if job["state"] == "STARTING":  # the start never reached the node: safe to retry placement
                job.update(state="QUEUED", node=None)
                if job["spec"].get("repo"):
                    job.pop("node_workspace", None)  # cloned onto the old node only
                self.store.event(job, "requeued", reason="start never reached the worker")
            else:
                self._finish(job, "LOST", reason="worker has no record of a job it was running")
            self.store.save(job)
            return
        self._absorb(job, st, node)

    def _finish(self, job, state, *, refused=False, **fields):
        job["state"], job["finished_at"] = state, self.clock()
        fields = {k: v for k, v in fields.items() if v is not None}
        cur = (self.store.ledger.get(job["receipt"]) or {}).get("status")
        if refused or cur == "proposed":
            self.store.ledger.transition(job["receipt"], "refused", reason=fields.get("reason") or state)
        elif cur == "authorized":
            self.store.ledger.transition(job["receipt"], "unknown", error=f"{state} before execution")
        else:
            status = {"SUCCEEDED": "succeeded", "LOST": "unknown"}.get(state, "failed")
            if state in ("CANCELLED", "TIMED_OUT"):
                fields.update(cancelled=state == "CANCELLED", timed_out=state == "TIMED_OUT")
            self.store.ledger.transition(job["receipt"], status, **fields)
        self.store.event(job, "finished", state=state, **{k: v for k, v in fields.items() if k != "reason"})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit")
    s.add_argument("--repo")
    s.add_argument("--workspace")
    s.add_argument("--command", required=True)
    s.add_argument("--node")
    s.add_argument("--cpu", type=int, default=1)
    s.add_argument("--mem-mib", type=int, default=512)
    s.add_argument("--timeout", type=int, default=600)
    s.add_argument("--network", action="store_true")
    s.add_argument("--id")
    sub.add_parser("tick")
    sv = sub.add_parser("serve")
    sv.add_argument("--interval", type=float, default=5)
    sub.add_parser("list")
    sh = sub.add_parser("show")
    sh.add_argument("id")
    c = sub.add_parser("cancel")
    c.add_argument("id")
    args = ap.parse_args(argv)
    sch = Scheduler()
    if args.cmd == "submit":
        spec = {"command": args.command, "cpu": args.cpu, "mem_mib": args.mem_mib, "timeout_s": args.timeout,
                "network": args.network, "node": args.node,
                "repo": os.path.realpath(args.repo) if args.repo else None, "workspace": args.workspace}
        print(json.dumps(sch.submit({k: v for k, v in spec.items() if v is not None}, args.id), indent=1))
    elif args.cmd == "tick":
        print(json.dumps(sch.tick(), indent=1))
    elif args.cmd == "serve":
        while True:
            sch.tick()
            time.sleep(args.interval)
    elif args.cmd == "list":
        for j in sch.store.jobs():
            print(f"{j['id']:<32} {j['state']:<17} {j.get('node') or '-':<8} {j['receipt']}  "
                  f"{j['spec']['command'][:60]}")
    elif args.cmd == "show":
        print(json.dumps(sch.store.load(args.id), indent=1))
    elif args.cmd == "cancel":
        print(json.dumps(sch.cancel(args.id), indent=1))


if __name__ == "__main__":
    main()
