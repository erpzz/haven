#!/usr/bin/env python3
"""Preregistered analysis for the E2 rerun (morphogenesis/PREREGISTRATION_E2.json).

  summarize_e2.py e2-qwen.jsonl e2-lfm.jsonl --out ../research/e2-rerun.json
"""
import argparse
import json
import math
import pathlib
import statistics

ARMS = ["none", "guard", "controller", "both"]
COMPARISONS = {"H_E2": ("controller", "none"), "H_G": ("guard", "none"), "H_GC": ("both", "controller")}


def sign_test(wins, losses):
    """Exact one-sided P(X >= wins) for X ~ Binomial(wins + losses, 0.5)."""
    n = wins + losses
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(wins, n + 1)) / 2 ** n


def verdict(wins, losses):
    p = sign_test(wins, losses)
    if losses >= wins:
        return "rejected", p
    if p < 0.05 and wins - losses >= 4:
        return "supported", p
    return "inconclusive", p


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None


def analyse(rows):
    by = {(r["agent"], r["task"], r["seed"], r["arm"]): r for r in rows}
    units = sorted({(r["agent"], r["task"], r["seed"]) for r in rows})
    hyp = {}
    for name, (a, b) in COMPARISONS.items():
        wins = losses = ties = missing = 0
        for u in units:
            ra, rb = by.get((*u, a)), by.get((*u, b))
            if not ra or not rb:
                missing += 1
                continue
            if ra["success"] and not rb["success"]:
                wins += 1
            elif rb["success"] and not ra["success"]:
                losses += 1
            else:
                ties += 1
        v, p = verdict(wins, losses)
        hyp[name] = {"comparison": f"{a} vs {b}", "wins": wins, "losses": losses, "ties": ties,
                     "missing": missing, "p_one_sided": round(p, 5), "verdict": v}
    table = []
    for agent in sorted({u[0] for u in units}):
        for arm in ARMS:
            rs = [r for r in rows if r["agent"] == agent and r["arm"] == arm]
            if not rs:
                continue
            table.append([agent, arm, f"{sum(r['success'] for r in rs)}/{len(rs)}", med([r["steps"] for r in rs]),
                          med([r["wall_s"] for r in rs]),
                          sum((r["tool_calls"] or 0) + (r.get("auto_test_runs") or 0) for r in rs),
                          sum("finish_guard" in (r.get("nudges") or []) for r in rs),
                          f"{sum(r['committed'] for r in rs)}/{len(rs)}"])
    return {"id": "e2-rerun", "title": "E2 rerun: runtime-invoked skill and premature-finish guard (preregistered)",
            "status": "measured", "units": len(units), "runs": len(rows), "hypotheses": hyp,
            "table": {"columns": ["agent", "arm", "success", "median steps", "median wall s",
                                  "executor actions (incl. runtime test runs)", "guard fired", "committed"],
                      "rows": table}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    rows = [json.loads(l) for f in args.files for l in pathlib.Path(f).read_text().splitlines() if l.strip()]
    rec = analyse(rows)
    rec["hypothesis"] = "Wiring an inherited skill into the controller helps small models more than offering tools alone; a premature-finish guard helps models that stop early."
    pathlib.Path(args.out).write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps(rec["hypotheses"], indent=2))
    for row in rec["table"]["rows"]:
        print(row)


if __name__ == "__main__":
    main()
