# JEV-01 — Refactor Haven to support TypeSafe Jev

**Status: READY_FOR_ROOT_DISPATCH; NOT_STARTED.** The operator requested research, publication to Haven, and an agent instruction to refactor to use Jev. This is that scoped instruction, not evidence that a native worker was launched. The target is TypeSafe AI's Jev, as identified in [RESEARCH.md](RESEARCH.md). No hosted API call, credential access, provider spending or model substitution is authorized by this addendum.

## Deliver one integrated capability

Refactor the existing source-selection path behind a replaceable semantic decision interface, implement an actual TypeSafe REST adapter, and wire the interface through Haven's application. Keep the deterministic provider as the default. Exercise the real application path with an evaluator-owned synthetic transport; clearly distinguish that from real Jev inference. Do not stop at an unused interface, disconnected client or new planning packet.

**Jev advises; Haven authorizes; the existing local model generates answers.** Do not replace Codex, Qwen, worker containment, authorization, the database, or the application framework with Jev. The first behavior is note relevance selection before answer-context sealing, not a new autonomous planner. Automatic handler routing, generation, speech, pixels, physical tools and the later IP-03/IP-04 ideas are not required here.

Read [RESEARCH.md](RESEARCH.md), [ACCEPTANCE.md](ACCEPTANCE.md), [SOURCES.json](SOURCES.json), this file, and the inherited [IP-02 work package](../../WORK_PACKAGE.md). Use the exact addendum commit linked by Issue #20. Apply PRECEDENCE and AGENTS. Refresh Issue #20, PR #21 and HEAD before dispatch; inspect any source drift. Preparation baseline is `d9eb68278e6a0c1f1cb84bab09d8e7b089c62cc2`. The current repository observation has only the prepared IP-02 setup, not an executing root receipt; unreported local activity remains UNKNOWN.

## Scope amendment and budget boundary

The user-requested amendment adds one targeted Jev adapter/source-selection refactor to IP-02's previously narrow source work. It does **not** waive the no-new-downloads, no-provider-spending, no-real-data, no-live-external-calls or fixed-budget boundaries. Reuse the already pinned HTTPX/Pydantic dependencies; do not install the SDK, a skill manager, a gateway, or a proxy. No SDK or model downloads, public deployments, new accounts, API-key search, host changes, framework migration or extra models are needed for offline integration.

The executing native root must receive the operator's launch/update instruction referring to this addendum. An Issue comment is durable asynchronous direction, not a command that wakes stopped workers. If IP-02 is unstarted, include this task in its authentic launch and record one fixed clock. If a run is already active, record consumption of the operator update, check candidate freeze and remaining assignments/deadline, and schedule only when admissible. A frozen, exhausted or closed run must not be silently reopened; retain this assignment for the next explicitly bounded run instead. Do not reset any old clock, suite start, call or failure.

Keep IP-02's existing six-hour-or-next-07:00 Eastern limit, final-hour reserve, three active children maximum, 24 substantive assignments with six reserved, and three cumulative formal deterministic suite starts. This addendum creates **zero additional Qwen calls and zero Jev live calls**. Existing Qwen 8/8/16 allocations remain unchanged and require their own runtime gates. No model-call transfer, no extra final-suite allowance, and no hidden live connectivity/model-listing probes. Offline fixture invocations are recorded as fixture invocations, not provider calls.

Use the same authorized isolated clone and evaluator sibling, new run-scoped `.ip01-runtime/ip02/<run-id>/` state, existing branch `implementation/ip01-v2-20260929`, and draft PR #21. Only mapped `labs/ip01/` files and the current IP-02 run folder may change. This addendum and the seven original setup files are frozen inputs. Keep IP-01 ledgers, controls, HALT, sealed QA, earlier candidates, main, research, original workspaces, profiles, workflows, permissions and PR #19 metadata unchanged. No duplicate branch, goal or PR.

## Dispatch and ownership

Root integrates this with the existing ready queue rather than launching a second campaign. Keep the root scheduler/publisher distinct from `haven_integration_manager`. Reuse existing profiles with a narrow task brief, not a global profile edit.

