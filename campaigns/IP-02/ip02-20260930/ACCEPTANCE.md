# IP-02 acceptance — useful behavior plus independent fault evidence

These are required scenarios and evidence definitions, not claims they have run. Independent QA owns executable cases and expected results; candidate authors do not grade themselves. Record exact candidate, input/config identity, actual command/browser action, expected observation, actual result, artifacts, failure/recheck history and applicability. A screenshot proves visible pixels, not the transition, authorization or process cessation by itself.

## A. Runtime gate before any model admission

| Case / finding | Required executed observation on isolated benign work |
|---|---|
| R1 / CF-F01 | Inject STOP_REQUESTED journal write and fsync failure while an exactly owned worker is still live. Termination/observation and lease handling are reached despite logging failure. Observe actual residuals; retain UNKNOWN/quarantine if termination is not established. Include a no-fault positive control and persistent-journal-failure case. |
| R2 / CF-F02 | Synchronize competing launcher processes on one new evaluator runtime directory. Exactly one owner is admitted; no overwritten/lost owner or second live app shares the state. Bind HTTP readiness to the launched child/instance, reject a wrong-instance response, and verify normal stop covers the admitted ownership. Test owner crash/recovery without erasing uncertain live ownership. |
| R3 / CF-F03 | Under independent outer containment, keep an owned benign process/output pipe live while stop confirmation is withheld. The adapter returns within its frozen drain deadline without waiting forever for EOF; supervisor propagates UNKNOWN/quarantine and blocks new admissions. A fixture that kills the process first does not cover this case. |
| R4 / original boundaries | Recheck cancel-before-start/during-work, timeout, worker crash, parent death, stale/duplicate result, fresh egress denial, terminal-versus-cleanup state and capacity. Include unrelated-process controls and real APP callback wiring where affected. Stub-only authority is insufficient for integration claims. |

Freeze stop targets before measured trials; carry forward the prior 3-second runtime / 20-second app targets where topology is unchanged. If topology differs, justify and freeze a target before trials; never lengthen it after a failure to pass. A separate bounded outer observer cleans up only exact owned identities. Record when the outer observer, rather than repaired runtime, performed termination: that is not a passing runtime cleanup result.

R1–R4 plus independent source review must support the new operational gate. Baseline reproductions require containment first. Missing safe baseline reproduction remains explicit; source-supported historical findings must not be relabeled observed. Model gate remains disabled until affected closure is earned.

## B. Required end-to-end user journeys

**U1 — Current fact to useful local next step.** In a real browser session, invented Person A creates a private note, asks an answerable question, follows the source/revision link and saves/edits a local draft or task. Correct the note and ask again: new output uses the current version, with old history distinguished. Reload/current restart preserves the intended state without replaying a consumed answer. No external task execution is implied.

**U2 — Deliberate two-person sharing.** Independent A/B sessions prove B cannot retrieve A's private content by UI or direct HTTP. A explicitly shares eligible content; B obtains a useful supported answer. Withdraw/correct an influencing source during queued/running work and verify stale output is not newly released. Preserve finite/joint grants, all influencing ancestors and once-only consumption. Session switching must not render the prior person's delayed response.

**U3 — Selected image without incidental-context failure.** Select an artificial PNG/JPEG, visibly choose image-only or image-plus-eligible-note scope, and ask a supported question. The actual model answer, route, source references and completed status agree. An unrelated exhausted note must not silently contaminate the sealed request. A deliberately selected ineligible source receives useful pre-admission feedback where determinable, with zero inference. An unsupported attribute receives a genuine grounded uncertainty response when the eligible model path runs; a release denial with no output is not an abstention pass.

**U4 — Understand failure and regain control.** Exercise cancellation, failure, denied request, unknown cleanup, overlapping requests, session switch and reload. An old completion cannot erase a newer operation's status. Next-request route controls do not relabel an older result. Show job disposition separately from whether compute actually stopped. Evidence must include real browser actions and server observations, not just an offline rendering.

