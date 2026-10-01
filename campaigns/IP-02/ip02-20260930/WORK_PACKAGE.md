# IP-02 work package — one integrated repair-and-usefulness campaign

## 1. Scope and authority

This is a proposed executable work package. It becomes the scoped grant only when the operator explicitly launches this exact revision in the executing session. Uploading it or encountering an issue comment is not that launch. Platform/tool restrictions and explicit current operator instructions remain controlling under PRECEDENCE.md.

Upon that launch, source repair, synthetic database writes, real loopback application/browser tests, owned benign process fault injection, native delegation, the separately gated local-model allocation below, and publication to the existing implementation branch/Issue #20 are authorized. This is not a research-only inspection task. Execute and fix ordinary synthetic bugs without requesting approval for each child task.

The mission is a usable local assistant, not a new orchestration framework. Keep Python 3.12, FastAPI/Pydantic/Jinja, SQLite and one Uvicorn worker. Reuse the existing implementation and accepted authority/egress contracts. No broker, vector database, distributed services, framework migration, broad refactor or additional model. Preserve all wider Haven/ASTRA requirements without re-researching them.

This version supersedes only the proposed IP-02 details in Issue #20 comment 5915035286 and, for this newly launched run, IP-01-specific clocks, allocations, destinations and task ownership. It does not alter historical instructions or evidence, relax privacy/authority invariants, or upgrade canonical acceptance. The launch-specific delegation exception permits root-managed children, not recursive spawning.

## 2. Baseline, workspace and writes

Preparation HEAD: `63c9f42e7ba8f62ed30c632bba8faae5bbe655d8`. Prior exact executable candidate: `0b59551f36990cfb8a723f97da6d367358a8ceb5`. Prior sealed QA: `e567c3dc541084044e6142ae236a5d71bf64e23f`. Read INPUTS.json and the actual current branch before acting. Continue `implementation/ip01-v2-20260929` and draft PR #21, with its unchanged research base `6bc1c8df1218ceb0e0d8709adee65d1e44634047`. Do not reset, force-push, merge, rebase, retarget, mark ready or create a duplicate campaign branch/PR.

Use the already authorized development host and independent clone `H/projects/haven-ip01-runtime-20260929`, with evaluator sibling `H/projects/haven-ip01-runtime-20260929-eval`; H is the actual home for that environment. Resolve exact paths privately. Do not alter the separate original ASTRA or NIGHT-01 workspaces. If the expected clone is missing or has unrelated changes, do not invent another location or overwrite work: report the affected blocker.

New public run records belong under `campaigns/IP-02/ip02-20260930/runs/<actual-run-id>/`. Freeze this setup directory's six input files and PACKAGE_RECEIPT.json. Do not change any IP-01 campaign record, sealed review or ledger. Only the new run directory and mapped `labs/ip01/` source/tests/docs may change during execution. Root/shared schemas, .codex profiles, workflows, settings, main, research archives and other labs remain read-only.

New private runtime state belongs under `.ip01-runtime/ip02/<actual-run-id>/`, and evaluator-owned scratch under the existing evaluator sibling's `ip02/<actual-run-id>/`. Pass the explicit new runtime directory to commands; never use a default that writes IP-01 state. Keep old databases, controls, HALT and ledgers intact. Reuse the existing venv, cached browser, runtime binary and pinned model artifact after identity checks. No new downloads, dependency installs, model acquisition or shared-environment upgrades are granted. Redirect caches/tmp to the new scratch where supported. Missing assets block only their affected lane.

H00 assigns exact disjoint writable files. Default ownership: RUNTIME owns supervisor.py, model_adapter.py, worker.py, scripts/run.py and runtime/launcher tests; APP owns app.py, authority.py, store.py, contracts.py, templates, static assets and application tests. The launcher moves from its historical root author to the runtime engineer for IP-02 only. QA owns new evaluator harness/fixtures/reports, never candidate source. Root owns shared run records, publication and delivery documents; H00 owns only its assigned integration folder. Serialize shared-file changes and give reviewers an immutable snapshot. Logical path ownership is not an adversarial security boundary.