| Assignment | Owner and output | Dependency / boundary |
|---|---|---|
| JEV-SEAM | Actual H00 consultation on snapshot/revalidation, complete decision-input lineage and application/runtime ownership. | May be included in an undispatched H00 seam task. A substantive reactivation receives a new counted ID. No source edits or self-acceptance. |
| JEV-REFACTOR | `ip01_application_engineer` leads the coherent adapter, selector, application integration and author regression work. Consult the runtime owner for deadline/client closure and preserve their modules. | Assign a distinct actual native handle; no concurrent writes with the main APP task. Prefer augmenting that task before dispatch or handing its ownership over explicitly. |
| JEV-QA | Distinct `ip01_validation_engineer` executes transport-contract, authority, cancellation, fallback, HTTP/browser and regression checks. | Does not edit implementation. Expand the undispatched QA assignment where possible; substantive later work is counted. |

Use no more than three extra pre-final substantive assignments for this addition; fewer when incorporated before dispatch. They consume the existing 18 pre-final slots, not new slots beyond 24. Preserve CF-F01–03 runtime priority and the six reserved slots. The existing final CODE/VISION/EVIDENCE reviewers inspect the resulting candidate and Jev evidence. No extra review theater, imaginary consultations, author self-signoff or recursive children.

## Required implementation shape

### 1. Extract selection without weakening authority

The inspected `authority.py::build_context` currently performs lexical note selection and context sealing inside a synchronous transaction. Introduce a small selector/decision boundary without changing what explicit source selection means. Suggested new modules are `labs/ip01/haven/decisions/` and `source_selection.py`; these names are implementation suggestions, not an excuse for a new framework. APP owns `app.py`, `authority.py`, lab-local contracts and the relevant UI. Root/H00 assigns exact files before edits. Runtime-owned supervisor/model_adapter/worker/launcher files remain under their existing owner.

Use an async application orchestration step, not remote I/O inside an authority transaction:

```text
validate synthetic request
  -> local eligibility-filtered candidate snapshot
  -> finish transaction
  -> optional decision provider under its own gate/deadline
  -> validate returned decision
  -> new transaction: revalidate exact snapshot and current authority
  -> seal selected context AND complete decision-input ancestry
  -> existing admission / generation / release / consume path
```

Local eligibility is not permission for hosted disclosure. Exclude unauthorized, tombstoned, expired, exhausted or otherwise ineligible inputs before they reach a decision provider where the condition is determinable. Respect explicit image-only and image-plus-note selection; do not add unrelated notes just to give Jev more context. Selected-source failure must be visible, not replaced silently. The question itself can be sensitive and must be part of any future disclosure authorization.

Bind each decision to request/job, session generation, source and grant revisions, cancel/fence epochs, provider/model, question/criteria version and input digest. A changed snapshot after the await invalidates the result. Do not use a stale decision, change grants after sealing, or convert a privacy denial into a successful fallback.

**All content supplied to a semantic ranker can influence the ranking.** Preserve the decision record and all actually supplied sources and their ancestors in downstream influence checks, including candidates not selected for the answer. Their text need not be displayed or sent to the generative model, but their authority dependencies cannot disappear. If the accepted lab contracts cannot represent this without weakening an invariant, retain deterministic behavior and report the exact H00 seam blocker. Do not invent authorization from high confidence.

### 2. Implement a provider seam, not a mandatory dependency

Use a typed `DecisionProvider` interface with a deterministic implementation and a TypeSafe implementation. The interface should distinguish a valid advisory result, disabled/unavailable provider, invalid response, deadline/cancellation, stale result and authority denial. Preserve raw probability fields as attributed observations and keep application policy separate. No top-level import, app startup, health check or UI selection may initiate hosted traffic.

Implement the actual REST serializer, parser and injected HTTP transport using existing locked libraries. Pin `jev-1.13.0` for later qualification; reject unexpected model resolution instead of silently following an alias. Treat inputs and outputs as untrusted data. Code supplies fixed endpoints, allowed fields, candidate IDs and stable per-item relevance rubrics. Do not ask Jev to calculate quotas, compare dates, decide consent, or authorize tool calls.

