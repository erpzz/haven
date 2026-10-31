# Haven E6 proposal: small specialists, evidence memory, and routing

**Date:** 2026-10-31  
**Status:** PROPOSED/NOT EXECUTED — no live GPU or trained model qualification by this note  
**Base:** main 53387e74a0ad90786ac3ea16753c8ad99142e9df  
**Companion:** [Architecture research](SMALL_SPECIALIST_MEMORY_ARCHITECTURE_20261031.md)

## Question and preregistration

**H0 (null):** At equal allowed hardware, identical task sets and tool permissions, the current 4B + Engineer baseline is as efficient as a small-specialist / memory / routing system after accounting for retries, cold starts and verification.

**H1a:** Verified executable skills increase independently verified task completion per wall minute without increasing task error.
**H1b:** Temporal, source-grounded retrieval reduces stale-fact errors and resume failures, yielding more verified successes than a context-budget-matched replay/summarization baseline.
**H1c:** A narrow 0.8B–2B trained specialist (or same-base LoRA) achieves a better efficiency/quality point in a named domain than its untrained base, *and* beats the base with only a verified skill and/or retrieved example.
**H1d:** A learned router improves the quality/cost Pareto frontier versus the eligible deterministic rule baseline; otherwise prefer rules.
**H1e (later):** Tiny neural test-time memory wins on temporal state and forgetting tasks at matched parameters/compute over a strong external-memory baseline.

These are separate hypotheses. Rejecting one does not invalidate the others. Do not retroactively redefine endpoints after looking at the final heldout results.

## Required evidence labels

- **STATIC_TEST:** fake servers, schema and security checks; not trained-model performance.
- **OBSERVED_MODEL_RUN:** real weights and backend, recorded model digest, model-generated tool calls.
- **OBSERVED_TOOL_EXECUTION:** actual executor receipt and independent task-artifact verification; a claimed success is not sufficient.
- **TRAINED_MODEL_RUN:** gradient updates and optimizer steps confirmed, checkpoint hash + training/eval provenance.
- **QUALIFIED:** preregistered heldout threshold and all gates met by independent verifier.
- **UNKNOWN/REFUSED:** absent source or measurement; never silently treated as zero, pass or fallback.

## Dataset and task sampling

**Pilot:** 8–12 tasks **only to debug** fixtures and discover failure types (not a publication-quality effect size). No promotion based on pilot.

**Confirmation:** aim for at least 30–60 **independent** real-task units from distinct repositories or isolated task families; 3 seeds/repetitions for stochastic arms where practical. Use paired tasks so every arm faces identical inputs. Account for correlation across tasks from one repository rather than treating repeats as independent. Expand only before viewing final holdout scores.

**Task families:**
1. *Engineering:* real code inspection, single-bug fix, test-run/receipt and commit in disposable cloned worktrees. Success requires independent tests, correct diff scope and no ignored failure.
2. *Security engineering:* authorized, permissively licensed vulnerable versions + independently validated fixes. No live-host attacks, exploit deployment or missing attribution; exact affected-file license required.
3. *Tool correctness:* schema-valid calls, refusals, error propagation, no invented receipt IDs, timeouts, cancellation.
4. *Temporal memory:* earlier success overturned by newer failed test, renamed API, changing owner-approved constraint, stale benchmark, contradictory claims; answer must name current evidence or abstain.
5. *Hardware planning:* resource telemetry **read-only**, propose an eligible route under RAM/VRAM/lease/budget constraints; no privileged writes or service restarts.
6. *Out of distribution:* repo/version changes, unseen tool schemas, tasks outside known specialty; correct abstention/escalation and preserved baseline quality.

**Splitting:** group by repository and underlying fix/advisory; if one solution spawns 10 near-duplicate test cases, all belong to one split. Hold out later-dated tasks and different repos. Deduplicate patch overlap/teacher traces. Freeze task files, evaluation scripts and reward versions before training; hide held-out task descriptions/expected outputs from the learner. Do not train on cloned test fixtures.

**Source safety:** the repository is public. Store only synthetic IDs, task-level aggregate results, non-sensitive citations and hashes. Real user prompts, credentials, machine IPs and tool raw state remain in private receipts.

## Controlled arms

| Arm | Same model? | Memory? | Training? | Router? | Why |
|---|---|---|---|---|---|
| A0 | 4B existing | No added memory | None | Fixed | Canonical current baseline |
| A1 | 4B existing | Verified skill only | None | Fixed | Is procedural inheritance enough? |
| A2 | 4B existing | Evidence-temporal retrieval | None | Fixed | Does external memory help? |
| A3 | 4B existing | Skill + episodic retrieval | None | Fixed | Interaction / complementarity |
| A4 | 0.8B or 2B | No | None | Fixed | Small base task performance |
| A5 | same as A4 | No | narrow LoRA/SFT | Fixed | Value from weight updates alone |
| A6 | same as A4 | Verified skill + memory | None | Fixed | Strong cheap non-training comparison |
| A7 | resident qualified models/skills | matched memory | existing weights | deterministic | Eligible heuristic cascade |
| A8 | exactly same candidate pool | matched memory | router trained only on train split | learned | Does learning beat the heuristic? |
| A9 | same candidate pool | matched memory | no | retrospective oracle | Unattainable upper bound, not deployable |

