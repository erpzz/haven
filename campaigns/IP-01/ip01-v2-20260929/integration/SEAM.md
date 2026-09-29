# IP-01 v2 implementation seam — SEAM / H00

Status: READY_FOR_IMPLEMENTATION; Q-SEAM-01 callback consultation pending actual RUNTIME response. This is a proposed implementation contract, not executed acceptance. Author: distinct haven_integration_manager, CUSTOM_PROFILE_FALLBACK; inherited model UNKNOWN; assignment #2. Root: `01a0eb51-c8b3-7923-94ed-ea1874de843e`. No source edits, Git, runtime execution, model calls or child spawning by this task.

## 1. Exact inputs and retained scope

Setup `8e1304caf82c0a889eeaea7691db7b9d7b98c526`; research baseline `6bc1c8df1218ceb0e0d8709adee65d1e44634047`; root reports later launch commit `faaf8ea`. Root-owned `../inputs/SOURCE_IDENTITY.json` is the exact Git-byte identity registry; worktree line endings may differ. INTAKE hard dependency completed by native `01a0eb5c-f3bf-7c52-9bb1-90465cc30b24`. No independent Git verification is claimed here.

`RI` below means `campaigns/RI-01/ri01-20260928T180322Z-6e8f`. Read assigned profile; current IP01 WORK_PACKAGE, START_HERE, ROLE_MAP, AGENT_BRIEFS, SUPERVISOR; RI orchestration MASTER_PROMPT/PROTOCOL/VISION/MULTIMODAL; relevant final-v1 CONTRACTS/CROSSWALK and exact R03/P01 amendments and closures. Their operational meaning controls over historical research-only launch restrictions, within this task's narrower documentation scope.

| Input / exact SHA256 Git bytes | Applied here |
|---|---|
| final-v1/CONTRACTS.md `cb6cea47fb00aba89da234da620b3fb3bd240c2a10e314bcc81cbfa647cc4be7` | I01–I06 full vector, influence closure, bounds, jobs, resource accounting, four output records |
| final-v1/CONTRACT_CROSSWALK.md `0ee3d9eb32f8d87f6d3d8b74cf310f0c4f7632f695f8f15a4b09776792584ea8` | Existing evidence/context/agent_job/delivery_receipt boundaries; no new authority service |
| R03/amendment-1/AMENDMENT.md `b2608ea743084af0f7f854b32b8156dc50e95370051de641ab9ae919ac77e667` + reviews/REVIEW-R03/CLOSURE-1.md (exact hash in identity registry) | One committed release charges each distinct finite grant once; existing claim consumes at zero remaining quota; immutable history |
| R02-P01/amendment-1/AMENDMENT.md `3efda1609fb138adc6bef9d125ac2390f4ccc484e797ab2eeefc7f4d26cc3605` + reviews/REVIEW-R02-P01/CLOSURE-1.md `2438d74f574ed79d7613207c2686f6429eb821f1e8ef232dcebc0376bcacf5f4` | Four orthogonal records replace combined publication enum; cancellation never rewrites delivery |
| final-v1/MANIFEST.json `c5ec562b5ea5390962ab8334b39f397e959a071a4314c3b17898ec991b3ede1b` | Identifies inherited frozen synthesis; does not qualify implementation |
| `../inputs/ORIGINAL_SOURCE_BASELINE.json` | ASTRA store reuse attribution; NIGHT01 historical source is not qualified R1 |

ASTRA is reported clean at `3aa1ac646052124b98c73d9d1f361bef3c123d81`, Ubuntu-24.04 `~/projects/project-astra`. Its tracked `astra/store.py` private reference copy has SHA256 `3533330a1957e5bdeb41275c1a62c5a600efc72cbf8f0f6ad490216fd6be0f75`; APP may selectively adapt transaction/receipt patterns with source-to-copy attribution, without copying DBs or credentials. NIGHT01 backend/coordinator match historical P01 snapshots per root, but have no repository identity: implement a NEW WINDOWS LABORATORY SUPERVISOR, never claim R1 repair. Root contracts/README is absent; read recovered `RI/inputs/recovered/starter/contracts/README.md` as inert design reference.

