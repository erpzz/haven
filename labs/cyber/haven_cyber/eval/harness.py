"""Cyber capability evaluation: conditions A (model alone), B (+ retrieval), C (+ retrieval + tools), D (adapter).

    python -m haven_cyber.eval.harness --endpoint http://127.0.0.1:8095/v1 --model qwythos \
        --conditions A,B,C --split all --out runs/eval/qwythos-nothink

The model sees eval/scenarios/v1.json only. Grading uses eval/answers/v1.json (grade.py, deterministic). Results are
one JSON line per (scenario, condition) plus summary.json; report.py turns them into the capability-gap report.
Condition D is the same as C with a different --model/--endpoint (the adapter); the harness does not care.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

from .. import EVAL, RUNS
from ..kb import KB
from .grade import grade, strip_reasoning
from .toolenv import TOOLS, ToolEnv

SYSTEM = """You are a careful cloud and identity security analyst.
Work only from the task's artifacts, the reference material if provided, and tool results if tools are available.
Distinguish what the artifacts show from your own inference. Never invent tool output, ids or results; if you cannot
determine something, say so in the answer format (for example null or "unknown").
Finish with ONLY a JSON object using exactly the requested keys, no markdown."""
TOOL_SYSTEM = """
Tools are available in this task. Before answering, use the tools that apply to this task's artifacts or lab host to
gather or check evidence; a tool result outranks your own reading. If a tool returns an error, read it and adjust
(different tool, different arguments) instead of guessing. After the last tool result, reply with only the JSON object."""


def user_prompt(s: dict, refs: str, tools: bool) -> str:
    parts = [f"Task: {s['question']}"]
    if s.get("artifacts"):
        parts.append("Artifacts (JSON):\n" + json.dumps(s["artifacts"], separators=(",", ":")))
    else:
        parts.append("Artifacts: none provided.")
    if refs:
        parts.append(refs)
    parts.append("Answer format (JSON keys and allowed values):\n" + json.dumps(s["answer_format"]))
    return "\n\n".join(parts)


class Client:
    def __init__(self, endpoint: str, model: str, think: bool, max_tokens: int, timeout: float = 900):
        self.url = endpoint.rstrip("/") + "/chat/completions"
        self.model, self.think, self.max_tokens, self.timeout = model, think, max_tokens, timeout

    def chat(self, messages, tools=None) -> dict:
        body = {"model": self.model, "messages": messages, "temperature": 0, "max_tokens": self.max_tokens,
                "chat_template_kwargs": {"enable_thinking": self.think}}
        if tools:
            body["tools"] = tools
        req = urllib.request.Request(self.url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        t0 = time.monotonic()
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            out = json.loads(r.read())
        out["_latency_s"] = time.monotonic() - t0
        return out


def run_one(client: Client, s: dict, truth: dict, cond: str, kb: KB, max_rounds: int = 6) -> dict:
    refs, hits = ("", [])
    if cond in ("B", "C", "D"):
        refs, hits = kb.retrieve(s["question"], k=3, max_chars=4500)
    use_tools = cond in ("C", "D")
    env = ToolEnv(s, kb)
    msgs = [{"role": "system", "content": SYSTEM + (TOOL_SYSTEM if use_tools else "")},
            {"role": "user", "content": user_prompt(s, refs, use_tools)}]
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    latency, final, err = 0.0, "", None
    try:
        for _ in range(max_rounds + 1):
            resp = client.chat(msgs, TOOLS if use_tools else None)
            latency += resp["_latency_s"]
            for k in usage:
                usage[k] += (resp.get("usage") or {}).get(k, 0)
            m = resp["choices"][0]["message"]
            calls = m.get("tool_calls") or []
            if not calls:
                final = m.get("content") or ""
                break
            msgs.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": calls})
            for c in calls:
                try:
                    args = json.loads(c["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {"_unparseable": c["function"].get("arguments")}
                out = env.call(c["function"]["name"], args if isinstance(args, dict) else {})
                msgs.append({"role": "tool", "tool_call_id": c.get("id", ""), "content": json.dumps(out, default=str)[:12000]})
        else:
            err = "max_tool_rounds"
    except Exception as e:  # record, do not abort the whole run
        err = f"{type(e).__name__}: {e}"
    g = grade(final, truth)
    calls = env.log
    failed = [i for i, c in enumerate(calls) if c["kind"] != "ok"]
    recovered = bool(failed) and any(c["kind"] == "ok" for c in calls[failed[0] + 1:])
    hallucinated_result = (s["id"] == "tf-01" and not any(c["tool"] == "run_command" and c["kind"] == "ok" for c in calls)
                           and g.get("answer", {}).get("ports") not in (None, [], "null"))
    return {"id": s["id"], "category": s["category"], "split": s["split"], "condition": cond, **{k: v for k, v in g.items() if k != "answer"},
            "answer": g.get("answer"), "raw_tail": strip_reasoning(final)[-600:], "error": err,
            "tool_calls": len(calls), "bad_tool_calls": sum(c["kind"] == "bad" for c in calls),
            "hallucinated_tools": sum(c["kind"] == "hallucinated" for c in calls), "tool_errors_recovered": recovered,
            "tools_used": [c["tool"] for c in calls], "hallucinated_result": hallucinated_result,
            "retrieved": [f"{h.doc_id}#{h.section}" for h in hits], **usage, "latency_s": round(latency, 2)}


def summarize(rows: list[dict]) -> dict:
    out = {}
    for cond in sorted({r["condition"] for r in rows}):
        rs = [r for r in rows if r["condition"] == cond]
        n = len(rs)
        passed = [r for r in rs if r["pass"]]
        fp_eligible = [r for r in rs if r.get("fp_eligible")]
        out[cond] = {
            "n": n, "pass": len(passed), "pass_rate": round(len(passed) / n, 3) if n else 0,
            "check_rate": round(sum(r["checks_passed"] for r in rs) / max(1, sum(r["checks"] for r in rs)), 3),
            "false_positives": sum(r["false_positive"] for r in rs), "fp_eligible": len(fp_eligible),
            "unparsed": sum(not r["parsed"] for r in rs), "errors": sum(bool(r["error"]) for r in rs),
            "tool_calls": sum(r["tool_calls"] for r in rs), "bad_tool_calls": sum(r["bad_tool_calls"] for r in rs),
            "hallucinated_tools": sum(r["hallucinated_tools"] for r in rs),
            "hallucinated_results": sum(r["hallucinated_result"] for r in rs),
            "recovered_from_tool_error": sum(r["tool_errors_recovered"] for r in rs),
            "tool_calls_per_success": round(sum(r["tool_calls"] for r in passed) / len(passed), 2) if passed else None,
            "prompt_tokens": sum(r["prompt_tokens"] for r in rs), "completion_tokens": sum(r["completion_tokens"] for r in rs),
            "latency_s": round(sum(r["latency_s"] for r in rs), 1),
            "by_category": {c: f"{sum(r['pass'] for r in rs if r['category'] == c)}/{sum(r['category'] == c for r in rs)}"
                            for c in sorted({r["category"] for r in rs})},
            "by_split": {sp: f"{sum(r['pass'] for r in rs if r['split'] == sp)}/{sum(r['split'] == sp for r in rs)}"
                         for sp in sorted({r["split"] for r in rs})},
        }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--model", default="local")
    ap.add_argument("--conditions", default="A,B,C")
    ap.add_argument("--split", default="all", choices=["all", "dev", "heldout"])
    ap.add_argument("--only", default="", help="comma-separated scenario ids")
    ap.add_argument("--think", action="store_true")
    ap.add_argument("--max-tokens", type=int, default=0)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--version", default="v1")
    args = ap.parse_args(argv)
    sc = json.loads((EVAL / "scenarios" / f"{args.version}.json").read_text())["scenarios"]
    ans = json.loads((EVAL / "answers" / f"{args.version}.json").read_text())["answers"]
    if args.split != "all":
        sc = [s for s in sc if s["split"] == args.split]
    if args.only:
        keep = set(args.only.split(","))
        sc = [s for s in sc if s["id"] in keep]
    client = Client(args.endpoint, args.model, args.think, args.max_tokens or (8192 if args.think else 1536))
    kb = KB()
    args.out.mkdir(parents=True, exist_ok=True)
    res_path = args.out / "results.jsonl"
    done = set()
    if res_path.exists():  # resumable
        done = {(r["id"], r["condition"]) for r in map(json.loads, res_path.read_text().splitlines())}
    meta = {"model": args.model, "endpoint": args.endpoint, "think": args.think, "conditions": args.conditions,
            "version": args.version, "split": args.split, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (args.out / "meta.json").write_text(json.dumps(meta, indent=1))
    with res_path.open("a") as f:
        for s in sc:
            for cond in args.conditions.split(","):
                if (s["id"], cond) in done:
                    continue
                row = run_one(client, s, ans[s["id"]], cond, kb)
                row["fp_eligible"] = bool(ans[s["id"]].get("false_positive_if"))
                f.write(json.dumps(row, default=str) + "\n")
                f.flush()
                print(f"{s['id']:8s} {cond} pass={row['pass']} parsed={row['parsed']} tools={row['tools_used']} {row['latency_s']}s"
                      + (f" ERR {row['error']}" if row["error"] else ""), flush=True)
    rows = [json.loads(x) for x in res_path.read_text().splitlines()]
    summ = summarize(rows)
    (args.out / "summary.json").write_text(json.dumps({"meta": meta, "summary": summ}, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
