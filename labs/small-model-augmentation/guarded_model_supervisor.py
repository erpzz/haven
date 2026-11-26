"""Compose guarded Hermes profile admission with #127's owned llama lease.

This module does not duplicate model-process ownership. It first executes the
host-owned Hermes/plugin/policy preflight, then verifies the exact external
owned_llama.py runtime trio, and only then invokes that launcher with a guarded
child command.

The actual model/server admission semantics remain owned_llama.py's contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

import hermes_plugin_preflight as plugin_preflight

HEX64 = re.compile(r"[0-9a-f]{64}$")
MAX_SOURCE = 2 * 1024 * 1024
MAX_ARG = 4096
SOURCE_NAMES = ("owned_llama.py", "observe_llama.py", "preflight.py")


class SupervisorError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _canon(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _receipt(errors, *, plugin_preflight_sha256=None,
             owned_llama_sha256=None, observe_llama_sha256=None,
             model_preflight_sha256=None, owned_llama_started=False,
             owned_llama_exit=None):
    return {
        "schema": "haven.guarded-local-model-supervisor.v1",
        "status": "block" if errors else "pass",
        "errors": sorted(set(errors)),
        "plugin_preflight_sha256": plugin_preflight_sha256,
        "owned_llama_sha256": owned_llama_sha256,
        "observe_llama_sha256": observe_llama_sha256,
        "model_preflight_sha256": model_preflight_sha256,
        "owned_llama_started": bool(owned_llama_started),
        "owned_llama_exit": owned_llama_exit,
    }


def _hash_source(path: Path):
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if not hasattr(os, "O_NOFOLLOW"):
        raise SupervisorError("NO_SYMLINK_GUARD")
    flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise SupervisorError("OWNED_LLAMA_SOURCE_UNAVAILABLE") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
            raise SupervisorError("OWNED_LLAMA_SOURCE_UNTRUSTED")
        if info.st_size > MAX_SOURCE:
            raise SupervisorError("OWNED_LLAMA_SOURCE_TOO_LARGE")
        h = hashlib.sha256()
        total = 0
        with os.fdopen(os.dup(fd), "rb") as stream:
            for block in iter(lambda: stream.read(128 * 1024), b""):
                total += len(block)
                if total > MAX_SOURCE:
                    raise SupervisorError("OWNED_LLAMA_SOURCE_TOO_LARGE")
                h.update(block)
        return h.hexdigest()
    finally:
        os.close(fd)


def _verify_owned_runtime(owned_llama: Path, expected):
    root = owned_llama.parent
    try:
        info = root.lstat()
    except OSError as exc:
        raise SupervisorError("OWNED_LLAMA_ROOT_UNAVAILABLE") from exc
    if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
            or info.st_uid != os.geteuid()):
        raise SupervisorError("OWNED_LLAMA_ROOT_UNTRUSTED")
    if owned_llama.name != "owned_llama.py":
        raise SupervisorError("INVALID_OWNED_LLAMA_PATH")
    actual = {}
    for name in SOURCE_NAMES:
        want = expected.get(name)
        if type(want) is not str or HEX64.fullmatch(want) is None:
            raise SupervisorError("INVALID_OWNED_LLAMA_HASH")
        digest = _hash_source(root / name)
        if digest != want:
            raise SupervisorError("OWNED_LLAMA_SOURCE_HASH_MISMATCH")
        actual[name] = digest
    return actual


def _valid_command(command):
    return (
        type(command) is list
        and bool(command)
        and len(command) <= 128
        and all(
            type(arg) is str and 0 < len(arg) <= MAX_ARG and "\x00" not in arg
            for arg in command
        )
    )


def run_supervisor(*, plugin_args: dict, owned_llama: Path,
                   owned_llama_sha256: str, observe_llama_sha256: str,
                   model_preflight_sha256: str, server: Path,
                   server_sha256: str, model: Path, model_sha256: str,
                   alias: str, port: int, context: int,
                   guarded_command, start_timeout=120.0,
                   server_log: Path | None = None, env=None):
    pre = plugin_preflight.run_preflight(**plugin_args)
    pre_sha = hashlib.sha256(_canon(pre)).hexdigest()
    if pre.get("status") != "pass":
        return _receipt(
            ["PLUGIN_PREFLIGHT_BLOCKED"],
            plugin_preflight_sha256=pre_sha,
        ), None

    try:
        actual = _verify_owned_runtime(
            owned_llama,
            {
                "owned_llama.py": owned_llama_sha256,
                "observe_llama.py": observe_llama_sha256,
                "preflight.py": model_preflight_sha256,
            },
        )
        if not _valid_command(guarded_command):
            raise SupervisorError("INVALID_GUARDED_COMMAND")
        if type(port) is not int or isinstance(port, bool) or not 1 <= port <= 65535:
            raise SupervisorError("INVALID_PORT")
        if type(context) is not int or isinstance(context, bool) or context < 64000:
            raise SupervisorError("INVALID_CONTEXT")
        if (type(start_timeout) not in (int, float) or isinstance(start_timeout, bool)
                or not 0.1 <= float(start_timeout) <= 600):
            raise SupervisorError("INVALID_START_TIMEOUT")

        child_env = dict(os.environ if env is None else env)
        child_env.update({
            "HERMES_HOME": str(plugin_args["hermes_home"]),
            "HAVEN_AUGMENTATION_ROOT": str(plugin_args["augmentation_root"]),
            "HAVEN_SCOPE_POLICY_FILE": str(plugin_args["scope_policy"]),
            "HAVEN_MCP_SCOPE_POLICY_FILE": str(plugin_args["mcp_policy"]),
            "HAVEN_MCP_SCOPE_REQUIRED": "1",
            "NO_COLOR": "1",
        })
        command = [
            sys.executable, str(owned_llama),
            "--server", str(server),
            "--server-sha256", server_sha256,
            "--model", str(model),
            "--model-sha256", model_sha256,
            "--alias", alias,
            "--port", str(port),
            "--context", str(context),
            "--start-timeout", str(start_timeout),
        ]
        if server_log is not None:
            command += ["--log", str(server_log)]
        command += ["--"] + list(guarded_command)
        try:
            cp = subprocess.run(command, env=child_env)
        except OSError as exc:
            raise SupervisorError("OWNED_LLAMA_EXEC_FAILED") from exc

        errors = [] if cp.returncode == 0 else ["OWNED_LLAMA_FAILED"]
        return _receipt(
            errors,
            plugin_preflight_sha256=pre_sha,
            owned_llama_sha256=actual["owned_llama.py"],
            observe_llama_sha256=actual["observe_llama.py"],
            model_preflight_sha256=actual["preflight.py"],
            owned_llama_started=True,
            owned_llama_exit=cp.returncode,
        ), cp.returncode
    except SupervisorError as exc:
        return _receipt(
            [exc.code],
            plugin_preflight_sha256=pre_sha,
        ), None


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Fail-closed guarded Hermes + owned llama composition"
    )
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

    p.add_argument("--owned-llama", type=Path, required=True)
    p.add_argument("--owned-llama-sha256", required=True)
    p.add_argument("--observe-llama-sha256", required=True)
    p.add_argument("--model-preflight-sha256", required=True)
    p.add_argument("--server", type=Path, required=True)
    p.add_argument("--server-sha256", required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--model-sha256", required=True)
    p.add_argument("--alias", required=True)
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--context", type=int, default=65536)
    p.add_argument("--start-timeout", type=float, default=120.0)
    p.add_argument("--server-log", type=Path)
    p.add_argument("command", nargs=argparse.REMAINDER)
    args = p.parse_args(argv)
    guarded = args.command[1:] if args.command[:1] == ["--"] else args.command

    plugin_args = {
        "hermes": args.hermes,
        "hermes_home": args.hermes_home,
        "hermes_sha256": args.hermes_sha256,
        "init_sha256": args.plugin_init_sha256,
        "manifest_sha256": args.plugin_manifest_sha256,
        "augmentation_root": args.augmentation_root,
        "scope_engine_sha256": args.scope_engine_sha256,
        "scope_policy": args.scope_policy,
        "scope_policy_sha256": args.scope_policy_sha256,
        "mcp_policy": args.mcp_policy,
        "mcp_policy_sha256": args.mcp_policy_sha256,
        "allowed_user_plugins": args.allow_user_plugin,
    }
    result, child_rc = run_supervisor(
        plugin_args=plugin_args,
        owned_llama=args.owned_llama,
        owned_llama_sha256=args.owned_llama_sha256,
        observe_llama_sha256=args.observe_llama_sha256,
        model_preflight_sha256=args.model_preflight_sha256,
        server=args.server,
        server_sha256=args.server_sha256,
        model=args.model,
        model_sha256=args.model_sha256,
        alias=args.alias,
        port=args.port,
        context=args.context,
        guarded_command=guarded,
        start_timeout=args.start_timeout,
        server_log=args.server_log,
    )
    print(json.dumps(result, sort_keys=True))
    if result["status"] != "pass":
        return 2
    return child_rc if isinstance(child_rc, int) else 2


if __name__ == "__main__":
    raise SystemExit(main())
