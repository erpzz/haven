# Haven IP-01 v2 — working handoff

**REVIEWED BOUNDED PARTIAL — CODE CHANGES_REQUIRED; runtime stopped.** The original campaign stopped model admissions when ordinary Codex allowance was nearly exhausted, then the usage limit interrupted integration and review. Administrative recovery on September 29 at 21:11 UTC reverified the unchanged 37 source files, all 106 sealed QA manifest entries, and the stopped application. The original 10:10:16 UTC deadline has passed and was not renewed. The operator subsequently requested a distinct closure run: `ip01-closure-20260929T212404Z`, ending 2026-09-29T22:54:04.782931+00:00. Its four remaining assignment slots cover H00 and independent final reviews; it authorizes no new model calls or final suite starts.

The deterministic evaluation is complete. The model pilot executed and independently graded **54 of 72 calls: 45 passed, nine conservatively failed, and 18 were not executed**. Protected evaluation remains **EVALUATION_INCONCLUSIVE**. H00 and all three distinct final reviewers have returned. CODE is CHANGES_REQUIRED; VISION and EVIDENCE pass only their bounded partial scopes. All four closure native children are closed. The prior interrupted review attempts remain historical. Final delivery reconciliation is pending; unrestricted runtime acceptance is withheld.

## Run the application

The Windows Python 3.12/FastAPI/Jinja/SQLite app provides two invented people, persistent notes and revisions, explicit sharing and withdrawal, source-linked deterministic answers, saved local drafts/tasks, observable jobs and a separately gated local text/image model route. The identity selector is simulated login; local tasks have no external dispatch.

These are reference commands for a **later separately authorized deterministic visit**, using **one serialized launcher lifecycle per runtime state**, with the model gate disabled. Do not run overlapping starts/stops. This closure performs no restart. CODE found untested cleanup/readiness failure paths; the commands do not imply an all-path deadline or cleanup guarantee.

From the isolated repository root in PowerShell:

```powershell
& ./.ip01-runtime/venv/Scripts/python.exe labs/ip01/scripts/run.py start
& ./.ip01-runtime/venv/Scripts/python.exe labs/ip01/scripts/run.py status
& ./.ip01-runtime/venv/Scripts/python.exe labs/ip01/scripts/run.py stop
```

Start prints the exact loopback URL, normally http://127.0.0.1:8765, using ports 8765–8767. The [README](../../../labs/ip01/README.md) includes locked dependency setup, migration/recovery behavior, invented walkthrough notes and producer/independent test commands. The existing local environment is already prepared. The deterministic route is retained for that restricted operator-controlled visit; this is not unrestricted runtime acceptance. A restart does not reset model slots or extend the expired model gate.

The app was stopped at 07:53:50 UTC, before the original 10:10:16 UTC / 06:10:16 EDT deadline. Its model gate is disabled and the resource-stop marker remains intact. At 21:11 UTC, status again reported STOPPED with no descendants. Restart commands above are provided for the operator; no evaluation or worker was restarted during recovery.

## Evaluated identity and useful behavior

Exact evaluated-byte Git commit: `0b59551f36990cfb8a723f97da6d367358a8ceb5`. Historical execution recorded `487c67299445a29e0fbbdede04259565f741f587` plus 37 worktree hashes in [FINAL_CANDIDATE_01](receipts/FINAL_CANDIDATE_01.json), SHA256 `643d8665a546a46dca0f89e1acdc954cc69f5a30354a7f81ff06bf34524d3b30`. Fourteen historical Git blobs differed by line endings; root materialized the exact evaluated bytes without changing a worktree file. All 37 blobs and all 37 archive members were verified. Use the explicit `core.autocrlf=false` archive command in [EXACT_CANDIDATE](EXACT_CANDIDATE.md), since a default-settings archive failed the byte check. This is a reproduction repair, not another empirical test. Later administrative commits are distinct; publication receipts and Issue20 identify each pushed revision.

