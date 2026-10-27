"""Task runtime shared by the CLI, the console and MCP sessions.

run_task() starts one agent on one workspace in a TaskSession. The executor it
builds can delegate: `delegate` creates a bounded child task (registry.py) that
runs another configured agent, possibly on another model, and returns the
child's executor-observed result to the parent.
"""
from __future__ import annotations

import json
import os
import pathlib
import time

import policy
import registry
from executor import Executor
from ledger import Ledger
from session import STATE, TaskSession

HERE = pathlib.Path(__file__).resolve().parent
CONFIG = pathlib.Path(os.environ.get("HAVEN_ENGINEER_CONFIG", pathlib.Path.home() / ".config/haven-engineer"))


def load_agents():
    path = CONFIG / "agents.json"
    if not path.exists():
        path = HERE / "agents.example.json"
    return json.loads(path.read_text())["agents"]


def agent_by_id(agent_id):
    for a in load_agents():
        if a["id"] == agent_id:
            return a
    raise KeyError(f"unknown agent {agent_id}")


def owner_scope():
    """Owner-held defaults (network grant etc.). No tool writes this file."""
    path = CONFIG / "scope.json"
    return json.loads(path.read_text()) if path.exists() else {}


def read_key(agent):
    kf = agent.get("key_file")
    return pathlib.Path(os.path.expanduser(kf)).read_text().strip() if kf else ""


def default_child_agent():
    agents = load_agents()
    pref = owner_scope().get("default_child_agent")
    for a in agents:
        if a["id"] == pref:
            return a
    return next(a for a in agents if a.get("kind", "local") == "local")


def make_executor(sess, workspace, scope, agent_id, *, approver=None, write_allow=None, depth=0,
                  max_steps=30, emit=None):
    ledger = Ledger(sess.ledger_path, session=sess.tid)
    leases = registry.Leases(sess.state)
    ex = Executor(workspace, scope, ledger, agent=agent_id, approver=approver or sess.approver(),
                  on_event=emit or sess.emit, cancel=sess.cancel)
    ex.task_id, ex.leases, ex.write_allow, ex.depth = sess.tid, leases, write_allow, depth
    ex.budget_steps = max_steps
    ex.delegator = lambda **kw: delegate(sess, ex, **kw)
    ex.linked_ledgers = lambda: child_ledgers(sess)
    return ex


def run_task(workspace, agent_cfg, mode, prompt, *, session=None, network=None, max_steps=30, overrides=None,
             approver=None, on_event=None, parent=None, write_allow=None, depth=0, extra_meta=None):
    if network is None:
        network = bool(owner_scope().get("network"))
    tool_host = agent_cfg.get("tool_host") or os.uname().nodename.split(".")[0]
    meta = dict(agent=agent_cfg["id"], agent_kind=agent_cfg.get("kind", "local"), workspace=str(workspace),
                workspace_name=pathlib.Path(workspace).name, mode=mode, network=network,
                inference_host=agent_cfg.get("inference_host"), tool_host=tool_host,
                egress=agent_cfg.get("egress", "LOCAL"), prompt=prompt, max_steps=max_steps, depth=depth,
                parent_id=parent, **(extra_meta or {}))
    sess = session or TaskSession(**meta)
    if on_event:
        orig = sess.emit
        sess.emit = lambda e: (orig(e), on_event(e))
    if agent_cfg.get("kind") == "cli":
        import hosted
        return hosted.run(agent_cfg, sess, os.path.realpath(workspace), mode, prompt, network=network,
                          max_turns=max_steps + 10)
    from loop import Agent
    scope = policy.Scope(mode=mode, network=network)
    ex = make_executor(sess, workspace, scope, agent_cfg["id"], approver=approver, write_allow=write_allow,
                       depth=depth, max_steps=max_steps)
    opts = {**{k: agent_cfg[k] for k in ("thinking", "max_tokens", "temperature", "ctx_chars") if k in agent_cfg},
            **(overrides or {})}
    tools = opts.pop("tools", None)
    if tools is None and depth >= registry.MAX_DEPTH:
        tools = [t for t in ex_tools() if t != "delegate"]
    agent = Agent(ex, base_url=agent_cfg["base_url"], model=agent_cfg["model"], api_key=read_key(agent_cfg),
                  label=agent_cfg["id"], max_steps=max_steps, on_event=sess.emit, tools=tools, **opts)
    try:
        record = agent.run(prompt)
    except Exception as e:  # keep a record of crashes too
        record = {"status": "error", "error": f"{type(e).__name__}: {e}", "answer": "",
                  "runtime_footer": ex.ledger.footer()}
        sess.emit({"type": "task_finished", "status": "error", "error": record["error"]})
    finally:
        ex.stop_all()
        ex.leases.release(sess.tid)
    record.update({"task_id": sess.tid, "parent_id": parent, "workspace": ex.root.name,
                   "inference_host": agent_cfg.get("inference_host"), "tool_host": tool_host,
                   "sandbox": ex.sandbox["backend"], "network": network,
                   "receipts": [{k: r.get(k) for k in ("receipt", "tool", "status", "summary", "exit_code", "class",
                                                       "decided_by", "duration_s", "changed_paths")}
                                for r in ex.ledger.receipts()]})
    sess.finish(record)
    return record


