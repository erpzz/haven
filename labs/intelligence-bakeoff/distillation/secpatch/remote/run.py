"""Kaggle-only environment wrapper around the UNCHANGED secpatch campaign."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check_lock(root, lock):
    for name, expected in lock["files"].items():
        rel = pathlib.PurePosixPath(name)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Unsafe payload path")
        path = root / name
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError("Payload checksum mismatch: " + name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--payload", type=pathlib.Path, required=True)
    p.add_argument("--output", type=pathlib.Path, required=True)
    a = p.parse_args()
    # Fail before importing torch. This command cannot be used on Slink.
    if not os.environ.get("KAGGLE_KERNEL_RUN_TYPE") or not pathlib.Path("/kaggle/input").is_dir():
        p.error("Run only in a private Kaggle notebook; local GPU execution is forbidden")
    os.umask(0o077)
    os.environ.update(CUDA_VISIBLE_DEVICES="0", TOKENIZERS_PARALLELISM="false",
                      HF_HOME="/kaggle/temp/haven-hf-cache", HF_HUB_DISABLE_TELEMETRY="1",
                      WANDB_DISABLED="true")
    lock = json.loads((a.payload / "payload-lock.json").read_text())
    check_lock(a.payload, lock)
    shutil.copyfile(a.payload / "payload-lock.json", a.output / "payload-lock.json")
    secpatch = a.payload / "distillation" / "secpatch"
    sys.path.insert(0, str(secpatch))
    from gpu_campaign import qualify_data, qualify_gpu
    qualification = qualify_data(a.payload / "data")
    if qualification != lock["qualification"]:
        raise ValueError("Dataset admission differs from prepared input")
    gpu = qualify_gpu()  # Uses provider's CUDA PyTorch; no torch wheel replacement.
    (a.output / "gpu-before.json").write_text(json.dumps(gpu, indent=2))
    with (a.output / "nvidia-smi.txt").open("w") as log:
        subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv"],
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=30)
    with (a.output / "environment-setup.log").open("w") as log:
        subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                        "transformers==4.56.2", "peft==0.17.1", "accelerate==1.10.1",
                        "bandit==1.9.4", "huggingface_hub==0.34.4"],
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1200)
    from huggingface_hub import snapshot_download
    snapshot_download(lock["model"], revision=lock["revision"], token=False,
                      allow_patterns=["*.json", "*.safetensors", "*.txt", "*.jinja", "LICENSE*", "README.md"])
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    with (a.output / "versions.txt").open("w") as log:
        subprocess.run([sys.executable, "-m", "pip", "freeze"], stdout=log, check=True, timeout=30)
    started = time.monotonic()
    with (a.output / "campaign.log").open("w") as log:
        subprocess.run([sys.executable, str(secpatch / "gpu_campaign.py"),
                        "--data", str(a.payload / "data"), "--output", str(a.output / "campaign"),
                        "--model", lock["model"], "--revision", lock["revision"],
                        "--max-steps", str(lock["max_steps"]), "--max-length", str(lock["max_length"]),
                        "--execute"], stdout=log, stderr=subprocess.STDOUT, check=True)
    execution = {"provider": "Kaggle", "gpu_preflight": gpu,
                 "campaign_wall_seconds": round(time.monotonic() - started, 3),
                 "provider_quota_consumed": None,
                 "quota_note": "Compute from provider before/after snapshots; wall time is not quota usage",
                 "paid_fallback": False, "local_gpu_used": False}
    (a.output / "execution.json").write_text(json.dumps(execution, indent=2))
    from verify import verify_result
    report = verify_result(a.output, lock, secpatch)
    (a.output / "verification.json").write_text(json.dumps(report, indent=2))
    sums = {str(f.relative_to(a.output)):digest(f) for f in sorted(a.output.rglob("*")) if f.is_file()}
    (a.output / "checksums.json").write_text(json.dumps(sums, indent=2))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
