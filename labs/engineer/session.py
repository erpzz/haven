"""Task sessions on disk: the shared bus between agents, executors and the console.

  <state>/tasks/<tid>/meta.json      who, where, mode, egress class (written at start)
  <state>/tasks/<tid>/events.jsonl   streamed actions, model turns, output chunks
  <state>/tasks/<tid>/ledger.jsonl   signed receipts (ledger.py)
  <state>/tasks/<tid>/record.json    final result
  <state>/tasks/<tid>/cancel         owner cancel request (any process may honour it)
  <state>/approvals/<rid>.json       pending approval; <rid>.decision.json is the owner's answer

The state directory is 0700, outside every workspace, and denied to the
command sandbox, so an agent cannot forge an approval or a cancel. Any
executor process (the in-process loop, an MCP server started by Claude Code
or Codex) uses the same files, and one console shows and approves them all.
"""
from __future__ import annotations

import fcntl
import json
import os
import pathlib
import threading
import time
import uuid

STATE = pathlib.Path(os.environ.get("HAVEN_ENGINEER_STATE", pathlib.Path.home() / ".local/state/haven-engineer"))


def _write_private(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(data)
    os.replace(tmp, path)


class TaskSession:
    def __init__(self, tid=None, state=None, **meta):
        self.state = pathlib.Path(state or STATE)
        self.tid = tid or time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
        self.dir = self.state / "tasks" / self.tid
        self.dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.state, 0o700)
        self.cancel = threading.Event()
        self._lock = threading.Lock()
        if meta:
            self.write_meta({"task_id": self.tid, "created": time.time(), "status": "running", **meta})
        self._watch = threading.Thread(target=self._watch_cancel, daemon=True)
        self._watch.start()

    @property
    def ledger_path(self):
        return self.dir / "ledger.jsonl"

    def meta(self):
        p = self.dir / "meta.json"
        return json.loads(p.read_text()) if p.exists() else {"task_id": self.tid}

    def write_meta(self, meta):
        _write_private(self.dir / "meta.json", json.dumps(meta, indent=2))

    def update_meta(self, **fields):
        with self._lock:
            m = self.meta()
            m.update(fields)
            self.write_meta(m)

    def emit(self, event):
        """Append one event. Several processes (loop, MCP server, CLI runner) may share a task."""
        line = (json.dumps({"pid": os.getpid(), **event}, default=str) + "\n").encode()
        with self._lock:
            fd = os.open(self.dir / "events.jsonl", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                os.write(fd, line)
            finally:
                os.close(fd)

    def finish(self, record):
        _write_private(self.dir / "record.json", json.dumps(record, indent=2, default=str))
        self.update_meta(status=record.get("status", "finished"), finished=time.time())

    def request_cancel(self):
        (self.dir / "cancel").touch(mode=0o600)
        self.cancel.set()

    def _watch_cancel(self):
        while not self.cancel.is_set():
            if (self.dir / "cancel").exists():
                self.cancel.set()
                return
            time.sleep(0.3)

    # -- approvals --------------------------------------------------------------

    def approver(self, timeout_s=1800):
        approvals = self.state / "approvals"
        approvals.mkdir(exist_ok=True, mode=0o700)
        meta = self.meta()

        def ask(rid, tool, args, decision):
            pending = approvals / f"{rid}.json"
            answer = approvals / f"{rid}.decision.json"
            _write_private(pending, json.dumps({
                "receipt": rid, "task_id": self.tid, "agent": meta.get("agent"), "workspace": meta.get("workspace"),
                "mode": meta.get("mode"), "tool": tool, "reason": decision.reason, "created": time.time(),
                "args": {k: (v if len(str(v)) < 4000 else str(v)[:4000] + "…") for k, v in args.items()}}))
            deadline = time.monotonic() + timeout_s
            try:
                while time.monotonic() < deadline:
                    if self.cancel.is_set():
                        return "task cancelled"
                    if answer.exists():
                        d = json.loads(answer.read_text())
                        return "approve" if d.get("decision") == "approve" else "reject"
                    time.sleep(0.3)
                return "approval timed out"
            finally:
                pending.unlink(missing_ok=True)
                answer.unlink(missing_ok=True)
        return ask


def pending_approvals(state=None):
    d = pathlib.Path(state or STATE) / "approvals"
    out = []
    for p in sorted(d.glob("R-*.json")) if d.exists() else []:
        if p.name.endswith(".decision.json"):
            continue
        try:
            out.append(json.loads(p.read_text()))
        except ValueError:
            continue
    return out


def decide_approval(rid, decision, by, state=None):
    d = pathlib.Path(state or STATE) / "approvals"
    if not (d / f"{rid}.json").exists():
        return False
    _write_private(d / f"{rid}.decision.json", json.dumps({"decision": decision, "by": by, "t": time.time()}))
    return True


def list_tasks(state=None, limit=100):
    root = pathlib.Path(state or STATE) / "tasks"
    out = []
    for d in sorted(root.iterdir(), reverse=True)[:limit] if root.exists() else []:
        m = d / "meta.json"
        if m.exists():
            try:
                out.append(json.loads(m.read_text()))
            except ValueError:
                continue
    return out


def read_events(tid, offset=0, state=None, limit_bytes=2_000_000):
    """Events after a byte offset, and the offset to resume from (survives reconnects)."""
    p = pathlib.Path(state or STATE) / "tasks" / tid / "events.jsonl"
    if not p.exists():
        return [], 0
    out = []
    with open(p, "rb") as f:
        f.seek(offset)
        data = f.read(limit_bytes)
    end = data.rfind(b"\n") + 1
    for line in data[:end].splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out, offset + end
