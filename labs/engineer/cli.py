#!/usr/bin/env python3
"""Run one Haven engineering task from the command line.

  cli.py run --workspace DIR --agent qwen35-4b --mode engineer "Fix the failing test"
  cli.py agents                       # configured agents and where they run
  cli.py sandbox                      # what OS enforcement this host has
  cli.py verify LEDGER.jsonl          # check a receipt ledger's chain and signatures

Agents come from the private ~/.config/haven-engineer/agents.json (see
agents.example.json). Records and ledgers go to ~/.local/state/haven-engineer/tasks/.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import policy  # noqa: E402
import sandbox  # noqa: E402
from ledger import Ledger  # noqa: E402

from runtime import STATE, agent_by_id as _agent_by_id, load_agents, owner_scope, run_task  # noqa: E402,F401


def agent_by_id(agent_id):
    try:
        return _agent_by_id(agent_id)
    except KeyError as e:
        raise SystemExit(f"{e}; see `cli.py agents`")


def _print_event(e):
    k = e["type"]
    if k == "model_turn":
        calls = ", ".join(c for c in e["calls"] if c) or "answer"
        print(f"  · model step {e.get('step')} {e.get('seconds', '')}{'s' if e.get('seconds') is not None else ''} → {calls}", flush=True)
    elif k == "action" and e.get("status") in ("refused", "succeeded", "failed", "unknown"):
        extra = f" exit {e['exit_code']}" if e.get("exit_code") is not None else ""
        print(f"    {e['receipt']} {e['tool']}: {e['status']}{extra} {e.get('reason', '') or ''}", flush=True)
    elif k == "approval":
        print(f"    ? approval needed for {e['receipt']}: {e['summary']} ({e['reason']})", flush=True)
    elif k == "nudge":
        print(f"  ! runtime nudge: {e['kind']}", flush=True)


def tty_approver(rid, tool, args, decision):
    if not sys.stdin.isatty():
        return "no interactive owner"
    ans = input(f"Approve {rid} {tool} {json.dumps(args)[:200]}? ({decision.reason}) [y/N] ")
    return "approve" if ans.strip().lower() in ("y", "yes") else "reject"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--workspace", required=True)
    r.add_argument("--agent", required=True)
    r.add_argument("--mode", choices=policy.MODES, default="engineer")
    r.add_argument("--network", choices=("owner", "on", "off"), default="owner",
                   help="sandbox network: owner default from scope.json, or force on/off")
    r.add_argument("--max-steps", type=int, default=30)
    r.add_argument("prompt")
    sub.add_parser("agents")
    sub.add_parser("sandbox")
    v = sub.add_parser("verify")
    v.add_argument("ledger")
    args = ap.parse_args(argv)
    if args.cmd == "agents":
        for a in load_agents():
            print(f"{a['id']:<22} {a.get('kind', 'local'):<8} inference={a.get('inference_host', '?'):<10} "
                  f"{a.get('label', '')}")
        return
    if args.cmd == "sandbox":
        print(json.dumps(sandbox.describe(), indent=2))
        return
    if args.cmd == "verify":
        led = Ledger(args.ledger)
        print(json.dumps({"verified": led.verify(), "receipts": len(led.receipts())}))
        return
    agent = agent_by_id(args.agent)
    print(f"task → {agent['id']} on {agent.get('inference_host', '?')}; tools on this host; mode {args.mode}; "
          f"network {'granted' if (owner_scope().get('network') if args.network == 'owner' else args.network == 'on') else 'off'}")
    rec = run_task(args.workspace, agent, args.mode, args.prompt,
                   approver=tty_approver if sys.stdin.isatty() else None, on_event=_print_event,
                   network={"owner": None, "on": True, "off": False}[args.network], max_steps=args.max_steps)
    print(f"\nstatus: {rec['status']}  steps: {rec['steps']}  tool calls: {rec['tool_calls']}  wall: {rec['wall_s']}s")
    if rec.get("error"):
        print("error:", rec["error"])
    print("\n" + (rec["answer"] or "(no answer)"))
    print("\n" + rec["runtime_footer"])
    if rec.get("answer_check") and not rec["answer_check"]["ok"]:
        print("answer check:", json.dumps(rec["answer_check"]))
    print(f"\nrecord: {STATE / 'tasks' / rec['task_id'] / 'record.json'}")


if __name__ == "__main__":
    main()
