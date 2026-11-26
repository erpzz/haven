"""Final MCP-server scope boundary for guarded small-model sessions.

This reuses haven.tool-scope.v1 but applies it to the raw MCP server names and
arguments *after* Hermes hook/middleware processing. It is deliberately a
second boundary: model-visible admission remains a separate client-side proof.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import threading

POLICY_ENV = "HAVEN_MCP_SCOPE_POLICY_FILE"
REQUIRED_ENV = "HAVEN_MCP_SCOPE_REQUIRED"
ROOT_ENV = "HAVEN_AUGMENTATION_ROOT"
MAX_POLICY_BYTES = 256 * 1024


class ScopeDenied(PermissionError):
    """Fixed-code host-policy denial; never contains model arguments."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _load_scope(root: Path):
    path = root / "tool_scope.py"
    if not path.is_file():
        raise ScopeDenied("SCOPE_ENGINE_MISSING")
    spec = importlib.util.spec_from_file_location("_haven_mcp_scope_engine", path)
    if spec is None or spec.loader is None:
        raise ScopeDenied("SCOPE_ENGINE_MISSING")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise ScopeDenied("SCOPE_ENGINE_INVALID") from exc
    return module


def _read_private(path: str):
    if not isinstance(path, str) or not os.path.isabs(path):
        raise ScopeDenied("INVALID_POLICY_PATH")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if not hasattr(os, "O_NOFOLLOW"):
        raise ScopeDenied("NO_SYMLINK_GUARD")
    flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ScopeDenied("POLICY_UNAVAILABLE") from exc
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_mode & 0o077):
            raise ScopeDenied("INSECURE_POLICY_FILE")
        if info.st_size > MAX_POLICY_BYTES:
            raise ScopeDenied("POLICY_TOO_LARGE")
        with os.fdopen(os.dup(fd), "rb") as f:
            raw = f.read(MAX_POLICY_BYTES + 1)
        if len(raw) > MAX_POLICY_BYTES:
            raise ScopeDenied("POLICY_TOO_LARGE")
        identity = (
            info.st_dev, info.st_ino, info.st_uid, info.st_mode,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns,
        )
        return raw, identity
    finally:
        os.close(fd)


class McpScopeGate:
    def __init__(self, policy_path: str, *, augmentation_root: str | Path):
        self.path = policy_path
        self.scope = _load_scope(Path(augmentation_root))
        raw, self.identity = _read_private(policy_path)
        policy, invalid = self.scope.parse_policy(raw)
        if invalid or policy is None:
            raise ScopeDenied("INVALID_POLICY")
        self.policy = policy
        self.policy_sha256 = hashlib.sha256(raw).hexdigest()
        self.state = self.scope.State()
        self._lock = threading.RLock()

    @property
    def allowed_tools(self):
        return tuple(self.policy["allowed_tools"])

    def _assert_unchanged(self):
        try:
            raw, identity = _read_private(self.path)
        except ScopeDenied:
            raise ScopeDenied("POLICY_CHANGED") from None
        if identity != self.identity or hashlib.sha256(raw).hexdigest() != self.policy_sha256:
            raise ScopeDenied("POLICY_CHANGED")

    def exposed(self, available_names):
        """Return the host-approved raw MCP names, refusing missing policy tools."""
        self._assert_unchanged()
        if type(available_names) not in (list, tuple, set):
            raise ScopeDenied("INVALID_AVAILABLE_SURFACE")
        available = list(available_names)
        if (not all(type(name) is str for name in available)
                or len(available) != len(set(available))):
            raise ScopeDenied("INVALID_AVAILABLE_SURFACE")
        allowed = set(self.allowed_tools)
        if not allowed <= set(available):
            raise ScopeDenied("POLICY_TOOL_MISSING")
        # Preserve server/catalog ordering while narrowing.
        return [name for name in available if name in allowed]

    def check(self, tool_name, args):
        """Authorize the exact final raw MCP call immediately before dispatch."""
        self._assert_unchanged()
        receipt = self.scope.check_call(self.policy, self.state, tool_name, args)
        if receipt.get("status") != "pass":
            raise ScopeDenied("CALL_OUT_OF_SCOPE")
        return receipt


def from_env(env=None):
    """Construct an optional gate; REQUIRED=1 turns absence/bad config into startup failure."""
    env = os.environ if env is None else env
    required = env.get(REQUIRED_ENV, "0")
    if required not in ("0", "1"):
        raise ScopeDenied("INVALID_REQUIRED_FLAG")
    path = env.get(POLICY_ENV)
    if not path:
        if required == "1":
            raise ScopeDenied("POLICY_REQUIRED")
        return None
    root = env.get(ROOT_ENV)
    if not root:
        raise ScopeDenied("AUGMENTATION_ROOT_REQUIRED")
    return McpScopeGate(path, augmentation_root=root)
