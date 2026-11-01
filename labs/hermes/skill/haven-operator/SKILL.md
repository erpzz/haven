---
name: haven-operator
description: Operate Haven, the owner's home AI lab (Slink GPU box, Model Lab, engineer fleet), through the haven MCP tools. Use for any question about what Haven is running, its GPU, models, jobs, tasks, receipts or security audit, and for loading or unloading models, running jobs, starting engineer tasks or creating a new Haven tool.
version: 0.1.0
metadata:
  hermes:
    tags: [haven, homelab, gpu, operations]
    category: devops
    requires_toolsets: [mcp-haven]
---

# Operating Haven

Haven's tools come from the `haven` MCP server. Reads (status, GPU, models, jobs, tasks, receipts, Sentinel) never change anything. Changes (model load and unload, jobs, tasks, Strata, tool creation) ask the owner first, and each one returns a signed receipt id.

## Always

1. **Look before acting.** Call `haven_status` first; call `haven_gpu` before any model or Strata change.
2. **One GPU owner at a time.** If a change is refused as `gpu_busy`, tell the owner which unit holds the GPU and stop. Never unload, cancel or kill another job to make room. The Lab refuses on its own too.
3. **Report evidence honestly.** Say whether something was *observed* (a tool just returned it), *prepared* (a job or task was started) or *planned*. A part that reports `unknown` is unknown, not fine.
4. **Cite receipts.** After a change, quote its `R-xxxxxxxxxx` id. Before claiming success, run `haven_check_answer` on your draft reply and fix whatever it flags.
5. **Don't retry long work.** `haven_model_use` and `haven_strata_connect` return a Lab `job_id`; poll `haven_lab_job` until it is no longer RUNNING. A `timeout` status means *unknown*: check state, never repeat blindly. Pass an `idempotency_key` when a retry is genuinely needed.
6. **Approvals belong to the owner.** `haven_approvals` lists what waits in the Haven console. You never decide them, and you never write held-out cases for a tool you proposed.

## Costs to know

- **Strata:** a cold start takes about 13-15 minutes and holds the GPU (READY within 2400 s). Use it only when the owner asks, with `confirm="COLD_START_15MIN"`.
- **Model loads:** a few seconds to about 2 minutes. Prefer the model that is already loaded when it can do the job.
- **Saved results:** Sentinel, benchmarks and audits are read from saved reports. Don't re-run expensive work to answer a question.
- **The Mac:** while its compute is off, jobs go to node `slink`, never `local`.

## Recipes

- **"What's Haven doing?"** `haven_status`, then summarize: the engine (state and model), GPU holders, running units, non-passing Sentinel findings and running tasks.
- **"Load model X":**
  1. `haven_models` to get the exact id.
  2. `haven_gpu` to check the GPU is free.
  3. `haven_model_use(model=X)`; add `switch=true` only if the owner agreed to replace what is loaded.
  4. Poll `haven_lab_job` until it finishes.
  5. Reply with the receipt id.
- **"Free the GPU":** `haven_model_unload` frees only the Lab's own model. If a peer holds the GPU, say so; the owner decides.
- **"Run the tests on Slink":** `haven_job_submit(command="python3 -m unittest discover -s tests", workspace=<registered name>)`, then follow with `haven_jobs(id=...)`.
- **"Have an agent fix X":** `haven_task_start(prompt, agent, workspace, mode="engineer")`, then follow with `haven_tasks` and `haven_receipts(task_id=...)`. The task's risky steps wait in `haven_approvals` for the owner.
- **"Make a tool that does X":**
  1. Write a stdlib Python script. It reads its JSON arguments from `sys.argv[1]` and prints one JSON object as its last stdout line.
  2. Call `haven_tool_propose` with 2-5 dev cases (`args` and the object the result must contain).
  3. Iterate until every dev case passes, then call `haven_tool_request_admission` and give the owner its steps.
  4. After the owner admits it, the tool appears as `skill_<name>`; `haven_tools` lists it.