Run U1/U2 and deterministic parts of U4 even if inference is blocked. The deterministic route must not claim pixel interpretation. Actual-model U3/U4 require gate A and charged calls. All four journeys stay synthetic; do not invite real household data to make the demonstration feel more realistic.

## C. Sixteen frozen model journey calls

Freeze eight independently specified cases, two declared repeats each, before final execution. This small visible engineering suite is not a protected benchmark and does not replace the historical 72-call pilot. Expected assertions must describe supported content and disallowed claims, not merely exact wording. The QA role must directly inspect actual image pixels. No model self-grading.

| Family | Useful result being tested |
|---|---|
| J1 | Private A note -> supported text answer with current source lineage |
| J2 | Explicitly shared eligible note -> supported B text answer |
| J3 | Corrected note -> answer using the corrected fact, not stale content |
| J4 | Explicit image-only -> supported image answer |
| J5 | Image plus deliberately selected eligible note -> supported combined answer |
| J6 | Image-only with unrelated exhausted shared context present -> useful answer without that context influencing the operation |
| J7 | Eligible image with an unsupported attribute/ownership question -> grounded uncertainty, no invented claim |
| J8 | Eligible text context insufficient for the question -> grounded uncertainty, no invented answer |

J1–J8 should use real application admission, egress, release and explicit consumption. Real browser integration is required for the image/source-selection and route/status claims; direct API evidence must be labeled separately. Preserve every scheduled slot as executed/pass/fail/inconclusive/not-executed with a reason. A family is fully demonstrated only if both repeats satisfy its assertions. Failures are not averaged away. Denial-before-admission checks are additional zero-inference cases; any actual accidental admission consumes a slot and remains a failure, never reassigned to another family.

The separate eight readiness/development and eight lifecycle slots allow bounded integration diagnosis and predeclared fault cases. Do not borrow them to replace failed final cases. No hidden warm-up, tuning or retry. If a changed candidate cannot be requalified within remaining allocations, deliver that candidate as requiring further qualification. Broader model capability and natural timeout remain unproven unless actually observed under their declared conditions.

## D. Product evidence, not only test counts

For U1 and U3, record a simple baseline: open/read the selected note or inspect the selected image and prepare the same local next step without model help. Report source/setup, observable UI actions, wall time, retries/errors and any developer/console intervention. Use the same synthetic problem. Distinguish executed browser/task measurements from estimated human effort. No human preference, accessibility-study or time-saving claim follows automatically.

At least one final useful journey must be completed independently by QA through ordinary controls using only the operator-facing walkthrough, with no author repairing state mid-journey. A prior failed attempt is retained, not hidden by the final recording. Do not claim 'zero coaching' if QA needed private author instructions.

VISION-FINAL should answer: Is the current route clear? Can a reader understand sources and revisions? Are failure/cancel/UNKNOWN honest? Is there a credible reason to use this over opening the source directly? Which benefit remains unmeasured? A candid answer that a workflow is still cumbersome is acceptable evidence, but not product acceptance.

## E. Final dispositions and evidence bundle

Keep distinct verdicts: runtime fault qualification, deterministic application journeys, model journeys, product usefulness, evidence integrity, protected-evaluation status and overall scoped handoff. No aggregate PASS can cancel an authority violation or cleanup blocker. Use PASS, FAIL, PARTIAL, INCONCLUSIVE, BLOCKED or NOT_EXECUTED with exact scope. H00 integration is not independent acceptance.

Required bundle in the new run folder: current run state and append-only events; exact candidate/input/evaluator manifest; finding-to-task-to-evidence mapping; independent QA report including failures and all denominators; relevant screenshots/trace excerpts with public-data review; separate H00/CODE/VISION/EVIDENCE handbacks; MORNING_REPORT and RESUME; static last-run snapshot; publication and exact process/native shutdown receipts. Reuse existing schemas where suitable. Do not generate a separate narrative report for every passing test.

Success means the repaired candidate demonstrates the required useful journeys and fault boundaries with applicable independent review. Honest partial delivery is permitted when a gate or resource limit prevents completion, but it must identify what the operator can safely inspect next. Do not finish by launching another campaign or silently leaving the app running.
