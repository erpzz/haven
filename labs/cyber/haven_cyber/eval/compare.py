"""Controlled model comparison under ADAPTER_SELECTION_PREREGISTRATION.md.

    python -m haven_cyber.eval.compare --run base=runs/cmp/base-nothink --run adapter-A=runs/cmp/A-nothink \
        --run adapter-B=runs/cmp/B-nothink [--secondary base=... --secondary adapter-A=...] \
        --classes results/compare/<date>/classes.json --out results/compare/<date>

Writes comparison.md and comparison.json: per-case correctness, tool-call success, abstention accuracy, latency,
false positives, regressions, gains split by provenance class (T1 targeted / T2 in-family / T3 out-of-family),
and the pre-registered decision. It only recommends; it never changes serving configuration.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from .. import EVAL
from .report import mcnemar_exact

APPLICABLE = {"tenant_snapshot": "entra_ca_assess", "tool_output": "verify_tool_finding", "azure_rbac": "azure_rbac_check"}
ABSTAIN_FIELDS = {("tf-01", "A"): "ports", ("tf-01", "B"): "ports", ("net-01", "*"): "rdp_running", ("fp-03", "*"): "verdict"}
ABSTAIN_VALUES = {None, "", "null", "none", "unknown", "not_assessed", "not_determined"}


def one_sided_mcnemar(gain: int, loss: int) -> float:
    """P(X >= gain) for X ~ Bin(gain+loss, 0.5): evidence that the adapter wins more discordant pairs."""
    import math
    n = gain + loss
    if n == 0:
        return 1.0
    return sum(math.comb(n, i) for i in range(gain, n + 1)) / 2 ** n


def load(path: Path) -> dict:
    rows = [json.loads(x) for x in (path / "results.jsonl").read_text().splitlines() if x.strip()]
    return {(r["id"], r["condition"]): r for r in rows}


def scenario_meta() -> dict:
    sc = json.loads((EVAL / "scenarios" / "v1.json").read_text())["scenarios"]
    return {s["id"]: s for s in sc}


def applicable_tools(s: dict) -> set[str]:
    out = {APPLICABLE[k] for k in s.get("artifacts", {}) if k in APPLICABLE}
    if s.get("host"):
        out.add("run_command")
    return out


def is_abstain(v) -> bool:
    if isinstance(v, list):  # ["unknown"] counts; an empty or multi-item list is an answer, not an abstention
        return len(v) == 1 and is_abstain(v[0])
    if isinstance(v, (dict, bool, int, float)):
        return False
    return (v.lower().strip() if isinstance(v, str) else v) in ABSTAIN_VALUES


def abstention(row: dict) -> tuple[bool | None, bool]:
    """(expected-abstention handled correctly or None if not an abstention case, false abstention elsewhere)."""
    key = ABSTAIN_FIELDS.get((row["id"], row["condition"])) or ABSTAIN_FIELDS.get((row["id"], "*"))
    ans = row.get("answer") or {}
    if key:
        return is_abstain(ans.get(key)), False
    false_abs = bool(ans) and any(is_abstain(v) for k, v in ans.items() if k not in ("reason", "method"))
    return None, false_abs


def model_metrics(runs: dict, meta: dict, cond: str, ids: list[str]) -> dict:
    rs = [runs[(i, cond)] for i in ids if (i, cond) in runs]
    lat = [r["latency_s"] for r in rs]
    calls = sum(r["tool_calls"] for r in rs)
    bad = sum(r["bad_tool_calls"] + r["hallucinated_tools"] for r in rs)
    appl = [r for r in rs if applicable_tools(meta[r["id"]])]
    used = sum(bool(applicable_tools(meta[r["id"]]) & set(r.get("tools_used", []))) for r in appl)
    ab = [abstention(r) for r in rs]
    exp = [a for a, _ in ab if a is not None]
    return {"n": len(rs), "pass": sum(r["pass"] for r in rs), "false_positives": sum(r["false_positive"] for r in rs),
            "fp_eligible": sum(bool(r.get("fp_eligible")) for r in rs), "unparsed": sum(not r["parsed"] for r in rs),
            "tool_calls": calls, "tool_call_success": round((calls - bad) / calls, 3) if calls else None,
            "hallucinated_tools": sum(r["hallucinated_tools"] for r in rs),
            "applicable_tool_used": f"{used}/{len(appl)}" if cond in ("C", "D") else "-",
            "abstention_correct": f"{sum(exp)}/{len(exp)}" if exp else "-", "false_abstentions": sum(f for _, f in ab),
            "latency_mean_s": round(statistics.mean(lat), 2) if lat else None,
            "latency_median_s": round(statistics.median(lat), 2) if lat else None}


def decide(base: dict, cand: dict, meta: dict, classes: dict, cond: str, ho: list[str], secondary: tuple | None) -> dict:
    pairs = [(base[(i, cond)]["pass"], cand[(i, cond)]["pass"], i) for i in ho if (i, cond) in base and (i, cond) in cand]
    gain = sum(1 for b, c, _ in pairs if c and not b)
    loss = sum(1 for b, c, _ in pairs if b and not c)
    gen = [(b, c, i) for b, c, i in pairs if classes.get(i, "T3") in ("T2", "T3")]
    gen_net = sum(1 for b, c, _ in gen if c and not b) - sum(1 for b, c, _ in gen if b and not c)
    t3_reg = [i for b, c, i in pairs if b and not c and classes.get(i, "T3") == "T3"]
    fp_b = sum(base[(i, cond)]["false_positive"] for _, _, i in pairs)
    fp_c = sum(cand[(i, cond)]["false_positive"] for _, _, i in pairs)
    up_b = sum(not base[(i, cond)]["parsed"] for _, _, i in pairs)
    up_c = sum(not cand[(i, cond)]["parsed"] for _, _, i in pairs)
    crit = {"1_net_gain>=3_and_p<=0.10": gain - loss >= 3 and one_sided_mcnemar(gain, loss) <= 0.10,
            "2_generalization_net>=2": gen_net >= 2,
            "3_false_positives<=base": fp_c <= fp_b,
            "4_out_of_family_regressions<=1": len(t3_reg) <= 1,
            "5_unparsed<=base": up_c <= up_b}
    if secondary:
        sb, sc_ = secondary
        sec_pairs = [i for i in ho if (i, "C") in sb and (i, "C") in sc_]
        if sec_pairs:
            crit["6_thinking_on_pass>=base-1"] = (sum(sc_[(i, "C")]["pass"] for i in sec_pairs)
                                                  >= sum(sb[(i, "C")]["pass"] for i in sec_pairs) - 1)
        else:
            crit["6_thinking_on_pass>=base-1"] = None
    return {"heldout_gain": gain, "heldout_loss": loss, "net": gain - loss, "p_one_sided": round(one_sided_mcnemar(gain, loss), 4),
            "generalization_net_T2_T3": gen_net, "t3_regressions": t3_reg, "fp": [fp_b, fp_c], "unparsed": [up_b, up_c],
            "criteria": crit, "qualifies": all(v is not False for v in crit.values()) and any(v for v in crit.values())}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="append", required=True, help="label=path (first is the base)")
    ap.add_argument("--secondary", action="append", default=[], help="label=path for thinking-on runs")
    ap.add_argument("--classes", type=Path, required=True)
    ap.add_argument("--reference", type=Path, help="original baseline run, for the reproducibility check")
    ap.add_argument("--cond", default="C")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    meta = scenario_meta()
    classes = json.loads(a.classes.read_text())["classes"]
    runs = {lbl: load(Path(p)) for lbl, p in (x.split("=", 1) for x in a.run)}
    sec = {lbl: load(Path(p)) for lbl, p in (x.split("=", 1) for x in a.secondary)}
    labels = list(runs)
    base_lbl = labels[0]
    ho = sorted(i for i, s in meta.items() if s["split"] == "heldout")
    dev = sorted(i for i, s in meta.items() if s["split"] == "dev")
    out = {"primary_condition": a.cond, "base": base_lbl, "metrics": {}, "decisions": {}, "per_case": {}, "regressions": {}}
    for lbl in labels:
        out["metrics"][lbl] = {"heldout": model_metrics(runs[lbl], meta, a.cond, ho), "dev": model_metrics(runs[lbl], meta, a.cond, dev),
                               **({"heldout_thinking_on": model_metrics(sec[lbl], meta, "C", ho)} if lbl in sec else {})}
    for i in ho + dev:
        out["per_case"][i] = {"split": meta[i]["split"], "category": meta[i]["category"], "class": classes.get(i, "T3"),
                              **{lbl: {"pass": runs[lbl].get((i, a.cond), {}).get("pass"),
                                       "tools": runs[lbl].get((i, a.cond), {}).get("tools_used"),
                                       "latency_s": runs[lbl].get((i, a.cond), {}).get("latency_s")} for lbl in labels}}
    for lbl in labels[1:]:
        secondary = (sec[base_lbl], sec[lbl]) if base_lbl in sec and lbl in sec else None
        out["decisions"][lbl] = decide(runs[base_lbl], runs[lbl], meta, classes, a.cond, ho, secondary)
        out["regressions"][lbl] = [i for i in ho + dev if runs[base_lbl].get((i, a.cond), {}).get("pass")
                                   and not runs[lbl].get((i, a.cond), {}).get("pass")]
    winners = sorted((lbl for lbl, d in out["decisions"].items() if d["qualifies"]),
                     key=lambda l: (-out["decisions"][l]["net"], len(out["regressions"][l]),
                                    out["metrics"][l]["heldout"]["latency_mean_s"] or 0))
    out["recommendation"] = winners[0] if winners else f"{base_lbl} (retain untouched baseline: no adapter met every pre-registered criterion)"
    if a.reference:
        ref = load(a.reference)
        agree = [i for i in ho + dev if (i, a.cond) in ref and (i, a.cond) in runs[base_lbl]]
        same = sum(ref[(i, a.cond)]["pass"] == runs[base_lbl][(i, a.cond)]["pass"] for i in agree)
        out["reproducibility"] = {"cases": len(agree), "same_verdict": same,
                                  "flipped": [i for i in agree if ref[(i, a.cond)]["pass"] != runs[base_lbl][(i, a.cond)]["pass"]]}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "comparison.json").write_text(json.dumps(out, indent=1, default=str))
    (a.out / "comparison.md").write_text(render(out, labels, ho, classes))
    print(render(out, labels, ho, classes))


def render(o: dict, labels: list[str], ho: list[str], classes: dict) -> str:
    L = [f"## Held-out comparison (condition {o['primary_condition']}, thinking off; n = {len(ho)})\n",
         "| Model | Pass | False positives | Unparsed | Tool calls | Tool-call success | Applicable tool used | Abstention correct | False abstentions | Latency mean / median (s) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for lbl in labels:
        m = o["metrics"][lbl]["heldout"]
        L.append(f"| {lbl} | {m['pass']}/{m['n']} | {m['false_positives']}/{m['fp_eligible']} | {m['unparsed']} | {m['tool_calls']} | "
                 f"{m['tool_call_success'] if m['tool_call_success'] is not None else '-'} | {m['applicable_tool_used']} | {m['abstention_correct']} | "
                 f"{m['false_abstentions']} | {m['latency_mean_s']} / {m['latency_median_s']} |")
    L.append(f"\nDev cases, descriptive only (not used for the decision; the abstention cases tf-01, net-01 and fp-03 are dev):\n")
    L.append("| Model | Pass | False positives | Tool calls | Tool-call success | Applicable tool used | Abstention correct | False abstentions | Latency mean (s) |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for lbl in labels:
        m = o["metrics"][lbl]["dev"]
        L.append(f"| {lbl} | {m['pass']}/{m['n']} | {m['false_positives']}/{m['fp_eligible']} | {m['tool_calls']} | "
                 f"{m['tool_call_success'] if m['tool_call_success'] is not None else '-'} | {m['applicable_tool_used']} | "
                 f"{m['abstention_correct']} | {m['false_abstentions']} | {m['latency_mean_s']} |")
    if any("heldout_thinking_on" in o["metrics"][l] for l in labels):
        L.append("\nSecondary, thinking on (held-out, condition C): " + ", ".join(
            f"{l} {o['metrics'][l]['heldout_thinking_on']['pass']}/{o['metrics'][l]['heldout_thinking_on']['n']}"
            for l in labels if "heldout_thinking_on" in o["metrics"][l]))
    L.append("\n## Pre-registered decision\n")
    for lbl, d in o["decisions"].items():
        L.append(f"**{lbl}**: net {d['net']:+d} (gain {d['heldout_gain']}, loss {d['heldout_loss']}, one-sided p = {d['p_one_sided']}); "
                 f"generalization net (T2+T3) {d['generalization_net_T2_T3']:+d}; FP base/adapter {d['fp'][0]}/{d['fp'][1]}; "
                 f"T3 regressions {d['t3_regressions'] or 'none'}. Qualifies: **{d['qualifies']}**")
        L += [f"- {k}: {v}" for k, v in d["criteria"].items()]
    L.append(f"\n**Recommendation: {o['recommendation']}** (recommendation only; nothing is promoted automatically)\n")
    if "reproducibility" in o:
        r = o["reproducibility"]
        L.append(f"Reproducibility: base re-run matches the original baseline on {r['same_verdict']}/{r['cases']} cases; flipped: {r['flipped'] or 'none'}\n")
    L.append("## Per case (condition C, thinking off)\n")
    L.append("| Case | Split | Category | Class | " + " | ".join(labels) + " |")
    L.append("|---|---|---|---|" + "---|" * len(labels))
    for i, v in o["per_case"].items():
        cells = []
        for lbl in labels:
            c = v[lbl]
            mark = "✓" if c["pass"] else ("✗" if c["pass"] is not None else "·")
            cells.append(f"{mark} {','.join(t.split('_')[0] for t in (c['tools'] or [])) or ''}".strip())
        L.append(f"| {i} | {v['split']} | {v['category']} | {v['class']} | " + " | ".join(cells) + " |")
    L.append("\n## Regressions (base ✓ → adapter ✗, all cases)\n")
    for lbl, regs in o["regressions"].items():
        L.append(f"- {lbl}: {', '.join(regs) or 'none'}")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
