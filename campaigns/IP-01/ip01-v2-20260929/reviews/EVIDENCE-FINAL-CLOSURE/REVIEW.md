# EVIDENCE-FINAL-CLOSURE — native independent handback

Native reviewer `01a0ef1f-a61b-7c60-b34a-477d91e77feb`; assignment 24; role `haven_evidence_auditor`. Root received this actual final message at 2026-09-29 21:54:18 UTC. Root transcribed the independent text below; repository path normalization only, no verdict or finding edits. Original native message retained privately. This is read-only review, not new executable QA.

---

**PASS — for the evidence integrity and honest bounded PARTIAL handoff at the frozen revisions below.** This verdict does not establish overall IP01 completion, protected benchmark acceptance, or canonical/production/physical qualification. Root’s final publication and cessation obligations remain downstream.

**Signed-role:** `haven_evidence_auditor` / R13–H06 / **Assignment 24, EVIDENCE-FINAL-CLOSURE**  
**Native identity:** `01a0ef1f-a61b-7c60-b34a-477d91e77feb` — **Chandrasekhar**  
**Profile:** `CUSTOM_PROFILE_FALLBACK`; inherited model and cost **UNKNOWN**; no model override.  
**Review completed:** 2026-09-29, approximately 21:52 UTC. **Publication: NOT_UPLOADED; root-owned.**

For the references below, `C/` expands to the repository-relative prefix `campaigns/IP-01/ip01-v2-20260929/`.

## Decisions

Accept the frozen evidence packet for an explicitly **PARTIAL** handoff. I found no blocking identity, denominator, or source-use inconsistency in that packet.

Reviewed identities:

| Artifact | Exact binding |
|---|---|
| Executable candidate | `0b59551f36990cfb8a723f97da6d367358a8ceb5` |
| Historical evaluated revision | `487c67299445a29e0fbbdede04259565f741f587`, qualified by the original 37 worktree hashes |
| Sealed QA publication | `e567c3dc541084044e6142ae236a5d71bf64e23f` |
| H00 closure publication | `01d0c746da73546478ed4882a484f3099fa110b9` |
| H00 manifest SHA-256 | `054eacd33074cb360fd195af6df6cc40e4a2277c92401532573c9b8c5b124121` |
| H00 handoff SHA-256 | `b458b7c6942612196e82b4e529937ac6ab17cb4199be71fef07ab8d87a41abd3` |

Initial checkout HEAD was the H00 publication. Final observed HEAD was administrative revision `03e159a8a4e23facb86788f8757c57445f39ce4c`; Git comparisons showed no changes to the candidate, sealed FINAL-QA directory, or frozen H00 closure directory. This is **not** acceptance of every administrative file at that later HEAD.

I read `AGENTS.md`, `PRECEDENCE.md`, the assigned profile, RI-01 and coordination protocols, handback requirements, and relevant work-package/coordination provisions. This review is distinct from root implementation/support, H00 synthesis, and empirical QA17. The recorded identities support that separation; they do not establish statistical independence of model errors. See `orchestration/RI-01/PROTOCOL.md:41–44` and `C/state/agents.jsonl:37,43,46`.

## Evidence

**Actual inspection performed:** read-only document/source inspection, JSON comparisons and arithmetic, SHA-256 checks, Git blob inspection, and Git archives streamed into memory for member hashing. No files were edited or extracted, and no repository code, application, tests, models, browser workflows, children, publication, or merge was executed.

The identity checks independently established:

- **37/37 candidate files:** current worktree and exact Git blob hashes match the reconciliation receipt. They also match the original freeze’s `worktree_sha256`, saved final source binding, and FINAL-QA source manifest. Historical/current source comparisons were equal after line-ending normalization.
- **107/107 sealed-QA files:** exact Git blobs and current worktree hashes match; the 106 manifest entries reconcile with those receipts plus the manifest itself.
- **H00:** all **94 inputs and four outputs** match their manifest hashes; the four outputs and manifest also match committed bytes.
- Both reproduction archives matched their recorded archive hashes. All **37 candidate members** and **107 designated QA members** matched. The QA archive contains **108 files overall**, because it also includes mutable `STATUS.json`, expressly excluded from the sealed manifest at `C/reviews/FINAL-QA/FINAL_PUBLIC_MANIFEST.json:110–114`. The 107 checks must not be described as sealing that mutable status file.

The independently reproduced archive hashes are:

- Candidate: `4a58860528135a89e67ed4fee4b74296be287d46d8f700600e47cf52a81f8d12`
- QA: `664a00d117c5aa626899f9ef579b6de8774b097c7e1e59f8bcb83a5eabc9548c`

