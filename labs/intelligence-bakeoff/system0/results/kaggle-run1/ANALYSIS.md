# Kaggle run 1: HARE-S0-1 and HARE-S0-2 results

**Executed.** Kaggle notebook `yahboyomni/haven-hare-s0` v2 (private), launched through the API at 2026-11-21 22:51 ET and complete before 05:46 ET on 11-22.
- **Hardware:** 2× Tesla T4 (CUDA 13.0.88, driver 580.178.04). The 4B ran on GPU0; the 35B was layer-split across both GPUs (Slink instead keeps its experts on the CPU).
- **Engine:** llama.cpp b11146, the hash-checked portable build from the private dataset `yahboyomni/haven-llama-b11146-cuda13-sm75`, run with round-2 server arguments.
- **Models:** pinned GGUFs, 4B `00fe7986…` and 35B `ac0e2c11…`. Temperature 0, thinking off, one greedy run per arm.

**Receipt integrity.** All 13 arms scored exactly their expected episode-ID sets (180 frozen, 179 fresh, 179 untouched). Code hashes match both preregistrations, and record files match their recorded sha256 (in `corrected_false_refusals.json`). Transcripts (`*.jsonl`) are kept out of the repository; summaries hold per-episode scores. Non-transport episodes are all `MAX_TOOL_ROUNDS` (the model looping), scored as failures as in round 2.

## HARE-S0-1 (registered): advisory System 0 for the 4B

| | Frozen 180 | Fresh 179 |
|---|---|---|
| 4B plain | **58** (round 2 on Slink: 58; reproduced across hardware) | 60 |
| 4B + System 0 | **83** | 75 |
| Paired gained / lost | 29 / 4, sign test p = 1.1e-5 | 23 / 8, p = 0.011 |
| 35B plain, same host | 123 | — |
| 35B + System 0 | 132 | — |

Preregistered verdict:
- **H1:** pass.
- **Replication direction:** pass.
- **Harm guard:** pass (no family net −3).
- **Calibration:** Δ 0 versus round 2.
- **H2 accuracy:** fail (83 vs 35B 123; the bar was ≥ 113).
- **H2 latency:** fail (4B+S0 5.58 s/episode vs 35B 4.75 s on this host).

By S0-1's adoption rule, System 0 qualifies as an advisory layer, but the 4B does not replace the 35B.

**Where the gain comes from.** `execute_refusal` went 0 → 12 on the frozen set and 1 → 12 on the fresh set (corrected after assurance review; the earlier text said "0 → 12 on both sets"); that is the request classifier. Without that family, the gain is +13 on the frozen set and **+4 on the fresh set**. The frozen gains in `stale_premise` (2→8) and `conflict_rule` (3→8) did not replicate (4→4 and 5→5 on fresh). The advisory checks mostly work through one suite-aware rule.

## HARE-S0-2 (registered separately): enforcement, verification, correction (179 untouched episodes)

| Arm | System pass | Raw pass | Model-clean | Blocked auth. attempts (episodes) | False refusals* | s / request |
|---|---|---|---|---|---|---|
| 4B plain | 55 | — | — | — | 4 | 5.54 |
| 4B advisory (S0) | 71 | — | — | — | 3 | 5.46 |
| 4B enforce (gateway) | 75 | 75 | 60 | 32 (23) | 6 | 5.52 |
| 4B verify + 1 correction | 95 | 55 | 95 | 0 | 4 | 7.18 |
| **4B full** | **126** | 81 | 118 | 12 (9) | 3 | 6.49 |
| 35B plain | 127 | — | — | — | 0 | 4.56 |
| **35B full** | **146** | 139 | 143 | 13 (6) | 0 | 4.86 |

\*Corrected false refusals: see "Defect found in the analysis" below.

| Versus 4B plain | Gained / lost | p | Family net −3? | False refusals vs plain | Rule verdict |
|---|---|---|---|---|---|
| advisory | 21 / 5 | 0.0025 | none | −1 | **supported** |
| enforce | 20 / 0 | 2e-6 | none | +2 | **supported** (as boundary, not competence: model-clean 60) |
| verify | 40 / 0 | <1e-6 | none | 0 | **supported**; verifier false alarms 0/55 on raw passes, fail-recall 71/118 |
| full | 72 / 1 | <1e-6 | none | −1 | **supported** |

