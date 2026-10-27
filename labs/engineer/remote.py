"""Remote tool hosts: run Haven's executor and worker on an enrolled node.

Transport is the owner's existing SSH trust: the node's alias, key auth,
BatchMode, StrictHostKeyChecking, and the host-key fingerprint recorded at
enrollment, re-checked before every connection. No new listener, daemon,
port or credential is added on either side.

  stage(node)                 ship this runtime (content-hashed, verified on arrival)
  push_workspace(node, repo)  snapshot a local git commit onto the node, on a task branch
  fetch_back(...)             replay the node's commits onto that commit here, as a new branch
  RemoteExecutor(...)         Executor-shaped MCP client: the model runs here, every
                              tool call is decided, sandboxed and receipted *there*
  mcp_command(...)            the same executor as an MCP server command for Claude Code / Codex

Receipts are signed by the tool host's ledger. pull_task() copies that ledger
and its key into the local task directory so the console, answer checks and
ledger verification work on the Mac exactly as for local tasks.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import pathlib
import re
import shlex
import subprocess
import tarfile
import tempfile
import threading
import time

import fleet

HERE = pathlib.Path(__file__).resolve().parent
RUNTIME_FILES = ("executor.py", "policy.py", "sandbox.py", "ledger.py", "session.py", "registry.py",
                 "runtime.py", "skills.py", "mcp_server.py", "worker.py")
REMOTE_RT = ".local/share/haven-engineer/rt"
REMOTE_WS = ".local/share/haven-workspaces"
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


class RemoteError(RuntimeError):
    pass


def ssh_argv(node):
    """SSH prefix for an enrolled node, after re-checking its pinned host key."""
    if node.get("kind") != "ssh":
        raise RemoteError(f"{node.get('name')} is not an SSH node")
    pin = fleet.host_fingerprint(node["ssh"])
    if not pin or pin["fingerprint"] != node.get("host_fingerprint"):
        raise RemoteError(f"{node['name']}: host key does not match the enrolled fingerprint; refusing")
    return fleet.SSH + [node["ssh"]]


def run(node, command, *, stdin=None, timeout=120, text=True):
    r = subprocess.run(ssh_argv(node) + [command], input=stdin, capture_output=True, text=text, timeout=timeout)
    return r


def runtime_digest():
    h = hashlib.sha256()
    for name in RUNTIME_FILES:
        h.update(name.encode() + b"\0" + (HERE / name).read_bytes() + b"\0")
    return h.hexdigest()


_VERIFY = ("import hashlib,sys\nh=hashlib.sha256()\nfor n in sys.argv[1:]:\n"
           "    h.update(n.encode()+b'\\0'+open(n,'rb').read()+b'\\0')\nprint(h.hexdigest())")


def stage(node):
    """Install this exact runtime on the node (idempotent). Returns its remote directory."""
    digest = runtime_digest()
    rdir = f"{REMOTE_RT}/{digest[:16]}"
    names = " ".join(RUNTIME_FILES)
    check = f"cd ~/{rdir} 2>/dev/null && python3 -c {shlex.quote(_VERIFY)} {names}"
    r = run(node, check, timeout=30)
    if r.returncode == 0 and r.stdout.strip() == digest:
        return "~/" + rdir
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name in RUNTIME_FILES:
            data = (HERE / name).read_bytes()
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o500 if name.endswith(".py") else 0o400, 0
            tar.addfile(info, io.BytesIO(data))
    install = (f"set -e; umask 077; mkdir -p ~/{REMOTE_RT}; rm -rf ~/{rdir}.new; mkdir ~/{rdir}.new; "
               f"tar -C ~/{rdir}.new -xf -; chmod -R a-w ~/{rdir}.new; rm -rf ~/{rdir}; mv ~/{rdir}.new ~/{rdir}; "
               + check)
    r = subprocess.run(ssh_argv(node) + [install], input=buf.getvalue(), capture_output=True, timeout=60)
    if r.returncode or r.stdout.decode().strip() != digest:
        raise RemoteError(f"runtime staging failed or hash mismatch: {r.stderr.decode()[-300:]}")
    return "~/" + rdir


def push_workspace(node, repo, name, ref="HEAD"):
    """Snapshot `repo` at `ref` onto the node as ~/.local/share/haven-workspaces/<name> on branch haven/<name>.

    A `git archive` snapshot, not the history: large repos move in seconds. The node's first commit is
    the snapshot (`base`); fetch_back replays everything after it onto `head` here.
    """
    if not NAME.fullmatch(name):
        raise RemoteError(f"bad workspace name {name!r}")
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", ref], capture_output=True, text=True,
                          check=True).stdout.strip()
    archive = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", head], capture_output=True,
                             check=True).stdout
    ws = f"{REMOTE_WS}/{name}"
    cmd = (f"set -e; umask 077; mkdir -p ~/{REMOTE_WS}; test ! -e ~/{ws}; mkdir ~/{ws}; cd ~/{ws}; tar -xf -; "
           f"git init -q -b haven/{name}; "  # task branch: commits never land on main unasked
           f"git config user.name 'Haven engineer'; git config user.email 'haven-engineer@localhost'; "
           f"git add -A; git commit -qm 'snapshot of {head[:12]}' --no-verify; echo $(pwd) $(git rev-parse HEAD)")
    r = subprocess.run(ssh_argv(node) + [cmd], input=archive, capture_output=True, timeout=300)
    if r.returncode:
        raise RemoteError(f"workspace push failed: {r.stderr.decode()[-300:]}")
    path, base = r.stdout.decode().split()
    return {"path": path, "head": head, "base": base}


def fetch_back(node, remote_ws, repo, local_branch, source_head, base):
    """Replay the node's commits after `base` onto `source_head` as local branch `local_branch`.

    Returns the branch commit and how many commits came back. The caller's checkout is not touched:
    patches are applied in a throwaway worktree.
    """
    cmd = f"cd {shlex.quote(remote_ws)} && git format-patch --stdout --binary {base}..HEAD"
    r = subprocess.run(ssh_argv(node) + [cmd], capture_output=True, timeout=120)
    if r.returncode:
        raise RemoteError(f"fetch failed: {r.stderr.decode()[-300:]}")
    with tempfile.TemporaryDirectory() as t:
        wt = pathlib.Path(t) / "wt"
        subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", "--detach", str(wt), source_head],
                       check=True, capture_output=True)
        try:
            if r.stdout.strip():
                am = subprocess.run(["git", "-C", str(wt), "-c", "core.hooksPath=/dev/null", "am", "-q",
                                     "--committer-date-is-author-date"], input=r.stdout, capture_output=True)
                if am.returncode:
                    raise RemoteError(f"patches did not apply: {am.stderr.decode()[-300:]}")
            commit = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"], capture_output=True, text=True,
                                    check=True).stdout.strip()
            subprocess.run(["git", "-C", str(repo), "branch", "-f", local_branch, commit], check=True,
                           capture_output=True)
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)], capture_output=True)
    count = subprocess.run(["git", "-C", str(repo), "rev-list", "--count", f"{source_head}..{commit}"],
                           capture_output=True, text=True).stdout.strip()
    return {"commit": commit, "new_commits": int(count or 0)}


def mcp_command(node, rt, workspace, mode, agent, task_id, network, meta=None):
    """argv for an MCP server whose tools execute on the node (for Claude Code / Codex configs)."""
    create = json.dumps({"agent_kind": "remote", "controller": os.uname().nodename.split(".")[0], **(meta or {})})
    remote = (f"python3 -I {rt}/mcp_server.py --workspace {shlex.quote(workspace)} --mode {mode} "
              f"--agent {shlex.quote(agent)} --network {'on' if network else 'off'} "
              f"--task-id {shlex.quote(task_id)} --create-task {shlex.quote(create)}")
    return ssh_argv(node) + [remote]


def pull_task(node, task_id, local_dir):
    """Copy the node's ledger, key and events for task_id into local_dir. Returns file names copied."""
    if not NAME.fullmatch(task_id):
        raise RemoteError("bad task id")
    files = ("ledger.jsonl", "ledger.key", "events.jsonl", "meta.json")
    cmd = (f"cd ~/.local/state/haven-engineer/tasks/{task_id} && tar -cf - "
           + " ".join(f"$(test -e {f} && echo {f})" for f in files))
    r = subprocess.run(ssh_argv(node) + [cmd], capture_output=True, timeout=60)
    if r.returncode:
        raise RemoteError(f"pull failed: {r.stderr.decode()[-300:]}")
    local_dir = pathlib.Path(local_dir)
    got = []
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tar:
        for m in tar.getmembers():
            if m.name not in files or not m.isfile():
                continue
            target = {"events.jsonl": "remote-events.jsonl", "meta.json": "remote-meta.json"}.get(m.name, m.name)
            data = tar.extractfile(m).read()
            fd = os.open(local_dir / target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            got.append(target)
    return got


class ApprovalRelay(threading.Thread):
    """Mirror the tool host's pending approvals into the local console and send back the owner's answers.

    The node's executor waits on <node state>/approvals/<rid>.decision.json; the owner decides in the
    Mac console, which writes the same file name locally. Only the owner (console) writes decisions.
    """

    def __init__(self, node, state, interval=2.5):
        super().__init__(daemon=True)
        self.node, self.dir, self.interval = node, pathlib.Path(state) / "approvals", interval
        self.stop = threading.Event()
        self.mirrored = set()

    def run(self):
        self.dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        while not self.stop.wait(self.interval):
            try:
                self.tick()
            except Exception:  # noqa: BLE001 - a dropped poll is retried; the node times the ask out
                pass

    def tick(self):
        r = run(self.node, "cd ~/.local/state/haven-engineer/approvals 2>/dev/null && "
                           "for f in R-*.json; do case $f in *.decision.json) ;; *) [ -e \"$f\" ] && cat \"$f\" "
                           "&& echo; esac; done", timeout=20)
        pending = {}
        for line in r.stdout.splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict) and RECEIPT.fullmatch(str(rec.get("receipt", ""))):
                pending[rec["receipt"]] = rec
        for rid, rec in pending.items():
            local = self.dir / f"{rid}.json"
            if rid not in self.mirrored:
                _private_write(local, json.dumps({**rec, "tool_host": self.node["name"]}))
                self.mirrored.add(rid)
            answer = self.dir / f"{rid}.decision.json"
            if answer.exists():
                decision = json.loads(answer.read_text())
                body = json.dumps({"decision": "approve" if decision.get("decision") == "approve" else "reject",
                                   "relayed_from": os.uname().nodename.split(".")[0], "t": time.time()})
                w = run(self.node, f"umask 077; cat > ~/.local/state/haven-engineer/approvals/{rid}.decision.json",
                        stdin=body, timeout=20)
                if w.returncode == 0:
                    answer.unlink(missing_ok=True)
                    local.unlink(missing_ok=True)
        for rid in list(self.mirrored - set(pending)):  # answered, timed out or cancelled on the node
            (self.dir / f"{rid}.json").unlink(missing_ok=True)
            self.mirrored.discard(rid)


