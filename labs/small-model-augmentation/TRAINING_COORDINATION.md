# Training / reasoning-search coordination with #123 — 2026-11-25

Workstream: #126 P2  
Training workspace of record: #123  
Status: **coordination/audit only — no training code, teacher batch, inference or GPU work in this branch**

## Decision

**DECISION:** Do not build a second training stack in #126. PRs #124/#125 remain the sole W1/W2 training implementation. The small-model augmentation work contributes runtime contracts, pre-training measurements and conditional research hypotheses only.

**DECISION:** The amended #123 research plan remains approved at PR #124 head `fd2c2998ad83ff1e7da49d7ce8ca461e40d4c867`. Operational sign-off on PR #125 remains withheld at head `a7abd59aa130333b49e0338078e01bab86e5f26a` until the previously reported CPU defects are closed and the actual loss-reduction weighting is verified before training.

**DECISION:** No new training arm is added merely because #127–#133 now exist. First establish the stock 4B's residual **model-clean** failure modes under the frozen intended inference controls. Train only the residual judgment failures that deterministic/runtime controls do not already solve.

## Exact source reviewed

### Plan stack (#124)

Head: `fd2c2998ad83ff1e7da49d7ce8ca461e40d4c867`

- `PLAN.md` blob `79454331871c74b69324231dc8bb1ceed7d92d11`
- `AMENDMENT_1.md` blob `1de921b087236c8d7085ee8a6e2d802d02453fc3`
- `AMENDMENT_2.md` blob `8204bb4ff7c32d48a76e0a2b636b5e97936c378b`

Amendment 1 already addresses the key research-validity concerns: three score views, group-level splits, matched oracle controls, frozen per-episode weighting, planned paired tests, evidence-flip/control pairs, and a stepwise teacher exchange. Amendment 2 correctly keeps only model-clean W1 attempts, freezes the regression margin, separates the reserve-collision checks and defines the private store.

### Phase 0 implementation (#125)

Head: `a7abd59aa130333b49e0338078e01bab86e5f26a`

- Phase 0 README blob `215f5eef61f9e56e864a6e281dd269836fb255d6`
- W1 runner blob `49de59e7e5f168723400c74fd4a07c11f4d7b668`
- notebook builder blob `f762b1fee6223897f0d69e61f6f0e839a672f3b8`
- teacher exchange blob `80101adce2039f1a7edc45c98f79587eef162452`
- SFT row-weight helper blob `8da94c6130417b608fa4c55bbc2cd5b8751e9be3`
- Phase 0 manifest Git blob `dd754a303fa175d5be06a38cc5a233d08138f0fc`

Reported CPU receipts are substantial: 54 tests, 3,600/3,600 + 2,370/2,370 HARE generator checks, 280/280 query oracle checks, 66 flip + 66 control pairs, 120/120 valid teacher sessions and 0/1,092 corrupted sessions kept.

The M4 v3 review step is now recorded as ACCEPT with the owner's documented deviation from the original human-review requirement. The remaining #123 blocker is Astra's operational sign-off on #125, not a missing M4 commitment.

## Existing #125 operational hold — closure contract

These are the defects already posted on #123. This document maps them to the augmentation controls so Claude can close them without duplicating implementations.

### 1. Pilot completion and resume identity

Current risk: duplicate/missing/foreign attempt rows can satisfy completion logic, and resume is not bound strongly enough to the original run definition.

Closure:

- define the exact assigned grid `(episode_id, attempt_id)` before execution;
- require exactly one terminal metric receipt for every assigned slot before G1 is eligible;
- duplicate, missing, foreign or mismatched slots block G1;
- bind resume to an immutable run identity containing at least episode-set hash, model artifact hash, engine, decoding/settings, harness/code revision and attempt count;
- recorded timeout/missing outcomes stay failures in the denominator.

**Reuse:** #130's journal contract supplies the right pattern: immutable `manifest_sha256`, unit id = episode/attempt, explicit recovery epoch, exact terminal state and no silent reuse of a foreign run. Claude should adapt this into the W1 runner rather than importing the #126 prototype blindly.

### 2. Pilot cost accounting

Current risk: deadline-skipped jobs can be counted as completed attempts, and device-hour accounting covers only part of a resumed allocation.

Closure:

- count queued, started, model-requested, terminal, skipped-before-start and timed-out slots separately;
- `attempts_completed` means terminal assigned slots, not jobs submitted;
- inference throughput remains a separate metric from allocation/device time;
- device-hour budget accumulates setup + server lifetime + all resumed allocation sessions;
- resuming cannot reset prior charged allocation time.

