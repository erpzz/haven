"""File leases and child agents.

Leases stop two running agents from editing the same file. The executor checks
them on every write; a lease belongs to a task and lapses when that task ends
or its expiry passes. They are advisory for shell commands (a command can
write any workspace file the sandbox allows); the write tools enforce them.

delegate() creates a child task: its own session, ledger and lease set, a
budget no larger than the parent's remaining budget, a mode no stronger than
the parent's, a depth limit, and a parent link recorded in both metas. The
child runs to completion inside the parent's tool call, and the parent gets
the child's executor-observed result, not the child's own description of it.
"""
from __future__ import annotations

import fcntl
import json
import os
import pathlib
import time

import policy

MODE_RANK = {m: i for i, m in enumerate(policy.MODES)}
MAX_DEPTH = 3


class Leases:
    def __init__(self, state):
        self.path = pathlib.Path(state) / "leases.json"
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _locked(self, fn):
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            raw = os.read(fd, 10_000_000)
            data = json.loads(raw) if raw.strip() else {}
            now = time.time()
            data = {p: l for p, l in data.items() if l["expires"] > now and _alive(l)}
            result = fn(data)
            os.lseek(fd, 0, 0)
            os.ftruncate(fd, 0)
            os.write(fd, json.dumps(data, indent=1).encode())
            return result
        finally:
            os.close(fd)

    def acquire(self, task_id, paths, ttl_s=3600):
        """All-or-nothing. Returns (ok, conflicts)."""
        paths = [os.path.realpath(p) for p in paths]

        def go(data):
            conflicts = {p: data[p]["task_id"] for p in paths if p in data and data[p]["task_id"] != task_id}
            if conflicts:
                return False, conflicts
            for p in paths:
                data[p] = {"task_id": task_id, "expires": time.time() + ttl_s, "pid": os.getpid()}
            return True, {}
        return self._locked(go)

    def release(self, task_id):
        def go(data):
            for p in [p for p, l in data.items() if l["task_id"] == task_id]:
                del data[p]
        self._locked(go)

    def holder(self, path):
        path = os.path.realpath(path)
        return self._locked(lambda data: data.get(path, {}).get("task_id"))

    def all(self):
        return self._locked(lambda data: dict(data))


def _alive(lease):
    try:
        os.kill(lease.get("pid", 0), 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def child_scope(parent: policy.Scope, requested_mode=None):
    mode = requested_mode or parent.mode
    if MODE_RANK.get(mode, 99) > MODE_RANK[parent.mode]:
        mode = parent.mode  # a child never gets more authority than its parent
    return policy.Scope(mode=mode, network=parent.network, push_remotes=(), deploy_targets=(),
                        protected_branches=parent.protected_branches,
                        max_command_seconds=parent.max_command_seconds)
