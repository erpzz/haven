# Specialist handback — MODEL-READY assignment8

Thread / owner / task ID: ip01_runtime_engineer, assignment8, CUSTOM_PROFILE_FALLBACK, inherited model UNKNOWN. Root `01a0eb51-c8b3-7923-94ed-ea1874de843e`. Task started about05:04Z on2026-09-29 and completed within the assigned25-minute bound. Cutoff09:25:16Z/deadline10:10:16Z unchanged. Native final handback; publication/root ledgers remain root-owned.

Actual work: **four real readiness calls through the root's live HTTP APP**, two text and two image, using separate synthetic A/B sessions, CSRF, current source/image admission, durable APP token bindings, owned Supervisor, APP release and explicit consumption. No direct/fake admission/generation, hidden preload, retry, protected QA fixture, extra model, GPU tuning, provider spending, original writes, recursive agents or Git actions. Candidate source remained unchanged. Root app remains running and was never stopped/reconfigured by this author.

## Decisions

Read and verified actual independent benign gate `reviews/LIFECYCLE-OBS/FINAL_BENIGN_GATE.json`, SHA256 `a63f368b2c788911b950d9696acf30ed02f9533f154c1fdacce7813818124426`, with13 independently passed lifecycle cases on supervisor `9713cac68f27ca627780334e27f2637fc258711da2e8072cd70b6f2cd1ff1437` and worker `db2a24a67de03080aeb5e8ce16942e8f4ef4b37ccc3b4f7b021f2dbdfff50d3d`. Its scope excludes model-backend qualification. Root's separate MODEL_READY_AUTHORIZATION and private gate enabled exactly FOUR readiness slots, with canonical gate SHA256 `08c027002e6e2b1c6abbd37c5186772d2e3766377a16f2bc63c6d504c726799b`.

Kept the reviewed fixed envelope: CPU `num_gpu=0`,4096 context,768 output,one image,120 seconds per attempt,12GiB Job Object committed-memory cap,one workload/model,cloud off. No new acquisition;4.1GiB cumulative download debit unchanged. The worker's actual model route generated all four responses. `/api/ps` was used only for read-only residency observations after verifying the listener belonged to current root-app descendants.

The author created an original448x320 synthetic PNG and actually inspected its pixels using view_image before either image request: white background, blue square on left, red circle on right, no printed numerals. Image SHA256 `69a740d129459ff0f41c2c44a83c27130ba3ea519d658b6a81c90ede9b429ac7`. No protected assets were read. APP normalized the uploads with `PIL_DECODE_RGB_METADATA_STRIPPED_PNG.v1`; both stored context digests and actual image byte hashes matched their sealed identities.

## Evidence

The following are producer observations, not independent semantic acceptance. All API requests/responses, exact process PID+birth identities, sample times and backend residency replies are retained privately in `.ip01-runtime/model-ready/case-01/` through `case-04/`. Public results contain synthetic answer text, hashes and minimized process-identity digests rather than session cookies/CSRF/destination capability material or raw host inventory.

| Case | Actual APP-consumed model text | HTTP submission-to-observation time | Separate semantic/format observation |
|---|---|---:|---|
|1 A private supported text|Tuesday at 09:15 in the Cedar room.|14.469s|Supported by the synthetic note;7 words within requested8.|
|2 B explicitly shared unsupported text|The exact four-digit access code is not recorded.|13.469s|Correctly abstains;8 words within requested12. Owner explicitly shared this note with max_uses1 before B's job.|
|3 A supported image|The square on the left is blue.|35.875s|Matches inspected pixels;**format failure:7 words exceeds requested5**.|
|4 B unsupported image|No number is visible.|36.813s|Matches inspected lack of numerals;4 words within requested12.|

Both text setups checked that B's ordinary note listing did not contain the newly created A-private source before sharing. This is a narrow observed path, not a replacement for independent adversarial isolation testing. Case2 used a fresh explicit grant; all model citations were inside the exact sealed source context. Each session pair used independent HTTP cookie jars and server-generated CSRF/destination bindings.

**Separate phase evidence for every case:** APP job disposition SUCCEEDED; runtime RESULT_DISPOSITION `RELEASE_ADMITTED`; consume `FRESH_CONSUMPTION` returned the exact payload; duplicate consume `HISTORY_ONLY` returned no payload. STOP_CONFIRMED was supported separately by zero active Job Object members, signaled retained handles and no independently sampled PID+birth identity surviving. No browser render/perception claim is made from an HTTP consume response.

