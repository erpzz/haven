# APP assignment 3 — executable application handback

Thread / owner / task ID: native APP `01a0eb68-1eef-7890-a6bb-4d1dc1bc5a57`; ip01_application_engineer (H04 with H01/H03); assignment 3, Issue 20. CUSTOM_PROFILE_FALLBACK; inherited model UNKNOWN. Root `01a0eb51-c8b3-7923-94ed-ea1874de843e`.

Input repository version: setup `8e1304caf82c0a889eeaea7691db7b9d7b98c526`, research baseline `6bc1c8df1218ceb0e0d8709adee65d1e44634047`, as assigned and recorded by INTAKE. No child Git commands or independent HEAD/branch claim. Workspace: `<campaign>`.

Status: **IMPLEMENTED_AND_EXECUTED_DEVELOPMENT; READY_FOR_INDEPENDENT_QA**, not self-accepted. Publication: NOT_UPLOADED by APP; root owns publication. This report/source code is public-safe; raw logs, DBs, browser profiles/screenshots and process identity evidence remain private under `.ip01-runtime/app-dev/`.

Requirements retained: I01–I06; original R03 plus amendment 1 and reviewer closure; P01 amendment 1 and reviewer closure. Dependencies INTAKE/H00 met; runtime callbacks integrated. Runtime lifecycle and model operational qualification remain separate owner/QA work. Deadline unchanged `2026-09-29T10:10:16Z`; feature cutoff unchanged `09:25:16Z`. APP used **0 model calls**, **0 final deterministic suite starts**, no children, no provider spend.

## Decisions

Delivered a running FastAPI/Jinja/SQLite app: two actual opaque-cookie demo sessions, notes with immutable revisions and CAS edits, explicit finite/unlimited sharing and revocation, tombstones, independent local drafts/tasks, reviewed PNG/JPEG import, source selection, durable jobs and contexts, metadata-only queue/status/source cards/timeline, cancellation, and explicit once-only answer consumption. Deterministic text selects relevant current source excerpts and labels its limitations. It never claims model inference or a running worker.

SQLite schema migrations 1/2 use connection-local foreign_keys/busy_timeout, verified WAL and synchronous FULL, a process-local writer lock, BEGIN IMMEDIATE, immutable history triggers, and unique release/job, consume-slot, finite-claim and model-token constraints. All influencing parents participate even when absent from citations. Full 26-field vector equality/current checks run at retrieval, attempt admission, release and consume; model egress rechecks in the callback. Bounds are retained at 2 people /32 sources /16 grants /128 edges /depth16 /64 KiB metadata /256 KiB output. No new shared schema/service.

Release atomically charges each distinct applicable finite grant once, creates immutable claims and one output slot. Authorization revision stays separate from quota accounting sequence. Existing matching slots consume at zero remaining parent quota. Duplicates/history never return payload. Current eligibility does not rewrite release/consume/delivery records; lost replies and unknown delivery remain visible. No automatic quota refund, replay, remint or worker resume.

Separate continuity sidecar binds DB generation, commit sequence and random commit token. Intact-current restart is distinguished from rollback/missing proof. Every restart expires old sessions and advances old job fences; unproven continuity also rotates authority/restore epochs and enters review-only. Sidecar failure fences current operations. This is an accidental rollback detector, not administrator tamper protection or distributed storage atomicity.

UI is local-only with no CDN, escaped text rendering, same-origin authenticated forms, explicit demo login, clear current-source and delivery uncertainty, and responsive desktop/mobile layouts. Generated-answer-to-ordinary-draft shortcut was removed before handback: persisting it without authority lineage would permit a later payload replay. Independent user-authored drafts/tasks remain durable and LOCAL_ONLY.

Actual consultation Q-APP-01: read RUNTIME_CONSULTATION.md and adopt admission -> local cancel recheck -> owned launch, exact attempt/fence/cancel/request/context identity, and independent stop evidence. APP separately checks durable cancellation and exact result request/admission identity. Release FENCED never means STOP_CONFIRMED.

