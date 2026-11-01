"""Read-only tools. Each answers from records or a live probe and never changes Haven."""
from __future__ import annotations

import tempfile
from pathlib import Path

from ..registry import ToolError, ToolSpec
from . import ID, engineer_state, obj


def _engineer_summary():
    import scheduler
    import session
    tasks = session.list_tasks(limit=200)
    jobs = scheduler.Store().jobs()
    by_state = {}
    for j in jobs:
        by_state[j["state"]] = by_state.get(j["state"], 0) + 1
    return {"running_tasks": [{k: t.get(k) for k in ("task_id", "agent", "mode", "workspace_name")}
                              | {"prompt": (t.get("prompt") or "")[:100]} for t in tasks if t.get("status") == "running"],
            "pending_approvals": len(session.pending_approvals()),
            "jobs_by_state": by_state}


def status(ctx):
    out = {"evidence": "observed", "slink": ctx.slink.probe("status")}
    try:
        out["controller"] = _engineer_summary()
    except Exception as e:
        out["controller"] = {"unknown": True, "error": f"{type(e).__name__}: {str(e)[:200]}"}
    return out


def gpu(ctx):
    return {"evidence": "observed", "gpu": ctx.slink.probe("gpu")}


def models(ctx):
    return {"evidence": "observed", **ctx.slink.probe("models")}


def sentinel(ctx):
    return {"evidence": "observed (saved report; the audit itself is not re-run)", "sentinel": ctx.slink.probe("sentinel")}


def brief(ctx):
    import cli
    text = cli.brief()
    return {"evidence": "from records", "brief": text[:12000], "truncated": len(text) > 12000}


def fleet(ctx):
    import fleet as fl
    obs = fl.observe(cache_s=10)
    return {"evidence": "observed", "nodes": [{"name": n["name"], "trust": n.get("trust"),
                                               **{k: n["observation"].get(k) for k in
                                                  ("status", "gpus", "mem_avail", "models", "units", "error")}}
                                              for n in obs["nodes"]],
            "unenrolled_candidates": len(obs.get("candidates", []))}


def jobs(ctx, id=None, limit=20):
    import scheduler
    store = scheduler.Store()
    if id:
        try:
            return {"job": store.load(id)}
        except (FileNotFoundError, scheduler.SchedError):
            raise ToolError("not_found", f"no scheduler job {id}", refused=True) from None
    rows = store.jobs()[-limit:]
    return {"jobs": [{"id": j["id"], "state": j["state"], "node": j.get("node"), "receipt": j.get("receipt"),
                      "command": j["spec"]["command"][:120]} for j in rows]}


def lab_job(ctx, id):
    return {"job": ctx.slink.labctl("job", id)}


def tasks(ctx, limit=15):
    import session
    return {"tasks": [{k: t.get(k) for k in ("task_id", "agent", "mode", "status", "workspace_name", "created")}
                      | {"prompt": (t.get("prompt") or "")[:120]} for t in session.list_tasks(limit=limit)]}


def approvals(ctx):
    import session
    return {"note": "Listed for awareness only. Only the owner decides approvals (Haven console).",
            "pending": [{k: a.get(k) for k in ("receipt", "task_id", "agent", "tool", "reason", "created")}
                        for a in session.pending_approvals()]}


def _ledger_for(ctx, task_id):
    from ledger import Ledger, LedgerError
    if not task_id:
        if ctx.receipts is None or ctx.receipts.task_id is None:
            return None, None
        return ctx.receipts.ledger, ctx.receipts.task_id
    p = engineer_state() / "tasks" / task_id / "ledger.jsonl"
    if not p.exists():
        raise ToolError("not_found", f"task {task_id} has no ledger", refused=True)
    try:
        return Ledger(p, session=task_id), task_id
    except (LedgerError, ValueError, KeyError) as e:
        return {"tampered": str(e)}, task_id


def receipts_verify(ctx, task_id=None, limit=20):
    led, tid = _ledger_for(ctx, task_id)
    if led is None:
        return {"task_id": None, "note": "this Hermes session has made no changes yet, so it has no ledger"}
    if isinstance(led, dict):
        return {"task_id": tid, "verified": False, "problem": led["tampered"]}
    rows = led.receipts()
    return {"task_id": tid, "verified": led.verify(), "receipts_total": len(rows),
            "receipts": [{k: r.get(k) for k in ("receipt", "tool", "status", "summary", "reason", "error")}
                         for r in rows[-limit:]]}


def check_answer(ctx, text, task_id=None):
    from ledger import Ledger
    led, tid = _ledger_for(ctx, task_id)
    if isinstance(led, dict):
        return {"task_id": tid, "ok": False, "problem": "ledger failed verification: " + led["tampered"]}
    if led is None:
        with tempfile.TemporaryDirectory() as t:  # no receipts yet: every cited id is unissued
            return {"task_id": None, **Ledger(Path(t) / "empty.jsonl").check_answer(text)}
    return {"task_id": tid, **led.check_answer(text)}


def specs():
    lim = {"type": "integer", "minimum": 1, "maximum": 100}
    return [
        ToolSpec("haven_status", "Haven at a glance: Model Lab engine and connection, who holds Slink's GPU, running "
                 "haven services, latest Sentinel findings, running engineer tasks, pending approvals and job counts. "
                 "Start here.", obj({}), status, rate_per_min=20),
        ToolSpec("haven_gpu", "Who holds Slink's GPU right now: each compute process with its systemd unit and owner "
                 "(lab, strata or peer), and whether the Lab could load a model without interrupting anyone.",
                 obj({}), gpu),
        ToolSpec("haven_models", "Models the Model Lab can serve: id, name, downloaded or not, size, admission stage, "
                 "and which one is loaded.", obj({}), models),
        ToolSpec("haven_sentinel", "Latest daily Sentinel security audit of Slink (saved report): counts and every "
                 "finding that is not passing.", obj({}), sentinel),
        ToolSpec("haven_brief", "The engineer controller's brief from records: running tasks, ledger-verified "
                 "outcomes, approvals, leases, fleet and admitted skills (Markdown).", obj({}), brief, rate_per_min=6),
        ToolSpec("haven_fleet", "Enrolled compute nodes with live status, GPUs, free memory, served models and units.",
                 obj({}), fleet, rate_per_min=10),
        ToolSpec("haven_jobs", "Scheduler jobs (CPU work on enrolled nodes): the recent list, or one job in full by id.",
                 obj({"id": ID, "limit": lim}), jobs),
        ToolSpec("haven_lab_job", "Progress of a Model Lab job (model load, Strata connect) by the job_id a change "
                 "tool returned.", obj({"id": ID}, ["id"]), lab_job, rate_per_min=60),
        ToolSpec("haven_tasks", "Recent engineer tasks with status (running, finished, cancelled).",
                 obj({"limit": lim}), tasks),
        ToolSpec("haven_approvals", "Actions waiting for the owner's decision in the Haven console. Read-only: Hermes "
                 "never decides approvals.", obj({}), approvals),
        ToolSpec("haven_receipts", "Verify a signed receipt ledger and list its receipts: this Hermes session's by "
                 "default, or an engineer task's by task_id.", obj({"task_id": ID, "limit": lim}), receipts_verify),
        ToolSpec("haven_check_answer", "Check a draft answer against the receipt ledger before sending it: flags "
                 "receipt ids that were never issued, failures described as successes, and success claims (tests "
                 "pass, committed, deployed) with no matching receipt.",
                 obj({"text": {"type": "string", "maxLength": 20000}, "task_id": ID}, ["text"]), check_answer),
    ]
