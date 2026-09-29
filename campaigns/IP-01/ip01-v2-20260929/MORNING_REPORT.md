# Haven IP-01 v2 - working handoff, final evaluation pending

**IN_PROGRESS as of 2026-09-29 06:05 UTC. This is not the final acceptance report.** Root is continuing the authorized campaign. Final qualification, reviews, publication reconciliation and shutdown audit remain pending. The fixed hard deadline is 10:10:16 UTC / 06:10:16 EDT, with new work cutoff09:25:16 UTC.

## What runs

The Windows Python3.12/FastAPI/Jinja/SQLite laboratory application implements two invented people, persistent notes and revisions, explicit sharing/revocation, saved local drafts/tasks, deterministic source excerpts, and a separately gated local text/image model route. The selector is visibly simulated login. The app does not connect accounts or dispatch external tasks.

From the isolated repository root in PowerShell:

```powershell
& ./.ip01-runtime/venv/Scripts/python.exe labs/ip01/scripts/run.py start
& ./.ip01-runtime/venv/Scripts/python.exe labs/ip01/scripts/run.py status
& ./.ip01-runtime/venv/Scripts/python.exe labs/ip01/scripts/run.py stop
```

Start prints the exact URL at the first free loopback port8765-8767, normally http://127.0.0.1:8765. It creates no persistent service. Dependency setup, private browser cache, migrations, synthetic walkthrough notes and producer-test commands are in [the application README](../../../labs/ip01/README.md). The relative link will be checked in final delivery.

The root app is currently **STOPPED for repaired-candidate validation**, observed STOP_CONFIRMED with no recorded descendant remaining. The model gate is disabled. The deterministic route will remain usable after the campaign; restarting does not extend or reset the model gate, call ledger or campaign.

## Source and execution identity

Repaired development candidate: `cb266a32459d624097da685817a399db7156bbe6`, bound by [DEVELOPMENT_CANDIDATE_02](receipts/DEVELOPMENT_CANDIDATE_02.json). Its receipt SHA256 is `09aa30f89d5c71bd284f2fff847cc69e0221c3788c5e2105ef1fac5ae2cdd825`. Later `06b63921dcb85fe127188e625ea5e6c3fb189149` adds README/administrative material. Current `83872d855d6a79e2d3845ad769f3b4a7199915ba` corrects one browser empty-state sentence; its affected independent recheck is pending. All Python implementation bytes remain those of cb266a3.

This is not the final candidate freeze. Final source, environment, evaluator/protocol identity and later administrative publication SHA will be stated separately.

## What has actually been exercised

- Initial independent QA found stale A browser responses rendered under B, an over-depth redundant-parent dependency graph, and an exhausted grant masking a usable one. The original failures remain in [QA-E2E](reviews/QA-E2E/QA_E2E_HANDOFF.md).
- Independent code review additionally identified stale model input egress after asynchronous preparation and incomplete terminal-state/audit reporting. H00 supplied an actual [seam amendment](integration/EGRESS_AMENDMENT.md); both owners adopted it, found and fixed an exact Windows process-birth representation mismatch, and repaired their separate modules.
- The repaired app author reports146 passing regression tests,22 focused tests, and two actual Chromium delayed-response rechecks. The runtime author reports75 passing benign tests. These are producer evidence, not independent acceptance.
- QA15's first repaired-snapshot independent run executed150 checks successfully. Both delayed-refresh and committed-consume browser races passed on the repaired JS; A's marker did not render beneath B. The final affected UI-copy recheck and full amended egress/terminal/lifecycle matrix are pending.
- Earlier independent execution exercised real synthetic database writes, A-private/B-forbidden/B-shared answers, revisions/tombstones/revocation, finite-use and joint-grant accounting, actual postcommit faults and lost consume replies, history without replay, saved drafts/tasks, current restart and rollback review-only behavior. These historical passes name their original bytes; changed paths need affected rechecks.
- Earlier benign lifecycle QA executed13 measured fault cases and21 observer-oracle checks, including actual parent death, worker crash, cancel, timeout, stale/duplicate/late results and uncertain-capacity behavior. Its234 observed identities were absent at reconciliation. New runtime bytes still need independent renewal. Frozen stop targets remain3seconds for runtime and20seconds for the app.

No collected-but-unrun test, static review, mocked model transport or screenshot is represented as actual model inference.

