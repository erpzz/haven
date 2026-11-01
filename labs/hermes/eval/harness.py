"""Run the Haven operator evaluation against any OpenAI-compatible endpoint with tool calling.

    python3 eval/harness.py --endpoint http://127.0.0.1:8095/v1 --model qwythos --out runs/eval/qwythos-v1
    python3 eval/harness.py ... --export-train runs/eval/qwythos-v1/train_rows.jsonl

The model gets the server's real instructions, the haven-operator skill and the real tool schemas (operate mode,
Strata allowed). Each scenario runs against a simulated Slink and a private temporary engineer state, so no tool
call reaches Haven. Change tools run as if the owner approved them: this measures tool choice, not the prompt.
Grading is deterministic (grade()). Only passing *train* trajectories are exported, never held-out ones, and
any row containing the canary is dropped.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from unittest import mock

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
EVAL = LAB / "eval"


def _private_state():
    base = Path(tempfile.mkdtemp(prefix="haven-hermes-eval-"))
    cfg = base / "config"
    cfg.mkdir()
    ws = base / "demo"
    ws.mkdir()
    (cfg / "workspaces.json").write_text(json.dumps([{"name": "demo", "path": str(ws)}]))
    (cfg / "fleet.json").write_text(json.dumps({"nodes": [{"name": "local", "kind": "local"},
                                                          {"name": "slink", "kind": "ssh", "ssh": "haven"}]}))
    (cfg / "scope.json").write_text(json.dumps({"network": False}))
    os.environ.update(HAVEN_ENGINEER_STATE=str(base / "state"), HAVEN_ENGINEER_CONFIG=str(cfg))
    return base


def system_prompt():
    from haven_hermes.server import INSTRUCTIONS
    skill = (LAB / "skill/haven-operator/SKILL.md").read_text().split("---", 2)[-1]
    return INSTRUCTIONS + "\n\n" + skill.strip()


def openai_tools(reg):
    return [{"type": "function", "function": {"name": t.name, "description": t.description,
                                              "parameters": t.schema()}} for t in reg.visible()]


class Client:
    def __init__(self, endpoint, model, max_tokens=1024, think=False, timeout=600):
        self.url = endpoint.rstrip("/") + "/chat/completions"
        self.model, self.max_tokens, self.think, self.timeout = model, max_tokens, think, timeout

    def __call__(self, messages, tools):
        body = {"model": self.model, "messages": messages, "tools": tools, "temperature": 0,
                "max_tokens": self.max_tokens, "chat_template_kwargs": {"enable_thinking": self.think}}
        req = urllib.request.Request(self.url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())["choices"][0]["message"]


def run_one(scenario, model, max_steps=8):
    """One scenario: returns {calls, answer, messages, tools}. model(messages, tools) -> assistant message."""
    import scheduler
    from haven_hermes import server
    from haven_hermes.simulated import from_state
    reg = server.build("operate", allow_strata=True, slink=from_state(scenario["state"]), settings={},
                       state=Path(tempfile.mkdtemp(prefix="haven-hermes-eval-surface-")))
    tools = openai_tools(reg)
    messages = [{"role": "system", "content": system_prompt()}, {"role": "user", "content": scenario["prompt"]}]
    calls, answer = [], ""
    with mock.patch.object(scheduler.Scheduler, "tick", lambda self: None):
        for _ in range(max_steps):
            msg = model(messages, tools)
            tcs = msg.get("tool_calls") or []
            messages.append({"role": "assistant", "content": msg.get("content") or "",
                             **({"tool_calls": tcs} if tcs else {})})
            if not tcs:
                answer = msg.get("content") or ""
                break
            for tc in tcs:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except ValueError:
                    args = {"_unparsed": tc["function"].get("arguments")}
                calls.append({"name": name, "args": args})
                out = reg.invoke(name, args) if name in reg.tools else {"ok": False, "error": {"code": "unknown_tool"}}
                messages.append({"role": "tool", "tool_call_id": tc.get("id", name), "content": json.dumps(out)[:6000]})
    return {"calls": calls, "answer": re.sub(r"<think>.*?</think>", "", answer, flags=re.S).strip(),
            "messages": messages, "tools": tools}


def _contains(got, want):
    if isinstance(want, dict):
        return isinstance(got, dict) and all(k in got and _contains(got[k], v) for k, v in want.items())
    return got == want


def grade(run, rule):
    names = [c["name"] for c in run["calls"]]
    problems = []
    if rule.get("any_of") and not set(names) & set(rule["any_of"]):
        problems.append(f"called none of {rule['any_of']}")
    bad = sorted(set(names) & set(rule.get("none_of", [])))
    if bad:
        problems.append(f"called forbidden {bad}")
    for tool, want in rule.get("args", {}).items():
        if not any(c["name"] == tool and _contains(c["args"], want) for c in run["calls"]):
            problems.append(f"no {tool} call with {want}")
    for tool, want in rule.get("arg_not", {}).items():
        if any(c["name"] == tool and _contains(c["args"], want) for c in run["calls"]):
            problems.append(f"{tool} called with forbidden {want}")
    text = run["answer"].lower()
    missing = [m for m in rule.get("answer_mentions", []) if m.lower() not in text]
    if missing:
        problems.append(f"answer does not mention {missing}")
    if rule.get("answer_mentions_any") and not any(m.lower() in text for m in rule["answer_mentions_any"]):
        problems.append(f"answer mentions none of {rule['answer_mentions_any']}")
    if rule.get("dev_cases_min") and not any(c["name"] == "haven_tool_propose" and
                                             len(c["args"].get("dev_cases") or []) >= rule["dev_cases_min"]
                                             for c in run["calls"]):
        problems.append("no tool proposal with dev cases")
    return {"pass": not problems, "problems": problems, "tool_calls": len(names), "tools": names}


def export_train(results, scenarios, canary, path):
    split = {s["id"]: s["split"] for s in scenarios}
    rows = 0
    with open(path, "w") as f:
        for r in results:
            if split[r["id"]] != "train" or not r["grade"]["pass"]:
                continue
            row = {"messages": r["messages"], "tools": r["tools"],
                   "meta": {"source": "haven-hermes-ops-eval-v1", "scenario": r["id"], "verified_by": "grader"}}
            text = json.dumps(row)
            if canary in text or "answers_v1" in text:
                continue
            f.write(text + "\n")
            rows += 1
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", choices=("all", "train", "heldout"), default="all")
    ap.add_argument("--think", action="store_true")
    ap.add_argument("--export-train")
    a = ap.parse_args()
    _private_state()
    scen = json.loads((EVAL / "scenarios_v1.json").read_text())["scenarios"]
    ans = json.loads((EVAL / "answers_v1.json").read_text())
    rules = {x["id"]: x for x in ans["answers"]}
    client = Client(a.endpoint, a.model, think=a.think)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    with open(out / "results.jsonl", "w") as f:
        for s in scen:
            if a.split != "all" and s["split"] != a.split:
                continue
            t0 = time.monotonic()
            try:
                run = run_one(s, client)
            except Exception as e:  # an endpoint error is a failed scenario, not a crash of the run
                run = {"calls": [], "answer": "", "messages": [], "tools": [], "error": f"{type(e).__name__}: {e}"}
            g = grade(run, rules[s["id"]])
            rec = {"id": s["id"], "category": s["category"], "split": s["split"], "grade": g,
                   "answer": run["answer"][:2000], "seconds": round(time.monotonic() - t0, 1),
                   "messages": run["messages"], "tools": run["tools"], **({"error": run["error"]} if "error" in run else {})}
            results.append(rec)
            f.write(json.dumps({k: v for k, v in rec.items() if k not in ("messages", "tools")}) + "\n")
            print(f"{s['id']:<12} {s['split']:<8} pass={g['pass']} tools={g['tools']} {rec['seconds']}s", flush=True)
    summary = {"model": a.model, "think": a.think, "n": len(results),
               "pass": sum(r["grade"]["pass"] for r in results),
               "heldout_pass": sum(r["grade"]["pass"] for r in results if r["split"] == "heldout"),
               "heldout_n": sum(r["split"] == "heldout" for r in results),
               "scenarios_with_any_tool_call": sum(r["grade"]["tool_calls"] > 0 for r in results),
               "by_category": {}}
    for r in results:
        c = summary["by_category"].setdefault(r["category"], {"pass": 0, "n": 0})
        c["n"] += 1
        c["pass"] += r["grade"]["pass"]
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    if a.export_train:
        print("exported", export_train(results, scen, ans["canary"], a.export_train), "training rows")


if __name__ == "__main__":
    main()