Actual Q-MODEL-SEAM-02: adopt runtime's root-issued token pool. APP reads ModelAdapter.gate_snapshot metadata only, binds one unused token inside the SQLite admission transaction to the exact wire job and a unique attempt/binding receipt, and returns limits.model_attempt_token/model_allocation/model_binding_id/model_gate_sha256 plus the four pinned model hashes and inference_authorized. Runtime independently claims once. Root gate remains `.ip01-runtime/model/model-gate.json`; Supervisor receives the same runtime root. Normal trusted allocation is readiness; only root process configuration HAVEN_MODEL_ALLOCATION can choose lifecycle/final. No HTTP/model authority fields choose caps/tokens/identity. All image bytes, derivative digest and preprocessing identity are sealed into context before admission; context_digest excludes only its self field. Actual model calls are NOT_EXECUTED here.

## Evidence

Latest complete author development run: **124 passed**, one non-fatal Starlette TestClient/httpx deprecation warning, 27.61 seconds (`.ip01-runtime/app-dev/pytest-05.log`). These are development tests, not the reserved final suites or independent acceptance. Coverage includes useful A/B/private/shared journeys; parent-uncited invalidation; grant/depth/source/edge limits; metadata rejection and exact output byte boundary; joint atomic and repeated-parent dedup claims; concurrent one-use release; consumption at remaining0; expiry/revoke/edit/tombstone; duplicate/conflict/history; unknown release commit and lost consume reply; late display after revoke and wrong tuple; CSRF/Origin/Host/principal spoofing; safe/hostile images; draft persistence; immutable receipts; current/rolled-back store recovery; gated model denial; exact callback request/admission identity. The 104 parameterized vector tests alter each captured vector field across four phases and observe the authority check; they are **not** independent empirical mutations of every current backing dependency through all live routes. QA's complete trace obligations remain.

Live browser (`browser_walkthrough.py`) passed 12 scenario categories twice, zero console/page errors, actual clicks/forms in separate A/B browser contexts, screenshots captured and visually inspected. Tested private note isolation, sharing, useful excerpt/source card, first consumption, four-record receipt UI, local task completion/persistence, reload no replay, revoke hiding source, note revision edit, and mobile no horizontal overflow. Agent-browser CLI was absent; the provisioned Playwright Chromium performed the same browser checks. No external data/accounts or inference.

Live current restart passed: INTACT_CURRENT proof, old session expiration, persisted edited note revision2 and completed B task, old consumed job without payload, unavailable old eligibility, and fresh current A answer SUCCEEDED. `.ip01-runtime/app-dev/browser-02/restart-result.json`. Both APP-owned live server directories were stopped using root's exact-identity launcher; latest `control/app-stop-observation.json` reports STOP_CONFIRMED and residual=[] for observed app descendants. This is app shutdown evidence, not model-backend qualification. Root's shared server was untouched.

