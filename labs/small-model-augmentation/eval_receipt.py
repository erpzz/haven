"""Host-owned private receipt binding for controlled augmentation evaluation.

The public sidecar intentionally contains only aggregate counters and a receipt SHA-256.
This module defines what that private receipt must bind and derives the public row from
it. Raw prompts, model output, gold answers, credentials, and host inventory are not
part of the receipt schema.

A receipt is one arm/case execution. It binds:
- the exact public evaluation manifest identity/settings;
- #127 admission;
- #129 model-visible tool policy;
- #199 guarded-Hermes preflight/supervisor receipts and raw final-dispatch policy;
- #131 catalogue/selection;
- #132 claim bundle/policy/renderer;
- #130 run manifest;
- MCP/tool implementation revision;
- fixed host-instrumentation source receipt hashes and their derived counters.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import stat
from pathlib import Path
from typing import Any, Mapping, Sequence

import augmentation_eval

SCHEMA = "haven.augmentation-eval-private-receipt.v2"
MAX_RECEIPT_BYTES = 1024 * 1024
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
TOKEN = re.compile(r"[A-Za-z0-9_.:@/+ -]{1,256}\Z", re.ASCII)

MANIFEST_BINDING_KEYS = {
    "experiment", "comparison_group", "arm", "dataset_id", "dataset_sha256",
    "model_id", "model_artifact_sha256", "engine", "hardware", "temperature",
    "max_tokens", "code_sha256", "grader_sha256", "reserve",
}
CONTROL_KEYS = {
    "admission_receipt_sha256",
    "guard_preflight_receipt_sha256",
    "guard_supervisor_receipt_sha256",
    "runtime_profile_sha256",
    "request_settings_sha256",
    "world_sha256",
    "tool_policy_sha256",
    "final_dispatch_policy_sha256",
    "catalog_sha256",
    "selection_receipt_sha256",
    "claim_bundle_sha256",
    "claim_policy_sha256",
    "renderer_sha256",
    "run_manifest_sha256",
    "tool_implementation_sha256",
}
SOURCE_KEYS = {"grader", "dispatcher", "observer", "verifier", "recovery", "backend"}
PROFILE_KEYS = {"runtime", "request"}
GUARD_KEYS = {"preflight", "supervisor"}
GUARD_PREFLIGHT_SCHEMA = "haven.hermes-plugin-preflight.v1"
GUARD_SUPERVISOR_SCHEMA = "haven.guarded-local-model-supervisor.v1"
GUARD_PREFLIGHT_KEYS = {
    "schema", "status", "errors", "hermes_sha256", "plugin_init_sha256",
    "plugin_manifest_sha256", "scope_engine_sha256", "scope_policy_sha256",
    "mcp_policy_sha256", "scope_policy_tool_count", "mcp_policy_tool_count",
    "enabled_user_plugin_count", "doctor_passed",
}
GUARD_SUPERVISOR_KEYS = {
    "schema", "status", "errors", "plugin_preflight_sha256",
    "owned_llama_sha256", "observe_llama_sha256", "model_preflight_sha256",
    "owned_llama_started", "owned_llama_exit",
}
RUNTIME_PROFILE_KEYS = {
    "hermes_sha256", "server_sha256", "model_artifact_sha256",
    "model_alias", "context_tokens", "provider", "ownership",
}
REQUEST_PROFILE_KEYS = {
    "temperature", "max_tokens", "request_seed", "max_turns", "stream",
}
MIN_CONTEXT_TOKENS = 64_000
SOURCE_FIELDS = {
    "grader": {"receipt_sha256", "semantic_pass"},
    "dispatcher": {
        "receipt_sha256", "unauthorized_attempts", "unblocked_unauthorized",
        "tool_calls", "blocked_calls",
    },
    "observer": {"receipt_sha256", "external_effects"},
    "verifier": {
        "receipt_sha256", "verification_failures", "claim_release_failures",
    },
    "recovery": {
        "receipt_sha256", "recovery_failures", "nonreplayable_replays",
    },
    "backend": {
        "receipt_sha256", "schema_bytes", "prompt_tokens",
        "completion_tokens", "latency_ms",
    },
}
ALWAYS_MATCH_CONTROLS = {
    "runtime_profile_sha256",
    "request_settings_sha256",
    "world_sha256",
    "catalog_sha256",
    "tool_implementation_sha256",
}
PRIVATE_COMPARE_SCHEMA = "haven.augmentation-eval-private-compare.v1"

RECEIPT_KEYS = {
    "schema", "manifest", "case_id", "family", "profiles", "guard", "controls",
    "sources", "receipt_sha256",
}


class ReceiptError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise ReceiptError("value is not canonical JSON") from exc


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _valid_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and HEX64.fullmatch(value) is not None
        and value != "0" * 64
    )


def _valid_token(value: Any) -> bool:
    return isinstance(value, str) and TOKEN.fullmatch(value) is not None


def _nonneg(value: Any) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 0 <= value <= 2**63 - 1
    )


def _manifest_binding(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        raise ReceiptError("manifest must be an object")
    if set(manifest) != augmentation_eval.MANIFEST_KEYS:
        raise ReceiptError("manifest shape does not match sidecar")
    # Reuse the sidecar's own validator by supplying one structurally valid dummy row.
    dummy = {
        "case_id": "receipt-preflight",
        "family": "receipt-preflight",
        "semantic_pass": False,
        "unauthorized_attempts": 0,
        "unblocked_unauthorized": 0,
        "external_effects": 0,
        "verification_failures": 0,
        "claim_release_failures": 0,
        "recovery_failures": 0,
        "nonreplayable_replays": 0,
        "tool_calls": 0,
        "blocked_calls": 0,
        "schema_bytes": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "latency_ms": 0,
        "receipt_sha256": "1" * 64,
    }
    errors = augmentation_eval.validate({"manifest": dict(manifest), "rows": [dummy]})
    if errors:
        raise ReceiptError("invalid sidecar manifest: " + ",".join(errors))
    if manifest.get("reserve") is not False:
        raise ReceiptError("reserve reports are forbidden")
    return {key: copy.deepcopy(manifest[key]) for key in sorted(MANIFEST_BINDING_KEYS)}


def _validate_profiles(
    manifest: Mapping[str, Any], profiles: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    if not isinstance(profiles, Mapping) or set(profiles) != PROFILE_KEYS:
        raise ReceiptError("invalid private profile shape")

    runtime = profiles["runtime"]
    request = profiles["request"]
    if not isinstance(runtime, Mapping) or set(runtime) != RUNTIME_PROFILE_KEYS:
        raise ReceiptError("invalid runtime profile shape")
    if not isinstance(request, Mapping) or set(request) != REQUEST_PROFILE_KEYS:
        raise ReceiptError("invalid request profile shape")

    runtime = copy.deepcopy(dict(runtime))
    request = copy.deepcopy(dict(request))

    for key in ("hermes_sha256", "server_sha256", "model_artifact_sha256"):
        if not _valid_hash(runtime.get(key)):
            raise ReceiptError(f"invalid runtime hash: {key}")
    if runtime["model_artifact_sha256"] != manifest["model_artifact_sha256"]:
        raise ReceiptError("runtime model artifact does not match public manifest")
    if not _valid_token(runtime.get("model_alias")):
        raise ReceiptError("invalid runtime model alias")
    if runtime["model_alias"] != manifest["model_id"]:
        raise ReceiptError("runtime model alias does not match public model_id")
    context = runtime.get("context_tokens")
    if (
        isinstance(context, bool)
        or not isinstance(context, int)
        or context < MIN_CONTEXT_TOKENS
        or context > 10_000_000
    ):
        raise ReceiptError("invalid runtime context")
    if not _valid_token(runtime.get("provider")):
        raise ReceiptError("invalid runtime provider")
    if runtime.get("ownership") != "owned-loopback":
        raise ReceiptError("runtime ownership must be owned-loopback")

    temperature = request.get("temperature")
    if (
        isinstance(temperature, bool)
        or not isinstance(temperature, (int, float))
        or not math.isfinite(float(temperature))
        or float(temperature) != float(manifest["temperature"])
    ):
        raise ReceiptError("request temperature does not match public manifest")
    max_tokens = request.get("max_tokens")
    if (
        isinstance(max_tokens, bool)
        or not isinstance(max_tokens, int)
        or max_tokens != manifest["max_tokens"]
    ):
        raise ReceiptError("request max_tokens does not match public manifest")
    seed = request.get("request_seed")
    if (
        isinstance(seed, bool)
        or not isinstance(seed, int)
        or not 0 <= seed <= 2**31 - 1
    ):
        raise ReceiptError("invalid request seed")
    max_turns = request.get("max_turns")
    if (
        isinstance(max_turns, bool)
        or not isinstance(max_turns, int)
        or not 1 <= max_turns <= 100
    ):
        raise ReceiptError("invalid max_turns")
    if type(request.get("stream")) is not bool:
        raise ReceiptError("invalid stream flag")
    return {"runtime": runtime, "request": request}


def _validate_guard(guard: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(guard, Mapping) or set(guard) != GUARD_KEYS:
        raise ReceiptError("invalid guard binding shape")
    preflight = guard["preflight"]
    supervisor = guard["supervisor"]
    if not isinstance(preflight, Mapping) or set(preflight) != GUARD_PREFLIGHT_KEYS:
        raise ReceiptError("invalid guard preflight shape")
    if not isinstance(supervisor, Mapping) or set(supervisor) != GUARD_SUPERVISOR_KEYS:
        raise ReceiptError("invalid guard supervisor shape")

    preflight = copy.deepcopy(dict(preflight))
    supervisor = copy.deepcopy(dict(supervisor))
    if preflight.get("schema") != GUARD_PREFLIGHT_SCHEMA:
        raise ReceiptError("invalid guard preflight schema")
    if preflight.get("status") != "pass" or preflight.get("errors") != []:
        raise ReceiptError("guard preflight did not pass")
    if preflight.get("doctor_passed") is not True:
        raise ReceiptError("guard plugin doctor did not pass")
    for key in (
        "hermes_sha256", "plugin_init_sha256", "plugin_manifest_sha256",
        "scope_engine_sha256", "scope_policy_sha256", "mcp_policy_sha256",
    ):
        if not _valid_hash(preflight.get(key)):
            raise ReceiptError(f"invalid guard preflight hash: {key}")
    for key in (
        "scope_policy_tool_count", "mcp_policy_tool_count",
        "enabled_user_plugin_count",
    ):
        if not _nonneg(preflight.get(key)):
            raise ReceiptError(f"invalid guard preflight count: {key}")
    if preflight["enabled_user_plugin_count"] < 1:
        raise ReceiptError("guard scope plugin was not enabled")

    if supervisor.get("schema") != GUARD_SUPERVISOR_SCHEMA:
        raise ReceiptError("invalid guard supervisor schema")
    if supervisor.get("status") != "pass" or supervisor.get("errors") != []:
        raise ReceiptError("guard supervisor did not pass")
    if supervisor.get("owned_llama_started") is not True:
        raise ReceiptError("owned llama was not started by guard supervisor")
    if supervisor.get("owned_llama_exit") != 0:
        raise ReceiptError("guarded owned llama did not exit cleanly")
    for key in (
        "plugin_preflight_sha256", "owned_llama_sha256",
        "observe_llama_sha256", "model_preflight_sha256",
    ):
        if not _valid_hash(supervisor.get(key)):
            raise ReceiptError(f"invalid guard supervisor hash: {key}")
    if supervisor["plugin_preflight_sha256"] != _sha(preflight):
        raise ReceiptError("guard supervisor preflight hash mismatch")
    return {"preflight": preflight, "supervisor": supervisor}


def _validate_controls(controls: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(controls, Mapping) or set(controls) != CONTROL_KEYS:
        raise ReceiptError("invalid control binding shape")
    out = {}
    for key in sorted(CONTROL_KEYS):
        value = controls[key]
        if not _valid_hash(value):
            raise ReceiptError(f"invalid control hash: {key}")
        out[key] = value
    return out


def _validate_sources(sources: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(sources, Mapping) or set(sources) != SOURCE_KEYS:
        raise ReceiptError("invalid source binding shape")
    out: dict[str, dict[str, Any]] = {}
    for source in sorted(SOURCE_KEYS):
        value = sources[source]
        expected = SOURCE_FIELDS[source]
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ReceiptError(f"invalid source shape: {source}")
        row = copy.deepcopy(dict(value))
        if not _valid_hash(row.get("receipt_sha256")):
            raise ReceiptError(f"invalid source receipt hash: {source}")
        for key, item in row.items():
            if key == "receipt_sha256":
                continue
            if key == "semantic_pass":
                if type(item) is not bool:
                    raise ReceiptError("semantic_pass must be boolean")
            elif not _nonneg(item):
                raise ReceiptError(f"invalid nonnegative metric: {source}.{key}")
        out[source] = row

    source_hashes = [out[source]["receipt_sha256"] for source in sorted(SOURCE_KEYS)]
    if len(source_hashes) != len(set(source_hashes)):
        raise ReceiptError("host source receipt hashes must be distinct")

    dispatcher = out["dispatcher"]
    if dispatcher["blocked_calls"] > dispatcher["tool_calls"]:
        raise ReceiptError("blocked_calls exceeds tool_calls")
    if dispatcher["unauthorized_attempts"] > dispatcher["tool_calls"]:
        raise ReceiptError("unauthorized_attempts exceeds tool_calls")
    if dispatcher["unblocked_unauthorized"] > dispatcher["unauthorized_attempts"]:
        raise ReceiptError("unblocked_unauthorized exceeds unauthorized_attempts")
    return out


def profile_sha256(private_profile: Mapping[str, Any]) -> str:
    """Hash a private stable runtime/settings/world profile without publishing it."""
    if not isinstance(private_profile, Mapping) or not private_profile:
        raise ReceiptError("profile must be a non-empty object")
    digest = _sha(dict(private_profile))
    if digest == "0" * 64:
        raise ReceiptError("invalid profile hash")
    return digest


def make_receipt(
    *,
    manifest: Mapping[str, Any],
    case_id: str,
    family: str,
    profiles: Mapping[str, Any],
    guard: Mapping[str, Any],
    controls: Mapping[str, Any],
    sources: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a canonical private receipt for one arm/case."""
    if not _valid_token(case_id) or not _valid_token(family):
        raise ReceiptError("invalid case/family token")
    manifest_binding = _manifest_binding(manifest)
    private_profiles = _validate_profiles(manifest_binding, profiles)
    guard_binding = _validate_guard(guard)
    control_bindings = _validate_controls(controls)
    if guard_binding["preflight"]["hermes_sha256"] != private_profiles["runtime"]["hermes_sha256"]:
        raise ReceiptError("guard/runtime Hermes hash mismatch")
    guard_preflight_hash = _sha(guard_binding["preflight"])
    guard_supervisor_hash = _sha(guard_binding["supervisor"])
    if control_bindings["guard_preflight_receipt_sha256"] != guard_preflight_hash:
        raise ReceiptError("guard preflight control hash mismatch")
    if control_bindings["guard_supervisor_receipt_sha256"] != guard_supervisor_hash:
        raise ReceiptError("guard supervisor control hash mismatch")
    if control_bindings["tool_policy_sha256"] != guard_binding["preflight"]["scope_policy_sha256"]:
        raise ReceiptError("model-side scope policy hash mismatch")
    if control_bindings["final_dispatch_policy_sha256"] != guard_binding["preflight"]["mcp_policy_sha256"]:
        raise ReceiptError("final-dispatch policy hash mismatch")
    if control_bindings["runtime_profile_sha256"] != profile_sha256(
        private_profiles["runtime"]
    ):
        raise ReceiptError("runtime profile hash mismatch")
    if control_bindings["request_settings_sha256"] != profile_sha256(
        private_profiles["request"]
    ):
        raise ReceiptError("request settings hash mismatch")
    body = {
        "schema": SCHEMA,
        "manifest": manifest_binding,
        "case_id": case_id,
        "family": family,
        "profiles": private_profiles,
        "guard": guard_binding,
        "controls": control_bindings,
        "sources": _validate_sources(sources),
    }
    body["receipt_sha256"] = _sha(body)
    return body


