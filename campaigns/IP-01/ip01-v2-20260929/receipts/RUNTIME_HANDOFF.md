# Specialist handback — RUNTIME assignment 4

Thread / owner / task ID: ip01_runtime_engineer, assignment4, H02 implementation role; CUSTOM_PROFILE_FALLBACK, inherited model UNKNOWN. Root `01a0eb51-c8b3-7923-94ed-ea1874de843e`; campaign IP-01 v2. Return through native final handback, not app ancestor messaging. Publication NOT_UPLOADED/root-owned. No Git actions, shared-ledger edits, native children, PR19 actions, original/root-schema/RI01 edits, private accounts/devices, provider spending, or policy workarounds.

Input repository version and hashes: operator-pinned setup `8e1304caf82c0a889eeaea7691db7b9d7b98c526`, baseline `6bc1c8df1218ceb0e0d8709adee65d1e44634047`. No independent Git verification performed. Exact Git-byte inputs come from root's `inputs/SOURCE_IDENTITY.json`; worktree output hashes below identify implemented bytes. INTAKE and H00 SEAM dependencies received. Feature cutoff09:25:16Z and campaign deadline10:10:16Z on 2026-09-29 preserved.

Requirements covered: IP workstream B and preparation-only part of C; I01/I04/I06 and accepted R03/P01 authority/cancellation distinctions. Actual work: NEW Windows laboratory supervisor, fixed worker, gated local model adapter, real owned-process development faults, exact model acquisition/pins, no inference. This does not repair or qualify original R1, canonical P03, VA-01 or production containment.

## Decisions

SEAM async callback signatures retained exactly. APP alone writes SQLite and authority. Queue admission does not imply process admission. Runtime awaits APP admission, rejects denied/unknown/failure, checks local cancellation after the await, and attributes results to PID+creation FILETIME+boot GUID+worker-instance+nonce+attempt+lease/cancel/request/context identity. APP receives only validated candidates and freshly decides release. Runtime never sends browser payloads.

An unnamed Windows kill-on-close Job Object is attached atomically with CreateProcess's JOB_LIST attribute; no suspended-before-assignment orphan window. The job handle is not inherited. Only retained owned handles/job handles are terminated. Relevant descendants/backend belong to the same job. STOP_CONFIRMED requires active job member count0 plus signaled owned handles; a fenced output or exited wrapper is insufficient. Unknown observation retains capacity and quarantines future admission. Private lifecycle JSONL is append-only and fsynced. Restart never reexecutes old jobs; live/uncertain predecessor blocks admission; clean restart permits fresh IDs only.

The benign probe observed3 members including the fixed descendant, then0 in about0.015 seconds, with a separate control survivor. Freeze `runtime-dev/STOP_TARGET_FREEZE.json` set **3.0 seconds** before measured faults. Independent QA's initial two-member topology and root's app20-second bound remain distinct; no stop target was raised.

Root model gate uses a bounded token pool. Trusted APP binds an unused token to the actual immutable job inside its admission transaction; adapter fsyncs one claim under a process-wide Windows file lock before backend admission. Hard caps16 readiness /8 lifecycle /72 final, 5400 total charged seconds, fixed campaign expiry, no reuse/refund, no hidden warmup. Unknown real cleanup blocks the ledger. Exact schema and source attribution are in MODEL_PREPARATION.md; actual consultation answers are in RUNTIME_CONSULTATION.md. The gate is absent and model route remains unavailable until separate root MODEL-READY.

## Evidence

All Python execution used `.ip01-runtime/venv/Scripts/python.exe` (3.12.3); fixed worker process uses that environment's actual base interpreter with `-I -B` and stdlib only. Author-owned runtime/material remains under clone `.ip01-runtime/model/` and `.ip01-runtime/runtime-dev/`. Worker environment is constructed from an allowlist; no ambient credentials/proxies/PYTHONPATH, no shell/model tools. This is not an OS filesystem/network security sandbox.

