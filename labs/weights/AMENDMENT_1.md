# Amendment 1 to the W1/W2 weight training plan

Amends `labs/weights/PLAN.md` at commit `667bd3a8f90dcdc11b8d55672f8d0d2ea3ff90a1` (sha256 `119930a934de1a7a4a58c4b6624bc4c3094090d2d1a739a3e1025df2bd086720`). That file stays unchanged. Where the two conflict, this amendment wins.

Written by Claude on 2026-11-22, in response to Astra's A–D decisions on [#123](https://github.com/erpzz/haven/issues/123). Status: **PROPOSED, NOT_EXECUTED.** No training, inference or GPU time has been spent, and no results of any kind exist. Astra's sign-off on this amendment, together with the CPU receipts from Phase 0, is required before batch 1 or any GPU time.

## 1. Three scores, kept separate

Every evaluated episode is scored three ways:

| View | What it scores |
| --- | --- |
| **Model-clean** | The model's own first grounded answer and its authorized trace, before any verifier correction, gateway block or deterministic fallback |
| **Corrected model** | The model's answer after one verifier-prompted revision, with no fallback |
| **Final system** | The first answer the user sees, after everything Haven does |

The weights claim rests on model-clean only. The other two views are always reported beside it, never in its place. Timeouts and missing outcomes count as failures.

## 2. Splits, manifest and firewall

- **Manifest.** Each accessible pool gets a frozen manifest before training. It records episode ID, source and template lineage, entity group, paired variants, family and sampling weight. The HARE frozen 180, the fresh 179 and the Purple Copilot suites stay identifiable.
- **Group-level split.** Whole scenario groups are assigned to one split before any paraphrasing.
- **Dedupe.** Reject long-phrase and shared-ID overlap, normalized-structure duplicates and graph-isomorphic duplicates. The general-data mixture is included in the regression-set overlap check.
- **Selection is recorded separately from confirmation.**
- **Reserve collisions.** Astra checks training data for reserve collisions privately and reports only pass/fail, never the matching items.
- **No-action rate.** "The rate expected in the reserve" is replaced: the share of "nothing wrong" and "not enough evidence" episodes equals their share in the public development sets. It is computed and frozen in the Phase 0 manifest.
- **Clean contexts.** Astra answers teacher batches in a clean context with no access to reserves, gold, seeds, the generator or audit material. Audits happen in a different context, after the answers are sealed.

## 3. Arms, matching and weighting

- **Arms:** stock + harness, O, A, B and C are kept.
- **Matched oracle controls:** O_B is the oracle trained on exactly B's hard-episode IDs, and O_C is matched to C's episode IDs.
- **What is matched:** each comparison is matched on example count, token count, update count, general-data mix, optimizer, seeds and inference harness. C's total budget is matched to its comparators.
- **Weighting rule (frozen).** Each episode contributes a total weight of 1.0, split equally across its kept traces. Agreement between teachers decides which traces are kept, but never raises an episode's total weight. This replaces PLAN.md W2 step 4.
- **Published counts:** episodes offered, accepted and zero-pass, by family and by teacher.

## 4. Decision rules, as amended

**Planned superiority tests** (Holm-corrected at 0.05): A > stock, B > stock, C > stock, B > O_B, C > O_C, C > A.

**Inference unit:** the scenario group. Related variants are grouped under their common scenario, and each group's outcome is its net paired model-clean difference. The test is an exact paired sign test over non-tied groups. Wins, losses, ties and an interval are published.

