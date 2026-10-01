# RUNTIME-FIX assignment 14 — in progress

Runtime ADOPTS H00 EGRESS_AMENDMENT SHA256 `46620137b8ff8bde83340b922c856a158c264a6e7639178bd974a1dc00726820`: optional named `authorize_egress(job_id, attempt_id, fence, context_digest)`; mandatory for model dispatch, strict AUTHORIZED/DENIED/UNKNOWN receipt binding, unchanged admission/token/claim, callback after backend and waiting worker plus PROCESS_STARTED completion. Seal context bytes before callback, finalize only the bound decision handoff envelope synchronously, then check and schedule without intervening await; writer checks again immediately before first byte. Worker checks bound expiry before generation. Denied/unknown dispatch sends zero frames and retains admitted accounting.

Runtime also ADOPTS identity-bound ATTEMPT_TERMINAL with stable pending event ID and metadata-only redelivery; STOP evidence remains independent. One RESOURCE_SETTLED record precedes claim-linked RESULT_DISPOSITION and validated usage. Existing four resource settlements remain immutable.

Actual APP adoption was relayed by root and is attributed to APP_FIX_HANDOFF: same signature/response, persisted admission context and gate hashes, production callback wiring, terminal projection and usage event storage. No callback key mismatch identified. This is contract adoption, not test closure or independent acceptance.

Real root gate remains closed; root stopped old shared app. Runtime will not restart it. All regression model transport is mocked/no inference. Further test results and final source hashes follow here.

## Actual peer check at 05:40Z — root relay requested

Read APP's actual receipt and in-progress `app.py`. One precise integration mismatch: `on_event` currently validates `process_birth` only as int/float, but runtime's established Windows GetProcessTimes birth is an exact decimal FILETIME **string** (`process_birth(handle)`), also used in original readiness results. Please have APP accept bounded positive decimal birth strings without lossy float conversion; runtime will preserve exact identity. This would otherwise silently mark all post-spawn events binding-invalid. No APP file was edited here.

APP authorize_egress intentionally denies deterministic routes. Runtime will invoke it only for model jobs; benign deterministic jobs retain existing admission/dispatch behavior. Production callback remains mandatory for model jobs. No token/grant re-admission.

## Final READY for independent recheck

Assignment14 completed within the approximately05:30–05:50Z bound. Producer checks passed; no independent acceptance claimed. No Git, original/APP/shared-state edits, server actions, model calls or final deterministic suites. Root stopped the old APP independently.

CE-F01: model-only fresh authorize_egress after backend readiness and PROCESS_STARTED; bounded exact response binding, immutable sealed bytes, no awaited operation before scheduled write, actual writer guard, one-shot dispatch, worker/generate handoff expiry. No callback fails closed. Known denial retains claim/cleanup and FAILED; uncertainty retains claim/cleanup and INCONCLUSIVE.

CE-F03: terminal metadata on early/no-result/result paths, outcome mapping follows APP release answer, duplicate/nonregression, pending stable-ID journal redelivery including restart without admission/result replay. Audit append failure still produces an inconclusive terminal event. Compute stop and capacity remain separate.

CE-F06/R8: new SETTLE phase RESOURCE_SETTLED and PENDING_VALIDATION for candidates, then one claim/job/context-linked RESULT_DISPOSITION. Backend usage bounded with absent counters null, not zero; same usage reaches terminal APP event. Four previous settlements unchanged.

APP peer update: on-disk app.py now accepts positive bounded decimal FILETIME strings and matching usage limits. This is direct source observation, not an invented peer test result. Callback is model-only, matching APP eligibility.

Exact changed source paths and SHA256:

- `labs/ip01/haven/supervisor.py` — `3ebae45e0b4b61eb62fcf6b3782482b395e9eeb02e6711acc890a3fdd4ae0ce9`
- `labs/ip01/haven/worker.py` — `2cd10d65aa81a5dd5e654113ea4df5d2bd1325f7bb5b3c49915222018207681a`
- `labs/ip01/haven/model_adapter.py` — `b8c9c73215bbb5f4cdd4fdb2d5ef5ed12c6277b65480a34c64556d7112ebb34a`
- `labs/ip01/tests/runtime/test_runtime.py` — `347f85fe350b6215714c1684395cab53e998304ad62cee324273b8c4224ca35a`
- `labs/ip01/tests/runtime/test_runtime_fix.py` — `7e61de543f231352561ff231f3ded358e0e87cc05b74043b0648267d8057455c`
- `labs/ip01/tests/runtime/fixture_worker.py` — `e901d13be77e953c35672b6f662204da1fe1aba647a157d2f0c894c9300ba1f8`

Other public changed paths: `campaigns/IP-01/ip01-v2-20260929/receipts/RUNTIME_FIX_HANDOFF.md` and `campaigns/IP-01/ip01-v2-20260929/receipts/RUNTIME_FIX_FINDINGS.json`. Private changes are under `.ip01-runtime/runtime-fix/`; exact inventory is `PRIVATE_FILE_MANIFEST.json`.

Commands/outcomes (all with PYTHONDONTWRITEBYTECODE=1, clone labs/ip01 PYTHONPATH, private TMP/TEMP/Hypothesis/pytest cache; commands/log hashes are expanded in findings JSON):

- `.ip01-runtime/venv/Scripts/python.exe -B -m pytest labs/ip01/tests/runtime/test_runtime_fix.py -q --basetemp=.ip01-runtime/runtime-fix/focused-01 -o cache_dir=.ip01-runtime/runtime-fix/pytest-cache` → 40 passed, 4.57s, exit0.
- `.ip01-runtime/venv/Scripts/python.exe -B -m pytest labs/ip01/tests/runtime/test_runtime_fix.py -q --basetemp=.ip01-runtime/runtime-fix/focused-02 -o cache_dir=.ip01-runtime/runtime-fix/pytest-cache` → 40 passed, 4.55s, exit0.
- `.ip01-runtime/venv/Scripts/python.exe -B -m pytest labs/ip01/tests/runtime/test_runtime_fix.py -q --basetemp=.ip01-runtime/runtime-fix/focused-03 -o cache_dir=.ip01-runtime/runtime-fix/pytest-cache` → 43 passed, 5.83s, exit0.
- `.ip01-runtime/venv/Scripts/python.exe -B -m pytest labs/ip01/tests/runtime/ -q --basetemp=.ip01-runtime/runtime-fix/full-benign-01 -o cache_dir=.ip01-runtime/runtime-fix/pytest-cache` → 74 passed, 8.69s, exit0.
- `.ip01-runtime/venv/Scripts/python.exe -B -m pytest labs/ip01/tests/runtime/test_runtime_fix.py -q --basetemp=.ip01-runtime/runtime-fix/focused-04 -o cache_dir=.ip01-runtime/runtime-fix/pytest-cache` → 44 passed, 5.14s, exit0.
- `.ip01-runtime/venv/Scripts/python.exe -B -m pytest labs/ip01/tests/runtime/ -q --basetemp=.ip01-runtime/runtime-fix/full-benign-final -o cache_dir=.ip01-runtime/runtime-fix/pytest-cache` → 75 passed, 10.0s, exit0.

First full benign run passed74. A subsequent ordinary robustness guard added the missing audit-write-failure terminal case and strict numeric response types; focused44 passed, then final full benign run passed75 on these final hashes. All trials/logs retained. No failed test trial. One initial read used an erroneous extra `/IP/` path segment; it failed without writes, then the correct peer receipt was read.

Owned lifecycle evidence: `.ip01-runtime/runtime-fix/full-benign-final/test_benign_owned_process_and_0/probe.json` — `{"after":{"active_processes":0,"confirmed":true,"owned_handles_signaled":true,"peak_job_memory_bytes":17776640,"pids":[],"terminated_processes":0,"total_processes":3},"before":{"active_processes":3,"peak_job_memory_bytes":17776640,"pids":[26020,28288,20804],"terminated_processes":0,"total_processes":3},"control_alive":true,"fixed_stop_target_seconds":3.0,"kind":"BENIGN_PROBE","stop_elapsed_seconds":0.014999999999417923}`.

