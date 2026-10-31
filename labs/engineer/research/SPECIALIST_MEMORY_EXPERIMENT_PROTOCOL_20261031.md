# H02/R02 preregistration — capability cascade + evidence-grounded memory

**Status: PROPOSED, NOT EXECUTED.** Owner and independent reviewer approval required before any live hardware/agent/training run.  
**Date:** 2026-10-31. **Base evidence:** Haven main 53387e74a0ad90786ac3ea16753c8ad99142e9df.  
**Research rationale:** [architecture note](SMALL_SPECIALISTS_ROUTING_MEMORY_ARCHITECTURE_20261031.md).  
**Existing executor:** [Haven Engineer](../README.md). This protocol proposes evidence collection and comparison; it does not grant autonomous permissions.

## Single question to answer first

**Can one ready small model, given verified skills and evidence-grounded retrieval plus conservative escalation, outperform the same model without those mechanisms on previously unseen real engineering tasks, without increasing false claims of success or using more resources per successfully verified task?**

This is a system-level hypothesis, *not* a claim that a new small model is intrinsically smarter. The first test must use the **same model and runtime** across arms, separating benefits from memory/tool structure rather than changing everything at once. Training an adapter is intentionally deferred until these results are known.

## Experiment C1: fixed-small baseline vs procedural/memory cascade

### Population, data and isolation

Construct a corpus of 120 owner-authorized, licensing-reviewed, bounded tasks with real runnable postconditions, using multiple open-source repositories or isolated Haven worktrees. The number 120 is a proposed collection target, not currently available cases.

- 40 repository bug-repair/verification tasks with reproducible failing and passing tests.
- 25 tool schema/use tasks including tool refusal, malformed arguments and nested tool outcomes.
- 25 *temporal* tasks where an earlier observation becomes stale or is superseded, and the agent must cite the current source correctly.
- 20 security-fix comprehension/patch tasks from permissively admissible sources with verified provenance and nested license checks. No unsanctioned scanning/exploitation.
- 10 resource-management planning tasks based on recorded, sanitized telemetry; proposals only, never real power/firmware/service writes.

Group by parent repository, advisory/issue family, copied solution, benchmark source and date; group-split them to prevent leakage. Reserve a chronologically later, repo-isolated test split that is never visible to a model trainer, skill author or prompt tuner. A proposed allocation is 60 train/dev, 20 calibration, 40 locked final test, retaining balanced task-family coverage; report any failures to meet this rather than quietly mixing groups. Store hashes, provenance, permissible licenses and holdout assignments privately. No data from the locked test can enter memory/skill admission, model prompts, router calibration, or hyperparameter tuning.

Have an independent reviewer prove each task passes under the known-good fix and fails under the empty/known-bad fix. Document contradictory or ungradable tasks and remove them **before** freezing final labels.

### Arms (paired with the same model and equivalent permissions)

| Arm | Description | Purpose |
| --- | --- | --- |
| A0 | Qwen3.5-4B, current Haven tool loop, no carried episodic memory, existing basic executor and normal tools | Reference |
| A1 | Same A0 + deterministic execution of one preregistered, independently admitted skill where applicable | Procedural-memory effect |
| A2 | Same A0 + compact source-linked ephemeral/episodic retrieval; no learned memory controller | Retrieval effect |
| A3 | A1 + A2 with one deterministic conservative escalation policy; escalation output and cost measured separately | Combined system |
| A4 | Same as A3 but with routed small decision model where its measured CPU/GPU overhead is accounted for | Optional, only if calibration and time permit |

In the first cycle use **one ready resident 4B model** to avoid confounding with GPU contention. If an escalation to a stronger model cannot be afforded or is not owner-authorized, record abstention instead of secretly spending. Disable hosted fallbacks by default. Do not use any model's own self-reported confidence as proof of correctness.

Task ordering randomized within isolated worktrees, with three pre-registered generation seeds where the runtime supports them. Run as paired comparisons; identical task budgets and model context caps. Cap each task at 20 minutes, at most 20 model turns and 50 tool calls, or stricter pre-existing Haven budgets (do not widen production permissions for the experiment). A cancellable/interruptible run must preserve an interruption receipt and must not reclassify it as success.

### Pre-registered metrics

Primary:
- **Verified task success:** an independently re-run expected postcondition on a pristine test environment, not the model's answer or an in-session lexical grader. Include negative/no-op controls.
- **False success:** claimed pass when independent grader fails; must not worsen versus A0 (any privacy boundary breach, unauthorized write, leaked credential or unapproved hosted egress is an immediate veto).

