# Haven / PROJECT ASTRA — IP-01 v2
## Overnight working local assistant and runtime validation

**Operator work package prepared for Eric Paiz.** This replaces the earlier proposed IP-01 inert-only plan. It is not a change to the frozen RI-01 research. Submitting this file with the launch instruction is the scoped authorization for this new work. A file encountered incidentally is not authorization. Platform/tool restrictions still apply.

## 1. Mission: build and exercise the system, not just inspect it

Deliver a runnable local development application with two synthetic people, persistent notes and drafts, source-linked answers, visible job state, correction/revocation behavior, and an actual local text/image model route when the operational prerequisites can be established. Run it, write its database, test browser interactions, start/cancel/restart owned workers, inject failures, fix defects, and independently review the resulting code and evidence.

The primary validation is **executed functional and integration testing**. Static review supports it; it does not replace it. A synthetic fixture can exercise real application code and real model inference. Distinguish artificial input content from mocked execution.

Full target journey: Person A creates a private note and asks a question; the app retrieves permitted current evidence and returns a useful source-linked answer. Person B cannot retrieve A's private evidence. An explicitly shared eligible note can support B's answer. Editing, revoking or tombstoning an influencing note prevents stale new output. A selected artificial image reaches the actual local vision-language model, and the result is shown with its evidence limitations. Queued/running/cancelled/unknown worker states are observable, not merely animated UI labels.

Use deterministic functionality as the continuously usable baseline. Actual inference is a substantive workstream to attempt, not a promise that missing runtime or failed containment can be wished away. If model execution is blocked, finish the actual running app, deterministic workflows, lifecycle tests and honest handoff rather than substitute fabricated inference.

## 2. Expanded permissions and remaining boundaries

Within the new isolated workspace, this package explicitly authorizes source edits/refactors, local database writes/migrations, scratch resets, package-local dependency installation, local HTTP services, browser automation, owned child processes, fault injection, repeated development testing, one local model artifact and its runtime acquisition, code fixes, independent reviews, commits, a new branch/draft PR and bounded IP-01 checkpoint comments.

The research-only restrictions against implementation, all dependency installation, all server execution, all subprocesses and all inference do **not** apply to this new scoped development campaign. The earlier three-suite/76-invocation limits are not silently reinterpreted as unlimited development rights: this is a separately versioned development/evaluation profile with the budgets below. No result may be relabeled as canonical CORE-P0, MF-P0, VA-01 or R02-P03 acceptance unless its original applicable prerequisites and protocol were actually met.

A failing assertion on synthetic data is an engineering defect to preserve, fix and recheck. It does not automatically require abandoning the whole night. An actual out-of-scope write, real-data disclosure, unowned process termination, policy denial or uncontrolled execution is different: stop that activity, preserve evidence and do not work around the restriction.

Do not merge, enable auto-merge, deploy publicly, create persistent services/startup tasks, change host security/approval/firewall/driver settings, use elevated installation, spend additional provider money, create accounts, use personal/workplace data, connect live mail/calendar/health systems, or operate cameras, microphones, wearables, printers, robots or aircraft. No GPU-driver, OS or shared-service changes. No employee/bank access. Physical and clinical capability is outside this campaign.

Leave the denied PR #19 description/ready action untouched. Do not retry it from this new thread, identity, shell or API route. It remains a separate operator approval matter. An optional publication failure does not block unrelated already-authorized local implementation.

## 3. Baseline, source reuse and exact writable scope

Repository: https://github.com/erpzz/haven
Pinned published research baseline: `6bc1c8df1218ceb0e0d8709adee65d1e44634047`
Source research branch: `campaign/ri01-20260928T180322Z-6e8f`
Research prefix `RI`: `campaigns/RI-01/ri01-20260928T180322Z-6e8f`
Frozen synthesis manifest SHA256: `c5ec562b5ea5390962ab8334b39f397e959a071a4314c3b17898ec991b3ede1b`
New implementation branch: `implementation/ip01-v2-20260929`

Use the existing development host. Define H as the actual home directory of its selected existing Windows/WSL execution environment. Create a fresh independent clone at `H/projects/haven-ip01-runtime-20260929`. The evaluator may use the separate sibling `H/projects/haven-ip01-runtime-20260929-eval`. Record absolute native/WSL mappings. Do not reset or change the original checkout. If either target already exists, verify matching campaign identity before resuming; never overwrite unrelated work or invent alternative target paths.

