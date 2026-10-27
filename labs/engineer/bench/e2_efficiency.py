#!/usr/bin/env python3
"""Exploratory, not preregistered: Qwen's controller-vs-none efficiency in the E2 rerun, next to the
spread between arms that received identical treatment (the guard never fired for Qwen, so guard = none
and both = controller). Reads the same raw rows as summarize_e2.py and never changes them.

  e2_efficiency.py e2-qwen.jsonl --out ../research/e2-rerun-efficiency.json
"""
import argparse
import json
import statistics

METRICS = ["steps", "tool_calls", "wall_s"]
PAIRS = {"controller_vs_none": ("controller", "none"),
         "identical_guard_vs_none": ("guard", "none"),
         "identical_both_vs_controller": ("both", "controller")}


def paired(by, units, a, b, key):
    d = [by[u + (a,)][key] - by[u + (b,)][key] for u in units]
    return {"fewer": sum(x < 0 for x in d), "more": sum(x > 0 for x in d), "equal": sum(x == 0 for x in d),
            "median_diff": round(statistics.median(d), 1)}


def analyse(rows, step_cap=20):
    by = {(r["task"], r["seed"], r["arm"]): r for r in rows}
    units = sorted({(r["task"], r["seed"]) for r in rows})
    guard_fired = sum("finish_guard" in (r.get("nudges") or []) for r in rows)
    return {
        "id": "e2-rerun-efficiency", "status": "exploratory",
        "note": "Written after the preregistered verdicts in e2-rerun.json, which it does not change.",
        "agent": sorted({r["agent"] for r in rows}), "units": len(units), "guard_fired": guard_fired,
        "paired": {name: {k: paired(by, units, a, b, k) for k in METRICS} for name, (a, b) in PAIRS.items()},
        "at_step_cap": {arm: sum(by[u + (arm,)]["steps"] >= step_cap for u in units)
                        for arm in ("none", "guard", "controller", "both")},
        "runtime_test_runs": {arm: sum(by[u + (arm,)].get("auto_test_runs") or 0 for u in units)
                              for arm in ("controller", "both")},
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("rows")
    ap.add_argument("--out")
    args = ap.parse_args()
    result = analyse([json.loads(line) for line in open(args.rows)])
    text = json.dumps(result, indent=2) + "\n"
    if args.out:
        open(args.out, "w").write(text)
    print(text, end="")