Useful slice: two invented people, private/shared current notes, saved drafts/tasks, source-linked deterministic answers, asynchronous jobs and selected-image local-model answers when operationally gated. Multimodal/speech/spatial/Observatory/physical and engineering vision remains retained and deferred to separately qualified packages; this implementation does not replace it. A changed upstream hash invalidates only the affected seam/tests and requires explicit reconciliation.

## 2. Disjoint ownership (effective immediately for dispatch)

All candidate paths relative to repository root. No agent edits another owner's paths; root serializes any later reassignment.

| Owner | Exclusive writable candidate files |
|---|---|
| APP | `labs/ip01/haven/app.py`, `store.py`, `authority.py`, `contracts.py`, `templates/**`, `static/**`; `labs/ip01/tests/app/**` |
| RUNTIME | `labs/ip01/haven/supervisor.py`, `worker.py`, `model_adapter.py`; `labs/ip01/tests/runtime/**` |
| root | `labs/ip01/haven/__init__.py`, `labs/ip01/scripts/**`, `labs/ip01/requirements.lock`, `labs/ip01/README.md`, any packaging config or common conftest; shared campaign ledgers/publication |
| QA | Independent harness/fixtures/oracles in `<evaluator>`; sanitized reports only in its root-assigned campaign QA directory. Candidate source is read-only. Root may copy reviewed public test artifacts into `labs/ip01/tests/independent/**` after freeze/ownership handoff. |
| H00 / this task | Only `campaigns/IP-01/ip01-v2-20260929/integration/**` |

APP writes shared wire dataclasses/Pydantic models once in `contracts.py` from this seam. RUNTIME may initially use mappings with these exact keys; no runtime dependency on FastAPI or SQLite. APP imports RUNTIME only inside app lifespan/factory, avoiding circular imports. `authority.py` imports contracts/store, never supervisor. Dependencies remain the package's Python 3.12/FastAPI/Pydantic2/Jinja2/Uvicorn/SQLite stack. No broker.

## 3. Runnable composition and startup

APP exports `create_app() -> FastAPI`. Root provisions one native Windows venv, data directory and exact lock, then uses from the repository root:

```powershell
$env:HAVEN_RUNTIME_DIR = Join-Path (Get-Location) '.ip01-runtime'
$env:HAVEN_ROUTE = 'deterministic'
& .\.ip01-runtime\venv\Scripts\python.exe -m uvicorn haven.app:create_app --factory --app-dir labs/ip01 --host 127.0.0.1 --port 8765 --workers 1
```

This is the target command; H00 did not run it. Root verifies its provisioned venv path and selects the first free owned app port 8765–8767. No reload or persistent service. All DB/media/log/temp/cache files stay inside `.ip01-runtime`; default DB is `data/haven.sqlite3`. Root's currently installed Ollama is a separate owned backend launch on 11435–11437 with its own runtime/model directory; installed binary does not prove any inference or stop qualification. Model route remains unavailable until root publishes exact artifact/runtime/rights and demonstrated ownership/stop readiness. No fallback model/provider.

FastAPI lifespan opens/migrates Store, establishes authority epoch/session state, performs recovery, constructs one Supervisor and closes it on shutdown. Root records exact app/backend PID+birth identity and uses owned handles for stop. Workers are not started merely by importing modules.

## 4. HTTP contract owned by APP

All state-changing routes require an authenticated simulated session, CSRF token and exact allowed Origin/Host. A/B selector is visibly demo login, not real identity authentication. No caller-supplied principal overrides session identity. Independent A/B cookie jars; server-generated opaque session/device/destination bindings. Escape all note/model/image metadata. No raw HTML/model tools. Status/reconciliation reads return only currently authorized, content-minimal facts.

