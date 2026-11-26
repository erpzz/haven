"""Host-owned preflight for a guarded Hermes plugin profile.

This proves the exact Hermes executable and installed scope-plugin bytes match
host enrollment, Hermes reports the expected user-plugin set enabled, and the
pinned Hermes runtime accepts the plugin through plugins doctor --ci.

It is intentionally a preflight, not proof that a later chat child loaded the
plugin. The real Mac campaign still binds this receipt to the same supervised
Hermes child and independently exercises the pre_tool_call + final MCP gates.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess

PLUGIN_NAME = "haven-scope"
PLUGIN_VERSION = "0.1.0"
MAX_OUTPUT = 1024 * 1024
MAX_FILE = 1024 * 1024
MAX_POLICY = 256 * 1024
MAX_PROFILE_ENV = 1024 * 1024
PROJECT_PLUGIN_ENV = re.compile(rb"(?m)^[ \\t]*(?:export[ \\t]+)?HERMES_ENABLE_PROJECT_PLUGINS[ \\t]*=")
HEX64 = re.compile(r"[0-9a-f]{64}$")
NAME = re.compile(r"[A-Za-z0-9_.:/-]{1,256}$", re.ASCII)


class PreflightError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _strict_json(raw: str):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("duplicate")
            out[key] = value
        return out

    def reject(_):
        raise ValueError("nonfinite")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=reject)


def _hash_regular(path: Path, *, executable=False) -> str:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if not hasattr(os, "O_NOFOLLOW"):
        raise PreflightError("NO_SYMLINK_GUARD")
    flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise PreflightError("ENROLLED_FILE_UNAVAILABLE") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
            raise PreflightError("ENROLLED_FILE_UNTRUSTED")
        if executable and not (info.st_mode & 0o111):
            raise PreflightError("HERMES_NOT_EXECUTABLE")
        if info.st_size > MAX_FILE:
            raise PreflightError("ENROLLED_FILE_TOO_LARGE")
        digest = hashlib.sha256()
        total = 0
        with os.fdopen(os.dup(fd), "rb") as stream:
            for block in iter(lambda: stream.read(128 * 1024), b""):
                total += len(block)
                if total > MAX_FILE:
                    raise PreflightError("ENROLLED_FILE_TOO_LARGE")
                digest.update(block)
        return digest.hexdigest()
    finally:
        os.close(fd)



def _read_private_policy(path: Path):
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if not hasattr(os, "O_NOFOLLOW"):
        raise PreflightError("NO_SYMLINK_GUARD")
    flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise PreflightError("POLICY_UNAVAILABLE") from exc
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_mode & 0o077):
            raise PreflightError("POLICY_FILE_UNTRUSTED")
        if info.st_size > MAX_POLICY:
            raise PreflightError("POLICY_TOO_LARGE")
        with os.fdopen(os.dup(fd), "rb") as stream:
            raw = stream.read(MAX_POLICY + 1)
        if len(raw) > MAX_POLICY:
            raise PreflightError("POLICY_TOO_LARGE")
        return raw, hashlib.sha256(raw).hexdigest()
    finally:
        os.close(fd)


def _load_scope_engine(root: Path, expected_sha256: str):
    engine = root / "tool_scope.py"
    actual = _hash_regular(engine)
    if actual != expected_sha256:
        raise PreflightError("SCOPE_ENGINE_HASH_MISMATCH")
    spec = importlib.util.spec_from_file_location("_haven_preflight_scope", engine)
    if spec is None or spec.loader is None:
        raise PreflightError("SCOPE_ENGINE_INVALID")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise PreflightError("SCOPE_ENGINE_INVALID") from exc
    return module, actual


def _verify_policy(engine, path: Path, expected_sha256: str, code: str):
    raw, actual = _read_private_policy(path)
    if actual != expected_sha256:
        raise PreflightError(code + "_HASH_MISMATCH")
    try:
        policy, invalid = engine.parse_policy(raw)
    except Exception as exc:
        raise PreflightError(code + "_INVALID") from exc
    if invalid or policy is None:
        raise PreflightError(code + "_INVALID")
    return actual, len(policy["allowed_tools"])


def _verify_profile_env(home: Path) -> None:
    """Require a private profile .env that cannot override the project-plugin kill switch."""
    path = home / ".env"
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if not hasattr(os, "O_NOFOLLOW"):
        raise PreflightError("NO_SYMLINK_GUARD")
    flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise PreflightError("PROFILE_ENV_REQUIRED") from exc
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_mode & 0o077):
            raise PreflightError("PROFILE_ENV_UNTRUSTED")
        if info.st_size > MAX_PROFILE_ENV:
            raise PreflightError("PROFILE_ENV_TOO_LARGE")
        with os.fdopen(os.dup(fd), "rb") as stream:
            raw = stream.read(MAX_PROFILE_ENV + 1)
        if len(raw) > MAX_PROFILE_ENV:
            raise PreflightError("PROFILE_ENV_TOO_LARGE")
        if PROJECT_PLUGIN_ENV.search(raw):
            raise PreflightError("PROFILE_ENV_PROJECT_PLUGINS_FORBIDDEN")
    finally:
        os.close(fd)


def _plugin_dir(home: Path) -> Path:
    root = home / "plugins" / PLUGIN_NAME
    try:
        info = root.lstat()
    except OSError as exc:
        raise PreflightError("PLUGIN_NOT_INSTALLED") from exc
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_uid != os.geteuid():
        raise PreflightError("PLUGIN_DIR_UNTRUSTED")
    return root


def _verify_plugin_files(home: Path, init_sha256: str, manifest_sha256: str):
    root = _plugin_dir(home)
    allowed = {"__init__.py", "plugin.yaml", "README.md", "__pycache__"}
    try:
        names = {entry.name for entry in root.iterdir()}
    except OSError as exc:
        raise PreflightError("PLUGIN_DIR_UNREADABLE") from exc
    if names - allowed:
        raise PreflightError("UNEXPECTED_PLUGIN_FILE")
    if not {"__init__.py", "plugin.yaml"} <= names:
        raise PreflightError("PLUGIN_FILE_MISSING")

    cache = root / "__pycache__"
    if cache.exists():
        if cache.is_symlink() or not cache.is_dir():
            raise PreflightError("PLUGIN_CACHE_UNTRUSTED")
        for entry in cache.iterdir():
            if (entry.is_symlink() or not entry.is_file()
                    or not entry.name.startswith("__init__.")
                    or not entry.name.endswith(".pyc")):
                raise PreflightError("PLUGIN_CACHE_UNTRUSTED")

    actual_init = _hash_regular(root / "__init__.py")
    actual_manifest = _hash_regular(root / "plugin.yaml")
    if actual_init != init_sha256:
        raise PreflightError("PLUGIN_CODE_HASH_MISMATCH")
    if actual_manifest != manifest_sha256:
        raise PreflightError("PLUGIN_MANIFEST_HASH_MISMATCH")
    return actual_init, actual_manifest


def _run(command, *, env, timeout):
    try:
        cp = subprocess.run(
            command, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=False, timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PreflightError("HERMES_PREFLIGHT_EXEC_FAILED") from exc
    if len(cp.stdout) > MAX_OUTPUT or len(cp.stderr) > MAX_OUTPUT:
        raise PreflightError("HERMES_PREFLIGHT_OUTPUT_TOO_LARGE")
    return cp


def _validate_plugin_list(raw: bytes, allowed_user_plugins):
    try:
        text = raw.decode("utf-8")
        rows = _strict_json(text)
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError, RecursionError) as exc:
        raise PreflightError("INVALID_PLUGIN_LIST") from exc
    if type(rows) is not list or len(rows) > 128:
        raise PreflightError("INVALID_PLUGIN_LIST")

    by_name = {}
    for row in rows:
        if type(row) is not dict:
            raise PreflightError("INVALID_PLUGIN_LIST")
        name = row.get("name")
        if type(name) is not str or NAME.fullmatch(name) is None or name in by_name:
            raise PreflightError("INVALID_PLUGIN_LIST")
        by_name[name] = row

    expected = set(allowed_user_plugins)
    if set(by_name) != expected:
        raise PreflightError("UNEXPECTED_ENABLED_USER_PLUGIN")
    row = by_name.get(PLUGIN_NAME)
    if row is None or row.get("status") != "enabled":
        raise PreflightError("SCOPE_PLUGIN_NOT_ENABLED")
    if str(row.get("version")) != PLUGIN_VERSION:
        raise PreflightError("SCOPE_PLUGIN_VERSION_MISMATCH")
    if row.get("source") != "user":
        raise PreflightError("SCOPE_PLUGIN_SOURCE_MISMATCH")
    if row.get("removed") not in (None, "", False):
        raise PreflightError("SCOPE_PLUGIN_REMOVED")


def receipt(errors, *, hermes_sha256=None, init_sha256=None, manifest_sha256=None,
            scope_engine_sha256=None, scope_policy_sha256=None,
            mcp_policy_sha256=None, scope_policy_tool_count=0,
            mcp_policy_tool_count=0, enabled_user_plugin_count=0,
            doctor_passed=False):
    return {
        "schema": "haven.hermes-plugin-preflight.v1",
        "status": "block" if errors else "pass",
        "errors": sorted(set(errors)),
        "hermes_sha256": hermes_sha256,
        "plugin_init_sha256": init_sha256,
        "plugin_manifest_sha256": manifest_sha256,
        "scope_engine_sha256": scope_engine_sha256,
        "scope_policy_sha256": scope_policy_sha256,
        "mcp_policy_sha256": mcp_policy_sha256,
        "scope_policy_tool_count": scope_policy_tool_count,
        "mcp_policy_tool_count": mcp_policy_tool_count,
        "enabled_user_plugin_count": enabled_user_plugin_count,
        "doctor_passed": bool(doctor_passed),
    }


def run_preflight(*, hermes: Path, hermes_home: Path, hermes_sha256: str,
                  init_sha256: str, manifest_sha256: str,
                  augmentation_root: Path, scope_engine_sha256: str,
                  scope_policy: Path, scope_policy_sha256: str,
                  mcp_policy: Path, mcp_policy_sha256: str,
                  allowed_user_plugins, timeout=30, env=None):
    if (not all(type(x) is str and HEX64.fullmatch(x) for x in
                (hermes_sha256, init_sha256, manifest_sha256,
                 scope_engine_sha256, scope_policy_sha256, mcp_policy_sha256))):
        return receipt(["INVALID_ENROLLED_HASH"])
    if (type(allowed_user_plugins) not in (list, tuple)
            or not allowed_user_plugins
            or not all(type(x) is str and NAME.fullmatch(x) for x in allowed_user_plugins)
            or len(allowed_user_plugins) != len(set(allowed_user_plugins))
            or PLUGIN_NAME not in allowed_user_plugins):
        return receipt(["INVALID_ALLOWED_PLUGIN_SET"])
    if type(timeout) not in (int, float) or isinstance(timeout, bool) or not 1 <= timeout <= 120:
        return receipt(["INVALID_TIMEOUT"])
    try:
        home_info = hermes_home.lstat()
        if (not stat.S_ISDIR(home_info.st_mode) or stat.S_ISLNK(home_info.st_mode)
                or home_info.st_uid != os.geteuid()):
            raise PreflightError("HERMES_HOME_UNTRUSTED")
        _verify_profile_env(hermes_home)
        actual_hermes = _hash_regular(hermes, executable=True)
        if actual_hermes != hermes_sha256:
            raise PreflightError("HERMES_HASH_MISMATCH")
        actual_init, actual_manifest = _verify_plugin_files(
            hermes_home, init_sha256, manifest_sha256
        )
        root_info = augmentation_root.lstat()
        if (not stat.S_ISDIR(root_info.st_mode) or stat.S_ISLNK(root_info.st_mode)
                or root_info.st_uid != os.geteuid()):
            raise PreflightError("AUGMENTATION_ROOT_UNTRUSTED")
        engine, actual_engine = _load_scope_engine(
            augmentation_root, scope_engine_sha256
        )
        actual_scope_policy, scope_tool_count = _verify_policy(
            engine, scope_policy, scope_policy_sha256, "SCOPE_POLICY"
        )
        actual_mcp_policy, mcp_tool_count = _verify_policy(
            engine, mcp_policy, mcp_policy_sha256, "MCP_POLICY"
        )

        child_env = dict(os.environ if env is None else env)
        child_env.update({
            "HERMES_HOME": str(hermes_home),
            "NO_COLOR": "1",
            "NO_PROXY": "127.0.0.1,localhost",
            "no_proxy": "127.0.0.1,localhost",
            "HAVEN_AUGMENTATION_ROOT": str(augmentation_root),
            "HAVEN_SCOPE_POLICY_FILE": str(scope_policy),
            "HAVEN_MCP_SCOPE_POLICY_FILE": str(mcp_policy),
            "HAVEN_MCP_SCOPE_REQUIRED": "1",
            "HERMES_ENABLE_PROJECT_PLUGINS": "0",
        })
        listed = _run(
            [str(hermes), "plugins", "list", "--enabled", "--user", "--json"],
            env=child_env, timeout=timeout,
        )
        if listed.returncode != 0:
            raise PreflightError("PLUGIN_LIST_FAILED")
        _validate_plugin_list(listed.stdout, allowed_user_plugins)

        doctor = _run(
            [str(hermes), "plugins", "doctor", PLUGIN_NAME, "--ci"],
            env=child_env, timeout=timeout,
        )
        if doctor.returncode != 0:
            raise PreflightError("PLUGIN_DOCTOR_FAILED")

        if _hash_regular(hermes, executable=True) != actual_hermes:
            raise PreflightError("HERMES_CHANGED_DURING_PREFLIGHT")
        _verify_plugin_files(hermes_home, init_sha256, manifest_sha256)
        if _hash_regular(augmentation_root / "tool_scope.py") != actual_engine:
            raise PreflightError("SCOPE_ENGINE_CHANGED_DURING_PREFLIGHT")
        after_scope, _ = _read_private_policy(scope_policy)
        after_mcp, _ = _read_private_policy(mcp_policy)
        if hashlib.sha256(after_scope).hexdigest() != actual_scope_policy:
            raise PreflightError("SCOPE_POLICY_CHANGED_DURING_PREFLIGHT")
        if hashlib.sha256(after_mcp).hexdigest() != actual_mcp_policy:
            raise PreflightError("MCP_POLICY_CHANGED_DURING_PREFLIGHT")
        return receipt(
            [], hermes_sha256=actual_hermes, init_sha256=actual_init,
            manifest_sha256=actual_manifest,
            scope_engine_sha256=actual_engine,
            scope_policy_sha256=actual_scope_policy,
            mcp_policy_sha256=actual_mcp_policy,
            scope_policy_tool_count=scope_tool_count,
            mcp_policy_tool_count=mcp_tool_count,
            enabled_user_plugin_count=len(allowed_user_plugins), doctor_passed=True,
        )
    except PreflightError as exc:
        return receipt([exc.code])
    except Exception:
        return receipt(["PREFLIGHT_INTERNAL_ERROR"])


def main(argv=None):
    p = argparse.ArgumentParser(description="Fail-closed Hermes scope-plugin preflight")
    p.add_argument("--hermes", type=Path, required=True)
    p.add_argument("--hermes-home", type=Path, required=True)
    p.add_argument("--hermes-sha256", required=True)
    p.add_argument("--plugin-init-sha256", required=True)
    p.add_argument("--plugin-manifest-sha256", required=True)
    p.add_argument("--augmentation-root", type=Path, required=True)
    p.add_argument("--scope-engine-sha256", required=True)
    p.add_argument("--scope-policy", type=Path, required=True)
    p.add_argument("--scope-policy-sha256", required=True)
    p.add_argument("--mcp-policy", type=Path, required=True)
    p.add_argument("--mcp-policy-sha256", required=True)
    p.add_argument("--allow-user-plugin", action="append", required=True)
    p.add_argument("--timeout", type=int, default=30)
    args = p.parse_args(argv)
    result = run_preflight(
        hermes=args.hermes,
        hermes_home=args.hermes_home,
        hermes_sha256=args.hermes_sha256,
        init_sha256=args.plugin_init_sha256,
        manifest_sha256=args.plugin_manifest_sha256,
        augmentation_root=args.augmentation_root,
        scope_engine_sha256=args.scope_engine_sha256,
        scope_policy=args.scope_policy,
        scope_policy_sha256=args.scope_policy_sha256,
        mcp_policy=args.mcp_policy,
        mcp_policy_sha256=args.mcp_policy_sha256,
        allowed_user_plugins=args.allow_user_plugin,
        timeout=args.timeout,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
