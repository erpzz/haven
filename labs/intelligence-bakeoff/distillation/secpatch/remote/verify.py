"""CPU-only verification of downloaded real artifacts. Never fabricates receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys


def rows(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def verify_result(result, lock, secpatch):
    sys.path.insert(0, str(secpatch))
    from registry import verify_training_artifacts
    campaign = result / "campaign"
    final = json.loads((campaign / "campaign-result.json").read_text())
    receipt = json.loads((campaign / "training" / "receipt.json").read_text())
    weights = verify_training_artifacts(campaign / "training", receipt)
    if final.get("classification") != "GPU_TRAINED_AND_HELDOUT_EVALUATED":
        raise ValueError("Campaign did not finish real training and evaluation")
    if final.get("train_receipt") != receipt or final.get("weights") != weights:
        raise ValueError("Campaign embeds different training evidence")
    if (receipt.get("base_model") != lock["model"] or receipt.get("base_revision") != lock["revision"] or
            receipt.get("data_sha256") != lock["qualification"]["train_sha256"] or
            receipt.get("optimizer_steps") != lock["max_steps"] or receipt.get("rows_encoded", 0) < 1):
        raise ValueError("Training differs from the locked campaign")
    if {k:final["dataset"].get(k) for k in lock["qualification"]} != lock["qualification"]:
        raise ValueError("Campaign dataset differs from prepared qualification")
    arms, identities = {}, {}
    for arm in ("base", "adapter"):
        items = rows(campaign / arm / "items.jsonl")
        identities[arm] = [(r["id"], r["key"], r["task"], r["label"], r["seed"]) for r in items]
        if not items or len(set(identities[arm])) != len(items):
            raise ValueError("Empty or duplicated evaluation items")
        if any(r.get("error") or not r.get("completion_tokens") for r in items):
            raise ValueError("Evaluation contains generation errors or empty generations")
        summary = json.loads((campaign / arm / "summary.json").read_text())
        if (summary.get("n") != len(items) or summary.get("seeds") != "0" or
                summary.get("temperature") != 0.0 or summary.get("backend") != "hf" or
                summary.get("classification") != "MEASURED_ON_HELD_OUT"):
            raise ValueError("Evaluation summary does not match campaign settings")
        selected_sha = hashlib.sha256(json.dumps([r["id"] for r in items]).encode()).hexdigest()
        if summary.get("eval_sha256") != selected_sha or final.get(arm) != summary:
            raise ValueError("Evaluation summary/ID digest mismatch")
        expected_model = lock["model"] + "@" + lock["revision"][:7]
        if arm == "adapter":
            expected_model += "+training"
        if summary.get("model") != expected_model:
            raise ValueError("Wrong evaluation model or adapter arm")
        score = round(sum(r["score"] for r in items) / len(items), 4)
        neg = [r for r in items if r["task"] == "detect" and r["label"] == "not_vulnerable"]
        if not neg or summary["score"] != score or summary["false_positive_rate"] != round(
                sum(r["false_positive"] for r in neg) / len(neg), 4):
            raise ValueError("Recomputed score/FPR differs or no fixed-code controls")
        arms[arm] = summary
    if identities["base"] != identities["adapter"]:
        raise ValueError("Base and adapter used different ordered evaluation items")
    # The lock carries the expected held-out selection, without targets.
    if [list(x) for x in identities["base"]] != lock["eval_identities"]:
        raise ValueError("Evaluated items differ from prepared held-out selection")
    return {"classification": "VERIFIED_SAVED_ADAPTER_AND_MATCHED_HELDOUT",
            "evidence_limit": "runtime observations and byte identity; not cryptographic hardware attestation",
            "weights": weights, "evaluation_rows_per_arm": len(identities["base"]),
            "base_score": arms["base"]["score"], "adapter_score": arms["adapter"]["score"],
            "base_fpr": arms["base"]["false_positive_rate"],
            "adapter_fpr": arms["adapter"]["false_positive_rate"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--result", type=pathlib.Path, required=True)
    p.add_argument("--expected-lock", type=pathlib.Path, required=True,
                   help="Original LOCAL lock, not the downloaded copy")
    a = p.parse_args()
    lock = json.loads(a.expected_lock.read_text())
    if json.loads((a.result / "payload-lock.json").read_text()) != lock:
        p.error("Downloaded lock differs from original local input")
    checksums = json.loads((a.result / "checksums.json").read_text())
    for name, checksum in checksums.items():
        rel = pathlib.PurePosixPath(name)
        if rel.is_absolute() or ".." in rel.parts:
            p.error("Unsafe result path")
        path = a.result / name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
            p.error("Downloaded checksum mismatch: " + name)
    watchdog = json.loads((a.result / "watchdog.json").read_text())
    if (watchdog.get("status") != "COMPLETED" or watchdog.get("exit_code") != 0 or
            watchdog.get("budget_seconds") != lock["runtime_seconds"] or
            not 0 < watchdog.get("wall_seconds", 0) <= lock["runtime_seconds"] + 15):
        p.error("Watchdog did not observe a successful bounded run")
    secpatch = pathlib.Path(__file__).resolve().parent.parent
    # Use local reviewed verification code, and ensure core source identity.
    for path in secpatch.glob("*.py"):
        name = "distillation/secpatch/" + path.name
        if name in lock["files"] and hashlib.sha256(path.read_bytes()).hexdigest() != lock["files"][name]:
            p.error("Local core code differs from submitted source: " + path.name)
    print(json.dumps(verify_result(a.result, lock, secpatch), indent=2))


if __name__ == "__main__":
    main()