| Method/path | Request and response / authority ordering |
|---|---|
| `GET /`, `GET /healthz` | Jinja UI; public health returns service/readiness only, no user/job/source inventory |
| `POST /api/session` | `{person:"A"|"B"}` via same-origin demo form/bootstrap CSRF; rotates opaque cookie and CSRF; returns simulated identity + destination binding |
| `GET /api/notes` / `POST /api/notes` | Eligible notes; create `{text,title,idempotency_key}` -> `{note_id,revision,commit_receipt}`. Creator from session. |
| `PATCH /api/notes/{id}` / `DELETE /api/notes/{id}` | `{expected_revision,...}`; CAS edit/tombstone and synchronous derivative invalidation; 409 stale revision |
| `POST /api/notes/{id}/grants` | Owner-only `{recipient,purpose,expires_at,max_uses,idempotency_key}`; explicit whole-output profile; server validates scope and records authorization revision |
| `POST /api/grants/{id}/revoke` | Owner-only expected authorization revision; advances revocation epoch atomically |
| `GET/POST /api/drafts`, `PATCH /api/drafts/{id}` | Durable local draft/task; `{kind:"draft"|"task",text,expected_revision}` as appropriate. LOCAL_ONLY means no dispatch boundary exists; no schedules/provider effects. |
| `POST /api/images` | Bounded PNG/JPEG upload bytes, never URL/path; returns owned source ID/revision and preprocessing identity |
| `POST /api/answers` | `{question,route:"deterministic"|"model",image_source_id?,idempotency_key,destination_ref}` -> 202 `{job_id,status_url}`; no answer payload yet; identical request returns same job metadata |
| `GET /api/jobs/{id}` | Current-authorized job metadata, queue/execution/stop axes, safe errors, source eligibility summaries and release ID if admitted; NEVER payload bypass |
| `POST /api/jobs/{id}/cancel` | Session/job owner; atomically advances cancel epoch/fence, then requests owned runtime stop; returns observed state, never assumed stop |
| `POST /api/outputs/{id}/consume` | `{release_id,output_digest,destination_ref,nonce,idempotency_key}`; fresh transaction, one matching slot. First known commit may return `{payload,ConsumptionPermitReceipt}` once; duplicate returns history only, never payload/usable permit. |
| `GET /api/outputs/{id}/receipts` | Currently authorized content-minimal four-record history/reconciliation; no transmission/replay |
| `POST /api/outputs/{id}/observations` | Exact release/consume/output/destination tuple and authenticated reported event; append only, never grant authority |

201 creates records; 202 admits queued work; 401 missing session; 403 denied/CSRF; inaccessible object IDs may return uniform 404; 409 revision/idempotency/fence conflict; 413 limits; 422 unsupported profile/input; 503 route unavailable/store busy/unknown admission. Structured `{code,message,operation_id?,retryable}`; no disclosure of other person's existence/content. Network retry never changes operation keys. Output reload does not silently reconsume/replay; user may explicitly request a fresh operation after reconciliation/current authority.

## 5. Callable job and authority seam

Proposed signatures are exact integration targets; APP owns contracts; RUNTIME implements Supervisor. Async methods run on the application's event loop, while actual computation runs in owned child processes. No model/network wait or process wait holds a DB transaction.

```python
class Supervisor:
    def __init__(self, *, runtime_dir, admit_attempt, on_event, on_result): ...
    async def start(self) -> None: ...
    async def submit(self, job: dict) -> dict: ...
    async def cancel(self, job_id: str, cancel_epoch: int, reason: str) -> dict: ...
    async def snapshot(self, job_id: str) -> dict: ...
    async def close(self, deadline_monotonic: float) -> dict: ...

# APP callbacks, awaitable; transactions completed before returning:
async def admit_attempt(job_id: str, attempt_id: str, fence: int) -> dict: ...
async def on_event(event: dict) -> None: ...
async def on_result(result: dict) -> dict: ...

# APP authority operations (Store passes its current transaction):
def build_context(tx, session, request) -> dict: ...
def check_current(tx, vector, *, phase, operation, now) -> dict: ...
def authorize_release(tx, candidate, *, release_key, request_digest) -> dict: ...
def consume_output(tx, session, request) -> dict: ...
```

`submit` accepts a durable APP-created job reference: `{job_id,request_id,request_digest,attempt_id,lease_fence,cancel_epoch,route,deadline_utc,max_elapsed_ms,reservation_id}`. Immutable request includes purpose, exact destination, source selection/question and sealed output profile. Same tuple is idempotent; conflicting reuse rejects. Queue admission is NOT process admission and does not claim RUNNING.