| Case | Peak sampled workload RSS bytes | Peak Job Object committed bytes | STOP_REQUESTED to STOP_CONFIRMED | Charged model seconds |
|---|---:|---:|---:|---:|
|1|3,572,289,536|4,644,659,200|41.059ms|13.079|
|2|3,573,530,624|4,645,343,232|32.110ms|13.031|
|3|4,152,123,392|4,721,016,832|38.257ms|35.610|
|4|4,150,755,328|4,718,288,896|41.068ms|35.484|

The three-second stop target was never increased. These are successful-completion shutdown observations, **not timeout/cancel/parent-death model-fault trials**. RAM sampling is not a continuous peak oracle; Job Object committed-memory high-water is separately reported. Observed workload roles included `ollama.exe`, actual `llama-server.exe`, the Python worker and `conhost.exe`; final job accounting included18 transient processes over each workload lifetime and0 active at confirmation. `/api/ps` observed exactly the pinned Q4_K_M manifest, context4096, model residency2,903,066,541 bytes and VRAM0. Residency is not interchangeable with process RSS or Job Object committed memory.

Final independent PID+birth rechecks found0 observed workload survivors and0 listeners on11435–11437. Root app's supplied PID+birth still matched and remained alive. Full owned backend/runner identities, command lines and birth times remain in each private result/sample record; public JSON includes hashes locating those identities and exact source/evidence hashes.

### Exact commands and outcomes