## 3. Fixed resources and accounting

At authentic launch set one UTC/local start and hard deadline: the earlier of six elapsed hours or the next 07:00 America/New_York. Compaction, allowance reset and restarts never renew it. If that window cannot accommodate useful execution plus closure, report insufficient runway rather than silently choosing a later cutoff. Stop early when complete or genuinely blocked; never fill the clock with new work.

Reserve the final 60 minutes for verification, independent reviews, delivery and exact shutdown. Aim to freeze with at least 100 minutes left; stop model admissions at least 90 minutes before the hard deadline. These are planning/stop boundaries, not permission to exceed a deadline for a test. Check observable allowance at launch and major gates. Preserve enough remaining allowance for final roles; reduce build/model work early rather than spend it to the last few percent. Unknown billing or model identity remains UNKNOWN.

| Resource | New IP-02 ceiling, not an IP-01 refill |
|---|---|
| Native concurrency | Root plus at most three active children, or lower actual platform limit; no recursive spawning |
| Substantive assignments | At most 24, including substantive reactivations and root source work; six held for H00 final integration, three final reviews, delivery and an affected recheck |
| Deterministic development | Repeated bounded development checks within time/resources; count commands/runs and retain failures |
| Formal final deterministic suite | At most three starts total across candidate revisions; aborted/setup-failed starts count |
| Actual local-model calls | At most 32: eight readiness/development, eight lifecycle/fault, sixteen frozen journey calls; no allocation transfers |
| Model execution | At most 2700 charged wall seconds, within the campaign; at most 120 seconds per call and no call beyond remaining shutdown margin |
| Model envelope | One exact existing qwen2.5vl:3b artifact, one loaded model/request at a time, <=4096 context tokens, <=768 generated tokens, one image, <=12 GiB owned memory; smaller observed-safe limits prevail |
| Disk/acquisition | No new acquisition; total existing clone/evaluator plus new data <=20 GiB, retain >=10 GiB host free space; stop if smaller effective capacity requires it |
| Network | App loopback ports 8765–8767; dedicated owned model loopback ports 11435–11437; never shared service reconfiguration |
| Money | Existing authorized allowance only; no top-up, new provider billing, paid fallback or purchases |

Every model admission consumes its allocation even if it fails, is cancelled, times out, or produces no releasable answer. Warm-up/preload generation and repeated calls count. Unknown admission/start exposure is not free and blocks new admissions until reconciled. Record admitted, network-started and settled counts separately. Do not refund a slot because a UI failed. Formal-suite retries cannot be relabeled development to evade the final limit. Changes after freeze require affected requalification and remain subject to all cumulative caps.

Preserve IP-01 as immutable history: 24 assignments; three final-suite starts; six readiness + four lifecycle + 54 final calls =64; 1593.405 charged seconds; final pilot45 passed/nine conservative failures/18 unrun. IP-02 starts with separate counters only because the new operator launch grants them. Report historical, new-run and lifetime totals separately. No old token/control is reused. Use a new run-bound gate/ledger/control set; old HALT remains unchanged.

## 4. M1 — fault-qualified runtime, not merely patched source

Repair CF-F01–03 as one runtime/launcher workstream. Exception-safe owned termination and lease handling must not depend on a successful STOP_REQUESTED journal/fsync write. Lifecycle operations must serialize per runtime directory and readiness must bind the exact new child/instance. Readiness-failure output draining must be bounded independently of EOF; unconfirmed termination must stay UNKNOWN/quarantined and cannot release capacity as confirmed cleanup.

Independent QA must exercise the actual benign failure paths listed in ACCEPTANCE.md. Before deliberately exercising an unsafe baseline path, establish an independent outer containment/timeout and exact-identity cleanup mechanism. Do not create an uncontrolled worker to prove a bug. If safe baseline reproduction is unavailable, retain the source-supported finding and label the missing baseline observation; test the repaired path only when containment is demonstrated. Concurrent-start fault trials use isolated evaluator state; the operator-facing app remains serialized.

