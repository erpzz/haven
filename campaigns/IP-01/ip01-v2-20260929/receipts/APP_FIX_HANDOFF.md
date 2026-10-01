# APP-FIX assignment 13 — READY

APP-owned source is stable as of 2026-09-29T05:47:46.708902+00:00. Return slot to root. Root 01a0eb51-c8b3-7923-94ed-ea1874de843e; ip01_application_engineer; CUSTOM_PROFILE_FALLBACK inherited model UNKNOWN. Approximately05:28–05:48Z bound respected. Fixed cutoff09:25:16Z/deadline10:10:16Z unchanged. Model calls0; final suites0. No Git, ancestor messaging, root server/gate/ledger edits, runtime-owned edits, original changes, provider spending or real data.

## Actual seam adoption and peer resolution

APP ADOPTS H00 EGRESS_AMENDMENT SHA46620137b8ff8bde83340b922c856a158c264a6e7639178bd974a1dc00726820. Early adoption was written before implementation. Named async authorize_egress(job_id,attempt_id,fence,context_digest), supplied to Supervisor, returns exactly decision/reason/job_id/attempt_id/lease_fence/context_digest/cancel_epoch/decision_id/checked_at/valid_until/authority_vector_digest/model_gate_sha256. Initial admission persists exact context/vector/gate/allocation binding. Fresh serialized check after runtime readiness examines the existing immutable admitted tuple, sealed complete context/vector and all ancestors, current session/job/grants/route/epoch/continuity, gate hash/identity/token/phase and expiry. AUTHORIZED follows committed EGRESS_DECISION only; validity is min(checked_at+1sec,job/session/grant/gate expiries). Unknown commit returns UNKNOWN/null evidence. No additional model token, grant claim, charge or context replacement. Runtime owns after-readiness ordering/write/worker guards.

Read actual RUNTIME_FIX_HANDOFF including05:40 FILETIME finding. RESOLVED: APP accepts bounded positive decimal process_birth strings and retains them exactly, without float conversion. Real Supervisor+APP test exposed and then verified this fix. Runtime invokes egress only on model routes; APP denies deterministic egress intentionally. No interface incompatibility remains identified. This is actual peer adoption plus development execution, not independent closure.

ATTEMPT_TERMINAL persists bounded usage and claim/context metadata after identity/evidence validation; only matching QUEUED projection settles. UNKNOWN becomes INCONCLUSIVE. Interim runtime errors remain timeline evidence pending terminal settlement. Duplicate/conflicting/stale events cannot regress settled job/receipt. Stop observations remain separate. Late result cannot reopen settled no-output jobs. Deterministic unknown admission also remains INCONCLUSIVE. APP never writes model ledger.

## Repairs and source-use mapping

- CE-F01/03: CODE-EARLY plus H00 amendment and actual runtime peer interface -> app.py callback/event/settlement changes and real-supervisor regression.
- CE-F02: CODE-EARLY plus actual QA9 Chromium refresh/consume reports -> static/app.js generation invalidated at switch begin, stale responses rejected before state/DOM/display observations, persona collections/forms/dialog references cleared; concurrent login serialized. CSP unchanged.
- CE-F04: CODE-EARLY plus QA9 redundant-parent DAG -> authority.py cycle-aware cached ancestor height, independent of deduplicated traversal and edge order. Existing2/32/16/128/depth16/64KiB/256KiB bounds retained.
- CE-F05: CODE-EARLY plus QA9 ordered grant fixture -> authority.py initially prefers a valid grant with available release quota. Once sealed, fixed grant stays fixed; existing zero-remaining claim still consumes. If all eligible grants exhausted, prior failed-release behavior remains. No refund/rebinding/replay.
- contracts.py: only normalized extra trailing blank line. Existing original R03/P01 adaptation/attribution from prior APP handback remains; no new original/reference code copied this assignment.

Exact input hashes, changed path list and evidence hashes are in APP_FIX_FINDINGS.json. No shared schema or store.py change in this assignment.

## Commands, outcomes, failed attempts

All Python commands used .ip01-runtime/venv/Scripts/python.exe -B. Environment: PYTHONUTF8=1, PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=labs/ip01, TEMP/TMP=.ip01-runtime/app-fix; Hypothesis storage .ip01-runtime/app-fix/hypothesis for suites. pytest cache_dir=.ip01-runtime/app-fix/pytest-cache. No cleanup of previous failures.

