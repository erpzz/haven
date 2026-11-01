"""Turn evaluation results into the capability matrix and gap report (Markdown).

    python -m haven_cyber.eval.report runs/eval/qwythos-nothink-v1 [runs/eval/qwythos-think-v1 ...] > report.md

Gap attribution per scenario (paired across conditions of the same run):
  pass A                      -> known (the base model already has it)
  fail A, pass B              -> knowledge gap (retrieval fixes it)
  fail A and B, pass C        -> tool gap (a tool fixes it)
  fail all, no parse / errors -> orchestration gap (format, loop, tool protocol)
  fail all, C called no tool  -> orchestration gap (did not use an applicable tool)
  fail all otherwise          -> reasoning gap (had the facts and the tools, still wrong)
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value on discordant pairs b (only first passes) and c (only second passes)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def load(run: Path) -> tuple[dict, list[dict]]:
    meta = json.loads((run / "meta.json").read_text()) if (run / "meta.json").exists() else {}
    rows = [json.loads(x) for x in (run / "results.jsonl").read_text().splitlines() if x.strip()]
    return meta, rows


def attribute(by_cond: dict) -> str:
    a, b, c = (by_cond.get(k) for k in "ABC")
    if a and a["pass"]:
        return "known"
    if b and b["pass"]:
        return "knowledge"
    if c and c["pass"]:
        return "tool"
    last = c or b or a
    if not last["parsed"] or last.get("error"):
        return "orchestration"
    if c is not None and c["tool_calls"] == 0:
        return "orchestration"
    return "reasoning"


def report(runs: list[Path]) -> str:
    out = []
    for run in runs:
        meta, rows = load(run)
        conds = sorted({r["condition"] for r in rows})
        out.append(f"### Run `{run.name}`: model `{meta.get('model')}`, thinking {'on' if meta.get('think') else 'off'}\n")
        out.append("| Condition | Pass | Held-out pass | False positives (of eligible) | Unparsed | Tool calls | Bad / hallucinated tool calls | "
                   "Hallucinated results | Tool calls per success | Prompt / completion tokens | Latency (s) |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for k in conds:
            rs = [r for r in rows if r["condition"] == k]
            n, p = len(rs), sum(r["pass"] for r in rs)
            ho = [r for r in rs if r["split"] == "heldout"]
            ok = [r for r in rs if r["pass"]]
            elig = [r for r in rs if r.get("fp_eligible")]
            tps = f"{sum(r['tool_calls'] for r in ok) / len(ok):.2f}" if ok and k in ("C", "D") else "-"
            out.append(f"| {k} | {p}/{n} ({p / n:.0%}) | {sum(r['pass'] for r in ho)}/{len(ho)} | {sum(r['false_positive'] for r in rs)}/{len(elig)} | "
                       f"{sum(not r['parsed'] for r in rs)} | {sum(r['tool_calls'] for r in rs)} | {sum(r['bad_tool_calls'] for r in rs)} / "
                       f"{sum(r['hallucinated_tools'] for r in rs)} | {sum(r['hallucinated_result'] for r in rs)} | {tps} | "
                       f"{sum(r['prompt_tokens'] for r in rs)} / {sum(r['completion_tokens'] for r in rs)} | {sum(r['latency_s'] for r in rs):.0f} |")
        idx = defaultdict(dict)
        for r in rows:
            idx[r["id"]][r["condition"]] = r
        out.append("\nPaired comparisons (exact McNemar on scenarios present in both conditions):\n")
        for x, y in (("A", "B"), ("B", "C"), ("A", "C")):
            pairs = [(v[x]["pass"], v[y]["pass"]) for v in idx.values() if x in v and y in v]
            if not pairs:
                continue
            b = sum(1 for p, q in pairs if p and not q)
            c = sum(1 for p, q in pairs if q and not p)
            out.append(f"- {x} → {y}: {sum(q for _, q in pairs) - sum(p for p, _ in pairs):+d} passes; only-{x} {b}, only-{y} {c}, "
                       f"p = {mcnemar_exact(b, c):.3f} (n = {len(pairs)})")
        cats = sorted({r["category"] for r in rows})
        out.append("\n| Category | " + " | ".join(conds) + " | Dominant gap |")
        out.append("|---|" + "---|" * len(conds) + "---|")
        gaps = {sid: attribute(v) for sid, v in idx.items() if all(k in v for k in conds)}
        for cat in cats:
            cells = []
            for k in conds:
                rs = [r for r in rows if r["condition"] == k and r["category"] == cat]
                cells.append(f"{sum(r['pass'] for r in rs)}/{len(rs)}")
            g = Counter(gaps[s] for s, v in idx.items() if s in gaps and next(iter(v.values()))["category"] == cat and gaps[s] != "known")
            out.append(f"| {cat} | " + " | ".join(cells) + f" | {', '.join(f'{k} {n}' for k, n in g.most_common()) or 'none'} |")
        tally = Counter(gaps.values())
        out.append(f"\nGap attribution over {len(gaps)} scenarios: " + ", ".join(f"{k} {v}" for k, v in tally.most_common()) + "\n")
        fails = [(sid, gaps[sid]) for sid in sorted(gaps) if gaps[sid] != "known"]
        if fails:
            out.append("<details><summary>Per-scenario attribution</summary>\n")
            out.append("| Scenario | Category | Split | " + " | ".join(conds) + " | Gap | C tools used |")
            out.append("|---|---|---|" + "---|" * len(conds) + "---|---|")
            for sid, gp in fails:
                v = idx[sid]
                any_r = next(iter(v.values()))
                out.append(f"| {sid} | {any_r['category']} | {any_r['split']} | " + " | ".join("✓" if v[k]["pass"] else "✗" for k in conds)
                           + f" | {gp} | {', '.join(v.get('C', {}).get('tools_used', [])) or '-'} |")
            out.append("\n</details>\n")
    return "\n".join(out)


if __name__ == "__main__":
    print(report([Path(p) for p in sys.argv[1:]]))
