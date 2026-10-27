#!/usr/bin/env python3
"""Haven engineering console: one private browser view of agents, actions and machines.

  console.py serve [--port 8895]     # prints the private link once

Loopback only, bearer token (0600 file, passed in the URL fragment so it never
reaches logs), Host-header check against DNS rebinding. Tasks run in this
process but their state lives in the shared task directory, so a browser can
disconnect and reconnect, and tasks started by MCP clients (Claude Code,
Codex) appear here too. The console never edits files itself: it starts
agents, answers approvals, cancels tasks, and shows git state read-only.
"""
from __future__ import annotations

import argparse
import hmac
import http.server
import json
import mimetypes
import os
import pathlib
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fleet  # noqa: E402
import policy  # noqa: E402
import runtime  # noqa: E402
import sandbox  # noqa: E402
import session  # noqa: E402
from ledger import Ledger  # noqa: E402

STATIC = HERE / "console"
WORKSPACES = runtime.CONFIG / "workspaces.json"
WORKSPACE_ROOT = pathlib.Path.home() / ".local/share/haven-workspaces"
FIXTURES = HERE / "bench" / "tasks"
RESEARCH = [HERE / "research", session.STATE / "research"]
MODE_HELP = {
    "observe": "Read-only discovery. Writes refused; only read-only commands, in a read-only sandbox.",
    "engineer": "Edits and development commands in the workspace. Pushes, history rewrites and destructive "
                "commands wait for your approval.",
    "autonomous": "Everything this workspace scope allows, without approval, inside the OS sandbox. "
                  "Admin, credential and out-of-scope actions stay refused.",
}


def token_path():
    return session.STATE / "console-token"


def load_token():
    p = token_path()
    session.STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not p.exists():
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_urlsafe(32))
    return p.read_text().strip()


def workspaces():
    items = json.loads(WORKSPACES.read_text()) if WORKSPACES.exists() else []
    return [w for w in items if pathlib.Path(w["path"]).is_dir()]


def save_workspaces(items):
    runtime.CONFIG.mkdir(parents=True, exist_ok=True, mode=0o700)
    WORKSPACES.write_text(json.dumps(items, indent=2))
    os.chmod(WORKSPACES, 0o600)


def workspace_path(name_or_path):
    for w in workspaces():
        if name_or_path in (w["name"], w["path"]):
            return pathlib.Path(w["path"])
    raise KeyError(f"unknown workspace {name_or_path}")


def git(path, *argv):
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
    r = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", *argv], cwd=path,
                       capture_output=True, text=True, timeout=30, env=env)
    return r.stdout if r.returncode == 0 else r.stderr