Do not compare 2B+LoRA with 4B+memory and attribute the difference to LoRA; identify which variables changed. For adapter experiment use A4/A5/A6 with **same base revision**, quant level, tokenizer, context and tool schemas. If sufficient infrastructure, evaluate per-request adapter routing versus per-token routing separately; do not mix with sequence-level inference and call it one treatment.

Do not run every arm on a busy shared GPU at once. Build sequential, resource-controlled comparisons or establish measured isolation and log competing load.

## Measurable endpoints

**Primary:** verified end-to-end task success, conditioned on exact scope and independent verifier. Report numerator and denominator by family, not only overall percentage.

**Efficiency:** successful tasks per wall hour; incremental successful tasks per measured kWh where available; time-to-first-token, p50/p95 end-to-end task time; cumulative prompt/decode tokens; total tool calls, retries, cancellations, timeouts; model load and adapter activation time; peak RAM/VRAM; paid dollars and provider-hard-cap status.

**Trust/quality:** inappropriate tool calls, forged or ungrounded receipt citations, approval bypass attempts, escalation misses, stale-memory citations, abstention precision/coverage, OOD regression, adapter interference and forgetting.

**Router:** per-family decision confusion matrix; eligible versus ineligible routes; normalized regret against oracle retrospectively; escalation rate; budget refusal correctness; expected and actual completion; cold-start-adjusted latency and energy.

**Memory:** stale and contradicted fact precision, temporal update and selective forgetting correctness, citation validity, source/provenance coverage, contamination rate, retrieval bytes/tokens, evidence contradiction handling.

**Energy:** collect GPU-board Watts and CPU/system Watts only through available documented probes. Convert measured power samples over time to Wh, subtract preregistered idle baseline if consistent; if whole-host energy is unobservable label GPU-only or UNKNOWN. Do **not** infer wall power from TDP or label missing sensor data zero.

**Quality floor (proposal to owner):** no loss of independently verified success or security constraints relative to A0/A7 on high-risk families. Favor Pareto improvements; do not force a single arbitrary universal score. Require confidence intervals or repeated cross-task wins, not one lucky prompt.

## Actual evaluation procedure

1. Verify hardware and model identity; record binary/version/quantization, checkpoint SHA-256, context and GPU-holder state. Exit rather than take a busy GPU lease.
2. Freeze task sampling, instructions, independent tests, reward/grader versions and train/eval partitions. Publish only non-sensitive hashes.
3. Dry-run harness with fake servers; record STATIC_TEST separately.
4. Run A0-A3 with identical resident model, prompt/tool budget, temperature/seed policy and executor tool schemas. Keep retrieval context budget matched to the no-retrieval arm (or report added tokens).
5. Conduct analysis and look for narrow repeated failures. Only then choose A4-A6 specialist training family. Do not pick a domain post hoc because it made a spectacular plot.
6. Verify license/provenance at the file/package level; reuse TRL+PEFT (SFT first), preserve base checkpoint, adapter hash, data hash, optimizer/log and train/test integrity evidence.
7. Run A7 heuristic first. Only train A8 router on training outcomes, with no hidden test labels; calibrate abstention on development data. For task-level routing, a non-generating heuristic or linear probe should be compared with an LLM-as-router.
8. Compare A0-A9 on frozen independent heldout tasks. Pair runs by task and stratify by repo; report raw cases and uncertainty. Treat rejected model runs honestly.
9. Present failure taxonomy before proposing any new architecture. A verifier exploiting a lexical shortcut voids the corresponding outcome claims.
10. Stop without automatic promotion. Release only a sanitized report, signed manifests and reproducibility commands; seek a new scoped approval for model deployment.

## Failure taxonomy: what a trained specialist might fix

| Failure | Try first | When training might help |
|---|---|---|
| Wrong tool schema/JSON | Guided decoding, function schema tests, feedback loop | Repeated structured planning failures despite schema validation |
| Doesn't know how to test project | Verified executable run_tests skill | Need adaptation to unseen tool families, not simple command selection |
| Forgets older lesson | Time-stamped episodic memory + retrieval | Cannot learn to select/weight evidence despite clear retrieval |
| Security task hallucination | Independent verifier, file-grounded evidence | Genuine domain understanding error persists across sound evidence |
| Long reasoning runs out of context | Context compaction, scoped retrieval, task splitting | Controlled state-tracking failure not explained by context management |
| Tool calls too many steps | Deterministic controller, shorter tools | Poor policy choices consistently attributable to weights |
| Router sends task to weak model | Better features/calibration/abstain + deterministic override | Enough verified outcome data exists to beat rules |
| High latency | Keep resident model, cache, batch independent tasks, adapter reuse | Training is unlikely to fix GPU contention or WAN latency |

