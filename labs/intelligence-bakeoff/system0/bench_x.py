#!/usr/bin/env python3
"""HARE-S0-2 extension arms: enforcement, verification, correction, combined; offline escalation.

  bench_x.py eval --arm enforce|verify|full --base-url http://127.0.0.1:PORT/v1 --label L --out R.jsonl [--episodes E]
  bench_x.py offline-verify --records PLAIN.jsonl [--episodes E]  # verifier accuracy on existing plain runs
  bench_x.py escalate --small FULL4B.summary.json --strong FULL35B.summary.json   # offline cascade
  bench_x.py compare --a PLAIN.summary.json --b ARM.summary.json

Arms (each records attempts, blocks, raw vs final answers and full request latency):
  enforce = gateway only
  verify  = verifier + one correction (no gateway, no advisory)
  full    = advisory checks + gateway + verifier + one correction
The baseline is the registered `plain` arm (bench_s0.py) on the same episodes and host.
Escalation is computed offline: an unresolved small-model episode takes the strong
model's own independent `full` run on that episode. The strong model never sees the
small model's reasoning, and the cost is the sum of both latencies.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bench_s0  # noqa: E402
from bench_s0 import agent, bench, contract, generator  # noqa: E402
import enforce  # noqa: E402

ARMS = {"enforce": dict(gateway=True),
        "verify": dict(verifier=True, correction=True),
        "full": dict(advisory=True, gateway=True, verifier=True, correction=True)}
UNTOUCHED = HERE / "fresh-x-untouched.jsonl"


def run_x(backend, episode, mechanisms):
    def dispatch(name, args):
        return contract.dispatch(episode["world"], episode["principal"], name, args)
    rec = enforce.run_episode_x(backend, episode["principal"], generator.task_text(episode), dispatch,
                                contract.TOOL_SCHEMAS, bench.BIND, system=agent.SYSTEM,
                                user_message=agent.user_message, max_rounds=agent.MAX_ROUNDS, **mechanisms)
    rec.update({"episode": episode["id"], "family": episode["family"]})
    return rec


def score_views(rec, episode):
    """Adjudicator on (a) the final system output and (b) the raw first answer."""
    final = bench.score_records([rec], [episode])[0]
    raw_rec = dict(rec, answer=rec.get("raw_answer") or "", trace=rec["trace"][:rec.get("raw_trace_len") or len(rec["trace"])])
    raw = bench.score_records([raw_rec], [episode])[0]
    return final, raw


def expected_statuses(episode):
    # expectations live in contract.expect_claims (post-run correction; the original read a
    # non-existent top-level "expect" key and counted every refusal as false)
    return {e["status"] for e in (episode.get("contract") or {}).get("expect_claims") or []}


def episode_metrics(rec, episode):
    final, raw = score_views(rec, episode)
    attempts = rec.get("attempts") or []
    blocked = [a for a in attempts if not a["executed"]]
    auth_blocked = [a for a in blocked if a["policy"] in ("P1_proposal_requires_request", "P2_named_owner_only")]
    claims = enforce.parse_claims(rec.get("answer") or "") or []
    refused = any(isinstance(c, dict) and c.get("status") == "refused" for c in claims)
    return {"episode": rec["episode"], "family": rec["family"], "pass": final["pass"], "raw_pass": raw["pass"],
            "model_clean_pass": bool(final["pass"] and not auth_blocked),
            "outcome": rec.get("outcome"), "raw_problems": rec.get("raw_problems"),
            "final_problems": rec.get("final_problems"),
            "attempted_calls": len(attempts), "executed_calls": len(attempts) - len(blocked),
            "blocked_authorization": len(auth_blocked),
            "blocked_duplicate": sum(a["policy"] == "P3_duplicate_call" for a in blocked),
            "false_refusal": bool(refused and "refused" not in expected_statuses(episode)),
            "unsupported_claims": not final.get("claims_ok", True),
            "violations": final.get("violations"),
            "seconds": rec["elapsed_seconds"], "transport_ok": rec["ok_transport"]}


def summarize_x(rows):
    n = len(rows)
    oc = collections.Counter(r["outcome"] for r in rows)
    verifier_conf = collections.Counter()
    for r in rows:
        if r["outcome"] in (None, "unverified"):
            continue
        accepted = not r["raw_problems"]
        verifier_conf[("accept" if accepted else "reject") + "_" + ("rawpass" if r["raw_pass"] else "rawfail")] += 1
    corrected = [r for r in rows if r["outcome"] == "corrected"]
    return {"episodes": n, "pass": sum(r["pass"] for r in rows), "raw_pass": sum(r["raw_pass"] for r in rows),
            "model_clean_pass": sum(r["model_clean_pass"] for r in rows),
            "outcomes": dict(oc), "verifier_vs_adjudicator_on_raw": dict(verifier_conf),
            "corrections_successful": sum(r["pass"] for r in corrected), "corrections_total": len(corrected),
            "attempted_calls": sum(r["attempted_calls"] for r in rows),
            "executed_calls": sum(r["executed_calls"] for r in rows),
            "blocked_authorization": sum(r["blocked_authorization"] for r in rows),
            "episodes_with_authorization_attempt": sum(r["blocked_authorization"] > 0 for r in rows),
            "blocked_duplicate": sum(r["blocked_duplicate"] for r in rows),
            "false_refusals": sum(r["false_refusal"] for r in rows),
            "unsupported_claim_episodes": sum(r["unsupported_claims"] for r in rows),
            "mean_request_seconds": round(sum(r["seconds"] for r in rows) / max(n, 1), 2),
            "by_family": {f: {"n": len(v), "pass": sum(r["pass"] for r in v)}
                          for f, v in sorted(_group(rows).items())}}


def _group(rows):
    g = collections.defaultdict(list)
    for r in rows:
        g[r["family"]].append(r)
    return g


def cmd_eval(args):
    if bench.verify_freeze()["problems"]:
        raise SystemExit("Refusing: frozen suite changed")
    out = pathlib.Path(args.out)
    summary_path = out.with_suffix(".summary.json")
    if out.exists() or summary_path.exists():
        raise SystemExit("Refusing to overwrite a receipt.")
    os.umask(0o077)
    episodes = bench.load_episodes(args.episodes)
    if args.limit:
        episodes = episodes[:args.limit]
    index = {e["id"]: e for e in episodes}
    backend = agent.OpenAIBackend(args.base_url, args.model, None, temperature=0.0, max_tokens=args.max_tokens)
    rows, started = [], time.monotonic()
    for e in episodes:
        rec = run_x(backend, e, ARMS[args.arm])
        rec["label"], rec["arm"] = args.label, args.arm
        bench.write_jsonl(out, [rec], mode="a")
        m = episode_metrics(rec, index[rec["episode"]])
        rows.append(m)
        print(rec["episode"], "PASS" if m["pass"] else "fail", m["outcome"], f"blocked={m['blocked_authorization']}",
              f"{rec['elapsed_seconds']}s", flush=True)
    report = {"schema": "haven-s0x-eval-1", "arm": args.arm, "mechanisms": ARMS[args.arm], "label": args.label,
              "model": args.model, "hardware": args.hardware, "episode_set": str(args.episodes or "frozen"),
              "episode_set_sha256": bench_s0.sha256_file(args.episodes) if args.episodes else bench_s0.sha256_file(bench.FROZEN),
              "code_sha256": {p: bench_s0.sha256_file(HERE / p) for p in ("checks.py", "enforce.py", "bench_x.py")},
              "records_sha256": bench_s0.sha256_file(out), "wall_seconds": round(time.monotonic() - started, 1),
              "summary": summarize_x(rows), "scores": rows,
              # compatibility with bench_s0.compare (paired by episode on final pass)
              "mean_episode_seconds": summarize_x(rows)["mean_request_seconds"]}
    summary_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report["summary"].items() if k != "by_family"}, indent=2))


def cmd_offline_verify(args):
    """Verifier accuracy on existing plain-arm records: no new inference."""
    episodes = {e["id"]: e for e in bench.load_episodes(args.episodes)}
    conf, rows = collections.Counter(), []
    for line in open(args.records):
        rec = json.loads(line)
        e = episodes[rec["episode"]]
        passed = bench.score_records([rec], [e])[0]["pass"]
        problems = enforce.verify(generator.task_text(e), rec["trace"], rec.get("answer") or "") if rec.get("ok_transport") else ["transport"]
        conf[("reject" if problems else "accept") + "_" + ("pass" if passed else "fail")] += 1
        rows.append({"episode": rec["episode"], "pass": passed, "problems": problems})
    tp, fn = conf["reject_fail"], conf["accept_fail"]
    fp, tn = conf["reject_pass"], conf["accept_pass"]
    print(json.dumps({"records": len(rows), "confusion": dict(conf),
                      "fail_recall": round(tp / (tp + fn), 3) if tp + fn else None,
                      "false_alarm_rate_on_passes": round(fp / (fp + tn), 3) if fp + tn else None,
                      "rows": rows if args.verbose else None}, indent=2))


def cmd_escalate(args):
    small = json.loads(pathlib.Path(args.small).read_text())
    strong = {r["episode"]: r for r in json.loads(pathlib.Path(args.strong).read_text())["scores"]}
    rows, escalated = [], 0
    for r in small["scores"]:
        if r["outcome"] == "rejected_unresolved" and r["episode"] in strong:
            s = strong[r["episode"]]
            escalated += 1
            rows.append({"episode": r["episode"], "pass": s["pass"], "seconds": r["seconds"] + s["seconds"]})
        else:
            rows.append({"episode": r["episode"], "pass": r["pass"], "seconds": r["seconds"]})
    n = len(rows)
    print(json.dumps({"episodes": n, "escalated": escalated, "pass": sum(x["pass"] for x in rows),
                      "small_alone_pass": small["summary"]["pass"],
                      "strong_alone_pass": sum(s["pass"] for s in strong.values()),
                      "mean_request_seconds_cascade": round(sum(x["seconds"] for x in rows) / max(n, 1), 2),
                      "mean_request_seconds_strong_alone": round(sum(s["seconds"] for s in strong.values()) / max(len(strong), 1), 2),
                      "note": "model loading excluded; assumes both models resident"}, indent=2))


def cmd_compare(args):
    a = json.loads(pathlib.Path(args.a).read_text())
    b = json.loads(pathlib.Path(args.b).read_text())
    print(json.dumps(bench_s0.compare(a, b, None), indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("eval")
    e.add_argument("--arm", choices=sorted(ARMS), required=True)
    e.add_argument("--base-url", required=True)
    e.add_argument("--model", default="haven-local")
    e.add_argument("--label", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--episodes", default=None)
    e.add_argument("--limit", type=int, default=0)
    e.add_argument("--max-tokens", type=int, default=1024)
    e.add_argument("--hardware", default="unknown")
    e.set_defaults(func=cmd_eval)
    o = sub.add_parser("offline-verify")
    o.add_argument("--records", required=True)
    o.add_argument("--episodes", default=None)
    o.add_argument("--verbose", action="store_true")
    o.set_defaults(func=cmd_offline_verify)
    s = sub.add_parser("escalate")
    s.add_argument("--small", required=True)
    s.add_argument("--strong", required=True)
    s.set_defaults(func=cmd_escalate)
    c = sub.add_parser("compare")
    c.add_argument("--a", required=True)
    c.add_argument("--b", required=True)
    c.set_defaults(func=cmd_compare)
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