H00 correctly distinguishes its worktree/manifest comparisons from root’s Git/archive checks. Its QA comparison scope is explicit at `C/integration/closure-v1/BYTE_VALIDATION.json:608–615`. My independent checks above are broader than that H00 scope; they do not retroactively change what H00 performed.

**Source use is substantive.** The closure overlay actually incorporates the failed attempts, partial denominator, B2 distinction, timeout limits, and cessation dependency into its decisions—not merely its bibliography. See `C/integration/closure-v1/INTEGRATION_HANDOFF.md:30–35,49–51` and `C/integration/closure-v1/CARRY_FORWARD.md:9–17`. The stale I05 totals in the preserved final map are explicitly superseded by the overlay at `C/integration/closure-v1/CARRY_FORWARD.md:11`.

## Acceptance

Application/test/model execution by this reviewer: **NOT_EXECUTED**. The following are audited historical observations, not new executions.

| Scope | Audited result and limit |
|---|---|
| Deterministic evaluation | Seven passing suite01 components plus **221 suite03 producer checks**. Suite01 retains **76 pass / 145 setup errors**; suite02 retains **7 pass / 214 setup errors**. Three starts consumed. The component receipts include commands, exit/JUnit projections and private receipt hashes. See `C/reviews/FINAL-QA/FINAL_DETERMINISTIC_RESULTS.json:225–299`. |
| Distinct strata | 150 independent checks; 38 APP/runtime checks using synthetic transport; 13 benign fault trials; 21 evidence checks comprising 13 validations plus eight corruption challenges; two browser races and journey/crash components. These are not one summed benchmark. See the same file at `:256–270`. |
| Pilot denominator | Independently recomputed **72 unique scheduled slots**, **54 observed and graded**, **45 pass**, **nine conservative fail**, **18 unrun**. All 24 family results agree with the requirement for three passing repeats. Protected supported **0/8**, unsupported **0/4**; criterion false. |
| Accounting | All **59 Task17 projections** have one unique claim hash and one unique settlement hash; charges match their settlement projections. They total **1484.451 seconds**. Adding the earlier five-call checkpoint, **108.954 seconds**, yields **64 calls / 1593.405 seconds**. The earlier checkpoint is at `C/reviews/MODEL-EXECUTION/EXECUTION_RESULTS.json:80–88`; final ledger attribution is at `C/receipts/FINAL_RUNTIME_SHUTDOWN.json:31–43`. |
| Actual versus semantic success | Successful computation is not a semantic pass. The two retained ambiguous image grades credit abstention/negative assertions but withhold grounding: `C/reviews/FINAL-QA/PILOT_INDEPENDENT_REVIEW.json:1233–1267,2121–2155`. I did not regrade unavailable pixels. |
| B1/B2 | Original B1 driver failure had zero model submissions and incomplete launch tracking; its later fresh scan is not retained-handle proof. Later B1 has attributed useful image/render evidence. B2 made one actual model submission but released no answer because of `GRANT_QUOTA_EXHAUSTED`; no observable abstention. See `C/reviews/FINAL-QA/ROOT_QUESTION_B1_PREMODEL_FAILURE.json:3–16` and `C/reviews/FINAL-QA/READINESS_RESULTS.json:58–104`. |
| Lifecycle | L1 text cancellation **0.156 seconds** is prior Task16 evidence; L2 image cancellation **0.141 seconds** is Task17 evidence. L3/L4 completed normally in **55.843/81.453 seconds**: natural model timeout **NOT_EXERCISED**. See `C/reviews/FINAL-QA/FINAL_QA_REPORT.json:32–43`. |

I inspected representative actual event, settlement and observer projections, including F001, B2, L2 and L3, and checked structural/accounting invariants across all 59 Task17 projections. For example, L2 preserves cancellation, settlement and independent zero-live/zero-listener transitions at `C/reviews/FINAL-QA/model-cases/L2.json:43–104,218–249`. B2 preserves failed terminal disposition separately from confirmed settlement and observed cleanup at `C/reviews/FINAL-QA/model-cases/B2.json:84–128,243–284`.

These projections provide more than runtime-summary prose. Nevertheless, raw traces and the private durable ledger were not opened. CPU-growth predicates, maximum sampling gaps, projection fidelity to private originals, and private semantic judgments remain **attributed QA evidence**, not independently reproduced measurements. Finite sampling cannot prove universal absence of short-lived processes.

## Findings and required responses