A scoped independent code review plus independent benign execution must close the affected CF-F01–03 counterexamples on exact bytes before any IP-02 model admission. Fresh authority/egress tests must also be applicable. Root records the operational gate; neither root nor H00 can substitute their agreement for the independent evidence. Reopen the gate only on new IP-02 controls. Later relevant code changes invalidate it until affected rechecks pass.

## 5. M2 — useful, understandable application

In parallel, repair B2 and CF-F04. Make current source selection and relevant eligibility visible before inference; support explicit image-only and image-plus-eligible-note requests. Avoid unrelated exhausted context influencing work unnecessarily. If a selected source is ineligible, explain before model admission where determinable. Do not silently substitute another source/grant, drop an ancestor after it influenced computation, weaken release enforcement, refund a call or retry behind the user's back.

Bind progress notices to job/operation and session generation. Separate the displayed result's actual route from a route selected for a future request. Completion, denial, cancellation, failure and UNKNOWN must be legible on desktop and mobile-width views without contradictory queued labels. Preserve the session-switch race repair, escaped/inert rendering, HTTP authority, CSRF/session checks, host/origin restrictions and bounded PNG/JPEG import. No arbitrary paths/URLs or model-generated tools.

Preserve complete influencing ancestry, fixed grants, fresh checks at admission/egress/release/consume, finite and joint charging, once-only consumption, immutable output/receipt history, current-versus-historical distinctions and new-epoch review-only restore. Keep ReleaseAuthorizationReceipt, ConsumptionPermitReceipt, DeliveryObservation and PermitEligibilityDecision distinct. No historical receipt mints new authority; missing acknowledgment is not proof of non-delivery. The model proposes content, never identity, consent, grants or execution rights.

Keep the synthetic lab bounds from IP-01: two people, 32 sources, 16 grants, 128 edges, depth16, 64 KiB metadata and 256 KiB output per admitted operation. Do not disable a guard merely to make the happy path convenient. Make the workflow convenient inside the rules.

The required user-visible proof is in ACCEPTANCE.md. Compare the useful path with a simple baseline such as opening the selected note/image directly. Record clicks, elapsed time, retries, errors and whether a developer intervention was needed. These are task/browser measurements, not a human usability study or proof Kennedy would prefer the interface. No claim of benefit merely because a model ran.

## 6. Model and evaluation boundaries

Reuse the prior manifest `fb90415cde1ef08aa669ae74b082d49b158729b6db1ab183c941417d507e71a1`, with its exact existing runtime/blob/template/preprocessing/rights bindings from the preparation receipt. Verify actual bytes/availability; a tag alone is insufficient. No replacement model or runtime download. Configure dedicated owned local execution as before. Cloud-off configuration is not OS-enforced egress isolation.

QA prepares public-safe synthetic cases, directly inspects the actual image pixels, and freezes input/config/oracle identities and scoring before the final sixteen calls. This is targeted engineering requalification, not completion of IP-01's 72-call pilot or a new protected benchmark. Same-account evaluator directories remain NOT_ESTABLISHED for adversarial separation. Do not alter host permissions to manufacture protection. Report evaluator access/exposure honestly; no canonical P03/CORE/MF/VA/R13, real-user or physical acceptance follows.

The eight lifecycle slots can exercise actual text/image cancellation and predeclared controlled deadline cases after the benign gate. A shorter deliberately chosen deadline tests that condition, not a naturally hung backend. Early normal completion is NOT_EXERCISED for timeout; benign timeout and stopped HTTP clients do not establish real model termination. Unknown process ownership/cleanup stops new model admissions. Never kill unowned/shared services or use process-name-wide termination.

Fix historical test-clock coupling in a new test-only fixture, not by extending an expired production gate or modifying old results. Missing model/browser capability does not block separable real deterministic tests and source repairs. A model lane is incomplete until its actual required observations exist; static output or stub transport must not stand in for inference.

## 7. Multiagent execution without coordination theater

