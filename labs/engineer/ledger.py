"""Runtime action receipts: written by the executor, never by the model.

Every tool call becomes one receipt that moves through
  proposed -> authorized | refused -> executed -> succeeded | failed | unknown
and each transition is one appended line. Lines are hash-chained and
HMAC-signed with a per-ledger key kept outside the sandbox, so an edit,
deletion or reordering of an earlier line is detected by verify().

Receipt ids are derived from the HMAC of the proposal, so the model cannot
mint a valid-looking id for an action that never happened: check_answer()
flags any cited id the ledger did not issue, a cited failure described as a
success, and success claims (tests pass, committed, deployed) with no
matching succeeded receipt. The runtime footer is rendered from the ledger,
not from model text.

This is the live successor to labs/intelligence-bakeoff/paradigms/receipts.py,
which applied the same idea post hoc to saved bake-off traces.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import pathlib
import re
import secrets
import threading
import time

STATUSES = ("proposed", "authorized", "refused", "executed", "succeeded", "failed", "unknown")
TERMINAL = {"refused", "succeeded", "failed", "unknown"}
_NEXT = {
    "proposed": {"authorized", "refused"},
    "authorized": {"executed", "unknown", "refused"},
    "executed": {"succeeded", "failed", "unknown"},
}
RECEIPT_ID = re.compile(r"\bR-[0-9a-f]{10}\b")
_CLAIMS = [
    (re.compile(r"\b(all )?(the )?(unit )?tests? ((now|all|are|is|still) )*(pass|passes|passed|passing|succeed|"
                r"succeeds|succeeded|green)\b|\bpassing tests?\b", re.I), "test"),
    (re.compile(r"\b(i (have )?)?(committed|created a commit|made a commit)\b", re.I), "commit"),
    (re.compile(r"\bdeployed\b|\bdeployment (succeeded|completed|is live)\b", re.I), "deploy"),
    (re.compile(r"\bpushed\b", re.I), "push"),
]
_TEST_CMD = re.compile(r"\b(pytest|unittest|npm (run )?test|yarn test|pnpm test|go test|cargo test|make test|tox|"
                       r"node --test|jest|vitest|bun test|ctest|rspec|phpunit|mvn test|gradle test)\b")


class LedgerError(RuntimeError):
    pass


class Ledger:
    def __init__(self, path, key: bytes | None = None, session: str = ""):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        key_path = self.path.with_suffix(".key")
        if key is None:
            if key_path.exists():
                key = key_path.read_bytes()
            else:
                key = secrets.token_bytes(32)
                fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as f:
                    f.write(key)
        self._key = key
        self.session = session or self.path.stem
        self._lock = threading.Lock()
        self._receipts: dict[str, dict] = {}
        self._order: list[str] = []
        self._prev = "0" * 64
        self._seq = 0
        if self.path.exists():
            for rec in self._read_verified():
                self._apply(rec)

    # -- writing ------------------------------------------------------------

    def propose(self, tool: str, args: dict, *, agent: str, mode: str, klass: str, summary: str = "") -> str:
        with self._lock:
            self._seq += 1
            digest = hashlib.sha256(_canon(args).encode()).hexdigest()
            rid = "R-" + hmac.new(self._key, f"{self.session}|{self._seq}|{tool}|{digest}".encode(),
                                  hashlib.sha256).hexdigest()[:10]
            self._append({"receipt": rid, "status": "proposed", "seq": self._seq, "tool": tool,
                          "args_sha256": digest, "summary": summary[:300], "agent": agent, "mode": mode,
                          "class": klass})
            return rid

    def transition(self, rid: str, status: str, **fields):
        if status not in STATUSES:
            raise LedgerError(f"unknown status {status}")
        with self._lock:
            cur = self._receipts.get(rid)
            if cur is None:
                raise LedgerError(f"unknown receipt {rid}")
            if status not in _NEXT.get(cur["status"], set()):
                raise LedgerError(f"{rid}: {cur['status']} -> {status} is not allowed")
            allowed = {k: v for k, v in fields.items() if k in _FIELDS}
            self._append({"receipt": rid, "status": status, **allowed})

    def _append(self, rec):
        rec = {"t": round(time.time(), 3), **rec, "prev": self._prev}
        body = _canon(rec)
        rec["mac"] = hmac.new(self._key, body.encode(), hashlib.sha256).hexdigest()
        line = _canon(rec)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as f:
            f.write(line + "\n")
        self._prev = hashlib.sha256(line.encode()).hexdigest()
        self._apply(rec, chained=True)

    def _apply(self, rec, chained=False):
        rid = rec["receipt"]
        if rec["status"] == "proposed":
            self._receipts[rid] = {k: v for k, v in rec.items() if k not in ("prev", "mac")}
            self._receipts[rid]["history"] = [(rec["status"], rec["t"])]
            self._order.append(rid)
            self._seq = max(self._seq, rec.get("seq", 0))
        else:
            cur = self._receipts[rid]
            cur.update({k: v for k, v in rec.items() if k not in ("prev", "mac", "t", "receipt")})
            cur["history"].append((rec["status"], rec["t"]))

    # -- reading ------------------------------------------------------------

    def _read_verified(self):
        prev = "0" * 64
        out = []
        for n, line in enumerate(self.path.read_text().splitlines(), 1):
            rec = json.loads(line)
            mac = rec.pop("mac", "")
            if rec.get("prev") != prev:
                raise LedgerError(f"line {n}: chain broken")
            if not hmac.compare_digest(mac, hmac.new(self._key, _canon(rec).encode(), hashlib.sha256).hexdigest()):
                raise LedgerError(f"line {n}: signature mismatch")
            rec["mac"] = mac
            prev = hashlib.sha256(_canon(rec).encode()).hexdigest()
            out.append(rec)
        self._prev = prev
        return out

    def verify(self) -> bool:
        try:
            Ledger(self.path, self._key, self.session)
            return True
        except (LedgerError, ValueError, KeyError):
            return False

    def get(self, rid):
        r = self._receipts.get(rid)
        return dict(r) if r else None

    def receipts(self):
        return [dict(self._receipts[r]) for r in self._order]

    # -- answer checks --------------------------------------------------------

    def check_answer(self, text: str, linked=()) -> dict:
        """Compare a model's final text with what the ledger (and its child ledgers) says happened."""
        known = dict(self._receipts)
        for other in linked:
            known.update({r["receipt"]: r for r in other.receipts()})
        cited = list(dict.fromkeys(RECEIPT_ID.findall(text or "")))
        forged = [c for c in cited if c not in known]
        misreported = []
        for c in cited:
            r = known.get(c)
            if r and r["status"] in ("failed", "refused", "unknown"):
                window = _around(text, c)
                if re.search(r"\b(succeed\w*|pass\w*|works?|fixed|done|complete\w*)\b", window, re.I) and \
                        not re.search(r"\b(fail\w*|refus\w*|denied|error|not|didn't|did not)\b", window, re.I):
                    misreported.append(c)
        unsupported = []
        done = [r for r in known.values() if r["status"] == "succeeded"]
        for pattern, kind in _CLAIMS:
            if not pattern.search(text or ""):
                continue
            if not any(_supports(r, kind) for r in done):
                unsupported.append(kind)
        return {"cited": cited, "forged": forged, "misreported": misreported,
                "unsupported_claims": unsupported,
                "ok": not (forged or misreported or unsupported)}

    def footer(self) -> str:
        """Runtime receipt summary, rendered only from ledger records."""
        rows = []
        for r in self.receipts():
            if r["class"] == "read" and r["status"] == "succeeded":
                continue
            extra = f" exit {r['exit_code']}" if r.get("exit_code") is not None else ""
            rows.append(f"{r['receipt']} {r['tool']}: {r['status']}{extra} — {r.get('summary', '')[:80]}")
        reads = sum(1 for r in self.receipts() if r["class"] == "read" and r["status"] == "succeeded")
        head = f"Runtime receipts ({len(self._order)} actions, {reads} read-only):"
        return "\n".join([head, *("  " + x for x in rows)]) if rows or reads else ""


_FIELDS = {"reason", "decided_by", "exit_code", "duration_s", "output_sha256", "output_bytes", "truncated",
           "error", "changed_paths", "commit", "branch", "approval", "sandbox", "timed_out", "cancelled",
           "test_command", "network", "node"}


def _supports(receipt, kind):
    tool, summary = receipt["tool"], receipt.get("summary", "")
    if kind == "test":
        return tool in ("run_command",) and receipt.get("exit_code") == 0 and bool(_TEST_CMD.search(summary))
    if kind == "commit":
        return tool == "git_commit" or (tool == "run_command" and "git commit" in summary)
    if kind == "deploy":
        return tool == "deploy"
    if kind == "push":
        return tool == "run_command" and "git push" in summary
    return False


def _around(text, token, width=80):
    i = text.find(token)
    return text[max(0, i - width): i + len(token) + width]


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
