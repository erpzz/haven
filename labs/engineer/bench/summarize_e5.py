#!/usr/bin/env python3
"""Preregistered analysis for E5 (morphogenesis/PREREGISTRATION_E5.json).

  summarize_e5.py e5-qwen.jsonl --out ../research/e5-exhaustion-recovery.json
"""
import argparse
import json
import math
import pathlib

from summarize_e2 import med, verdict

ARMS = ["none", "recover", "controller", "controller_recover"]
COMPARISONS = {"H_R": ("recover", "none"), "H_C": ("controller", "none"), "H_CR": ("controller_recover", "controller")}
RECOVERY_ARMS = {"recover", "controller_recover"}
MIN_EVENTS = 5


def fisher_greater(a, b, c, d):
    """One-sided Fisher exact p that the first row's success rate a/(a+b) exceeds c/(c+d)."""
    n, row1, col1 = a + b + c + d, a + b, a + c
    total = math.comb(n, row1)
    return sum(math.comb(col1, k) * math.comb(n - col1, row1 - k)
               for k in range(a, min(row1, col1) + 1)) / total


def paired(rows, a, b):
    by = {(r["task"], r["seed"], r["arm"]): r for r in rows}
    wins = losses = ties = missing = 0
    for u in sorted({(r["task"], r["seed"]) for r in rows}):
        ra, rb = by.get((*u, a)), by.get((*u, b))
        if not ra or not rb:
            missing += 1
        elif ra["success"] and not rb["success"]:
            wins += 1
        elif rb["success"] and not ra["success"]:
            losses += 1
        else:
            ties += 1
    v, p = verdict(wins, losses)
    return {"comparison": f"{a} vs {b}", "wins": wins, "losses": losses, "ties": ties, "missing": missing,
            "p_one_sided": round(p, 5), "verdict": v}


def mechanism(rows):
    groups = {}
    for name, arms in (("recovery", RECOVERY_ARMS), ("baseline", set(ARMS) - RECOVERY_ARMS)):
        rs = [r for r in rows if r["arm"] in arms]
        groups[name] = {"exhausted_turns": sum(r.get("exhausted_turns", 0) for r in rs),
                        "followups": sum(r.get("exhaust_followups", 0) for r in rs),
                        "recovered": sum(r.get("exhaust_recovered", 0) for r in rs),
                        "runs_with_exhaustion": sum(r.get("exhausted_turns", 0) > 0 for r in rs),
                        "runs_ended_by_empty_replies": sum(r["agent_status"] == "error" and r.get("exhausted_turns", 0) >= 3
                                                           for r in rs)}
    rec, base = groups["recovery"], groups["baseline"]
    out = {"comparison": "turn after an exhausted turn is non-empty: recovery arms vs baseline arms", **groups}
    if rec["followups"] < MIN_EVENTS or base["followups"] < MIN_EVENTS:
        out.update(verdict="untestable", p_one_sided=None)
        return out
    p = fisher_greater(rec["recovered"], rec["followups"] - rec["recovered"],
                       base["recovered"], base["followups"] - base["recovered"])
    better = rec["recovered"] / rec["followups"] > base["recovered"] / base["followups"]
    out.update(p_one_sided=float(f"{p:.3g}"),
               verdict="supported" if better and p < 0.05 else "inconclusive" if better else "rejected")
    return out


def analyse(rows):
    hyp = {name: paired(rows, a, b) for name, (a, b) in COMPARISONS.items()}
    hyp["H_RM"] = mechanism(rows)
    table = []
    for arm in ARMS:
        rs = [r for r in rows if r["arm"] == arm]
        if rs:
            table.append([arm, f"{sum(r['success'] for r in rs)}/{len(rs)}", med([r["steps"] for r in rs]),
                          med([r["wall_s"] for r in rs]),
                          sum((r["tool_calls"] or 0) + (r.get("auto_test_runs") or 0) for r in rs),
                          sum(r.get("exhausted_turns", 0) for r in rs),
                          sum(r["agent_status"] == "error" for r in rs),
                          f"{sum(r['committed'] for r in rs)}/{len(rs)}"])
    return {"id": "e5-exhaustion-recovery",
            "title": "E5: reasoning-budget recovery and test controller on harder tasks (preregistered)",
            "status": "measured", "units": len({(r["task"], r["seed"]) for r in rows}), "runs": len(rows),
            "hypotheses": hyp,
            "table": {"columns": ["arm", "success", "median steps", "median wall s",
                                  "executor actions (incl. runtime test runs)", "exhausted turns", "errored runs",
                                  "committed"], "rows": table}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    rows = [json.loads(l) for f in args.files for l in pathlib.Path(f).read_text().splitlines() if l.strip()]
    rec = analyse(rows)
    rec["hypothesis"] = ("Handing a model the tail of reasoning that ran out of budget, with thinking off for one turn, "
                         "turns empty replies into actions and raises success on tasks a 4B model finds hard.")
    pathlib.Path(args.out).write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps(rec["hypotheses"], indent=2))
    for row in rec["table"]["rows"]:
        print(row)


if __name__ == "__main__":
    main()