| ID / severity | Evidence and disposition | Required response |
|---|---|---|
| **E24-01 — LOW, draft correction** | `C/MORNING_REPORT.md:72` lists H00 closure as next after saying it returned. `C/state/COMPLETION_AUDIT.json:580` still says root/H00 closure awaits returns. These are changing drafts, not frozen reviewed final bytes. | Root should reconcile those phrases with actual returned reviews during finalization. Do not rewrite the preserved H00 packet to repair root drafts. |
| **E24-02 — LOW, assignment digest transcription** | The supplied QA-handoff digest omitted one `5b`. Independently verified bytes match the repository binding at `C/integration/closure-v1/BYTE_VALIDATION.json:431–438`. | Use **`733b1d373c42c01ef5a94b5b5b0a971bd6c002952fae9c3a0cdf93ee8041649d`** in the final receipt. This is not an evidence-file defect. |
| **E24-03 — qualification gap retained** | Same-user protected separation remains **NOT_ESTABLISHED**; protected result remains **EVALUATION_INCONCLUSIVE**. The public input-inspection receipt supports attributed evaluator access, not enforced author blindness: `C/reviews/FINAL-QA/INPUT_INSPECTION.json:3–12`. | Preserve both verdicts. Do not convert a role label, separate directory, or absence-of-exposure assertion into protection evidence. |
| **E24-04 — readiness/usefulness gap retained** | B1/B2 readiness is **NOT_MET_BY_B1_B2**. Separate work-package pilot eligibility is recorded at `C/receipts/TASK17_B2_RESULT_RECONCILIATION.json:23–25`; it does not repair B2. | Preserve both positions, the spent slot, and no-abstention result. Retain source-relevance/early-quota feedback as future work under separate authority. |
| **E24-05 — final-completion dependency** | APP shutdown does not close native reviewers: `C/receipts/FINAL_RUNTIME_SHUTDOWN.json:43–45`. The old no-active snapshot prose is explicitly corrected at `C/receipts/H00_CLOSURE_FREEZE.json:15`. | Root must receive actual verdicts, reconcile findings, finalize publication, and record exact native cessation before claiming closure complete. See `C/COORDINATION_AMENDMENT.md:47`. |

No new blocking defect was established against the frozen packet. Retained qualification gaps must remain visible.

## Interface changes

None. No requirement, contract, schema, rubric, source, or evidence bytes changed.

Original **CE-F01–06 / R8-F01** remain traceable:

- CE-F01/03/06 have explicit egress, terminal-projection and settlement/result mappings at `C/integration/final-v1/CONTRACT_CODE_EVIDENCE_MAP.md:11–13`.
- CE-F02 has an exact-source-bound two-case browser recheck at `C/reviews/FINAL-QA/executions/suite-01/CE-F02_RECHECK.json:4–24`.
- CE-F04/05 have concrete independent regression assertions at `labs/ip01/evaluation/deterministic/test_code_early.py:8–30`.
- B2’s exhausted incidental context is not proof that the specific CE-F05 overlapping-usable-grant repair failed; its separate usefulness defect remains retained.

This evidence review accepts the traceability and bounded empirical attribution. It does not replace CODE-FINAL’s static disposition of those findings.

## Risks and open questions

Protected questions, expected answers, private assets, raw outputs and private grading rationales were not opened. The two conservative ambiguous grades and their dissent remain unchanged; original-grade preservation is attributed through the sealed QA records.

A narrow scan of **93 selected public text files** found no configured absolute-home-path or credential-pattern matches. This is not exhaustive privacy certification, image inspection, or review of future root publication bytes. The historical pathname disclosure remains disclosed at `C/receipts/PUBLIC_REPORT_EDITIONS.json:24–31`.

Original-workspace preservation remains the root’s bounded four-file comparison plus ASTRA identity/status observation, not my independent inspection of those workspaces or a filesystem-wide guarantee. See `C/receipts/ORIGINAL_SOURCE_FINAL_CHECK.json:8–44`.

## Next package

Root can publish this native review as part of the **bounded PARTIAL handoff**, retain dissent and failed attempts, correct the current drafts, complete checkpoints E/F and required readbacks, verify final public artifacts, and record exact cessation. No new model calls, suite starts, counter resets, or authority follow from this PASS.

The supportable claim is: **exact reproducible candidate and QA bytes; a retained three-start deterministic composite; attributed useful local/B1 behavior and observed cancellation; a partially executed, conservatively graded 54/72 pilot; protected evaluation inconclusive; final administrative closure still requiring root completion.**

**Signed: Chandrasekhar — `haven_evidence_auditor`, Assignment 24 — `01a0ef1f-a61b-7c60-b34a-477d91e77feb`.**
