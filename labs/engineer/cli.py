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
import time

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


def brief(limit=12):
    """State recovered from records (task dirs, ledgers, approvals, leases, fleet, skills), not transcripts."""
    import fleet
    import registry
    import session
    import skills
    from ledger import Ledger
    out = [f"# Haven engineer brief — {time.strftime('%Y-%m-%d %H:%M %Z')}"]
    tasks = session.list_tasks(limit=400)
    running = [t for t in tasks if t.get("status") == "running"]
    out.append(f"\n## Running tasks ({len(running)})")
    out += [f"- {t['task_id']} {t['agent']} [{t['mode']}] {t.get('workspace_name')}: {t['prompt'][:90]}" for t in running]
    out.append("\n## Recent outcomes (ledger-verified)")
    for t in [t for t in tasks if t.get("status") != "running"][:limit]:
        p = session.STATE / "tasks" / t["task_id"] / "ledger.jsonl"
        ok = Ledger(p, session=t["task_id"]).verify() if p.exists() else None
        kids = sum(1 for x in tasks if x.get("parent_id") == t["task_id"])
        out.append(f"- {t['task_id']} {t['agent']} {t['status']}{' +%d children' % kids if kids else ''}"
                   f" ledger={'ok' if ok else 'none' if ok is None else 'TAMPERED'}: {t['prompt'][:80]}")
    appr = session.pending_approvals()
    out.append(f"\n## Pending approvals ({len(appr)})")
    out += [f"- {a['receipt']} {a['agent']} {a['tool']}: {a['reason']}" for a in appr]
    leases = registry.Leases(session.STATE).all()
    out.append(f"\n## File leases ({len(leases)})")
    out += [f"- {p} held by {l['task_id']}" for p, l in leases.items()]
    obs = fleet.observe()
    out.append("\n## Fleet")
    for n in obs["nodes"]:
        o = n["observation"]
        gpu = (o.get("gpus") or [{}])[0]
        out.append(f"- {n['name']} {o.get('status')} trust={n['trust']} mem_free={round((o.get('mem_avail') or 0) / 1e9, 1)}GB "
                   f"gpu={gpu.get('name')} {gpu.get('mem_used_mb')}/{gpu.get('mem_total_mb')}MiB "
                   f"models={[m.get('alias') or m.get('file') for m in o.get('models', [])]} units={o.get('units')}")
    out.append(f"- {len(obs['candidates'])} discovered, unenrolled candidates")
    out.append("\n## Inherited skills")
    out += [f"- {s['name']} {s['status']} {str(s.get('sha256'))[:12]} {s.get('validation_summary')}"
            for s in skills.list_skills()["skills"]]
    return "\n".join(out)


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
    rr = sub.add_parser("run-remote", help="model here, tools on an enrolled node, commits come back as a branch")
    rr.add_argument("--node", required=True)
    rr.add_argument("--repo", required=True, help="local git repo; cloned to the node, never modified here")
    rr.add_argument("--agent", required=True)
    rr.add_argument("--mode", choices=policy.MODES, default="engineer")
    rr.add_argument("--network", choices=("on", "off"), default="off")
    rr.add_argument("--max-steps", type=int, default=30)
    rr.add_argument("prompt")
    sub.add_parser("agents")
    sub.add_parser("brief", help="state for a returning supervisor, from records")
    sub.add_parser("sandbox")
    v = sub.add_parser("verify")
    v.add_argument("ledger")
    args = ap.parse_args(argv)
    if args.cmd == "agents":
        for a in load_agents():
            print(f"{a['id']:<22} {a.get('kind', 'local'):<8} inference={a.get('inference_host', '?'):<10} "
                  f"{a.get('label', '')}")
        return
    if args.cmd == "brief":
        print(brief())
        return
    if args.cmd == "sandbox":
        print(json.dumps(sandbox.describe(), indent=2))
        return
    if args.cmd == "verify":
        led = Ledger(args.ledger)
        print(json.dumps({"verified": led.verify(), "receipts": len(led.receipts())}))
        return
    if args.cmd == "run-remote":
        import remote
        import trust
        rec = remote.run_remote_task(args.node, args.repo, args.agent, args.mode, args.prompt,
                                     max_steps=args.max_steps, network=args.network == "on", on_event=_print_event,
                                     gate=trust.Gate())
        print(f"\nstatus: {rec['status']}  tool host: {rec['tool_host']}  receipts: {len(rec['receipts'])}  "
              f"ledger verified: {rec['ledger_verified']}  wall: {rec.get('wall_s')}s")
        print("\n" + (rec.get("answer") or "(no answer)"))
        print("\n" + (rec.get("runtime_footer") or ""))
        print(f"\nbranch: {rec.get('fetched_branch')} @ {rec.get('fetched_commit')} ({rec.get('new_commits')} new)")
        print(f"record: {STATE / 'tasks' / rec['task_id'] / 'record.json'}")
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
