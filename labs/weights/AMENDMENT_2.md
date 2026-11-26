# Amendment 2 to the W1/W2 weight training plan

Amends `labs/weights/PLAN.md` (`667bd3a`, sha256 `119930a934de1a7a4a58c4b6624bc4c3094090d2d1a739a3e1025df2bd086720`) as already amended by `labs/weights/AMENDMENT_1.md` (`63bcd6e`, sha256 `cb7954a2c384059e1acbcc904b5356f0a57e0bcb287a41160274691b124a1a1b`). Both files stay unchanged. Where they conflict with this one, this amendment wins.

Written by Claude on 2026-11-22. The owner delegated to the Claude lead the four questions left open in the Phase 0 report on [#123](https://github.com/erpzz/haven/issues/123). Status: **PROPOSED, NOT_EXECUTED.** No training, inference or GPU time has been spent, and no results of any kind exist. Astra may change any of this as reviewer before GPU time.

These decisions do not replace two independent checks. Astra's sign-off on the amended plan, and an independent human review of an accepted M4 reserve on #119, are still required before batch 1 or any GPU time.

## D1. W1 keeps model-clean attempts only

This replaces PLAN.md W1 Stage A step 3, and the corrected-attempt handling in the Phase 0 report.

- **Keep rule.** A W1 attempt is kept only if:
  - its *first* answer, scored on the trace at that point, passes the adjudicator against gold (Amendment 1's model-clean view); and
  - the attempt has zero blocked or duplicate calls anywhere; and
  - transport succeeded.

  An attempt that passes only after a verifier correction is not training data. It counts in the corrected-model view only.
- **Truncation.** Training rows cover the model's own turns up to and including that first answer. Nothing after a verifier message is ever a training target or prefix.
- **Selection.** At most 2 kept attempts per episode, taken in attempt order. The verifier's verdict does not choose between passing attempts.
- **Gate G1** uses this kept rate over all attempted rollouts, with the corrected-model and final-system rates published beside it.

**Why:**
- The weights claim rests on model-clean outcomes, so the training data should be model-clean too. Teacher traces already are (Amendment 1, section 5).
- Training on post-correction turns would teach the 4B to depend on the verifier's feedback. That is the failure Astra named in D: the harness supplies the part that makes the answer correct.
- The verifier also stays out of data selection, consistent with keeping it out of the RL reward.

## D2. Rule 4: no change

Rule 4 stays as Amendment 1 states it. The trained arm must stay within 2 absolute percentage points of a paired stock baseline on each benchmark, judged on the point estimate. The paired 95% interval and the denominators are published beside every delta. No retries, re-runs or noise carve-outs are allowed.

**Why:** IFEval's 541 prompts make a chance drop of about 2 points possible. But a false stop only produces a negative result on record, while loosening the margin would weaken a safety gate after the builder had seen the risk. Decoding is greedy, with a fixed seed and an identical serving path, which already removes sampling noise.

## D3. Reserve-collision check: two stages, pass/fail only

This makes Amendment 1 section 2 ("Reserve collisions") concrete.

| Stage | When | What Claude gives Astra's reserve context | What Astra returns |
| --- | --- | --- | --- |
| 1 | After a training pool is generated and before any batch from it | Hashed fingerprint of what round 0 reveals anyway: each item's request text and authenticated principal (`dedupe.py export-fingerprint --scope prompts`) | PASS or FAIL |
| 2 | After the pool's last teacher batch is sealed and its gold revealed, and before any training run uses the pool | Hashed fingerprint of the full items: request, note texts, causes, entity ids and structure keys (`--scope full`) | PASS or FAIL |

- **Before stage 2, no fingerprint contains note texts or causes.** Hashes over a small templated value space could be brute-forced, which would let anyone with the hashes see tool outputs early and undo the stepwise exchange.
- **A FAIL discards the whole pool.** The pool is regenerated from a fresh secret seed, all traces from it are dropped, and both stages run again. Astra never names the matching items. Claude never sees reserve content or reserve hashes.
- **Separate contexts.** The fingerprints go to Astra's reserve context only, never to its teacher context.

## D4. Private store (operational)

Seeds, salts, gold before reveal, and training-pool manifests live in one owner-held place:
- **Canonical copy:** `~/haven-private/weights/<pool>/` on the owner's Mac. It sits outside every Git checkout and outside any folder synced to ChatGPT or Astra.
- **Kaggle copy:** a private Kaggle dataset holds only what a notebook needs, such as the episode file, and no salts.
- **Never before reveal:** the public repository, issue comments, or Astra's Library or any ChatGPT context.
- **How it gets there:** the Claude session writes these files through the desktop bridge when the chat is linked. Otherwise it sends them to the owner to save there.
- **Each reveal** (seed, salt, gold or manifest) is posted on #123 with a verification command, and the commitment must check out.

## Handback metadata

- Task issue: #123. Base: `63bcd6e` on `claude/weights-plan-20261122` (PR #124).
- Output: `labs/weights/AMENDMENT_2.md` (new file; PLAN.md and AMENDMENT_1.md unchanged). Implementation: PR #125 (Phase 0).
- Tests: NOT_EXECUTED for the plan itself. The Phase 0 code changes are tested in PR #125.
- Publication: public-safe. Review requested from Astra on #123. No self-approval.
