# ChatGPT-distilled Haven operator rows (v1)

**Teacher.** The owner's ChatGPT plan, through the Codex CLI in chat mode (`eval/teacher.py`):
- model `gpt-6.1-terra`, `model_reasoning_effort=high`
- every tool, command and web feature disabled, so the teacher only wrote text
- tool calls requested through a schema-enforced JSON reply, then converted to native OpenAI `tool_calls` messages

Run 2026-10-31 23:46 to 2026-11-01 (EDT).

**Prompts.** The 42 prompts in `eval/distill_v1.json`:
- disjoint from the evaluation set (`eval/build_distill.py` asserts it)
- each run against a simulated Slink and a private temporary engineer state, through the real `haven` tool surface (operate mode, Strata allowed)

**Verification.** Each trajectory is graded with the evaluation's deterministic rules (`eval/harness.py::grade`). Only passing trajectories are exported. All 42 passed after one fix to the simulator, below.

**Rerun (recorded, not hidden).** In the first pass 33 of 42 passed.
- **8 load/switch failures were the simulator's fault.** Its Model Lab catalog listed only `qwen35-4b`, and the teacher correctly refused to load unlisted models. The simulator now serves the real catalog ids.
- **1 failure was a prompt that really did ask for Strata.** It was reworded.
- Only those 9 were rerun, and all 9 passed.

**Export hygiene:**
- temporary paths are rewritten to real-install paths (`normalize_paths`)
- no row contains the evaluation canary or any evaluation prompt
- no evaluation answers are used

**Files:**
- `train_rows.jsonl`: 42 rows of `{messages, tools, meta}`, averaging 3.3 tool calls each
- `results.jsonl`: per-prompt grades
- `summary.json`: run summary
