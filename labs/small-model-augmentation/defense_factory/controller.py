#!/usr/bin/env python3
"""Deterministic cross-stage controller for Haven Local Defense Factory."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from defense_factory import FindingLedger, canonical_rel_path
from runner import Recipe, recipe_policy_sha256

RUN_SCHEMA = "haven-local-defense-factory-run-v1"
WORKFLOW_SCHEMA = "haven-local-defense-factory-workflow-v1"
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40,64}$")
_FINDING_RE = re.compile(r"^hdf_[0-9a-f]{32}$")

_RUN_KEYS = {
    "schema", "finding_id", "fix_packet_sha256", "base_commit",
    "patch_sha256", "recipe_policy_sha256", "touched_paths",
    "recipes", "passed", "receipt_sha256",
}
_RECIPE_KEYS = {
    "recipe_id", "exit_code", "timed_out", "duration_ms",
    "stdout_sha256", "stderr_sha256", "stdout_bytes", "stderr_bytes",
}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def build_workflow_contract(
    *,
    validated_fix: Mapping[str, Any],
    base_commit: str,
    recipes: Iterable[Recipe],
) -> dict[str, Any]:
    """Bind the exact finding, fix packet, patch, base and host retest policy."""
    if not isinstance(validated_fix, Mapping):
        raise ValueError("validated_fix must be an object")
    finding_id = validated_fix.get("finding_id")
    packet_sha = validated_fix.get("packet_sha256")
    patch_sha = validated_fix.get("patch_sha256")
    paths = validated_fix.get("touched_paths")
    if not isinstance(finding_id, str) or not _FINDING_RE.fullmatch(finding_id):
        raise ValueError("invalid finding_id")
    for label, value in (("packet_sha256", packet_sha), ("patch_sha256", patch_sha)):
        if not isinstance(value, str) or not _HASH_RE.fullmatch(value):
            raise ValueError(f"invalid {label}")
    if not isinstance(base_commit, str) or not _COMMIT_RE.fullmatch(base_commit):
        raise ValueError("base_commit must be an exact lowercase commit hash")
    if not isinstance(paths, list) or not paths:
        raise ValueError("touched_paths required")
    normalized = [canonical_rel_path(p) for p in paths]
    if len(set(normalized)) != len(normalized):
        raise ValueError("duplicate touched_paths")

    recipe_list = list(recipes)
    policy_sha = recipe_policy_sha256(recipe_list)
    recipe_ids = [r.recipe_id for r in recipe_list]
    if len(set(recipe_ids)) != len(recipe_ids):
        raise ValueError("duplicate recipe_id")

    body = {
        "schema": WORKFLOW_SCHEMA,
        "finding_id": finding_id,
        "fix_packet_sha256": packet_sha,
        "patch_sha256": patch_sha,
        "base_commit": base_commit,
        "touched_paths": normalized,
        "recipe_policy_sha256": policy_sha,
        "recipe_ids": recipe_ids,
    }
    body["workflow_contract_sha256"] = _sha256(body)
    return body


def _validate_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(contract, Mapping):
        raise ValueError("workflow contract must be an object")
    expected = {
        "schema", "finding_id", "fix_packet_sha256", "patch_sha256",
        "base_commit", "touched_paths", "recipe_policy_sha256",
        "recipe_ids", "workflow_contract_sha256",
    }
    if set(contract) != expected:
        raise ValueError("workflow contract keys do not match schema")
    body = dict(contract)
    claimed = body.pop("workflow_contract_sha256")
    if not isinstance(claimed, str) or not _HASH_RE.fullmatch(claimed):
        raise ValueError("invalid workflow contract hash")
    if _sha256(body) != claimed:
        raise ValueError("workflow contract hash mismatch")
    if body.get("schema") != WORKFLOW_SCHEMA:
        raise ValueError("unsupported workflow contract schema")
    if not isinstance(body.get("finding_id"), str) or not _FINDING_RE.fullmatch(body["finding_id"]):
        raise ValueError("invalid contract finding_id")
    for key in ("fix_packet_sha256", "patch_sha256", "recipe_policy_sha256"):
        if not isinstance(body.get(key), str) or not _HASH_RE.fullmatch(body[key]):
            raise ValueError(f"invalid contract {key}")
    if not isinstance(body.get("base_commit"), str) or not _COMMIT_RE.fullmatch(body["base_commit"]):
        raise ValueError("invalid contract base_commit")
    paths = body.get("touched_paths")
    if not isinstance(paths, list) or not paths:
        raise ValueError("invalid contract touched_paths")
    normalized = [canonical_rel_path(p) for p in paths]
    if normalized != paths or len(set(paths)) != len(paths):
        raise ValueError("contract touched_paths must be canonical and unique")
    ids = body.get("recipe_ids")
    if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or not x for x in ids):
        raise ValueError("invalid contract recipe_ids")
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate contract recipe_id")
    return dict(contract)


def _validate_command_receipt(row: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(row, Mapping) or set(row) != _RECIPE_KEYS:
        raise ValueError("malformed command receipt")
    recipe_id = row.get("recipe_id")
    exit_code = row.get("exit_code")
    timed_out = row.get("timed_out")
    duration_ms = row.get("duration_ms")
    if not isinstance(recipe_id, str) or not recipe_id:
        raise ValueError("invalid receipt recipe_id")
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        raise ValueError("invalid receipt exit_code")
    if not isinstance(timed_out, bool):
        raise ValueError("invalid receipt timed_out")
    if isinstance(duration_ms, bool) or not isinstance(duration_ms, int) or duration_ms < 0:
        raise ValueError("invalid receipt duration_ms")
    for key in ("stdout_sha256", "stderr_sha256"):
        if not isinstance(row.get(key), str) or not _HASH_RE.fullmatch(row[key]):
            raise ValueError(f"invalid receipt {key}")
    for key in ("stdout_bytes", "stderr_bytes"):
        value = row.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"invalid receipt {key}")
    return dict(row)


def verify_run_receipt(
    receipt: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify receipt integrity, contract binding and the pass calculation."""
    contract = _validate_contract(contract)
    if not isinstance(receipt, Mapping) or set(receipt) != _RUN_KEYS:
        raise ValueError("runner receipt keys do not match schema")
    body = dict(receipt)
    claimed_hash = body.pop("receipt_sha256")
    if not isinstance(claimed_hash, str) or not _HASH_RE.fullmatch(claimed_hash):
        raise ValueError("invalid receipt_sha256")
    if _sha256(body) != claimed_hash:
        raise ValueError("runner receipt hash mismatch")
    if body.get("schema") != RUN_SCHEMA:
        raise ValueError("unsupported runner receipt schema")

    bindings = (
        ("finding_id", "finding_id"),
        ("fix_packet_sha256", "fix_packet_sha256"),
        ("base_commit", "base_commit"),
        ("patch_sha256", "patch_sha256"),
        ("recipe_policy_sha256", "recipe_policy_sha256"),
        ("touched_paths", "touched_paths"),
    )
    for receipt_key, contract_key in bindings:
        if body.get(receipt_key) != contract.get(contract_key):
            raise ValueError(f"runner receipt binding mismatch: {receipt_key}")

    rows = body.get("recipes")
    if not isinstance(rows, list) or not rows:
        raise ValueError("runner recipes must be a non-empty array")
    checked = [_validate_command_receipt(row) for row in rows]
    expected_ids = contract["recipe_ids"]
    actual_ids = [row["recipe_id"] for row in checked]
    if actual_ids != expected_ids[: len(actual_ids)]:
        raise ValueError("runner recipe order/id mismatch")
    if len(actual_ids) > len(expected_ids):
        raise ValueError("runner contains extra recipe receipts")
    if len(checked) < len(expected_ids):
        last = checked[-1]
        if not last["timed_out"] and last["exit_code"] == 0:
            raise ValueError("incomplete runner receipt stopped after a successful recipe")

    recomputed_pass = (
        len(checked) == len(expected_ids)
        and all((not row["timed_out"] and row["exit_code"] == 0) for row in checked)
    )
    if not isinstance(body.get("passed"), bool) or body["passed"] != recomputed_pass:
        raise ValueError("runner passed flag does not match command receipts")
    return dict(receipt)