class Console:
    def __init__(self):
        self.token = load_token()
        self.threads = {}
        self._mark_interrupted()

    def _mark_interrupted(self):
        """A task whose runner is gone is not running, whatever its meta says."""
        for m in session.list_tasks(limit=500):
            if m.get("status") != "running":
                continue
            pid = m.get("runner_pid")
            if pid is None:  # MCP sessions and early tasks: use the last process that wrote an event
                evs, _ = session.read_events(m["task_id"])
                pids = {e.get("pid") for e in evs[-20:] if e.get("pid")}
                alive = any(_alive(p) for p in pids)
                stale = time.time() - (evs[-1].get("t", m.get("created", 0)) if evs else m.get("created", 0)) > 1800
                if alive or not stale:
                    continue
            elif _alive(pid):
                continue
            session.TaskSession(tid=m["task_id"]).update_meta(
                status="interrupted", note="runner process ended before the task finished")

    # -- tasks -------------------------------------------------------------------

    def start_task(self, body):
        agent = runtime.agent_by_id(body["agent"])
        ws = workspace_path(body["workspace"])
        mode = body.get("mode", "engineer")
        if mode not in policy.MODES:
            raise ValueError("unknown mode")
        if agent.get("kind") == "cli" and body.get("egress_ack") != "HOSTED_SUBSCRIPTION":
            raise PermissionError("hosted agents need explicit acknowledgement that the task leaves this house")
        prompt = str(body.get("prompt") or "").strip()
        if not prompt:
            raise ValueError("empty task")
        network = bool(runtime.owner_scope().get("network")) if body.get("network", "owner") == "owner" \
            else body.get("network") == "on"
        sess = session.TaskSession(agent=agent["id"], agent_kind=agent.get("kind", "local"), workspace=str(ws),
                                   workspace_name=ws.name, mode=mode, network=network,
                                   inference_host=agent.get("inference_host"),
                                   tool_host=os.uname().nodename.split(".")[0], egress=agent.get("egress", "LOCAL"),
                                   prompt=prompt, max_steps=int(body.get("max_steps") or 30), depth=0,
                                   parent_id=None, runner_pid=os.getpid(), started_by="owner@console")

        def go():
            try:
                runtime.run_task(ws, agent, mode, prompt, session=sess, network=network,
                                 max_steps=int(body.get("max_steps") or 30))
            except Exception as e:  # noqa: BLE001 - recorded on the task
                sess.emit({"type": "task_finished", "status": "error", "error": f"{type(e).__name__}: {e}"})
                sess.finish({"status": "error", "error": str(e)})

        t = threading.Thread(target=go, daemon=True, name=f"task-{sess.tid}")
        self.threads[sess.tid] = t
        t.start()
        return {"task_id": sess.tid}

    def task_detail(self, tid):
        if not re.fullmatch(r"[0-9T]+-[0-9a-f]{6}", tid):
            raise KeyError("bad task id")
        s = session.TaskSession(tid=tid)
        meta = s.meta()
        rec_path = s.dir / "record.json"
        record = json.loads(rec_path.read_text()) if rec_path.exists() else None
        receipts, verified = [], None
        if s.ledger_path.exists():
            led = Ledger(s.ledger_path, session=tid)
            receipts, verified = led.receipts(), led.verify()
        children = [m for m in session.list_tasks(limit=1000) if m.get("parent_id") == tid]
        return {"meta": meta, "record": record, "receipts": receipts, "ledger_verified": verified,
                "children": children}

    def events(self, tid, offset, wait_s=15):
        deadline = time.monotonic() + wait_s
        while True:
            evs, new = session.read_events(tid, offset)
            meta = session.TaskSession(tid=tid).meta()
            if evs or meta.get("status") != "running" or time.monotonic() > deadline:
                return {"events": evs, "offset": new, "status": meta.get("status")}
            time.sleep(0.4)

    # -- research ------------------------------------------------------------------

    def research(self):
        items = []
        for root in RESEARCH:
            for p in sorted(root.glob("*.json")) if root.exists() else []:
                try:
                    d = json.loads(p.read_text())
                    d.setdefault("id", p.stem)
                    d["_source"] = "repository" if root == RESEARCH[0] else "private state"
                    items.append(d)
                except ValueError:
                    continue
        return items

    def skills(self):
        try:
            import skills
            return skills.list_skills()
        except Exception as e:  # noqa: BLE001
            return {"error": str(e), "skills": []}


def _alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError):
        return False


