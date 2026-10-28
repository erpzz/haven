# M1: real engineering tasks, local Qwen 4B / 9B / 35B-A3B vs hosted agents. DRAFT, not frozen

Status: **draft, 2026-10-27.** No M1 run has been made. The plan is frozen by a commit that adds
`PREREGISTRATION_M1.json` with the validated task list and the analysis code. Nothing below counts until then.

## Question

On real Haven engineering tasks judged by hidden tests, how do these compare?

- Qwen3.5-4B, Qwen3.5-9B and Qwen3.6-35B-A3B in Haven's own loop (`loop.py`, Slink GPU)
- hosted agents: Claude Code (Opus) and Codex, through Haven's MCP tools (`mcp_server.py`, the same executor and receipts)

The measures are success, elapsed time, prompt processing, executor actions, tool reliability, memory and actual usage.

## Tasks: replayed real fixes, chosen mechanically

- **Pool:** non-merge commits on `main` from 2026-10-20 onward that change both source (`.py`/`.js`) and tests, with at most 3 source files and at most 80 changed source lines. Merge commits, bench fixtures and results-only commits are excluded. On 2026-10-27, 25 commits pass a looser filter (≤ 3 source files, ≤ 8 files); the line limit and validation are not yet applied.
- **Validity, checked by `bench/select_m1.py` (to be written and committed before the freeze):** in a clean copy at the parent commit with the fix commit's test files applied, the new or changed tests **fail**. At the fix commit they **pass**. The pre-existing suite passes at both. The task must run offline in the Landlock sandbox with no GPU and no live service.
- **Selection:** the first 12 valid commits in date order. If fewer than 8 are valid, M1 is not run and the pool is widened by a recorded amendment.
- **Prompt, generated rather than written:** the repository at the parent commit, plus the failing test names and assertion messages produced at the parent. The test files themselves are withheld.
- **Judge:** after the agent finishes, a grader that sees only the final tree (not the transcript or the model's identity) does three things:
  1. applies the fix commit's test files
  2. runs them plus the pre-existing suite
  3. checks that protected tests are byte-identical

  Success requires all three. The grader is `bench/run_bench.py verify`, run by the harness, so no model grades another.

## Arms and fair budgets

| Arm | Where | Budget per task |
|---|---|---|
| qwen35-4b | Slink GPU, Lab-owned llama.cpp, catalog profile | 30 model steps, 1,800 s wall, 4,096 completion tokens per turn |
| qwen35-9b | same | same |
| qwen36-35b-a3b | same, experts in RAM | same |
| claude-code-opus | Mac, Claude Code on the owner's plan, Haven MCP tools only | 30 tool calls, 1,800 s wall |
| codex | Mac, Codex CLI on the owner's plan, Haven MCP tools only | 30 tool calls, 1,800 s wall |

- Seeds: 3 per local arm (sampling only). Hosted arms run once per task because of plan quotas, and that is reported as a threat.
- One local model is loaded at a time. Arms are interleaved by task within each loaded model.
- Hosted runs may overlap local runs only on different hosts. They always run on the Mac, so they never compete for Slink.

## Measures (per run, from receipts)

- **success:** the judge above
- **elapsed:** task wall seconds
- **prompt processing:** llama.cpp `timings.prompt_n` / `prompt_ms` summed per run. Not available for hosted arms; reported as n/a.
- **decode:** `predicted_n` / `predicted_ms`
- **executor actions:** ledger lines per run
- **tool reliability:** invalid or failed tool calls ÷ all tool calls
- **memory:** peak llama-server RSS and GPU MiB, sampled every 2 s; local arms only
- **usage:**
  - local: GPU-seconds and Wh from `nvidia-smi` power samples
  - hosted: turns, input and output tokens where the CLI reports them, and the plan-usage percentage before and after the arm
  - $0 paid usage is a hard rule; a run that would incur overage is not started

## Analysis

- **Primary:** success rate per arm with exact 95% binomial intervals. For local models, pairwise exact sign tests on paired (task, seed) units, with the same thresholds as E2 (supported if p < 0.05 and wins − losses ≥ 4; rejected if losses ≥ wins).
- **Hosted vs local:** descriptive only, because n is 1 per task and the harness differs.
- **Secondary, descriptive:** medians of elapsed, prompt-processing seconds, actions and tool reliability per arm. Peak memory per local model.

## Known threats

- Opus wrote many of the fix commits. A hosted Opus arm may recognise its own code style. Hosted models may also have seen the public repo, although every task postdates their training data.
- Hosted agents use their own planning loop, not `loop.py`, so this compares whole agents, not models.
- llama.cpp is not bit-exact. E2 measured 3 of 24 discordant pairs between identical treatments.

## Gates before any run

1. Runtime ownership is confirmed. Today an idle 35B-A3B engine started at 20:17 UTC by an unconfirmed owner holds the Lab, and Strata is stopped.
2. The owner OKs the GPU time, roughly 12 tasks × 3 seeds × 3 models.
3. `prompt_ms` and peak-memory capture are added to the bench rows and tested. That is the only harness change before the freeze.
4. `select_m1.py` and `summarize_m1.py` are committed together with `PREREGISTRATION_M1.json`.
