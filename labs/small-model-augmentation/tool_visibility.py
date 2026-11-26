"""Probe the exact tool definitions Hermes exposes to its model.

This starts a loopback scripted OpenAI-compatible endpoint and runs Hermes against it.
The endpoint never asks Hermes to call a tool; it only captures the model-visible tool array.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROBE_MODEL = "haven-tool-visibility-probe"
MAX_REQUEST_BYTES = 2 * 1024 * 1024
DEFAULT_TIMEOUT = 60
PREFIX = re.compile(r"[A-Za-z0-9_]{1,128}\Z", re.ASCII)
TOOL_NAME = re.compile(r"[A-Za-z0-9_.:-]{1,256}\Z", re.ASCII)
HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
TOOLSETS = re.compile(r"[A-Za-z0-9_.:-]+(?:,[A-Za-z0-9_.:-]+)*\Z", re.ASCII)


class ProbeState:
    def __init__(self):
        self.requests = []
        self.invalid_request = False


class ProbeHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server_version = "haven-tool-probe"
    sys_version = ""

    def log_message(self, *args):
        pass

    def _send_json(self, code, value):
        body = json.dumps(value).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/").endswith("/models"):
            return self._send_json(200, {"object": "list", "data": [{"id": PROBE_MODEL, "object": "model"}]})
        self._send_json(404, {"error": "not found"})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1
        if length < 0 or length > MAX_REQUEST_BYTES:
            self.server.state.invalid_request = True
            return self._send_json(413, {"error": "invalid request"})
        try:
            request = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            self.server.state.invalid_request = True
            return self._send_json(400, {"error": "invalid request"})
        if type(request) is not dict or request.get("model") != PROBE_MODEL or "messages" not in request:
            self.server.state.invalid_request = True
            return self._send_json(400, {"error": "invalid request"})
        self.server.state.requests.append(request)
        message = {"role": "assistant", "content": "OK"}
        usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
        if not request.get("stream"):
            return self._send_json(200, {"id": "probe", "object": "chat.completion", "created": int(time.time()),
                                         "model": PROBE_MODEL, "usage": usage,
                                         "choices": [{"index": 0, "message": message, "finish_reason": "stop"}]})
        chunks = [
            {"id": "probe", "object": "chat.completion.chunk", "created": 0, "model": PROBE_MODEL,
             "choices": [{"index": 0, "delta": {"role": "assistant", "content": "OK"}, "finish_reason": None}]},
            {"id": "probe", "object": "chat.completion.chunk", "created": 0, "model": PROBE_MODEL, "usage": usage,
             "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
        ]
        body = "".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks) + "data: [DONE]\n\n"
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _canon(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def fixed_receipt(errors, tool_count=0, prefix_counts=None, exit_code=None,
                  requests=0, executed=False, names=None, surface_sha256=None):
    return {"schema": "haven.hermes-tool-visibility.v2",
            "status": "block" if errors else "pass",
            "errors": errors,
            "tool_count": tool_count,
            "tool_names": list(names or []),
            "tool_surface_sha256": surface_sha256,
            "required_prefix_counts": prefix_counts or {},
            "hermes_exit_code": exit_code,
            "model_requests": requests,
            "actual_hermes_executed": executed}


def tool_names(request):
    tools = request.get("tools")
    if type(tools) is not list:
        raise ValueError("tools missing")
    names = []
    for tool in tools:
        if type(tool) is not dict or tool.get("type") != "function" or type(tool.get("function")) is not dict:
            raise ValueError("invalid tool")
        name = tool["function"].get("name")
        if type(name) is not str or not name or len(name) > 256:
            raise ValueError("invalid name")
        names.append(name)
    if len(names) != len(set(names)):
        raise ValueError("duplicate names")
    return names


def validate_inputs(toolsets, required_prefixes, expected_names=None,
                    expected_surface_sha256=None, expected_tool_count=None):
    if type(toolsets) is not str:
        return "INVALID_TOOLSETS"
    if toolsets:
        if TOOLSETS.fullmatch(toolsets) is None:
            return "INVALID_TOOLSETS"
    elif not (
        expected_tool_count == 0
        and (expected_names is None or expected_names == [])
        and required_prefixes == []
    ):
        return "EMPTY_TOOLSETS_REQUIRE_ZERO_EXPECTATION"
    if (type(required_prefixes) is not list
            or any(type(x) is not str or PREFIX.fullmatch(x) is None for x in required_prefixes)
            or len(required_prefixes) != len(set(required_prefixes))):
        return "INVALID_REQUIRED_PREFIX"
    if expected_names is not None:
        if (type(expected_names) is not list
                or any(type(x) is not str or TOOL_NAME.fullmatch(x) is None for x in expected_names)
                or len(expected_names) != len(set(expected_names))):
            return "INVALID_EXPECTED_TOOL_NAME"
    if (expected_surface_sha256 is not None
            and (type(expected_surface_sha256) is not str
                 or HEX64.fullmatch(expected_surface_sha256) is None)):
        return "INVALID_EXPECTED_SURFACE_HASH"
    if (expected_tool_count is not None
            and (type(expected_tool_count) is not int
                 or isinstance(expected_tool_count, bool)
                 or not 0 <= expected_tool_count <= 4096)):
        return "INVALID_EXPECTED_TOOL_COUNT"
    return None


def run_probe(hermes, hermes_home, toolsets, required_prefixes, *, cwd=None,
              timeout=DEFAULT_TIMEOUT, env=None, expected_names=None,
              expected_surface_sha256=None, expected_tool_count=None):
    invalid = validate_inputs(
        toolsets, required_prefixes, expected_names, expected_surface_sha256,
        expected_tool_count,
    )
    if invalid:
        return fixed_receipt([invalid], exit_code=None, executed=False)
    hermes_path = Path(hermes)
    if not hermes_path.is_file() or not os.access(hermes_path, os.X_OK):
        return fixed_receipt(["HERMES_NOT_EXECUTABLE"], exit_code=None, executed=False)
    home_path = Path(hermes_home) if type(hermes_home) is str else None
    if home_path is None or not home_path.is_dir():
        return fixed_receipt(["INVALID_HERMES_HOME"], exit_code=None, executed=False)
    if cwd is not None and not Path(cwd).is_dir():
        return fixed_receipt(["INVALID_WORKING_DIRECTORY"], exit_code=None, executed=False)

    state = ProbeState()
    server = ThreadingHTTPServer(("127.0.0.1", 0), ProbeHandler)
    server.state = state
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    command = [str(hermes_path), "chat", "--oneshot", "--format", "stream-json",
               "--toolsets", toolsets, "--max-turns", "1", "--provider", "custom",
               "--base-url", f"http://127.0.0.1:{port}/v1", "--api-key", "local-probe",
               "--model", PROBE_MODEL, "-q", "Reply exactly OK. Do not call any tool."]
    child_env = dict(os.environ if env is None else env)
    child_env.update({"HERMES_HOME": str(home_path), "OPENAI_API_KEY": "local-probe", "NO_COLOR": "1",
                      "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"})
    try:
        cp = subprocess.run(command, cwd=cwd, env=child_env, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return fixed_receipt(["HERMES_TIMEOUT"], exit_code=None, requests=len(state.requests), executed=True)
    except OSError:
        return fixed_receipt(["HERMES_EXEC_FAILED"], exit_code=None, requests=len(state.requests), executed=True)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    errors = []
    if "Unknown toolsets:" in cp.stderr or "Unknown toolset:" in cp.stderr:
        errors.append("UNKNOWN_TOOLSET")
    if cp.returncode != 0:
        errors.append("HERMES_EXIT_NONZERO")
    if state.invalid_request:
        errors.append("INVALID_MODEL_REQUEST")
    if not state.requests:
        errors.append("NO_MODEL_REQUEST")
        return fixed_receipt(errors, exit_code=cp.returncode, requests=0, executed=True)
    try:
        names = tool_names(state.requests[0])
        tools = state.requests[0].get("tools")
        surface_sha256 = hashlib.sha256(_canon(tools)).hexdigest()
    except (ValueError, TypeError):
        errors.append("INVALID_TOOL_SCHEMA")
        return fixed_receipt(
            errors, exit_code=cp.returncode, requests=len(state.requests),
            executed=True
        )
    # Attribute each tool to its most-specific required prefix. Required prefixes may overlap
    # (for example mcp_haven_ and mcp_haven_cyber_); naive startswith counts would let a
    # cyber-only inventory falsely satisfy both requirements.
    counts = {prefix: 0 for prefix in required_prefixes}
    ordered = sorted(required_prefixes, key=len, reverse=True)
    for name in names:
        match = next((prefix for prefix in ordered if name.startswith(prefix)), None)
        if match is not None:
            counts[match] += 1
    if any(count == 0 for count in counts.values()):
        errors.append("MISSING_REQUIRED_PREFIX")
    if expected_tool_count is not None and len(names) != expected_tool_count:
        errors.append("TOOL_COUNT_MISMATCH")
    if expected_names is not None and names != expected_names:
        errors.append("TOOL_NAME_SEQUENCE_MISMATCH")
    if (expected_surface_sha256 is not None
            and surface_sha256 != expected_surface_sha256):
        errors.append("TOOL_SURFACE_HASH_MISMATCH")
    return fixed_receipt(
        errors, tool_count=len(names), prefix_counts=counts,
        exit_code=cp.returncode, requests=len(state.requests), executed=True,
        names=names, surface_sha256=surface_sha256,
    )


def main(argv=None):
    p = argparse.ArgumentParser(description="Verify the exact tools Hermes sends to its model")
    p.add_argument("--hermes", required=True)
    p.add_argument("--hermes-home", required=True)
    p.add_argument("--toolsets", required=True)
    p.add_argument("--require-prefix", action="append", default=[])
    p.add_argument("--expect-name", action="append")
    p.add_argument("--expect-surface-sha256")
    p.add_argument("--expect-tool-count", type=int)
    p.add_argument("--cwd")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = p.parse_args(argv)
    if not 1 <= args.timeout <= 300:
        result = fixed_receipt(["INVALID_TIMEOUT"], exit_code=None, executed=False)
    else:
        result = run_probe(
            args.hermes, args.hermes_home, args.toolsets, args.require_prefix,
            cwd=args.cwd, timeout=args.timeout,
            expected_names=args.expect_name,
            expected_surface_sha256=args.expect_surface_sha256,
            expected_tool_count=args.expect_tool_count,
        )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
