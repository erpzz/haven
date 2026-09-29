# Haven IP-01 v2 — working handoff

**BOUNDED PARTIAL — runtime stopped; required final reviews incomplete.** The original campaign stopped model admissions when ordinary Codex allowance was nearly exhausted, then the usage limit interrupted integration and review. Administrative recovery on September 29 at 21:11 UTC reverified the unchanged 37 source files, all 106 sealed QA manifest entries, and the stopped application. The original 10:10:16 UTC deadline has passed and was not renewed. The operator subsequently requested a distinct closure run: `ip01-closure-20260929T212404Z`, ending 2026-09-29T22:54:04.782931+00:00. Its four remaining assignment slots cover H00 and independent final reviews; it authorizes no new model calls or final suite starts.

The deterministic evaluation is complete. The model pilot executed and independently graded **54 of 72 calls: 45 passed, nine conservatively failed, and 18 were not executed**. Protected evaluation remains **EVALUATION_INCONCLUSIVE**. H00 saved final documents were recovered, but their native final handback is unconfirmed; final code and vision verdicts were interrupted, and final evidence review was not dispatched. This is not final acceptance.

## Run the application

The Windows Python 3.12/FastAPI/Jinja/SQLite app provides two invented people, persistent notes and revisions, explicit sharing and withdrawal, source-linked deterministic answers, saved local drafts/tasks, observable jobs and a separately gated local text/image model route. The identity selector is simulated login; local tasks have no external dispatch.

From the isolated repository root in PowerShell:

```powershell
& ./.ip01-runtime/venv/Scripts/python.exe labs/ip01/scripts/run.py start
& ./.ip01-runtime/venv/Scripts/python.exe labs/ip01/scripts/run.py status
& ./.ip01-runtime/venv/Scripts/python.exe labs/ip01/scripts/run.py stop
```

Start prints the exact loopback URL, normally http://127.0.0.1:8765, using ports 8765–8767. The [README](../../../labs/ip01/README.md) includes locked dependency setup, migration/recovery behavior, invented walkthrough notes and producer/independent test commands. The existing local environment is already prepared. The deterministic route remains usable after the campaign. A restart does not reset model slots or extend the expired model gate.

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

The original run dispatched **20/24** assignments; its final review handles became unavailable without confirmed verdicts. Closure task21 is distinct H00; the remaining three slots are reserved for distinct code, vision and evidence reviewers. Final deterministic suite starts remain **3/3**. The original two-of-four checkpoint count is preserved; the current operator amendment requires continuation boundaries A through F and material exceptions, each followed by an Issue20 reread. Acquisition is conservatively debited at **4.1/12 GiB**. Last measured combined workspace storage was **4,668,652,652 bytes / 20 GiB**. Root observed 97% weekly usage when reserving resources; the three review workers subsequently returned usage-limit errors. After the user reported resetting limits, the current tool reported 0% used and ordinary usage allowed. The agent did not redeem credits or add spending; unavailable monetary costs remain UNKNOWN. A reset does not renew the campaign deadline.

The [read-only original comparison](receipts/ORIGINAL_SOURCE_FINAL_CHECK.json) found all four inspected source files unchanged and ASTRA at its original clean revision `3aa1ac646052124b98c73d9d1f361bef3c123d81`. NIGHT01 has no identified Git checkout; this comparison does not claim a filesystem-wide snapshot. The new supervisor does not qualify original R1.

Source, sealed final QA reports, the historical run reconciliation and exact-byte reproduction receipt are published on the authorized branch and existing [draft PR21](https://github.com/erpzz/haven/pull/21). Closure integration and independent reviews remain in progress. Main, RI-01 and PR19 metadata remain untouched. One absolute home pathname appeared in an intermediate commit and was corrected without history rewriting; [PUBLIC_REPORT_EDITIONS](receipts/PUBLIC_REPORT_EDITIONS.json) retains that disclosure. The latest root publication scan covered 437 files without pattern findings; it supplements manual review and does not prove the absence of every privacy issue. Final delivery will be checked again after its actual edits.

The broader multimodal, spatial, wearables, engineering, robotics, aircraft, emergency and Observatory ambitions remain in the cumulative RI-01 vision. This local slice does not replace them. H00 saved a final integration packet under integration/final-v1 at 07:58; closure will verify and rebind it before independent acceptance. The earlier preparation-only recovery statement is corrected in receipts/H00_SAVED_FINAL_RECOVERY_CORRECTION.json.

## Remaining work

Required final H00 integration and distinct code/vision/evidence reviews remain incomplete. Eighteen original pilot calls remain unrun. The operator has now requested bounded closure. Exact candidate publication is complete; the next work is H00 closure and independent final review of this partial result; the 18 unrun calls are retained as a limitation. No runtime or review worker will be restarted solely because account usage reset. Publication and static handoff recovery preserve the saved result without claiming the missing reviews passed. The [current RESUME](RESUME.md) and [59-item audit](state/COMPLETION_AUDIT.json) record the exact gaps.