Independent final execution covered real synthetic database writes; private A answers, forbidden B access and explicitly shared B answers; revisions, tombstones and revocation; finite and joint grants; once-only consumption and lost-reply reconciliation; immutable receipt history; saved drafts/tasks; current restart and rollback review-only behavior. Actual Chromium workflows covered forms, source links, session races, cancellation, image import, app crash and restart. The deterministic image route explicitly refuses to pretend it interpreted pixels.

The [final deterministic report](reviews/FINAL-QA/FINAL_DETERMINISTIC_RESULTS.json) contains 150 independent checks, 38 APP/runtime seam checks using synthetic transport, 13 actual benign process fault trials, 21 evidence-oracle checks, two browser session-race cases, full browser journeys and 221 producer regression checks. The 104 authority-vector cases comprise 76 backing/configuration perturbations and 28 in-memory static faults, not 104 HTTP workflows. The 21 oracle checks comprise 13 evidence validations and eight corrupted-evidence challenges, not 21 additional process trials.

All three final suite starts are used. Suite 1 retained 145 producer setup errors while seven components passed. Suite 2 retained 214 setup errors from a missing temporary-directory parent. Suite 3 passed all 221 affected producer cases. Candidate source never changed during these harness repairs. The final result is this explicit composite, not a rewritten all-green first attempt. Independent reconciliation found none of 529 captured test-process identities still live.

Earlier independent findings led to fixes for stale session rendering, dependency depth, usable-grant selection, post-preparation model egress authorization and terminal/settlement reporting. The original findings and actual H00/owner consultations are retained. Final static reviewers must still close applicable findings at the frozen revision.

## Actual model and browser outcomes

The only artifact is qwen2.5vl:3b Q4_K_M, manifest `fb90415cde1ef08aa669ae74b082d49b158729b6db1ab183c941417d507e71a1`, with Ollama 0.34.4. [MODEL_PREPARATION](receipts/MODEL_PREPARATION.md) binds model/runtime/blob, template, preprocessing and license provenance. The CPU envelope is 4096 context tokens, 768 output tokens, one image, 120 seconds and a 12 GiB owned Job Object. Cloud-off application settings do not establish OS-level egress isolation.

Four initial readiness calls ran through actual APP authority and explicit consumption: two text and two image. Independent review found 4/4 semantically correct and 3/4 within word bounds. The one format failure and historical token-usage unknowns remain recorded.

Four actual lifecycle calls followed. Text and image cancellation exercised active computation and confirmed stop in 0.156 and 0.141 seconds. The intended natural text and image timeout trials completed normally in 55.843 and 81.453 seconds, both reaching the fixed output limit; **real-model timeout was not exercised**. No prompt or limit was changed to force a success. Benign-worker timeout was independently exercised. All model cleanup was confirmed.

The selected-image browser positive case displayed “The square is blue,” matching the inspected pixels, with one submission and one consumption. Source links rendered and reload did not replay the answer. A prior upload-response test-driver error occurred before any model submission; its failure and incomplete early browser tracking remain preserved. A versioned driver repair passed a benign upload probe before root reconciliation.

The second browser case admitted inference but failed release with `GRANT_QUOTA_EXHAUSTED`: browser retrieval also included an existing shared note. No answer was released or consumed, so unsupported-question/abstention behavior is ungraded for that case. Cleanup was confirmed and the slot remains spent. There was no retry, grant expansion, source change or hidden tuning. [READINESS_RESULTS](reviews/FINAL-QA/READINESS_RESULTS.json) records both outcomes. This limitation belongs in the final code and usefulness reviews.

The final pilot used the original 24-family/72-call protocol, explicit per-family source selection, 12 development and 12 protected families, and three scheduled repeats. Root stopped admissions to reserve the remaining allowance for reviews and shutdown. All 54 executed calls were independently graded: 45 passed and nine conservatively failed. Two of those failures involve disclosed ambiguous grounding wording. The remaining 18 calls retain NOT_EXECUTED_RESOURCE_BOUND in the original denominator; no retries, reordering or threshold changes occurred. The failed browser comparison remains a separate failure.

| Modality | Executed / scheduled | Semantically passed / executed | Median / maximum latency | Maximum job committed memory |
|---|---:|---:|---:|---:|
| Text | 30 / 36 | 25 / 30 | 13.492 / 14.218 seconds | 4.329 GiB |
| Image | 24 / 36 | 20 / 24 | 36.399 / 40.109 seconds | 4.400 GiB |

