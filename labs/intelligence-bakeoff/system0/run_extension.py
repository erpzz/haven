#!/usr/bin/env python3
"""Run the HARE-S0-2 extension on the untouched episode set, one host, every arm matched.

  run_extension.py --engine PATH/llama-server --model-4b PATH.gguf --out DIR [--model-35b PATH.gguf]

Arms on fresh-x-untouched.jsonl (179 episodes, generated and hashed before any extension
inference and never inspected): 4b-plain, 4b-s0, 4b-enforce, 4b-verify, 4b-full, and
optionally 35b-plain and 35b-full. Finished arms are skipped on rerun. results-extension.json
holds the preregistered comparisons, the non-inferiority test and the offline cascade.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bench_s0  # noqa: E402
import bench_x  # noqa: E402
from run_arms import PORT, reusable, sha256, start_server  # noqa: E402

UNTOUCHED = HERE / "fresh-x-untouched.jsonl"


def run(kind, arm, label, out, model_name, hardware, limit):
    path = out / f"{label}.jsonl"
    summary = path.with_suffix(".summary.json")
    if summary.exists() and reusable(summary, UNTOUCHED, limit):
        print(f"== {label}: complete receipt found (all expected episodes), skipping", flush=True)
        return json.loads(summary.read_text())
    if summary.exists():
        print(f"== {label}: receipt incomplete or for a different episode set; rerunning", flush=True)
        summary.unlink()
    if path.exists():
        path.unlink()
    common = ["--base-url", f"http://127.0.0.1:{PORT}/v1", "--model", model_name, "--label", label,
              "--out", str(path), "--episodes", str(UNTOUCHED), "--hardware", hardware]
    if limit:
        common += ["--limit", str(limit)]
    print(f"== {label}", flush=True)
    if kind == "s0":
        bench_s0.main(["eval", "--arm", arm, *common])  # registered HARE-S0-1 code on the new episode set
    else:
        bench_x.main(["eval", "--arm", arm, *common])
    return json.loads(summary.read_text())


def passes(summary):
    return {s["episode"]: bool(s["pass"]) for s in summary["scores"]}


def noninferiority(test, control, margin):
    """Paired difference test - control; one-sided 95% lower bound (Wald, paired)."""
    a, b = passes(test), passes(control)
    common = sorted(set(a) & set(b))
    n = len(common)
    win = sum(a[e] and not b[e] for e in common)
    loss = sum(b[e] and not a[e] for e in common)
    d = (win - loss) / n
    se = math.sqrt(max(win + loss - (win - loss) ** 2 / n, 0)) / n
    lower = d - 1.6449 * se
    return {"n": n, "test_only": win, "control_only": loss, "difference": round(d, 4),
            "one_sided_95_lower": round(lower, 4), "margin": -margin, "non_inferior": lower > -margin}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--engine", required=True)
    p.add_argument("--model-4b", required=True)
    p.add_argument("--model-35b", default=None)
    p.add_argument("--out", required=True)
    p.add_argument("--hardware", default="unknown")
    p.add_argument("--gpu-4b", default="0")
    p.add_argument("--limit", type=int, default=0, help="smoke test only")
    args = p.parse_args()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    reg = json.loads((HERE / "PREREGISTRATION_S0X.json").read_text())
    if bench_s0.sha256_file(UNTOUCHED) != reg["episode_sets"]["untouched"]["sha256"]:
        raise SystemExit("untouched episode set changed")
    for name, h in reg["code_sha256"].items():
        if bench_s0.sha256_file(HERE / name) != h:
            raise SystemExit(f"{name} differs from PREREGISTRATION_S0X.json")
    s = {}
    sha4 = sha256(args.model_4b)
    if sha4 != reg["settings"]["4b_sha256"]:
        raise SystemExit("4B GGUF sha256 mismatch")
    proc, _ = start_server(args.engine, args.model_4b, out / "server-4b-x.log", {"CUDA_VISIBLE_DEVICES": args.gpu_4b})
    try:
        for kind, arm, label in (("s0", "plain", "4b-plain-untouched"), ("s0", "s0", "4b-s0-untouched"),
                                 ("x", "enforce", "4b-enforce-untouched"), ("x", "verify", "4b-verify-untouched"),
                                 ("x", "full", "4b-full-untouched")):
            s[label] = run(kind, arm, label, out, "qwen35-4b", args.hardware, args.limit)
    finally:
        proc.terminate(); proc.wait(60)
    if args.model_35b:
        if sha256(args.model_35b) != reg["settings"]["35b_sha256"]:
            raise SystemExit("35B GGUF sha256 mismatch")
        proc, _ = start_server(args.engine, args.model_35b, out / "server-35b-x.log")
        try:
            for kind, arm, label in (("s0", "plain", "35b-plain-untouched"), ("x", "full", "35b-full-untouched")):
                s[label] = run(kind, arm, label, out, "qwen36-35b-a3b", args.hardware, args.limit)
        finally:
            proc.terminate(); proc.wait(60)

    base = s["4b-plain-untouched"]
    res = {"prereg": reg["id"], "hardware": args.hardware, "comparisons": {}, "arms": {}}
    for label, summ in s.items():
        res["arms"][label] = {k: summ["summary"].get(k) for k in
                              ("pass", "raw_pass", "model_clean_pass", "outcomes", "verifier_vs_adjudicator_on_raw",
                               "corrections_successful", "corrections_total", "blocked_authorization",
                               "episodes_with_authorization_attempt", "blocked_duplicate", "false_refusals",
                               "unsupported_claim_episodes", "mean_request_seconds") if k in summ["summary"]}
        res["arms"][label]["mean_episode_seconds"] = summ.get("mean_episode_seconds")
        if label != "4b-plain-untouched" and label.startswith("4b"):
            res["comparisons"][f"{label} vs 4b-plain"] = bench_s0.compare(base, summ)
    margin = reg["decision_rules"]["noninferiority_margin"]
    if "35b-plain-untouched" in s:
        res["noninferiority_4b_full_vs_35b_plain"] = noninferiority(s["4b-full-untouched"], s["35b-plain-untouched"], margin)
        cascade, esc, secs = 0, 0, 0.0
        strong = {r["episode"]: r for r in s["35b-full-untouched"]["scores"]}
        rows = s["4b-full-untouched"]["scores"]
        cas = {}
        for r in rows:
            if r["outcome"] == "rejected_unresolved" and r["episode"] in strong:
                esc += 1
                cas[r["episode"]] = strong[r["episode"]]["pass"]
                secs += r["seconds"] + strong[r["episode"]]["seconds"]
            else:
                cas[r["episode"]] = r["pass"]
                secs += r["seconds"]
        cascade_summary = {"scores": [{"episode": e, "pass": v} for e, v in cas.items()]}
        res["cascade_4b_full_escalate_35b_full"] = {
            "pass": sum(cas.values()), "escalated": esc, "mean_request_seconds": round(secs / len(rows), 2),
            "note": "model loading excluded (both models assumed resident); strong model runs independently",
            "noninferiority_vs_35b_plain": noninferiority(cascade_summary, s["35b-plain-untouched"], margin)}
    (out / "results-extension.json").write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "comparisons"}, indent=2)[:6000])


if __name__ == "__main__":
    main()