def _scheduler_view():
    """Scheduled jobs and each node's current trust decision, read from files only."""
    import scheduler
    import trust
    gate = trust.Gate()
    nodes = {n["name"]: n for n in fleet.load()["nodes"]}
    jobs = scheduler.Store().jobs()[-40:]
    keep = ("id", "state", "node", "receipt", "created", "finished_at", "waiting", "revoked", "node_problem")
    return {"trust": {name: gate.decide(n, "tools") for name, n in nodes.items()},
            "jobs": [{**{k: j.get(k) for k in keep}, "command": j["spec"]["command"][:160],
                      "exit_code": (j.get("worker") or {}).get("exit_code"),
                      "sandbox": (j.get("worker") or {}).get("sandbox")} for j in reversed(jobs)]}


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "HavenConsole/0.1"
    console: Console = None
    port = 0

    def log_message(self, fmt, *args):  # keep tokens and prompts out of logs
        sys.stderr.write(f"{time.strftime('%H:%M:%S')} {self.command} {self.path.split('?')[0]}\n")

    def _host_ok(self):
        host = (self.headers.get("Host") or "").lower()
        return host in (f"127.0.0.1:{self.port}", f"localhost:{self.port}", f"[::1]:{self.port}")

    def _auth(self):
        got = (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
        return bool(got) and hmac.compare_digest(got, self.console.token)

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                         "img-src 'self' data:; connect-src 'self'; frame-ancestors 'self'")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 2_000_000:
            raise ValueError("request too large")
        if n and "application/json" not in (self.headers.get("Content-Type") or ""):
            raise ValueError("JSON body required")
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")

    def _route(self, method):
        if not self._host_ok():
            return self._send(421, {"error": "wrong host"})
        url = urllib.parse.urlsplit(self.path)
        q = dict(urllib.parse.parse_qsl(url.query))
        path = url.path
        if method == "GET" and (path == "/" or path.startswith("/static/")):
            name = "index.html" if path == "/" else path[len("/static/"):]
            f = (STATIC / name).resolve()
            if STATIC.resolve() not in f.parents or not f.is_file():
                return self._send(404, {"error": "not found"})
            return self._send(200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "application/octet-stream")
        if not self._auth():
            return self._send(401, {"error": "unauthorized"})
        c = self.console
        try:
            body = self._body() if method == "POST" else {}
            if method == "GET" and path == "/api/state":
                return self._send(200, {
                    "host": os.uname().nodename.split(".")[0], "sandbox": sandbox.describe(),
                    "scope": runtime.owner_scope(), "modes": [{"id": m, "help": MODE_HELP[m]} for m in policy.MODES],
                    "agents": [{k: a.get(k) for k in ("id", "kind", "label", "inference_host", "egress", "model")}
                               for a in runtime.load_agents()],
                    "workspaces": workspaces(),
                    "fixtures": sorted(p.name for p in FIXTURES.iterdir() if (p / "repo").is_dir())})
            if method == "GET" and path == "/api/fleet":
                obs = fleet.observe()
                tasks = session.list_tasks(limit=300)
                running = [t for t in tasks if t.get("status") == "running"]
                return self._send(200, {**obs, "running_tasks": running, **_scheduler_view()})
            if method == "POST" and path == "/api/fleet/enroll":
                return self._send(200, fleet.enroll(body["name"], body["ssh"], body.get("roles") or ["tools"]))
            if method == "POST" and path == "/api/fleet/remove":
                return self._send(200, {"removed": fleet.remove(body["name"])})
            if method == "GET" and path == "/api/tasks":
                c._mark_interrupted()
                return self._send(200, session.list_tasks(limit=int(q.get("limit", 200))))
            if method == "POST" and path == "/api/tasks":
                return self._send(200, c.start_task(body))
            m = re.fullmatch(r"/api/tasks/([0-9T]+-[0-9a-f]{6})(/events|/cancel)?", path)
            if m and method == "GET" and not m[2]:
                return self._send(200, c.task_detail(m[1]))
            if m and method == "GET" and m[2] == "/events":
                return self._send(200, c.events(m[1], int(q.get("offset", 0))))
            if m and method == "POST" and m[2] == "/cancel":
                session.TaskSession(tid=m[1]).request_cancel()
                return self._send(200, {"cancelled": m[1]})
            if method == "GET" and path == "/api/approvals":
                return self._send(200, session.pending_approvals())
            m = re.fullmatch(r"/api/approvals/(R-[0-9a-f]{10})", path)
            if m and method == "POST":
                decision = body.get("decision")
                if decision not in ("approve", "reject"):
                    raise ValueError("decision must be approve or reject")
                return self._send(200, {"recorded": session.decide_approval(m[1], decision, "owner@console")})
            if method == "POST" and path == "/api/workspaces":
                return self._send(200, add_workspace(body))
            if method == "GET" and path == "/api/workspace/git":
                ws = workspace_path(q["ws"])
                return self._send(200, {"status": git(ws, "status", "--short", "--branch"),
                                        "diff": git(ws, "diff", "--no-color", "--no-ext-diff")[:400_000],
                                        "log": git(ws, "log", "-15", "--format=%h %an · %s")})
            if method == "GET" and path == "/api/workspace/tree":
                ws = workspace_path(q["ws"])
                return self._send(200, tree(ws))
            if method == "GET" and path == "/api/workspace/file":
                ws = workspace_path(q["ws"])
                f = (ws / q["file"]).resolve()
                if ws.resolve() not in f.parents or not f.is_file():
                    raise KeyError("no such file")
                return self._send(200, {"file": q["file"], "text": f.read_bytes()[:300_000].decode(errors="replace")})
            if method == "GET" and path == "/api/research":
                return self._send(200, {"research": c.research(), "skills": c.skills()})
            return self._send(404, {"error": "not found"})
        except PermissionError as e:
            return self._send(403, {"error": str(e)})
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            return self._send(400, {"error": str(e)})
        except SystemExit as e:
            return self._send(400, {"error": str(e)})


