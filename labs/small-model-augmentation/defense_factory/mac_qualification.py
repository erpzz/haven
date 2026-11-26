#!/usr/bin/env python3
"""Target-Mac/APFS qualification for the #186 Local Defense Factory host boundary.

This evidence runner exercises the real defense_factory.runner.run_fix() against a
private synthetic Git repository located on the qualified filesystem.

It proves:
- the qualification output and runner temporary worktrees are on APFS;
- the tested checkout descends from the reviewed #186 candidate;
- exact hashes of the Defense Factory core/runner/controller/integration sources;
- runner-owned Git commands suppress a malicious post-checkout hook;
- a validated existing-file patch is applied only to the allowed path;
- a host-owned passing recipe observes the patched bytes;
- a timed-out recipe's delayed descendant is killed before its side effect;
- disposable worktrees are removed after both runs.

It does not claim a model proposed the patch, and it is not an OS sandbox.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any

HERE = Path(__file__).resolve().parent
AUG = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import runner

SCHEMA = "haven.defense-factory-mac-qualification.v1"
CANDIDATE_COMMIT = "d00c55231dcd5c090a8de91ff5ca2c38736889af"
SOURCE_FILES = (
    "defense_factory.py",
    "runner.py",
    "controller.py",
    "integration.py",
)


class MacDefenseQualificationError(RuntimeError):
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


def _sha_file(path: Path) -> str:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise MacDefenseQualificationError("SOURCE_FILE_UNTRUSTED")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _write_private(path: Path, value: Any) -> None:
    raw = _canon(value) + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise MacDefenseQualificationError("RECEIPT_CREATE_FAILED") from exc
    try:
        os.write(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)


def _run(argv, *, cwd: Path, timeout=30.0, check=True) -> subprocess.CompletedProcess:
    try:
        cp = subprocess.run(
            list(argv), cwd=cwd, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MacDefenseQualificationError("HOST_COMMAND_FAILED") from exc
    if check and cp.returncode != 0:
        raise MacDefenseQualificationError("HOST_COMMAND_NONZERO")
    return cp


def _require_apfs(path: Path) -> dict[str, str]:
    if sys.platform != "darwin":
        raise MacDefenseQualificationError("MACOS_REQUIRED")
    df = _run(["df", "-P", str(path)], cwd=path, timeout=10)
    rows = [line for line in df.stdout.splitlines() if line.strip()]
    if len(rows) < 2 or not rows[-1].split():
        raise MacDefenseQualificationError("FILESYSTEM_PROBE_INVALID")
    device = rows[-1].split()[0]
    info = _run(["diskutil", "info", device], cwd=path, timeout=15)
    lower = info.stdout.lower()
    if "file system personality:" not in lower or "apfs" not in lower:
        raise MacDefenseQualificationError("APFS_REQUIRED")
    return {
        "platform": "darwin",
        "filesystem": "apfs",
        "device": device,
        "diskutil_sha256": hashlib.sha256(info.stdout.encode()).hexdigest(),
    }


def _source_identity() -> dict[str, Any]:
    checkout = HERE.resolve()
    top = _run(
        ["git", "rev-parse", "--show-toplevel"], cwd=checkout, timeout=10
    ).stdout.strip()
    repo = Path(top).resolve()
    head = _run(["git", "rev-parse", "HEAD"], cwd=repo, timeout=10).stdout.strip()
    ancestor = _run(
        ["git", "merge-base", "--is-ancestor", CANDIDATE_COMMIT, head],
        cwd=repo, timeout=10, check=False,
    )
    if ancestor.returncode != 0:
        raise MacDefenseQualificationError("CANDIDATE_NOT_ANCESTOR")
    hashes = {name: _sha_file(HERE / name) for name in SOURCE_FILES}
    body = {
        "candidate_commit": CANDIDATE_COMMIT,
        "qualification_checkout_head": head,
        "source_sha256": hashes,
        "qualification_runner_sha256": _sha_file(Path(__file__).resolve()),
    }
    body["implementation_sha256"] = _sha_obj({
        "candidate_commit": CANDIDATE_COMMIT,
        "source_sha256": hashes,
    })
    return body


def _init_fixture_repo(root: Path, hook_marker: Path) -> tuple[Path, str]:
    repo = root / "fixture-repo"
    repo.mkdir(mode=0o700)
    _run(["git", "init", "-q"], cwd=repo)
    _run(["git", "config", "user.name", "Haven Defense Qualification"], cwd=repo)
    _run(["git", "config", "user.email", "haven-defense@example.invalid"], cwd=repo)

    src = repo / "src"
    src.mkdir()
    (src / "app.py").write_text('VALUE = "before"\n', encoding="utf-8")
    _run(["git", "add", "src/app.py"], cwd=repo)
    _run(["git", "commit", "-q", "-m", "fixture base"], cwd=repo)
    base = _run(["git", "rev-parse", "HEAD"], cwd=repo).stdout.strip()

    hooks = repo / ".git" / "hooks"
    hooks.mkdir(exist_ok=True)
    hook = hooks / "post-checkout"
    hook.write_text(
        "#!/bin/sh\n"
        f"printf hook-ran > {json.dumps(str(hook_marker))}\n",
        encoding="utf-8",
    )
    hook.chmod(0o700)
    return repo, base


def _validated_fix(base_text: str = "before", new_text: str = "after") -> dict[str, Any]:
    patch = (
        "diff --git a/src/app.py b/src/app.py\n"
        "--- a/src/app.py\n"
        "+++ b/src/app.py\n"
        "@@ -1 +1 @@\n"
        f'-VALUE = "{base_text}"\n'
        f'+VALUE = "{new_text}"\n'
    )
    patch_sha = hashlib.sha256(patch.encode("utf-8")).hexdigest()
    return {
        "finding_id": "hdf_" + "a" * 32,
        "packet_sha256": "b" * 64,
        "patch": patch,
        "patch_sha256": patch_sha,
        "touched_paths": ["src/app.py"],
    }


def _worktree_paths(repo: Path) -> list[str]:
    cp = _run(
        ["git", "-c", "core.hooksPath=/dev/null", "worktree", "list", "--porcelain"],
        cwd=repo,
    )
    paths = []
    for line in cp.stdout.splitlines():
        if line.startswith("worktree "):
            paths.append(line[len("worktree "):])
    return paths


def _pass_recipe() -> runner.Recipe:
    code = (
        "from pathlib import Path;"
        "assert Path('src/app.py').read_text(encoding='utf-8') == "
        "'VALUE = \"after\"\\n'"
    )
    return runner.Recipe(
        "verify-patched-content",
        (sys.executable, "-c", code),
        timeout_seconds=10.0,
        cwd=".",
    )


def _timeout_recipe(marker: Path) -> runner.Recipe:
    child = (
        "import time;"
        "from pathlib import Path;"
        "time.sleep(0.8);"
        f"Path({str(marker)!r}).write_text('late', encoding='utf-8')"
    )
    parent = (
        "import subprocess,sys,time;"
        f"subprocess.Popen([sys.executable,'-c',{child!r}]);"
        "time.sleep(60)"
    )
    return runner.Recipe(
        "timeout-process-group",
        (sys.executable, "-c", parent),
        timeout_seconds=0.25,
        cwd=".",
    )


def run_qualification(*, out_dir: Path, require_apfs: bool = True) -> dict[str, Any]:
    if os.name != "posix":
        raise MacDefenseQualificationError("POSIX_REQUIRED")
    out_dir = Path(out_dir).expanduser().resolve()
    if out_dir.exists():
        raise MacDefenseQualificationError("OUTPUT_DIR_EXISTS")
    out_dir.mkdir(mode=0o700, parents=False)
    if stat.S_IMODE(out_dir.stat().st_mode) != 0o700:
        raise MacDefenseQualificationError("OUTPUT_DIR_MODE_INVALID")

    platform = (
        _require_apfs(out_dir)
        if require_apfs
        else {
            "platform": sys.platform,
            "filesystem": "not-qualified",
            "device": "",
            "diskutil_sha256": "",
        }
    )
    identity = _source_identity()

    hook_marker = out_dir / "git-hook-marker"
    delayed_marker = out_dir / "delayed-descendant-marker"
    fixture_root = out_dir / "fixture"
    fixture_root.mkdir(mode=0o700)
    repo, base = _init_fixture_repo(fixture_root, hook_marker)
    expected_worktrees = [str(repo.resolve())]

    temp_root = out_dir / "runner-temp"
    temp_root.mkdir(mode=0o700)
    previous_tempdir = tempfile.tempdir
    tempfile.tempdir = str(temp_root)
    try:
        validated = _validated_fix()

        passing = runner.run_fix(
            repo=repo,
            base_commit=base,
            validated_fix=validated,
            recipes=[_pass_recipe()],
        )
        if not passing.get("passed"):
            raise MacDefenseQualificationError("PASSING_RUN_FAILED")
        if passing.get("base_commit") != base:
            raise MacDefenseQualificationError("BASE_BINDING_MISMATCH")
        if passing.get("touched_paths") != ["src/app.py"]:
            raise MacDefenseQualificationError("TOUCHED_PATH_MISMATCH")
        if hook_marker.exists():
            raise MacDefenseQualificationError("GIT_HOOK_EXECUTED")
        after_pass = _worktree_paths(repo)
        if after_pass != expected_worktrees:
            raise MacDefenseQualificationError("PASS_WORKTREE_LEAK")

        timed = runner.run_fix(
            repo=repo,
            base_commit=base,
            validated_fix=validated,
            recipes=[_timeout_recipe(delayed_marker)],
        )
        rows = timed.get("recipes")
        if (
            timed.get("passed") is not False
            or not isinstance(rows, list)
            or len(rows) != 1
            or rows[0].get("timed_out") is not True
        ):
            raise MacDefenseQualificationError("TIMEOUT_RUN_INVALID")

        # Wait beyond the descendant's scheduled write. A surviving grandchild
        # would create the marker after the parent recipe has been killed.
        time.sleep(1.2)
        if delayed_marker.exists():
            raise MacDefenseQualificationError("DESCENDANT_SURVIVED_TIMEOUT")
        if hook_marker.exists():
            raise MacDefenseQualificationError("GIT_HOOK_EXECUTED")
        after_timeout = _worktree_paths(repo)
        if after_timeout != expected_worktrees:
            raise MacDefenseQualificationError("TIMEOUT_WORKTREE_LEAK")
    finally:
        tempfile.tempdir = previous_tempdir

    receipt = {
        "schema": SCHEMA,
        "classification": "development",
        "status": "pass",
        "errors": [],
        "platform": platform,
        "implementation": identity,
        "fixture_base_commit": base,
        "fixture_repo_sha256": _sha_obj({
            "base_commit": base,
            "baseline_file_sha256": _sha_file(repo / "src" / "app.py"),
        }),
        "passing_run_receipt_sha256": passing["receipt_sha256"],
        "passing_recipe_policy_sha256": passing["recipe_policy_sha256"],
        "passing_touched_paths": passing["touched_paths"],
        "timeout_run_receipt_sha256": timed["receipt_sha256"],
        "timeout_recipe_policy_sha256": timed["recipe_policy_sha256"],
        "timeout_exit_code": rows[0].get("exit_code"),
        "timeout_observed": rows[0].get("timed_out"),
        "git_hook_suppressed": not hook_marker.exists(),
        "delayed_descendant_killed": not delayed_marker.exists(),
        "worktree_cleanup_verified": (
            after_pass == expected_worktrees
            and after_timeout == expected_worktrees
        ),
        "runner_temp_root": str(temp_root),
        "model_patch_proposal_tested": False,
        "os_sandbox_claimed": False,
    }
    receipt["receipt_sha256"] = _sha_obj(receipt)
    _write_private(out_dir / "defense-mac-qualification.json", receipt)
    return receipt


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)
    result = run_qualification(out_dir=args.out_dir, require_apfs=True)
    print(json.dumps({
        "schema": result["schema"],
        "status": result["status"],
        "receipt_sha256": result["receipt_sha256"],
        "implementation_sha256": result["implementation"]["implementation_sha256"],
        "git_hook_suppressed": result["git_hook_suppressed"],
        "delayed_descendant_killed": result["delayed_descendant_killed"],
        "worktree_cleanup_verified": result["worktree_cleanup_verified"],
        "model_patch_proposal_tested": result["model_patch_proposal_tested"],
        "out_dir": str(args.out_dir),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