## Actual local model work so far

The one selected artifact is qwen2.5vl:3bQ4_K_M, manifest `fb90415cde1ef08aa669ae74b082d49b158729b6db1ab183c941417d507e71a1`, using pinned Ollama0.34.4. [MODEL_PREPARATION](receipts/MODEL_PREPARATION.md) records blob/runtime-library, rights, template and preprocessing identities. The CPU envelope is4096context tokens,768generated tokens,oneimage,120seconds and12GiB per owned Job Object; no driver change or hosted fallback.

Four actual APP-authorized readiness calls ran: two text and two image. All four had confirmed owned cleanup and fresh once-only consumption. Independent review judged4/4 semantically correct and3/4 within requested word bounds. The image-positive response used seven words where five were requested; that failure was retained without tuning or retry. Latency was roughly13-37seconds; sampled RSS was below4.2GB.

The old ledger's resource-settlement outcome says QUEUED because it preceded result validation. Those four original records remain unchanged; new code separates resource settlement from claim-linked result disposition and validated usage. Exact historical token counts were not retained and remain UNKNOWN.

Task16 is preparing live model cancel/timeout observation, actual selected-image browser calls, and the unchanged24-family/72-slot final driver. **No new calls or final pilot have been authorized or executed at this report point.**

Protected expected assets reside in the evaluator sibling, but all roles share the same host account and full-access environment. Actual adversarial separation is NOT_ESTABLISHED. Any protected pilot verdict must retain EVALUATION_INCONCLUSIVE on that dimension; comparison criteria do not establish canonical P03 or R13 qualification.

## Budgets at this checkpoint

| Budget | Observed use | Limit |
|---|---:|---:|
| Substantive assignments |16|24; six reserved for final review/delivery/rechecks|
| Active native children |2|3 plus root|
| Readiness model slots |4|16|
| Lifecycle model slots |0|8|
| Final pilot slots |0|72|
| Charged model time |97.204seconds|5400seconds|
| Final deterministic suite starts |0|3|
| Issue20 runtime checkpoints |2|4|
| Newly acquired assets, conservative debit |4.1GiB|12GiB|
| Combined workspace logical file bytes,05:58UTC |4,505,015,204|21,474,836,480|
| Free host disk,05:58UTC |409,945,968,640bytes|at least10GiB retained|

The conservative model count uses the union of durable APP token bindings and runtime claims:4bindings,4claims,4network markers,4confirmed settlements,zero pending/unknown cleanup. No refund, allocation borrowing, copied real ledger, account change or extra provider spending occurred. Last observed weekly allowance was63percent used with ordinary usage allowed; monetary cost is UNKNOWN.

## Publication, originals and remaining work

The repaired candidate cb266a3 is pushed to the existing implementation branch and [draft PR21](https://github.com/erpzz/haven/pull/21). Later administrative/copy changes await the next push. [Issue20 checkpoint2](https://github.com/erpzz/haven/issues/20#issuecomment-5884105889) is a dated development receipt, not the current live-process state. A fresh oversight read found only setup plus our two runtime checkpoints.

One absolute user-home pathname was inadvertently included in intermediate commit7a9d4f9; the next public edition redacted it and recorded the miss without rewriting history. [PUBLIC_REPORT_EDITIONS](receipts/PUBLIC_REPORT_EDITIONS.json) preserves old/new hashes. No credentials, real-user records, model assets, runtime databases or reusable protected fixtures are intended for publication; final scan/manual review remains required.

Original ASTRA was inspected read-only at clean revision3aa1ac646052124b98c73d9d1f361bef3c123d81; inspected NIGHT01 files were hashed, but no Git metadata was available there. A final read-only comparison remains pending. The new isolated supervisor does not qualify or repair originalR1.

Remaining: finish independent repaired integration; execute bounded model fault/browser work if gates hold; freeze final source/protocol; execute the final deterministic plan and eligible72-call pilot; obtain H00 integration plus distinct code/vision/evidence reviews; deliver sanitized evidence and offline snapshot; reconcile originals, publication and exact-owned process shutdown. Broader multimodal, engineering, spatial, augmentation, robotics, aircraft and Observatory ambitions remain in the preserved RI-01 baseline and are outside this phase.

The smallest next operational decision is pending final evidence. No user decision or permission is currently needed for the remaining authorized work.