def validate_receipt(receipt: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(receipt, Mapping) or set(receipt) != RECEIPT_KEYS:
        return ["INVALID_RECEIPT_SHAPE"]
    if receipt.get("schema") != SCHEMA:
        errors.append("INVALID_RECEIPT_SCHEMA")
    try:
        manifest = receipt.get("manifest")
        if not isinstance(manifest, Mapping) or set(manifest) != MANIFEST_BINDING_KEYS:
            raise ReceiptError("invalid manifest binding shape")
        # Reconstruct a full sidecar manifest by adding the public schema.
        full_manifest = {"schema": augmentation_eval.SCHEMA, **dict(manifest)}
        _manifest_binding(full_manifest)
    except ReceiptError:
        errors.append("INVALID_MANIFEST_BINDING")

    if not _valid_token(receipt.get("case_id")) or not _valid_token(receipt.get("family")):
        errors.append("INVALID_CASE_IDENTITY")
    manifest_binding = receipt.get("manifest")
    try:
        profiles = _validate_profiles(manifest_binding, receipt.get("profiles"))
    except ReceiptError:
        profiles = None
        errors.append("INVALID_PRIVATE_PROFILES")
    try:
        guard = _validate_guard(receipt.get("guard"))
    except ReceiptError:
        guard = None
        errors.append("INVALID_GUARD_BINDING")
    try:
        controls = _validate_controls(receipt.get("controls"))
    except ReceiptError:
        controls = None
        errors.append("INVALID_CONTROL_BINDINGS")
    if profiles is not None and guard is not None:
        if guard["preflight"]["hermes_sha256"] != profiles["runtime"]["hermes_sha256"]:
            errors.append("GUARD_RUNTIME_HERMES_MISMATCH")
    if guard is not None and controls is not None:
        if controls["guard_preflight_receipt_sha256"] != _sha(guard["preflight"]):
            errors.append("GUARD_PREFLIGHT_HASH_MISMATCH")
        if controls["guard_supervisor_receipt_sha256"] != _sha(guard["supervisor"]):
            errors.append("GUARD_SUPERVISOR_HASH_MISMATCH")
        if controls["tool_policy_sha256"] != guard["preflight"]["scope_policy_sha256"]:
            errors.append("MODEL_SCOPE_POLICY_HASH_MISMATCH")
        if controls["final_dispatch_policy_sha256"] != guard["preflight"]["mcp_policy_sha256"]:
            errors.append("FINAL_DISPATCH_POLICY_HASH_MISMATCH")
    if profiles is not None and controls is not None:
        if controls["runtime_profile_sha256"] != profile_sha256(profiles["runtime"]):
            errors.append("RUNTIME_PROFILE_HASH_MISMATCH")
        if controls["request_settings_sha256"] != profile_sha256(profiles["request"]):
            errors.append("REQUEST_PROFILE_HASH_MISMATCH")
    try:
        _validate_sources(receipt.get("sources"))
    except ReceiptError:
        errors.append("INVALID_SOURCE_BINDINGS")

    claimed = receipt.get("receipt_sha256")
    if not _valid_hash(claimed):
        errors.append("INVALID_RECEIPT_HASH")
    else:
        body = copy.deepcopy(dict(receipt))
        body.pop("receipt_sha256", None)
        try:
            actual = _sha(body)
        except ReceiptError:
            errors.append("INVALID_RECEIPT_JSON")
        else:
            if claimed != actual:
                errors.append("RECEIPT_HASH_MISMATCH")
    return sorted(set(errors))


def row_from_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    errors = validate_receipt(receipt)
    if errors:
        raise ReceiptError(",".join(errors))
    s = receipt["sources"]
    return {
        "case_id": receipt["case_id"],
        "family": receipt["family"],
        "semantic_pass": s["grader"]["semantic_pass"],
        "unauthorized_attempts": s["dispatcher"]["unauthorized_attempts"],
        "unblocked_unauthorized": s["dispatcher"]["unblocked_unauthorized"],
        "external_effects": s["observer"]["external_effects"],
        "verification_failures": s["verifier"]["verification_failures"],
        "claim_release_failures": s["verifier"]["claim_release_failures"],
        "recovery_failures": s["recovery"]["recovery_failures"],
        "nonreplayable_replays": s["recovery"]["nonreplayable_replays"],
        "tool_calls": s["dispatcher"]["tool_calls"],
        "blocked_calls": s["dispatcher"]["blocked_calls"],
        "schema_bytes": s["backend"]["schema_bytes"],
        "prompt_tokens": s["backend"]["prompt_tokens"],
        "completion_tokens": s["backend"]["completion_tokens"],
        "latency_ms": s["backend"]["latency_ms"],
        "receipt_sha256": receipt["receipt_sha256"],
    }


def _manifest_matches(receipt: Mapping[str, Any], manifest: Mapping[str, Any]) -> bool:
    expected = _manifest_binding(manifest)
    return dict(receipt.get("manifest", {})) == expected


def report_from_receipts(
    manifest: Mapping[str, Any], receipts: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Derive one public sidecar arm report from private host-owned receipts."""
    public_manifest = copy.deepcopy(dict(manifest))
    _manifest_binding(public_manifest)
    if not isinstance(receipts, Sequence) or not receipts:
        raise ReceiptError("receipt set must be non-empty")

    rows = []
    hashes = set()
    cases = set()
    for receipt in receipts:
        errors = validate_receipt(receipt)
        if errors:
            raise ReceiptError("invalid receipt: " + ",".join(errors))
        if not _manifest_matches(receipt, public_manifest):
            raise ReceiptError("receipt manifest does not match report manifest")
        digest = receipt["receipt_sha256"]
        if digest in hashes:
            raise ReceiptError("duplicate private receipt")
        hashes.add(digest)
        case_id = receipt["case_id"]
        if case_id in cases:
            raise ReceiptError("duplicate case receipt")
        cases.add(case_id)
        rows.append(row_from_receipt(receipt))

    report = {"manifest": public_manifest, "rows": rows}
    errors = augmentation_eval.validate(report)
    if errors:
        raise ReceiptError("derived public report invalid: " + ",".join(errors))
    return report


def compare_private_receipt_sets(
    a_receipts: Sequence[Mapping[str, Any]],
    b_receipts: Sequence[Mapping[str, Any]],
    *,
    allowed_control_differences: Sequence[str] = (),
) -> dict[str, Any]:
    """Preflight matched arms before producing/accepting the public comparison.

    Stable runtime/settings/world/catalog/tool-implementation identities can never be
    waived. The tool-implementation identity must cover the complete enforcement
    implementation used for the run, including the #199 guard/plugin/final-dispatch
    code when that stack is active. Other control bindings may differ only when the
    caller explicitly names them as the experiment's intended manipulation.
    """
    if not isinstance(allowed_control_differences, Sequence) or isinstance(
        allowed_control_differences, (str, bytes)
    ):
        return {
            "schema": PRIVATE_COMPARE_SCHEMA,
            "status": "block",
            "errors": ["INVALID_ALLOWED_CONTROL_DIFFERENCES"],
        }
    allowed = list(allowed_control_differences)
    if (
        len(allowed) != len(set(allowed))
        or any(key not in CONTROL_KEYS for key in allowed)
        or set(allowed) & ALWAYS_MATCH_CONTROLS
    ):
        return {
            "schema": PRIVATE_COMPARE_SCHEMA,
            "status": "block",
            "errors": ["INVALID_ALLOWED_CONTROL_DIFFERENCES"],
        }

    for label, rows in (("A", a_receipts), ("B", b_receipts)):
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
            return {
                "schema": PRIVATE_COMPARE_SCHEMA,
                "status": "block",
                "errors": [f"{label}:INVALID_RECEIPT_SET"],
            }
        for value in rows:
            errors = validate_receipt(value)
            if errors:
                return {
                    "schema": PRIVATE_COMPARE_SCHEMA,
                    "status": "block",
                    "errors": [f"{label}:{error}" for error in errors],
                }

    a_by_case = {r["case_id"]: r for r in a_receipts}
    b_by_case = {r["case_id"]: r for r in b_receipts}
    if len(a_by_case) != len(a_receipts) or len(b_by_case) != len(b_receipts):
        return {
            "schema": PRIVATE_COMPARE_SCHEMA,
            "status": "block",
            "errors": ["DUPLICATE_CASE_ID"],
        }
    if set(a_by_case) != set(b_by_case):
        return {
            "schema": PRIVATE_COMPARE_SCHEMA,
            "status": "block",
            "errors": ["CASE_SET_MISMATCH"],
        }

    # Sidecar public match fields must match at the private receipt layer too.
    first_a = next(iter(a_by_case.values()))
    first_b = next(iter(b_by_case.values()))
    public_mismatch = sorted(
        key for key in augmentation_eval.MATCH_FIELDS
        if first_a["manifest"].get(key) != first_b["manifest"].get(key)
    )
    if public_mismatch:
        return {
            "schema": PRIVATE_COMPARE_SCHEMA,
            "status": "block",
            "errors": ["MANIFEST_MISMATCH"],
            "mismatched_fields": public_mismatch,
        }
    if first_a["manifest"]["arm"] == first_b["manifest"]["arm"]:
        return {
            "schema": PRIVATE_COMPARE_SCHEMA,
            "status": "block",
            "errors": ["ARMS_NOT_DISTINCT"],
        }

    observed = set()
    disallowed = set()
    family_mismatch = 0
    reused_receipts = 0
    for case_id in sorted(a_by_case):
        a = a_by_case[case_id]
        b = b_by_case[case_id]
        if a["family"] != b["family"]:
            family_mismatch += 1
        if a["receipt_sha256"] == b["receipt_sha256"]:
            reused_receipts += 1
        for key in CONTROL_KEYS:
            if a["controls"][key] != b["controls"][key]:
                observed.add(key)
                if key not in allowed:
                    disallowed.add(key)

    errors = []
    if family_mismatch:
        errors.append("FAMILY_MISMATCH")
    if reused_receipts:
        errors.append("CROSS_ARM_RECEIPT_REUSE")
    if disallowed:
        errors.append("CONTROL_BINDING_MISMATCH")
    return {
        "schema": PRIVATE_COMPARE_SCHEMA,
        "status": "block" if errors else "pass",
        "errors": errors,
        "cases": len(a_by_case),
        "allowed_control_differences": sorted(allowed),
        "observed_control_differences": sorted(observed),
        "disallowed_control_differences": sorted(disallowed),
        "family_mismatch_count": family_mismatch,
        "reused_receipt_count": reused_receipts,
    }


def write_private_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    """Create one new private receipt file, never overwriting an existing path."""
    errors = validate_receipt(receipt)
    if errors:
        raise ReceiptError(",".join(errors))
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise ReceiptError("private receipt path already exists")
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise ReceiptError("private receipt parent must be an existing non-symlink directory")
    raw = _canon(dict(receipt)) + b"\n"
    if len(raw) > MAX_RECEIPT_BYTES:
        raise ReceiptError("private receipt too large")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=True) as writer:
            writer.write(raw)
            writer.flush()
            os.fsync(writer.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def load_private_receipt(path: Path) -> dict[str, Any]:
    """Read only a private regular file; reject symlinks and broad permissions."""
    path = Path(path)
    try:
        st = path.lstat()
    except OSError as exc:
        raise ReceiptError("private receipt read failed") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise ReceiptError("private receipt must be a regular non-symlink file")
    if st.st_mode & 0o077:
        raise ReceiptError("private receipt permissions must be 0600-like")
    if st.st_size > MAX_RECEIPT_BYTES:
        raise ReceiptError("private receipt too large")
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError("invalid private receipt file") from exc
    errors = validate_receipt(value)
    if errors:
        raise ReceiptError(",".join(errors))
    return value


def _load_public_manifest(path: Path) -> dict[str, Any]:
    path = Path(path)
    try:
        st = path.lstat()
    except OSError as exc:
        raise ReceiptError("manifest read failed") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode) or st.st_size > 256 * 1024:
        raise ReceiptError("manifest must be a bounded regular non-symlink file")

    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("duplicate JSON key")
            out[key] = value
        return out

    def reject(_):
        raise ValueError("nonfinite")

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=unique,
            parse_constant=reject,
        )
    except (OSError, UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise ReceiptError("invalid manifest JSON") from exc
    _manifest_binding(value)
    return value


def _write_new_json(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise ReceiptError("output path already exists")
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise ReceiptError("output parent must be an existing non-symlink directory")
    raw = _canon(dict(value)) + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=True) as writer:
            writer.write(raw)
            writer.flush()
            os.fsync(writer.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    validate_cmd = sub.add_parser("validate-receipt")
    validate_cmd.add_argument("receipt", type=Path)

    report_cmd = sub.add_parser("build-report")
    report_cmd.add_argument("--manifest", type=Path, required=True)
    report_cmd.add_argument("--receipt", type=Path, action="append", required=True)
    report_cmd.add_argument("--out", type=Path, required=True)

    compare_cmd = sub.add_parser("compare-private")
    compare_cmd.add_argument("--a", type=Path, action="append", required=True)
    compare_cmd.add_argument("--b", type=Path, action="append", required=True)
    compare_cmd.add_argument(
        "--allow-control-difference", action="append", default=[]
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "validate-receipt":
            value = load_private_receipt(args.receipt)
            out = {
                "schema": SCHEMA,
                "status": "pass",
                "receipt_sha256": value["receipt_sha256"],
                "case_id": value["case_id"],
                "arm": value["manifest"]["arm"],
            }
        elif args.command == "build-report":
            manifest = _load_public_manifest(args.manifest)
            receipts = [load_private_receipt(path) for path in args.receipt]
            report = report_from_receipts(manifest, receipts)
            _write_new_json(args.out, report)
            out = {
                "schema": augmentation_eval.SCHEMA,
                "status": "pass",
                "arm": manifest["arm"],
                "cases": len(report["rows"]),
                "report_sha256": augmentation_eval.report_sha256(report),
                "out": str(args.out),
            }
        else:
            a = [load_private_receipt(path) for path in args.a]
            b = [load_private_receipt(path) for path in args.b]
            out = compare_private_receipt_sets(
                a, b,
                allowed_control_differences=args.allow_control_difference,
            )
            if out["status"] != "pass":
                print(json.dumps(out, sort_keys=True))
                return 2
    except ReceiptError as exc:
        out = {
            "schema": SCHEMA,
            "status": "block",
            "error": str(exc),
        }
        print(json.dumps(out, sort_keys=True))
        return 2
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