Immediately before launching actual work RUNTIME awaits `admit_attempt`. APP freshly checks source/grant/session/rights/time/cancel/lease/epoch conditions, records attempt admission and resources atomically, and returns `{decision:"ADMITTED",context,authority_vector,job,limits,model_identity}` or `{decision:"DENIED"|"UNKNOWN",reason}`. For model calls, root's allocation/attempt token is required and durably claimed once; all admitted failures/cancelled/preload calls count in the original 16/8/72 allocations. Grant-use release quota is separate and is NOT charged here. No admission on callback failure. A queued job is rechecked at start, not trusted from queue time. Cancellation between admission and spawn is rechecked locally; any remaining race fences results and is reported rather than declared impossible.

`context` is a bounded current snapshot containing all influencing source revisions/parents, permitted excerpts, image bytes/preprocessing references, omissions and the complete vector. RUNTIME/worker receives no DB handle, principal credentials, grant-writing API, arbitrary file path, shell or model tools. Worker pipes use bounded typed JSON/framing; image bytes are supplied by APP from its reviewed import, not model-selected paths.

`event` binds `{event_id,job_id,request_id,attempt_id,worker_instance_id,pid,process_birth,boot_id,nonce,lease_fence,cancel_epoch,kind,observed_at,evidence}`. APP checks identity/fence, appends idempotently and never trusts a worker's authority decisions. Preserve duplicate/conflicting/stale-event history while preventing state regression. RUNTIME retains the exact owned process handles needed for termination observation.

`result` binds the same execution identity plus `{request_digest,context_digest,output_digest,payload,source_refs,model_identity,outcome,usage,certainty}`. Actual payload hash must match; source citations must be a subset of context, while authority checks include ALL influencing context/ancestor dependencies whether cited or not. `on_result` returns `{disposition:"RELEASE_ADMITTED"|"FENCED"|"REJECTED"|"UNKNOWN",release_id?}` after APP's release transaction. A worker result never sends directly to a browser. Late/duplicate results append minimal audit facts but cannot trigger a second release. Deterministic answers pass the same release/consume boundary and are labeled deterministic; they may execute directly in APP without claiming a process ran.

Compute states: NOT_STARTED/RUNNING/STOP_REQUESTED/STOP_CONFIRMED/UNKNOWN, distinct from job disposition QUEUED/SUCCEEDED/FAILED/CANCELLED/INCONCLUSIVE and from output eligibility/delivery. SUCCEEDED means a validated compute result exists, not authorized display. STOP_CONFIRMED requires observed owned workload termination including relevant descendants/dedicated backend; wrapper exit or cancelled HTTP stream is insufficient. Uncertain cleanup retains capacity/uncertainty and blocks new model admission. Parent-death, timeout and crash paths need real independent observations; no R1 claim.

## 6. SQLite ownership, full vector, and receipts

APP Store is the only DB writer and migration owner. One Uvicorn process; a process-local writer lock serializes short transactions. Each connection uses foreign keys, bounded busy timeout, WAL if supported/verified and synchronous FULL. Connection/thread use must follow SQLite's rules; never share an active transaction across callbacks/threads. Use `BEGIN IMMEDIATE` for all authority mutations, release, consumption, job admission/fencing and budget reservations. DB constraints remain the final guard against races. Worker and model adapter never open the DB. QA normally tests through HTTP, with any read-only DB inspection separately recorded.

Store persists principals/demo sessions/devices, sources/immutable revisions, parent edges, grants, quota ledger, GrantUseClaims, drafts/tasks, jobs/attempts/events, sealed contexts, outputs/outbox, the four record tables and restore/reconciliation facts. Mutable current projections point to append-only history. CAS mutations and lineage updates share one transaction. Unknown commit forbids send and requires same-key read-only reconciliation, never a replacement key or refund. Do not hold transactions during model calls or delivery.