Tracked changes are confined to `labs/ip01/` and `campaigns/IP-01/ip01-v2-20260929/`. Package-local pyproject/lock files, application source, tests, migrations, fixtures, scripts, templates and reviewed reports belong under `labs/ip01/`. Do not edit root/shared schemas, workflow configuration, main or frozen RI-01 content. Record these new implementation paths as an explicit mapping from the reused upstream designs, not an assertion that their original path grants already covered this work.

Runtime binaries, virtual environment, downloaded weights, databases, caches, browser profiles, logs and temporary execution files stay inside the new clone's `.ip01-runtime/`, except evaluator-owned assets in its named sibling. Redirect tool caches/tmp directories there when supported. Use clone-local Git exclusion metadata. Never commit weights, credentials, raw session logs, runtime databases or reusable protected holdouts.

Read applicable AGENTS instructions and pinned START_HERE.md, CURRENT_STATUS.md, PRECEDENCE.md, coordination/DECISIONS.md and contracts/README.md. Then read `RI/MORNING_REPORT.md`, `RI/state/FINAL_REVIEW_RECEIPT.json`, final-v1 ARCHITECTURE.md, CONTRACTS.md, CONTRACT_CROSSWALK.md, IMPLEMENTATION_QUEUE.md, WORK_PACKAGES.json, INPUT_USE.json, MANIFEST.json and `RI/reviews/R13/PROMOTION_GATES.md`. Follow exact required accepted composites for the behavior used, including R02-P01/R03 corrections and reviewer closures. Do not silently use superseded original-only semantics.

The known source workspaces `~/projects/project-astra` and `~/projects/haven-tonight-2026-09-27-c2cc0e` are authorized for read-only inspection of their actual tracked source/config identity. Map them to real paths on the existing host; do not search unrelated personal directories when absent. Record current revision and dirty-state identity without altering either. Reuse relevant tracked non-sensitive source by copying it into the new clone with explicit source-to-copy hashes. Do not copy `.env`, credentials, runtime DBs, private records or active jobs. Repair copied R1 code only in the new implementation workspace.

If current R1 source is unavailable, do not pretend to fix it. Implement a clearly new isolated worker supervisor for this laboratory, test it, and record that current R1 remains unqualified. An unavailable original workspace need not block a separately authorized new prototype, but it blocks claims about that original.

## 4. Runtime and acquisition grant

Keep Python 3.12, FastAPI, Pydantic 2, Jinja2, one Uvicorn worker and SQLite. Use a small modular application, not a broker, universal framework or distributed microservice system.

Prefer installed Python/runtime tools. Package-local virtual-environment installs are authorized for FastAPI, Pydantic 2, Jinja2, Uvicorn, pytest, Hypothesis, HTTPX, psutil, Pillow, Playwright and necessary declared transitive dependencies. Pin compatible resolved versions and hashes, record sources, prefer published wheels, and never run arbitrary repository installation scripts or pipe downloaded scripts into a privileged shell. Browser binaries may be acquired through Playwright's official distribution into the campaign cache. No system package-manager/sudo fallback.

Use the existing installed Ollama binary where possible. If absent, one compatible official portable/user-space Ollama distribution may be downloaded and extracted inside the runtime directory, subject to the platform's existing controls. Verify official provenance and available checksums. No system service installer, daemon reconfiguration, GPU-driver work or account sign-in.

The single model choice is the inherited `qwen2.5vl:3b` candidate. Prefer an existing artifact only after identifying it. Otherwise one download from its official Ollama registry route is authorized. Record the full manifest/blob digests, quantization, license chain, template, runtime and preprocessing. A mutable tag alone is not an exact pin. Do not test an assortment of replacement models when this one fails. Documentation/retrieval may use official upstream sources to resolve compatibility and rights; this is not another broad model-selection study.

Total newly downloaded dependencies/runtime/model/browser assets: at most 12 GiB. Total new workspace/runtime storage: at most 20 GiB, with at least 10 GiB free host disk retained. Apply a smaller effective cap when actual available resources demand it. Stop acquisition if provenance, rights, storage or policy cannot be satisfied; continue separable app work.

Start an **owned dedicated** model server on an available loopback port from 11435–11437 with its own model/runtime directory and process-scoped configuration. Never stop or reconfigure a shared Ollama service to make tests pass. Configure cloud features off where supported, one loaded model and one inference request at a time. Local-only/cloud-off application configuration is not proof of OS-level egress isolation; record the distinction.

Start the application on the first available loopback port from 8765–8767. No wildcard/LAN bind, tunnel, public origin, port forward or firewall exception. Check ownership before binding or stopping processes. No service should persist after this campaign ends; deliver a restart command for the operator.

## 5. Time, usage and working roles