The planned supported/unsupported family comparison was not met. Incomplete repeats and observed failures remain visible; a family requires all three repeats to pass. See [FINAL_QA_HANDOFF](reviews/FINAL-QA/FINAL_QA_HANDOFF.md) and [PILOT_INDEPENDENT_REVIEW](reviews/FINAL-QA/PILOT_INDEPENDENT_REVIEW.json). Sampled RSS and committed memory are different measurements.

Protected assets are outside the candidate directory but all roles share the same host account and full-access environment. Protection is **NOT_ESTABLISHED**; protected evaluation must remain **EVALUATION_INCONCLUSIVE** even if the comparison criterion is met. No original R1, canonical P03/CORE/MF/VA/R13, production, real-account, device or physical qualification follows.

## Budgets, originals and publication

Final recorded runtime use: readiness **6/16**, lifecycle **4/8**, final **54/72**; 64 durable APP bindings, runtime claims, network-start markers and confirmed settlements; **1593.405/5400 charged model seconds**, zero unknown cleanup. The independent QA audit checked 1,255 captured identities and found no matching residuals. [FINAL_RUNTIME_SHUTDOWN](receipts/FINAL_RUNTIME_SHUTDOWN.json) records exact APP shutdown and disabled gate; model per-call cleanup evidence remains separate.

The original run dispatched **20/24** assignments; its final review handles became unavailable without confirmed verdicts. Closure assignments21–24 have now used all four remaining slots: H00 and all three distinct code, vision and evidence reviewers returned and were closed. Cumulative assignments are **24/24**, with zero remaining. Final deterministic suite starts remain **3/3**. The original two-of-four checkpoint count is preserved; the current operator amendment requires continuation boundaries A through F and material exceptions, each followed by an Issue20 reread. Acquisition is conservatively debited at **4.1/12 GiB**. Last measured combined workspace storage was **4,668,652,652 bytes / 20 GiB**. Root observed 97% weekly usage when reserving resources; the three review workers subsequently returned usage-limit errors. After the user reported resetting limits, the current tool reported 0% used and ordinary usage allowed. The agent did not redeem credits or add spending; unavailable monetary costs remain UNKNOWN. A reset does not renew the campaign deadline.

The [read-only original comparison](receipts/ORIGINAL_SOURCE_FINAL_CHECK.json) found all four inspected source files unchanged and ASTRA at its original clean revision `3aa1ac646052124b98c73d9d1f361bef3c123d81`. NIGHT01 has no identified Git checkout; this comparison does not claim a filesystem-wide snapshot. The new supervisor does not qualify original R1.

