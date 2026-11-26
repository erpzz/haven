"""Crash-safe append-only checkpoint journal for small-model runs.

The journal records only run/unit/operation identifiers plus hashes of payloads. Completed
units are skipped on resume. Incomplete units are restartable only when every tool dispatch
in the current attempt was explicitly marked replay-safe.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path

SCHEMA = "haven.checkpoint-journal.v1"
MAX_JOURNAL_BYTES = 64 * 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024
MAX_EVENTS = 100_000
ZERO = "0" * 64
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
TOKEN = re.compile(r"[A-Za-z0-9_.:@/-]{1,256}\Z")
EVENTS = {
    "run_started",
    "run_resumed",
    "unit_started",
    "model_request_started",
    "model_response_committed",
    "tool_dispatch_started",
    "tool_result_committed",
    "unit_completed",
    "unit_failed",
    "run_completed",
}
EVENT_KEYS = {
    "schema", "run_id", "manifest_sha256", "seq", "event", "unit", "attempt",
    "op_id", "replay_safe", "payload_sha256", "prev_sha256", "event_sha256",
}
try:
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - Windows fallback is single-process only.
    _fcntl = None

_thread_lock = threading.Lock()


@dataclass
class Scan:
    events: list[dict]
    valid_bytes: int
    torn_tail: bool
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def _canon(v) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _event_hash(event: dict) -> str:
    body = {k: event[k] for k in EVENT_KEYS if k != "event_sha256"}
    return hashlib.sha256(_canon(body)).hexdigest()


def _valid_token(v, allow_empty=False):
    return type(v) is str and ((allow_empty and v == "") or TOKEN.fullmatch(v) is not None)


def _validate_shape(e):
    errs = []
    if type(e) is not dict or set(e) != EVENT_KEYS:
        return ["INVALID_EVENT_SHAPE"]
    if e.get("schema") != SCHEMA:
        errs.append("INVALID_EVENT_SCHEMA")
    if not _valid_token(e.get("run_id")):
        errs.append("INVALID_RUN_ID")
    if (type(e.get("manifest_sha256")) is not str or HEX64.fullmatch(e["manifest_sha256"]) is None
            or e["manifest_sha256"] == ZERO):
        errs.append("INVALID_MANIFEST_HASH")
    if type(e.get("seq")) is not int or type(e.get("seq")) is bool or e["seq"] < 1:
        errs.append("INVALID_SEQUENCE")
    if e.get("event") not in EVENTS:
        errs.append("INVALID_EVENT_TYPE")
    if not _valid_token(e.get("unit"), allow_empty=True):
        errs.append("INVALID_UNIT")
    if type(e.get("attempt")) is not int or type(e.get("attempt")) is bool or e["attempt"] < 0:
        errs.append("INVALID_ATTEMPT")
    if not _valid_token(e.get("op_id"), allow_empty=True):
        errs.append("INVALID_OP_ID")
    if type(e.get("replay_safe")) is not bool:
        errs.append("INVALID_REPLAY_FLAG")
    for k in ("payload_sha256", "prev_sha256", "event_sha256"):
        if type(e.get(k)) is not str or HEX64.fullmatch(e[k]) is None:
            errs.append("INVALID_HASH")
    return errs


def _read_lines(path: Path) -> tuple[list[tuple[bytes, int]], int, bool, list[str]]:
    if not path.exists():
        return [], 0, False, []
    try:
        size = path.stat().st_size
    except OSError:
        return [], 0, False, ["JOURNAL_STAT_FAILED"]
    if size > MAX_JOURNAL_BYTES:
        return [], 0, False, ["JOURNAL_TOO_LARGE"]
    lines = []
    pos = 0
    errors = []
    torn = False
    try:
        with path.open("rb") as f:
            while True:
                raw = f.readline(MAX_LINE_BYTES + 1)
                if not raw:
                    break
                if len(raw) > MAX_LINE_BYTES:
                    return [], pos, False, ["JOURNAL_LINE_TOO_LARGE"]
                start = pos
                pos += len(raw)
                if not raw.endswith(b"\n"):
                    torn = True
                    pos = start
                    break
                lines.append((raw[:-1], pos))
                if len(lines) > MAX_EVENTS:
                    return [], pos, False, ["TOO_MANY_EVENTS"]
    except OSError:
        return [], 0, False, ["JOURNAL_READ_FAILED"]
    return lines, pos, torn, errors


def scan(path) -> Scan:
    path = Path(path)
    rows, valid_bytes, torn, errors = _read_lines(path)
    if errors:
        return Scan([], valid_bytes, torn, errors)
    events = []
    prev = ZERO
    run_id = manifest = None
    for raw, end in rows:
        try:
            def unique(pairs):
                out = {}
                for k, v in pairs:
                    if k in out:
                        raise ValueError("duplicate")
                    out[k] = v
                return out
            def reject(_):
                raise ValueError("nonfinite")
            e = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=reject)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            return Scan(events, end - len(raw) - 1, torn, ["CORRUPT_COMMITTED_LINE"])
        shape = _validate_shape(e)
        if shape:
            return Scan(events, end - len(raw) - 1, torn, shape)
        if e["seq"] != len(events) + 1:
            return Scan(events, end - len(raw) - 1, torn, ["SEQUENCE_GAP"])
        if e["prev_sha256"] != prev:
            return Scan(events, end - len(raw) - 1, torn, ["HASH_CHAIN_MISMATCH"])
        if _event_hash(e) != e["event_sha256"]:
            return Scan(events, end - len(raw) - 1, torn, ["EVENT_HASH_MISMATCH"])
        if run_id is None:
            run_id, manifest = e["run_id"], e["manifest_sha256"]
        elif e["run_id"] != run_id or e["manifest_sha256"] != manifest:
            return Scan(events, end - len(raw) - 1, torn, ["RUN_IDENTITY_MISMATCH"])
        prev = e["event_sha256"]
        events.append(e)
    return Scan(events, valid_bytes, torn, validate_transitions(events))


def validate_transitions(events):
    if not events:
        return []
    errors = []
    if events[0]["event"] != "run_started":
        errors.append("RUN_START_MISSING")
    run_started = run_completed = 0
    epoch = 0
    units = {}
    op_seen = {}
    for idx, e in enumerate(events):
        kind, unit, attempt, op = e["event"], e["unit"], e["attempt"], e["op_id"]
        if kind == "run_started":
            run_started += 1
            epoch = 1
            if e["seq"] != 1 or unit or attempt != 0 or op or e["replay_safe"]:
                errors.append("INVALID_RUN_START")
        elif kind == "run_resumed":
            epoch += 1
            if run_started != 1 or run_completed or unit or attempt != 0 or op or e["replay_safe"]:
                errors.append("INVALID_RUN_RESUME")
        elif kind == "run_completed":
            run_completed += 1
            if unit or attempt != 0 or op or e["replay_safe"]:
                errors.append("INVALID_RUN_COMPLETE")
            if any(st["open"] for st in units.values()):
                errors.append("ACTIVE_UNIT_AT_RUN_COMPLETE")
            if idx != len(events) - 1:
                errors.append("EVENT_AFTER_RUN_COMPLETE")
        else:
            if run_completed:
                errors.append("EVENT_AFTER_RUN_COMPLETE")
            if not unit or attempt < 1:
                errors.append("UNIT_CONTEXT_REQUIRED")
                continue
            st = units.setdefault(unit, {
                "attempt": 0, "open": False, "terminal": False, "epoch": 0, "nonreplayable": False
            })
            if kind == "unit_started":
                fresh = not st["open"] and not st["terminal"] and attempt == st["attempt"] + 1
                resumed = (st["open"] and not st["nonreplayable"] and epoch > st["epoch"]
                           and attempt == st["attempt"] + 1)
                if op or e["replay_safe"] or st["terminal"] or not (fresh or resumed):
                    errors.append("INVALID_UNIT_START")
                else:
                    st.update(attempt=attempt, open=True, epoch=epoch, nonreplayable=False)
            else:
                if not st["open"] or attempt != st["attempt"]:
                    errors.append("UNIT_NOT_ACTIVE")
                    continue
                if kind in ("unit_completed", "unit_failed"):
                    if op or e["replay_safe"]:
                        errors.append("INVALID_UNIT_TERMINAL")
                    st["open"] = False
                    st["terminal"] = True
                elif kind in ("model_request_started", "tool_dispatch_started"):
                    if not op or op in op_seen:
                        errors.append("INVALID_OPERATION_START")
                    else:
                        op_seen[op] = (kind, unit, attempt, e["replay_safe"], False)
                    if kind == "model_request_started" and not e["replay_safe"]:
                        errors.append("MODEL_REQUEST_MUST_BE_REPLAY_SAFE")
                    if kind == "tool_dispatch_started" and not e["replay_safe"]:
                        st["nonreplayable"] = True
                elif kind in ("model_response_committed", "tool_result_committed"):
                    if not op or op not in op_seen:
                        errors.append("OPERATION_START_MISSING")
                    else:
                        start_kind, su, sa, replay, committed = op_seen[op]
                        expected = "model_request_started" if kind == "model_response_committed" else "tool_dispatch_started"
                        if start_kind != expected or su != unit or sa != attempt or committed:
                            errors.append("OPERATION_COMMIT_MISMATCH")
                        else:
                            op_seen[op] = (start_kind, su, sa, replay, True)
                    if e["replay_safe"]:
                        errors.append("COMMIT_REPLAY_FLAG_INVALID")
    if run_started != 1:
        errors.append("RUN_START_COUNT")
    if run_completed > 1:
        errors.append("RUN_COMPLETE_COUNT")
    return sorted(set(errors))


def resume_plan(events, max_attempts=3):
    if type(max_attempts) is not int or type(max_attempts) is bool or max_attempts < 1:
        raise ValueError("max_attempts")
    units = {}
    run_done = any(e["event"] == "run_completed" for e in events)
    for e in events:
        if not e["unit"]:
            continue
        u = units.setdefault(e["unit"], {
            "attempts": 0, "status": "unknown", "current": 0, "nonreplayable": False,
            "uncertain_replay_safe": 0, "pending_model": 0,
        })
        if e["event"] == "unit_started":
            u.update(attempts=max(u["attempts"], e["attempt"]), current=e["attempt"], status="incomplete",
                     nonreplayable=False, uncertain_replay_safe=0, pending_model=0)
        elif e["event"] == "unit_completed":
            u["status"] = "completed"
        elif e["event"] == "unit_failed":
            u["status"] = "failed"
        elif e["attempt"] == u["current"]:
            if e["event"] == "tool_dispatch_started" and not e["replay_safe"]:
                u["nonreplayable"] = True
            if e["event"] == "model_request_started":
                u["pending_model"] += 1
            elif e["event"] == "model_response_committed":
                u["pending_model"] = max(0, u["pending_model"] - 1)
    committed_tools = {e["op_id"] for e in events if e["event"] == "tool_result_committed"}
    for name, u in units.items():
        if u["status"] == "incomplete":
            current = u["current"]
            u["uncertain_replay_safe"] = sum(
                1 for e in events
                if e["unit"] == name and e["attempt"] == current and e["event"] == "tool_dispatch_started"
                and e["replay_safe"] and e["op_id"] not in committed_tools
            )
    completed = sorted(k for k, v in units.items() if v["status"] == "completed")
    failed = sorted(k for k, v in units.items() if v["status"] == "failed")
    retryable, blocked = [], []
    for k, v in units.items():
        if v["status"] != "incomplete":
            continue
        reasons = []
        if v["nonreplayable"]:
            reasons.append("NONREPLAYABLE_TOOL_IN_INCOMPLETE_UNIT")
        if v["attempts"] >= max_attempts:
            reasons.append("ATTEMPT_LIMIT")
        if reasons:
            blocked.append({"unit": k, "attempts": v["attempts"], "reasons": reasons})
        else:
            retryable.append({
                "unit": k,
                "next_attempt": v["attempts"] + 1,
                "pending_model_requests": v["pending_model"],
                "uncertain_replay_safe_tools": v["uncertain_replay_safe"],
            })
    return {
        "run_completed": run_done,
        "completed_units": completed,
        "failed_units": failed,
        "retryable_units": sorted(retryable, key=lambda x: x["unit"]),
        "blocked_units": sorted(blocked, key=lambda x: x["unit"]),
    }


def _fsync_directory(path: Path):
    """Persist directory-entry changes on POSIX filesystems."""
    if os.name != "posix":
        return
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_DIRECTORY", 0)
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextlib.contextmanager
def _locked_file(path: Path, *, sync_parent=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with _thread_lock:
        flags = os.O_RDWR | os.O_APPEND | getattr(os, "O_CLOEXEC", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        created = False
        try:
            fd = os.open(path, flags | os.O_CREAT | os.O_EXCL, 0o600)
            created = True
        except FileExistsError:
            fd = os.open(path, flags)
        try:
            if created and sync_parent:
                _fsync_directory(path.parent)
            with os.fdopen(fd, "a+b", closefd=False) as fh:
                if _fcntl is not None:
                    _fcntl.flock(fh.fileno(), _fcntl.LOCK_EX)
                try:
                    yield fh
                finally:
                    if _fcntl is not None:
                        _fcntl.flock(fh.fileno(), _fcntl.LOCK_UN)
        finally:
            os.close(fd)


class RunLease:
    """Exclusive POSIX ownership lease held for the lifetime of one runner process.

    The lock file's contents are diagnostic only; the kernel-held flock is the
    authority. POSIX releases it automatically if the owner process dies.
    """

    def __init__(self, journal_path):
        self.path = Path(str(journal_path) + ".owner.lock")
        self._fh = None

    def __enter__(self):
        if _fcntl is None:
            raise RuntimeError("exclusive run lease unsupported on this platform")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fh = self.path.open("a+", encoding="utf-8")
        try:
            _fcntl.flock(fh.fileno(), _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        except (BlockingIOError, OSError):
            fh.close()
            raise RuntimeError("run already has a live owner") from None
        fh.seek(0)
        fh.truncate()
        fh.write(json.dumps({"pid": os.getpid()}, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
        self._fh = fh
        return self

    def __exit__(self, exc_type, exc, tb):
        fh, self._fh = self._fh, None
        if fh is not None:
            try:
                _fcntl.flock(fh.fileno(), _fcntl.LOCK_UN)
            finally:
                fh.close()


class Journal:
    def __init__(self, path, run_id, manifest_sha256, fsync=True):
        if (not _valid_token(run_id) or type(manifest_sha256) is not str
                or HEX64.fullmatch(manifest_sha256) is None or manifest_sha256 == ZERO):
            raise ValueError("invalid run identity")
        self.path = Path(path)
        self.run_id = run_id
        self.manifest_sha256 = manifest_sha256
        self.fsync = fsync

    def open(self, resume=False):
        with _locked_file(self.path, sync_parent=self.fsync) as fh:
            s = scan(self.path)
            if not s.ok:
                raise ValueError("journal invalid: " + ",".join(s.errors))
            if s.torn_tail:
                fh.truncate(s.valid_bytes)
                fh.flush()
                if self.fsync:
                    os.fsync(fh.fileno())
                s = scan(self.path)
            if s.events:
                first = s.events[0]
                if first["run_id"] != self.run_id or first["manifest_sha256"] != self.manifest_sha256:
                    raise ValueError("run identity mismatch")
                if resume and s.events[-1]["event"] != "run_completed":
                    self._append_locked(fh, s, "run_resumed", "", 0, "", False, ZERO)
            else:
                self._append_locked(fh, s, "run_started", "", 0, "", False, ZERO)
        return self

    def _append_locked(self, fh, s, event, unit, attempt, op_id, replay_safe, payload_sha256):
        if event not in EVENTS:
            raise ValueError("event")
        if type(payload_sha256) is not str or HEX64.fullmatch(payload_sha256) is None:
            raise ValueError("invalid payload hash")
        seq = len(s.events) + 1
        prev = s.events[-1]["event_sha256"] if s.events else ZERO
        e = {
            "schema": SCHEMA,
            "run_id": self.run_id,
            "manifest_sha256": self.manifest_sha256,
            "seq": seq,
            "event": event,
            "unit": unit,
            "attempt": attempt,
            "op_id": op_id,
            "replay_safe": replay_safe,
            "payload_sha256": payload_sha256,
            "prev_sha256": prev,
            "event_sha256": ZERO,
        }
        e["event_sha256"] = _event_hash(e)
        errs = validate_transitions(s.events + [e])
        if errs:
            raise ValueError("invalid transition: " + ",".join(errs))
        raw = _canon(e) + b"\n"
        if len(raw) > MAX_LINE_BYTES:
            raise ValueError("event too large")
        fh.seek(0, os.SEEK_END)
        fh.write(raw)
        fh.flush()
        if self.fsync:
            os.fsync(fh.fileno())
        return e

    def append(self, event, unit="", attempt=0, op_id="", replay_safe=False, payload_sha256=ZERO):
        with _locked_file(self.path, sync_parent=self.fsync) as fh:
            s = scan(self.path)
            if not s.ok:
                raise ValueError("journal invalid: " + ",".join(s.errors))
            if s.torn_tail:
                fh.truncate(s.valid_bytes)
                fh.flush()
                if self.fsync:
                    os.fsync(fh.fileno())
                s = scan(self.path)
            if not s.events:
                raise ValueError("journal not opened")
            if s.events[0]["run_id"] != self.run_id or s.events[0]["manifest_sha256"] != self.manifest_sha256:
                raise ValueError("run identity mismatch")
            return self._append_locked(fh, s, event, unit, attempt, op_id, replay_safe, payload_sha256)

    @contextlib.contextmanager
    def owned(self, resume=False):
        """Acquire exclusive runner ownership, open/resume, and hold it until exit."""
        with RunLease(self.path):
            self.open(resume=resume)
            yield self

    def state(self, max_attempts=3):
        s = scan(self.path)
        if not s.ok:
            raise ValueError("journal invalid: " + ",".join(s.errors))
        return resume_plan(s.events, max_attempts=max_attempts)