Focused command: python -B -m pytest labs/ip01/tests/app/test_app_fixes.py --basetemp=.ip01-runtime/app-fix/pytest-NN -o cache_dir=.ip01-runtime/app-fix/pytest-cache -q; output piped to matching focused-NN.log. NN01:17pass/2fail because tests wrongly expected invalid depth graph creation to succeed; actual413 correct. NN02:17pass/3fail: two regex spelling errors, one real FILETIME-string binding issue. NN03:20pass. NN04:22pass after unknown-admission/late-result checks. NN05:22pass on final test bytes with forced G1<G2 ordering, after reading QA9 actual fixture. Full regression production bytes unchanged by this final test-only strengthening.

Full command: python -B -m pytest labs/ip01/tests/app --basetemp=.ip01-runtime/app-fix/pytest-regression-NN -o cache_dir=.ip01-runtime/app-fix/pytest-cache -q. NN01:144passed/32.90sec; NN02:146passed/34.18sec after additional settled-job guards. No final suite consumed. Both retain Starlette httpx deprecation warning; no dependency change.

Browser command: python -B .ip01-runtime/app-fix/browser_races.py (failed harness string-eval under CSP; stopped confirmed); corrected python -B .ip01-runtime/app-fix/browser_races_02.py passed. No policy bypass or CSP change. Harness used actual root launcher start/stop through imported module, selecting only a socket-verified-free8766 via private function override because start currently ignores --port. Actual Chromium delayed A200 refresh and consumed-payload replies until B rendered; both stale payloads discarded, collections empty, no DISPLAY_REPORTED request, no pageerrors. Screenshot browser-persona-fence.png inspected. Logs retain exact PIDs/birth/nonce and STOP_CONFIRMED with both observed descendants absent for each run. Browser profiles/temp/cache remained private. No private service remains.

Additional retained failed edit attempt: failed-trial-01.txt records default cp1252 UnicodeDecodeError before JS writes; retried explicit UTF-8. All failing logs/DBs/runtime journals preserved. Real-supervisor negative test uses real APP HTTP/admission/egress/store/events + owned Windows worker, with only ModelAdapter readiness stubbed to mutate an uncited ancestor. No actual model lease/inference. It observed EGRESS_DENIED, zero dispatch, no output/release, durable FAILED and independent STOP_CONFIRMED; counterpart runtime journal retains process/dispatch observations.

## Exact APP bytes

- `labs/ip01/haven/app.py` — `93b9335f9bb5eb73b506c34a08bc8c2490263ed2ccbe551fa45253f0cd5b7427`
- `labs/ip01/haven/authority.py` — `15ca0f6b4e273d5d4d19b54d2cd082cc41bb592c8fadd60c1c9871a5c724ac75`
- `labs/ip01/haven/contracts.py` — `9912e3282f5634627f6b8ff3b0969c2c2e1920ca8077729f5bf3e365d1de8b3f`
- `labs/ip01/haven/static/app.js` — `a34d7d3682c78d94e7cad46a653a8a9b95646297a163ccae8a4b02431fed3508`
- `labs/ip01/tests/app/test_app_fixes.py` — `1ef8c3bfb98fa70c9da72e7e9eb2586a9759108e73b22b3a015de36ce348e9c2`

Findings manifest SHA256: add4c4dcf0e87965bd675d052d6782ca1f0c385b18e4d256ce587bd1205836a4

## Limits and next action

Author development evidence only. Independent QA9 reported old-candidate defects; none of its passes automatically transfers here. H00's full E1/E2/E3/T1/T2/S1 matrix, positive instrumented dispatch, all backing-state phase mutations, settlement/capacity/unknown redelivery and model work remain independent obligations. No inference used. Root should freeze combined APP+RUNTIME+launcher bytes, restart its own integrated app with gate closed, and give candidate-bound independent QA15 the affected tests. Runtime counterpart hashes were not frozen by APP. Preserve NOT_ESTABLISHED/EVALUATION_INCONCLUSIVE protection limitations and no original-R1 qualification.
