# Haven HS-01 / R02 — Independent evidence audit and next experiments
Date: 2026-10-25 America/New_York (GitHub receipts dated 2026-10-26 UTC)
Status: REVIEW PROPOSAL ONLY; no host access, new inference, new training, paid job, firmware action, branch merge or session launch performed by this reviewer.

## Scope, provenance and verified repository state
Read as of this review:
- Main `4a73a55bfc263d53b8e657403a693004e2871ef6`: previous Windows Model Lab and retained research. Main does **not** yet contain Linux deployment or distillation experiments.
- HS-01 design PR [#34](https://github.com/erpzz/haven/pull/34) (draft): v1 and Ubuntu-on-X9 v2.
- Bootstrap PR [#35](https://github.com/erpzz/haven/pull/35) (draft) based on main.
- Linux runtime PR [#36](https://github.com/erpzz/haven/pull/36) (draft), stacked on #35; Linux operational handoff, user services, Mac SSH tunnel, llama.cpp, prepared Strata, administration receipts.
- Bakeoff PR [#28](https://github.com/erpzz/haven/pull/28) (open), distillation PR [#29](https://github.com/erpzz/haven/pull/29) (open, stacked on #28), Linux LoRA pilot PR [#37](https://github.com/erpzz/haven/pull/37) (draft, stacked on #29).
- Concurrent Claude branch `claude/opus-tool-distill-20261026` (from Codex's distillation work). This audit did **not** change that branch or claim to have read the live Claude/Codex terminal sessions.
- Evidence sources: `ops/haven-core/CLAUDE_NEXT_SESSION.md`, `LINUX_MODEL_LAB.md`, `STRATA_LINUX.md`, `linux-strata-result-20261026.json`, `labs/intelligence-bakeoff/distillation/LINUX_PILOT.md`, `results/linux-pilot-20261025.json`, and the Claude branch's `tool_sft/{README.md,PREREGISTRATION.json,agent.py,train.py,run.py,run_arms.sh,teacher_session.py,world.py}`.

GitHub repository and published receipts are accessible; **raw local Mac CLI session history and live Slink are not accessible to this reviewer**. Thus all observed host results below are *checked-in execution receipts*, not independently repeated tests. A running Claude branch is not itself evidence of any newly completed teacher collection or fine-tuning. Hugging Face account authorization was checked through the linked connector; `hf_jobs ps` returned no currently running jobs. No HF compute was launched or paid.

## Genuine host tests already documented — avoid re-running without reason
| Work | Evidence | Correct interpretation |
|---|---|---|
| Fast 4B | 33 of 33 layers offloaded, one warm browser response 91.25 decode tok/s, 0.17 s first output | Real CUDA inference, but short sample; initial cold arithmetic response was wrong |
| Strata IQ2_XS | Signed Linux v0.2.6/Control 0.1.51/engine 0.1.50; one authenticated 27-token response at 27.7 backend tok/s; unauthenticated 401; clean explicit stop and return to 4B | Real model response and isolation check, **not** quality or sustained performance |
| Strata cold startup | 868 s until API-ready; 836 s/33.02 GiB effective expert load | Approx. **40.4 MiB/s effective load**, not a raw USB bandwidth measurement |
| Local SFT | 40 CUDA steps, 18.016 s, 2,826,555,904 peak allocated bytes, 3 train examples | Real 0.6B LoRA mechanics; no inference model promotion |
| Frozen 11-probe comparison | Facts 0/3 → 0/3; composition 0/4 → 0/4; retrieval 1/2 → 2/2; unknown 2/2 → 2/2 | No demonstrated skill or fact learning; a one-item retrieval change is inconclusive |
| Tool-use 4B | 2/8 before interface/scorer fix, 3/8 after; 7/8 tool choice; 8/8 transport | Real local model attempts on **synthetic** worlds, not trained improvement or production task reliability |
| Remote admin | Mac `ssh haven`, strict host key, private SSH tunnel; signed driver survived reboot; GPU container visibility; restricted UFW + clean apt receipts | Reported completed operations, but not independently rechecked here |

### Highest-value systems question: Strata cold-start bottleneck
Expert-loading effective rate = 33.02 GiB / 836 s = 40.4 MiB/s. This aggregates reads, decompression, memory movement, paging and initialization. **Do not equate it to physical SSD throughput or assume a faster drive solves it.** Before changing hardware:
1. While Strata is **stopped**, record `lsusb -t` topology/link speed, filesystem and root device, `dmesg` USB/UAS resets, SMART/thermal data where supported, and CPU/RAM/swap activity. No private serials in Git.
2. Perform a **bounded read-only** sequential throughput probe on a *known model shard* under operator control, using direct reads only if supported; record cache state, read amount, elapsed, block size and errors. Complement with nonsequential read samples or process I/O instrumentation to match actual expert-load pattern. Never `drop_caches` on a production workload or unplug/move the mounted root device to benchmark it.
3. Compare the physical read observation with expert-load logs and CPU utilization. Distinguish USB link limitation vs many small I/O operations vs decompression/dispatch vs caching/page faults.
4. A second 15-minute cold Strata startup is warranted only if one concrete candidate fix can be changed reversibly and the baseline is preserved. Measure identical profile and model with before/after receipts; otherwise conserve time and focus on capabilities.

## Research: Claude's 550-episode tool-learning campaign
The active Claude branch specifies:
- train: 400, dev: 40, held-out paraphrase: 60, held-out novel composition: 50; 10 train families and 5 held-out composition families;
- teacher Strata trajectories, verified-success only; Qwen3-0.6B base, matched teacher-SFT and oracle-SFT arms; the 4B and teacher as references;
- exact tool contracts, per-principal isolation, inert proposals, no external actions or private data;
- frozen hashes and a threshold of **+15 percentage points** pooled held-out pass rate (n=110), without increased authority/leak/execution-claim violations.

**What it does and does not prove:**
- The scripted oracle's 550/550 passes validate consistency between its built-in plans and its own deterministic verifier. They do **not** establish that any model passes those cases.
- The splits are genuinely disjoint on selected vocabulary and composition families, but all worlds are generated by the same procedural world and verifier. Treat held-out score as **within-generator generalization**, not proof of real-world task competence.
- The PREREGISTRATION file records a contract amendment after inspecting the untrained 4B reference failures, affecting checks on **217 episodes** while reportedly preserving prompts and oracle plans. This is disclosed, but the reference is **not a fully blinded pre-amendment baseline**. Retain both hashes and original/rescored numbers; prohibit further test-driven revisions after teacher/student results are seen.
- Teacher and oracle training sets are matched by selected episode IDs and optimization steps, **not necessarily by target token count, tool-turn count or distribution**. Measure those differences before attributing any teacher/oracle improvement to learned policy.
- The `run.py` deadline permits partial evaluations. **Do not evaluate pass/fail thresholds on n<110** or compare arms with different completed episode sets. A valid comparison must check exact ID equality, full denominators, same model revision/template/generation limits, format/transport failures and task-family coverage.
- A keyword/trace-based deterministic verifier can have false positives and negatives. Preserve sample-based independent adjudication on a separate blind suite; do not equate lexical compliance with safe end-to-end tools.
- One deterministic seed and one generation per task are a reproducible pilot, not statistically stable evidence. If the pilot crosses threshold, request another independent seed and Wilson or paired bootstrap uncertainty/discordance analysis before any promotion. Treat harmful/privacy violations as hard gates independent of aggregate score.

**Suggested stop/go:**
1. Let Claude finish **one** preregistered baseline → bounded teacher collection → verified train-data assembly → paired student/oracle training and evaluation on Slink, if it has actual local operator approval and a single GPU lease. Keep all results private and publish sanitized aggregate receipts. Don't repeat the already successful 3-example LoRA mechanics test.
2. If verified teacher coverage is small or there is no complete held-out run, stop with the actual failure rate/timeout details rather than filling gaps with oracle rows disguised as teacher successes.
3. If 0.6B demonstrates a real meaningful signal, **then** consider a 1.7B text-only student pilot. Hugging Face confirmed `Qwen/Qwen3-1.7B` (about 2.03B actual parameters, Apache-2.0), but fp16 weights alone are roughly 3.8 GiB before gradients/activations; fit on 8 GiB is **not** verified. A measured 4-bit NF4 + LoRA path is worth a separate feasibility test, using fp16 on Turing rather than assuming bf16. No blind 2B/4B fine-tuning downloads.
4. Don't promote an adapter without passing functional and privacy regression suites on a **fresh external benchmark** that neither teacher-data generation nor development accessed.

## Next genuine end-to-end acceptance test: useful Haven behavior
After or independently of the Claude research campaign, prioritize **one real scoped Haven workflow** executed through the actual Mac → SSH tunnel → user service → local model → tool boundary:
- An operator creates a synthetic task in the real running Haven UI/API that requests a read-only inventory or evidence-grounded answer, with deliberate missing evidence and an attempted cross-principal resource reference.
- Observe authenticated submission, actual tool dispatch (or explicitly absent tool route), evidence IDs, answer correctness, cancellation, timeout/partial output, server process ownership, and reconnection after closing the Mac browser/SSH client.
- Reconnect and retrieve the *same durable job ID and result*. If the present application has no persistent queue, record FAIL/MISSING_CAPABILITY and build the minimum viable queue instead of substituting a mock.
- Test two synthetic principals with real session-level isolation, including unauthorized direct API requests and cache boundaries. No household-private records, cameras, drone movements or third-party security targets.
- One actual clean **reboot with external X9** and service recovery/SSH reconnect receipt before calling the host unattended. Avoid repeated reboot loops.
- Record executable command, exact commit/service version, date, local-only raw receipt hash, pass/fail and rollback. Check objective outputs rather than judging a fluent response as correct.

## Priority recommendation and resource allocation
**P0 — Preserve the running system.** No speculative driver reinstalls, USB disk moves, blind sudo/service changes or merge of stacked PRs. Keep known-good fast 4B service and Windows fallback.
**P1 — Claude experimental gate.** Finish exactly one frozen teacher/student/oracle comparison if not already finished. Keep independent eval inaccessible to training.
**P1 — Slinky research & independent review.** Inspect receipts, actual model licensing and hardware fit, audit evaluation leakage and benchmark design; don't occupy Slink GPU while Claude runs.
**P2 — Cold-start diagnostics.** One bounded read-only USB/expert-loading profile, targeted at the observed 836 s load.
**P2 — User-visible end-to-end job.** Real tunnel, durable identity, restart, cancellation, and evidence-linked answer.
**P3 — Future models/workers.** Optional 1.7B QLoRA, Mac M4/ThinkPad task workers, model-vs-agent comparisons on task-matched workflows, hosted DeepSeek under explicit budget and data classification. No synthetic pass substituted for a real-world qualification.

### Reporting requirements
For every experiment distinguish `PROPOSED`, `STATIC_TEST`, `SYNTHETIC_MODEL_RUN`, `REAL_GPU_RUN`, `REAL_END_TO_END`, `INDEPENDENT_VERIFICATION`, `BLOCKED`. Tests must include failure counts, known-answer accuracy, cost/timing, actual environment and raw receipt location held privately. No fake evidence, no trainer loss as a quality metric, no model judge as the sole verifier.

### Hugging Face landscape checked
Linked HF account is connected. Checked official Hub entries:
- [Qwen3 0.6B](https://huggingface.co/Qwen/Qwen3-0.6B), existing executed student, Apache-2.0;
- [Qwen3 1.7B](https://huggingface.co/Qwen/Qwen3-1.7B), text-only next student candidate, Apache-2.0;
- [Qwen3.5 0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B) and [Qwen3.5 2B](https://huggingface.co/Qwen/Qwen3.5-2B), newer multimodal architectures, Apache-2.0, separate runtime/training validation;
- [Qwen3.5 4B](https://huggingface.co/Qwen/Qwen3.5-4B), current fast-model architecture.
Official [bitsandbytes hardware matrix](https://huggingface.co/docs/transformers/quantization/bitsandbytes) lists Turing support for int8 and NF4/FP4 LoRA. **Support ≠ measured fit for 2B/4B training on this 8GB GPU.**
HF connector `hf_jobs ps` returned no running jobs; none were started by this review.

## Integration / Git procedure
This document lives in its own **review branch** and should not alter the ongoing Claude or Codex worktrees. Do not merge unrelated PRs or retarget stacked PRs automatically. Review in dependency order: #28 → #29 → #37 (and any later Claude research PR); #35 → #36; #34 separately as architecture. Validate actual diff/tests for each before merge. Current `main` remains the historical Windows baseline. Preserve private receipts and leave raw CLI transcripts, API keys, model weights and sensitive storage details out of Git.
