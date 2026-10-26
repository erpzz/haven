#!/usr/bin/env python3
"""Aggregate a private paradigm session into a sanitized, publishable result.

Every eval record is re-verified with the current verifier (stored verdicts are
never trusted). Only counts, rates, Wilson intervals, paired sign tests,
timings and buffer sizes are emitted: no prompts, answers, transcripts, keys,
paths or host details.

  report.py --session DIR [--reference qwen35-4b] > results/paradigms-YYYYMMDD.json
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "distillation" / "tool_sft"))
import run  # noqa: E402

MAX_TOKENS = 1024


def wilson(passed, total, z=1.959964):
    if not total:
        return None
    p = passed / total
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return [round(100 * max(0.0, centre - half), 1), round(100 * min(1.0, centre + half), 1)]


def sign_test(gained, lost):
    """Exact two-sided binomial test on discordant pairs."""
    n = gained + lost
    if n == 0:
        return 1.0
    k = min(gained, lost)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return round(min(1.0, 2 * tail), 6)


def truncated_steps(records, limit=MAX_TOKENS):
    return sum(1 for r in records for s in r.get("steps", [])
               if (s.get("usage") or {}).get("completion_tokens", 0) >= limit)


def summarize_eval(records):
    scores = run.score_records(records)
    by_id = {s["episode"]: s for s in scores}
    tracks = collections.defaultdict(list)
    families = collections.defaultdict(list)
    for s in scores:
        tracks[s["track"]].append(s)
        families[f"{s['track']}/{s['family']}"].append(s)
    heldout = tracks["paraphrase"] + tracks["composition"]
    passed = sum(s["pass"] for s in heldout)

    def rate(rows):
        return {"passed": sum(s["pass"] for s in rows), "total": len(rows)}
    seconds = [r.get("elapsed_seconds", 0) for r in records]
    return by_id, {
        "heldout": {**rate(heldout), "wilson95_pct": wilson(passed, len(heldout))},
        "by_track": {k: rate(v) for k, v in sorted(tracks.items())},
        "by_family": {k: rate(v) for k, v in sorted(families.items())},
        "heldout_violations": dict(collections.Counter(v for s in heldout for v in s["violations"])),
        "heldout_answer_flags": dict(collections.Counter(f for s in heldout for f in s["flags"])),
        "format_error_episodes": sum(not s["format_ok"] for s in scores),
        "transport_failures": sum(not s["transport"] for s in scores),
        "truncated_steps": truncated_steps(records),
        "mean_episode_seconds": round(sum(seconds) / len(seconds), 2) if seconds else None,
        "episodes_completed": len(records),
    }


def paired(reference, other, ids):
    out = collections.Counter()
    for i in ids:
        if i not in reference or i not in other:
            out["unpaired"] += 1
            continue
        a, b = reference[i]["pass"], other[i]["pass"]
        out["both" if a and b else "gained" if b else "lost" if a else "neither"] += 1
    out = dict(out)
    out["sign_test_p"] = sign_test(out.get("gained", 0), out.get("lost", 0))
    return out


def performance(model_receipt):
    """Sanitized load, memory, probe and buffer figures from the ready attempt."""
    attempts = model_receipt.get("attempts") or []
    ready = [a for a in attempts if a.get("ready")]
    out = {"status": model_receipt.get("status"),
           "load_attempts": [{"ctx": a["ctx"], "ready": a.get("ready"), "seconds": a.get("seconds")}
                             for a in attempts]}
    if not ready:
        return out
    a = ready[-1]
    out.update({
        "ctx": a["ctx"], "load_seconds": a.get("seconds"),
        "buffers_mib": a.get("buffers_mib"),
        "peak_gpu_mib": (a.get("final") or a.get("at_ready") or {}).get("peak_gpu_mib"),
        "peak_rss_mib": (a.get("final") or a.get("at_ready") or {}).get("peak_rss_mib"),
        "probes": [{k: p.get(k) for k in ("prompt_tokens", "status", "prompt_tok_s", "decode_tok_s")}
                   for p in a.get("probes") or []],
        "eval_wall_seconds": (a.get("eval") or {}).get("seconds"),
    })
    return out


def build(session_dir, reference="qwen35-4b"):
    session_dir = pathlib.Path(session_dir)
    session = json.loads((session_dir / "session.json").read_text())
    heldout_ids = sorted(e["id"] for e in run.load_split("heldout"))
    legacy_ids = sorted("legacy-" + t["id"] for t in json.loads(run.LEGACY_TASKS.read_text()))
    models, scores = {}, {}
    for m in session["models"]:
        entry = {"performance": performance(m)} if m.get("attempts") else {"status": m.get("status")}
        path = session_dir / m["id"] / "eval.jsonl"
        if path.exists():
            records = run.read_jsonl(path)
            scores[m["id"]], entry["tool_benchmark"] = summarize_eval(records)
        models[m["id"]] = entry
    if reference in scores:
        for model_id, by_id in scores.items():
            if model_id != reference:
                models[model_id]["paired_vs_reference"] = {
                    "heldout": paired(scores[reference], by_id, heldout_ids),
                    "legacy": paired(scores[reference], by_id, legacy_ids)}
    restore = session.get("restore") or {}
    return {"schema": "haven-paradigm-result-1", "verifier_version": run.world.VERIFIER_VERSION,
            "reference": reference, "max_tokens": MAX_TOKENS,
            "session": {"status": session.get("status"), "gpu_minutes": session.get("gpu_minutes"),
                        "total_minutes": session.get("total_minutes"),
                        "strata_restored_and_connected": restore.get("restored"),
                        "strata_ready_seconds": restore.get("strata_ready_seconds")},
            "models": models}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--session", required=True)
    ap.add_argument("--reference", default="qwen35-4b")
    args = ap.parse_args(argv)
    print(json.dumps(build(args.session, args.reference), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
