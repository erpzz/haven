"""Change tools. Each one is approved by the owner in Hermes, then receipted (registry + receipts.py).

They wrap the existing controllers and keep their rules: the Model Lab owns the GPU (and refuses on its own
lease too), the scheduler places CPU jobs only, engineer tasks queue their own risky steps for the owner.
Long work returns a job or task id at once; read tools follow it, so no MCP call blocks for minutes.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid

from .. import ROOT
from ..registry import ToolError, ToolSpec
from . import ID, engineer_config, engineer_state, obj

MODEL_ID = {"type": "string", "pattern": r"[a-z0-9][a-z0-9._-]{1,63}"}
STRATA_CONFIRM = "COLD_START_15MIN"


def _gpu_holders(ctx):
    g = ctx.slink.probe("gpu")
    if g.get("unknown"):
        raise ToolError("gpu_unknown", "could not read Slink's GPU state, so nothing was started: " + g.get("error", ""),
                        refused=True)
    peers = [a for a in g.get("compute_apps", []) if a.get("owner") == "peer"]
    return g, sorted({a.get("unit") or f"pid {a['pid']}" for a in peers} | set(g.get("peer_units_busy", [])))


def _engine(ctx):
    s = ctx.slink.labctl("state")
    return s.get("engine") or {}, s.get("connection") or {}


def model_use(ctx, model, context=8192, switch=False):
    _, holders = _gpu_holders(ctx)
    if holders:
        raise ToolError("gpu_busy", "another job holds Slink's GPU; Haven never interrupts it. Wait, or ask the owner.",
                        refused=True, detail={"holders": holders})
    engine, conn = _engine(ctx)
    busy = engine.get("state") not in (None, "STOPPED", "FAILED") or conn.get("ownership") == "EXTERNAL"
    replaced = None
    if busy:
        current = engine.get("label") or conn.get("model") or engine.get("state")
        if not switch:
            raise ToolError("engine_busy", f"the Lab is serving {current}; call again with switch=true to replace it",
                            refused=True, detail={"engine": engine.get("state"), "serving": current})
        ctx.slink.labctl("disconnect" if conn.get("ownership") == "EXTERNAL" else "unload")
        replaced = current
    out = ctx.slink.labctl("load", model, "--context", str(context), timeout=60)
    return {"model": model, "context": context, "replaced": replaced, "lab": out,
            "next": "poll haven_lab_job with the job_id until state is not RUNNING" if out.get("job_id") else None}


def model_unload(ctx):
    engine, conn = _engine(ctx)
    if conn.get("ownership") == "EXTERNAL":
        return {"action": "disconnect", "note": "external backend (Strata) left running; its service is the owner's",
                "lab": ctx.slink.labctl("disconnect")}
    if engine.get("state") in (None, "STOPPED"):
        return {"action": "none", "note": "no model was loaded"}
    return {"action": "unload", "lab": ctx.slink.labctl("unload")}


def strata_connect(ctx, confirm):
    if not ctx.allow_strata:
        raise ToolError("strata_disabled", "Strata connect is off; the owner enables it with --allow-strata", refused=True)
    if confirm != STRATA_CONFIRM:
        raise ToolError("confirm_required", f"pass confirm={STRATA_CONFIRM!r}: a cold start takes about 13-15 min "
                        "and holds the GPU", refused=True)
    _, holders = _gpu_holders(ctx)
    if holders:
        raise ToolError("gpu_busy", "another job holds Slink's GPU; Haven never interrupts it", refused=True,
                        detail={"holders": holders})
    out = ctx.slink.labctl("strata", timeout=60)
    return {"lab": out, "expect": "READY in up to 2400 s; poll haven_lab_job, do not retry while it runs"}


def _workspaces():
    p = engineer_config() / "workspaces.json"
    rows = json.loads(p.read_text()) if p.exists() else []
    return {w["name"]: w["path"] for w in rows if isinstance(w, dict) and w.get("name") and w.get("path")}


def _workspace(name):
    ws = _workspaces()
    if name not in ws:
        raise ToolError("unknown_workspace", f"{name!r} is not a registered engineer workspace", refused=True,
                        detail={"registered": sorted(ws)})
    return ws[name]


def _owner_network():
    p = engineer_config() / "scope.json"
    try:
        return bool(json.loads(p.read_text()).get("network")) if p.exists() else False
    except ValueError:
        return False


def job_submit(ctx, command, workspace, node="slink", cpu=1, mem_mib=512, timeout_s=600, network=False):
    import fleet
    import scheduler
    if node == "local" and not ctx.settings.get("allow_local_jobs"):
        raise ToolError("node_disabled", "the controller host ('local', the Mac) takes no jobs while its compute is "
                        "off; use node 'slink'", refused=True)
    if node not in {n["name"] for n in fleet.load()["nodes"]}:
        raise ToolError("unknown_node", f"{node!r} is not an enrolled node", refused=True)
    if network and not _owner_network():
        raise ToolError("network_not_granted", "the owner has not granted network to engineer jobs", refused=True)
    spec = {"command": command, "repo": _workspace(workspace), "node": node, "cpu": cpu, "mem_mib": mem_mib,
            "timeout_s": timeout_s, "network": network}
    sch = scheduler.Scheduler()
    try:
        job = sch.submit(spec, "hermes-" + time.strftime("%Y%m%dT%H%M%S-") + uuid.uuid4().hex[:4])
    except scheduler.SchedError as e:
        raise ToolError("scheduler_refused", str(e), refused=True) from None
    placed = None
    try:  # one placement pass now; `scheduler.py serve` (if running) keeps it moving
        sch.tick()
        placed = sch.store.load(job["id"])["state"]
    except Exception as e:
        placed = f"tick failed: {type(e).__name__}"
    serving = subprocess.run(["pgrep", "-f", "scheduler.py serve"], capture_output=True).returncode == 0
    return {"job_id": job["id"], "scheduler_receipt": job["receipt"], "state": placed, "scheduler_serving": serving,
            "next": "follow with haven_jobs(id)" + ("" if serving else "; no `scheduler.py serve` is running, so "
                                                    "the job advances only when the owner runs a tick or serve")}


def job_cancel(ctx, id):
    import scheduler
    try:
        job = scheduler.Scheduler().cancel(id)
    except (FileNotFoundError, scheduler.SchedError):
        raise ToolError("not_found", f"no scheduler job {id}", refused=True) from None
    return {"job_id": id, "state": job["state"]}


def task_start(ctx, prompt, agent, workspace, mode="engineer", max_steps=30):
    allowed = ctx.settings.get("task_agents") or []
    if agent not in allowed:
        raise ToolError("agent_not_allowed", "the owner has not allowed this agent for Hermes-started tasks "
                        "(task_agents in ~/.config/haven-engineer/hermes.json)", refused=True,
                        detail={"allowed": allowed})
    path = _workspace(workspace)
    tid = time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    logs = engineer_state() / "hermes" / "task-logs"
    logs.mkdir(parents=True, exist_ok=True, mode=0o700)
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT), os.environ.get("PYTHONPATH", "")])}
    with open(logs / f"{tid}.log", "ab") as log:
        p = subprocess.Popen([sys.executable, "-m", "haven_hermes.task_launcher", "--task-id", tid, "--workspace",
                              path, "--agent", agent, "--mode", mode, "--max-steps", str(max_steps)],
                             stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, env=env,
                             start_new_session=True, cwd=str(ROOT))
        p.stdin.write(prompt.encode())
        p.stdin.close()
    return {"task_id": tid, "runner_pid": p.pid, "agent": agent, "mode": mode, "workspace": workspace,
            "next": "follow with haven_tasks / haven_receipts(task_id); the task's risky steps wait in "
                    "haven_approvals for the owner"}


def task_cancel(ctx, task_id):
    d = engineer_state() / "tasks" / task_id
    if not (d / "meta.json").exists():
        raise ToolError("not_found", f"no engineer task {task_id}", refused=True)
    (d / "cancel").touch(mode=0o600)  # the same signal TaskSession.request_cancel() writes
    return {"task_id": task_id, "cancel_requested": True}


def specs():
    return [
        ToolSpec("haven_model_use", "Load a model on Slink's Model Lab (see haven_models for ids). Refused if another "
                 "job holds the GPU. If a model is already served, pass switch=true to replace it. Returns a Lab "
                 "job_id: poll haven_lab_job.",
                 obj({"model": MODEL_ID, "context": {"type": "integer", "minimum": 2048, "maximum": 131072},
                      "switch": {"type": "boolean"}}, ["model"]),
                 model_use, effect="change", rate_per_min=4,
                 summary=lambda a: f"load {a['model']} ctx={a.get('context', 8192)}{' switch' if a.get('switch') else ''}"),
        ToolSpec("haven_model_unload", "Unload the Model Lab's model on Slink (or disconnect an external backend such "
                 "as Strata, leaving its service running). Frees the GPU.", obj({}), model_unload,
                 effect="change", idempotent=True, destructive=True, rate_per_min=4, summary=lambda a: "unload"),
        ToolSpec("haven_strata_connect", f"Connect the Lab to Haven Strata (cold start about 13-15 min; holds the GPU "
                 f"until READY, up to 2400 s). Requires confirm='{STRATA_CONFIRM}'. Poll haven_lab_job; never retry "
                 "while it runs.", obj({"confirm": {"type": "string", "maxLength": 40}}, ["confirm"]),
                 strata_connect, effect="change", rate_per_min=2, summary=lambda a: "strata connect"),
        ToolSpec("haven_job_submit", "Run a shell command as a scheduler job on an enrolled node (CPU only; the GPU "
                 "belongs to the Model Lab). The repository is a registered engineer workspace, cloned to the node; "
                 "the command runs in the node's sandbox.",
                 obj({"command": {"type": "string", "minLength": 1, "maxLength": 2000},
                      "workspace": {"type": "string", "pattern": r"[A-Za-z0-9._-]{1,80}"},
                      "node": {"type": "string", "pattern": r"[a-z0-9-]{1,40}"},
                      "cpu": {"type": "integer", "minimum": 1, "maximum": 16},
                      "mem_mib": {"type": "integer", "minimum": 64, "maximum": 16384},
                      "timeout_s": {"type": "integer", "minimum": 10, "maximum": 7200},
                      "network": {"type": "boolean"}}, ["command", "workspace"]),
                 job_submit, effect="change", rate_per_min=6,
                 summary=lambda a: f"job on {a.get('node', 'slink')} in {a['workspace']}: $ {a['command'][:160]}"),
        ToolSpec("haven_job_cancel", "Cancel a scheduler job by id.", obj({"id": ID}, ["id"]), job_cancel,
                 effect="change", idempotent=True, destructive=True, summary=lambda a: f"cancel job {a['id']}"),
        ToolSpec("haven_task_start", "Start an engineer task: a Haven agent works on a registered workspace with "
                 "sandboxed tools and signed receipts. mode 'observe' only reads; 'engineer' may edit and run "
                 "commands, and asks the owner before push, rm -r or network. Returns a task_id at once.",
                 obj({"prompt": {"type": "string", "minLength": 1, "maxLength": 8000},
                      "agent": {"type": "string", "pattern": r"[A-Za-z0-9._-]{1,60}"},
                      "workspace": {"type": "string", "pattern": r"[A-Za-z0-9._-]{1,80}"},
                      "mode": {"type": "string", "enum": ["observe", "engineer"]},
                      "max_steps": {"type": "integer", "minimum": 1, "maximum": 60}},
                     ["prompt", "agent", "workspace"]),
                 task_start, effect="change", rate_per_min=3,
                 summary=lambda a: f"task {a['agent']} [{a.get('mode', 'engineer')}] in {a['workspace']}: {a['prompt'][:140]}"),
        ToolSpec("haven_task_cancel", "Ask a running engineer task to stop.", obj({"task_id": ID}, ["task_id"]),
                 task_cancel, effect="change", idempotent=True, destructive=True,
                 summary=lambda a: f"cancel task {a['task_id']}"),
    ]
