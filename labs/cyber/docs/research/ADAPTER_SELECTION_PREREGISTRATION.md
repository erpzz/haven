# Adapter selection pre-registration (frozen before any adapter result)

Written 2026-10-31, before either Kaggle adapter existed as a GGUF and before any adapter output was seen. The commit that adds this file is the timestamp. Any later change is appended as a dated amendment with its reason; nothing above an amendment is edited.

## Candidates

| Label | Model | Source |
|---|---|---|
| **base** | Qwythos-9B-v2, `Qwythos-9B-v2-MTP-Q4_K_M.gguf`, untouched | the GGUF used for the A/B/C baseline |
| **adapter-A** | Qwythos-9B-v2 + agent-reliability LoRA v1, merged, Q4_K_M | Kaggle `haven-forge-train-qwythos-agent-v1` (forge session) |
| **adapter-B** | Qwythos-9B-v2 + secpatch code-review LoRA c001, merged, Q4_K_M | Kaggle `haven-forge-train-qwythos-c001` (forge session) |

## Controlled conditions

- One host (Slink), one llama.cpp build (b11146), identical server flags: `-c 24576 -np 1 -b 2048 -ub 2048 -fa auto --jinja --threads 12`, auto-fit GPU layers. One model loaded at a time, run back to back.
- **base is re-run** in the same window; the earlier baseline is not reused for the decision. Per-case agreement between the re-run and the original baseline is reported as a reproducibility check.
- The co-tenant forge teacher's state (idle / active) is recorded per run.
- Harness, scenarios and answers are frozen at the commit that adds this file. sha256 values of `eval/scenarios/v1.json` and `eval/answers/v1.json` go into the receipt.
- Temperature 0; the same max tokens as the baseline (1,536 thinking off; 8,192 thinking on).

## Cases and metrics

- **Frozen held-back cases**: the 20 `split=heldout` scenarios of v1. Dev cases (35) are run and reported, but **are not used for the decision**.
- **Primary metric**: held-out pass count in **condition C (retrieval + tools), thinking off**. That is the configuration the agent adapter targets and the fast path the owner wants.
- **Secondary**: held-out condition C with thinking on, and all conditions on all cases (descriptive).
- Reported per case and per model:
  - correctness;
  - **tool-call success**: calls made, share returning without error, applicable tool used, hallucinated tool names;
  - **abstention accuracy**: correct "cannot determine"/unknown where expected, and false abstentions elsewhere;
  - latency (mean and median per item);
  - false positives on trap scenarios;
  - unparsed answers;
  - **regressions** (base passes, adapter fails).

## Provenance classes (to separate training-target gains from generalization)

Each scenario is assigned one class **before** adapter results are read, from the forge session's disclosure:

- **T1, training-targeted.** The scenario's specific failure pattern, or the scenario id, was communicated to the training side, and the training data contains that pattern.
  - Items named to the forge session so far: tf-01, rbac-01, lg-01 (handoff); ca-01, ca-02, ca-03, rbac-04, tf-03, idp-04, lg-01, lg-02, fp-02 (baseline message).
  - A named item counts as T1 only if the data contains its pattern. Named held-out items (ca-02, lg-02, fp-02) are T1 and **excluded from generalization claims**.
- **T2, in-family.** The category is covered by a training family (ca, rbac, lab-host/tool), but the pattern was not disclosed.
- **T3, out-of-family.** No training rows for the category (identity, cloud, graph, network, logs, fp, os). Gains here are generalization, for example transfer of the tool-use habit.

Gains are reported separately for T1, T2 and T3. Only **T2 + T3 held-out** gains count as unseen generalization.

## Decision rule

An adapter is **convincingly better** than base only if **all** of the following hold, compared with the base re-run:

1. Held-out C thinking-off: net gain ≥ +3 of 20, with exact one-sided McNemar p ≤ 0.10 on the paired held-out cases.
2. The gain survives excluding T1 cases. Net gain on held-out T2 + T3 ≥ +2, so the improvement is not only on disclosed targets.
3. False positives on held-out traps ≤ base.
4. Out-of-family (T3) held-out regressions ≤ 1 case.
5. Unparsed held-out answers ≤ base.
6. Secondary check: held-out C thinking-on pass ≥ base − 1.