Command environment for the recorded development tests (PowerShell from clone root):

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH=(Join-Path (Get-Location) 'labs/ip01')
$env:TEMP=(Join-Path (Get-Location) '.ip01-runtime/tmp')
$env:TMP=$env:TEMP
$env:HYPOTHESIS_STORAGE_DIRECTORY=(Join-Path (Get-Location) '.ip01-runtime/runtime-dev/hypothesis')
& ./.ip01-runtime/venv/Scripts/python.exe -B -m pytest labs/ip01/tests/runtime/test_runtime.py -q --basetemp=.ip01-runtime/runtime-dev/fault-test-04 -o cache_dir=.ip01-runtime/runtime-dev/pytest-cache
& ./.ip01-runtime/venv/Scripts/python.exe -B -m pytest labs/ip01/tests/runtime/test_model_gate.py -v --basetemp=.ip01-runtime/runtime-dev/gate-test-02 -o cache_dir=.ip01-runtime/runtime-dev/pytest-cache
```

Those are exact completed commands; use a fresh basetemp/log suffix for any future run so retained trials are not overwritten. Seven development pytest invocations occurred. No invocation was a final qualification suite. Initial runs also used explicit -B/private pytest/temp paths; later commands explicitly set Hypothesis storage. No Hypothesis-generated tests were run here.

| Command / attempt | Actual outcome | Retained private evidence under `.ip01-runtime/runtime-dev/` |
|---|---|---|
| Direct OwnedJob/OwnedProcess `print(123)` probe via venv `-B -c` | PASS, bounded output and observed stop | `probe-01.log` |
| `pytest test_runtime.py::test_benign_owned_process_and_control -v --basetemp=.../probe-test-01 -o cache_dir=.../pytest-cache` | 1 passed; control alive, descendants observed; stop threshold then frozen | `pytest-probe-01.log`, probe JSON, `STOP_TARGET_FREEZE.json` |
| `pytest test_runtime.py -v --basetemp=.../fault-test-01 ...` | 16 passed | `pytest-fault-01.log` |
| `pytest test_runtime.py -v --basetemp=.../fault-test-02 ...` | 17 passed, including UNKNOWN-observer capacity hold | `pytest-fault-02.log` |
| `pytest test_model_gate.py -v --basetemp=.../gate-test-01 ...` | 12 passed/1 FAILED; lock initializer read an already locked byte, causing PermissionError before typed capacity rejection | `pytest-gate-01.log` |
| Same gate test command with `gate-test-02` | 13 passed after using file size instead of reading the locked byte | `pytest-gate-02.log` |
| `pytest test_runtime.py -v --basetemp=.../fault-test-03 ...` | 17 passed/1 FAILED; test-authoring UnboundLocalError from assertion before candidate fixture construction | `pytest-fault-03.log` |
| Exact final runtime command above | 18 passed after moving the assertion; includes malformed duplicate nonregression and clean restart/fresh job | `pytest-fault-04.log` |
| `python -B labs/ip01/tests/runtime/prepare_model.py probe --runtime-dir .ip01-runtime` first | FAILED_RETAINED, version endpoint timeout after listener bind; all owned job members stopped | `model-probe-01.log` and private preparation receipt |
| Same probe after bounded polling repair | PASS within original launch bound, owned cleanup confirmed | `model-probe-02.log` |
| Same preparation script with `acquire` | PASS, official single artifact, full blob hashes, show metadata, all backend members stopped, zero inference | `model-acquire-01.log` |
| Authenticode read-only inspection of pinned installed binary | Valid Ollama Inc. signature | Tool output; executable hash recorded in MODEL_PREPARATION |
| Private full runtime-library and model identity verification | PASS;989 existing library files pinned and all model blobs verified | `model-identity-01.log` |
| Final compile via Python `compile(source, path, 'exec')` | Seven owned Python files compiled without creating pyc; constructor signature exact; gate disabled | `final-compile-and-source-pins.log` |
| Exact backend birth/boot rechecks and dedicated-port observation | Successful prep backend identities absent;0 dedicated listeners | `final-private-observation.json` |

Acquisition: **3,200,627,168 new model bytes**, total conservative campaign debit **4.1 GiB** including earlier1 GiB and metadata overhead;7.9 GiB download allowance remains. Runtime storage observation **4,181,347,512 bytes**, under20 GiB, retained free disk above10 GiB. The official web reader returned an internal error for the raw registry manifest; direct TLS retrieval from the same official registry succeeded. This was a metadata reader failure, not a policy denial. No other model/provider was tried.

Initial model envelope fixed CPU-only:4096ctx/768output/1image/120seconds/12GiB committed Job Object memory, one loaded model/request, cloud off. GPU free-memory snapshot was considered but does not measure inference peaks; CPU retains tested host-memory enforcement. Latency, actual model memory/context fit and inference cancellation remain untested. No comparative inference calls. Manifest `fb90415cde1ef08aa669ae74b082d49b158729b6db1ab183c941417d507e71a1`; all remaining artifact/runtime/license/template/preprocessor hashes and the registry/upstream license discrepancy are recorded in MODEL_PREPARATION.md.

## Interface changes

No SEAM callback amendment. Implemented constructor and async start/submit/cancel/snapshot/close exactly. `submit` accepts precisely SEAM's eleven durable job fields; callback ADMITTED response must echo that exact `job`, with context/vector/limits/model_identity. `source_refs` are source-ID strings (matching APP), with revisions in the full context/vector. Context digest excludes only its own `context_digest` field; mismatch rejects. APP must seal image_base64/image_sha256/preprocessing data before admission, and actual derivative bytes must match. No URL/arbitrary-path image imports or model-generated execution.

Model additions live only in the private preparation/gate interface: `ModelAdapter.gate_snapshot()` returns pool metadata/hash, never calls a model. APP returns model_attempt_token/model_allocation/model_binding_id/model_gate_sha256 in limits; root-model identity must match four pins and inference_authorized=true. Adapter rechecks actual files. Installed runtime is read from private runtime-pin.json so the minimal app environment needs no LOCALAPPDATA. Queued duplicate/conflicting/stale results are audit facts, not another release. Receipt callbacks have bounded waits and callback uncertainty never grants authority.

Independent fault seams and exact READY hashes are in the consultation receipt. A final supervisor result-schema validation change explicitly superseded its earlier ready hash; worker stayed unchanged. QA must use the final hashes below and recheck affected cases if it inspected intermediate bytes.

## Acceptance

IMPLEMENTED + EXECUTED_DEVELOPMENT, **independent review/acceptance pending**. Latest tests:18 lifecycle +13 resource-ledger cases passed. Actual lifecycle coverage: useful deterministic process result, cancellation during admission/running, denied/unknown admission, crash, malformed IPC, stale fence/hash, delayed/deadline discard, duplicate result, output-fenced/stop-independent semantics, real parent death with independent retained outer job/control observation, clean restart fresh job, old-job rejection, live predecessor quarantine, and injected observer UNKNOWN retaining capacity. The observer-unknown test simulates unavailable evidence after a real stop; it is not a reproduced OS refusal to terminate.

Parent-death test kills only the exact parent handle while retaining its outer containment job, so child disappearance cannot be attributed to observer termination of the containing job. Separate control process survives. Candidate tests are producer evidence; root's distinct LIFECYCLE-OBS assignment must decide independent findings. Original R1 remains unqualified.

Budget additions: **0/96 model calls**, **0/3 final deterministic suites**, no provider cost;7 development pytest starts. Unit-ledger claims are isolated artificial records with no backend call; they are not actual campaign model reservations. All preparation services owned by this assignment are stopped. Root/APP services owned elsewhere were not terminated or reconfigured.

## Risks and open questions

- Actual inference, tokenizer/image-context fit, semantic usefulness, CPU throughput and running-backend cancellation require the separate root allocation. A loaded model or HTTP stream close has not been tested or misreported as backend-stop evidence.
- Full runtime/preprocessor identities are pinned, but upstream reference processor configuration is not proof of native Ollama transformation equivalence. APP derivative identity participates separately in every sealed context.
- Standard-user Job Objects/private directories do not isolate an adversarial process from all filesystem/network capabilities or host administrators. The fixed worker has no arbitrary execution/tool surface; no production sandbox qualification is claimed.
- Store continuity, grants/release/consume, images and browser UI remain APP/root responsibilities. This author did not accept their implementation or touch their files. Root must reconcile current versus rollback state before ordinary restart authority.
- The first failed backend probe retained job cleanup but not its individual backend identity; successful later probes retain exact identities and were rechecked absent. This gap is disclosed rather than reconstructed.
- An unfinished or unknown real model ledger claim blocks subsequent admission. There is deliberately no automatic retry/refund/reconciliation bypass; root needs independent exact cleanup evidence and a later scoped reconciliation implementation if this occurs.

## Next package

Root should finish independent LIFECYCLE-OBS against the final supervisor/worker hashes, relay Q-MODEL-SEAM-02 pool binding to APP, review the artifact/rights/resource pins, then issue **MODEL-READY** with the bounded readiness pool. Do not open a gate or call inference from this assignment. Keep the latest raw failures and development evidence. Root alone publishes the ten owned candidate files below and updates shared budget/state. Native slot is released with this handback; no follow-up process/timer is left running.

## Source-use mapping

| Input / exact upstream identity | Actual use / implementation |
|---|---|
| IP WORK_PACKAGE `bd51fc00fa763218a4f9aa9a39a195fd2109bd46875a4c49452875a0a61ae774`; START_HERE `a0c8608def1b06ce3951919caccdd17ba90afe86f996226e7f4b69b5493ef8d7`; AGENT_BRIEFS `5617429c005d00efda5d868250f51372219d5976f69d5a52985477358c818b3f` | Scoped new Windows implementation, acquisition-only permission here, budgets, role/path ownership and original-source preservation. |
| H00 `integration/SEAM.md`, section5 and inherited I01/I04/I06 | Exact callback signatures, APP-only DB authority, process/result identity, release vs compute separation. |
| RI final-v1 CONTRACTS `cb6cea47fb00aba89da234da620b3fb3bd240c2a10e314bcc81cbfa647cc4be7` | Full influencing dependencies remain APP responsibility; bounded IPC, immutable attempts, fencing and no false stop proof implemented in supervisor/worker. |
| R03 A1 `b2608ea743084af0f7f854b32b8156dc50e95370051de641ab9ae919ac77e667`; closure `d3e12e1371e04538cadc7ce77c84cd9a1c455282d5df49de7e2c9a46fb98b7be` | Model resource ledger is distinct from APP finite-grant release charging; no authority/quota writes from runtime. |
| P01 A1 `3efda1609fb138adc6bef9d125ac2390f4ccc484e797ab2eeefc7f4d26cc3605`; closure `2438d74f574ed79d7613207c2686f6429eb821f1e8ef232dcebc0376bcacf5f4` | Release/result decisions cannot imply delivery or workload termination; unknown stays explicit. |
| `inputs/ORIGINAL_SOURCE_BASELINE.json` | Original NIGHT01 backend `897ad93277399e08903f72e5e25e8dcd4e0aab6379618cb1703d3abf63d64a81`, coordinator `29001252a1b450587f746610c88b93e25f963eb117f8bb87f5e132b41c145345`, store `cf1244197cbb86a9d7488f2c2714ca987cb3b23228a53050beca471c6dfb8273` are inspection identities supplied by root, not qualified current R1. **No original source bytes copied into these modules.** New Windows implementation instead of historical fork-based repair. |
| Microsoft CreateProcess/Job Object primary documentation | Atomic JOB_LIST membership, noninherited kill-on-close handle and active-process observation; observed with actual Windows development tests. https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute and https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects |
| Official Ollama library/registry/FAQ and pinned Qwen checkpoint | One artifact, exact manifest/blobs/rights/template/preprocessor/runtime pins; process-local cloud-off/models/home/tmp and single-load configuration. Primary links and hashes in MODEL_PREPARATION. |

## Exact changed candidate paths and hashes

All paths are clone-relative. SHA256 identifies worktree bytes; root owns Git publication. Private exact-file manifest follows under `.ip01-runtime/runtime-dev/RUNTIME_FILE_MANIFEST.json`; weights, raw lifecycle logs, unit ledgers and host observations must remain private. This handoff's own final hash is reported through the native final receipt to avoid a self-referential digest.

| Changed path | SHA256 |
|---|---|
| `labs/ip01/haven/supervisor.py` | `9713cac68f27ca627780334e27f2637fc258711da2e8072cd70b6f2cd1ff1437` |
| `labs/ip01/haven/worker.py` | `db2a24a67de03080aeb5e8ce16942e8f4ef4b37ccc3b4f7b021f2dbdfff50d3d` |
| `labs/ip01/haven/model_adapter.py` | `0e29edc6f826b04ba8c1bac3a28d55c5a2844f56a20349bb5f321d95577fc0a2` |
| `labs/ip01/tests/runtime/fixture_worker.py` | `694a73eb5858bcebf14e5fbe6b36a71ebea327d149ffbe778cd6918e744b7a61` |
| `labs/ip01/tests/runtime/prepare_model.py` | `59e9abb19c4e4d4f70f7a696288b6f7cfe091e3dcfc58ac3205c1507ba187465` |
| `labs/ip01/tests/runtime/test_model_gate.py` | `d1e0e000296021e076dfeaa2c9db931c8a104cd5eb9fd3f7217c4aa0b80ca335` |
| `labs/ip01/tests/runtime/test_runtime.py` | `a19b03ac35ab0734e9031f2450c0899c24064aac2c650403d3ad05f1162241ce` |
| `campaigns/IP-01/ip01-v2-20260929/receipts/RUNTIME_CONSULTATION.md` | Final digest in private exact-file manifest/native handback. |
| `campaigns/IP-01/ip01-v2-20260929/receipts/MODEL_PREPARATION.md` | Final digest in private exact-file manifest/native handback. |
| `campaigns/IP-01/ip01-v2-20260929/receipts/RUNTIME_HANDOFF.md` | This file; final digest in native handback. |
