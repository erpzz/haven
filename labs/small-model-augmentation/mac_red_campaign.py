#!/usr/bin/env python3
"""Per-case target-Mac qualification campaign for #212 guarded runtime × #189 Red Factory.

The campaign intentionally launches ONE guarded owned-llama/Hermes child per HRF
case. A mixed suite is forbidden because the host authorization policy is
case-specific.

For each case:
1. build the deterministic HRF fixture and raw-MCP scope policy;
2. run a no-tool-call real-Hermes discovery request against that exact fixture;
3. derive the early-hook policy from the ACTUAL transformed model-visible name;
4. run #212 preflight and retain its full receipt;
5. run #212 guarded supervisor / #127 owned llama for exactly one HRF case;
6. bind the child result back to both policy hashes and the discovered surface.

No live target exists in this lane; every MCP object is synthetic.
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
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping

import guarded_model_supervisor as supervisor
import hermes_plugin_preflight as plugin_preflight
import tool_visibility

_RED_FACTORY_DIR = Path(__file__).resolve().parent / "red_factory"
if str(_RED_FACTORY_DIR) not in sys.path:
    sys.path.insert(0, str(_RED_FACTORY_DIR))

from hermes_runner import _logical_fixture_surface, _mcp_scope_policy
from local_runner import _parse_csv_ints, _parse_families
from mcp_fixture import fixture_for_case
from red_factory import build_suite

SCHEMA = "haven.mac-red-per-case-campaign.v1"
CASE_SCHEMA = "haven.mac-red-per-case-receipt.v1"
MAX_HASH_BYTES = 64 * 1024 * 1024 * 1024
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
TOOLSETS = re.compile(r"[A-Za-z0-9_.:-]+(?:,[A-Za-z0-9_.:-]+)*\Z", re.ASCII)


class _DiscoveryState:
    def __init__(self, expected_model: str):
        self.expected_model = expected_model
        self.requests: list[dict[str, Any]] = []
        self.invalid_request = False


class _DiscoveryHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server_version = "haven-mac-red-discovery"
    sys_version = ""

    def log_message(self, *args):
        pass

    def _json(self, code, value):
        body = json.dumps(value).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/").endswith("/models"):
            model = self.server.state.expected_model
            return self._json(200, {
                "object": "list",
                "data": [{"id": model, "object": "model"}],
            })
        self._json(404, {"error": "not found"})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1
        if length < 0 or length > tool_visibility.MAX_REQUEST_BYTES:
            self.server.state.invalid_request = True
            return self._json(413, {"error": "invalid request"})
        try:
            request = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.server.state.invalid_request = True
            return self._json(400, {"error": "invalid request"})
        if (
            type(request) is not dict
            or request.get("model") != self.server.state.expected_model
            or "messages" not in request
        ):
            self.server.state.invalid_request = True
            return self._json(400, {"error": "invalid request"})
        self.server.state.requests.append(request)
        model = self.server.state.expected_model
        message = {"role": "assistant", "content": "OK"}
        usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
        if not request.get("stream"):
            return self._json(200, {
                "id": "probe", "object": "chat.completion",
                "created": int(time.time()), "model": model, "usage": usage,
                "choices": [{
                    "index": 0, "message": message, "finish_reason": "stop"
                }],
            })
        chunks = [
            {
                "id": "probe", "object": "chat.completion.chunk",
                "created": 0, "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {"role": "assistant", "content": "OK"},
                    "finish_reason": None,
                }],
            },
            {
                "id": "probe", "object": "chat.completion.chunk",
                "created": 0, "model": model, "usage": usage,
                "choices": [{
                    "index": 0, "delta": {}, "finish_reason": "stop"
                }],
            },
        ]
        body = (
            "".join("data: " + json.dumps(row) + "\\n\\n" for row in chunks)
            + "data: [DONE]\\n\\n"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class CampaignError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha_obj(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _hermes_shebang_python(hermes: Path) -> Path:
    try:
        first = Path(hermes).read_bytes().splitlines()[0]
    except (OSError, IndexError) as exc:
        raise CampaignError("HERMES_SHEBANG_UNAVAILABLE") from exc
    if not first.startswith(b"#!"):
        raise CampaignError("HERMES_SHEBANG_INVALID")
    try:
        value = first[2:].decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise CampaignError("HERMES_SHEBANG_INVALID") from exc
    # Qualification requires the concrete interpreter embedded by the venv
    # console-script install, not /usr/bin/env indirection.
    if not value.startswith("/") or " " in value or "\t" in value:
        raise CampaignError("HERMES_INTERPRETER_NOT_PINNED")
    python = Path(value)
    if not python.exists() or not os.access(python, os.X_OK):
        raise CampaignError("HERMES_INTERPRETER_UNAVAILABLE")
    return python


def _core_source_manifest(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    entries: list[dict[str, str]] = []
    locations = [root / "hermes_cli", root / "agent", root / "tools"]
    singles = [root / "model_tools.py", root / "run_agent.py"]
    files: list[Path] = []
    for directory in locations:
        if not directory.is_dir() or directory.is_symlink():
            raise CampaignError("HERMES_CORE_SOURCE_MISSING")
        files.extend(directory.rglob("*.py"))
    files.extend(path for path in singles if path.is_file())
    for file in sorted(set(files), key=lambda p: str(p.relative_to(root))):
        if file.is_symlink() or not file.is_file():
            raise CampaignError("HERMES_CORE_SOURCE_UNTRUSTED")
        relative = file.relative_to(root).as_posix()
        # Core source files are intentionally small; refuse generated blobs or
        # unexpected giant Python files instead of silently hashing arbitrary data.
        if file.stat().st_size > 4 * 1024 * 1024:
            raise CampaignError("HERMES_CORE_SOURCE_TOO_LARGE")
        h = hashlib.sha256()
        with file.open("rb") as stream:
            for block in iter(lambda: stream.read(256 * 1024), b""):
                h.update(block)
        entries.append({"path": relative, "sha256": h.hexdigest()})
    if not entries:
        raise CampaignError("HERMES_CORE_SOURCE_MISSING")
    body = {
        "schema": "haven.hermes-core-source-manifest.v1",
        "file_count": len(entries),
        "files": entries,
    }
    body["manifest_sha256"] = _sha_obj(body)
    return body


def _hermes_provenance(hermes: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    python = _hermes_shebang_python(hermes)
    probe = (
        "import json,pathlib,hermes_cli;"
        "p=pathlib.Path(hermes_cli.__file__).resolve();"
        "print(json.dumps({"
        "'version':getattr(hermes_cli,'__version__',None),"
        "'release_date':getattr(hermes_cli,'__release_date__',None),"
        "'module_file':str(p),"
        "'source_root':str(p.parent.parent)"
        "},sort_keys=True))"
    )
    try:
        cp = subprocess.run(
            [str(python), "-c", probe],
            text=True, capture_output=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CampaignError("HERMES_PROVENANCE_PROBE_FAILED") from exc
    if cp.returncode != 0:
        raise CampaignError("HERMES_PROVENANCE_PROBE_FAILED")
    try:
        meta = json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        raise CampaignError("HERMES_PROVENANCE_INVALID") from exc
    if (
        meta.get("version") != EXPECTED_HERMES_VERSION
        or meta.get("release_date") != EXPECTED_HERMES_RELEASE_DATE
    ):
        raise CampaignError("HERMES_RELEASE_MISMATCH")
    root = Path(meta.get("source_root", "")).resolve()
    module_file = Path(meta.get("module_file", "")).resolve()
    if not module_file.is_file() or root not in module_file.parents:
        raise CampaignError("HERMES_PROVENANCE_INVALID")

    try:
        git = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True, capture_output=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CampaignError("HERMES_GIT_PROVENANCE_UNAVAILABLE") from exc
    head = git.stdout.strip() if git.returncode == 0 else ""
    if head != EXPECTED_HERMES_COMMIT:
        raise CampaignError("HERMES_COMMIT_MISMATCH")

    manifest = _core_source_manifest(root)
    provenance = {
        "schema": "haven.hermes-runtime-provenance.v1",
        "version": meta["version"],
        "release_date": meta["release_date"],
        "git_commit": head,
        "source_root": str(root),
        "module_file": str(module_file),
        "core_source_manifest_sha256": manifest["manifest_sha256"],
        "core_source_file_count": manifest["file_count"],
    }
    provenance["provenance_sha256"] = _sha_obj(provenance)
    return provenance, manifest


def _hash_file(path: Path, *, executable: bool | None = None) -> str:
    path = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if not hasattr(os, "O_NOFOLLOW"):
        raise CampaignError("NO_SYMLINK_GUARD")
    flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise CampaignError("HASH_INPUT_UNAVAILABLE") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
            raise CampaignError("HASH_INPUT_UNTRUSTED")
        if executable is True and not (info.st_mode & stat.S_IXUSR):
            raise CampaignError("HASH_INPUT_NOT_EXECUTABLE")
        if executable is False and (info.st_mode & stat.S_IXUSR):
            pass
        if info.st_size < 0 or info.st_size > MAX_HASH_BYTES:
            raise CampaignError("HASH_INPUT_TOO_LARGE")
        h = hashlib.sha256()
        total = 0
        with os.fdopen(os.dup(fd), "rb") as stream:
            for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                total += len(block)
                if total > MAX_HASH_BYTES:
                    raise CampaignError("HASH_INPUT_TOO_LARGE")
                h.update(block)
        return h.hexdigest()
    finally:
        os.close(fd)


def _write_private(path: Path, value: Any) -> str:
    path = Path(path)
    if not path.is_absolute():
        raise CampaignError("OUTPUT_PATH_NOT_ABSOLUTE")
    raw = _canon(value) + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise CampaignError("OUTPUT_CREATE_FAILED") from exc
    try:
        os.write(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)
    return hashlib.sha256(raw[:-1]).hexdigest()


def _write_policy(path: Path, value: Mapping[str, Any]) -> str:
    raw = json.dumps(
        dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)
    return hashlib.sha256(raw).hexdigest()


def _zero_policy() -> dict[str, Any]:
    return {
        "schema": "haven.tool-scope.v1",
        "allowed_tools": [],
        "max_calls": 0,
        "per_tool_max": {},
        "unique_calls": True,
        "argument_rules": {},
    }


def _model_policy(case, fixture: Mapping[str, Any], logical_surface: Mapping[str, str]) -> dict[str, Any]:
    case.validate()
    expected = set(case.tool_policy.allowed_tools)
    if set(logical_surface) != expected:
        raise CampaignError("DISCOVERY_SURFACE_MISMATCH")
    allowed = [logical_surface[name] for name in case.tool_policy.allowed_tools]
    rules: dict[str, Any] = {}
    for logical in case.tool_policy.allowed_tools:
        if logical != "read_fixture":
            raise CampaignError("UNSUPPORTED_CASE_TOOL")
        transformed = logical_surface[logical]
        rules[transformed] = {
            "allowed_keys": ["object"],
            "required_keys": ["object"],
            "exact_values": {"/object": [fixture["object"]]},
        }
    return {
        "schema": "haven.tool-scope.v1",
        "allowed_tools": allowed,
        "max_calls": case.tool_policy.max_total_calls,
        "per_tool_max": {
            logical_surface[name]: case.tool_policy.max_per_tool
            for name in case.tool_policy.allowed_tools
        },
        "unique_calls": not case.tool_policy.allow_duplicate_calls,
        "argument_rules": rules,
    }


def _capture_surface(*, hermes: Path, hermes_home: Path, toolsets: str,
                     model_alias: str, fixture_path: Path, call_log: Path, discovery_policy: Path,
                     raw_mcp_policy: Path, augmentation_root: Path,
                     timeout: float, env: Mapping[str, str] | None = None):
    """Capture exact first model-visible tool names from pinned real Hermes."""
    state = _DiscoveryState(model_alias)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _DiscoveryHandler)
    server.state = state
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    command = [
        str(hermes), "chat", "--oneshot", "--format", "stream-json",
        "--toolsets", toolsets, "--max-turns", "1", "--provider", "custom",
        "--base-url", f"http://127.0.0.1:{port}/v1",
        "--api-key", "local-probe", "--model", model_alias,
        "-q", "Reply exactly OK. Do not call any tool.",
    ]
    child_env = dict(os.environ if env is None else env)
    child_env.update({
        "HERMES_HOME": str(hermes_home),
        "HAVEN_AUGMENTATION_ROOT": str(augmentation_root),
        "HAVEN_SCOPE_POLICY_FILE": str(discovery_policy),
        "HAVEN_MCP_SCOPE_POLICY_FILE": str(raw_mcp_policy),
        "HAVEN_MCP_SCOPE_REQUIRED": "1",
        "HERMES_ENABLE_PROJECT_PLUGINS": "0",
        "HRF_FIXTURE_FILE": str(fixture_path),
        "HRF_MCP_LOG": str(call_log),
        "HRF_MCP_SCOPE_POLICY_FILE": str(raw_mcp_policy),
        "HRF_MCP_SCOPE_REQUIRED": "1",
        "OPENAI_API_KEY": "local-probe",
        "NO_COLOR": "1",
        "NO_PROXY": "127.0.0.1,localhost",
        "no_proxy": "127.0.0.1,localhost",
    })
    try:
        cp = subprocess.run(
            command, env=child_env, text=True, capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise CampaignError("DISCOVERY_TIMEOUT") from exc
    except OSError as exc:
        raise CampaignError("DISCOVERY_EXEC_FAILED") from exc
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    if cp.returncode != 0:
        raise CampaignError("DISCOVERY_HERMES_NONZERO")
    if state.invalid_request:
        raise CampaignError("DISCOVERY_INVALID_MODEL_REQUEST")
    if len(state.requests) != 1:
        raise CampaignError("DISCOVERY_REQUEST_COUNT")
    request = state.requests[0]
    try:
        names = tool_visibility.tool_names(request)
    except ValueError as exc:
        raise CampaignError("DISCOVERY_INVALID_TOOL_SCHEMA") from exc
    tools = request.get("tools")
    surface_sha = _sha_obj(tools)
    try:
        logical, extras = _logical_fixture_surface(names)
    except ValueError as exc:
        raise CampaignError("DISCOVERY_DUPLICATE_LOGICAL_TOOL") from exc
    if extras:
        raise CampaignError("DISCOVERY_EXTRA_TOOL")
    return {
        "names": names,
        "logical_surface": logical,
        "surface_sha256": surface_sha,
        "tool_count": len(names),
        "hermes_exit_code": cp.returncode,
        "model_requests": len(state.requests),
    }


def _assert_source_layout(augmentation_root: Path) -> dict[str, Path]:
    root = Path(augmentation_root)
    red = root / "red_factory"
    paths = {
        "owned_llama": root / "owned_llama.py",
        "observe_llama": root / "observe_llama.py",
        "model_preflight": root / "preflight.py",
        "scope_engine": root / "tool_scope.py",
        "plugin_init_source": root / "hermes_scope_plugin" / "__init__.py",
        "plugin_manifest_source": root / "hermes_scope_plugin" / "plugin.yaml",
        "child": red / "mac_red_case_child.py",
    }
    for path in paths.values():
        if not path.is_file():
            raise CampaignError("CAMPAIGN_SOURCE_MISSING")
    return paths


def _installed_plugin_hashes(home: Path, source_paths: Mapping[str, Path]):
    plugin = home / "plugins" / "haven-scope"
    installed_init = plugin / "__init__.py"
    installed_manifest = plugin / "plugin.yaml"
    init_hash = _hash_file(installed_init)
    manifest_hash = _hash_file(installed_manifest)
    if init_hash != _hash_file(source_paths["plugin_init_source"]):
        raise CampaignError("INSTALLED_PLUGIN_INIT_DRIFT")
    if manifest_hash != _hash_file(source_paths["plugin_manifest_source"]):
        raise CampaignError("INSTALLED_PLUGIN_MANIFEST_DRIFT")
    return init_hash, manifest_hash


def _read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise CampaignError("CHILD_RESULT_UNSAFE")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CampaignError("CHILD_RESULT_INVALID") from exc
    if not isinstance(value, dict):
        raise CampaignError("CHILD_RESULT_INVALID")
    return value


def _case_receipt(*, case, discovery, preflight, supervisor_receipt,
                  result, hashes, model_policy_sha, raw_policy_sha):
    errors: list[str] = []
    pre_hash = _sha_obj(preflight)
    if supervisor_receipt.get("plugin_preflight_sha256") != pre_hash:
        errors.append("SUPERVISOR_PREFLIGHT_BINDING_MISMATCH")
    if supervisor_receipt.get("status") != "pass":
        errors.append("SUPERVISOR_BLOCKED")
    if result.get("status") != "pass":
        errors.append("RED_HARNESS_BLOCKED")
    if result.get("case_id") != case.case_id:
        errors.append("CASE_ID_MISMATCH")
    if result.get("final_mcp_policy_sha256") != raw_policy_sha:
        errors.append("FINAL_MCP_POLICY_MISMATCH")
    if result.get("fixture_tool_names") != discovery["logical_surface"]:
        errors.append("RUNTIME_SURFACE_DRIFT")
    if result.get("extra_visible_tool_count") != 0:
        errors.append("EXTRA_RUNTIME_TOOL")
    if result.get("dispatch_alignment") is not True:
        errors.append("DISPATCH_ALIGNMENT_FAILED")
    body = {
        "schema": CASE_SCHEMA,
        "classification": "development",
        "status": "block" if errors else "pass",
        "errors": sorted(set(errors)),
        "case_id": case.case_id,
        "family": case.family,
        "seed": case.seed,
        "discovery": {
            "tool_names": discovery["names"],
            "logical_surface": discovery["logical_surface"],
            "surface_sha256": discovery["surface_sha256"],
            "tool_count": discovery["tool_count"],
        },
        "policy": {
            "model_scope_sha256": model_policy_sha,
            "raw_mcp_scope_sha256": raw_policy_sha,
        },
        "runtime": dict(hashes),
        "preflight": preflight,
        "supervisor": supervisor_receipt,
        "red_result_sha256": result.get("result_sha256"),
        "model_score_pass": result.get("score", {}).get("pass"),
        "execution_score_pass": result.get("execution_score", {}).get("pass"),
        "proposed_fixture_calls": result.get("proposed_fixture_calls"),
        "actual_fixture_calls": result.get("actual_fixture_calls"),
    }
    body["receipt_sha256"] = _sha_obj(body)
    return body


def run_campaign(*, hermes: Path, hermes_home: Path, toolsets: str,
                 server: Path, model: Path, alias: str, port: int,
                 context: int, seeds, families, out_dir: Path,
                 augmentation_root: Path, allowed_user_plugins,
                 discovery_timeout: float = 60.0, case_timeout: float = 180.0,
                 max_turns: int = 8, start_timeout: float = 120.0,
                 env: Mapping[str, str] | None = None):
    if not TOOLSETS.fullmatch(toolsets):
        raise CampaignError("INVALID_TOOLSETS")
    out_dir = Path(out_dir)
    if not out_dir.is_absolute() or out_dir.exists():
        raise CampaignError("OUTPUT_DIR_MUST_BE_NEW_ABSOLUTE_PATH")
    out_dir.mkdir(mode=0o700, parents=False)
    if stat.S_IMODE(out_dir.stat().st_mode) & 0o077:
        raise CampaignError("OUTPUT_DIR_NOT_PRIVATE")

    source = _assert_source_layout(augmentation_root)
    hermes_provenance, hermes_manifest = _hermes_provenance(hermes)
    _write_private(out_dir / "hermes-core-source-manifest.json", hermes_manifest)
    hermes = Path(hermes)
    hermes_home = Path(hermes_home)
    server = Path(server)
    model = Path(model)

    init_hash, manifest_hash = _installed_plugin_hashes(hermes_home, source)
    hashes = {
        "hermes_sha256": _hash_file(hermes, executable=True),
        "llama_server_sha256": _hash_file(server, executable=True),
        "model_artifact_sha256": _hash_file(model),
        "scope_engine_sha256": _hash_file(source["scope_engine"]),
        "owned_llama_sha256": _hash_file(source["owned_llama"]),
        "observe_llama_sha256": _hash_file(source["observe_llama"]),
        "model_preflight_sha256": _hash_file(source["model_preflight"]),
        "plugin_init_sha256": init_hash,
        "plugin_manifest_sha256": manifest_hash,
        "case_child_sha256": _hash_file(source["child"]),
        "hermes_provenance_sha256": hermes_provenance["provenance_sha256"],
        "hermes_core_source_manifest_sha256": hermes_manifest["manifest_sha256"],
    }

    suite = build_suite(seeds=list(seeds), families=list(families))
    receipts = []
    base_env = dict(os.environ if env is None else env)

    for index, case in enumerate(suite["cases"]):
        case_dir = out_dir / f"{index:04d}-{case.case_id}"
        case_dir.mkdir(mode=0o700)
        fixture = fixture_for_case(case)
        fixture_path = case_dir / "fixture.json"
        _write_private(fixture_path, fixture)
        raw_policy = _mcp_scope_policy(case, fixture)
        raw_policy_path = case_dir / "raw-mcp-policy.json"
        raw_policy_sha = _write_policy(raw_policy_path, raw_policy)

        discovery_policy_path = case_dir / "discovery-model-policy.json"
        discovery_policy_sha = _write_policy(discovery_policy_path, _zero_policy())
        discovery_log = case_dir / "discovery-mcp.jsonl"

        discovery_pre = plugin_preflight.run_preflight(
            hermes=hermes,
            hermes_home=hermes_home,
            hermes_sha256=hashes["hermes_sha256"],
            init_sha256=init_hash,
            manifest_sha256=manifest_hash,
            augmentation_root=Path(augmentation_root),
            scope_engine_sha256=hashes["scope_engine_sha256"],
            scope_policy=discovery_policy_path,
            scope_policy_sha256=discovery_policy_sha,
            mcp_policy=raw_policy_path,
            mcp_policy_sha256=raw_policy_sha,
            allowed_user_plugins=list(allowed_user_plugins),
            timeout=min(120, max(1, int(discovery_timeout))),
            env=base_env,
        )
        if discovery_pre.get("status") != "pass":
            raise CampaignError("DISCOVERY_PREFLIGHT_BLOCKED")

        discovery = _capture_surface(
            hermes=hermes,
            hermes_home=hermes_home,
            toolsets=toolsets,
            model_alias=alias,
            fixture_path=fixture_path,
            call_log=discovery_log,
            discovery_policy=discovery_policy_path,
            raw_mcp_policy=raw_policy_path,
            augmentation_root=Path(augmentation_root),
            timeout=discovery_timeout,
            env=base_env,
        )
        expected_logical = set(case.tool_policy.allowed_tools)
        if set(discovery["logical_surface"]) != expected_logical:
            raise CampaignError("DISCOVERY_SURFACE_MISMATCH")

        model_policy = _model_policy(case, fixture, discovery["logical_surface"])
        model_policy_path = case_dir / "model-scope-policy.json"
        model_policy_sha = _write_policy(model_policy_path, model_policy)

        preflight = plugin_preflight.run_preflight(
            hermes=hermes,
            hermes_home=hermes_home,
            hermes_sha256=hashes["hermes_sha256"],
            init_sha256=init_hash,
            manifest_sha256=manifest_hash,
            augmentation_root=Path(augmentation_root),
            scope_engine_sha256=hashes["scope_engine_sha256"],
            scope_policy=model_policy_path,
            scope_policy_sha256=model_policy_sha,
            mcp_policy=raw_policy_path,
            mcp_policy_sha256=raw_policy_sha,
            allowed_user_plugins=list(allowed_user_plugins),
            timeout=min(120, max(1, int(discovery_timeout))),
            env=base_env,
        )
        if preflight.get("status") != "pass":
            raise CampaignError("CASE_PREFLIGHT_BLOCKED")

        child_out = case_dir / "red-result.json"
        child_command = [
            sys.executable, str(source["child"]),
            "--hermes", str(hermes),
            "--hermes-home", str(hermes_home),
            "--toolsets", toolsets,
            "--base-url", f"http://127.0.0.1:{port}/v1",
            "--model", alias,
            "--family", case.family,
            "--seed", str(case.seed),
            "--timeout", str(case_timeout),
            "--max-turns", str(max_turns),
            "--out", str(child_out),
        ]
        sup, child_rc = supervisor.run_supervisor(
            plugin_args={
                "hermes": hermes,
                "hermes_home": hermes_home,
                "hermes_sha256": hashes["hermes_sha256"],
                "init_sha256": init_hash,
                "manifest_sha256": manifest_hash,
                "augmentation_root": Path(augmentation_root),
                "scope_engine_sha256": hashes["scope_engine_sha256"],
                "scope_policy": model_policy_path,
                "scope_policy_sha256": model_policy_sha,
                "mcp_policy": raw_policy_path,
                "mcp_policy_sha256": raw_policy_sha,
                "allowed_user_plugins": list(allowed_user_plugins),
            },
            owned_llama=source["owned_llama"],
            owned_llama_sha256=hashes["owned_llama_sha256"],
            observe_llama_sha256=hashes["observe_llama_sha256"],
            model_preflight_sha256=hashes["model_preflight_sha256"],
            server=server,
            server_sha256=hashes["llama_server_sha256"],
            model=model,
            model_sha256=hashes["model_artifact_sha256"],
            alias=alias,
            port=port,
            context=context,
            guarded_command=child_command,
            start_timeout=start_timeout,
            server_log=case_dir / "llama-server.log",
            env=base_env,
        )
        if child_rc != 0 or not child_out.is_file():
            result = {
                "status": "block", "case_id": case.case_id,
                "errors": ["GUARDED_CHILD_FAILED"], "result_sha256": None,
            }
        else:
            result = _read_json(child_out)

        receipt = _case_receipt(
            case=case,
            discovery=discovery,
            preflight=preflight,
            supervisor_receipt=sup,
            result=result,
            hashes=hashes,
            model_policy_sha=model_policy_sha,
            raw_policy_sha=raw_policy_sha,
        )
        _write_private(case_dir / "case-receipt.json", receipt)
        receipts.append(receipt)

    body = {
        "schema": SCHEMA,
        "classification": "development",
        "status": "pass" if all(r["status"] == "pass" for r in receipts) else "block",
        "suite_sha256": suite["suite_sha256"],
        "runtime": hashes,
        "hermes_provenance": hermes_provenance,
        "model_alias": alias,
        "context_tokens": context,
        "toolsets": toolsets,
        "n": len(receipts),
        "harness_passes": sum(r["status"] == "pass" for r in receipts),
        "model_passes": sum(r.get("model_score_pass") is True for r in receipts),
        "execution_passes": sum(r.get("execution_score_pass") is True for r in receipts),
        "case_receipt_sha256s": [r["receipt_sha256"] for r in receipts],
    }
    body["campaign_sha256"] = _sha_obj(body)
    _write_private(out_dir / "campaign-receipt.json", body)
    return body


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--hermes", type=Path, required=True)
    p.add_argument("--hermes-home", type=Path, required=True)
    p.add_argument("--toolsets", default="mcp-red-factory")
    p.add_argument("--server", type=Path, required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--alias", required=True)
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--context", type=int, default=65536)
    p.add_argument("--seeds", default="0")
    p.add_argument("--families", default="all")
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--augmentation-root", type=Path, default=Path(__file__).resolve().parent)
    p.add_argument("--allow-user-plugin", action="append", default=["haven-scope"])
    p.add_argument("--discovery-timeout", type=float, default=60.0)
    p.add_argument("--case-timeout", type=float, default=180.0)
    p.add_argument("--max-turns", type=int, default=8)
    p.add_argument("--start-timeout", type=float, default=120.0)
    args = p.parse_args(argv)

    result = run_campaign(
        hermes=args.hermes,
        hermes_home=args.hermes_home,
        toolsets=args.toolsets,
        server=args.server,
        model=args.model,
        alias=args.alias,
        port=args.port,
        context=args.context,
        seeds=_parse_csv_ints(args.seeds),
        families=_parse_families(args.families),
        out_dir=args.out_dir,
        augmentation_root=args.augmentation_root,
        allowed_user_plugins=args.allow_user_plugin,
        discovery_timeout=args.discovery_timeout,
        case_timeout=args.case_timeout,
        max_turns=args.max_turns,
        start_timeout=args.start_timeout,
    )
    print(json.dumps({
        "schema": result["schema"],
        "status": result["status"],
        "campaign_sha256": result["campaign_sha256"],
        "n": result["n"],
        "harness_passes": result["harness_passes"],
        "model_passes": result["model_passes"],
        "execution_passes": result["execution_passes"],
        "out_dir": str(args.out_dir),
    }, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
