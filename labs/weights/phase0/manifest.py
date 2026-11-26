#!/usr/bin/env python3
"""Write or check PHASE0_MANIFEST.json: what Phase 0 fixed, by hash, before any training data.

  python3 manifest.py          # rewrite after a change
  python3 manifest.py --check  # exit 1 if any recorded hash is stale

The manifest ties every Phase 0 artifact to the preregistered plan (labs/weights/PLAN.md at
commit 667bd3a, sha256 119930a9...). Phase 1+ receipts cite this file's sha256 and the commit
that holds it, so a later change to the dedupe rule, the generators, the harness pins or the
regression slice is visible as a manifest change made before the results it affects.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import dedupe  # noqa: E402
import gen_hare  # noqa: E402

PLAN = {"path": "labs/weights/PLAN.md", "commit": "667bd3a8f90dcdc11b8d55672f8d0d2ea3ff90a1",
        "sha256": "119930a934de1a7a4a58c4b6624bc4c3094090d2d1a739a3e1025df2bd086720", "pr": 124}
AMENDMENT = {"path": "labs/weights/AMENDMENT_1.md", "commit": "63bcd6e8e2b53d7559d6965fd372f4cabcf4078a",
             "sha256": "cb7954a2c384059e1acbcc904b5356f0a57e0bcb287a41160274691b124a1a1b", "pr": 124}
AMENDMENT_2 = {"path": "labs/weights/AMENDMENT_2.md", "commit": "fd2c2998ad83ff1e7da49d7ce8ca461e40d4c867",
               "sha256": "480db5838d3c7c80b5ff1d6e0d786515dc7737b47d3e086cf39c3b6610c48db7", "pr": 124}
FILES = ["deps.json", "fetch_deps.py", "common.py", "gen_hare.py", "gen_query.py", "dedupe.py", "sft.py", "pools.py",
         "flip_pairs.py", "rule8/evidence_flip_pairs.jsonl", "pools/dev_manifest.jsonl",
         "oracle_export.py", "astra_batch.py", "manifest.py", "regression/config.json",
         "regression/mmlu_pro_subset.json", "kaggle/w1_phase1.py", "kaggle/build_w1_phase1.py",
         "kaggle/llama_build_cell.py", "kaggle/w1_phase1_kaggle.ipynb", "tests/test_phase0.py",
         "tests/test_notebook_and_config.py", ".gitignore"]
OUT = HERE / "PHASE0_MANIFEST.json"


def _check(doc) -> dict:
    tree = common.REPO / doc["path"]
    if subprocess.run(["git", "-C", str(common.REPO), "cat-file", "-e", f"{doc['commit']}:{doc['path']}"],
                      capture_output=True).returncode:
        subprocess.run(["git", "-C", str(common.REPO), "fetch", "-q", "--depth=1", "origin", doc["commit"]],
                       capture_output=True)       # a shallow clone may not hold the commit
    at_commit = subprocess.run(["git", "-C", str(common.REPO), "show", f"{doc['commit']}:{doc['path']}"],
                               capture_output=True)
    return {"working_tree_matches": tree.exists() and common.sha256_file(tree) == doc["sha256"],
            "commit_matches": at_commit.returncode == 0 and common.sha256_bytes(at_commit.stdout) == doc["sha256"]}


def plan_check() -> dict:
    """PLAN.md and AMENDMENT_1.md, in the working tree and at their commits, must match their hashes."""
    p, a, b = _check(PLAN), _check(AMENDMENT), _check(AMENDMENT_2)
    return {"plan": p, "amendment_1": a, "amendment_2": b,
            "commit_matches": p["commit_matches"] and a["commit_matches"] and b["commit_matches"]}


def build() -> dict:
    import astra_batch
    import pools
    fp = dedupe.load_fingerprint()
    pairs = common.read_jsonl(HERE / "rule8" / "evidence_flip_pairs.jsonl")
    return {
        "schema": "haven-weights-phase0-manifest-1",
        "status": "PHASE 0 BUILT AGAINST PLAN.md + AMENDMENTS 1 AND 2. No GPU time, no inference, no teacher batch, no "
                  "training. Real generator seeds are drawn at Phase 1 start and posted by salted hash then.",
        "plan": PLAN,
        "amendment_1": AMENDMENT,
        "amendment_2": AMENDMENT_2,
        "gates_before_any_gpu_or_batch": [
            "Astra operational sign-off on #123 for the hardened Phase 0 implementation (#125 or reviewed successor)",
            "M4 reserve/review disposition remains closed on #119 under the owner-accepted documented AI-review deviation; "
            "do not silently restate it as an independent human review",
            "no teacher batch export or GPU collection until both the implementation gate and any newly recorded #123 prerequisite are satisfied",
        ],
        "score_views": {"model_clean": "first answer and the trace at that point pass, no blocked call before it",
                        "corrected_model": "final answer after at most one verifier revision passes, no blocked call",
                        "final_system": "final answer passes, whatever the harness did",
                        "weights_claims_use": "model_clean"},
        "no_action_stratum": {"definition": "dispositions no_action_needed + insufficient_evidence (pools.py)",
                              **{k: v for k, v in pools.frozen_no_action_rate().items() if k != "by_pool"}},
        "weighting_rule": "each episode's kept traces share a total weight of 1.0, split equally (sft.py)",
        "training_seeds_registered": [1101, 2202, 3303],
        "rule8_flip_pairs": {"file": "rule8/evidence_flip_pairs.jsonl", "public_seed": __import__("flip_pairs").SEED,
                             "flip": sum(p["kind"] == "flip" for p in pairs),
                             "control": sum(p["kind"] == "control" for p in pairs),
                             "families": sorted({p["family"] for p in pairs})},
        "dev_manifest": {"file": "pools/dev_manifest.jsonl", "rows": len(common.read_jsonl(pools.DEV_MANIFEST))},
        "teacher_exchange": {"protocol": "stepwise (astra_batch.py)", "versions": astra_batch.tool_versions(),
                             "commitment_rule": common.COMMITMENT_RULE},
        "files_sha256": {f: common.sha256_file(HERE / f) for f in FILES},
        "deps": {"main_commit": common.SPEC["main"]["commit"],
                 "sources": {s["name"]: {"pr": s["pr"], "commit": s["commit"]} for s in common.SPEC["sources"]}},
        "harness": {"mechanisms_full": common.FULL, "mechanisms_replay": common.REPLAY,
                    "keep_rule": "model-clean pass (first answer and its trace pass the adjudicator) AND zero blocked "
                                 "or duplicate calls anywhere AND transport ok; rows stop at the first answer "
                                 "(Amendment 2, D1)"},
        "reserve_collision_check": "two stages, pass/fail only: --scope prompts before any batch, --scope full "
                                   "after the pool's batches are sealed and revealed; FAIL regenerates the pool "
                                   "(Amendment 2, D3)",
        "rule_4": "unchanged: 2 absolute points per benchmark on the point estimate; paired 95% CI published; no "
                  "retries (Amendment 2, D2)",
        "private_store": "owner's Mac ~/haven-private/weights/<pool>/ plus a private Kaggle dataset for notebook "
                         "inputs only (Amendment 2, D4)",
        "dedupe": {"params": dedupe.PARAMS, "fingerprint_sha256": fp["sha256"], "dev_items": fp["counts"],
                   "structure_keys": len(fp["structures"]), "label_only_sources": sorted(dedupe.LABEL_ONLY),
                   "checks": ["8-token runs", "entity ids", "prompt lineage", "whole-item structure",
                              "WL tenant-graph hash", "question skeleton on WL-equal graph",
                              "general-mix vs regression set (check_general)"]},
        "generators": {"hare_vocabulary_overlap_with_dev": gen_hare.vocabulary_overlap(),
                       "hare_families": sorted(gen_hare.FAMILIES)},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    pc = plan_check()
    if not pc["commit_matches"]:
        raise SystemExit(f"PLAN.md or an amendment does not match its registered sha256: {pc}")
    m = build()
    if args.check:
        old = json.loads(OUT.read_text())
        stale = sorted(k for k in set(m) | set(old) if m.get(k) != old.get(k))
        print(json.dumps({"stale_sections": stale, "plan": pc}, indent=2))
        if stale:
            raise SystemExit(1)
        return
    OUT.write_text(json.dumps(m, indent=2) + "\n")
    print(json.dumps({"written": OUT.name, "sha256": common.sha256_file(OUT), "plan": pc}, indent=2))


if __name__ == "__main__":
    main()
