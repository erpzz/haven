"""Start/status/stop one owned loopback IP-01 app. No service or auto-restart.

Invoke with the package-local virtual environment from any directory.
The shutdown receipt covers the app and observed descendants only; the
separately owned model backend has its own lifecycle receipt.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid
import urllib.error
import urllib.request

import psutil

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = Path(__file__).resolve()
PRIVATE = ROOT / ".ip01-runtime"
EVALUATOR = ROOT.parent / "haven-ip01-runtime-20260929-eval"


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    pending.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(pending, path)


def runtime_path(value):
    path = Path(value).resolve()
    allowed = (PRIVATE.resolve(), EVALUATOR.resolve())
    if not any(path == parent or parent in path.parents for parent in allowed):
        raise ValueError("runtime directory must be inside this campaign's runtime or evaluator sibling")
    return path


def read_owner(runtime):
    path = runtime / "control/app-owner.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def record_observation(runtime, receipt):
    with (runtime / "control/process-observations.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(receipt) + "\n")


def previously_observed(runtime, owner):
    known = list(owner.get("observed_descendants", [])) if owner else []
    path = runtime / "control/app-stop-observation.json"
    if path.exists() and owner:
        prior = json.loads(path.read_text(encoding="utf-8"))
        if (prior.get("identity") or {}).get("nonce") == owner["nonce"]:
            known.extend(prior.get("descendants_before", []))
            known.extend(prior.get("residual", []))
    return list({(row["pid"], row["process_birth"]): row for row in known}.values())


def observed_process(owner):
    if not owner:
        return None
    try:
        process = psutil.Process(owner["pid"])
        if abs(process.create_time() - owner["process_birth"]) > 0.001:
            raise RuntimeError("PID was reused; ownership mismatch; no stop attempted")
        cmd = process.cmdline()
        if str(SCRIPT) not in cmd or "_serve" not in cmd:
            raise RuntimeError("command identity mismatch; no stop attempted")
        return process
    except psutil.NoSuchProcess:
        return None


def children(process):
    result = []
    try:
        for child in process.children(recursive=True):
            try:
                result.append({"pid": child.pid, "process_birth": child.create_time()})
            except psutil.NoSuchProcess:
                pass
    except psutil.NoSuchProcess:
        pass
    return result


def identity_alive(identity):
    try:
        return abs(psutil.Process(identity["pid"]).create_time() - identity["process_birth"]) <= 0.001
    except psutil.NoSuchProcess:
        return False


def choose_port():
    for port in (8765, 8766, 8767):
        with socket.socket() as probe:
            try:
                if os.name == "nt":
                    probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                probe.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No authorized app loopback port is free")


def start(args):
    runtime = runtime_path(args.runtime_dir)
    owner = read_owner(runtime)
    if observed_process(owner):
        print(json.dumps({"state": "ALREADY_RUNNING", "url": owner["url"], "identity": owner}))
        return 0
    if any(identity_alive(row) for row in previously_observed(runtime, owner)):
        raise RuntimeError("An earlier owned descendant remains live; reconcile its identity before starting")
    deadline = None
    if args.deadline:
        deadline = datetime.fromisoformat(args.deadline.replace("Z", "+00:00"))
        if deadline.tzinfo is None or deadline <= datetime.now(timezone.utc):
            raise ValueError("deadline must be a future time with explicit timezone")
    port = choose_port()
    nonce = uuid.uuid4().hex
    for directory in (runtime / "control", runtime / "logs", runtime / "tmp"):
        directory.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(SCRIPT), "_serve", "--runtime-dir", str(runtime), "--port", str(port), "--nonce", nonce]
    if deadline:
        command += ["--deadline", deadline.isoformat()]
    # The app receives a minimal environment, not the invoking shell's tokens.
    environment = {k: v for k, v in os.environ.items() if k.upper() in {
        "SYSTEMROOT", "WINDIR", "COMSPEC", "SYSTEMDRIVE", "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS"
    }}
    environment.update({"PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ.get("SYSTEMROOT", "C:\\Windows") + "\\System32",
                        "PYTHONPATH": str(ROOT / "labs/ip01"), "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1",
                        "HAVEN_RUNTIME_DIR": str(runtime), "HAVEN_ROUTE": "deterministic",
                        "TEMP": str(runtime / "tmp"), "TMP": str(runtime / "tmp")})
    logfile = runtime / "logs" / f"app-{nonce}.log"
    with logfile.open("wb") as output:
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                                   stdout=output, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    owned = {"kind": "IP01_APP", "nonce": nonce, "pid": process.pid,
             "process_birth": psutil.Process(process.pid).create_time(), "boot_time": psutil.boot_time(),
             "started_at": utcnow(), "url": f"http://127.0.0.1:{port}", "port": port,
             "deadline": deadline.isoformat() if deadline else None,
             "log": str(logfile.relative_to(runtime)), "runtime": str(runtime)}
    atomic_json(runtime / "control/app-owner.json", owned)
    expires = time.monotonic() + 20
    # No proxy, redirects or remote origin are needed for this local probe.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.monotonic() < expires:
        if process.poll() is not None:
            print(json.dumps({"state": "START_FAILED", "exit_code": process.returncode, "log": str(logfile)}))
            return 1
        try:
            with opener.open(owned["url"] + "/healthz", timeout=0.5) as response:
                if response.status == 200:
                    owned["observed_descendants"] = children(psutil.Process(process.pid))
                    atomic_json(runtime / "control/app-owner.json", owned)
                    record_observation(runtime, {"at": utcnow(), "event": "APP_STARTED", "identity": owned})
                    print(json.dumps({"state": "RUNNING", "url": owned["url"], "identity": owned}))
                    return 0
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.15)
    print(json.dumps({"state": "START_UNKNOWN", "identity": owned, "next": "inspect status and log; do not launch a duplicate"}))
    return 2


def stop(args):
    runtime = runtime_path(args.runtime_dir)
    owner = read_owner(runtime)
    process = observed_process(owner)
    before = previously_observed(runtime, owner)
    if process:
        before.extend(children(process))
    before = list({(row["pid"], row["process_birth"]): row for row in before}.values())
    expires = time.monotonic() + 20
    if process:
        atomic_json(runtime / "control/stop-request.json", {"nonce": owner["nonce"], "requested_at": utcnow()})
        try:
            process.wait(timeout=20)
        except psutil.TimeoutExpired:
            receipt = {"state": "UNKNOWN", "reason": "graceful stop not observed before fixed20second target", "identity": owner,
                       "observed_at": utcnow(), "descendants_before": before}
            atomic_json(runtime / "control/app-stop-observation.json", receipt)
            record_observation(runtime, receipt)
            print(json.dumps(receipt))
            return 2
    residual = [child for child in before if identity_alive(child)]
    while residual and time.monotonic() < expires:
        time.sleep(0.05)
        residual = [child for child in before if identity_alive(child)]
    receipt = {"state": "UNKNOWN" if residual else "STOP_CONFIRMED" if owner else "NOT_STARTED",
               "scope": "Exact app identity and descendants observed before request; separate backend not covered",
               "observed_at": utcnow(), "identity": owner, "descendants_before": before, "residual": residual}
    atomic_json(runtime / "control/app-stop-observation.json", receipt)
    record_observation(runtime, receipt)
    print(json.dumps(receipt))
    return 2 if residual else 0


async def serve(args):
    import uvicorn
    runtime = runtime_path(args.runtime_dir)
    config = uvicorn.Config("haven.app:create_app", factory=True, host="127.0.0.1", port=args.port, workers=1, access_log=False)
    server = uvicorn.Server(config)

    async def watch():
        while not server.should_exit:
            request = runtime / "control/stop-request.json"
            try:
                if request.exists() and json.loads(request.read_text(encoding="utf-8")).get("nonce") == args.nonce:
                    server.should_exit = True
            except (OSError, ValueError):
                pass
            if args.deadline and datetime.now(timezone.utc) >= datetime.fromisoformat(args.deadline.replace("Z", "+00:00")):
                server.should_exit = True
            await asyncio.sleep(0.2)

    watcher = asyncio.create_task(watch())
    try:
        await server.serve()
    finally:
        watcher.cancel()
        try:
            await watcher
        except asyncio.CancelledError:
            pass
        atomic_json(runtime / "control/app-shutdown-report.json", {"nonce": args.nonce, "pid": os.getpid(),
                    "at": utcnow(), "state": "UVICORN_SHUTDOWN_RETURNED", "termination": "Requires independent process observation"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "status", "stop", "_serve"])
    parser.add_argument("--runtime-dir", default=str(PRIVATE))
    parser.add_argument("--deadline")
    parser.add_argument("--port", type=int, choices=[8765, 8766, 8767])
    parser.add_argument("--nonce")
    args = parser.parse_args()
    if args.action == "start":
        return start(args)
    if args.action == "stop":
        return stop(args)
    if args.action == "_serve":
        if not args.nonce or not args.port:
            parser.error("internal serving requires an owned nonce and allowed port")
        asyncio.run(serve(args))
        return 0
    owner = read_owner(runtime_path(args.runtime_dir))
    process = observed_process(owner)
    descendants = previously_observed(runtime_path(args.runtime_dir), owner)
    if process:
        descendants.extend(children(process))
    descendants = list({(row["pid"], row["process_birth"]): row for row in descendants if identity_alive(row)}.values())
    print(json.dumps({"state": "RUNNING" if process else "UNKNOWN" if descendants else "STOPPED" if owner else "NOT_STARTED", "identity": owner,
                      "descendants": descendants}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, psutil.AccessDenied) as error:
        print(json.dumps({"state": "ERROR", "reason": str(error)}), file=sys.stderr)
        raise SystemExit(2)