## Resource/control boundaries

- No paid inference/training or cloud account registration from this research package.
- No sudo, raw disk/kernel/driver changes, GPU voltage/power-cap manipulation, public network listener or untrusted worker assignment.
- Honor existing Haven Lab GPU lease, agent-worktree boundaries and review-before-merge.
- Same file/skill permissions across all model arms; no tool authority expansion after self-approval.
- A refusal or failed model load stays a failed datum, not replaced with a different checkpoint and called successful.
- HIVE PR #100-102 remain unmerged pilots. Their toy model correctness tests do not constitute a production model fleet.

## Decision gates and stopping points

- **Gate 0: benchmark validity.** Holdout separation, provenance, independent expected behavior, can the grader reject hand-crafted falsifications? If no, stop before training.
- **Gate 1: reusable skill value.** Promote only a previously independently admitted skill on held-out tasks; if it is not called, compare a deterministic auto-invocation controller.
- **Gate 2: memory value.** If memory provides no reproducible task-success lift beyond evidence supplied in a comparable prompt, don't add a memory service.
- **Gate 3: specialist training value.** If trained 2B does not beat base 2B+skills on target family without unacceptable OOD regressions, stop that adapter.
- **Gate 4: router value.** Learned A8 must beat A7 on real verified successes, or reach the same success level with materially lower measured cost, *with no forbidden route*. Otherwise leave the rules scheduler.
- **Gate 5: neural memory novelty.** Only test new recurrent/neural memory if Gate 2 demonstrates a *specific unresolved temporal/state tracking failure*. Match parameters/data FLOPs/context and compare to a simple recurrent baseline, standard attention, and retrieval.
- **Gate 6: hardware/efficiency.** Only authorize a new resource strategy after independent repeated actual measurements and rollback verification.

## Data schema proposal for private task-level records

Each run records:
- experiment_id, preregistered_task_id, repository_family_id, split, model_name, exact checkpoint_hash, adapter_hash if any, inference backend version, hardware_node_id (private), task_family;
- executor_version, tool_schema_hash, skill_admission_hash, memory_snapshot_hash, route_candidates and chosen route with decision evidence;
- egress_grant, sandbox_mode, provider_boundary, measured startup time, warm/cold, context, max steps, random seed, wall/decode/prefill time, observed sensor coverage;
- independent test artifact hash, grader_hash, final verifier status, error taxon, full receipt references (private), summary digest for public handback.

Version each run; do not rewrite old evidence when regrading with a new grader. A regraded report points to the original immutable run.

## Literature used to design these experiments

- RouteLLM, ICLR 2025: https://proceedings.iclr.cc/paper_files/paper/2025/hash/5503a7c69d48a2f86fc00b3dc09de686-Abstract-Conference.html
- Switchcraft, Microsoft Research 2026: https://www.microsoft.com/en-us/research/publication/switchcraft-ai-model-router-for-agentic-tool-calling/
- Single vs multi-agent small model study, ACL 2026: https://aclanthology.org/2026.acl-industry.123/
- MoLoRA, ICML 2026: https://proceedings.mlr.press/v306/shah26d.html
- S-LoRA, MLSys 2024: https://proceedings.mlsys.org/paper_files/paper/2024/hash/906419cd502575b617cc489a1a696a67-Abstract-Conference.html
- QLoRA: https://arxiv.org/abs/2305.14314
- TRL/PEFT: https://huggingface.co/docs/trl/peft_integration
- LongMemEval, ICLR 2025: https://mlanthology.org/iclr/2025/wu2025iclr-longmemeval/
- MemoryAgentBench, ICLR 2026: https://mlanthology.org/iclr/2026/hu2026iclr-evaluating/
- AMA-Bench, ICML 2026: https://proceedings.mlr.press/v306/zhao26bs.html
- Titans, NeurIPS 2025: https://research.google/pubs/titans-learning-to-memorize-at-test-time/
- Nested Learning/Hope, 2025: https://research.google/blog/introducing-nested-learning-a-new-ml-paradigm-for-continual-learning/
- Mamba-3, ICLR 2026: https://proceedings.iclr.cc/paper_files/paper/2026/hash/8abd2043b71a074278d5f687947bff9c-Abstract-Conference.html

## Handback, status, and next decision

**Delivered:** experimental question, non-overlapping arms, eligibility and license gates, primary and secondary endpoints, controlled training/fallback test, failure taxonomy, explicit stop conditions.

**Not done:** no training run, router integration, live model invocation, installed memory stack, hardware modification, model promotion, public deployment, or cost incurred.

**Next human decision:** approve a finite Gate-0/1 experiment, with one heldout task family and one model on a free GPU lease. Owner approval of this document is not automatic permission to merge, deploy, register cloud services, or spend money.
