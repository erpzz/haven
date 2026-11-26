#!/usr/bin/env python3
"""Landed-commit verification for Haven Local Defense Factory."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

from controller import (
    _assert_ledger_integrity,
    _receipt_used,
    _validate_command_receipt,
    _validate_contract,
)
from defense_factory import FindingLedger, canonical_rel_path
from runner import (
    Recipe,
    _GIT,
    _require_repo,
    _run,
    _validate_fix,
    recipe_policy_sha256,
)

SCHEMA = "haven-local-defense-factory-integration-v1"
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40,64}$")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as reader:
        for block in iter(lambda: reader.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _remove_worktree(repo: Path, path: Path) -> None:
    if path.exists():
        try:
            subprocess.run(
                _GIT + ("worktree", "remove", "--force", str(path)),
                cwd=repo,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10.0,
            )
        except subprocess.TimeoutExpired:
            pass


def verify_landed_fix(
    *,
    repo: Path,
    integration_commit: str,
    validated_fix: Mapping[str, Any],
    contract: Mapping[str, Any],
    recipes: Iterable[Recipe],
) -> dict[str, Any]:
    """Prove the validated patch's touched files landed exactly, then retest the landed commit.

    This is deliberately strict: touched files at the integration commit must byte-match
    the files produced by applying the validated patch to the contract base commit.
    """
    repo = _require_repo(Path(repo))
    contract = _validate_contract(contract)
    if not isinstance(integration_commit, str) or not _COMMIT_RE.fullmatch(integration_commit):
        raise ValueError("integration_commit must be an exact lowercase commit hash")

    finding_id, packet_sha, patch, expected_paths = _validate_fix(validated_fix)
    if finding_id != contract["finding_id"]:
        raise ValueError("validated fix finding does not match workflow contract")
    if packet_sha != contract["fix_packet_sha256"]:
        raise ValueError("validated fix packet does not match workflow contract")
    if validated_fix.get("patch_sha256") != contract["patch_sha256"]:
        raise ValueError("validated fix patch does not match workflow contract")
    if list(expected_paths) != contract["touched_paths"]:
        raise ValueError("validated fix paths do not match workflow contract")

    recipe_list = list(recipes)
    policy_sha = recipe_policy_sha256(recipe_list)
    if policy_sha != contract["recipe_policy_sha256"]:
        raise ValueError("recipe policy does not match workflow contract")
    if [r.recipe_id for r in recipe_list] != contract["recipe_ids"]:
        raise ValueError("recipe order does not match workflow contract")

    ancestor = subprocess.run(
        _GIT + ("merge-base", "--is-ancestor", contract["base_commit"], integration_commit),
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=10.0,
    )
    if ancestor.returncode != 0:
        raise ValueError("integration commit is not a descendant of the workflow base")

    root = Path(tempfile.mkdtemp(prefix="haven-defense-integration-"))
    expected_tree = root / "expected"
    landed_tree = root / "landed"
    command_receipts = []
    try:
        add_expected = _run(
            _GIT + ("worktree", "add", "--detach", str(expected_tree), contract["base_commit"]),
            cwd=repo,
            timeout=30.0,
            recipe_id="git_worktree_expected",
        )
        if add_expected.timed_out or add_expected.exit_code != 0:
            raise RuntimeError("failed to create expected worktree")

        add_landed = _run(
            _GIT + ("worktree", "add", "--detach", str(landed_tree), integration_commit),
            cwd=repo,
            timeout=30.0,
            recipe_id="git_worktree_landed",
        )
        if add_landed.timed_out or add_landed.exit_code != 0:
            raise RuntimeError("failed to create landed worktree")

        check = _run(
            _GIT + ("apply", "--check", "--whitespace=nowarn", "-"),
            cwd=expected_tree,
            timeout=15.0,
            stdin=patch.encode("utf-8"),
            recipe_id="git_apply_check",
        )
        if check.timed_out or check.exit_code != 0:
            raise ValueError("validated patch no longer applies to workflow base")

        applied = _run(
            _GIT + ("apply", "--whitespace=nowarn", "-"),
            cwd=expected_tree,
            timeout=15.0,
            stdin=patch.encode("utf-8"),
            recipe_id="git_apply",
        )
        if applied.timed_out or applied.exit_code != 0:
            raise RuntimeError("validated patch failed to apply to expected tree")

        touched_hashes: dict[str, str] = {}
        for rel in expected_paths:
            rel = canonical_rel_path(rel)
            expected_file = expected_tree / rel
            landed_file = landed_tree / rel
            if (
                expected_file.is_symlink()
                or landed_file.is_symlink()
                or not expected_file.is_file()
                or not landed_file.is_file()
            ):
                raise ValueError("touched integration path must be an existing non-symlink file")
            expected_hash = _file_sha256(expected_file)
            landed_hash = _file_sha256(landed_file)
            if expected_hash != landed_hash:
                raise ValueError(f"integration file does not exactly match validated patch: {rel}")
            touched_hashes[rel] = landed_hash

        for recipe in recipe_list:
            recipe_cwd = landed_tree if recipe.cwd == "." else landed_tree / canonical_rel_path(recipe.cwd)
            resolved = recipe_cwd.resolve()
            landed_root = landed_tree.resolve()
            if resolved != landed_root and landed_root not in resolved.parents:
                raise ValueError("recipe cwd escapes landed worktree")
            if not resolved.is_dir():
                raise ValueError("recipe cwd does not exist")
            receipt = _run(
                recipe.argv,
                cwd=resolved,
                timeout=float(recipe.timeout_seconds),
                recipe_id=recipe.recipe_id,
            )
            command_receipts.append(receipt)
            if receipt.timed_out or receipt.exit_code != 0:
                break

        passed = (
            len(command_receipts) == len(recipe_list)
            and all(not r.timed_out and r.exit_code == 0 for r in command_receipts)
        )
        body = {
            "schema": SCHEMA,
            "finding_id": finding_id,
            "workflow_contract_sha256": contract["workflow_contract_sha256"],
            "fix_packet_sha256": packet_sha,
            "patch_sha256": contract["patch_sha256"],
            "base_commit": contract["base_commit"],
            "integration_commit": integration_commit,
            "recipe_policy_sha256": policy_sha,
            "touched_paths": list(expected_paths),
            "touched_file_sha256": touched_hashes,
            "recipes": [r.__dict__ for r in command_receipts],
            "passed": passed,
        }
        body["integration_receipt_sha256"] = _sha256(body)
        return body
    finally:
        _remove_worktree(repo, expected_tree)
        _remove_worktree(repo, landed_tree)
        shutil.rmtree(root, ignore_errors=True)


_EXPECTED_KEYS = {
    "schema",
    "finding_id",
    "workflow_contract_sha256",
    "fix_packet_sha256",
    "patch_sha256",
    "base_commit",
    "integration_commit",
    "recipe_policy_sha256",
    "touched_paths",
    "touched_file_sha256",
    "recipes",
    "passed",
    "integration_receipt_sha256",
}


def verify_integration_receipt(
    receipt: Mapping[str, Any],
    contract: Mapping[str, Any],
    repo: Path,
) -> dict[str, Any]:
    repo = _require_repo(Path(repo))
    contract = _validate_contract(contract)
    if not isinstance(receipt, Mapping) or set(receipt) != _EXPECTED_KEYS:
        raise ValueError("integration receipt keys do not match schema")
    body = dict(receipt)
    claimed = body.pop("integration_receipt_sha256")
    if not isinstance(claimed, str) or not _HASH_RE.fullmatch(claimed):
        raise ValueError("invalid integration receipt hash")
    if _sha256(body) != claimed:
        raise ValueError("integration receipt hash mismatch")
    if body.get("schema") != SCHEMA:
        raise ValueError("unsupported integration receipt schema")

    bindings = (
        ("finding_id", "finding_id"),
        ("workflow_contract_sha256", "workflow_contract_sha256"),
        ("fix_packet_sha256", "fix_packet_sha256"),
        ("patch_sha256", "patch_sha256"),
        ("base_commit", "base_commit"),
        ("recipe_policy_sha256", "recipe_policy_sha256"),
        ("touched_paths", "touched_paths"),
    )
    for receipt_key, contract_key in bindings:
        if body.get(receipt_key) != contract.get(contract_key):
            raise ValueError(f"integration receipt binding mismatch: {receipt_key}")

    commit = body.get("integration_commit")
    if not isinstance(commit, str) or not _COMMIT_RE.fullmatch(commit):
        raise ValueError("invalid integration commit")
    hashes = body.get("touched_file_sha256")
    if not isinstance(hashes, Mapping) or set(hashes) != set(contract["touched_paths"]):
        raise ValueError("integration receipt file hashes do not match touched paths")
    for path, digest in hashes.items():
        if canonical_rel_path(path) != path:
            raise ValueError("noncanonical integration receipt path")
        if not isinstance(digest, str) or not _HASH_RE.fullmatch(digest):
            raise ValueError("invalid touched file hash")
        tree = subprocess.run(
            _GIT + ("ls-tree", commit, "--", path),
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
            timeout=10.0,
        )
        if tree.returncode != 0 or not tree.stdout.strip():
            raise ValueError("touched path is absent from integration commit")
        first = tree.stdout.strip().split("\t", 1)[0].split()
        if len(first) < 2 or first[0] not in {"100644", "100755"} or first[1] != "blob":
            raise ValueError("touched integration path is not a regular file")
        shown = _run(
            _GIT + ("show", f"{commit}:{path}"),
            cwd=repo,
            timeout=15.0,
            recipe_id="git_show_touched",
        )
        if shown.timed_out or shown.exit_code != 0:
            raise ValueError("failed to read touched file from integration commit")
        if shown.stdout_sha256 != digest:
            raise ValueError("integration receipt file hash does not match commit")

    ancestor = subprocess.run(
        _GIT + ("merge-base", "--is-ancestor", contract["base_commit"], commit),
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=10.0,
    )
    if ancestor.returncode != 0:
        raise ValueError("integration receipt commit is not a descendant of workflow base")

    rows = body.get("recipes")
    if not isinstance(rows, list) or len(rows) != len(contract["recipe_ids"]):
        raise ValueError("integration receipt must contain every recipe result")
    checked = [_validate_command_receipt(row) for row in rows]
    if [row["recipe_id"] for row in checked] != contract["recipe_ids"]:
        raise ValueError("integration recipe order mismatch")
    recomputed = all(not row["timed_out"] and row["exit_code"] == 0 for row in checked)
    if not isinstance(body.get("passed"), bool) or body["passed"] != recomputed:
        raise ValueError("integration pass flag does not match recipe receipts")
    if not body["passed"]:
        raise ValueError("failed integration receipt cannot close a finding")
    return dict(receipt)


def close_verified_finding(
    *,
    ledger: FindingLedger,
    contract: Mapping[str, Any],
    receipt: Mapping[str, Any],
    repo: Path,
) -> dict[str, Any]:
    """Close only a previously verified finding with a fresh landed-commit receipt."""
    _assert_ledger_integrity(ledger)
    contract = _validate_contract(contract)
    receipt = verify_integration_receipt(receipt, contract, repo)
    fid = contract["finding_id"]
    if ledger.state(fid) != "verified":
        raise ValueError("finding must be verified before integration closure")

    latest = next(
        (entry for entry in reversed(ledger.entries) if entry.get("finding_id") == fid),
        None,
    )
    if not latest or latest.get("event") != "retested":
        raise ValueError("latest finding event must be the passing retest")
    payload = latest.get("payload")
    if (
        not isinstance(payload, Mapping)
        or payload.get("passed") is not True
        or payload.get("workflow_contract_sha256") != contract["workflow_contract_sha256"]
    ):
        raise ValueError("verified retest does not match workflow contract")

    receipt_sha = receipt["integration_receipt_sha256"]
    if _receipt_used(ledger, receipt_sha):
        raise ValueError("integration receipt has already been consumed")

    entry = ledger.append(
        finding_id=fid,
        event="closed",
        payload={
            "integration_receipt_sha256": receipt_sha,
            "integration_commit": receipt["integration_commit"],
            "workflow_contract_sha256": contract["workflow_contract_sha256"],
        },
    )
    return {
        "finding_id": fid,
        "state": ledger.state(fid),
        "integration_commit": receipt["integration_commit"],
        "integration_receipt_sha256": receipt_sha,
        "event_hash": entry["event_hash"],
    }