Exact commands (repository cwd; interpreter always package-local):

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH='labs/ip01'
$env:TEMP=(Join-Path (Get-Location) '.ip01-runtime/app-dev')
$env:TMP=$env:TEMP
$env:HYPOTHESIS_STORAGE_DIRECTORY=(Join-Path (Get-Location) '.ip01-runtime/app-dev/hypothesis')
& ./.ip01-runtime/venv/Scripts/python.exe -m pytest labs/ip01/tests/app/test_application.py -q --tb=short --basetemp=.ip01-runtime/app-dev/pytest-05 -o cache_dir=.ip01-runtime/app-dev/pytest-cache
& ./.ip01-runtime/venv/Scripts/python.exe labs/ip01/scripts/run.py start --runtime-dir .ip01-runtime/app-dev/browser-02 --deadline 2026-09-29T10:10:16Z
$env:PLAYWRIGHT_BROWSERS_PATH=(Join-Path (Get-Location) '.ip01-runtime/cache/ms-playwright')
& ./.ip01-runtime/venv/Scripts/python.exe labs/ip01/tests/app/browser_walkthrough.py browser-02
& ./.ip01-runtime/venv/Scripts/python.exe labs/ip01/scripts/run.py stop --runtime-dir .ip01-runtime/app-dev/browser-02
```

The browser's initial run used private directory `browser` and no script directory argument; the second used `browser-02`. Live restart repeated the latter start/stop and executed the HTTP assertions preserved in `restart-01.log`/`restart-result.json`. Early TestClient smoke ran via package-local Python stdin and retained `skeleton-validation.json` and `smoke-01.log`. Latest browser screenshots: `browser-02/workspace-desktop.png`, `receipt-history.png`, `workspace-mobile.png`.

Failed/partial attempts retained:

- One apply_patch delete/add of app.py in one patch was rejected for duplicate target before writing; ordinary Update File succeeded.
- `pytest-01` with the same test file, private basetemp/cache and `-q` produced **118 fixture errors + 1 failed**. Fixture errors were HTTPX duplicate-domain cookie handling in the author harness. The product failure was a fault injection default: None matched an unlabeled transaction and incorrectly raised COMMIT_UNKNOWN.
- `pytest-02` added `-x --tb=short`: **115 passed + 1 failed**, stopping at that store hook defect after fixture repair.
- Fixed the hook to fire only when explicitly configured. `pytest-03`: **119 passed**. Expanded boundaries/delivery checks in `pytest-04`: **123 passed**. Added exact callback checks in `pytest-05`: **124 passed**. All logs remain; no failed trial removed or relabeled.
- Root independently reported a launcher attempt while static/ was still under construction; retained by QA at reviews/LIFECYCLE-OBS/LAUNCHER_START_FINDING.md. Later complete UI and start/stop executions above passed; original attempt remains evidence.
- Existing `labs/ip01/haven/__pycache__` directory timestamp 00:28 local was observed at final inspection and left untouched. APP executions explicitly disabled bytecode; tests/app has no observed __pycache__. No broad cleanup was performed.

## Interface changes

Factory remains `haven.app:create_app`. Optional Python-only runtime_dir and supervisor_factory support isolated tests. No workers launch on import; lifespan owns Store/Supervisor and closes both. Runtime modules, root __init__/scripts/lock/README, originals, RI01 and root schemas were not edited.

Q-QA-APP-01 exact stable API:

1. GET /api/session creates/reads the bootstrap opaque HttpOnly SameSite=Strict cookie and returns csrf_token. Every mutation needs that cookie, X-CSRF-Token, and Origin exactly matching the allowed loopback host with port8765–8767. POST /api/session {person:"A"|"B"} rotates cookie/token and returns destination_ref. Separate cookie jars allow simultaneous A/B.
2. Notes create {title,text,idempotency_key,parents?}; edits include expected_revision; tombstone DELETE includes expected_revision. Grant POST uses recipient, purpose="answer", expires_at RFC3339, max_uses integer or null, idempotency_key. Revoke uses expected_revision matching authorization_revision.
3. Answers POST uses question, route, destination_ref, idempotency_key; optional source_ids/image_source_id. Returns202 job_id/status_url. GET /api/jobs and /api/jobs/{id} are metadata-only; sources cards carry currently authorized title/revision, never answer payload.
4. Job.output has output_id, release_id, output_digest, destination_ref, nonce, expires_at, consumed. POST /api/outputs/{output_id}/consume includes release_id/output_digest/destination_ref/nonce/idempotency_key. Only first known committed fresh consumption returns payload. Duplicate identical request returns HISTORY_ONLY; conflicting identity/key returns409. No GET/history/reload answer payload.
5. GET /api/outputs/{id}/receipts returns four distinct content-minimal history/current records. Observation POST binds exact consumed tuple, includes consumption_id, kind and idempotency_key; reports may be late without authorizing new output. Already rendered bytes cannot be recalled.
6. POST /api/images accepts raw PNG/JPEG body with MIME type or a multipart file/image field. No URLs/paths/filenames used for storage. Max2MiB file, one frame, 8M pixels, normalized8MiB. Raw image bytes are not retained beyond decode; a metadata-stripped RGB PNG derivative and raw/derivative hashes are retained privately.

Private QA fault seam: TestClient app.state.store.fault_after_commit='release:'+job_id or 'consume:'+output_id raises COMMIT_UNKNOWN after durable SQLite commit/sidecar and before payload return. It is a Python-only seam, no production fault API. Unknown release/consume response observations are retained as events; consumed-slot delivery remains unknown. Evaluator transport may independently discard a real HTTP response. Independent read-only SQLite inspection can use app.state.store.path or `<runtime>/data/haven.sqlite3`, mode=ro. Distinct JSON-record tables: contexts, source_revisions, grants, quota_ledger, grant_use_claims, attempts, events, release_receipts, consumption_receipts, delivery_observations, eligibility_decisions. Mutations remain APP-only. A/B session bindings are credentials: keep raw DB/evidence private.

## Source-use mapping

The frozen source hashes below come from INTAKE's exact Git-byte identity registry, not a child Git operation. Runtime/seam rows use actual current worktree-byte hashes at this handback. Source content was read for the stated adopted behavior; original code/research qualification is not inherited.

| Source | SHA256 | Applied behavior |
|---|---|---|
| `campaigns/RI-01/ri01-20260928T180322Z-6e8f/integration/final-v1/CONTRACTS.md` | `cb6cea47fb00aba89da234da620b3fb3bd240c2a10e314bcc81cbfa647cc4be7` | I01 complete vector and closure; I02/I03 immutable source revisions/context; I04 job/attempt fences; I06 separate receipts. |
| `campaigns/RI-01/ri01-20260928T180322Z-6e8f/integration/final-v1/CONTRACT_CROSSWALK.md` | `0ee3d9eb32f8d87f6d3d8b74cf310f0c4f7632f695f8f15a4b09776792584ea8` | Implementation remains in new lab namespace; no root schema or original qualification claim. |
| `campaigns/RI-01/ri01-20260928T180322Z-6e8f/research/R03/CONTRACTS.md` | `cfd271d1650e40daa735651ddc2ab28ca4ccdcb17f117c96cc5602975bad5eea` | Current rights/grants/source/session/destination checks, serialized write ordering, correction/tombstone/restore boundaries. |
| `campaigns/RI-01/ri01-20260928T180322Z-6e8f/research/R03/amendment-1/AMENDMENT.md` | `b2608ea743084af0f7f854b32b8156dc50e95370051de641ab9ae919ac77e667` | Once-per-release finite claims, separate authorization/accounting revisions, all-or-none distinct grant charges, zero-remaining existing-claim redemption, no refund/replay. |
| `campaigns/RI-01/ri01-20260928T180322Z-6e8f/reviews/REVIEW-R03/CLOSURE-1.md` | `d3e12e1371e04538cadc7ce77c84cd9a1c455282d5df49de7e2c9a46fb98b7be` | Accepted original-plus-amendment composite, preserving original limitations. |
| `campaigns/RI-01/ri01-20260928T180322Z-6e8f/research/R02-P01/amendment-1/AMENDMENT.md` | `3efda1609fb138adc6bef9d125ac2390f4ccc484e797ab2eeefc7f4d26cc3605` | Four orthogonal records, late/unknown delivery retained through revoke/cancel; no false stop claim. |
| `campaigns/RI-01/ri01-20260928T180322Z-6e8f/reviews/REVIEW-R02-P01/CLOSURE-1.md` | `2438d74f574ed79d7613207c2686f6429eb821f1e8ef232dcebc0376bcacf5f4` | Accepted clarification; consumption slot is separate from parent quota and human perception. |
| `campaigns/IP-01/ip01-v2-20260929/integration/SEAM.md` | `09380772d5e19838950d94e4cf94e682fc41d65fed217f8587d2e53b579b0985` (current worktree bytes) | Exact HTTP and Supervisor callbacks, disjoint ownership, no-payload GET and explicit consumption. |
| `campaigns/IP-01/ip01-v2-20260929/receipts/RUNTIME_CONSULTATION.md` | `18eb44ff8b3fd555346ac99ee57b4ca94137e9e1757dd3142ae6767a63be090e` (current worktree bytes) | Actual Q-APP-01/Q-SEAM-01 author answers adopted; not lifecycle qualification. |
| `campaigns/IP-01/ip01-v2-20260929/receipts/MODEL_PREPARATION.md` | `67cbb253d690680fbef6bc62c28854847537e1a874f173a98f91659575e37f3e` (current worktree bytes) | Actual Q-MODEL-SEAM-02 root token pool and limits binding fields adopted; metadata-only gate_snapshot. |

ASTRA reference: tracked `astra/store.py` at `3aa1ac646052124b98c73d9d1f361bef3c123d81`, private reference copy SHA256 independently rehashed as `3533330a1957e5bdeb41275c1a62c5a600efc72cbf8f0f6ad490216fd6be0f75`. Selectively adapted its transaction ownership, PRAGMA verification, digest-conflict and after-commit-hook patterns into new store.py. No wholesale copied file and no source DB/credentials copied. Candidate store.py hash below binds the adaptation. No NIGHT01/R1 code adapted or qualified.

## Owned paths changed and hashes

Only these assigned source/test files, the explicitly requested early readiness marker, and this APP_HANDOFF.md were changed. All other APP execution writes were under `.ip01-runtime/app-dev/**`. This report's own hash is provided in the native final handback, avoiding a self-hash cycle.

| Changed path | SHA256 current bytes |
|---|---|
| `labs/ip01/haven/app.py` | `dfbcab013af21ee086fce8c4d659476d9df47fe6000a6b1f0c34ac6904df1e56` |
| `labs/ip01/haven/store.py` | `602316d179080111732c3e2dbb136ae0d66c7230a543199f43f7631599cadb6d` |
| `labs/ip01/haven/authority.py` | `9c9547375e7cb96b6f159635d0eb24b93ada54b27dc17ba427fccd86836ad3ca` |
| `labs/ip01/haven/contracts.py` | `95a7721f42fc76a38fa457b950d5c1fface81beff0f766e030afd142fa856dd5` |
| `labs/ip01/haven/templates/index.html` | `b5d485d711e392d8c50ba63fd596db7cc5f66494ddb81b28a0413c5a3748f57c` |
| `labs/ip01/haven/static/app.css` | `f237f944b99b79051978874ae4e7e45cfafd1c2e676f3341f2dc6dc7eff92790` |
| `labs/ip01/haven/static/app.js` | `5930eb6331a2dec25d0a69d2ad1ff142666cf85667a9793b311f409ff0a33574` |
| `labs/ip01/tests/app/test_application.py` | `45410aebc3e96d1c932a5be6bdd4f243a61fc748798ae05e3d4e6672e4e5f57b` |
| `labs/ip01/tests/app/browser_walkthrough.py` | `49c602312e21ee4e3796bee8fe1dd2a295b412d989e16c52fee45aee11296557` |
| `campaigns/IP-01/ip01-v2-20260929/receipts/APP_READY.json` | `deec5aa0d863f121145e002c0db66b3f0cb219d91f6808a2c0ea24ec68b64996` |

## Acceptance

Request independent HTTP/browser/security/continuity/model-seam review against these exact candidate bytes and independently produced traces. No self-approval, protected result, canonical CORE-P0/MF-P0/VA-01 result, original R1 qualification, physical/clinical readiness, or model quality claim. Root owns candidate freeze, shared budget/state, broader independent suites and publication.

## Risks and open questions

- No model inference has run in APP. The actual root gate, independent backend cleanup, four exact pins and runtime token/claim accounting must be established before model UI/pilot execution. The new seam is wired, not empirically qualified with a model.
- Author vector tests establish complete captured-precondition rejection but do not replace QA's 104 current-dependency mutation traces. Exact independent boundary-pair coverage, queued/running barriers, corrupt continuity/I/O interruption, and model egress remain for QA. The edge negative case here is144 rather than129; metadata has overflow tests, not a byte-exact two-sided oracle.
- SQLite stores synthetic revision/context/output/history data. Tombstones synchronously deny eligibility; physical erasure, backup expiry and production retention are not implemented/claimed. No model/generated-answer auto-save into ordinary notes/drafts is offered.
- Sidecar proves local commit-sequence continuity under normal ownership. Copying/restoring both DB and sidecar, malicious same-account modification, and filesystem power-loss atomicity are outside this detector's proof. Review-only state has no public unquarantine shortcut; trusted later-history reconciliation remains root-owned work.
- Demo identity selection is deliberately not real authentication. The app is loopback-only and synthetic-data-only; no account/OS isolation or production deployment claim.
- Full process/backend lifecycle, parent-death/capacity and independent worker faults belong to RUNTIME/QA. Deterministic computation is in-process and truthfully leaves owned-worker compute_state NOT_STARTED.
- A consumed response can be lost or rendered after revocation; no server/browser distributed-atomicity or recall guarantee. Reports of display are assertions, not proof of perception.

## Next package

Root can start the shared stable app with its existing launcher, relay this handback to independent QA/code reviewers, and run the authorized operational model gate separately. Root restart command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
& ./.ip01-runtime/venv/Scripts/python.exe labs/ip01/scripts/run.py start --runtime-dir .ip01-runtime --deadline 2026-09-29T10:10:16Z
```

If fixing independent findings, assign a bounded follow-up on these owned paths and retain all failing trials. Do not consume final-suite/model budgets implicitly. APP-owned temporary services and browsers are stopped; native final handback returns control to root. No ancestor app messaging was used.