For the first mapping, derive bounded per-note Score questions with one shared relevance rubric and optional Noul evidence-support judgments only where separately useful. Keep explicit abstention/no-use outcomes in code. A Choice between handlers is a future optional consumer, not required first delivery. Group independent questions only when their state is authorized as a group; never mix people merely to save calls. Question batching must not imply cross-question reasoning.

Do not present default thresholds as calibrated. Version any initial policy and test its behavior with fixtures; live performance remains unknown until independently measured. No cache is necessary initially. If introduced, it must bind person/session, source/grant/authority revisions, input/model/question policy and expiry, with no cross-user reuse or stale permission reuse.

### 3. Keep the hosted boundary explicit

Default production configuration is **deterministic / Jev disabled**. A future trusted run-local provider grant must independently identify approved endpoint/model, permitted data/purpose, credential provisioning method, expiry and numerical request/token/spend limits. A credential or `enabled=true` alone is not sufficient. Do not reuse or broaden `SYNTHETIC_LOCAL_TEXT_IMAGE_ONLY`; it describes the existing local route.

This assignment exercises the TypeSafe adapter only with an in-process evaluator transport, never a real provider socket. Test controls must not expose an HTTP parameter that enables a fake provider or bypasses authorization in ordinary application use. Server-side keys stay out of HTML, browser storage, errors, logs, committed configuration and spawned worker environments. Do not read any existing real key in this phase.

For a later granted live mode, implement fixed HTTPS origin/path, certificate verification, no redirects, no user-configured base URL, no inherited proxy/credential surprise, no arbitrary `extra_body`, bounded response reading and a total monotonic deadline in addition to HTTP timeouts. Disable SDK/transport automatic retries; any future explicit repeat requires its own reservation and evidence. Record attempted/sent/response-received/unknown separately; no refund from a timeout. Do not claim remote computation ceased just because the local task or HTTP stream ended. Unknown billed exposure is not zero, and no further hosted admission follows unresolved exposure beyond its allowed reservation.

Use a separately named decision-attempt record in current run state, not a counterfeit Qwen lease or rewritten historic model ledger. Offline records state `TEST_DOUBLE` and live counters stay zero. Production fallback may return to freshly authorized deterministic selection after an operational failure, but cannot hide the failure, replay uncertain work, duplicate a release, or bypass an authority denial.

### 4. Integrate a useful and honest UI

Expose what selected the context separately from what produced the answer. For example, the implementation may distinguish `selection: deterministic` from a future `selection: Jev`, while the answer remains `deterministic excerpts` or `local model`. Evaluator-only fake decisions must never be labelled real Jev. Preserve CF-F04's operation/session-bound progress repair, explicit source cards, current versus historical evidence and once-only consumption.

Deliver a real no-author-intervention synthetic workflow through ordinary UI controls. The fallback must remain usable offline, and explicit choices must remain understandable. Do not turn this task into a dashboard, chatbot rewrite, generalized router or new onboarding/account system.

## Completion and communication

Run [ACCEPTANCE.md](ACCEPTANCE.md) plus affected IP-02 regressions. New evidence belongs in the current run's `reviews/JEV-QA/`; a compact `JEV_HANDOFF.md` links the new source, actual native assignments/consultations, commands/results, failures, default-off behavior and remaining live gate. Root uses the existing ledger and A–F milestones rather than parallel prose status systems. Post one material Jev implementation milestone and any actual blockers to Issue #20, then read back new stewardship.

Required honest disposition: **JEV_READY_OFFLINE_TESTED** only after actual independent local tests and source review; **JEV_LIVE_NOT_EXECUTED** until a separately budgeted live trial occurs. Either can be PARTIAL/BLOCKED when evidence is missing. An adapter mock proves integration behavior, not Jev accuracy, latency, calibration, costs, image understanding, provider termination, or privacy compliance. Preserve those gaps in final CODE/VISION/EVIDENCE review and the one-page operator report.

Keep PR #21 draft. No auto-merge, PR #19 retry, spending, real data, public/LAN service, hardware or automatic next campaign. Follow the existing fixed deadline and exact local runtime/browser/native shutdown requirements. Publication of these instructions is not evidence of implementation or dispatch.