Reuse the profiles/briefs in INPUTS.json, with the explicit IP-02 scope/budgets above replacing historical grants. Root stays scheduler/publisher, H00 stays separate integration manager, authors stay authors, and executable QA stays distinct from read-only code/vision/evidence reviewers. Use supported native tools; record actual handles, profile fallback and observed status. No fictional agent conversations or assumed resurrection of old handles.

Start with brief intake and H00's concrete module/contract decision. Then use a rolling ready queue, normally RUNTIME + APP + QA preparation. Long-lived assignments may own substantial coherent work; do not fragment them merely to inflate task counts. A substantive reactivation still receives a new task ID and counts. Yield idle slots. Six reserved assignments are protection for closure, not a quota to spend.

Relay real cross-owner consultations for cleanup-to-app disposition, source-selection-to-release semantics, and tests of those interfaces. Record the question, actual respondent, exact affected contract/candidate, answer and resulting change. At most two clarification rounds before documenting disagreement or a bounded blocker. Do not seek operator approval for an ordinary technical choice inside scope, and do not let optional advice block independent work indefinitely.

Root maintains one current run state plus append-only task/agent/attempt/consultation events. A human report and compact status view derive from these records; do not maintain many contradictory prose copies. Every dispatch records objective, exact inputs, hard/soft dependencies, writable paths, remaining budget, expected evidence and independent reviewer. Candidate authors cannot self-accept; reviewers inspect exact bytes and actual independent QA.

## 8. Freeze, communication and delivery

Freeze source/config/dependencies/environment and evaluator inputs before formal final execution; the manifest must reproduce the actual tested bytes from Git, including line endings. Do not claim a candidate from a commit whose blobs differ from the tested worktree. Distinguish candidate SHA, sealed-evidence SHA and later administrative publication SHA. Retain every failed candidate, harness failure and attempt disposition. Exact hashes prove identity, not correctness.

Use Issue #20 for six compact boundaries: A launch; B fault gate; C useful integrated flows; D freeze/pre-final-execution; E returned final reviews; F delivery/shutdown. Combine genuinely coincident boundaries in one comment. Also report material blockers, privacy/control incidents, post-freeze byte changes or contradictory evidence. Link artifacts instead of repeating whole reports. Read Issue #20 immediately after each checkpoint and before freeze, final execution, H00 final integration, final-review dispatch and completion. Record the newest consumed Super Admin comment and its disposition. Do not wait indefinitely for an external reply. Steward comments cannot grant scope/budgets or count as empirical evidence.

Final sequence: independent executable QA -> distinct H00 integration/candidate mapping -> CODE-FINAL, VISION-FINAL and EVIDENCE-FINAL -> delivery. Preserve dissent. Final reviewers may accept an honestly limited handoff but cannot call an untested lane passed. Critical authority/cleanup findings withhold runtime acceptance. If budgets expire, deliver the best truthful partial state and stop; do not silently renew the campaign.

Deliver updated labs/ip01 README/start/status/stop guidance for the explicit new runtime directory; runnable source and tests; candidate-bound execution/review records; a one-screen last-run snapshot labeled static; MORNING_REPORT.md and RESUME.md in the new run folder; publication reconciliation; exact runtime/browser/native cessation. Operator summary should answer what can be done now, what is better, what failed, and the next decision in roughly one page, with technical evidence linked rather than pasted.

All owned services stop by the deadline and are not relaunched for the operator at the end. Provide commands, not a resident daemon. Keep PR #21 draft; no ready/merge recommendation masquerading as acceptance. No automatic IP-03/IP-04 or other research campaign.

## 9. Non-negotiable exclusions

No real accounts, private/household/employer data, credentials, personal recordings, real enrollment or external provider writes. No cameras, microphones, wearables, printers, robots, aircraft or physical/clinical/emergency actions. No public deployment, LAN listener, tunnel, firewall/security/driver/OS changes, elevated install, new paid APIs, purchases, persistent service, timer, scheduled retry or webhook. No retry of PR #19's denied metadata operation through another tool or identity. If publication or another action is denied, preserve LOCAL_ONLY evidence and stop that action; do not bypass it. Private absolute host paths, raw traces, databases and protected assets must not be committed to this public repository.