RECEIPT = re.compile(r"R-[0-9a-f]{10}")


def _private_write(path, data):
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(data)
    os.replace(tmp, path)


class _MirrorLedger:
    """Ledger view for the loop: refreshed from the tool host on demand, verified locally."""

    def __init__(self, rex):
        self.rex = rex

    def _fresh(self):
        from ledger import Ledger
        pull_task(self.rex.node, self.rex.task_id, self.rex.local_dir)
        path = pathlib.Path(self.rex.local_dir) / "ledger.jsonl"
        return Ledger(path, key=(path.with_suffix(".key")).read_bytes(), session=self.rex.task_id)

    def __getattr__(self, name):
        return getattr(self._fresh(), name)


class RemoteExecutor:
    """Executor-shaped client for loop.Agent; the real Executor runs on the node."""

    def __init__(self, node, workspace, scope, agent, task_id, local_dir, *, rt=None, cancel=None, meta=None):
        self.node, self.scope, self.agent, self.task_id, self.local_dir = node, scope, agent, task_id, local_dir
        self.root = pathlib.PurePosixPath(workspace)
        self.cancel = cancel or threading.Event()
        self.rt = rt or stage(node)
        argv = mcp_command(node, self.rt, workspace, scope.mode, agent, task_id, scope.network, meta)
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, bufsize=1)
        self._id = 0
        self._lock = threading.Lock()
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "haven-remote", "version": "1"}})
        self._schemas = {t["name"]: {"description": t["description"], "parameters": t["inputSchema"]}
                         for t in self._rpc("tools/list", {})["tools"]}
        self.ledger = _MirrorLedger(self)
        self.sandbox = {"backend": f"remote:{node['name']}", "available": True}

    def _rpc(self, method, params, timeout=None):
        with self._lock:
            self._id += 1
            self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self._id, "method": method,
                                              "params": params}) + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
        if not line:
            raise RemoteError(f"tool host closed the connection: {self.proc.stderr.read()[-300:]}")
        msg = json.loads(line)
        if "error" in msg:
            raise RemoteError(msg["error"].get("message"))
        return msg["result"]

    def tool_schemas(self, names=None):
        return {n: s for n, s in self._schemas.items() if names is None or n in names}

    def call(self, tool, args):
        try:
            res = self._rpc("tools/call", {"name": tool, "arguments": args or {}})
        except (RemoteError, OSError, ValueError) as e:
            return {"status": "unknown", "text": f"[remote tool host error] {e}"}
        text = "".join(c.get("text", "") for c in res.get("content", []))
        m = re.match(r"\[receipt (R-[0-9a-f]{10}) \| (\w+)", text)
        out = {"text": text, "status": m[2] if m else ("invalid" if text.startswith("[invalid") else "unknown")}
        if m:
            out["receipt"] = m[1]
        ec = re.search(r"\| exit (-?\d+)", text.split("\n", 1)[0])
        if ec:
            out["exit_code"] = int(ec[1])
        return out

    def stop_all(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            self.proc.kill()


def node_by_name(name):
    node = next((n for n in fleet.load()["nodes"] if n["name"] == name), None)
    if node is None:
        raise RemoteError(f"{name} is not an enrolled node")
    return node


def run_remote_task(node_name, repo, agent_id, mode, prompt, *, max_steps=30, network=False, ref="HEAD",
                    timeout_s=1800, on_event=None, gate=None):
    """One engineering task: the model runs here, every tool runs on `node_name`, commits come back.

    The local repo is never modified except for one new branch `<node>/<task id>` holding the node's
    commits. `gate` (trust.Gate) must allow the node for the "tools" role.
    """
    import uuid

    import runtime
    from ledger import Ledger
    from session import TaskSession

    node = node_by_name(node_name)
    if gate is not None:
        decision = gate.decide(node, "tools")
        if not decision["ok"]:
            raise RemoteError(f"trust gate refused {node_name}: {decision['reason']}")
    else:
        decision = None
    agent_cfg = runtime.agent_by_id(agent_id)
    repo = os.path.realpath(repo)
    rt = stage(node)
    tid = time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    ws = push_workspace(node, repo, f"{pathlib.Path(repo).name[:40]}-{tid}", ref)
    sess = TaskSession(tid=tid, agent=agent_id, agent_kind=agent_cfg.get("kind", "local"), workspace=ws["path"],
                       workspace_name=pathlib.Path(ws["path"]).name, mode=mode, network=network,
                       inference_host=agent_cfg.get("inference_host"), tool_host=node["name"],
                       tool_host_fingerprint=node["host_fingerprint"], egress=agent_cfg.get("egress", "LOCAL"),
                       prompt=prompt, max_steps=max_steps, runner_pid=os.getpid(), source_repo=str(repo),
                       source_head=ws["head"], runtime=rt, trust=decision)
    if on_event:
        orig = sess.emit
        sess.emit = lambda e: (orig(e), on_event(e))
    relay = ApprovalRelay(node, sess.state)
    relay.start()
    remote_meta = {"controller_task": tid, "source_head": ws["head"], "inference_host": agent_cfg.get("inference_host")}
    try:
        if agent_cfg.get("kind") == "cli":
            import hosted
            cwd = pathlib.Path.home() / ".cache/haven-engineer/remote-cwd" / tid  # nothing for the CLI to read
            cwd.mkdir(parents=True, mode=0o700)
            record = hosted.run(agent_cfg, sess, ws["path"], mode, prompt, network=network,
                                max_turns=max_steps + 10, timeout_s=timeout_s, cwd=str(cwd),
                                mcp=mcp_command(node, rt, ws["path"], mode, agent_id, tid, network, remote_meta),
                                before_finish=lambda: pull_task(node, tid, sess.dir))
        else:
            import policy
            from loop import Agent
            rex = RemoteExecutor(node, ws["path"], policy.Scope(mode=mode, network=network), agent_id, tid,
                                 sess.dir, rt=rt, cancel=sess.cancel, meta=remote_meta)
            opts = {k: agent_cfg[k] for k in ("thinking", "max_tokens", "temperature", "ctx_chars") if k in agent_cfg}
            agent = Agent(rex, base_url=agent_cfg["base_url"], model=agent_cfg["model"],
                          api_key=runtime.read_key(agent_cfg), label=agent_id, max_steps=max_steps,
                          on_event=sess.emit, tools=[t for t in rex.tool_schemas() if t != "delegate"], **opts)
            try:
                record = agent.run(prompt)
            finally:
                rex.stop_all()
            pull_task(node, tid, sess.dir)
    finally:
        relay.stop.set()
    led = Ledger(sess.ledger_path, key=(sess.dir / "ledger.key").read_bytes(), session=tid)
    record.update({"task_id": tid, "tool_host": node["name"], "remote_workspace": ws["path"],
                   "source_head": ws["head"], "runtime": rt, "ledger_verified": led.verify(),
                   "receipts": [{k: r.get(k) for k in ("receipt", "tool", "status", "summary", "exit_code", "class",
                                                       "decided_by", "duration_s", "changed_paths", "commit")}
                                for r in led.receipts()]})
    try:
        branch = f"{node['name']}/{tid}"
        back = fetch_back(node, ws["path"], repo, branch, ws["head"], ws["base"])
        record.update({"fetched_branch": branch, "fetched_commit": back["commit"], "new_commits": back["new_commits"]})
    except (RemoteError, subprocess.CalledProcessError) as e:
        record["fetch_error"] = str(e)[:300]
    sess.finish(record)
    return record
