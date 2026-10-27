#!/usr/bin/env python3
"""Summarize E1 benchmark rows into the sanitized research record, applying the preregistered rules.

  summarize.py results-qwen.jsonl results-lfm.jsonl --out ../research/e1-inheritance.json
"""
import argparse
import json
import pathlib
import statistics

HERE = pathlib.Path(__file__).resolve().parent
ARMS = ["none", "recipe", "skill", "controller"]


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    rows = [json.loads(l) for f in args.files for l in pathlib.Path(f).read_text().splitlines() if l.strip()]
    agents = sorted({r["agent"] for r in rows})
    table = []
    cell = {}
    for a in agents:
        for arm in ARMS:
            rs = [r for r in rows if r["agent"] == a and r["arm"] == arm]
            if not rs:
                continue
            c = {"success": sum(r["success"] for r in rs), "n": len(rs),
                 "steps": med([r["steps"] for r in rs]), "waste": sum(r["discovery_waste"] for r in rs),
                 "wall": med([r["wall_s"] for r in rs]), "skill_calls": sum(r.get("skill_calls", 0) for r in rs),
                 "auto": sum(r.get("auto_test_runs", 0) for r in rs),
                 "committed": sum(r["committed"] for r in rs)}
            cell[(a, arm)] = c
            table.append([a, arm, f"{c['success']}/{c['n']}", c["steps"], c["waste"], c["wall"],
                          c["skill_calls"], c["auto"], f"{c['committed']}/{c['n']}"])
    tot = lambda arm: sum(cell[(a, arm)]["success"] for a in agents if (a, arm) in cell)
    used = sum(cell[(a, "skill")]["skill_calls"] for a in agents if (a, "skill") in cell)

    def judge(diff, supported):
        # Preregistered: effects smaller than 2 tasks are inconclusive; a skill never executed cannot be credited.
        if used == 0:
            return "not attributable: the skill tool was never called"
        if abs(diff) < 2:
            return "inconclusive (difference under 2 tasks)"
        return "supported" if supported else "rejected"

    d1 = tot("skill") - tot("none")
    d2 = tot("skill") - tot("recipe")
    verdicts = {
        "H1 skill tool vs tools-only": judge(d1, d1 > 0),
        "H2 skill tool vs prose recipe": judge(d2, d2 > 0),
        "H3 discovery waste with skill tool": judge(2, sum(cell[(a, "skill")]["waste"] for a in agents if (a, "skill") in cell)
                                                    < sum(cell[(a, "none")]["waste"] for a in agents if (a, "none") in cell)),
        "skill tool calls (all agents)": used,
    }
    if (agents and all((a, "controller") in cell for a in agents)):
        dc = tot("controller") - tot("none")
        verdicts["E2 controller vs tools-only (exploratory)"] = (
            "inconclusive (difference under 2 tasks)" if abs(dc) < 2 else ("better" if dc > 0 else "worse"))
    rec = {"id": "e1-inheritance", "title": "E1: inherited run_tests skill on unseen bug-fix tasks",
           "status": "measured",
           "hypothesis": "Executable inheritance helps small local models more than tools alone and more than the same knowledge as prose.",
           "table": {"columns": ["agent", "arm", "success", "median steps", "discovery waste (sum)", "median wall s",
                                 "skill tool calls", "runtime test runs", "committed"], "rows": table},
           "preregistered_verdicts": verdicts,
           "totals": {arm: tot(arm) for arm in ARMS if any((a, arm) in cell for a in agents)},
           "limits": "4 tasks x 1 replicate per cell, temperature 0; effects under 2 tasks are inconclusive by preregistration. "
                     "The controller arm was added after the first 12 Qwen runs (not preregistered) and is reported as exploratory."}
    pathlib.Path(args.out).write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps({"totals": rec["totals"], "verdicts": verdicts}, indent=2))
    for row in table:
        print(row)


if __name__ == "__main__":
    main()