- **Both qualify:** recommend the one with the larger held-out gain. On a tie, prefer fewer regressions, then lower latency.
- **Neither qualifies:** **retain the untouched base**.
- **Recommendation only.** No serving configuration, catalog entry, Hermes setting or forge champion pointer is changed by this evaluation.

## Preservation

- All three GGUFs stay on Slink, with sha256 recorded.
- Evaluation rows (`results.jsonl`), summaries, server command lines, the teacher state and harness commit go into `labs/cyber/results/compare/<date>/receipt.json`, committed to the PR.
- Training provenance (kernel ids and versions, data and generator commits, dataset sha256, config, losses, disclosure) is copied from the forge session into the same folder.

## Amendment 1 (2026-10-31, before any adapter output)

- **Classes.** Provenance classes are frozen in `results/compare/2026-10-31/classes.json`, from the forge session's disclosure.
  - The CA training family was modelled on the generators behind the eval fixtures, so **all CA scenarios are T1**, along with rbac-01, rbac-04 (design-overlapping) and tf-01.
  - Held-out: T1 5, T2 2, T3 13. Criterion 2's generalization set is therefore the 15 held-out T2+T3 cases.
- **Secondary control.** The thinking-on check (criterion 6) uses a **base re-run** of held-out condition C with thinking on, in the comparison window under identical conditions. The earlier thinking-on baseline is reported, not used for the decision.
- **Teacher idle.** The forge teacher and its timer are paused for the whole window (`scripts/run_compare_slink.sh`, restored on exit), so all three models see the same GPU state.

## Amendment 2 (2026-11-01, before any adapter output was seen)

- Adapter A cannot exist for ~6 days (Kaggle quota exhausted; three training attempts failed with OOM). Adapter B has landed.
- **Interim window (informational only).** Run base vs adapter-B now, under exactly the conditions of this document: same Slink harness deployment (`VERSION` 11e865b, unchanged since the thinking-on baseline), same server flags, teacher paused. The criteria are computed and reported for B, but **no selection is made from the interim window**.
- **Decision window.** When Adapter A's GGUF lands, run base, adapter-A and adapter-B back to back in one window, re-running base and B, and apply the decision rule to that window only. If A never lands, a base-vs-B decision may be taken from a fresh window run at that time; this is a stated future amendment, not done now.

## Amendment 3 (2026-11-01, before any adapter output was seen): host memory fault

- **Finding.** The base GGUF used for both A/B/C baselines on Slink was not the upstream file. Its sha256 is `7d68ba92…`, against the upstream LFS oid `cfdd00ac…`, which the Mac copy of commit `97c11b0` matches.
  - It differs by **three single-bit flips** (offsets 2211447204, 2382294632, 3631800168).
  - Two flips are on disk. The third exists only in the page cache (the O_DIRECT read is correct), which shows bits flipping in RAM.
  - Slink registers no EDAC/ECC memory controller.
- **Consequences.**
  - The thinking-off and thinking-on baselines were measured on a 3-bit-corrupted base. They remain reported, labelled as such, and are **not** used for any decision. The base re-run in each comparison window uses a **verified clean copy** (`~/.local/state/haven-cyber/models/Qwythos-9B-v2-MTP-Q4_K_M.cfdd00ac.gguf`). The difference between the two base runs gives a rough measure of the flips' effect.
  - The runner now hashes every model through O_DIRECT and through the page cache, before and after its run, against a known-good sha256 (`receipt.jsonl`, event `integrity`). A mismatch marks that model's run compromised; it is re-run or reported as such.
  - Adapter B was verified intact on Slink's disk by the forge session (direct-IO sha `38cea636…`, equal to a fresh Kaggle download on the Mac).
- **Owner action needed:** memtest86+ and a BIOS memory-profile check (physical access and a reboot). Until then, every Slink result carries this caveat.