Complete AuthorityVector keys are mandatory (including explicit local NOT_APPLICABLE, never omitted wildcard): `vector_version`; `authority_instance_epoch`, `restore_epoch`; `policy_ref`, `purpose_definition_ref`, `rights_policy_refs[]`; `principal_ref`, `session_revision`, `device_binding_revision`, `device_epoch`; `service_capability_revision`, `tool_catalog_digest`; `grant_dependencies[{id,revision,revocation_epoch}]`; `source_dependencies[{id,revision,sha256,lineage_epoch,authenticity_epoch}]`; `subject_scope_revision`, `participant_area_scope_revision`; `job_ref`, `lease_fence`, `cancel_scope_epochs[{scope_id,epoch}]`; `destination_ref`, `destination_epoch`, `audience_revision`, `route_profile_revision`; `provider_data_policy_revision`; `dependency_closure_digest`, `canonicalization_version`.

Check complete current dependencies at retrieval, attempt admission, model egress if applicable, release and consumption. Canonicalization is a pinned versioned deterministic UTF-8 JSON profile (sorted object keys, explicit ordered arrays, no NaN/Infinity, no implicit Unicode mutation); raw byte digests remain distinct from canonical metadata digests. All ancestors/cached intermediates/influencing grants participate, not only cited notes. Cycles, missing closure or overflow reject: two people, 32 sources, 16 grants, 128 edges, depth16, metadata64KiB, output256KiB per operation. No truncation that changes authority.

Four distinct persisted records: ReleaseAuthorizationReceipt (immutable committed admission), ConsumptionPermitReceipt (immutable exact slot redemption), DeliveryObservation (append-only reported observations), PermitEligibilityDecision (fresh current check; never bearer permission). Bind whole-output digest/canonicalization, destination/route/audience, sequences, nonce where applicable, and full checked vector. Internal release outbox contains data eligible for later consumption; GET/poll/history cannot bypass consumption.

Only `ONE_RELEASE_ONE_DESTINATION_WHOLE_OUTPUT`. Release atomically rechecks current vector, deduplicates grants by exact grant/profile, verifies each remaining quota, inserts one immutable GrantUseClaim per applicable finite grant, increments each accounting_sequence/charged_units, creates one consume slot and receipt/outbox: all or none. Quota accounting changes do NOT change grant authorization_revision. Consumption checks current authority/expiry/bindings but does not require unused parent quota and never debits it again. A max_uses=1 committed claim therefore redeems its own slot once at remaining0. Unique release key/request digest and unique consume slot enforce duplicate history without new send. Wrong key tuples reject. No refunds on cancel/revoke/lost reply, no automatic replay/remint.

Missing ACK stays DELIVERY_UNKNOWN or SENT_UNACKNOWLEDGED; revoke denies future eligibility without erasing earlier display. Consumption commit and browser rendering are not distributed-atomic; retain in-flight disclosure race and any consumed-slot response uncertainty. Authenticated browser DISPLAY_REPORTED is a report, not proof of perception. Never claim NOT_SENT from absence of an ACK.

## 7. Safe images and restore

APP accepts only upload bytes with a bounded 2MiB request file, decoded PNG/JPEG, one still frame and at most 8 million pixels; reject decompression bombs, mismatched formats, animations, unknown/executable containers and malformed/truncated images. Decode under explicit limits using the locked Pillow; ignore filenames for storage, strip metadata from model derivatives and bound normalized derivative bytes to 8MiB. Assign server-owned source IDs and private storage paths; bind raw digest, decoded dimensions and exact preprocessing/derivative digest. Retain only scoped originals/derivatives under declared retention. Neither HTML nor worker APIs accept arbitrary URL/path imports. These tighter provisional image bounds may be adjusted only before fixture/evaluation freeze with an explicit seam revision.

Ordinary restart does not silently resume jobs/permits. New worker-instance/fences invalidate old results; reconcile exact prior process identities before releasing uncertain capacity. Root/APP must demonstrate an intact-current store continuity mechanism (e.g. separately retained checkpoint evidence bound to DB generation/commit sequence) before treating a restart as current; DB opening/integrity_check alone is insufficient. If continuity is unproven, default to quarantine/review-only. This proof is a laboratory accident/rollback detector, not host-administrator tamper protection.

