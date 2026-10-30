"""One bounded, real-CUDA secpatch LoRA campaign with held-out paired evaluation.

This launcher NEVER trains on fake fixtures or labels a CPU run as a GPU run.
It reuses secpatch/train.py and secpatch/evaluate.py; no new model backend
or model grader is introduced.

A run requires a real harvested, license-checked secpatch dataset, a pinned
locally cached open-weight model, an available CUDA GPU, and --execute.
A model adapter is NOT promoted or loaded by this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
TRAIN_TASKS = "detect,root_cause,finding_support"
EVAL_TASKS = TRAIN_TASKS
MIN_TRAIN_FIXES = 25
MIN_HELDOUT_FIXES = 8
MIN_FREE_GIB = 4.0
MAX_EVAL_FIXES = 12


class QualificationError(ValueError):
    pass


def _rows(path: pathlib.Path):
    if not path.is_file() or path.is_symlink():
        raise QualificationError("Missing or symlinked input: " + path.name)
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise QualificationError(f"{path.name}:{number}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise QualificationError(f"{path.name}:{number}: expected object")
        yield row


def digest(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as reader:
        for chunk in iter(lambda: reader.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def qualify_data(data: pathlib.Path, min_train=MIN_TRAIN_FIXES,
                 min_heldout=MIN_HELDOUT_FIXES) -> dict:
    """Do not expend a GPU-hour on arbitrary strings masquerading as real fixes."""
    if not (data / "manifest.json").is_file():
        raise QualificationError("Dataset manifest is required; run the OSV harvest/build pipeline.")
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    if (not isinstance(manifest, dict) or
            not manifest.get("osv_archive_sha256") or
            "recorded fixes" not in str(manifest.get("note", ""))):
        raise QualificationError("Missing OSV provenance or recorded-fix evidence.")
    train = list(_rows(data / "train.jsonl"))
    heldout = list(_rows(data / "eval-heldout.jsonl"))
    if not train or not heldout:
        raise QualificationError("Both true train rows and held-out evaluation are required.")
    train_repos, held_repos, train_keys, held_keys = set(), set(), set(), set()
    permissive = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0",
                  "ISC", "PSF-2.0", "0BSD", "Unlicense"}
    for split, rows, repos, keys in (
            ("train", train, train_repos, train_keys),
            ("heldout", heldout, held_repos, held_keys)):
        for row in rows:
            src, verified = row.get("source") or {}, row.get("verification") or {}
            repo = src.get("repo")
            if (row.get("split") != split or not isinstance(repo, str) or
                    not repo or not isinstance(row.get("key"), str)):
                raise QualificationError("Dataset row missing split/repository/advisory ID.")
            if (src.get("code_license") not in permissive or
                    not src.get("commit") or not src.get("parent") or
                    not src.get("advisory_ids") or
                    not all(verified.get(k) is True for k in (
                        "fix_commit_fetched", "single_parent", "permissive_license",
                        "single_function_fix", "parsed"))):
                raise QualificationError("Row lacks independently sourced, permissively licensed fix evidence.")
            messages = row.get("messages") or []
            if not isinstance(messages, list) or not messages:
                raise QualificationError("Missing source messages.")
            if split == "train":
                if messages[-1].get("role") != "assistant":
                    raise QualificationError("Training row needs a recorded answer.")
            elif messages[-1].get("role") == "assistant" or not row.get("grader"):
                raise QualificationError("Held-out row leaks its answer or lacks a grader.")
            repos.add(repo)
            keys.add((repo, row["key"]))
    if train_repos & held_repos or train_keys & held_keys:
        raise QualificationError("Training and held-out repository or advisory overlap.")
    if len(train_keys) < min_train or len(held_keys) < min_heldout:
        raise QualificationError(
            f"Insufficient real fixes: train={len(train_keys)} (need {min_train}), "
            f"heldout={len(held_keys)} (need {min_heldout}). Harvest more data.")
    return {
        "source": "license-checked OSV historical fixes",
        "train_fix_count": len(train_keys), "heldout_fix_count": len(held_keys),
        "train_repo_count": len(train_repos), "heldout_repo_count": len(held_repos),
        "train_rows": len(train), "heldout_eval_rows": len(heldout),
        "train_sha256": digest(data / "train.jsonl"),
        "heldout_sha256": digest(data / "eval-heldout.jsonl"),
        "manifest_sha256": digest(data / "manifest.json"),
        "tasks": TRAIN_TASKS,
    }


def qualify_gpu(min_free_gib: float = MIN_FREE_GIB) -> dict:
    import torch
    if not torch.cuda.is_available() or torch.cuda.device_count() < 1:
        raise QualificationError("CUDA GPU unavailable. Refusing CPU fallback or simulated GPU results.")
    props = torch.cuda.get_device_properties(0)
    free_bytes, total_bytes = torch.cuda.mem_get_info(0)
    if free_bytes < min_free_gib * (1024 ** 3):
        raise QualificationError(
            f"GPU has {free_bytes / 2**30:.2f} GiB free; requires "
            f"{min_free_gib:.2f} GiB. Haven will not unload an active model.")
    return {"device": props.name, "visible_cuda_devices": torch.cuda.device_count(),
            "total_bytes": total_bytes, "free_bytes_before_run": free_bytes,
            "compute_capability": list(torch.cuda.get_device_capability(0))}


def run_logged(argv: list[str], output: pathlib.Path, timeout_s: int) -> None:
    """Record actual child process stdout/stderr and never turn failures into success."""
    with output.open("w", encoding="utf-8") as log:
        log.write("argv=" + json.dumps(argv) + "\n")
        log.flush()
        try:
            result = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=timeout_s, check=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Timed out; see {output}") from exc
    if result.returncode:
        raise RuntimeError(f"Exit {result.returncode}; see {output}")


def campaign(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--model", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--revision", required=True, help="Immutable 40-character model commit SHA")
    parser.add_argument("--max-steps", type=int, default=60)
    parser.add_argument("--max-length", type=int, default=1536)
    parser.add_argument("--min-free-gib", type=float, default=MIN_FREE_GIB)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if (len(args.revision) != 40 or
            any(x not in "0123456789abcdef" for x in args.revision.lower())):
        parser.error("--revision must be an exact 40-character hexadecimal Hugging Face commit")
    if not 1 <= args.max_steps <= 600 or not 256 <= args.max_length <= 8192:
        parser.error("Use 1..600 optimizer steps and context length 256..8192.")
    if not MIN_FREE_GIB <= args.min_free_gib <= 80:
        parser.error("Cannot lower the enforced 4 GiB CUDA memory headroom.")
    report = qualify_data(args.data)
    report.update({"model": args.model, "revision": args.revision,
                   "max_steps_requested": args.max_steps, "execute": args.execute})
    if not args.execute:
        print(json.dumps({"classification": "DATA_PREFLIGHT_ONLY_NOT_TRAINING", **report}, indent=2))
        return report
    if args.output.exists():
        raise QualificationError("Output path already exists; use a new path to preserve prior receipts.")
    # Preflight CUDA and memory BEFORE touching the training environment.
    gpu = qualify_gpu(args.min_free_gib)
    os.umask(0o077)
    args.output.mkdir(parents=True, mode=0o700)
    report["gpu_preflight"] = gpu
    (args.output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    base = [sys.executable, str(HERE / "train.py"), "--data", str(args.data / "train.jsonl"),
            "--tasks", TRAIN_TASKS, "--model", args.model, "--revision", args.revision,
            "--output", str(args.output / "training"), "--device", "cuda",
            "--max-steps", str(args.max_steps), "--max-length", str(args.max_length),
            "--batch", "8", "--save-steps", "30", "--execute"]
    run_logged(base, args.output / "train.log", timeout_s=10800)
    from registry import passes_quality_gate, verify_training_artifacts
    receipt_path = args.output / "training" / "receipt.json"
    if not receipt_path.is_file():
        raise RuntimeError("Trainer did not write a GPU receipt.")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    weights = verify_training_artifacts(args.output / "training", receipt)
    if receipt["data_sha256"] != report["train_sha256"]:
        raise RuntimeError("Training dataset changed during execution; refusing evaluation.")
    if digest(args.data / "eval-heldout.jsonl") != report["heldout_sha256"]:
        raise RuntimeError("Held-out dataset changed during training; refusing evaluation.")
    # Independent, unchanged base versus learned adapter on identical real
    # held-out security fixes. No promotion happens even if the adapter wins.
    summaries = {}
    for arm in ("base", "adapter"):
        cmd = [sys.executable, str(HERE / "evaluate.py"), "--eval",
               str(args.data / "eval-heldout.jsonl"), "--out", str(args.output / arm),
               "--backend", "hf", "--model", args.model, "--revision", args.revision,
               "--device", "cuda", "--tasks", EVAL_TASKS, "--limit", str(MAX_EVAL_FIXES)]
        if arm == "adapter":
            cmd.extend(["--adapter", str(args.output / "training" / "adapter")])
        run_logged(cmd, args.output / (arm + ".log"), timeout_s=10800)
        sums = args.output / arm / "summary.json"
        if not sums.exists():
            raise RuntimeError(f"Missing {arm} evaluation summary")
        summaries[arm] = json.loads(sums.read_text(encoding="utf-8"))
    a, b = summaries["adapter"], summaries["base"]
    if a.get("eval_sha256") != b.get("eval_sha256") or a.get("n") != b.get("n"):
        raise RuntimeError("Base/adapter evaluated on inconsistent held-out sets")
    final = {
        "classification": "GPU_TRAINED_AND_HELDOUT_EVALUATED",
        "status": "verified_result_not_production_promoted",
        "dataset": report, "train_receipt": receipt, "weights": weights,
        "base": b, "adapter": a,
        "improved_vs_base": passes_quality_gate(a, b),
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (args.output / "campaign-result.json").write_text(json.dumps(final, indent=2) + "\n")
    print(json.dumps({"classification": final["classification"],
                      "base_score": b["score"], "adapter_score": a["score"],
                      "improved_vs_base": final["improved_vs_base"],
                      "report": str(args.output / "campaign-result.json")}))
    return final


if __name__ == "__main__":
    campaign()
