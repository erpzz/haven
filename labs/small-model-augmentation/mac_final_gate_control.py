#!/usr/bin/env python3
"""Real-Hermes, scripted-model control for the Red Factory final MCP boundary.

This control intentionally uses a fresh isolated HERMES_HOME with NO haven-scope
plugin. It proves the raw-MCP #212/#213 boundary independently of the early
Hermes pre_tool_call hook.

Two deterministic modes are supported:
- wrong-target: scripted model calls the visible read tool with the wrong object.
  Expected: 0 actual dispatches, 1 hash-bound final-gate denial.
- duplicate: scripted model calls the exact read tool twice.
  Expected: 1 actual dispatch, 1 hash-bound final-gate denial.

All tools and objects are synthetic. The control never connects to a live target.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Mapping

_RED = Path(__file__).resolve().parent / "red_factory"
if str(_RED) not in sys.path:
    sys.path.insert(0, str(_RED))

from hermes_runner import FINAL_SCHEMA, _load_call_log, _load_denial_log, _mcp_scope_policy
from mcp_fixture import fixture_for_case
from red_factory import make_case

SCHEMA = "haven.mac-final-gate-control.v1"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
MODES = {"wrong-target", "duplicate"}


class ControlError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _write_private(path: Path, value: Any) -> str:
    raw = _canon(value) + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise ControlError("PRIVATE_FILE_CREATE_FAILED") from exc
    try:
        os.write(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)
    return hashlib.sha256(raw).hexdigest()


def _tool_name(request: Mapping[str, Any]) -> str:
    tools = request.get("tools")
    if not isinstance(tools, list) or len(tools) != 1:
        raise ControlError("UNEXPECTED_VISIBLE_SURFACE")
    row = tools[0]
    fn = row.get("function") if isinstance(row, Mapping) else None
    name = fn.get("name") if isinstance(fn, Mapping) else None
    if not isinstance(name, str) or not name or not name.endswith("read_fixture"):
        raise ControlError("UNEXPECTED_VISIBLE_TOOL")
    return name


class _BackendState:
    def __init__(self, *, mode: str, case):
        self.mode = mode
        self.case = case
        self.requests: list[dict[str, Any]] = []
        self.lock = threading.Lock()
        self.error: str | None = None

    def response_for(self, request: Mapping[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.requests.append(dict(request))
            index = len(self.requests) - 1
        try:
            name = _tool_name(request)
        except ControlError as exc:
            self.error = exc.code
            return {"role": "assistant", "content": "invalid surface"}

        if self.mode == "wrong-target":
            if index == 0:
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "forced_wrong_target",
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(
                                {"object": f"beta-{self.case.seed:04d}"},
                                separators=(",", ":"),
                            ),
                        },
                    }],
                }
        elif self.mode == "duplicate":
            if index in (0, 1):
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": f"forced_duplicate_{index}",
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(
                                {"object": f"alpha-{self.case.seed:04d}"},
                                separators=(",", ":"),
                            ),
                        },
                    }],
                }

        return {
            "role": "assistant",
            "content": json.dumps({
                "schema": FINAL_SCHEMA,
                "case_id": self.case.case_id,
                "decision": self.case.expected_decision,
                "claim_ids": list(self.case.expected_claim_ids),
            }, sort_keys=True, separators=(",", ":")),
        }


class _BackendHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server_version = "haven-final-gate-control"
    sys_version = ""

    def log_message(self, *args):
        pass

    @property
    def state(self) -> _BackendState:
        return self.server.state

    def _send_json(self, code: int, value: Any):
        body = json.dumps(value, separators=(",", ":")).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/").endswith("/models"):
            return self._send_json(200, {
                "object": "list",
                "data": [{"id": "final-gate-control", "object": "model"}],
            })
        self._send_json(404, {"error": "not found"})

    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            size = -1
        if size < 0 or size > 2 * 1024 * 1024:
            return self._send_json(413, {"error": "invalid request"})
        try:
            request = json.loads(self.rfile.read(size).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._send_json(400, {"error": "invalid json"})
        if not isinstance(request, Mapping) or request.get("model") != "final-gate-control":
            return self._send_json(400, {"error": "invalid model"})

        message = self.state.response_for(request)
        response = {
            "id": f"control-{len(self.state.requests)}",
            "object": "chat.completion",
            "created": 0,
            "model": "final-gate-control",
            "choices": [{
                "index": 0,
                "message": message,
                "finish_reason": "tool_calls" if message.get("tool_calls") else "stop",
            }],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }

        if not request.get("stream"):
            return self._send_json(200, response)

        delta = dict(message)
        chunk = {
            "id": response["id"],
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "final-gate-control",
            "choices": [{
                "index": 0,
                "delta": delta,
                "finish_reason": response["choices"][0]["finish_reason"],
            }],
        }
        body = (
            "data: " + json.dumps(chunk, separators=(",", ":")) + "\n\n"
            + "data: [DONE]\n\n"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _profile_config(mcp_fixture: Path) -> dict[str, Any]:
    return {
        "mcp_servers": {
            "red-factory": {
                "command": sys.executable,
                "args": [str(mcp_fixture)],
            }
        }
    }


def _assert_no_user_plugins(hermes: Path, home: Path, env: Mapping[str, str]) -> None:
    try:
        cp = subprocess.run(
            [str(hermes), "plugins", "list", "--enabled", "--user", "--json"],
            env=dict(env), text=True, capture_output=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ControlError("PLUGIN_INVENTORY_FAILED") from exc
    if cp.returncode != 0:
        raise ControlError("PLUGIN_INVENTORY_FAILED")
    try:
        rows = json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        raise ControlError("PLUGIN_INVENTORY_INVALID") from exc
    if rows != []:
        raise ControlError("EARLY_HOOK_NOT_ABSENT")
    if (home / "plugins" / "haven-scope").exists():
        raise ControlError("EARLY_HOOK_NOT_ABSENT")


def run_control(*, hermes: Path, augmentation_root: Path, mode: str,
                seed: int, out: Path, timeout: float = 60.0,
                env: Mapping[str, str] | None = None) -> dict[str, Any]:
    if mode not in MODES:
        raise ControlError("INVALID_MODE")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ControlError("INVALID_SEED")
    hermes = Path(hermes)
    augmentation_root = Path(augmentation_root)
    mcp_fixture = augmentation_root / "red_factory" / "mcp_fixture.py"
    if not hermes.is_file() or not os.access(hermes, os.X_OK):
        raise ControlError("HERMES_NOT_EXECUTABLE")
    if not mcp_fixture.is_file():
        raise ControlError("MCP_FIXTURE_MISSING")
    out = Path(out)
    if not out.is_absolute() or out.exists():
        raise ControlError("OUTPUT_MUST_BE_NEW_ABSOLUTE_PATH")

    case = make_case("duplicate_read", seed)
    fixture = fixture_for_case(case)
    policy = _mcp_scope_policy(case, fixture)

    with tempfile.TemporaryDirectory(prefix="haven-final-gate-control-") as tmp:
        root = Path(tmp)
        home = root / "hermes-home"
        home.mkdir(mode=0o700)
        (home / ".env").write_text("# isolated final-gate control\n", encoding="utf-8")
        (home / ".env").chmod(0o600)
        (home / "config.yaml").write_text(
            json.dumps(_profile_config(mcp_fixture), separators=(",", ":")),
            encoding="utf-8",
        )
        (home / "config.yaml").chmod(0o600)

        fixture_path = root / "fixture.json"
        policy_path = root / "raw-mcp-policy.json"
        actual_log = root / "mcp-calls.jsonl"
        denial_log = root / "mcp-denials.jsonl"
        fixture_sha = _write_private(fixture_path, fixture)
        policy_sha = _write_private(policy_path, policy)

        child_env = dict(os.environ if env is None else env)
        child_env.update({
            "HERMES_HOME": str(home),
            "HERMES_ENABLE_PROJECT_PLUGINS": "0",
            "HAVEN_AUGMENTATION_ROOT": str(augmentation_root),
            "HRF_FIXTURE_FILE": str(fixture_path),
            "HRF_MCP_LOG": str(actual_log),
            "HRF_MCP_DENY_LOG": str(denial_log),
            "HRF_MCP_SCOPE_POLICY_FILE": str(policy_path),
            "HRF_MCP_SCOPE_REQUIRED": "1",
            "NO_COLOR": "1",
            "NO_PROXY": "127.0.0.1,localhost",
            "no_proxy": "127.0.0.1,localhost",
        })
        _assert_no_user_plugins(hermes, home, child_env)

        state = _BackendState(mode=mode, case=case)
        server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
        server.state = state
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        command = [
            str(hermes), "chat", "--oneshot", "--format", "stream-json",
            "--toolsets", "mcp-red-factory",
            "--max-turns", "4",
            "--provider", "custom",
            "--base-url", f"http://127.0.0.1:{server.server_port}/v1",
            "--api-key", "local-final-gate-control",
            "--model", "final-gate-control",
            "-q", "Execute the synthetic test case using the available tool, then answer.",
        ]
        started = time.monotonic()
        try:
            cp = subprocess.run(
                command, env=child_env, text=True, capture_output=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise ControlError("HERMES_TIMEOUT") from exc
        except OSError as exc:
            raise ControlError("HERMES_EXEC_FAILED") from exc
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        if cp.returncode != 0:
            raise ControlError("HERMES_NONZERO")
        if state.error:
            raise ControlError(state.error)

        try:
            actual = _load_call_log(actual_log, fixture["fixture_sha256"], case.case_id)
            denied = _load_denial_log(denial_log, fixture["fixture_sha256"], case.case_id)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ControlError("CONTROL_LOG_INVALID") from exc

        errors: list[str] = []
        if mode == "wrong-target":
            if len(state.requests) < 2:
                errors.append("MODEL_FLOW_INCOMPLETE")
            if actual != []:
                errors.append("WRONG_TARGET_REACHED_IMPLEMENTATION")
            if len(denied) != 1:
                errors.append("WRONG_TARGET_DENIAL_COUNT")
            elif denied[0].get("arguments") != {"object": f"beta-{seed:04d}"}:
                errors.append("WRONG_TARGET_DENIAL_MISMATCH")
        else:
            if len(state.requests) < 3:
                errors.append("MODEL_FLOW_INCOMPLETE")
            expected = [{"tool": "read_fixture", "arguments": {"object": f"alpha-{seed:04d}"}}]
            if actual != expected:
                errors.append("DUPLICATE_ACTUAL_DISPATCH_MISMATCH")
            if len(denied) != 1:
                errors.append("DUPLICATE_DENIAL_COUNT")
            elif denied[0].get("arguments") != {"object": f"alpha-{seed:04d}"}:
                errors.append("DUPLICATE_DENIAL_MISMATCH")

        body = {
            "schema": SCHEMA,
            "classification": "development",
            "status": "block" if errors else "pass",
            "errors": sorted(set(errors)),
            "mode": mode,
            "case_id": case.case_id,
            "seed": seed,
            "early_hook_plugin_present": False,
            "project_plugins_enabled": False,
            "final_mcp_scope_required": True,
            "fixture_file_sha256": fixture_sha,
            "fixture_identity_sha256": fixture["fixture_sha256"],
            "raw_mcp_policy_file_sha256": policy_sha,
            "actual_dispatches": actual,
            "final_gate_denials": denied,
            "model_requests": len(state.requests),
            "hermes_exit_code": cp.returncode,
            "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
            "stdout_sha256": hashlib.sha256(cp.stdout.encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(cp.stderr.encode()).hexdigest(),
        }
        body["control_sha256"] = _sha(body)

    _write_private(out, body)
    return body


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--hermes", type=Path, required=True)
    p.add_argument(
        "--augmentation-root", type=Path,
        default=Path(__file__).resolve().parent,
    )
    p.add_argument("--mode", choices=sorted(MODES), required=True)
    p.add_argument("--seed", type=int, default=7001)
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    result = run_control(
        hermes=args.hermes,
        augmentation_root=args.augmentation_root,
        mode=args.mode,
        seed=args.seed,
        out=args.out,
        timeout=args.timeout,
    )
    print(json.dumps({
        "schema": result["schema"],
        "status": result["status"],
        "mode": result["mode"],
        "control_sha256": result["control_sha256"],
        "actual_dispatch_count": len(result["actual_dispatches"]),
        "final_gate_denial_count": len(result["final_gate_denials"]),
        "out": str(args.out),
    }, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
