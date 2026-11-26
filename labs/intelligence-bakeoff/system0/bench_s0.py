#!/usr/bin/env python3
"""Matched plain vs System-0 runs on the frozen adjudicated suite (180 episodes).

  bench_s0.py check
  bench_s0.py eval --arm plain|s0 --base-url http://127.0.0.1:PORT/v1 --model NAME --label L --out R.jsonl
  bench_s0.py compare --a plain.summary.json --b s0.summary.json [--ref-35b 121]

`plain` calls adjudicated/bench.py's own run(), byte-for-byte the round-2 protocol.
`s0` runs the same loop with checks.py annotations in the messages the model reads.
Scoring is adjudicator.py, unchanged, on the raw trace and answer.
Records hold full transcripts: keep them out of Git. Commit only summaries.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
BAKEOFF = HERE.parent
sys.path.insert(0, str(BAKEOFF / "adjudicated"))
sys.path.insert(0, str(BAKEOFF / "distillation" / "tool_sft"))
sys.path.insert(0, str(HERE))
import bench  # noqa: E402  (adjudicated/bench.py)
import agent  # noqa: E402
import generator  # noqa: E402
import world as contract  # noqa: E402
import checks  # noqa: E402

PREREG = HERE / "PREREGISTRATION_S0.json"
ROUND2_REF = {"qwen35-4b": 58, "qwen35-9b": 101, "qwen36-35b-a3b": 121, "episodes": 180}


def sha256_file(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def s0_hashes() -> dict:
    return {p.name: sha256_file(p) for p in (HERE / "checks.py", HERE / "bench_s0.py")}


# ------------------------------------------------------------------ the s0 loop
def run_episode_s0(backend, principal, prompt, dispatch, tools, bind):
    """agent.run_episode with runtime checks in the model-visible messages only."""
    note = checks.request_note(prompt)
    user = agent.user_message(principal, prompt) + ("\n\n" + note if note else "")
    messages = [{"role": "system", "content": agent.SYSTEM}, {"role": "user", "content": user}]
    trace, format_errors, steps, annotations = [], [], [], 0
    started = time.monotonic()
    for round_no in range(agent.MAX_ROUNDS):
        t0 = time.monotonic()
        try:
            reply = backend.step(messages, tools)
        except Exception as error:  # transport failure is a recorded outcome
            return {"ok_transport": False, "error": f"{type(error).__name__}: {str(error)[:300]}",
                    "answer": "", "trace": trace, "messages": messages, "format_errors": format_errors,
                    "steps": steps, "annotations": annotations, "request_note": bool(note),
                    "elapsed_seconds": round(time.monotonic() - started, 3)}
        steps.append({"seconds": round(time.monotonic() - t0, 3), "usage": reply.get("usage") or {},
                      "finish_reason": reply.get("finish_reason")})
        if reply.get("format_error"):
            format_errors.append(reply["format_error"])
        calls = reply.get("tool_calls") or []
        if not calls:
            answer = reply.get("content") or ""
            messages.append({"role": "assistant", "content": answer})
            return {"ok_transport": True, "answer": answer, "trace": trace, "messages": messages,
                    "format_errors": format_errors, "steps": steps, "rounds": round_no + 1,
                    "annotations": annotations, "request_note": bool(note),
                    "elapsed_seconds": round(time.monotonic() - started, 3)}
        messages.append({"role": "assistant", "content": "", "tool_calls": [
            {"id": f"call_{round_no}_{i}", "name": c["name"], "arguments": c["arguments"]}
            for i, c in enumerate(calls)]})
        for i, call in enumerate(calls):
            args = dict(call["arguments"])
            if call["name"] in bind:
                args["principal"] = principal
            output = dispatch(call["name"], args)
            parsed = json.loads(output)
            findings = checks.check_output(call["name"], args, parsed, prompt, list(trace))
            annotations += bool(findings)
            trace.append({"name": call["name"], "arguments": args, "output": parsed})  # raw, scored
            messages.append({"role": "tool", "tool_call_id": f"call_{round_no}_{i}",
                             "name": call["name"], "content": checks.annotate(output, findings)})
    return {"ok_transport": False, "error": "MAX_TOOL_ROUNDS", "answer": "", "trace": trace,
            "messages": messages, "format_errors": format_errors, "steps": steps,
            "annotations": annotations, "request_note": bool(note),
            "elapsed_seconds": round(time.monotonic() - started, 3)}


def run_s0(backend, episode: dict) -> dict:
    def dispatch(name, args):
        return contract.dispatch(episode["world"], episode["principal"], name, args)
    # The checks see the user's request text, never the episode's expectations or world.
    record = run_episode_s0(backend, episode["principal"], generator.task_text(episode),
                            dispatch, contract.TOOL_SCHEMAS, bench.BIND)
    record.update({"episode": episode["id"], "family": episode["family"]})
    return record


# ------------------------------------------------------------------ commands
def cmd_check(args):
    status = bench.verify_freeze()
    problems = list(status["problems"])
    if PREREG.exists():
        reg = json.loads(PREREG.read_text())
        if reg.get("code_sha256") != s0_hashes():
            problems.append("checks.py/bench_s0.py differ from PREREGISTRATION_S0.json")
    else:
        problems.append("PREREGISTRATION_S0.json missing")
    episodes = bench.load_episodes()

    class Oracle:
        """The scripted plan; it parses tool JSON, so it reads messages without annotations."""

        def __init__(self, episode):
            self.inner = agent.OracleBackend(episode)

        def step(self, messages, tools):
            clean = [dict(m, content=m["content"].split("\n[runtime check]")[0])
                     if m.get("role") == "tool" else m for m in messages]
            return self.inner.step(clean, tools)

    oracle_pass, annotated = 0, 0
    for e in episodes:
        rec = run_s0(Oracle(e), e)
        annotated += bool(rec["annotations"] or rec["request_note"])
        oracle_pass += bench.score_records([rec], [e])[0]["pass"]
    print(json.dumps({"problems": problems, "oracle_s0": f"{oracle_pass}/{len(episodes)}",
                      "episodes_with_annotations_on_oracle_path": annotated}, indent=2))
    if problems or oracle_pass != len(episodes):
        raise SystemExit(1)


def cmd_eval(args):
    status = bench.verify_freeze()
    if status["problems"]:
        raise SystemExit("Refusing: frozen suite changed: " + "; ".join(status["problems"]))
    reg = json.loads(PREREG.read_text())
    if reg.get("code_sha256") != s0_hashes() and not args.allow_unregistered:
        raise SystemExit("Refusing: code differs from PREREGISTRATION_S0.json")
    out = pathlib.Path(args.out)
    summary_path = out.with_suffix(".summary.json")
    if out.exists() or summary_path.exists():
        raise SystemExit("Refusing to overwrite a receipt.")
    os.umask(0o077)
    episodes = bench.load_episodes(args.episodes)
    if args.limit:
        episodes = episodes[:args.limit]
    backend = agent.OpenAIBackend(args.base_url, args.model, None, temperature=0.0,
                                  max_tokens=args.max_tokens, seed=None)
    runner = bench.run if args.arm == "plain" else run_s0
    started, records = time.monotonic(), []
    for episode in episodes:
        record = runner(backend, episode)
        record["label"], record["arm"] = args.label, args.arm
        records.append(record)
        bench.write_jsonl(out, [record], mode="a")
        print(record["episode"], "ok" if record["ok_transport"] else record.get("error"),
              f"{record['elapsed_seconds']}s", flush=True)
    scores = bench.score_records(records, episodes)
    prompt_tokens = sum((s.get("usage") or {}).get("prompt_tokens", 0) for r in records for s in r["steps"])
    completion_tokens = sum((s.get("usage") or {}).get("completion_tokens", 0) for r in records for s in r["steps"])
    report = {"schema": "haven-s0-eval-1", "arm": args.arm, "label": args.label, "model": args.model,
              "hardware": args.hardware, "engine": args.engine, "gguf_sha256": args.gguf_sha256,
              "temperature": 0.0, "max_tokens": args.max_tokens,
              "frozen_sha256": sha256_file(bench.FROZEN), "s0_code_sha256": s0_hashes(),
              "records_sha256": sha256_file(out), "wall_seconds": round(time.monotonic() - started, 1),
              "episodes_planned": len(episodes), "episodes_completed": len(records),
              "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
              "mean_episode_seconds": round(sum(r["elapsed_seconds"] for r in records) / max(len(records), 1), 2),
              "annotated_episodes": sum(1 for r in records if r.get("annotations") or r.get("request_note")),
              "summary": bench.summarize(scores),
              "scores": [{"episode": s["episode"], "family": s["family"], "pass": s["pass"],
                          "violations": s.get("violations")} for s in scores]}
    summary_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("arm", "label", "episodes_completed", "wall_seconds")}
                     | {"pass": report["summary"].get("pass")}, indent=2))


def sign_test(gained: int, lost: int) -> float:
    n, k = gained + lost, min(gained, lost)
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def compare(a: dict, b: dict, ref_35b: int | None = None) -> dict:
    pa = {s["episode"]: bool(s["pass"]) for s in a["scores"]}
    pb = {s["episode"]: bool(s["pass"]) for s in b["scores"]}
    fam = {s["episode"]: s["family"] for s in a["scores"]}
    common = sorted(set(pa) & set(pb))
    gained = sum(1 for e in common if pb[e] and not pa[e])
    lost = sum(1 for e in common if pa[e] and not pb[e])
    by_family = collections.defaultdict(lambda: [0, 0, 0])
    for e in common:
        row = by_family[fam[e]]
        row[0] += pa[e]; row[1] += pb[e]; row[2] += 1
    out = {"a": a["label"], "b": b["label"], "episodes": len(common),
           "a_pass": sum(pa[e] for e in common), "b_pass": sum(pb[e] for e in common),
           "gained": gained, "lost": lost, "sign_test_p": round(sign_test(gained, lost), 6),
           "mean_episode_seconds": {"a": a.get("mean_episode_seconds"), "b": b.get("mean_episode_seconds")},
           "by_family": {f: {"a": r[0], "b": r[1], "n": r[2]} for f, r in sorted(by_family.items())}}
    if ref_35b is not None:
        out["round2_reference_35b"] = ref_35b
        out["b_minus_35b_reference"] = out["b_pass"] - ref_35b
    return out


def cmd_compare(args):
    a = json.loads(pathlib.Path(args.a).read_text())
    b = json.loads(pathlib.Path(args.b).read_text())
    print(json.dumps(compare(a, b, args.ref_35b), indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(func=cmd_check)
    e = sub.add_parser("eval")
    e.add_argument("--arm", choices=["plain", "s0"], required=True)
    e.add_argument("--base-url", required=True)
    e.add_argument("--model", default="haven-local")
    e.add_argument("--label", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--episodes", default=None, help="alternate JSONL (e.g. fresh seed); default frozen")
    e.add_argument("--limit", type=int, default=0)
    e.add_argument("--max-tokens", type=int, default=1024)
    e.add_argument("--hardware", default="unknown")
    e.add_argument("--engine", default="llama.cpp b11146")
    e.add_argument("--gguf-sha256", default=None)
    e.add_argument("--allow-unregistered", action="store_true", help="smoke tests only")
    e.set_defaults(func=cmd_eval)
    c = sub.add_parser("compare")
    c.add_argument("--a", required=True)
    c.add_argument("--b", required=True)
    c.add_argument("--ref-35b", type=int, default=None)
    c.set_defaults(func=cmd_compare)
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
