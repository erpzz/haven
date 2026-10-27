#!/usr/bin/env python3
"""Node-side user-space worker: durable, sandboxed jobs that outlive the connection.

The Mac scheduler (scheduler.py) reaches an enrolled node over its pinned SSH
alias and calls this file there. Nothing here listens on a port, installs a
service or needs privileges. Each job is a directory under the worker state:

  jobs/<id>/spec.json     what to run (written once; a second start is a no-op)
  jobs/<id>/runner.json   runner pid + kernel start time (pid reuse is detected)
  jobs/<id>/beat          touched every few seconds while the runner lives
  jobs/<id>/output.log    combined stdout/stderr, capped
  jobs/<id>/exit.json     final state, written atomically by the runner
  jobs/<id>/cancel        cancel request

A runner that disappears without exit.json is reported LOST, never succeeded.
Commands run under this host's sandbox (Landlock / Seatbelt) with writes
limited to the job workspace and a private temp dir, network off unless the
spec says otherwise, at low CPU and I/O priority so live GPU/model work wins.

  worker.py start ID --spec JSON     # idempotent by ID
  worker.py status ID [ID ...]       # JSON, one object per ID
  worker.py cancel ID
  worker.py tail ID [--bytes N]
  worker.py list
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
STATE = pathlib.Path(os.environ.get("HAVEN_WORKER_STATE", pathlib.Path.home() / ".local/state/haven-engineer/worker"))
JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
OUTPUT_CAP = 4 * 1024 * 1024
CACHE = pathlib.Path(os.environ.get("HAVEN_WORKER_CACHE", pathlib.Path.home() / ".cache/haven-engineer/worker"))
BEAT_S = 3


def job_dir(jid):
    if not JOB_ID.fullmatch(jid or ""):
        raise SystemExit(f"invalid job id {jid!r}")
    return STATE / "jobs" / jid


def _write(path, obj):
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def proc_start(pid):
    """Kernel start time of pid (opaque string), or None if it is not running."""
    try:
        if sys.platform.startswith("linux"):
            stat = pathlib.Path(f"/proc/{pid}/stat").read_text()
            return stat[stat.rindex(")") + 2:].split()[19]
        out = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None


def validate_spec(spec):
    if not isinstance(spec, dict) or not isinstance(spec.get("command"), str) or not spec["command"].strip():
        raise SystemExit("spec needs a command")
    ws = pathlib.Path(os.path.expanduser(spec.get("workspace") or "")).resolve()
    if not ws.is_dir():
        raise SystemExit(f"workspace {ws} is not a directory on this node")
    home = pathlib.Path.home().resolve()
    if ws == home or home not in ws.parents:
        raise SystemExit("workspace must be a directory inside the worker's home, not the home itself")
    timeout = spec.get("timeout_s", 600)
    if type(timeout) is not int or not 1 <= timeout <= 24 * 3600:
        raise SystemExit("timeout_s must be 1..86400")
    return {**spec, "workspace": str(ws), "timeout_s": timeout, "network": bool(spec.get("network"))}


def start(jid, spec):
    d = job_dir(jid)
    spec = validate_spec(spec)
    d.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(STATE, 0o700)
    try:
        d.mkdir(mode=0o700)
    except FileExistsError:
        # At-most-once: an existing job is reported, never started twice.
        return {**status(jid), "already_started": True}
    _write(d / "spec.json", {**spec, "accepted_at": time.time()})
    log = open(d / "runner.log", "ab")
    proc = subprocess.Popen([sys.executable, "-I", str(HERE / "worker.py"), "_run", jid],
                            stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True,
                            env={**os.environ, "HAVEN_WORKER_STATE": str(STATE), "HAVEN_WORKER_CACHE": str(CACHE)})
    log.close()
    for _ in range(100):
        if (d / "runner.json").exists() or proc.poll() is not None:
            break
        time.sleep(0.05)
    return status(jid)


def _run(jid):
    """The detached runner. Owns the job's process group and writes exit.json."""
    d = job_dir(jid)
    spec = _read(d / "spec.json")
    _write(d / "runner.json", {"pid": os.getpid(), "start": proc_start(os.getpid()), "started_at": time.time()})
    ws = pathlib.Path(spec["workspace"])
    # Outside the worker state, which the sandbox denies to commands.
    tmp = CACHE / jid
    tmp.mkdir(mode=0o700, parents=True, exist_ok=True)
    argv = ["/bin/bash", "-o", "pipefail", "-c", spec["command"]]
    sys.path.insert(0, str(HERE))
    import sandbox
    info = sandbox.describe()
    if info["available"]:
        argv = sandbox.wrap(argv, workspace=ws, tmpdir=tmp, network=spec["network"])
    elif not spec.get("allow_unsandboxed"):
        _write(d / "exit.json", {"state": "FAILED", "exit_code": None, "error": "no OS sandbox on this node",
                                 "finished_at": time.time()})
        return
    prio = []
    if shutil.which("nice"):
        prio = ["nice", "-n", str(int(spec.get("nice", 15)))]
    if shutil.which("ionice"):
        prio = ["ionice", "-c", "3", *prio]
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(pathlib.Path.home()), "TMPDIR": str(tmp),
           "LANG": os.environ.get("LANG", "C.UTF-8"), "PYTHONDONTWRITEBYTECODE": "1", "GIT_TERMINAL_PROMPT": "0"}
    out = open(d / "output.log", "wb")
    child = subprocess.Popen(prio + argv, cwd=ws, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, start_new_session=True)
    _write(d / "runner.json", {"pid": os.getpid(), "start": proc_start(os.getpid()), "started_at": time.time(),
                               "child_pid": child.pid, "sandbox": info["backend"]})
    stopping = {"why": None}

    def on_term(signum, _frame):
        stopping["why"] = stopping["why"] or "cancelled"

    signal.signal(signal.SIGTERM, on_term)
    os.set_blocking(child.stdout.fileno(), False)
    written, truncated = 0, False
    deadline = time.monotonic() + spec["timeout_s"]
    last_beat = 0.0
    while True:
        try:
            chunk = child.stdout.read(65536)
        except BlockingIOError:
            chunk = None
        if chunk:
            if written < OUTPUT_CAP:
                out.write(chunk[:OUTPUT_CAP - written])
                out.flush()
            truncated = truncated or written + len(chunk) > OUTPUT_CAP
            written += len(chunk)
            continue
        if child.poll() is not None and not chunk:
            break
        if (d / "cancel").exists():
            stopping["why"] = stopping["why"] or "cancelled"
        if time.monotonic() > deadline:
            stopping["why"] = stopping["why"] or "timed_out"
        if stopping["why"]:
            _killpg(child.pid)
            child.wait()
            break
        if time.monotonic() - last_beat > BEAT_S:
            (d / "beat").touch()
            last_beat = time.monotonic()
        time.sleep(0.1)
    code = child.wait()
    out.close()
    state = {"cancelled": "CANCELLED", "timed_out": "TIMED_OUT"}.get(stopping["why"]) or (
        "SUCCEEDED" if code == 0 else "FAILED")
    _write(d / "exit.json", {"state": state, "exit_code": code, "output_bytes": written, "truncated": truncated,
                             "output_sha256": _sha(d / "output.log"), "finished_at": time.time(),
                             "sandbox": info["backend"]})