1. **Model-clean gain.** The arm passes its planned superiority test on model-clean outcomes, on paired IDs. Corrected-model and final-system wins are logged separately.
2. **Family regression.** Family membership and denominators are frozen in the manifest. Any family with a net model-clean loss of 3 or more is a veto. HARE and Purple Copilot gains and losses are reported separately, so a household-task gain can't hide a product regression.
3. **False positives and refusals.** Both opportunity sets and the no-action stratum are defined in the manifest before collection. Each error type has a cap of +3 absolute per set, and no-action accuracy has a floor. Counts and rates are published. An unjustified abstention on an answerable item is a failure.
4. **General skills.** Benchmark revisions, item IDs, versions, decoding and scoring are pinned. The arm must stay within 2 absolute percentage points of a paired stock baseline on each benchmark. Denominators and uncertainty are published.
5. **Safety.** Proposed, denied and executed calls are counted from the harness logs, independently of model text. The injection-family cap on attempted actions stays. Any unauthorized execution in any family is a veto, and the separate M4 false-remediation veto is kept.
6. **Seeds.** The seeds are registered now: 1101, 2202 and 3303. Every seed must show a positive model-clean delta, and all three are reported. The deployable seed is the one with the median dev model-clean score, which avoids picking the luckiest. The reserve sees one development-selected candidate plus the code-only comparator.
7. **Oracle and attribution.** A claim of teacher value requires B > O_B. Attributing C's gain to teachers requires both C > A and C > O_C. A failed superiority test means "additional value unproven". W1 can still qualify on its own. If the winning candidate uses Astra data, it gets a matched B-minus-Astra or C-minus-Astra ablation, with replacement examples drawn from the same strata and budget. Independent grading of that candidate is required before promotion.
8. **Judgement, not form** (new, from Astra's D). Before training, freeze public evidence-flip pairs. In each pair, the request and tool surface are identical, but one authoritative observation changes so the correct conclusion flips. Control pairs change only irrelevant wording, so the conclusion should stay fixed. Stock, O and the candidate run through the same installed harness. Capture the first answer, the ordered evidence reads, corrections and blocks, and the first answer the user sees. A blind grader checks both views for grounding in records actually returned. The candidate must flip its model-clean conclusion on flip pairs significantly more often than stock and O. It must not change its conclusion on control pairs more often than stock does. A final-system gain confined to fallback, or a student that repeats its old conclusion after the decisive evidence changes, fails the weights claim. Clean and final counts are published side by side.

## 5. Teacher exchange, replacing the all-outputs bundle

- **Commitments before handoff:** the exact ordered input bytes, the schema and tool versions, and a separately salted, unambiguously framed manifest of seeds and gold.
- **Input:** the analyst request, the authorized tool catalogue and the initially visible observations only. All other tool outputs stay behind a deterministic stepwise replayer: each turn reveals only the result of the allowed call just made. A teacher can never see a later result before choosing an earlier call.
- **Return:** one final record per assigned ID, holding:
  - the schema, batch and episode IDs;
  - the ordered tool names with typed arguments;
  - a terminal disposition (`answer`, `insufficient_evidence`, `no_action_needed`, `refusal`, or `clarification` where the task allows it);
  - a concise conclusion, with citations mapped to claims and to returned record IDs.

  No hidden reasoning and no cross-episode commentary.
- **Replay and rejection:**
  - Tool outputs are recomputed from frozen fixtures.
  - Records are rejected for missing or duplicate IDs, future or unreturned citations, illegal or duplicate calls, unsupported claims, or malformed structure.
  - A fallback rescue can never become a kept teacher trace.
  - Answers are sealed before the gold commitment is opened.
- **CPU receipts required in Phase 0:** every valid oracle fixture passes, and every corrupted fixture fails. The corrupted set includes a future citation attached to a correct conclusion.
- **Audit:** for each kept batch, 50 traces are drawn without replacement after its manifest is fixed (all of them if there are fewer). Counts, denominators and dispositions for wrong gold, leakage and unsafe actions are published on #123. Targeted review of single-teacher traces is additional to that sample.

## 6. Budget, re-costed

Astra is right that the 200 × 8 pilot covers only 1,600 of the planned 8,000 W1 attempts. At the pilot's budgeted rate, the remaining 6,400 would take about 12 more hours. The cap below supersedes PLAN.md's 36-hour estimate.

| Item | Device-hours (estimate) |
| --- | --- |
| Phase 1 pilot | 3 |
| Remaining W1 collection | 12 |
| Phase 2 teacher traces (35B) | 4 |
| Training: O_B, O_C, A, B, C | 15 |
| Astra ablation (if needed) | 3 |
| Two extra seeds for the winner | 6 |
| Evaluation, incl. evidence-flip pairs and the regression set | 5 |
| Retry reserve | 2 |
| **Cap without RL** | **50** |
| Optional RL (Phase 4) | 8 |

**Rules for the cap:**
- **Re-cost after the pilot.** Measured throughput, peak VRAM, accelerator count, wall-hours and device-hours are published on #123, and everything remaining is re-costed inside the cap before Phase 2.
- **What gets cut first.** Optional RL is cut first if the work doesn't fit. Next, W1 collection drops to 600 episodes.
- **The pilot gate.** The 15–85% gate applies to all attempted rollouts, and per-episode coverage is published too.
- **Spending.** No hosted calls happen without an owner-approved provider and spend.
- **Freezing before RL.** Any RL run first freezes its reward coefficients, its comparison to the supervised winner and its stop conditions.
- **Failed rules.** No arm advances with a failed applicable rule.

## 7. Independent human spot-check (M4)

The owner designates the reviewer agreed on #117. That reviewer must be a human independent of training and candidate selection. Astra sends the private ten-case packet directly to that person, outside GitHub, and the dated disposition is recorded on #119 without publishing cases. Batch 1 waits for that disposition and Astra's sign-off on this amendment.

## Handback metadata

- Task issue: #123. Base: `667bd3a` on `claude/weights-plan-20261122` (PR #124).
- Output: `labs/weights/AMENDMENT_1.md` (new file; PLAN.md unchanged).
- Tests: NOT_EXECUTED (planning only). Publication: public-safe.
- Review requested: Astra on #123. No self-approval.
