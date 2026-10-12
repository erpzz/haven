"""Build privacy-scoped distillation datasets from frozen, synthetic R02 bakeoff runs.

No live tool/model access, API calls, or training. Outputs are local and gitignored.
SRD-inspired foresight targets require independently reviewed hindsight annotations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
BAKEOFF = HERE.parent
sys.path.insert(0, str(BAKEOFF))
from score import score_row  # noqa: E402

TRUSTED_TASKS = BAKEOFF / "tasks.json"
ALLOWED_PRINCIPALS = {"user-a", "user-b"}
MAX_FIELD = 16000


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(obj):
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def read_jsonl(path):
    if not path:
        return []
    rows = []
    with pathlib.Path(path).open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError(f"{path}:{number}: expected object")
            rows.append(obj)
    return rows


def write_jsonl(path, records):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for item in records:
            handle.write(canonical(item) + "\n")


def load_fixtures(tasks_path=TRUSTED_TASKS):
    # This explicit limitation avoids inadvertently processing private task exports.
    if pathlib.Path(tasks_path).resolve() != TRUSTED_TASKS.resolve():
        raise ValueError("Only checked-in synthetic tasks.json is accepted.")
    tasks = json.loads(TRUSTED_TASKS.read_text(encoding="utf-8"))
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("Missing synthetic tasks.")
    found = {}
    for task in tasks:
        if task["id"] in found or task.get("principal") not in ALLOWED_PRINCIPALS:
            raise ValueError("Duplicate task or unexpected principal.")
        if len(task["prompt"]) > MAX_FIELD:
            raise ValueError("Oversize prompt.")
        found[task["id"]] = task
    return found


def split_ids(tasks, eval_fraction=0.25, seed="haven-distillation-v1"):
    if len(tasks) < 2 or not (0 < eval_fraction < 1):
        raise ValueError("Need at least two tasks and eval fraction in (0,1).")
    ranked = sorted(tasks, key=lambda task_id: hashlib.sha256(
        (seed + "\0" + task_id).encode("utf-8")).digest())
    n_eval = max(1, min(len(ranked) - 1, round(len(ranked) * eval_fraction)))
    return set(ranked[:-n_eval]), set(ranked[-n_eval:])


def source_prompt(task):
    return ("You are a bounded Haven assistant. Actions are proposals only; "
            "never invent tool evidence or bypass another user's access. "
            f"Authenticated principal: {task['principal']}\n\nTask: {task['prompt']}")


def tool_evidence(row):
    observations = []
    for event in row.get("tool_trace") or []:
        if not isinstance(event, dict) or not isinstance(event.get("output"), dict):
            raise ValueError("Unexpected tool observation shape.")
        # Ignore caller-supplied principal, as bakeoff binds identity outside the model.
        observations.append({
            "tool": str(event.get("name", ""))[:100],
            "arguments": {k: v for k, v in (event.get("arguments") or {}).items()
                          if k != "principal"},
            "result": event["output"],
        })
    return observations


def make_annotation_queue(task, row, outcome):
    # Failure traces remain ONLY in the local review queue, not training targets.
    return {
        "task": task["id"],
        "source_digest": digest(row),
        "principal": task["principal"],
        "result": outcome,
        "observations": tool_evidence(row),
        "answer": str(row.get("answer", ""))[:MAX_FIELD],
        "reviewed": False,
        "foresight": "",
        "notes": "Human/teacher reviewer: state a verifiable, prospective lesson; "
                 "do not paste private facts or failed completions.",
    }


def build(rows, annotations=None, eval_fraction=0.25, seed="haven-distillation-v1"):
    tasks = load_fixtures()
    train_ids, eval_ids = split_ids(tasks, eval_fraction, seed)
    annotations = annotations or []
    approved = {}
    for item in annotations:
        if item.get("reviewed") is not True:
            continue
        key = (item.get("task"), item.get("source_digest"))
        foresight = item.get("foresight", "")
        if (not isinstance(foresight, str) or not foresight.strip()
                or len(foresight) > 3000 or key in approved):
            raise ValueError("Reviewed annotation needs unique, bounded foresight.")
        if not isinstance(item.get("evidence"), str) or len(item["evidence"].strip()) < 5:
            raise ValueError("Reviewed annotation must cite supporting evidence.")
        approved[key] = item

    success, foresight_data, policy, review, outcomes = [], [], [], [], Counter()
    for task_id in sorted(train_ids):
        task = tasks[task_id]
        policy.append({"task": task_id, "prompt": source_prompt(task)})
    for row in rows:
        task_id = row.get("task")
        if task_id not in tasks:
            raise ValueError(f"Unknown task in input: {task_id!r}")
        task = tasks[task_id]
        if row.get("principal") != task["principal"]:
            raise ValueError("Principal mismatch: possible cross-user contamination.")
        if not isinstance(row.get("answer", ""), str):
            raise ValueError("Answer must be text.")
        if len(row.get("answer", "")) > MAX_FIELD:
            raise ValueError("Oversize answer; refusing to process.")
        if task_id in eval_ids:
            # Evaluate on entirely different task IDs; never train on these traces.
            outcomes["held_out_rows"] += 1
            continue
        passed = score_row(task, row)
        observations = tool_evidence(row)
        row_digest = digest(row)
        outcomes["train_rows"] += 1
        if passed["pass"]:
            # Ground the answer using the actually observed tool results, not a
            # hallucinated "successful" reply directly after a bare task prompt.
            evidence_text = canonical(observations)
            prompt = source_prompt(task) + "\n\nObserved tool results (read-only): " + evidence_text
            if len(prompt) > MAX_FIELD:
                outcomes["oversize_skipped"] += 1
                continue
            success.append({
                "task": task_id, "source_digest": row_digest,
                "recipe": "verified_success_sft", "prompt": prompt,
                "completion": row["answer"], "validated_by": "synthetic_bakeoff_score",
            })
            outcomes["verified_success"] += 1
        else:
            review.append(make_annotation_queue(task, row, passed))
            outcomes["failure_to_review"] += 1
        note = approved.pop((task_id, row_digest), None)
        if note:
            # This prompt deliberately excludes any trajectory/results/hindsight.
            foresight_data.append({
                "task": task_id, "source_digest": row_digest,
                "recipe": "reviewed_foresight_sft",
                "prompt": "Before using any tools, anticipate likely pitfalls.\n"
                          + source_prompt(task),
                "completion": note["foresight"].strip(),
                "validated_by": note["evidence"].strip(),
            })
            outcomes["reviewed_foresight"] += 1
    if approved:
        raise ValueError("Reviewed annotation did not match a training trajectory.")
    sets = {"success.jsonl": success, "foresight.jsonl": foresight_data,
            "policy_prompts.jsonl": policy, "review_queue.jsonl": review}
    manifest = {
        "schema": "haven-distillation-1",
        "source": "checked-in synthetic R02 fixtures only",
        "training_status": "NOT_EXECUTED",
        "accuracy_claim": "NONE",
        "seed": seed,
        "train_task_ids": sorted(train_ids),
        "holdout_task_ids": sorted(eval_ids),
        "counts": dict(outcomes),
        "files": {key: len(val) for key, val in sets.items()},
        "method_note": "Foresight SFT is an SRD-inspired proxy, NOT a reproduction "
                       "of the paper's policy-training method.",
    }
    return sets, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=pathlib.Path, required=True)
    parser.add_argument("--annotations", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, default=HERE / "data")
    parser.add_argument("--eval-fraction", type=float, default=0.25)
    parser.add_argument("--seed", default="haven-distillation-v1")
    parser.add_argument("--synthetic-only", action="store_true", required=True,
                        help="Confirm runs use ONLY R02 synthetic fixtures.")
    args = parser.parse_args(argv)
    sets, manifest = build(read_jsonl(args.runs), read_jsonl(args.annotations),
                           args.eval_fraction, args.seed)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, records in sets.items():
        write_jsonl(args.output / name, records)
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