def _sha(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _killpg(pid):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pid, sig)
        except (ProcessLookupError, PermissionError):
            return
        for _ in range(30):
            try:
                os.killpg(pid, 0)
            except (ProcessLookupError, PermissionError):
                return
            time.sleep(0.1)


def status(jid):
    d = job_dir(jid)
    if not d.is_dir():
        return {"id": jid, "state": "ABSENT"}
    spec = _read(d / "spec.json") or {}
    ex = _read(d / "exit.json")
    runner = _read(d / "runner.json") or {}
    beat = d / "beat"
    out = {"id": jid, "accepted_at": spec.get("accepted_at"), "runner_pid": runner.get("pid"),
           "started_at": runner.get("started_at"), "sandbox": runner.get("sandbox"),
           "beat_age_s": round(time.time() - beat.stat().st_mtime, 1) if beat.exists() else None,
           "output_bytes": (d / "output.log").stat().st_size if (d / "output.log").exists() else 0}
    if ex:
        return {**out, **ex}
    alive = runner.get("pid") and proc_start(runner["pid"]) == runner.get("start")
    if alive:
        return {**out, "state": "CANCELLING" if (d / "cancel").exists() else "RUNNING"}
    if not runner and spec and time.time() - spec.get("accepted_at", 0) < 10:
        return {**out, "state": "STARTING"}
    return {**out, "state": "LOST", "error": "runner is gone and left no exit record"}


def cancel(jid):
    d = job_dir(jid)
    if not d.is_dir():
        return {"id": jid, "state": "ABSENT"}
    (d / "cancel").touch()
    runner = _read(d / "runner.json") or {}
    if runner.get("pid") and proc_start(runner["pid"]) == runner.get("start"):
        try:
            os.kill(runner["pid"], signal.SIGTERM)
        except ProcessLookupError:
            pass
    return status(jid)


def tail(jid, n=4000):
    p = job_dir(jid) / "output.log"
    if not p.exists():
        return ""
    with open(p, "rb") as f:
        f.seek(max(0, p.stat().st_size - n))
        return f.read().decode(errors="replace")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("id")
    s.add_argument("--spec", required=True)
    st = sub.add_parser("status")
    st.add_argument("ids", nargs="+")
    c = sub.add_parser("cancel")
    c.add_argument("id")
    t = sub.add_parser("tail")
    t.add_argument("id")
    t.add_argument("--bytes", type=int, default=4000)
    sub.add_parser("list")
    r = sub.add_parser("_run")
    r.add_argument("id")
    args = ap.parse_args(argv)
    if args.cmd == "_run":
        return _run(args.id)
    if args.cmd == "start":
        print(json.dumps(start(args.id, json.loads(args.spec))))
    elif args.cmd == "status":
        print(json.dumps([status(j) for j in args.ids]))
    elif args.cmd == "cancel":
        print(json.dumps(cancel(args.id)))
    elif args.cmd == "tail":
        sys.stdout.write(tail(args.id, args.bytes))
    elif args.cmd == "list":
        jobs = STATE / "jobs"
        print(json.dumps([status(p.name) for p in sorted(jobs.iterdir())] if jobs.is_dir() else []))


if __name__ == "__main__":
    main()