All commands ran from `<campaign>`, using the designated venv. Driver scripts are private evidence tools and make model requests only through APP's `/api/answers` route.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:TEMP=(Join-Path (Get-Location) '.ip01-runtime/model-ready/tmp')
$env:TMP=$env:TEMP
& ./.ip01-runtime/venv/Scripts/python.exe -B .ip01-runtime/model-ready/run_readiness.py 1
& ./.ip01-runtime/venv/Scripts/python.exe -B .ip01-runtime/model-ready/run_readiness.py 2
& ./.ip01-runtime/venv/Scripts/python.exe -B .ip01-runtime/model-ready/run_readiness.py 3
& ./.ip01-runtime/venv/Scripts/python.exe -B .ip01-runtime/model-ready/run_readiness.py 4
& ./.ip01-runtime/venv/Scripts/python.exe -B .ip01-runtime/model-ready/build_results.py
```

Each driver invocation exited0, made exactly one model job, and retained its result and command output; no HTTP/model call failed or was repeated. Aggregation was run once, then rerun after adding explicit release/citation fields; it is read-only with respect to APP/root accounting and makes **no model call**. Initial fixture creation, source-hash checks and GET /healthz used the same venv with -B; the native view_image tool inspected the saved fixture. The root's accounting helper was inspected, not executed, because it appends to a root-owned observation ledger. This author computed the same union read-only into its own readiness directory.

## Interface changes

**None. No candidate file changed, so no app restart or affected source requalification was required by this assignment.** Full before/after SHA256 equality is recorded in MODEL_READY_RESULTS.json. APP final app.py hash `dfbcab013af21ee086fce8c4d659476d9df47fe6000a6b1f0c34ac6904df1e56`, authority `9c9547375e7cb96b6f159635d0eb24b93ada54b27dc17ba427fccd86836ad3ca`, store `602316d179080111732c3e2dbb136ae0d66c7230a543199f43f7631599cadb6d`, model_adapter `0e29edc6f826b04ba8c1bac3a28d55c5a2844f56a20349bb5f321d95577fc0a2`.

Root briefly requested a reload pause while case2 was running, then corrected it after file-time checks showed final application code predated the05:02:32 root start. This author verified all code pins matched initial and final APP hashes before the next submission. No restart, session reset, repeated case, READY_FOR_ROOT_RESTART marker, or renewed budget occurred. Root later explicitly requested preserving code pending coordinated repair; followed.

## Acceptance and accounting

**FOUR_ACTUAL_READINESS_CALLS_COMPLETED_PRODUCER_EVIDENCE**, with independent model lifecycle/semantic review pending. No self-acceptance, protected result, canonical P03/VA-01, production isolation or original R1 qualification.

Conservative union of durable APP allocation_token bindings and runtime CLAIM tokens: **4 consumed readiness slots**,4 APP bindings,4 runtime CLAIMs,4 network-start markers,4 confirmed settlements,0 pending/unknown cleanup,**97.204 charged seconds**. Lifecycle0/8; final0/72; final deterministic suites0/3. Campaign readiness capacity remaining12/16, but **this four-token authorization has0 remaining**. Remaining campaign model-time capacity5,302.796 seconds (88min22.796s), subject to fixed campaign deadline. No token refund/remint, gate copy, isolated-ledger reset, lifecycle token or final token was used. All immutable original entries remain.

## Risks and open questions

1. **R8-F01 audit-label defect:** all SETTLE records say outcome QUEUED because cleanup settlement precedes result validation. Resource charges/cleanup confirmations remain accurate; APP and runtime result events separately prove release admission. Root has relayed this to CODE-EARLY. Do not reinterpret QUEUED as no computation, overwrite old entries, or refund slots. A coordinated repair can append later result disposition and use an explicit cleanup-phase outcome, with root-controlled restart/recheck.
2. **R8-F02 model format failure:** case3's correct color answer violates the requested5-word bound. Retained without retry/tuning/denominator reduction.
3. **R8-L01 token telemetry retention:** exact backend prompt/output counts passed through worker validation but are not persisted in retained APP job/lifecycle records. Config4096/768 and backend residency context4096 are verified; exact per-call token counts are UNKNOWN here. Do not infer them from text length. Root may include usage persistence in a scoped repair.
4. These four small, author-created cases do not establish72-call performance, generalized visual ability, protected benchmark validity, or cancellation/deadline cleanup while actual inference is running. Independent lifecycle allocation and semantic review remain separate.
5. CPU peak observations were below the12GiB cap, but sampled RAM/residency and four successful shutdowns cannot replace deliberate fault trials. Standard-user isolation limitations remain unchanged.

## Source-use mapping

| Actual input | Applied use |
|---|---|
|Independent FINAL_BENIGN_GATE, exact SHA above|Hard prerequisite to the root's separate readiness authorization; no inference permission inferred from the benign receipt alone.|
|MODEL_READY_AUTHORIZATION.json and root private four-slot gate|Exact4-call ceiling, CPU resource envelope, model identity, expiry and root-issued readiness token pool. Both unchanged before/after.|
|APP_HANDOFF and actual app.py/authority.py/store.py/contracts.py|Real session/CSRF/image/note/grant/job/consume HTTP contract; readonly diagnostic rows filtered to this assignment's jobs. APP final hashes matched loaded-start candidate.|
|MODEL_PREPARATION and runtime modules|Pinned qwen2.5vl:3b manifest `fb90415cde1ef08aa669ae74b082d49b158729b6db1ab183c941417d507e71a1`, runtime `d571e4cf0ad4456fccd33d5b985b6d63ba5669c6e5a812391704083952aae3d5`, template `a242d8dfdc8f8c2b0586ee85fba70adb408fb633aba2836fe1b05f2c46631474`, preprocessing descriptor `b6b6a5ebfa3bb4f08f1edad7ae9950d09b79facf9e1ef2be6c16761beb236ee5`; private noncommercial scope reviewed by root remains unchanged.|
|Root accounting clarification and inspected model_budget_observation.py|Union of bindings+claims, no failed-admission refund, immutable settlements; replicated read-only without running its root-ledger append.|
|Author-created synthetic note/image|Useful positive and unsupported questions only; no protected assets/oracles, original project data, accounts or physical sensor input.|

## Owned paths changed

Public-safe candidates only:

- `campaigns/IP-01/ip01-v2-20260929/receipts/MODEL_READY_FINDING.md`
- `campaigns/IP-01/ip01-v2-20260929/receipts/MODEL_READY_RESULTS.json`
- `campaigns/IP-01/ip01-v2-20260929/receipts/MODEL_READY_HANDOFF.md`

Private scripts, fixture, command logs, raw request/response/process evidence, accounting/source snapshots and exact file manifest are under `.ip01-runtime/model-ready/**`. Exact paths/bytes/SHA256 are in `.ip01-runtime/model-ready/ARTIFACT_MANIFEST.json`; final public receipt hashes are returned natively. Normal authorized HTTP execution also wrote synthetic APP data, media, lifecycle evidence and runtime model claims/settlements through their owning implementations. No manual edits to APP database, root gate, model-call ledger, root shared ledgers or candidate source were made.

## Next package

Root should review R8-F01/R8-L01 with CODE-EARLY and the exact successful readiness evidence, then coordinate any source repair/restart and an independently authored model-lifecycle assignment using separate root-issued tokens. Actual inference timeout/cancel/parent-death cleanup and independent semantic conclusions still require their own evidence. This assignment will make **no fifth call**. Native slot is released; root's shared APP stays running under root ownership.
