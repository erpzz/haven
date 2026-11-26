#!/usr/bin/env python3
"""CPU-only rescore of a frozen W1 Phase-1 run under the current W1 keep rule.

This never runs a model and never mutates the frozen run directory. It verifies the
transcript/metric receipt pairing, recomputes common.judge() for every terminal record,
and writes a separate repaired view containing rescored metrics, kept SFT rows, hard
episode ids, and a public-safe aggregate summary.

Example:
  python3 rescore_w1.py \
    --episodes-root ~/haven-private/weights/w1-pilot \
    --episodes-sha256 HEX \
    --run-dir ~/haven-private/weights/w1-pilot/phase1/w1-phase1 \
    --out ~/haven-private/weights/w1-pilot/phase1/rescore-auth-guard-v1
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib

import common
import sft

KEEP_PER_EPISODE = 2
TEACHER = "qwen35-4b-self"
G1 = (0.15, 0.85)


def _indexed(rows, *, kind):
    out = {}
    for row in rows:
        key = (row.get("episode"), row.get("attempt"))
        if key[0] is None or not isinstance(key[1], int):
            raise SystemExit(f"{kind} has malformed episode/attempt identity")
        if key in out:
            raise SystemExit(f"{kind} contains duplicate slot {key}")
        out[key] = row
    return out


def _family_summary(episodes, old_metrics, new_metrics):
    old_by = collections.defaultdict(list)
    new_by = collections.defaultdict(list)
    for m in old_metrics:
        old_by[m["episode"]].append(m)
    for m in new_metrics:
        new_by[m["episode"]].append(m)
    out = {}
    for family in sorted({e["family"] for e in episodes}):
        ids = [e["id"] for e in episodes if e["family"] == family]
        out[family] = {
            "episodes": len(ids),
            "attempts": sum(len(new_by[eid]) for eid in ids),
            "old_kept_attempts": sum(sum(bool(m.get("keep")) for m in old_by[eid]) for eid in ids),
            "new_kept_attempts": sum(sum(bool(m.get("keep")) for m in new_by[eid]) for eid in ids),
            "old_solved": sum(any(bool(m.get("keep")) for m in old_by[eid]) for eid in ids),
            "new_solved": sum(any(bool(m.get("keep")) for m in new_by[eid]) for eid in ids),
        }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ep = ap.add_mutually_exclusive_group(required=True)
    ep.add_argument("--episodes")
    ep.add_argument("--episodes-root", help="search recursively for the unique JSONL matching --episodes-sha256")
    ap.add_argument("--episodes-sha256", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    os.umask(0o077)
    run_dir = pathlib.Path(args.run_dir).expanduser().resolve()
    out = pathlib.Path(args.out).expanduser().resolve()

    if args.episodes:
        episodes_path = pathlib.Path(args.episodes).expanduser().resolve()
        if common.sha256_file(episodes_path) != args.episodes_sha256:
            raise SystemExit("episodes file does not match the frozen SHA-256")
    else:
        root = pathlib.Path(args.episodes_root).expanduser().resolve()
        candidates = []
        for path in root.rglob("*.jsonl"):
            try:
                if common.sha256_file(path) == args.episodes_sha256:
                    candidates.append(path.resolve())
            except (OSError, PermissionError):
                pass
        if len(candidates) != 1:
            raise SystemExit(
                f"expected exactly one episode JSONL matching the frozen SHA under {root}; "
                f"found {len(candidates)}"
            )
        episodes_path = candidates[0]
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty; refusing to overwrite a prior rescore")
    out.mkdir(parents=True, exist_ok=True)

    attempts_path = run_dir / "attempts.jsonl"
    metrics_path = run_dir / "metrics.jsonl"
    if not attempts_path.is_file() or not metrics_path.is_file():
        raise SystemExit("run-dir must contain attempts.jsonl and metrics.jsonl")

    episodes = common.read_jsonl(episodes_path)
    if len({e["id"] for e in episodes}) != len(episodes):
        raise SystemExit("episodes file contains duplicate ids")
    episode_index = {e["id"]: e for e in episodes}

    records = _indexed(common.read_jsonl(attempts_path), kind="transcript")
    old_metrics_map = _indexed(common.read_jsonl(metrics_path), kind="metric")
    if set(records) != set(old_metrics_map):
        raise SystemExit("transcript and metric slot sets differ")

    run_ids = {r.get("run_id") for r in records.values()} | {m.get("run_id") for m in old_metrics_map.values()}
    if len(run_ids) != 1 or None in run_ids:
        raise SystemExit("run identity is inconsistent across receipts")
    run_id = next(iter(run_ids))

    episode_ids = {eid for eid, _ in records}
    if episode_ids != set(episode_index):
        raise SystemExit("receipt episode set does not equal the frozen episode file")

    attempts_per_episode = collections.Counter(eid for eid, _ in records)
    attempt_counts = set(attempts_per_episode.values())
    if len(attempt_counts) != 1:
        raise SystemExit(f"non-uniform frozen attempt grid: {sorted(attempt_counts)}")
    attempts = next(iter(attempt_counts))
    expected_slots = {(eid, k) for eid in episode_index for k in range(attempts)}
    if set(records) != expected_slots:
        raise SystemExit("frozen receipt grid is not the exact episode x attempt Cartesian grid")

    for key, rec in records.items():
        old = old_metrics_map[key]
        if old.get("run_id") != run_id:
            raise SystemExit(f"metric run-id mismatch at {key}")
        if old.get("record_sha256") != common.sha256_bytes(common.canonical(rec)):
            raise SystemExit(f"metric/transcript SHA mismatch at {key}")

    new_metrics_map = {}
    guard_counts = collections.Counter()
    newly_rejected = []
    newly_accepted = []
    diagnostic_drift = []
    episode_order = {e["id"]: i for i, e in enumerate(episodes)}
    ordered_keys = sorted(records, key=lambda x: (x[1], episode_order[x[0]]))

    for key in ordered_keys:
        rec, old = records[key], old_metrics_map[key]
        e = episode_index[key[0]]
        scored = common.judge(rec, e, apply_w1_training_guard=True)
        new = dict(old)
        new.update(scored)
        # Identity/receipt fields are immutable evidence from the frozen run.
        for field in ("episode", "family", "attempt", "seed", "temperature", "seconds",
                      "run_id", "slot_status", "record_sha256"):
            if field in old:
                new[field] = old[field]
        new_metrics_map[key] = new
        if old.get("views") != new.get("views") or bool(old.get("raw_pass")) != bool(new.get("raw_pass")):
            diagnostic_drift.append(key)
        for v in new.get("w1_semantic_guard_violations") or []:
            guard_counts[v] += 1
        if bool(old.get("keep")) and not bool(new.get("keep")):
            newly_rejected.append(key)
        if not bool(old.get("keep")) and bool(new.get("keep")):
            newly_accepted.append(key)

    if newly_accepted:
        raise SystemExit("guard-only rescore unexpectedly accepted previously unkept trajectories")
    if diagnostic_drift:
        raise SystemExit(
            f"guard-only rescore changed frozen diagnostic scoring at {len(diagnostic_drift)} slots"
        )

    old_metrics = [old_metrics_map[k] for k in ordered_keys]
    new_metrics = [new_metrics_map[k] for k in ordered_keys]

    by_ep = collections.defaultdict(list)
    for m in new_metrics:
        by_ep[m["episode"]].append(m)

    rows = []
    hard = []
    for e in episodes:
        ms = sorted(by_ep[e["id"]], key=lambda m: m["attempt"])
        kept = [m for m in ms if m["keep"]][:KEEP_PER_EPISODE]
        if len(ms) == attempts and not kept:
            hard.append(e["id"])
        for m in kept:
            rows += sft.rows_from_record(
                records[(e["id"], m["attempt"])],
                source="w1",
                arm="A",
                teacher=TEACHER,
            )
    rows = sft.apply_episode_weights(rows)

    metrics_out = out / "metrics.rescored.jsonl"
    kept_out = out / "kept-rows.rescored.jsonl"
    hard_out = out / "hard-episodes.rescored.txt"
    common.write_jsonl(metrics_out, new_metrics)
    common.write_jsonl(kept_out, rows)
    hard_out.write_text("\n".join(hard) + ("\n" if hard else ""))

    old_kept = sum(bool(m.get("keep")) for m in old_metrics)
    new_kept = sum(bool(m.get("keep")) for m in new_metrics)
    old_by_ep = collections.defaultdict(list)
    for m in old_metrics:
        old_by_ep[m["episode"]].append(m)
    old_solved = sum(any(bool(m.get("keep")) for m in old_by_ep[e["id"]]) for e in episodes)
    new_solved = sum(any(bool(m.get("keep")) for m in by_ep[e["id"]]) for e in episodes)
    rate = new_kept / len(new_metrics) if new_metrics else 0.0

    summary = {
        "schema": "haven-w1-private-rescore-auth-scope-1",
        "run_id": run_id,
        "episodes_sha256": common.sha256_file(episodes_path),
        "input_receipts": {
            "attempts_sha256": common.sha256_file(attempts_path),
            "metrics_sha256": common.sha256_file(metrics_path),
            "slots": len(records),
            "episodes": len(episodes),
            "attempts_per_episode": attempts,
        },
        "old_strict_kept_attempts": old_kept,
        "new_strict_kept_attempts": new_kept,
        "newly_rejected_by_current_keep_rule": len(newly_rejected),
        "affected_episode_count": len({eid for eid, _ in newly_rejected}),
        "diagnostic_view_drift_slots": 0,
        "guard_violation_counts": dict(sorted(guard_counts.items())),
        "old_solved_episodes": old_solved,
        "new_solved_episodes": new_solved,
        "old_hard_episodes": len(episodes) - old_solved,
        "new_hard_episodes": len(episodes) - new_solved,
        "new_passing_rate": round(rate, 6),
        "gate_G1_band": list(G1),
        "gate_G1_in_band": G1[0] <= rate <= G1[1],
        "new_kept_rows": len(rows),
        "new_kept_rows_sha256": common.sha256_file(kept_out),
        "new_hard_episodes_sha256": common.sha256_file(hard_out),
        "rescored_metrics_sha256": common.sha256_file(metrics_out),
        "by_family": _family_summary(episodes, old_metrics, new_metrics),
    }
    if (run_dir / "kept-rows.jsonl").is_file():
        summary["old_kept_rows_sha256"] = common.sha256_file(run_dir / "kept-rows.jsonl")
    if (run_dir / "hard-episodes.txt").is_file():
        summary["old_hard_episodes_sha256"] = common.sha256_file(run_dir / "hard-episodes.txt")

    summary_path = out / "rescore-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