def add_workspace(body):
    items = json.loads(WORKSPACES.read_text()) if WORKSPACES.exists() else []
    if body.get("fixture"):
        src = FIXTURES / body["fixture"] / "repo"
        if not src.is_dir() or "/" in body["fixture"]:
            raise KeyError("unknown fixture")
        WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
        dest = WORKSPACE_ROOT / f"{body['fixture']}-{time.strftime('%m%d-%H%M%S')}"
        shutil.copytree(src, dest)
        env = {**{k: os.environ[k] for k in ("PATH", "HOME") if k in os.environ},
               "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@haven.invalid",
               "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@haven.invalid"}
        for argv in (["git", "init", "-q", "-b", "work"], ["git", "add", "-A"], ["git", "commit", "-qm", "fixture"]):
            subprocess.run(argv, cwd=dest, env=env, check=True, capture_output=True)
        item = {"name": dest.name, "path": str(dest), "kind": "disposable", "created": time.time()}
    else:
        p = pathlib.Path(os.path.expanduser(body["path"])).resolve()
        if not p.is_dir():
            raise KeyError("not a directory")
        home = pathlib.Path.home().resolve()
        for s in sandbox.SENSITIVE_HOME:
            sp = (home / s).resolve()
            if p == sp or sp in p.parents:
                raise PermissionError("that directory holds credentials or private state")
        item = {"name": body.get("name") or p.name, "path": str(p), "kind": "existing", "created": time.time()}
    items = [w for w in items if w["path"] != item["path"]] + [item]
    save_workspaces(items)
    return item


def tree(ws, limit=600):
    out = []
    for dirpath, dirnames, filenames in os.walk(ws):
        dirnames[:] = sorted(d for d in dirnames if d not in (".git", "node_modules", "__pycache__", ".venv"))
        rel = pathlib.Path(dirpath).relative_to(ws)
        for f in sorted(filenames):
            out.append(str(rel / f) if str(rel) != "." else f)
            if len(out) >= limit:
                return out
    return out


def serve(port):
    console = Console()
    Handler.console, Handler.port = console, port
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True
    link = f"http://127.0.0.1:{port}/#token={console.token}"
    link_file = session.STATE / "console-url"
    link_file.write_text(link)
    os.chmod(link_file, 0o600)
    print(f"Haven console on http://127.0.0.1:{port}/ (private link written to {link_file})", flush=True)
    httpd.serve_forever()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--port", type=int, default=8895)
    args = ap.parse_args(argv)
    serve(args.port)


if __name__ == "__main__":
    main()