def _latest_event(ledger: FindingLedger, finding_id: str) -> Mapping[str, Any] | None:
    for entry in reversed(ledger.entries):
        if entry.get("finding_id") == finding_id:
            return entry
    return None


def _receipt_used(ledger: FindingLedger, receipt_sha256: str) -> bool:
    for entry in ledger.entries:
        payload = entry.get("payload")
        if isinstance(payload, Mapping) and payload.get("receipt_sha256") == receipt_sha256:
            return True
    return False


def _assert_ledger_integrity(ledger: FindingLedger) -> None:
    try:
        rebuilt = FindingLedger.from_jsonl(ledger.to_jsonl())
    except (TypeError, ValueError) as exc:
        raise ValueError("finding ledger integrity check failed") from exc
    if rebuilt.entries != ledger.entries:
        raise ValueError("finding ledger canonical state mismatch")
    ids = {entry.get("finding_id") for entry in ledger.entries}
    for finding_id in ids:
        if isinstance(finding_id, str) and rebuilt.state(finding_id) != ledger.state(finding_id):
            raise ValueError("finding ledger state map mismatch")


class DefenseWorkflowController:
    """Advance a finding only when cross-stage bindings verify exactly."""

    def __init__(self, ledger: FindingLedger) -> None:
        if not isinstance(ledger, FindingLedger):
            raise ValueError("ledger must be a FindingLedger")
        self.ledger = ledger

    def record_proposal(self, contract: Mapping[str, Any]) -> dict[str, Any]:
        _assert_ledger_integrity(self.ledger)
        contract = _validate_contract(contract)
        fid = contract["finding_id"]
        state = self.ledger.state(fid)
        if state not in ("triaged", "fix_applied"):
            raise ValueError("finding is not ready for a fix proposal")
        payload = {
            "patch_sha256": contract["patch_sha256"],
            "fix_packet_sha256": contract["fix_packet_sha256"],
            "base_commit": contract["base_commit"],
            "touched_paths": list(contract["touched_paths"]),
            "recipe_policy_sha256": contract["recipe_policy_sha256"],
            "workflow_contract_sha256": contract["workflow_contract_sha256"],
        }
        return self.ledger.append(finding_id=fid, event="fix_proposed", payload=payload)

    def record_run(
        self,
        *,
        contract: Mapping[str, Any],
        receipt: Mapping[str, Any],
    ) -> dict[str, Any]:
        _assert_ledger_integrity(self.ledger)
        contract = _validate_contract(contract)
        receipt = verify_run_receipt(receipt, contract)
        fid = contract["finding_id"]
        if self.ledger.state(fid) != "fix_proposed":
            raise ValueError("finding does not have a pending fix proposal")

        latest = _latest_event(self.ledger, fid)
        if not latest or latest.get("event") != "fix_proposed":
            raise ValueError("latest finding event is not the pending proposal")
        payload = latest.get("payload")
        if not isinstance(payload, Mapping):
            raise ValueError("pending proposal payload is malformed")
        for key in (
            "patch_sha256", "fix_packet_sha256", "base_commit",
            "touched_paths", "recipe_policy_sha256", "workflow_contract_sha256",
        ):
            if payload.get(key) != contract.get(key):
                raise ValueError(f"pending proposal does not match workflow contract: {key}")

        receipt_sha = receipt["receipt_sha256"]
        if _receipt_used(self.ledger, receipt_sha):
            raise ValueError("runner receipt has already been consumed")

        self.ledger.append(
            finding_id=fid,
            event="fix_applied",
            payload={
                "applied_patch_sha256": contract["patch_sha256"],
                "receipt_sha256": receipt_sha,
                "workflow_contract_sha256": contract["workflow_contract_sha256"],
            },
        )
        self.ledger.append(
            finding_id=fid,
            event="retested",
            payload={
                "passed": receipt["passed"],
                "receipt_sha256": receipt_sha,
                "workflow_contract_sha256": contract["workflow_contract_sha256"],
            },
        )
        return {
            "finding_id": fid,
            "state": self.ledger.state(fid),
            "passed": receipt["passed"],
            "receipt_sha256": receipt_sha,
            "workflow_contract_sha256": contract["workflow_contract_sha256"],
        }