Any backup/import/rollback/uncertain intactness produces fresh authority_instance_epoch and restore_epoch, expires sessions, fences jobs/leases/permits, and enters review-only. Restore does not autoexecute queued jobs/timers or preserve executable credentials. Reconcile trusted later revocations/tombstones/quota claims before reauthorization; if history is incomplete, data stays quarantined and finite quota cannot be reset. Historical evidence may be inspected only under current authority; newly approved operations require fresh keys/grants where appropriate and never reuse consumed slots. Root owns restore scripts, APP owns the policy/store primitives, QA tests both demonstrated current restart and rolled-back/unknown cases.

## 8. First implementation/QA handoff and consultation

**Q-IP01-01 — actual root consultation, ANSWERED by H00.** Root scheduler asked before APP dispatch whether metadata-only polling plus fresh POST consumption should replace cached-answer GET. Decision: adopt root's proposed interface exactly. `GET /api/jobs/{id}` never returns answer bytes; only the first known successfully committed `POST /api/outputs/{id}/consume` can return payload to its bound destination/session. Duplicate consume, receipt lookup and page reload return currently authorized immutable history with no payload or usable permit. If the first response is lost, retain consumed-slot/response uncertainty; never resend automatically. A browser may keep already received bytes in its current rendered view without refetching, but no localStorage/service-worker answer cache or automatic replay on reload. UI shows "Previously consumed; reload does not replay this answer" and offers only an explicit fresh answer request under current eligibility/quota. Note reads remain separately authorized source-read operations; they must not retrieve stored generated-answer bytes or imply a release grant. Contract basis: I06 immutable receipts are history, R03-A1 A3/A4 permit-slot redemption is once only, and explicit replay requires a new operation/charge. APP/RUNTIME/QA must assert that polling, duplicate consumption and reload disclose no cached output. This is an attributed design response, not independent empirical acceptance.

APP can build deterministic positive A/private, B/denied, explicit shared B/answer, notes/drafts and four-record delivery immediately. RUNTIME can build benign owned processes/cancel/deadline/crash/parent-death observation using the proposed callback. QA can prepare independent sessions and tests against the HTTP table without seeing protected candidate answers. Integrate once useful source-backed deterministic output traverses release and consumption; then gate the single qwen2.5vl:3b route. No model calls are requested by this H00 task.

Required empirical cases: useful allowed answer; private cross-person denial; shared answer; correction/revoke of an uncited ancestor while queued/running; finite max_uses=1 release then consume; concurrent joint-grant all-or-none admissions; duplicate release/consume/results; unknown release commit; lost consume reply; lost ACK then revoke; wrong output/destination; explicit replay denial; safe/hostile image imports; worker stop/timeout/crash/parent-death/stale fence/restart/capacity; current versus rollback restore. Preserve failing trials. Final deterministic qualification at most three suite starts; all model attempts count in 16 readiness/8 fault/72 final allocations. Distinct final code/vision/evidence reviewers inspect frozen candidate plus independent QA; this seam cannot self-accept.

Q-SEAM-01, asking H00 to root for actual RUNTIME author: **Can RUNTIME implement the injected async `admit_attempt(job_id, attempt_id, fence)` callback immediately before owned process/backend admission, with APP the sole SQLite/authority writer, or does its actual Windows process topology require one specific interface change?** Evidence: final-v1 I01/I04/I06, R03 A1 and P01 A1 above; alternative DB-polling supervisor adds writer/authority coupling. Affected APP/RUNTIME/QA. Request one attributed callable/topology response, maximum two rounds, no broad redesign. Callback is a reversible provisional design, not consensus.

Actual messaging attempt: `mcp__codex_app__send_message_to_thread` to root returned `cannot send to your native ancestor`; no native parent messaging capability was exposed in tool discovery. This question is therefore delivered through the final native handback for root relay; no delivered message or author answer is claimed. Root appends real question/response/decision to its consultation ledger. Keep unrelated implementation moving.

Deadline retained exactly as assigned: feature cutoff 2026-09-29T09:25:16Z; stop deadline 2026-09-29T10:10:16Z. Tool clock during this task read about 04:17Z; no campaign deadline was recomputed. Root retains shared budget/state ownership. Expected next action: dispatch APP/RUNTIME/QA on the disjoint paths, relay Q-SEAM-01, and release this H00 slot. Actual result of this task: documentation only; runtime/tests/model NOT_EXECUTED; source review and independent acceptance still required.