**Reuse:** #133's sidecar terminology deliberately separates attempts, blocked attempts and runtime metrics. Do not overload a single counter.

### 3. Executable notebook preflight

Current risk: a piped test command can return the downstream process's status while the actual test runner failed; the notebook bundle also omits a build-time test file.

Closure:

- preserve the unit-test process exit code (for example `set -o pipefail` or no pipeline);
- explicitly list which tests execute in the generated notebook and which are build-time-only;
- inject one harmless failing test in a CPU preflight and demonstrate engine startup is never reached;
- remove the injected failure and rerun the exact generated notebook preflight.

No #126 code is needed here.

### 4. Seal before gold reveal

Current risk: a batch can seal with assigned IDs still open; reveal trusts the existence of a seal file without fully revalidating terminal coverage/current session state.

Closure:

- every assigned ID appears exactly once as a final terminal record or explicitly terminal transport failure before seal;
- no open IDs at seal;
- seal binds batch id, exact assigned-id set, answer/session state hash, input commitment and schema/tool versions;
- reveal recomputes/revalidates the current sealed session before writing any gold;
- wrong-batch, changed-session, missing-terminal, duplicate-terminal and open-session cases all refuse reveal.

**Reuse:** #130's hash-chained terminal-state idea and #132's content-bound exact release pattern are useful design references. Do not expose gold merely because a filename exists.

### 5. Actual loss-reduction weighting (required before training, not necessarily before pilot collection)

Current risk: helper-level trace weights can sum to 1.0 while a trainer that applies the same trace weight to every row/token gives long traces disproportionate loss.

Required invariant:

- each episode contributes total optimization weight 1.0;
- if an episode has N kept traces, each trace contributes exactly `1/N`;
- within a trace, token-level/row-level reduction must normalize to that trace contribution rather than multiply it by trace length.

Minimum closure test:

- one episode with two traces: one very short and one much longer;
- set an identical synthetic per-token loss;
- assert each trace contributes 0.5 and the episode contributes 1.0 after the **actual trainer loss reduction**, not only in exported metadata;
- repeat with different turn and token counts.

If the training library cannot express this invariant directly, implement/verify the custom loss reduction before any GPU training result is trusted.

## How #127–#133 should affect training — and how they should not

### #127 model/runtime admission

Use it to freeze the exact local inference identity for development evaluation. Do **not** train a model to compensate for a wrong alias, wrong context window or wrong executable.

### #128 evidence admission

Evidence structural/lineage failures are runtime data-integrity failures. They should block the episode, not become student targets.

### #129 exact tool/target scope

Keep the gateway regardless of training. Unauthorized attempts remain a model-safety metric and may be a training signal, but weights are never treated as the authorization boundary.

### #130 checkpoint/recovery

This belongs in collection/evaluation infrastructure. A resume bug must not be interpreted as a model failure or used as training data.

### #131 tool-context narrowing

This one can change model behavior because it changes what the model sees. Before collecting W1/W2 data, decide whether the deployed 4B will use the narrowed tool surface.

If #131 E1 passes and is intended for deployment:

- teacher and student must see the **same routed/authorized tool catalogue** for each episode;
- the route/catalog hash belongs in the training/evaluation run manifest;
- a teacher trace that calls a tool the deployed router would hide is invalid training data.

If #131 is not adopted, keep the current #123 full-harness catalogue and do not mix routed and unrouted traces in one arm.

### #132 bounded claim mode

This can change the output contract. Do not train prose and then silently deploy an id-only structured answer contract.

If #132 E2 passes and structured claim mode becomes the answer-of-record for a task family, amend #123 **before teacher batch 1 for that family** so:

- teacher outputs use the same claim-selection contract;
- W1 kept rows use the same contract;
- oracle controls use the same contract;
- model-clean scoring grades the structured selection before deterministic rendering.

If #132 is not adopted, the existing #123 conclusion+claim format remains.

### #133 controlled evaluation

Run the stock 4B through E0–E2 **before GPU training** after the intended inference controls are integrated. This becomes the new engineering baseline for residual-error attribution. It does not replace #123's development decision rules or #119 M4.

For every matched comparison, bind the exact unchanged semantic grader/adjudicator revision (`grader_sha256`) separately from the arm code hash, and require distinct host-owned private receipts per arm/case. Receipt hashes must be unique within an arm and disjoint across compared arms. Otherwise an apparent model delta can be a grader/instrumentation or evidence-reuse artifact.

## Residual-error taxonomy before training

Every stock-4B development failure should be assigned to one primary class from host evidence, not model self-report:

| Class | Primary remedy |
|---|---|
| wrong model/runtime admitted | #127 infrastructure |
| malformed/untrusted evidence | #128 infrastructure |
| out-of-scope tool/target attempt | #129 gateway; optionally train safety afterward |
| interruption/resume artifact | #130 infrastructure |
| relevant tool hidden / excessive tool context | #131 routing policy |
| relation/value/time fabrication that exact claim mode can prevent | #132 structured boundary |
| correct evidence/tools available, but model chooses the wrong supported conclusion | **weights candidate** |
| unjustified refusal/abstention on answerable evidence | **weights candidate** |
| failure to update conclusion when decisive evidence flips | **weights candidate / Rule 8** |
| inability to follow the observable tool/claim output contract | **weights candidate**, after contract is frozen |

Training should target the last four classes. This prevents the model from being trained around infrastructure defects.

## Reasoning-search ladder — conditional, not new arms today

The existing #123 arms O/A/B/C remain the first training experiment.

Only if the preregistered W1/W2 supervised arms fail for a clearly diagnosed residual judgment reason should another training method be proposed.

### R0 — runtime controls only

Stock 4B + frozen intended inference controls. Establish the residual-error baseline with #133.

### R1 — existing W1/W2 supervised plan

Run #123 exactly as amended after #125 closes. This is the first weights experiment.

### R2 — preference training from observable decisions (conditional)

Consider only if R1 improves answer form but Rule 8 still shows evidence-insensitive judgment.

Potential pairs already exist without inventing hidden chain-of-thought:

- accepted model-clean trace vs rejected stock trace on the same episode;
- correct evidence-flip response vs stale-conclusion response;
- correct no-action/insufficient-evidence response vs unjustified action/refusal.

Use observable calls, dispositions and claims only. No hidden reasoning target. Freeze a matched oracle/preference control and a budget before running it.

This is a research proposal, not authorization to add DPO/ORPO/another arm now.

### R3 — RL already specified in #123

Only after supervised gates pass and a meaningful gap remains. Keep the existing rule: reward comes from generator/adjudicator gold and safety events, never from the verifier. Freeze coefficients/stopping rules first.

## One additional coordination rule: harness version is part of the weights claim

Before the first training rollout, freeze which inference controls are in the comparison harness.

A trained-vs-stock claim is valid only when both are evaluated under the same:

- model-visible tool/context policy;
- authorization gateway;
- evidence verifier/admission path;
- claim/output contract;
- deterministic renderer/fallback policy;
- model engine/decoding settings;
- exact semantic grader/adjudicator revision;
- per-arm instrumentation/receipt provenance, with no cross-arm receipt reuse.

If a runtime control, grader or output contract changes after training, rerun the paired development comparison under the new harness before reserve qualification. Do not attribute a harness improvement to weights.

## No-duplicate-stack boundary

#126 will not add:

- a second generator;
- a second dedupe implementation;
- a second Astra teacher exchange;
- another Kaggle training notebook;
- another LoRA trainer;
- a parallel W1/W2 arm registry.

All such work stays in #123/#124/#125 under Claude's training lead. #126 may provide reusable runtime concepts, controlled-eval receipts and independent review.

## Gate state at this review

- M4 v3 review disposition: accepted by owner as documented AI-reviewer deviation.
- #124 amended research plan: approved.
- #125 operational Phase 0: **not yet signed off** at head `a7abd59`.
- GPU/model collection: remains blocked.
- teacher batch export: remains blocked.
- GitGuardian finding on #125: requires maintainer/security disposition without copying the flagged value.

The next training action is not a GPU run. It is a revised #125 head that closes the four CPU operational defects, updates its manifest/receipts, preserves the amended plan, and leaves the actual loss-weight reduction check scheduled before training.

## Second-pass state recheck — 2026-11-26

Re-read #123's current comments and PR heads before handback:
- #124 remains open/draft at `fd2c2998ad83ff1e7da49d7ce8ca461e40d4c867`; the amended plan remains approved.
- #125 remains open/draft at `a7abd59aa130333b49e0338078e01bab86e5f26a`; no revised implementation has closed the operational hold.
- #123's latest Astra coordination decision still withholds GPU collection and teacher-batch export.
- The M4 v3 AI-reviewer ACCEPT remains an owner-documented deviation from the earlier human-review requirement; this memo does not reinterpret it.
- #133's final comparison contract now additionally binds the unchanged grader and rejects receipt reuse across arms; those constraints are incorporated above.

No training, inference, teacher exchange, reserve inspection, GPU work or GitGuardian disposition was performed in this second pass.