Secondary:
- Total wall time to verified outcome and p50/p95, including routing/retrieval/skill/load/prefill/generation/tools/verification/retry.
- GPU and host memory peak, warm/cold model residency and reload count; token throughput only as diagnostic.
- Tokens in/out, tool calls, extra retry/escalation rate, uncompleted and abstained fraction.
- Energy in **measured joules**, separately by host where trustworthy power sensors exist; otherwise UNKNOWN, never estimated as measured. Cost in dollars including hosted tokens/egress with a default hard $0 budget.
- Privacy/authorization outcomes, cited-evidence accuracy, stale-memory and refusal correctness.

Report paired per-task differences and uncertainty intervals; do not bury harmed task families in one aggregate mean. For an initial 40-case locked split, call results **pilot evidence**, never production qualification. Expansion and formal promotion require fresh held-out repositories/cases with predeclared statistical power.

### Promotion gate

Do not promote any new memory/tool/router to the live Haven route unless a fresh, independently graded evaluation shows (a) no authorization/privacy regression; (b) no increase in false-success rate; (c) verified success is non-inferior to the ready 4B baseline within a predeclared margin, with confidence bounds appropriate to sample size; and (d) end-to-end latency, energy, or successfully completed tasks per hour improves materially. A proposed practical target is at least **15% median end-to-end wall-time improvement at unchanged verified task quality**; it is a *goal to test*, not a guaranteed result. Any statistical ambiguity returns NOT QUALIFIED, not a pass.

## Experiment M1: what counts as real memory?

Run a separate paired set of multi-session tasks, built from tasks with **dated changes** rather than static fact recall. The same model/permissions, no training.

| Memory arm | Mechanism |
| --- | --- |
| M0 | Fresh session with only current task |
| M1 | Whole available transcript within the same fixed context budget |
| M2 | Deterministic compact summary plus explicit pointers to original receipts |
| M3 | SQLite FTS/BM25 source-linked retrieval; bounded token/context |
| M4 | Typed episodic + temporal graph memory (Hindsight-like system *or* a small local implementation), external records only |
| M5 | M4 + hash-addressed, separately admitted executable procedures |

Do **not** silently treat an open-source memory framework as a free, production-qualified dependency; it may need PostgreSQL, embedding or extraction models, and licensing/security review.

Every test must cover both recall and correction:
1. Correctly carry forward the known-good prior fix into a new session.
2. Notice when an earlier observation is now false or belongs to another branch.
3. Cite original source/receipt rather than a compressed second-hand summary.
4. Separate a model hypothesis from an independently observed outcome.
5. Reject retrieval from another principal's private workspace.
6. Abstain when conflicting records lack independent resolution.

Track temporal precision, provenance coverage, contradiction/correction rate, wrong-principal reads, task success, token load, retrieval time and memory growth. If M3 matches M4/M5, keep M3. If structured memory benefits only static factual questions, do not promote it as an autonomous learning improvement.

Suggested immutable event fields: event_id, timestamp, principal, scope, repository+commit, evidence ref+hash, epistemic type, validity interval, supersedes, retention class, and verification status. Derived summaries may be regenerated; the raw receipt is the source of truth. Tool and model prompts are not authority to modify access controls.

## Experiment S1: one domain LoRA, only if C1 justifies training

Predeclare *one* failure cluster from C1 (for example malformed tool arguments or security provenance omissions), with a frozen verifier and baseline. Train only if collected training cases are legally admissible, independent of test cases, and contain enough examples of correct and incorrect decisions to teach something beyond a simple script.

Compare:
- B0: unchanged 4B, original prompt/tooling;
- B1: same 4B + explicit deterministic recipe;
- B2: same 4B + verified retrieval/executable skill;
- B3: same 4B + SFT/QLoRA adapter trained from a rule/oracle trace source;
- B4: same 4B + adapter trained from stronger-model traces **after** independently verifying those traces;
- B5: optional combination B2 + best adapter.

All arms use the same tool interface and evaluation. The previous 0.6B SFT experiment tied the rule/oracle training arm, so B3 is an indispensable control; don't ascribe a win to teacher reasoning without testing that claim. Also measure unrelated-task regressions to detect catastrophic forgetting and capability displacement.