Source, sealed final QA reports, the historical run reconciliation and exact-byte reproduction receipt are published on the authorized branch and existing [draft PR21](https://github.com/erpzz/haven/pull/21). H00 closure is frozen at manifest `054eacd33074cb360fd195af6df6cc40e4a2277c92401532573c9b8c5b124121`; all three independent reviews have returned with their different scoped verdicts preserved. Main, RI-01 and PR19 metadata remain untouched. One absolute home pathname appeared in an intermediate commit and was corrected without history rewriting; [PUBLIC_REPORT_EDITIONS](receipts/PUBLIC_REPORT_EDITIONS.json) retains that disclosure. The latest root publication scan covered 437 files without pattern findings; it supplements manual review and does not prove the absence of every privacy issue. Final delivery will be checked again after its actual edits.

The broader multimodal, spatial, wearables, engineering, robotics, aircraft, emergency and Observatory ambitions remain in the cumulative RI-01 vision. This local slice does not replace them. H00 saved a final integration packet under integration/final-v1 at 07:58 and returned a frozen [closure overlay](integration/closure-v1/INTEGRATION_HANDOFF.md) at 21:40. Root verified all 94 bound inputs and four outputs. This remains synthesis for independent review, not self-acceptance. The earlier preparation-only recovery statement is corrected in receipts/H00_SAVED_FINAL_RECOVERY_CORRECTION.json.

## Returned independent reviews and retained defects

[CODE-FINAL](reviews/CODE-FINAL-CLOSURE/REVIEW.md) returned **CHANGES_REQUIRED**, accepting only the restricted bounded partial handoff. Four source-supported findings remain unresolved:

| Finding | Required retained limit |
|---|---|
| CF-F01 — P1/HIGH | A STOP_REQUESTED journal write/fsync failure can precede and bypass owned-process termination. Withhold all-path cancellation, deadline and cleanup guarantees. This was not an observed escaped workload. |
| CF-F02 — P2 | Concurrent launcher starts can overwrite recorded ownership and readiness does not bind the precise child. Later authorized visits must serialize the entire lifecycle per runtime state. |
| CF-F03 — P2 | After unconfirmed termination, a readiness-failure output-drain wait can remain unbounded. The existing UNKNOWN fixture killed its process before withholding confirmation; it did not cover a live retained pipe. |
| CF-F04 — P2 | Completed answers can retain contradictory route/queued notices. Actual job state and model payload labeling remain distinct; the finding does not invalidate B1's observed answer. |

[Retained blockers](state/RETAINED_BLOCKERS.json) records exact source references, proposed future fault checks, B2 and qualification gaps. No repair or new test is claimed for these findings. The frozen candidate is preserved because this zero-new-execution closure has consumed all24 assignments and all3 formal suite starts. A changed candidate requires a separately bounded repair and affected independent qualification.

The original CE-F01–06 counterexamples have scoped code dispositions in the review; those closures do not establish safety for CF-F01–03. Positive model-lease producer tests depend on the old gate deadline and are historical evidence, not a promise that those exact cases pass after expiry. A future test-clock correction must preserve the production gate. The separate exported deterministic harness does not require that model gate.

[EVIDENCE-FINAL](reviews/EVIDENCE-FINAL-CLOSURE/REVIEW.md) passed the integrity of the frozen evidence and honest bounded partial framing. It independently verified exact candidate/QA blobs and archive hashes, the 94 H00 inputs/four outputs and the full scheduled pilot denominator. The QA archive has 108 files; only 107 designated files (106 manifest entries plus the manifest) are sealed. Mutable STATUS.json is excluded.

[VISION-FINAL](reviews/VISION-FINAL-CLOSURE/REVIEW.md) passed retention of the broader vision and truthful partial framing. It verified canonical102REQ/102AT/32EX objects and inspected seven supplied screenshots, without starting the application. It retains two P2 product defects: B2 can spend inference and then release no useful answer; the completed B1 model view retains a hardcoded “Deterministic excerpts” badge and stale “Question queued” notice. Those defects block a general reliable image-flow claim and accurate route/progress presentation. The executable candidate remains unchanged; CODE-FINAL independently agrees with the UI finding while distinguishing correct backend disposition/payload labeling from contradictory surrounding notices. Neither review grants model readiness, protected evaluation, production or physical acceptance.

The minor stale-H00 wording and assignment-digest typo were corrected in root delivery documents without altering sealed evidence. Root final publication and exact cessation remain pending.

## Delivery status and next decision

All required independent review handbacks are received. Final operator artifact verification, publication reconciliation, exact cessation receipts and Issue20 E/F readbacks remain root delivery obligations. Source and sealed evidence remain unchanged. No model call, suite start or app restart is authorized by a usage reset, review PASS or unused historical slot.

The smallest next operator decision after this handoff is whether to authorize a separately bounded corrective package for **CF-F01–03 runtime ownership/cleanup first**, with independent benign fault tests and a new candidate binding. VISION recommends a focused source-selection/quota-feedback and route/status package; that useful path is retained, while root prioritizes the high-severity lifecycle defect. Both positions and their evidence remain visible. CF-F04/B2 should receive affected browser qualification in the subsequent bounded work. No such package is launched here.

The [current RESUME](RESUME.md), [59-item audit](state/COMPLETION_AUDIT.json), [independent review receipt](receipts/FINAL_REVIEW_RECEIPT.json) and [retained blockers](state/RETAINED_BLOCKERS.json) separate delivered evidence from unfinished qualification.
