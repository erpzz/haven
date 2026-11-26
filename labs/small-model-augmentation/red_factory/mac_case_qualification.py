#!/usr/bin/env python3
"""One-case Mac qualification runner for guarded local Qwythos/Hermes.

This is development/qualification tooling. It never targets a live tenant or network.
The workflow is intentionally one Red Factory case per #212 supervisor admission:
1. validate enrolled source/runtime identity and the isolated Hermes profile;
2. run a no-tool-call surface discovery against the synthetic Red MCP fixture;
3. build case-specific model-side and raw-MCP scope policies from that exact surface;
4. replay the exact surface under those policies;
5. bind those same policy bytes in #212 preflight/supervisor;
6. run one #189/#213 Red case under the owned llama lease;
7. verify the child used the preflight-bound raw policy and exact transformed surface.
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
from typing import Any, Mapping

AUG = Path(__file__).resolve().parents[1]
RED = Path(__file__).resolve().parent
if str(AUG) not in sys.path:
    sys.path.insert(0, str(AUG))
if str(RED) not in sys.path:
    sys.path.insert(0, str(RED))

import guarded_model_supervisor
import hermes_plugin_preflight
import tool_visibility
from hermes_runner import _mcp_scope_policy
from local_runner import _write_private_json
from mcp_fixture import fixture_for_case
from red_factory import FAMILIES, make_case

ENROLLMENT_SCHEMA = "haven.mac-red-case-enrollment.v1"
RECEIPT_SCHEMA = "haven.mac-red-case-qualification.v1"
HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
VERSION_LINE = re.compile(r"^Hermes Agent v([^ ]+) \(([^)]+)\)")
MAX_JSON = 1024 * 1024

SOURCE_BINDINGS = {
    "plugin_init_sha256": AUG / "hermes_scope_plugin" / "__init__.py",
    "plugin_manifest_sha256": AUG / "hermes_scope_plugin" / "plugin.yaml",
    "scope_engine_sha256": AUG / "tool_scope.py",
    "mcp_scope_runtime_sha256": AUG / "mcp_scope_runtime.py",
    "owned_llama_sha256": AUG / "owned_llama.py",
    "observe_llama_sha256": AUG / "observe_llama.py",
    "model_preflight_sha256": AUG / "preflight.py",
    "tool_visibility_sha256": AUG / "tool_visibility.py",
    "plugin_preflight_source_sha256": AUG / "hermes_plugin_preflight.py",
    "guarded_supervisor_source_sha256": AUG / "guarded_model_supervisor.py",
    "red_runner_sha256": RED / "hermes_runner.py",
    "red_fixture_sha256": RED / "mcp_fixture.py",
    "red_factory_sha256": RED / "red_factory.py",
}
ENROLLMENT_KEYS = {
    "schema", "hermes_sha256", "hermes_version", "hermes_release_date",
    "hermes_config_sha256", "hermes_profile_env_sha256",
    *SOURCE_BINDINGS.keys(),
}


class QualificationError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha_file(path: Path, *, executable: bool = False, max_bytes: int = 16 * 1024 * 1024) -> str:
    path = Path(path)
    if not path.is_absolute():
        path = path.resolve()
    if not hasattr(os, "O_NOFOLLOW"):
        raise QualificationError("NO_SYMLINK_GUARD")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0))
    except OSError as exc:
        raise QualificationError("SOURCE_UNAVAILABLE") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
            raise QualificationError("SOURCE_UNTRUSTED")
        if executable and not (info.st_mode & stat.S_IXUSR):
            raise QualificationError("SOURCE_NOT_EXECUTABLE")
        if info.st_size > max_bytes:
            raise QualificationError("SOURCE_TOO_LARGE")
        h = hashlib.sha256()
        total = 0
        with os.fdopen(os.dup(fd), "rb") as stream:
            for block in iter(lambda: stream.read(128 * 1024), b""):
                total += len(block)
                if total > max_bytes:
                    raise QualificationError("SOURCE_TOO_LARGE")
                h.update(block)
        return h.hexdigest()
    finally:
        os.close(fd)


def _read_private_json(path: Path, expected_schema: str | None = None) -> dict[str, Any]:
    path = Path(path)
    if not path.is_absolute():
        path = path.resolve()
    if not hasattr(os, "O_NOFOLLOW"):
        raise QualificationError("NO_SYMLINK_GUARD")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0))
    except OSError as exc:
        raise QualificationError("PRIVATE_JSON_UNAVAILABLE") from exc
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_mode & 0o077 or info.st_size > MAX_JSON):
            raise QualificationError("PRIVATE_JSON_UNTRUSTED")
        with os.fdopen(os.dup(fd), "rb") as stream:
            raw = stream.read(MAX_JSON + 1)
    finally:
        os.close(fd)
    if len(raw) > MAX_JSON:
        raise QualificationError("PRIVATE_JSON_TOO_LARGE")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualificationError("PRIVATE_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise QualificationError("PRIVATE_JSON_INVALID")
    if expected_schema is not None and value.get("schema") != expected_schema:
        raise QualificationError("PRIVATE_JSON_SCHEMA_MISMATCH")
    return value


def _load_enrollment(path: Path) -> tuple[dict[str, Any], str, dict[str, str]]:
    enrollment = _read_private_json(path, ENROLLMENT_SCHEMA)
    if set(enrollment) != ENROLLMENT_KEYS:
        raise QualificationError("ENROLLMENT_SHAPE_MISMATCH")
    for key in ("hermes_sha256", "hermes_config_sha256",
                "hermes_profile_env_sha256", *SOURCE_BINDINGS.keys()):
        value = enrollment.get(key)
        if not isinstance(value, str) or HEX64.fullmatch(value) is None:
            raise QualificationError("ENROLLMENT_HASH_INVALID")
    if not isinstance(enrollment.get("hermes_version"), str) or not enrollment["hermes_version"]:
        raise QualificationError("ENROLLMENT_VERSION_INVALID")
    if not isinstance(enrollment.get("hermes_release_date"), str) or not enrollment["hermes_release_date"]:
        raise QualificationError("ENROLLMENT_VERSION_INVALID")

    actual_sources = {}
    for key, path_value in SOURCE_BINDINGS.items():
        digest = _sha_file(path_value)
        if digest != enrollment[key]:
            raise QualificationError("ENROLLED_SOURCE_HASH_MISMATCH")
        actual_sources[str(path_value.relative_to(AUG))] = digest
    implementation_sha256 = hashlib.sha256(_canon(actual_sources)).hexdigest()
    return enrollment, implementation_sha256, actual_sources


def _sha_private_profile_file(path: Path, *, max_bytes: int = 1024 * 1024) -> str:
    path = Path(path)
    if not path.is_absolute():
        path = path.resolve()
    if not hasattr(os, "O_NOFOLLOW"):
        raise QualificationError("NO_SYMLINK_GUARD")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0))
    except OSError as exc:
        raise QualificationError("PROFILE_FILE_UNAVAILABLE") from exc
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_mode & 0o077):
            raise QualificationError("PROFILE_FILE_UNTRUSTED")
        if info.st_size > max_bytes:
            raise QualificationError("PROFILE_FILE_TOO_LARGE")
        h = hashlib.sha256()
        total = 0
        with os.fdopen(os.dup(fd), "rb") as stream:
            for block in iter(lambda: stream.read(128 * 1024), b""):
                total += len(block)
                if total > max_bytes:
                    raise QualificationError("PROFILE_FILE_TOO_LARGE")
                h.update(block)
        return h.hexdigest()
    finally:
        os.close(fd)


def _verify_profile_files(hermes_home: Path,
                          enrollment: Mapping[str, Any]) -> dict[str, str]:
    home = Path(hermes_home).expanduser().resolve()
    config_sha = _sha_private_profile_file(home / "config.yaml")
    env_sha = _sha_private_profile_file(home / ".env")
    if config_sha != enrollment["hermes_config_sha256"]:
        raise QualificationError("HERMES_CONFIG_HASH_MISMATCH")
    if env_sha != enrollment["hermes_profile_env_sha256"]:
        raise QualificationError("HERMES_PROFILE_ENV_HASH_MISMATCH")
    return {"config_sha256": config_sha, "env_sha256": env_sha}


def _version_probe(hermes: Path, hermes_home: Path, enrollment: Mapping[str, Any],
                   env: Mapping[str, str]) -> dict[str, Any]:
    if _sha_file(hermes, executable=True) != enrollment["hermes_sha256"]:
        raise QualificationError("HERMES_HASH_MISMATCH")
    child_env = dict(env)
    child_env.update({
        "HERMES_HOME": str(hermes_home),
        "HERMES_ENABLE_PROJECT_PLUGINS": "0",
        "NO_COLOR": "1",
    })
    try:
        cp = subprocess.run(
            [str(hermes), "--version"], env=child_env, text=True,
            capture_output=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise QualificationError("HERMES_VERSION_PROBE_FAILED") from exc
    if cp.returncode != 0:
        raise QualificationError("HERMES_VERSION_PROBE_FAILED")
    first = cp.stdout.splitlines()[0] if cp.stdout.splitlines() else ""
    match = VERSION_LINE.match(first)
    if not match:
        raise QualificationError("HERMES_VERSION_OUTPUT_INVALID")
    version, release_date = match.groups()
    if (version != enrollment["hermes_version"]
            or release_date != enrollment["hermes_release_date"]):
        raise QualificationError("HERMES_VERSION_MISMATCH")
    return {
        "version": version,
        "release_date": release_date,
        "stdout_sha256": hashlib.sha256(cp.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(cp.stderr.encode()).hexdigest(),
    }


def _write_policy(path: Path, value: Mapping[str, Any]) -> str:
    path = Path(path)
    raw = json.dumps(
        dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as writer:
        writer.write(raw)
        writer.flush()
        os.fsync(writer.fileno())
    return hashlib.sha256(raw).hexdigest()


def _deny_all_policy() -> dict[str, Any]:
    return {
        "schema": "haven.tool-scope.v1",
        "allowed_tools": [],
        "max_calls": 0,
        "per_tool_max": {},
        "unique_calls": True,
        "argument_rules": {},
    }


def _model_policy(case, fixture: Mapping[str, Any],
                  transformed_names: list[str]) -> dict[str, Any]:
    allowed_raw = list(case.tool_policy.allowed_tools)
    if len(allowed_raw) != len(transformed_names):
        raise QualificationError("DISCOVERED_TOOL_COUNT_MISMATCH")
    if not allowed_raw:
        return _deny_all_policy()
    if allowed_raw != ["read_fixture"] or len(transformed_names) != 1:
        raise QualificationError("UNSUPPORTED_RED_TOOL_MAPPING")
    visible = transformed_names[0]
    return {
        "schema": "haven.tool-scope.v1",
        "allowed_tools": [visible],
        "max_calls": case.tool_policy.max_total_calls,
        "per_tool_max": {visible: case.tool_policy.max_per_tool},
        "unique_calls": not case.tool_policy.allow_duplicate_calls,
        "argument_rules": {
            visible: {
                "allowed_keys": ["object"],
                "required_keys": ["object"],
                "exact_values": {"/object": [fixture["object"]]},
            }
        },
    }


def _preflight_args(enrollment, hermes, hermes_home, model_policy, model_sha,
                    raw_policy, raw_sha):
    return {
        "hermes": Path(hermes),
        "hermes_home": Path(hermes_home),
        "hermes_sha256": enrollment["hermes_sha256"],
        "init_sha256": enrollment["plugin_init_sha256"],
        "manifest_sha256": enrollment["plugin_manifest_sha256"],
        "augmentation_root": AUG,
        "scope_engine_sha256": enrollment["scope_engine_sha256"],
        "scope_policy": Path(model_policy),
        "scope_policy_sha256": model_sha,
        "mcp_policy": Path(raw_policy),
        "mcp_policy_sha256": raw_sha,
        "allowed_user_plugins": ["haven-scope"],
    }


def _preflight_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canon(dict(value))).hexdigest()


def _new_output_dir(path: Path) -> Path:
    path = Path(path).expanduser().resolve()
    if path.exists():
        raise QualificationError("OUTPUT_DIR_EXISTS")
    path.mkdir(mode=0o700, parents=False)
    if stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise QualificationError("OUTPUT_DIR_MODE_INVALID")
    return path


def _fixture_env(base_env, hermes_home, fixture_path, call_log,
                 model_policy, raw_policy, *, raw_guard: bool):
    env = dict(base_env)
    env.update({
        "HERMES_HOME": str(hermes_home),
        "HERMES_ENABLE_PROJECT_PLUGINS": "0",
        "HAVEN_AUGMENTATION_ROOT": str(AUG),
        "HAVEN_SCOPE_POLICY_FILE": str(model_policy),
        "HAVEN_MCP_SCOPE_POLICY_FILE": str(raw_policy),
        "HAVEN_MCP_SCOPE_REQUIRED": "1",
        "HRF_FIXTURE_FILE": str(fixture_path),
        "HRF_MCP_LOG": str(call_log),
        "HRF_MCP_SCOPE_REQUIRED": "1" if raw_guard else "0",
        "NO_COLOR": "1",
        "NO_PROXY": "127.0.0.1,localhost",
        "no_proxy": "127.0.0.1,localhost",
    })
    if raw_guard:
        env["HRF_MCP_SCOPE_POLICY_FILE"] = str(raw_policy)
    else:
        env.pop("HRF_MCP_SCOPE_POLICY_FILE", None)
    return env


def run_case_qualification(*, hermes: Path, hermes_home: Path, toolsets: str,
                           server: Path, server_sha256: str,
                           model: Path, model_sha256: str, alias: str,
                           port: int, context: int, family: str, seed: int,
                           enrollment_path: Path, out_dir: Path,
                           timeout_seconds: float = 180.0,
                           max_turns: int = 8, start_timeout: float = 120.0,
                           env: Mapping[str, str] | None = None) -> dict[str, Any]:
    if family not in FAMILIES:
        raise QualificationError("INVALID_FAMILY")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise QualificationError("INVALID_SEED")
    if not isinstance(server_sha256, str) or HEX64.fullmatch(server_sha256) is None:
        raise QualificationError("INVALID_SERVER_HASH")
    if not isinstance(model_sha256, str) or HEX64.fullmatch(model_sha256) is None:
        raise QualificationError("INVALID_MODEL_HASH")

    out_dir = _new_output_dir(out_dir)
    enrollment, implementation_sha256, source_hashes = _load_enrollment(
        Path(enrollment_path)
    )
    profile_identity = _verify_profile_files(Path(hermes_home), enrollment)
    base_env = dict(os.environ if env is None else env)
    version = _version_probe(Path(hermes), Path(hermes_home), enrollment, base_env)
    _verify_profile_files(Path(hermes_home), enrollment)

    case = make_case(family, seed)
    # Pinned Hermes only creates mcp-<server> aliases after >=1 tool registers.
    # A true zero-tool HRF case therefore uses an empty CLI toolset selection,
    # which falls back to the enrolled profile's platform_toolsets.cli: [].
    # Exact zero is still proved by the captured first model request below.
    effective_toolsets = toolsets if case.tool_policy.allowed_tools else ""
    fixture = fixture_for_case(case)
    fixture_path = out_dir / "discovery-fixture.json"
    _write_private_json(fixture_path, fixture)
    discovery_log = out_dir / "discovery-mcp-calls.jsonl"

    deny_model = out_dir / "discovery-model-scope.json"
    deny_raw = out_dir / "discovery-raw-mcp-scope.json"
    deny_model_sha = _write_policy(deny_model, _deny_all_policy())
    deny_raw_sha = _write_policy(deny_raw, _deny_all_policy())
    discovery_env = _fixture_env(
        base_env, hermes_home, fixture_path, discovery_log,
        deny_model, deny_raw, raw_guard=False,
    )

    discovery_preflight = hermes_plugin_preflight.run_preflight(
        **_preflight_args(
            enrollment, hermes, hermes_home, deny_model, deny_model_sha,
            deny_raw, deny_raw_sha,
        ),
        env=discovery_env,
    )
    _write_private_json(out_dir / "discovery-preflight.json", discovery_preflight)
    if discovery_preflight.get("status") != "pass":
        raise QualificationError("DISCOVERY_PREFLIGHT_BLOCKED")

    discovery = tool_visibility.run_probe(
        str(hermes), str(hermes_home), effective_toolsets, [],
        timeout=60, env=discovery_env,
        expected_tool_count=len(case.tool_policy.allowed_tools),
    )
    _write_private_json(out_dir / "surface-discovery.json", discovery)
    _verify_profile_files(Path(hermes_home), enrollment)
    if discovery.get("status") != "pass":
        raise QualificationError("SURFACE_DISCOVERY_BLOCKED")
    names = discovery.get("tool_names")
    if not isinstance(names, list):
        raise QualificationError("SURFACE_DISCOVERY_INVALID")

    model_policy_value = _model_policy(case, fixture, names)
    raw_policy_value = _mcp_scope_policy(case, fixture)
    model_policy = out_dir / "model-scope.json"
    raw_policy = out_dir / "raw-mcp-scope.json"
    model_policy_sha = _write_policy(model_policy, model_policy_value)
    raw_policy_sha = _write_policy(raw_policy, raw_policy_value)

    guarded_env = _fixture_env(
        base_env, hermes_home, fixture_path, out_dir / "replay-mcp-calls.jsonl",
        model_policy, raw_policy, raw_guard=True,
    )
    preflight_args = _preflight_args(
        enrollment, hermes, hermes_home, model_policy, model_policy_sha,
        raw_policy, raw_policy_sha,
    )
    preflight = hermes_plugin_preflight.run_preflight(
        **preflight_args, env=guarded_env
    )
    _write_private_json(out_dir / "preflight.json", preflight)
    _verify_profile_files(Path(hermes_home), enrollment)
    if preflight.get("status") != "pass":
        raise QualificationError("CASE_PREFLIGHT_BLOCKED")

    replay = tool_visibility.run_probe(
        str(hermes), str(hermes_home), effective_toolsets, [],
        timeout=60, env=guarded_env,
        expected_names=names,
        expected_surface_sha256=discovery.get("tool_surface_sha256"),
        expected_tool_count=len(names),
    )
    _write_private_json(out_dir / "surface-replay.json", replay)
    _verify_profile_files(Path(hermes_home), enrollment)
    if replay.get("status") != "pass":
        raise QualificationError("SURFACE_REPLAY_BLOCKED")

    red_out = out_dir / "red-run.json"
    guarded_command = [
        sys.executable, str(RED / "hermes_runner.py"),
        "--hermes", str(hermes),
        "--hermes-home", str(hermes_home),
        "--toolsets", effective_toolsets,
        "--base-url", f"http://127.0.0.1:{port}/v1",
        "--model", alias,
        "--seeds", str(seed),
        "--families", family,
        "--timeout", str(timeout_seconds),
        "--max-turns", str(max_turns),
        "--final-mcp-policy", str(raw_policy),
        "--final-mcp-policy-sha256", raw_policy_sha,
        "--out", str(red_out),
    ]
    _verify_profile_files(Path(hermes_home), enrollment)
    supervisor, child_rc = guarded_model_supervisor.run_supervisor(
        plugin_args=preflight_args,
        owned_llama=AUG / "owned_llama.py",
        owned_llama_sha256=enrollment["owned_llama_sha256"],
        observe_llama_sha256=enrollment["observe_llama_sha256"],
        model_preflight_sha256=enrollment["model_preflight_sha256"],
        server=Path(server),
        server_sha256=server_sha256,
        model=Path(model),
        model_sha256=model_sha256,
        alias=alias,
        port=port,
        context=context,
        guarded_command=guarded_command,
        start_timeout=start_timeout,
        server_log=out_dir / "llama-server.log",
        env=base_env,
    )
    _write_private_json(out_dir / "supervisor.json", supervisor)
    _verify_profile_files(Path(hermes_home), enrollment)
    if supervisor.get("plugin_preflight_sha256") != _preflight_hash(preflight):
        raise QualificationError("SUPERVISOR_PREFLIGHT_BINDING_MISMATCH")
    if supervisor.get("status") != "pass" or child_rc != 0:
        raise QualificationError("SUPERVISOR_OR_CHILD_BLOCKED")

    red_run = _read_private_json(red_out)
    if (red_run.get("status") != "pass"
            or red_run.get("n") != 1
            or not isinstance(red_run.get("results"), list)
            or len(red_run["results"]) != 1):
        raise QualificationError("RED_HARNESS_BLOCKED")
    result = red_run["results"][0]
    expected_surface = (
        {} if not names else {"read_fixture": names[0]}
    )
    if (result.get("case_id") != case.case_id
            or result.get("fixture_tool_names") != expected_surface
            or result.get("final_mcp_policy_sha256") != raw_policy_sha
            or result.get("final_mcp_policy_bound_by_parent") is not True):
        raise QualificationError("RED_BINDING_MISMATCH")

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "classification": "development",
        "status": "pass",
        "errors": [],
        "case_id": case.case_id,
        "family": family,
        "seed": seed,
        "model_alias": alias,
        "context_tokens": context,
        "effective_toolsets": effective_toolsets,
        "hermes": version,
        "enrollment_sha256": hashlib.sha256(
            _canon(enrollment)
        ).hexdigest(),
        "tool_implementation_sha256": implementation_sha256,
        "source_hashes": source_hashes,
        "hermes_profile": profile_identity,
        "surface_discovery": discovery,
        "surface_replay": replay,
        "model_scope_policy_sha256": model_policy_sha,
        "final_dispatch_policy_sha256": raw_policy_sha,
        "guard_preflight": preflight,
        "guard_supervisor": supervisor,
        "red_run_sha256": red_run.get("run_sha256"),
        "red_result_sha256": result.get("result_sha256"),
        "model_behavior_pass": (
            result.get("score", {}).get("pass")
            if isinstance(result.get("score"), dict) else None
        ),
        "execution_protection_pass": (
            result.get("execution_score", {}).get("pass")
            if isinstance(result.get("execution_score"), dict) else None
        ),
        "server_sha256": server_sha256,
        "model_artifact_sha256": model_sha256,
    }
    receipt["receipt_sha256"] = hashlib.sha256(_canon(receipt)).hexdigest()
    _write_private_json(out_dir / "qualification.json", receipt)
    return receipt


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--hermes", type=Path, required=True)
    p.add_argument("--hermes-home", type=Path, required=True)
    p.add_argument("--toolsets", required=True)
    p.add_argument("--server", type=Path, required=True)
    p.add_argument("--server-sha256", required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--model-sha256", required=True)
    p.add_argument("--alias", required=True)
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--context", type=int, default=65536)
    p.add_argument("--family", choices=sorted(FAMILIES), required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--enrollment", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--max-turns", type=int, default=8)
    p.add_argument("--start-timeout", type=float, default=120.0)
    args = p.parse_args(argv)
    result = run_case_qualification(
        hermes=args.hermes,
        hermes_home=args.hermes_home,
        toolsets=args.toolsets,
        server=args.server,
        server_sha256=args.server_sha256,
        model=args.model,
        model_sha256=args.model_sha256,
        alias=args.alias,
        port=args.port,
        context=args.context,
        family=args.family,
        seed=args.seed,
        enrollment_path=args.enrollment,
        out_dir=args.out_dir,
        timeout_seconds=args.timeout,
        max_turns=args.max_turns,
        start_timeout=args.start_timeout,
    )
    print(json.dumps({
        "schema": result["schema"],
        "status": result["status"],
        "case_id": result["case_id"],
        "family": result["family"],
        "receipt_sha256": result["receipt_sha256"],
        "model_behavior_pass": result["model_behavior_pass"],
        "execution_protection_pass": result["execution_protection_pass"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
