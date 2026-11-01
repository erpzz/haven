"""Tool registry for operating Haven: schemas, effect classes, launch-time mode, rate limits, audit and receipts.

Generalized from labs/cyber/haven_cyber/tools/registry.py (PR #105), which only ever had to refuse writes.
Differences, each needed once tools change state:

- effect is read | change | create instead of a read_only flag. change/create tools exist only when the
  server was launched in `operate` mode, and their MCP annotations come from the effect, so the client
  (Hermes with trust: untrusted) asks the owner before each one.
- Every change/create call is a signed, hash-chained receipt in an engineer ledger (receipts.py):
  proposed -> authorized -> executed -> succeeded | failed | unknown, or refused before acting.
- Schema validation is recursive (nested objects, array items, string limits, null, const).
- A timeout is reported as `unknown`, never as retryable: the action may still have happened.
- Optional idempotency_key on change tools; a repeat returns the earlier receipt instead of acting twice.
- Rate limits persist in the state directory, so a new Hermes session or a restart does not reset them.
- Error text is scrubbed of home paths and token-shaped strings before it reaches the model.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

EFFECTS = ("read", "change", "create")
MODES = ("observe", "operate")


class ToolError(Exception):
    """A failure the model should see. refused=True means nothing was attempted."""

    def __init__(self, code: str, message: str, *, refused: bool = False, detail: dict | None = None):
        super().__init__(message)
        self.code, self.message, self.refused, self.detail = code, message, refused, detail or {}

    def to_dict(self):
        out = {"ok": False, "error": {"code": self.code, "message": scrub(self.message)}}
        if self.detail:
            out["error"]["detail"] = self.detail
        return out


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    fn: Callable[..., dict]
    effect: str = "read"
    idempotent: bool = False
    destructive: bool = False
    rate_per_min: int = 30
    summary: Callable[[dict], str] | None = None  # one-line receipt summary of the arguments
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.effect not in EFFECTS:
            raise ValueError(f"{self.name}: unknown effect {self.effect}")
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", self.name):
            raise ValueError(f"bad tool name {self.name!r}")

    def schema(self) -> dict:
        s = json.loads(json.dumps(self.input_schema))
        if self.effect != "read":
            s.setdefault("properties", {})["idempotency_key"] = {
                "type": "string", "maxLength": 80,
                "description": "Optional. Reuse the same key to retry safely; a repeat returns the first receipt."}
        return s

    def annotations(self) -> dict:
        return {"readOnlyHint": self.effect == "read", "destructiveHint": self.destructive,
                "idempotentHint": self.idempotent, "openWorldHint": False}


# -- validation ------------------------------------------------------------------------------------------

_TYPES = {"string": (str,), "integer": (int,), "number": (int, float), "boolean": (bool,),
          "object": (dict,), "array": (list,), "null": (type(None),)}


def _is(value, t):
    if t not in _TYPES:
        raise ToolError("bad_schema", f"schema uses unsupported type {t!r}")
    if t in ("integer", "number") and isinstance(value, bool):
        return False
    return isinstance(value, _TYPES[t])


def validate(schema: dict, value: Any, where: str = "arguments") -> None:
    types = schema.get("type")
    if types is not None:
        types = types if isinstance(types, list) else [types]
        if not any(_is(value, t) for t in types):
            raise ToolError("invalid_input", f"{where}: expected {'/'.join(types)}", refused=True)
    if "const" in schema and value != schema["const"]:
        raise ToolError("invalid_input", f"{where}: must be {schema['const']!r}", refused=True)
    if "enum" in schema and value not in schema["enum"]:
        raise ToolError("invalid_input", f"{where}: must be one of {schema['enum']}", refused=True)
    if isinstance(value, str):
        if len(value) > schema.get("maxLength", 1 << 30) or len(value) < schema.get("minLength", 0):
            raise ToolError("invalid_input", f"{where}: length out of range", refused=True)
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            raise ToolError("invalid_input", f"{where}: does not match {schema['pattern']}", refused=True)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < schema.get("minimum", float("-inf")) or value > schema.get("maximum", float("inf")):
            raise ToolError("invalid_input", f"{where}: out of range", refused=True)
    if isinstance(value, list):
        if len(value) > schema.get("maxItems", 1 << 30):
            raise ToolError("invalid_input", f"{where}: too many items", refused=True)
        if "items" in schema:
            for i, item in enumerate(value):
                validate(schema["items"], item, f"{where}[{i}]")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for k in schema.get("required", []):
            if k not in value:
                raise ToolError("invalid_input", f"{where}: missing {k}", refused=True)
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(props))
            if extra:
                raise ToolError("invalid_input", f"{where}: unexpected {extra}", refused=True)
        if len(json.dumps(value, default=str)) > schema.get("maxBytes", 1 << 30):
            raise ToolError("invalid_input", f"{where}: too large", refused=True)
        for k, v in value.items():
            if k in props:
                validate(props[k], v, f"{where}.{k}")


# -- scrubbing ---------------------------------------------------------------------------------------------

_SECRETISH = re.compile(r"(?i)(token|key|secret|password|bearer)([=: ]+)\S+|\b[A-Za-z0-9_\-]{40,}\b")


def scrub(text: str) -> str:
    text = str(text).replace(str(Path.home()), "~")
    text = re.sub(r"/(?:home|Users)/[A-Za-z0-9._-]+", "~", text)
    return _SECRETISH.sub(lambda m: f"{m.group(1)}{m.group(2)}[redacted]" if m.group(1) else "[redacted]", text)[:2000]


# -- rate limits (persisted) -----------------------------------------------------------------------------

class RateLimiter:
    def __init__(self, path: Path, clock=time.time):
        self.path, self.clock = Path(path), clock

    def hit(self, tool: str, per_min: int) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        with os.fdopen(fd, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                data = json.loads(f.read() or "{}")
            except ValueError:
                data = {}
            now = self.clock()
            recent = [t for t in data.get(tool, []) if now - t < 60]
            allowed = len(recent) < per_min
            if allowed:
                recent.append(now)
            data[tool] = recent
            f.seek(0), f.truncate(), f.write(json.dumps(data))
        return allowed


# -- registry ----------------------------------------------------------------------------------------------

class Registry:
    def __init__(self, ctx, *, mode: str, state: Path, receipts=None, clock=time.time):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.ctx, self.mode, self.state, self.receipts, self.clock = ctx, mode, Path(state), receipts, clock
        self.tools: dict[str, ToolSpec] = {}
        self.rate = RateLimiter(self.state / "rate.json", clock)
        self.audit_path = self.state / "audit.jsonl"
        self.listeners: list[Callable[[], None]] = []
        self.refreshers: list[Callable[[], bool]] = []  # each re-syncs dynamic tools; True if the set changed

    def register(self, spec: ToolSpec, replace: bool = False):
        if spec.name in self.tools and not replace:
            raise ValueError(f"duplicate tool {spec.name}")
        self.tools[spec.name] = spec

    def unregister(self, name: str):
        self.tools.pop(name, None)

    def refresh(self) -> bool:
        changed = False
        for fn in self.refreshers:
            changed = fn() or changed
        return changed

    def changed(self):
        for fn in self.listeners:
            fn()

    def visible(self) -> list[ToolSpec]:
        return [t for t in self.tools.values() if self.mode == "operate" or t.effect == "read"]

    def invoke(self, name: str, args: dict | None = None, caller: str = "mcp") -> dict:
        t0 = time.monotonic()
        args = dict(args or {})
        spec = self.tools.get(name)
        receipt = None
        try:
            if spec is None:
                raise ToolError("unknown_tool", f"no tool named {name}", refused=True)
            if spec.effect != "read" and self.mode != "operate":
                raise ToolError("mode_forbids", "this server was launched in observe mode; changes are disabled",
                                refused=True)
            validate(spec.schema(), args)
            if not self.rate.hit(name, spec.rate_per_min):
                raise ToolError("rate_limited", f"{name} is limited to {spec.rate_per_min} calls per minute",
                                refused=True)
            if spec.effect == "read":
                out = {"ok": True, **spec.fn(self.ctx, **args)}
            else:
                key = args.pop("idempotency_key", None)
                summary = spec.summary(args) if spec.summary else json.dumps(args, sort_keys=True)[:200]
                out = self.receipts.run(spec, args, summary, lambda: spec.fn(self.ctx, **args), key)
                receipt = out.get("receipt")
        except ToolError as e:
            out = e.to_dict()
        except Exception as e:  # a bug in a tool must not crash the server or leak a traceback to the model
            out = ToolError("tool_failed", f"{type(e).__name__}: {e}").to_dict()
        self._audit(name, args, caller, out, receipt, t0)
        return out

    def _audit(self, name, args, caller, out, receipt, t0):
        rec = {"t": round(self.clock(), 3), "tool": name, "caller": caller, "mode": self.mode,
               "input_sha256": hashlib.sha256(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest(),
               "ok": bool(out.get("ok")), "ms": round((time.monotonic() - t0) * 1000, 1),
               "error": (out.get("error") or {}).get("code"), "receipt": receipt}
        self.audit_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.audit_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(rec) + "\n")