This is a fresh campaign budget: up to six elapsed hours, stopping by the earlier of that elapsed deadline and the next 07:00 America/New_York. Resolve launch/deadline once and record UTC/local times. Preserve the deadline across compaction and process restarts. Reserve the last 45 minutes for final verification, handoff, publication and shutdown. Stop earlier when complete, genuinely blocked or at a resource boundary; never busy-loop to fill time.

Use existing authorized Codex allowance only; no extra-provider spending, top-ups or account changes. Inspect available allowance at startup, record observable counters and UNKNOWN for unavailable costs. Don't confuse model token accounting with billing or wall-clock duration.

Maximum root plus three active native coding/review children, or the lower actual platform limit. Maximum 24 substantive assignments, with six reserved for independent review and delivery. Use narrow contexts and exact source references rather than sending the entire research corpus to every child.

Suggested roles: root integration lead; application/authority engineer; runtime/lifecycle engineer; independent evaluator/browser tester; and a final independent code/authority reviewer scheduled within the slots. Parallelize genuinely independent work. Reviewers must not certify their own candidate implementations. The Super Admin can give concrete correction instructions and direct rework inside this grant without asking Eric about ordinary technical decisions; it cannot enlarge permissions, money, time or experimental budgets.

Ordinary deterministic development tests may run repeatedly inside the wall/resource envelope. Count runs, retain failures and fix defects. Stop an individual stalled test/process using only owned handles; do not repeatedly retry the same ineffective command. Freeze a useful targeted regression plan instead of aiming for an arbitrary giant test count. Final deterministic integration qualification has at most three recorded suite starts; report which changes each recheck covers and whether protected feedback was exposed.

## 6. Workstream A — useful stateful application

Implement real SQLite persistence and migrations for two invented demo people, notes, revisions, grants, source/derivative lineage, drafts/tasks, jobs and output records. Provide server-side ownership/eligibility checks; browser UI hiding is not access control. Use independent test sessions/cookie jars. A demo identity selector is allowed only as visibly simulated login, not real enrollment/authentication.

Implement create/edit/delete/tombstone of synthetic notes; explicit sharing and withdrawal; saved local task/draft create/edit; deterministic retrieval/answering; and a model-backed answer route through the same authorization path. No external schedule execution, notifications, OAuth or provider writes. Synthetic persona content must not be copied from Eric or Kennedy's real accounts.

Preserve the accepted contract invariants: complete influencing source/grant dependency checks (including uncited ancestors); current preconditions at retrieval/admission/release; immutable history; typed unknown outcomes; once-only finite-grant charging; exactly one consume slot for the first whole-output/destination profile; all-or-none joint-grant transactions; duplicate history rather than replay; new-epoch review-only restore. Honor the small upstream 2-person/32-source/16-grant/128-edge/depth16/64KiB-metadata/256KiB-output laboratory limits per admitted operation.

Maintain distinct ReleaseAuthorizationReceipt, ConsumptionPermitReceipt, DeliveryObservation and PermitEligibilityDecision records. A missing ACK is not proof of NOT_SENT; a returned historical receipt does not mint new authority. The model may propose answer content, not grants, session identity, task execution or arbitrary tools. Restrict image import to reviewed bounded PNG/JPEG files; no executable payloads, URLs or arbitrary path reads.

The application should remain useful when inference is unavailable. A deterministic source-supported answer is a labeled route, not a fake model response.

## 7. Workstream B — actual lifecycle and recovery

Implement or repair the copied worker supervisor with real owned processes, immutable job/request IDs, worker birth/boot identity, nonce/fence, deadlines, cancellation and append-only event records. Actual process observations distinguish NOT_STARTED, RUNNING, STOP_REQUESTED, STOP_CONFIRMED and UNKNOWN. Wrapper exit alone cannot prove backend cleanup.

Run actual tests for cancellation before start/during work, timeout, parent death, worker crash, delayed/duplicate result, stale lease/fence, restart recovery and capacity release. Use a benign owned test workload to exercise the lifecycle first. An independent observer records descendants and any dedicated backend. Freeze topology-specific stop targets after basic environment probes, before the measured fault trials; never increase targets after a failure just to pass.

For an owned model backend, test cleanup/abort using only its dedicated process identity and API. Closing a request stream may not stop inference; observe rather than assume. Never terminate other jobs, shared services or broad PID/name sets. Model buffers/memory residency, active computation, termination and billable exposure are separate observations.

