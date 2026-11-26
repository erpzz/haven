#!/usr/bin/env python3
"""Host-owned isolated apply/retest runner for Haven Local Defense Factory."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from defense_factory import canonical_rel_path

_COMMIT_RE = re.compile(r"^[0-9a-f]{40,64}$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT = ("git", "-c", "core.hooksPath=/dev/null")


def _sha256_stream(f) -> tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    f.seek(0)
    while True:
        block = f.read(1024 * 1024)
        if not block:
            break
        h.update(block)
        n += len(block)
    return h.hexdigest(), n


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


@dataclass(frozen=True)
class Recipe:
    recipe_id: str
    argv: tuple[str, ...]
    timeout_seconds: float = 60.0
    cwd: str = "."

    def validate(self) -> None:
        if not isinstance(self.recipe_id, str) or not self.recipe_id.strip():
            raise ValueError("recipe_id required")
        if not isinstance(self.argv, tuple) or not self.argv or any(not isinstance(x, str) or not x for x in self.argv):
            raise ValueError("argv must be a non-empty tuple of strings")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)):
            raise ValueError("timeout_seconds must be numeric")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 3600:
            raise ValueError("timeout_seconds out of bounds")
        canonical_rel_path(self.cwd if self.cwd != "." else "workspace")


@dataclass(frozen=True)
class CommandReceipt:
    recipe_id: str
    exit_code: int | None
    timed_out: bool
    duration_ms: int
    stdout_sha256: str
    stderr_sha256: str
    stdout_bytes: int
    stderr_bytes: int


def _terminate_group(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=0.5)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        raise RuntimeError("process group did not terminate")


def _run(argv: Sequence[str], *, cwd: Path, timeout: float, stdin: bytes | None = None, recipe_id: str) -> CommandReceipt:
    if os.name != "posix":
        raise RuntimeError("hard process-group runner currently requires POSIX")
    start = time.monotonic()
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(
            tuple(argv),
            cwd=str(cwd),
            stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            start_new_session=True,
        )
        timed_out = False
        try:
            proc.communicate(input=stdin, timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _terminate_group(proc)
            proc.communicate()
        stdout_sha, stdout_bytes = _sha256_stream(out)
        stderr_sha, stderr_bytes = _sha256_stream(err)
    duration_ms = max(0, int((time.monotonic() - start) * 1000))
    return CommandReceipt(
        recipe_id=recipe_id,
        exit_code=proc.returncode,
        timed_out=timed_out,
        duration_ms=duration_ms,
        stdout_sha256=stdout_sha,
        stderr_sha256=stderr_sha,
        stdout_bytes=stdout_bytes,
        stderr_bytes=stderr_bytes,
    )


def _require_repo(path: Path) -> Path:
    p = path.resolve()
    if not p.is_dir():
        raise ValueError("repository path must be a directory")
    probe = subprocess.run(
        _GIT + ("rev-parse", "--show-toplevel"), cwd=p,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True, timeout=10.0,
    )
    if probe.returncode != 0:
        raise ValueError("repository path is not a git worktree")
    root = Path(probe.stdout.strip()).resolve()
    if root != p:
        raise ValueError("repository path must be the git toplevel")
    return p


def _validate_fix(validated_fix: Mapping[str, Any]) -> tuple[str, tuple[str, ...]]:
    if not isinstance(validated_fix, Mapping):
        raise ValueError("validated_fix must be an object")
    patch = validated_fix.get("patch")
    patch_sha = validated_fix.get("patch_sha256")
    paths = validated_fix.get("touched_paths")
    if not isinstance(patch, str) or not isinstance(patch_sha, str) or not _HASH_RE.fullmatch(patch_sha):
        raise ValueError("validated fix missing patch/hash")
    actual = hashlib.sha256(patch.encode("utf-8")).hexdigest()
    if actual != patch_sha:
        raise ValueError("patch hash mismatch")
    if not isinstance(paths, list) or not paths:
        raise ValueError("validated fix missing touched_paths")
    normalized = tuple(canonical_rel_path(p) for p in paths)
    if len(set(normalized)) != len(normalized):
        raise ValueError("duplicate touched_paths")
    return patch, normalized


def run_fix(*, repo: Path, base_commit: str, validated_fix: Mapping[str, Any], recipes: Iterable[Recipe]) -> dict[str, Any]:
    """Apply one validated patch in a detached worktree and run host-owned recipes.

    The return value contains no raw command output, only hashes and bounded metadata.
    """
    repo = _require_repo(Path(repo))
    if not isinstance(base_commit, str) or not _COMMIT_RE.fullmatch(base_commit):
        raise ValueError("base_commit must be an exact lowercase commit hash")
    patch, expected_paths = _validate_fix(validated_fix)
    recipe_list = list(recipes)
    if not recipe_list:
        raise ValueError("at least one host-owned retest recipe is required")
    seen_ids: set[str] = set()
    for recipe in recipe_list:
        if not isinstance(recipe, Recipe):
            raise ValueError("recipes must contain Recipe objects")
        recipe.validate()
        if recipe.recipe_id in seen_ids:
            raise ValueError("duplicate recipe_id")
        seen_ids.add(recipe.recipe_id)

    root = Path(tempfile.mkdtemp(prefix="haven-defense-factory-"))
    worktree = root / "worktree"
    receipts: list[CommandReceipt] = []
    try:
        add = _run(_GIT + ("worktree", "add", "--detach", str(worktree), base_commit), cwd=repo, timeout=30.0, recipe_id="git_worktree_add")
        if add.timed_out or add.exit_code != 0:
            raise RuntimeError("failed to create detached worktree")

        for rel in expected_paths:
            target = worktree / rel
            if target.is_symlink() or not target.is_file():
                raise ValueError("patch target must be an existing non-symlink file")

        check = _run(_GIT + ("apply", "--check", "--whitespace=nowarn", "-"), cwd=worktree, timeout=15.0, stdin=patch.encode("utf-8"), recipe_id="git_apply_check")
        if check.timed_out or check.exit_code != 0:
            raise ValueError("patch failed git apply --check")
        apply_receipt = _run(_GIT + ("apply", "--whitespace=nowarn", "-"), cwd=worktree, timeout=15.0, stdin=patch.encode("utf-8"), recipe_id="git_apply")
        if apply_receipt.timed_out or apply_receipt.exit_code != 0:
            raise RuntimeError("validated patch failed to apply")

        changed = subprocess.run(
            _GIT + ("diff", "--name-only", "--no-renames", "--"), cwd=worktree,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True, timeout=10.0,
        )
        if changed.returncode != 0:
            raise RuntimeError("failed to enumerate changed files")
        actual_paths = tuple(sorted(canonical_rel_path(x) for x in changed.stdout.splitlines() if x.strip()))
        if actual_paths != tuple(sorted(expected_paths)):
            raise RuntimeError("actual changed-file set differs from validated patch receipt")

        for recipe in recipe_list:
            recipe_cwd = worktree if recipe.cwd == "." else worktree / canonical_rel_path(recipe.cwd)
            resolved = recipe_cwd.resolve()
            if resolved != worktree.resolve() and worktree.resolve() not in resolved.parents:
                raise ValueError("recipe cwd escapes worktree")
            if not resolved.is_dir():
                raise ValueError("recipe cwd does not exist")
            receipt = _run(recipe.argv, cwd=resolved, timeout=float(recipe.timeout_seconds), recipe_id=recipe.recipe_id)
            receipts.append(receipt)
            if receipt.timed_out or receipt.exit_code != 0:
                break

        passed = len(receipts) == len(recipe_list) and all((not r.timed_out and r.exit_code == 0) for r in receipts)
        body = {
            "schema": "haven-local-defense-factory-run-v1",
            "base_commit": base_commit,
            "patch_sha256": validated_fix["patch_sha256"],
            "touched_paths": list(expected_paths),
            "recipes": [r.__dict__ for r in receipts],
            "passed": passed,
        }
        body["receipt_sha256"] = hashlib.sha256(_canonical_json(body)).hexdigest()
        return body
    finally:
        if worktree.exists():
            try:
                subprocess.run(_GIT + ("worktree", "remove", "--force", str(worktree)), cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=10.0)
            except subprocess.TimeoutExpired:
                pass
        shutil.rmtree(root, ignore_errors=True)
