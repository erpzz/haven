#!/usr/bin/env python3
"""Deterministic tool receipts and cross-model routing, scored on saved bake-off records.

The LFM2.5-8B-A1B run showed a specific failure: correct tools, correct facts,
but the final answer omits the evidence_id or the "not executed" status that
the tool returned. Haven's runtime already holds those values in the trace, so
it can state them itself instead of trusting the model to copy them.

receipt_footer() renders only fields from successful tool outputs in the same
episode: evidence ids, and proposal ids with their returned authority. It
never adds note text, device state or causes, so it cannot supply a missing
fact, and the verifier's must_not checks (stale values, leaks, exec claims,
injected text) still see the model's own words.

This is a *system* contract (model + Haven runtime), reported beside, never
instead of, the model-only score. No inference is run here.

  receipts.py --session DIR [--fast lfm25-8b-a1b --strong qwen35-4b]
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "distillation" / "tool_sft"))
import run  # noqa: E402
import world  # noqa: E402


def receipt_footer(trace, answer=""):
    """Receipt line for ids the tools returned and the answer does not already state."""
    stated = world.norm(answer)
    items, seen = [], set()
    for entry in trace or []:
        out = entry.get("output")
        if not isinstance(out, dict) or not out.get("ok"):
            continue
        evidence = out.get("evidence_id")
        if evidence and evidence not in seen and world.norm(evidence) not in stated:
            seen.add(evidence)
            items.append(f"evidence {evidence}")
        proposal = out.get("proposal_id")
        if (entry.get("name") == "haven_propose_action" and proposal and proposal not in seen
                and out.get("executed") is False):
            seen.add(proposal)
            # Restated even when the model named the id: the authority is the receipt.
            authority = str(out.get("authority") or "PROPOSAL_ONLY").replace("_", " ").lower()
            items.append(f"proposal {proposal} ({authority}, not executed)")
    return "Receipts: " + "; ".join(items) + "." if items else ""


def with_receipts(record):
    out = copy.deepcopy(record)
    footer = receipt_footer(out.get("trace"), out.get("answer") or "")
    if footer:
        out["answer"] = ((out.get("answer") or "").rstrip() + "\n\n" + footer).strip()
    return out


def escalate(record):
    """Runtime-observable escalation rule, fixed before scoring (no verifier labels).

    Escalate when the fast model made no tool call, hit a failed tool result, or
    its answer repeats tool-output text marked as an embedded instruction.
    """
    trace = record.get("trace") or []
    if not trace or not record.get("ok_transport") or record.get("format_errors"):
        return True
    if any(isinstance(e.get("output"), dict) and not e["output"].get("ok") for e in trace):
        return True
    return "embedded instruction" in world.norm(record.get("answer") or "")


def _passes(records):
    return {s["episode"]: s["pass"] for s in run.score_records(records)}


def analyse(session_dir, fast="lfm25-8b-a1b", strong="qwen35-4b"):
    session_dir = pathlib.Path(session_dir)
    heldout = sorted(e["id"] for e in run.load_split("heldout"))
    raw, models = {}, {}
    for path in sorted(session_dir.glob("*/eval.jsonl")):
        records = run.read_jsonl(path)
        raw[path.parent.name] = {r["episode"]: r for r in records}
        base = _passes(records)
        sysp = _passes([with_receipts(r) for r in records])
        models[path.parent.name] = {
            "model_only": sum(base[i] for i in heldout if i in base),
            "with_receipts": sum(sysp[i] for i in heldout if i in sysp),
            "receipts_gained": sum(sysp.get(i, False) and not base.get(i, False) for i in heldout),
            "receipts_lost": sum(base.get(i, False) and not sysp.get(i, False) for i in heldout),
            "episodes": len(records),
        }
    out = {"schema": "haven-paradigm-receipts-1", "verifier_version": world.VERIFIER_VERSION,
           "heldout_total": len(heldout), "models": models}
    if fast in raw and strong in raw:
        both = [i for i in heldout if i in raw[fast] and i in raw[strong]]
        def scored(model, receipts):
            rows = [raw[model][i] for i in both]
            return _passes([with_receipts(r) for r in rows] if receipts else rows)
        cascade = {}
        for receipts in (False, True):
            f, s = scored(fast, receipts), scored(strong, receipts)
            esc = [i for i in both if escalate(raw[fast][i])]
            cascade["with_receipts" if receipts else "model_only"] = {
                "oracle_union": sum(f[i] or s[i] for i in both),
                "cascade_pass": sum(s[i] if i in esc else f[i] for i in both),
                "escalated": len(esc),
                "strong_alone": sum(s[i] for i in both),
                "fast_alone": sum(f[i] for i in both),
            }
        out["cascade"] = {"fast": fast, "strong": strong, "paired": len(both), **cascade}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--session", required=True)
    ap.add_argument("--fast", default="lfm25-8b-a1b")
    ap.add_argument("--strong", default="qwen35-4b")
    args = ap.parse_args(argv)
    print(json.dumps(analyse(args.session, args.fast, args.strong), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
