"""Detached runner for one engineer task started by Hermes (haven_task_start). The prompt arrives on stdin.

  python3 -m haven_hermes.task_launcher --task-id ID --workspace DIR --agent AGENT --mode engineer

Same path as `labs/engineer/cli.py run`, except the task id is chosen by the caller (so Hermes can follow
and cancel it) and there is no terminal: every "ask" decision waits in the Haven console for the owner.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

from . import ENGINEER  # noqa: F401  (puts labs/engineer on sys.path)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--agent", required=True)
    ap.add_argument("--mode", choices=("observe", "engineer"), required=True)
    ap.add_argument("--max-steps", type=int, default=30)
    a = ap.parse_args(argv)
    import runtime
    from session import TaskSession
    prompt = sys.stdin.read()
    agent = runtime.agent_by_id(a.agent)
    network = bool(runtime.owner_scope().get("network"))
    sess = TaskSession(tid=a.task_id, agent=agent["id"], agent_kind=agent.get("kind", "local"),
                       workspace=os.path.realpath(a.workspace), workspace_name=pathlib.Path(a.workspace).name,
                       mode=a.mode, network=network, inference_host=agent.get("inference_host"),
                       tool_host=agent.get("tool_host") or os.uname().nodename.split(".")[0],
                       egress=agent.get("egress", "LOCAL"), prompt=prompt, max_steps=a.max_steps, depth=0,
                       parent_id=None, runner_pid=os.getpid(), launched_by="hermes")
    runtime.run_task(a.workspace, agent, a.mode, prompt, session=sess, network=network, max_steps=a.max_steps)


if __name__ == "__main__":
    main()