A laboratory implementation can run in the standard permitted development environment without pretending it is a production-grade sandbox. Remove secrets and unrelated file/tool capabilities from the worker context; no model-generated shell, network tools, package installs or arbitrary code execution. Use existing process/container/OS isolation where available and verify it. Do not claim VA-01/R13 security qualification merely from a separate directory or a role label. If critical process ownership/termination control is absent, do not start a long-running inference workload; finish separable app and supervisor work.

## 8. Workstream C — real local text/image pilot

Attempt actual inference once the exact artifact/runtime/rights are identified and an owned launch, deadline and stop path has been demonstrated. Do not wait for all future Haven components, original R1 qualification or production-quality deployment certification. This is the separately authorized synthetic-data development pilot, not retroactive acceptance of canonical P03.

Pin the prompt/template, image handling, context limit and output limit. Start with at most 4096 context tokens, at most 768 generated tokens, one image per image request and a 120-second per-call wall limit; smaller justified settings may be frozen before the evaluation. Do not add hosted fallback or new models. Bound candidate RAM to at most 12 GiB and select a smaller admissible envelope based on actual free RAM/VRAM; preserve enough resources for the desktop and evaluator. Measure actual peaks where possible. No drivers or GPU clocks are changed.

Total model invocation ceiling is 96: up to 16 readiness/development calls, up to 8 lifecycle/fault calls, and 72 final pilot calls. Every admitted call—including failed, partial, cancelled, repeated, warm-up/preload generation and tuning calls—consumes a slot in its allocation. Up to 90 wall-clock minutes of model execution are available within, not in addition to, the campaign deadline. Do not borrow unused allocations after seeing results. If a call hangs or ownership/cleanup is unknown, stop new model admissions until safely resolved within scope.

The final pilot borrows the original 24-family shape: 12 development families and 12 protected families, each six text/six image, with three repeats (72 final calls). In protected cases, each modality has four answerable and two intentionally unsupported/uncertain questions. Preserve original family/repeat disposition logic and report the 7/8 answerable and 4/4 unanswerable criteria as a **pilot comparison criterion**, not canonical P03 qualification. All repeats and errors remain visible. Freeze family membership, exact artifacts, positive/negative assertions, resource settings and any supported uncertainty before final calls.

Use original artificial images (for example clearly rendered shapes, labels and diagrams) and synthetic notes. An independent evaluator must actually inspect the evaluated pixels and text. Generator parameters alone cannot stand in for visual inspection. A correct assertion about these rendered pixels is real model behavior on artificial inputs, not real-world perception generalization. Insufficient evaluator modality access blocks a protected visual verdict, not the already permitted deterministic app work.

Keep protected expected outputs outside candidate write access where actual enforcement is available. Record who can read/write/invoke them. If the environment cannot establish the prescribed protection, the development pilot can still yield inspectable engineering observations on non-sensitive fixtures, but its final verdict must state EVALUATION_INCONCLUSIVE / protection not established rather than claim an R13-quality protected benchmark. Independent code review and independent empirical evidence remain different things.

No extra model calls are allowed after the final allocation is exhausted. A repaired later candidate can be delivered with honest prior failures and requalification needed; it does not inherit a PASS from earlier bytes. Report text and image usefulness, abstention/denial, source grounding, latency and memory separately. Model output is not an independent evaluator of its own correctness.

## 9. Workstream D — browser-tested local interface

Build a small coherent FastAPI/Jinja interface with: demo identity indicator; notes and sharing controls; local drafts/tasks; a question/image panel; source cards and revision links; visible job queue/status/cancel control; and a compact activity timeline. Show deterministic versus actual-model routes explicitly.

Use Playwright or available browser tooling to exercise real clicks, forms, separate sessions, reload/restart behavior, errors and rendered output. Verify server-side two-person isolation with HTTP tests as well as UI behavior. Escape untrusted content, validate CSRF/session binding for state changes, restrict origins/hosts, and keep file imports and rendered model output inert. Do not treat localhost alone as authentication or a complete web-security boundary.

Exercise at least: create/edit a note; private A answer; forbidden B retrieval; explicitly shared B answer; revoke/correct during queued/running work; one-use and duplicate behavior; saved draft persistence; cancel and crash recovery; restart with current versus rolled-back state; and actual selected-image answering when the model gate is met. Derived stale answers must not be silently released after correction. Where delivery/physical display remains unobservable, use honest status language.

A full Observatory, three-dimensional world renderer, device frontend, household enrollment, mobile HTTPS tunnel or wearable integration is not part of this night. Make this slice pleasant and inspectable without building all fourteen packages.

## 10. Integration sequence and autonomous decision rules

