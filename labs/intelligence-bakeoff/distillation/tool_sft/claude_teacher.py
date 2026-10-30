"""Batched, turn-by-turn harness that lets a hosted Claude agent act as the teacher.

The agent sees exactly what agent.run_episode shows a model: the bakeoff system
prompt, the tool schemas, the authenticated user message and the real outputs of
the synthetic tools. It never sees check contracts, oracle plans or verdicts.
Tool execution, principal binding and the round limit are the same as agent.py,
and `export` writes records in run_world_episode's format so `run.py build`
consumes them unchanged.

  prepare  write a state file for a split or shard of it (no contracts inside)
  view     print the system prompt and tools (--header) or the open episodes
  step     apply one round of actions: tool calls or a final answer per episode
  export   state files -> agent-format records (one attempt per episode)
  score    verify exported records and write a run.py-style summary

States, actions and records are private run files; keep them out of Git.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agent  # noqa: E402
import run  # noqa: E402
import world  # noqa: E402

BIND = ("haven_read_note", "haven_list_resources")  # as in agent.run_world_episode


def _episodes(split):
    return {e["id"]: e for e in run.load_split(split)}


def _write(path, obj):
    tmp = pathlib.Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def cmd_prepare(args):
    out = pathlib.Path(args.out)
    if out.exists():
        raise SystemExit(f"{out} exists; refusing to overwrite a collection state.")
    episodes = run.load_split(args.split)
    index, count = (int(x) for x in args.shard.split("/"))
    chosen = [e for i, e in enumerate(episodes) if i % count == index]
    state = {"schema": "haven-tool-sft-claude-teacher-state-1", "split": args.split,
             "shard": args.shard, "teacher": args.teacher, "created_unix": int(time.time()),
             "episodes": [{"id": e["id"], "principal": e["principal"], "status": "open",
                           "rounds": 0, "answer": "", "trace": [],
                           "messages": [{"role": "system", "content": agent.SYSTEM},
                                        {"role": "user",
                                         "content": agent.user_message(e["principal"], e["prompt"])}]}
                          for e in chosen]}
    os.umask(0o077)
    _write(out, state)
    print(json.dumps({"episodes": len(chosen), "split": args.split, "shard": args.shard}))


def _show(ep):
    lines = [f"== {ep['id']}  status={ep['status']}  tool_rounds={ep['rounds']}/{agent.MAX_ROUNDS}"]
    for m in ep["messages"][1:]:
        if m["role"] == "user":
            lines.append("USER: " + m["content"].replace("\n\n", " | "))
        elif m["role"] == "assistant" and m.get("tool_calls"):
            for c in m["tool_calls"]:
                lines.append(f"  CALL {c['name']} {json.dumps(c['arguments'], ensure_ascii=False)}")
        elif m["role"] == "tool":
            lines.append(f"  RESULT {m['content']}")
        elif m["role"] == "assistant":
            lines.append("ANSWER: " + m["content"])
    return "\n".join(lines)


def cmd_view(args):
    if args.header:
        print("SYSTEM PROMPT (verbatim):\n" + agent.SYSTEM + "\n\nTOOLS:")
        print(json.dumps(world.TOOL_SCHEMAS, indent=1))
        return
    state = json.loads(pathlib.Path(args.state).read_text(encoding="utf-8"))
    shown = [e for e in state["episodes"] if args.all or e["status"] == "open"]
    for ep in shown:
        print(_show(ep) + "\n")
    done = sum(e["status"] != "open" for e in state["episodes"])
    print(f"[{done}/{len(state['episodes'])} finished, {len(state['episodes']) - done} open]")


def _apply(ep, action, world_ep):
    """One assistant turn, exactly as agent.run_episode would record it."""
    if "answer" in action:
        answer = str(action["answer"])
        ep["messages"].append({"role": "assistant", "content": answer})
        ep.update(answer=answer, status="done")
        return
    calls = action.get("calls")
    if not isinstance(calls, list) or not calls:
        raise ValueError(f"{ep['id']}: action needs a non-empty 'calls' list or an 'answer'.")
    round_no = ep["rounds"]
    clean = []
    for c in calls:
        if not isinstance(c, dict) or not isinstance(c.get("name"), str) \
                or not isinstance(c.get("arguments", {}), dict):
            raise ValueError(f"{ep['id']}: each call needs a string name and an arguments object.")
        clean.append({"name": c["name"], "arguments": dict(c.get("arguments", {}))})
    ep["messages"].append({"role": "assistant", "content": "", "tool_calls": [
        {"id": f"call_{round_no}_{i}", "name": c["name"], "arguments": c["arguments"]}
        for i, c in enumerate(clean)]})
    for i, call in enumerate(clean):
        bound = dict(call["arguments"])
        if call["name"] in BIND:
            bound["principal"] = ep["principal"]  # the model cannot switch identity
        output = world.dispatch(world_ep["world"], world_ep["principal"], call["name"], bound)
        ep["trace"].append({"name": call["name"], "arguments": bound, "output": json.loads(output)})
        ep["messages"].append({"role": "tool", "tool_call_id": f"call_{round_no}_{i}",
                               "name": call["name"], "content": output})
    ep["rounds"] = round_no + 1
    if ep["rounds"] >= agent.MAX_ROUNDS:
        ep["status"] = "max_rounds"


def cmd_step(args):
    path = pathlib.Path(args.state)
    state = json.loads(path.read_text(encoding="utf-8"))
    actions = json.loads(pathlib.Path(args.actions).read_text(encoding="utf-8"))
    worlds = _episodes(state["split"])
    by_id = {e["id"]: e for e in state["episodes"]}
    unknown = sorted(set(actions) - set(by_id))
    closed = sorted(k for k in actions if k in by_id and by_id[k]["status"] != "open")
    if unknown or closed:
        raise SystemExit(f"Rejected: unknown episodes {unknown}, already finished {closed}.")
    for episode_id, action in actions.items():
        _apply(by_id[episode_id], action, worlds[episode_id])
    _write(path, state)
    for episode_id in actions:
        print(_show(by_id[episode_id]) + "\n")
    done = sum(e["status"] != "open" for e in state["episodes"])
    print(f"[{done}/{len(state['episodes'])} finished, {len(state['episodes']) - done} open]")


def cmd_export(args):
    out = pathlib.Path(args.out)
    if out.exists():
        raise SystemExit(f"{out} exists; refusing to overwrite.")
    records = []
    for state_path in args.states:
        state = json.loads(pathlib.Path(state_path).read_text(encoding="utf-8"))
        worlds = _episodes(state["split"])
        for ep in state["episodes"]:
            w = worlds[ep["id"]]
            record = {"ok_transport": ep["status"] == "done", "answer": ep["answer"],
                      "trace": ep["trace"], "messages": ep["messages"], "format_errors": [],
                      "steps": [], "rounds": ep["rounds"] + (ep["status"] == "done"),
                      "elapsed_seconds": 0.0, "episode": ep["id"], "family": w["family"],
                      "track": w["track"], "label": args.label, "teacher": state.get("teacher")}
            if ep["status"] == "max_rounds":
                record["error"] = "MAX_TOOL_ROUNDS"
            elif ep["status"] == "open":
                record["error"] = "NOT_FINISHED"
            records.append(record)
    os.umask(0o077)
    run.write_jsonl(out, records)
    print(json.dumps({"records": len(records), "finished": sum(r["ok_transport"] for r in records),
                      "sha256": world.file_sha256(out)}))


def cmd_score(args):
    out = pathlib.Path(args.out)
    if out.exists():
        raise SystemExit(f"{out} exists; refusing to overwrite.")
    records = run.read_jsonl(args.records)
    scores = run.score_records(records)
    report = {"schema": "haven-tool-sft-eval-1", "label": args.label, "backend": "claude-agent-harness",
              "model": args.model, "sets": args.sets, "verifier_version": world.VERIFIER_VERSION,
              "records_sha256": world.file_sha256(args.records),
              "frozen_sha256": {p.name: world.file_sha256(p) for p in sorted(run.FROZEN.glob("*.jsonl"))},
              "episodes_completed": len(records), "summary": run.summarize(scores, records),
              "scores": scores}
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--split", choices=("train", "dev", "heldout"), required=True)
    p.add_argument("--shard", default="0/1", help="i/n: every n-th episode starting at i")
    p.add_argument("--teacher", required=True, help="Which model acts as the teacher.")
    p.add_argument("--out", required=True)
    p = sub.add_parser("view")
    p.add_argument("--state")
    p.add_argument("--header", action="store_true")
    p.add_argument("--all", action="store_true")
    p = sub.add_parser("step")
    p.add_argument("--state", required=True)
    p.add_argument("--actions", required=True)
    p = sub.add_parser("export")
    p.add_argument("--states", nargs="+", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("score")
    p.add_argument("--records", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--sets", default="heldout")
    p.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    {"prepare": cmd_prepare, "view": cmd_view, "step": cmd_step, "export": cmd_export,
     "score": cmd_score}[args.command](args)


if __name__ == "__main__":
    main()