def child_ledgers(sess):
    """Ledgers of every descendant task, so cited child receipts resolve."""
    out, frontier = [], [sess.tid]
    tasks = sess.state / "tasks"
    metas = []
    for d in tasks.iterdir() if tasks.exists() else []:
        try:
            metas.append(json.loads((d / "meta.json").read_text()))
        except (OSError, ValueError):
            continue
    while frontier:
        parent = frontier.pop()
        for m in metas:
            if m.get("parent_id") == parent:
                p = tasks / m["task_id"] / "ledger.jsonl"
                if p.exists():
                    out.append(Ledger(p, session=m["task_id"]))
                frontier.append(m["task_id"])
    return out


def ex_tools():
    from executor import TOOLS
    return list(TOOLS)


def delegate(parent_sess, parent_ex, *, task, agent=None, paths=None, mode=None, max_steps=None):
    """Run a bounded child task and return its executor-observed outcome."""
    if parent_ex.depth + 1 > registry.MAX_DEPTH:
        raise ValueError(f"delegation depth limit {registry.MAX_DEPTH} reached")
    cfg = agent_by_id(agent) if agent else default_child_agent()
    if cfg.get("kind") == "cli":
        raise ValueError("children are local agents; hosted agents are selected by the owner, not delegated to")
    scope = registry.child_scope(parent_ex.scope, mode)
    used = len(parent_ex.ledger.receipts())
    budget = max(3, min(int(max_steps or 15), max(3, parent_ex.budget_steps - used // 2)))
    leased = None
    if paths:
        leased = [str(parent_ex.resolve(p, must_exist=False)) for p in paths]
    child = TaskSession(state=parent_sess.state, agent=cfg["id"], agent_kind="local",
                        workspace=str(parent_ex.root), workspace_name=parent_ex.root.name, mode=scope.mode,
                        network=scope.network, inference_host=cfg.get("inference_host"),
                        tool_host=os.uname().nodename.split(".")[0], egress="LOCAL", prompt=task,
                        max_steps=budget, depth=parent_ex.depth + 1, parent_id=parent_sess.tid,
                        root_id=parent_sess.meta().get("root_id") or parent_sess.tid,
                        leased_paths=[str(pathlib.Path(p).relative_to(parent_ex.root)) for p in leased or []])
    if leased:
        ok, conflicts = parent_ex.leases.acquire(child.tid, leased)
        if not ok:
            child.finish({"status": "refused", "error": f"lease conflict {conflicts}"})
            raise ValueError(f"paths are leased by other tasks: {conflicts}")
    parent_sess.emit({"type": "child_started", "child_id": child.tid, "agent": cfg["id"], "mode": scope.mode,
                      "budget_steps": budget, "paths": paths or []})
    t0 = time.monotonic()
    if parent_sess.cancel.is_set():
        child.request_cancel()
    rec = run_task(parent_ex.root, cfg, scope.mode, task, session=child, network=scope.network, max_steps=budget,
                   parent=parent_sess.tid, write_allow=leased, depth=parent_ex.depth + 1)
    parent_sess.emit({"type": "child_finished", "child_id": child.tid, "status": rec.get("status"),
                      "wall_s": round(time.monotonic() - t0, 2)})
    return rec
