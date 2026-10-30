#!/usr/bin/env python3
"""Engineering benchmark: real bug-fix tasks in disposable repos, judged independently.

Each run copies a task repo into a fresh git workspace, runs one agent with a
fixed step budget, and then the harness (never the agent) decides the outcome:
  * protected test files are byte-identical to the fixture,
  * the task's own verifier passes (real pytest from a private venv, node --test,
    or unittest) on the final working tree,
  * a commit beyond the fixture exists (reported separately).

Arms for the inheritance experiment (morphogenesis/README.md):
  none    tools only
  recipe  the admitted skill's recipe.md in the system prompt (same knowledge, prose)
  skill   the admitted skill offered as an executable tool
  controller  E2: the runtime runs the skill before the first turn and after every edit (model patches only)
  guard   tools only + premature-finish guard (a final answer before any edit or command goes back once)
  both    controller + guard

  run_bench.py --agents qwen35-4b-mac --arms none,recipe,skill --tasks t1,t2,t3,t4 --out results.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import runtime  # noqa: E402

TASKS = HERE / "tasks"
VERIFY_PY = pathlib.Path.home() / ".local/share/haven-engineer-bench/venv/bin/python"
VERIFY = {
    "pytest-style": [str(VERIFY_PY), "-m", "pytest", "-q", "-p", "no:cacheprovider"],
    "node-test": ["node", "--test"],
    "unittest": None,  # chosen per layout below
}


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def git(cwd, *argv):
    env = {**{k: os.environ[k] for k in ("PATH", "HOME") if k in os.environ},
           "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@haven.invalid",
           "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@haven.invalid"}
    return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", *argv], cwd=cwd, env=env,
                          capture_output=True, text=True)


def verify(repo, spec):
    fw = spec["framework"]
    if fw == "unittest":
        if (repo / "tests").is_dir():
            argv = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."]
        else:
            argv = [sys.executable, "-m", "unittest"]
    else:
        argv = VERIFY[fw]
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
    if (repo / "src").is_dir():
        env["PYTHONPATH"] = str(repo / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run(argv, cwd=repo, capture_output=True, text=True, timeout=120, env=env)
    return r.returncode == 0, (r.stdout + r.stderr)[-600:]


def discovery_waste(receipts):
    """Failed run_command attempts before the first command that actually ran tests (exit 0 or 1 with results)."""
    waste = 0
    for r in receipts:
        if r["tool"].startswith("skill_"):
            return waste
        if r["tool"] != "run_command":
            continue
        code = r.get("exit_code")
        if code in (126, 127) or (code not in (0, None) and "pytest" in r.get("summary", "")):
            waste += 1
            continue
        return waste
    return waste


def run_one(agent_id, arm, task, *, max_steps, temperature, skill="run_tests", seed=None):
    spec = json.loads((TASKS / task / "task.json").read_text())
    src = TASKS / task / "repo"
    root = pathlib.Path(tempfile.mkdtemp(prefix=f"bench-{task}-", dir=pathlib.Path.home() / ".local/share/haven-workspaces"))
    repo = root / task
    shutil.copytree(src, repo)
    git(repo, "init", "-q", "-b", "work")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "fixture")
    base = git(repo, "rev-parse", "HEAD").stdout.strip()
    protected = {p: sha(src / p) for p in spec["protected"]}
    agent = runtime.agent_by_id(agent_id)
    t0 = time.monotonic()
    rec = runtime.run_task(repo, agent, "engineer", spec["prompt"], max_steps=max_steps,
                           overrides={"temperature": temperature, "seed": seed,
                                      "finish_guard": arm in ("guard", "both"),
                                      "exhaust_recovery": arm in ("recover", "controller_recover")},
                           skill_names=[skill] if arm == "skill" else None,
                           recipe_names=[skill] if arm == "recipe" else None,
                           auto_tests=skill if arm in ("controller", "both", "controller_recover") else None,
                           extra_meta={"bench": {"task": task, "arm": arm, "seed": seed}})
    wall = time.monotonic() - t0
    tests_unchanged = all((repo / p).exists() and sha(repo / p) == h for p, h in protected.items())
    passed, tail = verify(repo, spec)
    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    committed = head != base and not git(repo, "diff", "--quiet", base, head).returncode == 0
    clean = git(repo, "status", "--porcelain").stdout.strip() == ""
    receipts = rec.get("receipts", [])
    row = {
        "task": task, "agent": agent_id, "arm": arm, "seed": seed, "temperature": temperature,
        "task_id": rec.get("task_id"),
        "success": bool(passed and tests_unchanged), "tests_pass": passed, "tests_unchanged": tests_unchanged,
        "committed": committed, "clean_tree": clean, "agent_status": rec.get("status"),
        "answer_check_ok": (rec.get("answer_check") or {}).get("ok"),
        "steps": rec.get("steps"), "tool_calls": rec.get("tool_calls"), "invalid_calls": rec.get("invalid_calls"),
        "failed_actions": sum(1 for r in receipts if r["status"] == "failed"),
        "discovery_waste": discovery_waste(receipts),
        "skill_calls": sum(1 for r in receipts if r["tool"].startswith("skill_")),
        "auto_test_runs": rec.get("auto_test_runs", 0),
        "wall_s": round(wall, 1), "model_s": rec.get("model_s"), "tool_s": rec.get("tool_s"),
        "prompt_tokens": rec.get("prompt_tokens"), "completion_tokens": rec.get("completion_tokens"),
        "nudges": rec.get("nudges"), "exhausted_turns": rec.get("exhausted_turns", 0),
        "exhaust_followups": rec.get("exhaust_followups", 0), "exhaust_recovered": rec.get("exhaust_recovered", 0),
        "verifier_tail": "" if passed else tail[-300:],
    }
    shutil.rmtree(root, ignore_errors=True)
    return row


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agents", required=True)
    ap.add_argument("--arms", default="none,recipe,skill")
    ap.add_argument("--tasks", default="t1-inventory-pytest-src,t2-durations-node,t3-ledger-unittest-src,t4-config-unittest-error")
    ap.add_argument("--max-steps", type=int, default=20)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--seeds", default="", help="comma-separated sampling seeds (one run per seed)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    out = pathlib.Path(args.out)
    done = set()
    if out.exists():
        for line in out.read_text().splitlines():
            r = json.loads(line)
            done.add((r["agent"], r["arm"], r["task"], r.get("seed")))
    seeds = [int(x) for x in args.seeds.split(",") if x] or [None]
    for agent in args.agents.split(","):
        for seed in seeds:
            for task in args.tasks.split(","):
                for arm in args.arms.split(","):
                    if (agent, arm, task, seed) in done:
                        continue
                    print(f"{agent} {arm} {task} seed={seed} …", flush=True)
                    row = run_one(agent, arm, task, max_steps=args.max_steps, temperature=args.temperature, seed=seed)
                    with open(out, "a") as f:
                        f.write(json.dumps(row) + "\n")
                    print(f"  success={row['success']} steps={row['steps']} waste={row['discovery_waste']} "
                          f"wall={row['wall_s']}s skill_calls={row['skill_calls']} nudges={row['nudges']}", flush=True)


if __name__ == "__main__":
    main()
