"""Signed receipts for every Hermes change, in an engineer task session (so they show in the Haven console).

The session is created lazily on the first change: Hermes starts this server at the beginning of every chat,
and a read-only chat should not leave an empty task behind. Each server process owns one ledger, because a
ledger's hash chain is held in memory by its writer (labs/engineer/ledger.py).

Authorization is recorded as the MCP client's: with `trust: untrusted`, Hermes asks the owner before calling
any tool that is not read-only, and Haven cannot see that prompt. The receipt says exactly that, nothing more.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import time
from pathlib import Path

from .registry import ToolError

AUTHORIZED_BY = "mcp-client"
APPROVAL_NOTE = "Hermes trust=untrusted: owner prompt before non-read-only tools (not observable by Haven)"


class Receipts:
    def __init__(self, state: Path, *, mode: str, agent: str = "hermes", engineer_state: Path | None = None,
                 meta: dict | None = None):
        self.state, self.mode, self.agent = Path(state), mode, agent
        self.engineer_state = engineer_state
        self.meta = meta or {}
        self._sess = None
        self._ledger = None

    # -- session ----------------------------------------------------------------------------------------

    @property
    def session(self):
        if self._sess is None:
            from session import TaskSession  # labs/engineer
            self._sess = TaskSession(state=self.engineer_state, agent=self.agent, agent_kind="mcp",
                                     mode=self.mode, network=False, inference_host="hermes",
                                     tool_host=os.uname().nodename.split(".")[0], egress="LOCAL",
                                     prompt="(Hermes operator session over MCP)", **self.meta)
        return self._sess

    @property
    def ledger(self):
        if self._ledger is None:
            from ledger import Ledger  # labs/engineer
            self._ledger = Ledger(self.session.ledger_path, session=self.session.tid)
        return self._ledger

    @property
    def task_id(self):
        return self._sess.tid if self._sess else None

    def close(self):
        if self._sess is None:
            return
        self._sess.finish({"status": "closed", "receipts": len(self.ledger.receipts()),
                           "runtime_footer": self.ledger.footer(), "ledger_verified": self.ledger.verify()})

    # -- one change ---------------------------------------------------------------------------------------

    def run(self, spec, args: dict, summary: str, call, idempotency_key: str | None = None) -> dict:
        args_sha = hashlib.sha256(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()
        if idempotency_key:
            prior = self._idem_get(idempotency_key)
            if prior:
                if prior["tool"] != spec.name or prior["args_sha256"] != args_sha:
                    raise ToolError("idempotency_conflict",
                                    "this idempotency_key was already used for a different call", refused=True)
                return {**prior["response"], "idempotent_replay": True}
        led = self.ledger
        rid = led.propose(spec.name, args, agent=self.agent, mode=self.mode, klass=spec.effect, summary=summary)
        led.transition(rid, "authorized", decided_by=AUTHORIZED_BY, approval=APPROVAL_NOTE)
        self._emit(rid, spec.name, "authorized", summary)
        t0 = time.monotonic()
        try:
            out = call()
        except ToolError as e:
            if e.refused:
                led.transition(rid, "refused", reason=f"{e.code}: {e.message}"[:300])
                status = "refused"
            elif e.code == "timeout":
                led.transition(rid, "unknown", timed_out=True, duration_s=round(time.monotonic() - t0, 2),
                               reason="timed out; the action may still complete")
                status = "unknown"
            else:
                led.transition(rid, "executed")
                led.transition(rid, "failed", error=f"{e.code}: {e.message}"[:300],
                               duration_s=round(time.monotonic() - t0, 2))
                status = "failed"
            self._emit(rid, spec.name, status, e.message)
            resp = {**e.to_dict(), "receipt": rid, "status": status}
            if idempotency_key and status != "refused":
                self._idem_put(idempotency_key, spec.name, args_sha, resp)
            return resp
        except Exception as e:
            led.transition(rid, "unknown", error=f"{type(e).__name__}: {e}"[:300])
            self._emit(rid, spec.name, "unknown", str(e))
            raise
        body = json.dumps(out, sort_keys=True, default=str)
        led.transition(rid, "executed")
        led.transition(rid, "succeeded", duration_s=round(time.monotonic() - t0, 2),
                       output_sha256=hashlib.sha256(body.encode()).hexdigest(), output_bytes=len(body))
        self._emit(rid, spec.name, "succeeded", summary)
        resp = {"ok": True, "receipt": rid, "status": "succeeded", **out}
        if idempotency_key:
            self._idem_put(idempotency_key, spec.name, args_sha, resp)
        return resp

    def _emit(self, rid, tool, status, text):
        self.session.emit({"type": "action", "receipt": rid, "tool": tool, "status": status,
                           "reason": str(text)[:200]})

    # -- idempotency (shared across Hermes sessions) ---------------------------------------------------------

    def _idem(self, update=None):
        path = self.state / "idempotency.json"
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        with os.fdopen(fd, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                data = json.loads(f.read() or "{}")
            except ValueError:
                data = {}
            if update:
                update(data)
                f.seek(0), f.truncate(), f.write(json.dumps(data))
            return data

    def _idem_get(self, key):
        return self._idem().get(key)

    def _idem_put(self, key, tool, args_sha, response):
        self._idem(lambda d: d.__setitem__(key, {"tool": tool, "args_sha256": args_sha, "t": time.time(),
                                                 "task_id": self.task_id, "response": response}))
