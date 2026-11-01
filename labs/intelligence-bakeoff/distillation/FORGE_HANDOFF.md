# Haven secpatch forge — handoff for outside review (2026-10-31)

This document lets an outside analyst review the training work without access to Slink. The code is in this repo. Data and models are in a private Hugging Face repo (see Artifacts). Every number below comes from a deterministic grader; no LLM judge is involved.

## What was built
- **secpatch dataset.** Python security fixes from OSV PyPI advisories become six graded tasks: detect, root_cause, finding_support, remediate, regression_test and tool_select. Graders: `secpatch/evaluate.py`.
  - Splits are by repository. The frozen held-out set is 37 fixes and 259 items; the gate set is 115 fixes.
- **Forge loop** (`secpatch/forge/loop.py`, a systemd timer on Slink). Steps run in order: refresh → mix → teach → review_teach → train → gate → promote.
  - Teacher: Qwen3.6-35B-A3B on Kaggle, plus GLM-4.7-Flash on Slink.
  - The teacher writes rationales with the real patch diff in view. Rules v6 reject leakage, history, speculation and ungrounded identifiers (`teach.py`, `handbook.md`). A calibrated critic and a human/Claude review step follow.
- **Training** (`secpatch/forge/kernels/train.py`, free Kaggle 2×T4):
  - QLoRA with loss on answer tokens only.
  - Then a DPO+NLL preference stage on grader-verified self-play pairs.
  - Then merge, restore the MTP head, convert to GGUF Q4_K_M.
  - Then student vs base/champion evaluation, and a gate: cluster bootstrap over fixes, a false-positive-rate guard and a collapse guard.
- **Qwythos-9B-v2 experiments.** The owner accepted the provenance risk of its Claude-distilled base.
  - Secpatch adapter: 16 GB low-VRAM path.
  - Agent-reliability adapter from verified tool-use trajectories: `secpatch/forge/agentgen.py`, using the cyber lab's deterministic tools (PR #105).
- **Ops.** Hourly off-box backup (`secpatch/forge/backup.py`), Model Lab GPU preemption, and the gpu-wanted contract (`local_train.py`).

## Results so far
| Model | Held-out score | Detection recall | FPR | Status |
|---|---|---|---|---|
| Qwen3.5-4B base | 0.502–0.506 | 0.14–0.19 | 0.135 | reference |
| Forge cycle 0 student (4B) | 0.679 | 0.27 | 0.108 | not promoted (FPR guard, old rule) |
| Forge cycle 1 student (4B) | 0.718 | 0.68 | 0.270 | not promoted (FPR guard) |
| Qwythos-9B-v2 stock (Q4_K_M) | 0.486 | — | 0.108 | reference |
| Qwen3.6-35B-A3B / Qwen3.8-27B (zero-shot) | 0.602 / 0.629 | 0.30–0.49 | — | Slink daily model / batch candidate |

The student scores are on the format it was trained for; the zero-shot scores are not. Cycle 1's false-positive rise was traced to preference pairs skewed toward "vulnerable": 86/54 on detect and 85/68 on finding_support. The skew is now balanced in `mix.py` (commit 123fdd1). Per-stage receipts: `forge/cycles/c00N/train/receipt.json` and `gate.json` in the HF repo.

Qwythos adapters: training on Kaggle at the time of writing. The cyber lab will run a pre-registered three-way comparison (base vs agent v1 vs secpatch c001); its provenance and contamination classes are in PR #105 under `labs/cyber/results/compare/2026-10-31/`. Disclosed contamination: parts of the agent data (host, NotActions, CA gap types) were shaped by eval descriptions and fixture builders, so gains on those items count as taught, not generalized.

## Artifacts
- **Code.** This branch: `claude/secpatch-forge-20261029` (PR #95). Cyber lab: `claude/cyber-intel-20261031` (PR #105).
- **Data and models.** Private HF dataset `jankycoder/haven-forge-state`. It mirrors:
  - `forge/`: cycle data, teacher traces and critic files, reviews, receipts, adapters, student GGUFs, benchmarks, loop state and logs;
  - `secpatch/`: harvested datasets and earlier runs.
  - Restore with `hf download jankycoder/haven-forge-state --repo-type dataset --local-dir <dir>`.
- **Kaggle** (account yahboyomni, private):
  - Datasets: `haven-forge-c00N` and `haven-forge-qwythos-*`.
  - Training kernels: `haven-forge-train-c00N`, `-qwythos-c001`, `-qwythos-agent-v1`.
  - Teaching kernels: `haven-forge-teach-c00N`.
- **Benchmarks** (under `forge/bench/` in the HF repo):
  - `relay-20261030/table.json`: Liquid↔35B thought relay. Liquid reasoning hurt; thinking off was the best value.
  - `qwythos-20261031/table.json`: serving matrix. MTP self-speculation gave 1.24–1.36x; a 0.8B drafter gave 0.73x.

## Open problems worth an outside opinion
1. **Recall/FPR trade-off.** Cycle 1 traded much higher recall for triple the FPR. Is pair balancing enough, or should the gate optimize a cost-weighted metric?
2. **Root cause on held-out.** Held-out root_cause stays near base (0.28 vs 0.25) while gate root_cause improved, which suggests memorized phrasing.
3. **CWE accuracy.** When the student detects a vulnerability it often names the wrong CWE (0.20 vs base 0.57).
4. **Two epochs on ~3.8k rows.** Loss falls to ~0.25, which suggests memorization.
5. **Agent data coverage.** The agent data covers only categories with deterministic labels (ca, rbac, host).

## Reproduce
- Tests: `python -m pytest labs/intelligence-bakeoff/distillation/tests`. One test fails on macOS only, from the /private/var path.
- Forge config: `secpatch/forge/config.json`.
- One loop step: `secpatch/forge/loop.py tick`; or use `loop.py status`.
