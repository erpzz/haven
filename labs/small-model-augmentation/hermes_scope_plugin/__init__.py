"""Hermes v2026.9.24 pre_tool_call bridge to Haven's host-owned scope gate.

Installation is opt-in on a dedicated HERMES_HOME profile. This hook is a
pre-dispatch veto, not a sandbox, model-visible catalog router, or proof that
Hermes loaded the plugin. Independently capture the actual first model request.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import threading

POLICY_ENV = "HAVEN_SCOPE_POLICY_FILE"
ROOT_ENV = "HAVEN_AUGMENTATION_ROOT"
MAX_POLICY_BYTES = 256 * 1024
MAX_SESSIONS = 256


def _block(code):
    # Never echo arguments, policy values, paths, or session identifiers.
    return {"action": "block", "message": "Haven tool policy denied: " + code}


def _read_policy_file(path):
    """Open one private regular file without following its final symlink."""
    if not isinstance(path, str) or not os.path.isabs(path):
        raise ValueError("INVALID_POLICY_PATH")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("NO_SYMLINK_GUARD")
    flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_mode & 0o077):
            raise ValueError("INSECURE_POLICY_FILE")
        if info.st_size > MAX_POLICY_BYTES:
            raise ValueError("POLICY_TOO_LARGE")
        with os.fdopen(os.dup(fd), "rb") as f:
            raw = f.read(MAX_POLICY_BYTES + 1)
        if len(raw) > MAX_POLICY_BYTES:
            raise ValueError("POLICY_TOO_LARGE")
        # Stable identity disallows even same-byte in-place replacement mid-run.
        identity = (info.st_dev, info.st_ino, info.st_uid, info.st_mode,
                    info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        return raw, identity
    finally:
        os.close(fd)


def _scope_engine(root):
    file = root / "tool_scope.py"
    if not file.is_file():
        raise ValueError("SCOPE_ENGINE_MISSING")
    spec = importlib.util.spec_from_file_location("_haven_scope_gate", file)
    if spec is None or spec.loader is None:
        raise ValueError("SCOPE_ENGINE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Gate:
    def __init__(self, *, policy_path=None, augmentation_root=None):
        self._lock = threading.RLock()
        self._states = {}
        self._failed = None
        self._scope = None
        self._policy = None
        self._policy_sha256 = None
        self._identity = None
        self._path = policy_path if policy_path is not None else os.environ.get(POLICY_ENV)
        root = augmentation_root if augmentation_root is not None else os.environ.get(ROOT_ENV)
        try:
            # In-tree tests may omit ROOT_ENV. A copied plugin must set it.
            root_path = Path(root) if root else Path(__file__).resolve().parents[1]
            self._scope = _scope_engine(root_path)
            raw, self._identity = _read_policy_file(self._path)
            self._policy, invalid = self._scope.parse_policy(raw)
            if invalid or self._policy is None:
                raise ValueError("INVALID_POLICY")
            self._policy_sha256 = hashlib.sha256(raw).hexdigest()
        except (OSError, ValueError, TypeError, ImportError, RecursionError) as exc:
            # Register the veto anyway: missing/bad configuration must not
            # silently remove the hook on an otherwise valid plugin.
            self._failed = str(exc).split(":", 1)[0][:64]

    def admit_surface(self, visible_names):
        """Host-side check only. Must receive a *real* captured model request."""
        if self._failed:
            return {"status": "block", "errors": ["POLICY_UNAVAILABLE"]}
        if not self._unchanged():
            return {"status": "block", "errors": ["POLICY_CHANGED"]}
        return self._scope.bind_surface(self._policy, visible_names)

    def _unchanged(self):
        try:
            raw, identity = _read_policy_file(self._path)
            return (identity == self._identity
                    and hashlib.sha256(raw).hexdigest() == self._policy_sha256)
        except (OSError, ValueError, TypeError):
            return False

    def pre_tool_call(self, tool_name=None, args=None, session_id=None, **_):
        try:
            if self._failed:
                return _block("POLICY_UNAVAILABLE")
            if not self._unchanged():
                return _block("POLICY_CHANGED")
            if type(session_id) is not str or not 1 <= len(session_id) <= 256:
                return _block("SESSION_ID_REQUIRED")
            with self._lock:
                state = self._states.get(session_id)
                if state is None:
                    if len(self._states) >= MAX_SESSIONS:
                        return _block("SESSION_LIMIT")
                    state = self._scope.State()
                    self._states[session_id] = state
            receipt = self._scope.check_call(self._policy, state, tool_name, args)
            if receipt.get("status") != "pass":
                # Only known fixed error codes, not raw model-supplied content.
                return _block("CALL_OUT_OF_SCOPE")
            return None
        except Exception:
            # Hermes hook errors may otherwise be skipped on some versions.
            return _block("GATE_INTERNAL_ERROR")


def register(ctx):
    # Called by Hermes only after the plugin is discovered and enabled.
    # A failed configuration still registers a callable that always vetoes.
    gate = Gate()
    ctx.register_hook("pre_tool_call", gate.pre_tool_call)
