"""Prepare a private Kaggle payload. No login, upload, model load or training.

Replays the existing dataset builder on the ORIGINAL sources; accepts no
replacement rows and never lowers gpu_campaign's admission thresholds.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
SECPATCH = HERE.parent
sys.path.insert(0, str(SECPATCH))
from gpu_campaign import digest, qualify_data  # noqa: E402
from harvest import PERMISSIVE, classify_license  # noqa: E402

MODEL = "Qwen/Qwen3-0.6B"
REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"
DATA_FILES = ("manifest.json", "train.jsonl", "dev.jsonl", "heldout.jsonl",
              "eval-dev.jsonl", "eval-heldout.jsonl", "repo-eval-candidates.jsonl")
# Replay every original output, but ship only inputs used by this campaign.
EXPORT_DATA_FILES = ("manifest.json", "train.jsonl", "eval-heldout.jsonl")
EXECUTION_FILES = ("gpu_campaign.py", "train.py", "evaluate.py", "harvest.py", "registry.py")


def write_source_notices(root, source_check, used_rows, harvest):
    """Retain checked fix-commit notices, rejecting incomplete or altered evidence.

    This checks internal consistency of an externally collected source audit;
    it does not, by itself, authenticate the upstream repositories.
    """
    report = json.loads(source_check.read_text(encoding="utf-8"))
    if (report.get("schema") != "haven-secpatch-fix-source-check-v1" or
            report.get("failures") or report.get("requested") != len(used_rows) or
            report.get("checked") != len(used_rows)):
        raise ValueError("Incomplete fix-commit source and license checks")
    items = report.get("items") or []
    by_key = {item["key"]: item for item in items}
    if len(items) != len(by_key) or set(by_key) != set(used_rows):
        raise ValueError("Fix-commit source check does not cover exactly the exported fixes")
    texts = report.get("notice_texts") or {}
    written = set()
    notices_dir = root / "notices"
    notices_dir.mkdir(parents=True)
    required_checks = {"commit_parent", "vulnerable_and_fixed_function_blobs",
                       "license_and_notice_files_at_commit"}
    for key, row in used_rows.items():
        item, src, h = by_key[key], row["source"], harvest[key]
        expected = {"repo": src["repo"], "commit": src["commit"], "parent": src["parent"],
                    "source_path": src["path"], "license": src["code_license"],
                    "license_file": h["license_file"], "advisory_ids": src["advisory_ids"]}
        if any(item.get(k) != v for k, v in expected.items()) or not required_checks.issubset(item.get("checked", [])):
            raise ValueError("Fix-commit source check disagrees with exported data: " + key)
        notices = item.get("notices") or []
        matches = [n for n in notices if n.get("path") == h["license_file"] and
                   n.get("classified_as") == src["code_license"]]
        if len(matches) != 1:
            raise ValueError("Missing original fix-commit license notice: " + key)
        for notice in notices:
            sha = notice.get("sha256", "")
            if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
                raise ValueError("Incomplete notice digest: " + key)
            try:
                content = base64.b64decode(texts[sha], validate=True)
            except (KeyError, ValueError) as exc:
                raise ValueError("Missing original notice bytes: " + key) from exc
            if not content or hashlib.sha256(content).hexdigest() != sha:
                raise ValueError("Original notice bytes do not match digest: " + key)
            if re.search(r"(?:^|/)(?:LICEN[CS]E|COPYING)(?:\.(?:md|txt|rst))?$",
                         notice.get("path", ""), re.I):
                actual = classify_license(content.decode("utf-8", "replace"))
                if actual not in PERMISSIVE or actual != notice.get("classified_as"):
                    raise ValueError("Non-permissive or unclassified license at the source path: " + key)
            if sha not in written:
                (notices_dir / (sha + ".txt")).write_bytes(content)
                written.add(sha)
    (root / "source-check.json").write_text(json.dumps(
        {k: v for k, v in report.items() if k != "notice_texts"}, indent=2) + "\n")
    (root / "ATTRIBUTION.md").write_text(
        "# Attribution and license notices\n\n"
        "This input contains transformed excerpts from the repositories and commits recorded "
        "for each fix in `source-check.json` and the data rows. Original license and notice "
        "bytes are in `notices/`, named by SHA-256, and their paths and hashes are recorded "
        "per fix. Different files retain their individual upstream licenses.\n\n"
        "Advisory text and metadata come from the GitHub Advisory Database and the Python "
        "Packaging Advisory Database through OSV; both are CC-BY-4.0. The data were selected, "
        "deduplicated and transformed into prompts, targets and grading records. Advisory IDs "
        "are recorded per fix; source records can be located at "
        "https://osv.dev/vulnerability/ followed by the advisory ID. Sources: "
        "https://github.com/github/advisory-database and "
        "https://github.com/pypa/advisory-database. License: "
        "https://creativecommons.org/licenses/by/4.0/.\n\n"
        "This is a composite dataset; it is not licensed as CC0.\n", encoding="utf-8")


def notebook(payload_sha: str) -> dict:
    # No credentials or private repository URL appear in this notebook.
    code = '''import hashlib, json, os, pathlib, signal, subprocess, sys, time, zipfile
payloads = list(pathlib.Path('/kaggle/input').rglob('haven-secpatch.payload'))
if len(payloads) != 1:
    raise RuntimeError('Attach exactly one private secpatch payload dataset')
payload = payloads[0]
if hashlib.sha256(payload.read_bytes()).hexdigest() != PAYLOAD_SHA:
    raise RuntimeError('Payload differs from the locally qualified package')
root = pathlib.Path('/kaggle/temp/haven-r02')
root.mkdir(parents=True, exist_ok=False)
with zipfile.ZipFile(payload) as archive:
    # Reject path traversal and symlinks even with an expected payload digest.
    for member in archive.infolist():
        path = pathlib.PurePosixPath(member.filename)
        if path.is_absolute() or '..' in path.parts or (member.external_attr >> 16) & 0o170000 == 0o120000:
            raise RuntimeError('Unsafe archive member')
    archive.extractall(root)
result = pathlib.Path('/kaggle/working/result')
result.mkdir(mode=0o700, exist_ok=False)
started = time.monotonic()
proc = subprocess.Popen([sys.executable, str(root / 'remote' / 'run.py'),
                         '--payload', str(root), '--output', str(result)], start_new_session=True)
status = 'FAILED'
rc = 125
try:
    rc = proc.wait(timeout=7200)
    status = 'COMPLETED' if rc == 0 else 'FAILED'
except subprocess.TimeoutExpired:
    status = 'TIMED_OUT'
    rc = 124
finally:
    # Kill all descendants, including any trainer/evaluator left by a failure.
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    (result / 'watchdog.json').write_text(json.dumps({
        'status': status, 'exit_code': rc, 'wall_seconds': round(time.monotonic()-started, 3),
        'budget_seconds': 7200, 'scope': 'dependencies_download_training_and_both_evaluations',
        'provider_session_shutdown': 'not controlled by process watchdog; inspect Kaggle session status'
    }, indent=2))
if rc:
    raise RuntimeError('Campaign failed; retain partial receipts and logs. Exit=' + str(rc))
'''
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "cells": [{"cell_type": "code", "id": "bounded-campaign", "metadata": {},
                   "execution_count": None, "outputs": [],
                   "source": ("PAYLOAD_SHA = " + repr(payload_sha) + "\n" + code).splitlines(True)}],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=pathlib.Path, required=True)
    p.add_argument("--candidates", type=pathlib.Path, required=True)
    p.add_argument("--harvest", type=pathlib.Path, nargs="+", required=True)
    p.add_argument("--osv-archive", type=pathlib.Path, required=True)
    p.add_argument("--source-check", type=pathlib.Path,
                   help="Private fix-commit and license-notice audit for exported fixes")
    p.add_argument("--bandit", default="bandit", help="Use original Bandit 1.9.4")
    p.add_argument("--owner", required=True, help="Authorized existing Kaggle username; private output only")
    p.add_argument("--slug", default="haven-r02-secpatch")
    p.add_argument("--output", type=pathlib.Path, required=True, help="New private directory OUTSIDE Git")
    a = p.parse_args(argv)
    if not all(re.fullmatch(r"[a-zA-Z0-9_-]+", s) for s in (a.owner, a.slug)):
        p.error("Invalid owner or slug")
    # Forbid private generated files anywhere inside any Git checkout.
    if any((parent / ".git").exists() for parent in (a.output.resolve(), *a.output.resolve().parents)):
        p.error("--output must be outside Git")
    q = qualify_data(a.data)
    if not a.source_check or a.source_check.is_symlink() or not a.source_check.is_file():
        p.error("A complete fix-commit source and license-notice audit is required")
    manifest = json.loads((a.data / "manifest.json").read_text())
    if manifest.get("cutoff") != "2025-07-01":
        p.error("Keep the campaign's original 2025-07-01 cutoff")
    if digest(a.osv_archive) != manifest["osv_archive_sha256"]:
        p.error("Original OSV archive does not match dataset provenance")
    version = subprocess.check_output([a.bandit, "--version"], text=True).splitlines()[0]
    if version != "bandit 1.9.4" or manifest.get("bandit_version") != version:
        p.error("Reproduce with original Bandit 1.9.4")
    with tempfile.TemporaryDirectory() as tmp:
        rebuilt = pathlib.Path(tmp) / "data"
        subprocess.run([sys.executable, str(SECPATCH / "build.py"), "--candidates", str(a.candidates),
                        "--harvest", *map(str, a.harvest), "--out", str(rebuilt),
                        "--bandit", a.bandit, "--cutoff", "2025-07-01", "--near-dup", "0.8"],
                       check=True, timeout=2400, stdout=subprocess.DEVNULL)
        for name in DATA_FILES[1:]:
            if digest(rebuilt / name) != digest(a.data / name):
                p.error("Dataset is not reproduced from original sources: " + name)
        replay_manifest = json.loads((rebuilt / "manifest.json").read_text())
        if {k:v for k,v in manifest.items() if k != "built_at"} != {
                k:v for k,v in replay_manifest.items() if k != "built_at"}:
            p.error("Rebuilt manifest differs beyond its build timestamp")
    # Existing harvester records the license filename and fix commit. Retain
    # them, rather than accepting row flags as independent license proof.
    used_rows = {}
    for name in ("train.jsonl", "eval-heldout.jsonl"):
        for line in (a.data / name).read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                previous = used_rows.setdefault(row["key"], row)
                if previous["source"] != row["source"]:
                    p.error("Inconsistent source records for fix " + row["key"])
    used = set(used_rows)
    harvest = {}
    for path in a.harvest:
        for line in path.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                if row["key"] in used:
                    harvest[row["key"]] = row
    if set(harvest) != used or any(not r.get("license_file") for r in harvest.values()):
        p.error("Missing original per-fix license-file provenance")
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for name in EXPORT_DATA_FILES:
            dest = root / "data" / name
            dest.parent.mkdir(exist_ok=True)
            shutil.copyfile(a.data / name, dest)
        for source in [SECPATCH / name for name in EXECUTION_FILES] + [SECPATCH.parent / "train_sft.py"]:
            rel = pathlib.Path("distillation") / ("secpatch" if source.parent == SECPATCH else "") / source.name
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        for name in ("run.py", "verify.py"):
            dest = root / "remote" / name
            dest.parent.mkdir(exist_ok=True)
            shutil.copyfile(HERE / name, dest)
        prov = root / "provenance"
        prov.mkdir()
        try:
            write_source_notices(prov, a.source_check, used_rows, harvest)
        except (ValueError, OSError) as exc:
            p.error(str(exc))
        (prov / "harvest.jsonl").write_text("".join(json.dumps(r) + "\n" for r in harvest.values()))
        candidates = [json.loads(x) for x in a.candidates.read_text().splitlines() if x.strip()]
        (prov / "candidates.jsonl").write_text("".join(json.dumps(r) + "\n" for r in candidates if r["key"] in used))
        a.output.mkdir(mode=0o700, parents=True, exist_ok=False)
        dataset, kernel = a.output / "dataset", a.output / "kernel"
        dataset.mkdir(mode=0o700); kernel.mkdir(mode=0o700)
        files = {str(f.relative_to(root)):digest(f) for f in sorted(root.rglob("*")) if f.is_file()}
        try:
            source_commit = subprocess.check_output(
                ["git", "-C", str(HERE), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
        except subprocess.CalledProcessError:
            # A portable execution package contains SOURCE_BASE.json instead
            # of a Git database. Its hashes still anchor unchanged core code.
            base = json.loads((HERE / "SOURCE_BASE.json").read_text())
            for name, checksum in base["core_sha256"].items():
                if digest(SECPATCH.parent / name) != checksum:
                    p.error("Portable core source differs from recorded base: " + name)
            source_commit = base["base_commit"]
        lock = {"schema": "haven-secpatch-remote-v1", "model": MODEL, "revision": REVISION,
                "max_steps": 60, "max_length": 1536, "runtime_seconds": 7200,
                "source_commit": source_commit,
                "qualification": q, "builder_replay": "identical_rows_and_manifest_except_build_timestamp",
                "source_hashes": {"osv_archive":digest(a.osv_archive), "candidates":digest(a.candidates),
                                  "harvest_in_order":[digest(h) for h in a.harvest]}, "files": files}
        # Mirror the unchanged evaluator's task filter then first-12-fix order.
        from gpu_campaign import EVAL_TASKS, MAX_EVAL_FIXES
        evaluation = [json.loads(x) for x in (a.data / "eval-heldout.jsonl").read_text().splitlines()
                      if x.strip() and json.loads(x)["task"] in EVAL_TASKS.split(",")]
        keys = list(dict.fromkeys(r["key"] for r in evaluation))[:MAX_EVAL_FIXES]
        lock["eval_identities"] = [[r["id"], r["key"], r["task"], r["label"], 0]
                                   for r in evaluation if r["key"] in keys]
        (root / "payload-lock.json").write_text(json.dumps(lock, indent=2) + "\n")
        # ZIP bytes with an opaque suffix, rather than a provider-expanded
        # dataset archive; the notebook verifies the whole container first.
        payload = dataset / "haven-secpatch.payload"
        with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(root))
        shutil.copyfile(root / "payload-lock.json", a.output / "expected-lock.json")
    (dataset / "dataset-metadata.json").write_text(json.dumps({
        "id": a.owner + "/" + a.slug + "-input", "title": "Haven R02 secpatch private input",
        "licenses": [{"name": "other"}],
        "description": "Composite original licenses and advisory attribution retained per row and fix. Private research input."
    }, indent=2))
    (kernel / "campaign.ipynb").write_text(json.dumps(notebook(digest(payload)), indent=2))
    (kernel / "kernel-metadata.json").write_text(json.dumps({
        "id": a.owner + "/" + a.slug, "title": "Haven R02 secpatch real CUDA experiment",
        "code_file": "campaign.ipynb", "language": "python", "kernel_type": "notebook",
        "is_private": True, "enable_gpu": True, "enable_tpu": False, "enable_internet": True,
        "dataset_sources": [a.owner + "/" + a.slug + "-input"],
        "competition_sources": [], "kernel_sources": [], "model_sources": []
    }, indent=2))
    print("Prepared locally; nothing uploaded or executed. Private package: " + str(a.output))


if __name__ == "__main__":
    main()
