"""Host-owned private receipt binding for controlled augmentation evaluation.

The public sidecar intentionally contains only aggregate counters and a receipt SHA-256.
This module defines what that private receipt must bind and derives the public row from
it. Raw prompts, model output, gold answers, credentials, and host inventory are not
part of the receipt schema.

A receipt is one arm/case execution. It binds:
- the exact public evaluation manifest identity/settings;
- #127 admission;
- #129 tool policy;
- #131 catalogue/selection;
- #132 claim bundle/policy/renderer;
- #130 run manifest;
- MCP/tool implementation revision;
- fixed host-instrumentation source receipt hashes and their derived counters.
"""
from __future__ import annotations

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

SCHEMA = "haven.augmentation-eval-private-receipt.v1"
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
    "tool_policy_sha256",
    "catalog_sha256",
    "selection_receipt_sha256",
    "claim_bundle_sha256",
    "claim_policy_sha256",
    "renderer_sha256",
    "run_manifest_sha256",
    "tool_implementation_sha256",
}
SOURCE_KEYS = {"grader", "dispatcher", "observer", "verifier", "recovery", "backend"}
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
RECEIPT_KEYS = {
    "schema", "manifest", "case_id", "family", "controls", "sources",
    "receipt_sha256",
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


def make_receipt(
    *,
    manifest: Mapping[str, Any],
    case_id: str,
    family: str,
    controls: Mapping[str, Any],
    sources: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a canonical private receipt for one arm/case."""
    if not _valid_token(case_id) or not _valid_token(family):
        raise ReceiptError("invalid case/family token")
    body = {
        "schema": SCHEMA,
        "manifest": _manifest_binding(manifest),
        "case_id": case_id,
        "family": family,
        "controls": _validate_controls(controls),
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
    try:
        _validate_controls(receipt.get("controls"))
    except ReceiptError:
        errors.append("INVALID_CONTROL_BINDINGS")
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
