# secpatch results: untuned baselines on real held-out security fixes (2026-10-28)

**Classification: MEASURED_ON_HELD_OUT, untuned models only.** No student has been trained. Training waits for an
approved GPU window (`gpu_window.sh`). Private per-item outputs stay on the host
(`~/.local/state/haven-secpatch/eval-regraded/`); this file holds aggregates only.

## Data actually collected

| | count |
|---|---|
| OSV PyPI advisories naming a GitHub fix commit (archive sha256 `92d85121…`) | 8,326 records → 3,879 after alias grouping |
| Fix commits fetched (TensorFlow excluded; ≤12 per repo per period) | 2,793 |
| Excluded on license at the fix commit (502 unclassifiable, 219 AGPL, 85 LGPL, 12 GPL, …) | 822 |
| Verified single-function fixes | 537 (train 270 · dev 230 · held-out 37) |
| … of which self-contained (no helper, import or other-file change) | 248 |
| Training rows (v2) | detect 540 · finding_support 810 · root_cause 253 · remediate 125 · regression_test 57 · tool_select 17 |
| Fixes where Bandit flags the vulnerable version and not the fix | 24 of 537 (4.5%) |

Leakage checks on the built data: 0 repositories shared between train and held-out. Training advisories run
2012-09-05 to 2025-06-23 and held-out ones 2025-08-25 to 2026-10-27. 2 exact duplicates and 1 near-duplicate of an
eval function were removed from training.

## Held-out evaluation: 259 items, 37 fixes, 32 repositories never trained on

Deterministic grading against recorded ground truth, greedy decoding, one seed. Run on CPU while the interactive
35B had priority (CPUWeight 1 vs 100), so latencies are not throughput numbers.

| arm | detect | finding support | root cause (CWE) | remediate, plausible¹ | recall | FPR on fixed code | paired detect | invalid JSON |
|---|---|---|---|---|---|---|---|---|
| **floor** (same answer every time) | 37/74 | 74/111 | — | — | — | — | — | — |
| Qwen3.5-4B Q4_K_M | 38/74 | 76/111 | 4/36 | 14/37 | 0.19 | 0.11 | 0.11 | 6 |
| Qwen3-0.6B base `c1899de` | 32/74 | 69/111 | 0/36 | 0/37 | 0.84 | 0.81 | 0.03 | 13 |

¹ It parses, keeps the signature, changes the code and does not re-trigger the Bandit rule the original fix cleared. This
is **not** evidence that the patch fixes the issue, and none matched the recorded fix. On the 18 self-contained fixes the
4B scores 5/18. 20 of the 4B's answers had copied the prompt's line-number gutter; the grader now strips a gutter that
appears on every line (`gutter_stripped`), which moved the score from 6 to 14. The 0.6B answered remediation requests
with JSON instead of code.

### With executed Bandit evidence in the prompt (judgment tasks, identical 186 items)

| arm | detect | finding support | tool_select | recall | FPR | paired | items gained / lost vs plain |
|---|---|---|---|---|---|---|---|
| 4B plain | 38/74 | 76/111 | 0/1 | 0.19 | 0.11 | 0.11 | |
| 4B + Bandit | 39/74 | 74/111 | 1/1 | 0.16 | 0.08 | 0.08 | 6 / 6 |
| 0.6B plain | 32/74 | 69/111 | 0/1 | 0.84 | 0.81 | 0.03 | |
| 0.6B + Bandit | 31/74 | 72/111 | 1/1 | 0.11 | 0.14 | 0.03 | 41 / 38 |

## What this shows

* Both untuned models are at the trivial floor on vulnerability judgment for real, previously unseen fixes. The 4B
  is conservative and rejects most findings: it accepts 8 of 37 that are genuinely supported. The 0.6B flags almost
  everything.
* Neither model names the advisory's CWE when it does detect a vulnerability (0 of 7 for the 4B, 0 of 31 for the 0.6B).
* Static-tool evidence is not a shortcut. Bandit catches about 4.5% of these vulnerabilities, so "no issues" is the
  usual evidence. The 0.6B follows it mechanically: recall drops from 0.84 to 0.11 with accuracy unchanged. The 4B is
  unaffected (6 items gained, 6 lost). A tools-plus-retrieval arm needs better evidence than Bandit alone.
* A trained student must beat these floors on the same held-out ids, with false positives not rising, before
  `registry.py promote` will accept it.

## Repository-level validation (pass 1, before the isolation gate)

Of 23 held-out fixes that shipped tests: 8 regression tests are validated (pass on the fix, fail on the vulnerable
parent by assertion, e.g. Datasette `'//nastyOpenRedirect' == '/nastyOpenRedirect'`). 10 projects' own tests did not
run in this environment (missing dev dependencies or system libraries), and 5 failed to install. For 4 of the 8
validated fixes, the recorded fixed function alone passes. The other 4 also needed a helper or import outside the
function, which is the evidence behind the v2 self-contained rule.

This pass executed third-party code on the Slink host without OS isolation. A post-run check found no changes to
`~/.ssh`, shell rc files, crontab or user units; that is evidence, not proof. `repo_eval.py` now refuses to run without
`--acknowledge-isolated-runner` (#80). Model patches have **not** been tested at repository level.

## Not done

* Training: no GPU window approved. The CPU pipeline check passed (2 steps, 5.2 GiB, about 100 s/step).
* A larger baseline through the Haven gateway (35B): skipped by owner decision to keep interactive chat responsive.
* Repository-level testing of model patches: needs an OS-isolated runner.
* Multiple seeds: these baselines used greedy decoding; seed variance applies to the trained arms.
* Recovery training rows: none. The only recovery events came from held-out repositories.
