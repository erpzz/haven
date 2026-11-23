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
FILES = ["deps.json", "fetch_deps.py", "common.py", "gen_hare.py", "gen_query.py", "dedupe.py", "sft.py",
         "oracle_export.py", "astra_batch.py", "manifest.py", "regression/config.json",
         "regression/mmlu_pro_subset.json", "kaggle/w1_phase1.py", "kaggle/build_w1_phase1.py",
         "kaggle/llama_build_cell.py", "kaggle/w1_phase1_kaggle.ipynb", "tests/test_phase0.py",
         "tests/test_notebook_and_config.py", ".gitignore"]
OUT = HERE / "PHASE0_MANIFEST.json"


def plan_check() -> dict:
    """PLAN.md in the working tree and at its preregistration commit must both match."""
    tree = common.REPO / PLAN["path"]
    at_commit = subprocess.run(["git", "-C", str(common.REPO), "show", f"{PLAN['commit']}:{PLAN['path']}"],
                               capture_output=True)
    return {"working_tree_matches": tree.exists() and common.sha256_file(tree) == PLAN["sha256"],
            "commit_matches": at_commit.returncode == 0 and common.sha256_bytes(at_commit.stdout) == PLAN["sha256"]}


def build() -> dict:
    fp = dedupe.load_fingerprint()
    return {
        "schema": "haven-weights-phase0-manifest-1",
        "status": "PHASE 0 BUILT. No GPU time, no inference, no teacher batch, no training. Real training seeds "
                  "are drawn at Phase 1 start and posted by salted hash then.",
        "plan": PLAN,
        "gates_before_any_gpu_or_batch": ["Astra 6.2 DECISION: sign-off on #123 (PLAN.md review)",
                                          "M4 reserve salted digest posted on #119"],
        "files_sha256": {f: common.sha256_file(HERE / f) for f in FILES},
        "deps": {"main_commit": common.SPEC["main"]["commit"],
                 "sources": {s["name"]: {"pr": s["pr"], "commit": s["commit"]} for s in common.SPEC["sources"]}},
        "harness": {"mechanisms_full": common.FULL, "mechanisms_replay": common.REPLAY,
                    "keep_rule": "adjudicator pass against gold AND zero blocked or duplicate calls AND transport ok"},
        "dedupe": {"params": dedupe.PARAMS, "fingerprint_sha256": fp["sha256"], "dev_items": fp["counts"],
                   "label_only_sources": sorted(dedupe.LABEL_ONLY)},
        "generators": {"hare_vocabulary_overlap_with_dev": gen_hare.vocabulary_overlap(),
                       "hare_families": sorted(gen_hare.FAMILIES)},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    pc = plan_check()
    if not pc["commit_matches"]:
        raise SystemExit(f"PLAN.md at {PLAN['commit']} does not match the preregistered sha256: {pc}")
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