Begin with a short preflight and exact source/path/permission mapping, not a new lengthy research report. Establish an executable skeleton early. In parallel, build stateful authority behavior and the benign worker lifecycle. Prepare independent fixtures/browser tests while implementation proceeds. Integrate deterministic end-to-end behavior, then the owned local model route, then final freeze/review and delivery.

Within this grant the root chooses routine modules, compatible dependency pins, small code refactors, test ordering, local ports from the allowed sets and bounded fixes without seeking overnight confirmation. Do not stop at PLAN_READY when authorized work remains possible. Do not let a missing optional browser/model/publication capability block unrelated useful executable work.

Distinguish blockers from bugs and watch items. A reproducible synthetic test failure usually authorizes repair and development recheck. Actual access/policy denial never authorizes rerouting the same blocked action. Uncontrolled process ownership stops the affected runtime. A complete or exhausted goal stops; it does not discover new domains to fill time.

The Super Admin checks scope, useful positive behavior, actual versus claimed execution, independence, budgets, dependencies and operator-facing quality at material milestones. Give specific praise where earned and the smallest actionable correction where needed. Independent reviewers can require fixes; the same author cannot simply label its own changes accepted.

## 11. Evidence, publication and handoff

Maintain one compact ledger of tasks, real agent identities, status, input/candidate revisions, source mappings, attempts, resources, findings and next admissible action. Preserve original failed outcomes. Distinguish IMPLEMENTED, EXECUTED, INDEPENDENTLY_REVIEWED, PILOT_PASSED, INCONCLUSIVE and NOT_EXECUTED. Do not pool good UX results to offset access-control failures.

Freeze candidate code/config/dependency/environment identity for final review. At minimum obtain independent code/authority review and an independently authored functional/lifecycle report. Review applicability must name the actual candidate revision. Changes after review require an affected recheck, not silent reuse of a PASS.

Commit public-safe source and reports only. Scan for credentials, household/workplace data, raw session material, runtime DBs, protected fixture disclosure and writes outside the grant. Push only the new implementation branch. Create one new draft PR targeting the unchanged source campaign branch when possible, so its diff contains this implementation rather than the whole research corpus. Record dependence on PR #19. If that base changed, retain the pinned work and report the issue rather than silently rebase/merge. Do not alter PR #19 or main.

Post up to four compact IP-01-v2 milestone receipts to Issue #17 with exact commits, task/review progress, executed tests, blockers and one next step, subject to normal tool approval. If any publication action is denied, preserve the proposed receipt and LOCAL_ONLY output; do not try an alternative route. A new commit's publication receipt must distinguish the evaluated candidate SHA from later administrative SHA.

Deliver README/start/stop commands, locked dependencies, source, tests, migrations, sanitized sample fixtures, actual test reports, browser screenshots when genuinely captured, immutable runtime traces, final independent findings, MORNING_REPORT.md and RESUME.md. Include a small offline results snapshot so Eric can inspect the last run after services stop. Do not call a screenshot or static report the runnable app.

MORNING_REPORT must answer: what runs now and exact start URL/commands; which real writes and user journeys passed; whether the actual model ran and its exact identity; what the lifecycle observer saw; failures/unknowns and unqualified claims; consumed versus remaining budgets; what was published; whether all original workspaces remained unchanged; and the single smallest next decision. Report a useful partial outcome honestly rather than a ceremonial all-green summary.

Stop owned app/model/test processes and native work at the deadline using exact observed identities. Do not leave a daemon, scheduled task, autonomous retry or timer to resume later. Preserve an operator restart command and record shutdown uncertainty where present. No process-name-wide killing.

## Launch instruction

/goal Execute Haven IP-01 v2 using the attached Haven_IP-01_v2_Working_Local_Assistant.md as my scoped authorization, replacing the earlier inert-only proposal. Build and RUN the isolated local assistant: persistent synthetic notes/drafts, two-person authority checks, real browser tests, owned worker lifecycle/fault tests, and one actual local qwen2.5vl:3b text/image pilot when its operational gates are met. Package-local installs and the specified one-model/runtime download are authorized within the file's limits. Use the pinned 6bc1c8df1218ceb0e0d8709adee65d1e44634047 baseline and named new workspace/branch. Fix ordinary test failures and continue independent work rather than stopping at a plan. Obtain independent reviews and publish only allowed new-branch/checkpoint artifacts. Work until complete, genuinely blocked, or the earlier of six elapsed hours and next 07:00 America/New_York. Leave PR #19's denied metadata action, main, original workspaces, real accounts and physical devices untouched. Do not bypass policy or spend additional provider money. Deliver a runnable app and an honest MORNING_REPORT, then stop owned processes.