**Non-inferiority to the 35B on the same host** (margin −0.10, paired one-sided 95% bound):
- **4B full vs 35B plain, system pass:** 126 vs 127, diff −0.006, bound −0.066. **Non-inferior.**
- **4B full vs 35B plain, model-clean pass (sensitivity, stricter):** 118 vs 127, diff −0.050, bound −0.113. **Not non-inferior.**
- **Offline cascade** (4B full, unresolved → independent 35B full; model loading excluded): 131, with 8 escalated, at 6.83 s/request. Non-inferior (bound −0.040).

**Latency on this host:** every 4B arm is slower than the 35B. The hardware was not symmetric: the 4B ran on one T4, while the 35B-A3B was offloaded across two T4s (about 3B active parameters) decodes faster than the dense 4B here. **35B full dominates the 4B systems on both accuracy (146) and latency (4.86 s).** Slink's balance is different (35B experts on CPU at 35 tok/s vs the 4B at 94 tok/s) and has not been measured for these arms. Under the assurance rule, the latency gate is judged only on the target host.

## Where the gains come from (honest accounting)

1. **Verifier:** 38 of the 39 successful corrections in the verify arm, and 45 of 45 in the full arm, were triggered by **V6** ("a value read from a tool must be labelled `supported`, not `direct`"). This is real contract compliance, but it is a representational fix that overlaps the adjudicator's status checks. It improves the grade more than the reasoning.
2. **Gateway:** it blocks unrequested proposals and probes of unnamed owners. That gives a higher system pass, but 23 episodes still contain a blocked authorization attempt by the 4B (model-clean 60 vs system 75).
3. **Advisory:** the execute-request flag carries most of it (see S0-1).
4. **The scaffolding helps the 35B too:** 127 → 146 (+19).

## What remains lost (4B full vs 35B full, /12)

`conflict_report` 0 vs 6 · `missing_admit` 6 vs 11 · `no_tool` 6 vs 10 · `chain3_conditional` 7 vs 9 · `household_denied` 3 vs 5 · `conflict_rule` 8 vs 10.
These are the language and judgement failures (conflicting sources, admitting missing evidence, answering without tools) that the rules cannot express. This matches the development taxonomy.

## Defect found in the analysis (not in the run)

`bench_x.expected_statuses` read a top-level `expect` key that does not exist in this episode format (expectations live in `contract.expect_claims`). It therefore counted every refusal, including correct refusals in `execute_refusal`, as false. The raw field in the extension summaries reads 4 / 15 / 17 / 4 / 15 / 9 / 12. Recomputed from transcripts with the correct field it is 4 / 3 / 6 / 4 / 3 / 0 / 0 (`corrected_false_refusals.json`). Pass/fail, the adjudicator and the run are unaffected. The fix to `bench_x.py` is a separate post-run commit; it changes that file's registered hash, so future runs need a new registration.

## Limits

- The untouched set is new worlds from **the same generator templates**, and the checks and verifier were written knowing the families. This is not evidence about analyst wording.
- Three verifier rules (V2, V3, V7) and V6's labelling overlap what the grader rewards.
- The deciding external test is the assurance lane's reserve (#117).
- One greedy run per arm; the hardware is not the deployment host.

## What I conclude

- **On these episodes, deterministic scaffolding is the largest lever among the comparisons run**, and it lifts both models: 4B 55 → 126, 35B 127 → 146. V6 triggered all 45 successful full-arm corrections; trigger counts cannot show whether changing only the label would have sufficed.
- **Much of the 4B's lift is format and boundary, not reasoning.** The model-clean numbers and the V6 share say so.
- **On this hardware, "4B plus scaffolding instead of the 35B" buys nothing:** the 35B is both better and faster. Whether the 4B system earns its place depends on the target host's latency, which must be measured there.
- **The next research target is the epistemic failures in the table above.** That is the only place a better model, a specialist or a decision model could add value over code.

## Assurance decision (issue #117, 2026-11-22)

The assurance lane independently paired the public summaries and reproduced the bounds: 4B full vs 35B plain has 21 wins / 22 losses on system pass (bound −0.066) and 19 / 28 on model-clean pass (bound −0.113).
- **Accepted:** the system-level improvement on this suite.
- **Model-clean non-inferiority:** inconclusive.
- **Not independently replayed:** the false-refusal correction, which is a disclosed post-run regrade from transcripts.
- **Decision:** this GPU comparison is closed, and **35B full (146/179, 4.86 s mean) is the measured Kaggle reference**.
- **Still open:** deployment-host p95 and accuracy on analyst questions.
