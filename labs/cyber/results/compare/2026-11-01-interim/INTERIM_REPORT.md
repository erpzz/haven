# Interim comparison: untouched Qwythos v2 vs Adapter B (secpatch c001)

**Status: informational only** (pre-registration amendment 2). No selection is made from this window. The decision-grade comparison is a three-way run that includes Adapter A, once its GGUF exists (~6 days; Kaggle quota exhausted).

## Conditions (from `runs/receipt.jsonl`)

- Slink, llama.cpp b11146, identical flags (`-c 24576 -np 1 --threads 12 -b 2048 -ub 2048 -fa auto --jinja`).
- The forge teacher and its timer were paused for both runs; the whole model fits on the GPU.
- Harness `VERSION` 11e865b (frozen since the baselines). Scenarios and answers are v1, hashes in the receipt.
- **Integrity:** every model was hashed by direct IO and through the page cache, before and after its run. 6/6 checks matched the known-good sha256:
  - base `cfdd00ac…`: the clean copy that replaced the bit-flipped one;
  - adapter-B `38cea636…`.
- **Adapter B's first attempt** crashed at the first request with `CUDA error: an illegal memory access` (the known intermittent b11146 crash). Its 185 error rows are kept in `runs/_failed-attempt1/`. The re-run with the hardened runner completed with 0 errors.

## Primary: held-out, condition C, thinking off (n = 20)

| | Pass | False positives (of 4 eligible) | Tool calls | Mean latency |
|---|---|---|---|---|
| base | **16/20** | 1 | 0 | 2.8 s |
| adapter-B | 13/20 | 2 | 0 | 3.8 s |

- **Net:** −3 (gain ca-02; losses ca-06, ca-09, net-02, rbac-05). One-sided p = 0.97.
- **Generalization (T2+T3) net:** −2.
- **Pre-registered criteria:** B fails #1 (gain), #2 (generalization) and #3 (false positives), and passes #4, #5 and #6 (thinking on: 15/20 against 16/20).
- **Interim outcome: retain untouched Qwythos.**

## All conditions, all 55 cases (descriptive)

| Condition | Base pass | B pass | Base false positives (of 15) | B false positives |
|---|---|---|---|---|
| A | 38 | 34 | 3 | **6** |
| B | 36 | 38 | 3 | 4 |
| C | 42 | 38 | 2 | 3 |

- **Regressions** (base ✓ → B ✗, condition C, all cases): ca-06, ca-09, net-02, rbac-05, ca-12, net-01.
- **B over-flags.** It raises more false positives in every condition, most in A (6 against 3). That matches the forge session's own secpatch regression check (FPR 0.405 against 0.081).
- **B never calls tools either.** That's expected: its training had no function-calling rows.

## Effect of the RAM bit flips on the earlier baselines

The clean base re-run gives the same verdict as the bit-flipped baseline on:
- 55/55 cases in A, 53/55 in B and 54/55 in C (thinking off);
- 18/20 held-out C cases with thinking on.

Pass counts: A 38 = 38, B 36 against 38, C 42 against 41. The handful of flips sits within the run-to-run variation you would expect from a different GPU offload (the earlier baseline shared the card, this one did not). The three flipped bits **did not materially change** the baseline results, though they are still labelled as run on a corrupted file.

Latency note: with the full model on the GPU (teacher paused), condition C thinking off averages 2.96 s per item, against 7.6 s in the shared-card baseline.