Before GPU allocation, specify: source/license manifest, repository-level split, base checkpoint + tokenizer revision/hash, adapter rank/target layers, trainable parameter count, optimizer, samples/tokens, batch/accumulation, seed(s), training GPU+time budget, and promotion/rejection criteria. Candidate adapters remain unpromoted until independent validation. An 8 GiB GPU **may or may not** fit the chosen model/training configuration; check actual free VRAM and allow LoRA on a smaller backbone rather than evicting a live job.

## Experiment R1: routing only when alternatives are proven useful

Once B0/B1/B2/B3 results establish genuinely different costs and abilities, fit and calibrate a router using **real action labels** (“which execution policy would have succeeded for this task, within budget?”). PR-title path classification is not an adequate target.

Baseline routes:
- R0 all tasks to ready 4B;
- R1 fixed rules / exact skill trigger + abstention;
- R2 gated adaptive retry on independently verified failure;
- R3 learned lightweight router + same fail-safe verification;
- R4 full oracle route computed *retrospectively* on observed outcomes (upper bound; never deploy as prediction).

Report confusion by task family, calibration, acceptance/abstention curves, paired full-task quality, p95 including route overhead, throughput per loaded GPU, and misroute cost. Split chronologically and by repo. Preserve an “UNKNOWN/ABSTAIN” route. Any result worse than rules goes back to research, as in Haven's 6/8 vs 7/8 routing pilot.

## Experiment H1: hardware awareness only after software effect

**Read-only** telemetry first: NVML, CPU pressure, memory availability, user-level process ownership, cache miss/load time. Compare a static placement rule to a deterministic measured-resource-aware scheduler, then an AI planner that can only suggest choices to the independent controller. Keep each run on a bounded owner-approved resource quota and preserve the existing GPU lease. No root, fan/thermal/firmware control or unsolicited interruption of the Lab.

Count completed verified tasks/hour and per joule; if energy measurement absent say UNKNOWN. During training runs, record GPU-hours and carbon/energy estimates separately if used; never confuse a modeled estimate with a sensor measurement. A smarter controller that spends 100ms routing to save 20ms inference is a regression.

## Experiment N1: neural memory research gate (conditional, not ready)

Only after M1 demonstrates failures of simple retrieval and real need for persistent internal state, compare a paper-faithful small recurrent/memory architecture against a size- and FLOP-matched Transformer or Gated DeltaNet, on:
- delayed state tracking,
- contradictory event sequences,
- long-distance retrieval with exact answers,
- learning and retaining updated associations,
- forgetting/overwriting behavior,
- inference throughput and resident state memory.

Do **not** claim that an external PostgreSQL store is equivalent to Titans, Hope, or a recurrent state-space network. Do not retrofit test-time weight updates into Qwythos GGUF without a dedicated training/inference design. Start at sub-billion scale and freeze the task/data splits and evaluation cost before running a GPU.

## Implementation without wholesale rewrites

Use existing Haven components:
- Existing runner: ../runtime.py; executor: ../executor.py; MCP: ../mcp_server.py; policies: ../policy.py; ledger: ../ledger.py.
- Existing evaluators: ../morphogenesis/README.md, ../router_lab/README.md, ../../intelligence-bakeoff/distillation/tool_sft/RESULTS.md.
- Existing model/worker gateway: ../../model-lab/gateway.py and ../../model-lab/providers.py.
- External framework candidates: RouteLLM for calibrated learned routers; llama.cpp (pinned build) and vLLM for conditional adapter serving; Hindsight/Mem0 for optional memory controls, after privacy/compatibility assessment.
- Keep data and individual user/host telemetry private under the existing Haven state directory. The public repository stores only source-level protocols, sanitized aggregate outcomes, and non-identifying checksums.

**No new production model scheduler, model installation, or web endpoint is authorized by this document.** Future implementation should land behind off-by-default research flags in an isolated worktree and a separately reviewed PR; do not auto-merge experimental routing or memory.

## What to hand back after each experiment

1. Exact base commit, hardware model (sanitized), runtime/weights hashes, task manifest+split hashes, and license admissibility results.
2. Execution authorization scope and real resource ownership; provenance of each human approval.
3. Per-arm results including failures, stop reasons, independently reproduced postconditions, p95 and full request/task time, money and energy measurement status.
4. Reproduction command or harness spec; static fixture and real execution are clearly labeled.
5. Statistical uncertainty, negative controls, leakage review and prereg deviations.
6. Single recommendation: KEEP AS BASELINE / RESEARCH ONLY / PROMOTION CANDIDATE / REJECT, with rollback.