Owned lifecycle evidence: `.ip01-runtime/runtime-fix/full-benign-final/test_parent_death_job_cleanup_0/parent-death-observed.json` — `{"after":{"active_processes":0,"peak_job_memory_bytes":36728832,"pids":[],"terminated_processes":0,"total_processes":6},"before":{"descendant":{"child_pid":18788},"observation":{"active_processes":3,"peak_job_memory_bytes":18362368,"pids":[27316,12120,18788],"terminated_processes":0,"total_processes":3},"worker":{"boot_id":"894859e6-d8a4-11ef-9f5d-b101f8ca7188","pid":27316,"process_birth":"134351343077047241"}},"control_alive":true}`.

Read-only root accounting: 4 claims/4 settlements, 97.204s, all cleanup confirmed=True; gate enabled=False; ledger last write 2026-09-29T05:11:39.571315+00:00. Assignment14 calls0, final suites0.

Source-use mapping:

- `campaigns/IP-01/ip01-v2-20260929/integration/EGRESS_AMENDMENT.md` SHA `46620137b8ff8bde83340b922c856a158c264a6e7639178bd974a1dc00726820`: Exact callback, dispatch ordering, all-path terminal event, resource/result settlement contract.
- `campaigns/IP-01/ip01-v2-20260929/reviews/CODE-EARLY/CODE_EARLY_REVIEW.md` SHA `28e4876f764a6efd30b339316afb36505d8b3729ead38456563c77fea232d1a0`: CE-F01/F03/F06 defect and affected recheck scope.
- `campaigns/IP-01/ip01-v2-20260929/receipts/APP_FIX_HANDOFF.md` SHA `713bc3a1c058b261a9f85a1d4d6ddbed731119bcb1b36bfce8c949d080cef654`: Actual attributed APP adoption; source inspection detected FILETIME mismatch and later observed acceptance.
- `campaigns/IP-01/ip01-v2-20260929/integration/SEAM.md` SHA `09380772d5e19838950d94e4cf94e682fc41d65fed217f8587d2e53b579b0985`: Inherited immutable attempt/owned process identity and callback authority boundary.
- `campaigns/IP-01/ip01-v2-20260929/inputs/SOURCE_IDENTITY.json` SHA `0889a0abdea1885ce22b98c6c01934925fd8dc9beb9dc367955d6531372d95af`: Input identity catalog only; does not imply new semantic reads of every historical source.
- `campaigns/IP-01/ip01-v2-20260929/inputs/ORIGINAL_SOURCE_BASELINE.json` SHA `8382283536ccbc1f07a7fbb2da01b90dadeaff04dafd7526f82895abdc985776`: Original inspection identity only; no original writes or original-R1 qualification.

Limits / remaining work:

- Producer development tests only; authority decisions, artifact/backend preparation and model transport in model barriers are mocked. Zero inference.
- Independent actual APP callback/HTTP authority barriers, semantic/model lifecycle validation and root freeze are still required. No finding self-acceptance.
- The complete influencing request bytes are sealed before authorize_egress. The returned decision/time/digest handoff envelope is attached synchronously after response, before final guard/scheduling; no influencing content is rebuilt.
- One-second egress window is not instantaneous revocation or a hard real-time OS guarantee. Post-first-byte cancellation records actual writes and cannot recall transmitted bytes.
- New supervisor/worker/adapter hashes invalidate affected applicability of prior benign/model readiness evidence. Root must load repaired sources; original four ledger entries remain historical.
- Pending terminal redelivery is metadata-only, at most32 per invocation, each callback bounded2sec; restart reuses original IDs and does not recompute or retry on_result.
- Claim resource settlement and later result disposition remain separate; a crash between phases leaves pending validation rather than implicit success. Stop uncertainty retains owned capacity independently.

Next action: Root freeze repaired APP and these runtime hashes; QA15 independently rechecks affected egress/terminal/settlement/lifecycle barriers. Keep model gate disabled until root explicitly authorizes later slots.
