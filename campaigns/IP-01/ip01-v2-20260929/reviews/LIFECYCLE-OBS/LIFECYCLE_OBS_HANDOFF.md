# LIFECYCLE-OBS independent handback

Thread / owner / task: assignment 7, independent ip01_validation_engineer; CUSTOM_PROFILE_FALLBACK, inherited model UNKNOWN. Root `01a0eb51-c8b3-7923-94ed-ea1874de843e`; 7/24 assignments as dispatched, at most root plus three children, final six reserved. Deadline `2026-09-29T10:10:16Z`, feature cutoff `09:25:16Z`, unchanged.

## Decisions

**Independent benign lifecycle PASS within the tested scope.** All thirteen runtime scenarios passed on the final owner-closed supervisor bytes after the observer correction described below. Earlier passes were not inherited. The root launcher passed independent start/status/duplicate-start, two ownership mismatch negatives, invalid-deadline rejection, stop, repeated stop, same-runtime process restart and earlier test-deadline shutdown. This satisfies a benign prerequisite for root's later MODEL-READY decision; it does not open a model gate or qualify a model backend.

Candidate remained read-only. Actual supervisor/worker bytes were copied unchanged into the named evaluator sibling before execution. Snapshot and source hashes matched at start/end of each runtime run; current applicability is recorded in RESULTS.json. The root launcher's real candidate script was executed with evaluator-private runtime state and bytecode suppression. No original code, Git, shared ledgers, models, accounts, devices, policies or host security were changed. No agents or messages were sent.

## Evidence

Executable: `<workspace>/.ip01-runtime/venv/Scripts/python.exe`. Final source snapshot: `<evaluator>/lifecycle_obs/snapshots/20260929T045903.425099Z/`. The earlier snapshot remains retained. Child actors used the actual base interpreter with `-I -B`, private temporary directories and explicit bytecode suppression. The observer ran in a separate process, sampled exact PID/birth identities, independently walked the actor process tree, compared Job Object member/handle reports, and kept a separate control process alive throughout each trial.

| Command (under evaluator lifecycle_obs) | Actual outcome | Retained run |
|---|---|---|
| `python -B snapshot.py` | Exact unchanged candidate snapshot + per-file hashes | `snapshots/20260929T044621.266062Z/` |
| `python -B run_faults.py`, initial | 11 passed; candidate membership plus independent PID observation | `runs/20260929T044758.134570Z/` |
| `python -B test_launcher.py`, attempt1 | APP START_FAILED: static directory not present yet; evaluator finding-writer KeyError also retained | `runs/launcher-20260929T045007.520408Z/` |
| `python -B test_negative_launcher.py` | 9 passed, control survived; prior failed launcher owner independently absent | `runs/launcher-negative-20260929T045135.347450Z/` |
| `python -B test_launcher.py`, recheck | 8 grouped checks passed; all observed descendants absent and control survived | `runs/launcher-20260929T045211.743148Z/` |
| `python -B run_faults.py`, strengthened observer | 10 passed, cancel-before assertion failed due harness console helper classification | `runs/20260929T045344.368406Z/` |
| `python -B run_faults.py`, corrected observer | All 11 passed with independent descendant discovery and pre-runtime baseline | `runs/20260929T045507.542222Z/` |
| `python -B verify_oracle.py` | 19 pytest checks passed in0.14s, including8 corrupted-evidence rejection tests | `runs/oracle-20260929T045543.773761Z/` |

Exact commands, environment-relevant paths, exit outcomes and raw stdout/stderr are private run artifacts. `RESULTS.json` provides sanitized case results and evidence hashes. Each runtime case retains `actor.jsonl`, `actor-result.json` where the parent survives, and `observer.json` with exact actor/worker/control identities, process births, monotonic samples, injected fault times and events. The final recheck covered every recorded identity across all attempts, including the earlier failures. The exact-identity shutdown receipt is `<evaluator>/lifecycle_obs/OWNED_SHUTDOWN.json`. Nothing was terminated by broad process name or PID range.

## Interface changes

None to candidate or SEAM. Read the actual Q-QA-LIFECYCLE-01 and Q-QA-APP-01 owner replies. The pinned callable callback seam, source-ID string refs and self-excluding context digest were respected. Faults were evaluator process-local substitutions only: an admission Event barrier, bounded PROCESS_STARTED callback barrier, malformed benign worker input causing a real worker exit, late/stale/duplicate candidate injection through `_accept_candidate`, and a wrapper around real stop that deliberately withheld confirmation. No production HTTP fault route was added.

## Acceptance

Runtime cases: useful benign compute; cancel before admission (no worker launched); cancel during actual owned work; timeout; actual parent death with independently observed child disappearance; actual worker crash; delayed first result; duplicate result; stale fence; restart rejecting old job identity and admitting fresh work; UNKNOWN cleanup retaining capacity and rejecting both new submit and parallel restart. Every case retained an independent control survivor and reconciled owned shutdown. Job Object zero active members plus exact signaled handles remained required for runtime STOP_CONFIRMED.

The frozen runtime target remains **3.0 seconds**, separately from the root app's **20 seconds**. The passing launcher graceful stop took about0.563 seconds, and automatic deadline shutdown was observed about0.473 seconds after its intentionally earlier three-second test deadline. The campaign deadline was not extended. Runtime case measurements are in RESULTS.json; polling is an observation bound, not a worst-case guarantee.

Unknown cleanup is specifically an **injected observation-loss policy test after actual real stop**. The runtime retained UNKNOWN, capacity_held and runtime_quarantined; new submit and parallel restart were denied; close remained unconfirmed. The evaluator then reconciled and closed only the original retained handles. This does not claim an actual OS termination failure was induced or resolved by normal cleanup.

## Failed attempts and corrections

1. APP was mid-build on launcher attempt1, and its static directory did not exist. Root/APP later created their own assets; QA changed no candidate files. The same launcher then passed against stable-in-run app bytes. No stateful APP journey is inferred. APP modules changed again after this launcher-only run; its recorded start/stop result is limited to those tested bytes. The launcher script hash remains separately checked.
2. The evaluator finding writer mixed Windows-backslash and slash path keys. It raised KeyError after preserving the original launch failure. The harness now normalizes keys; the failed trace is retained.
3. The first independent descendant-walk extension found an extra actor descendant and correctly failed the cancel-before assertion. A new pre-runtime handshake established that Windows `conhost.exe` was already attached to the harness actor before Supervisor construction. The corrected oracle distinguishes baseline harness infrastructure from actual admitted workload. **All descendants, including that helper, still had to be absent at final shutdown; no cleanup target or time limit was relaxed.** All eleven cases were rechecked and the erroneous run remains retained.
4. Eight oracle mutations were rejected: dead control, surviving workload, absent independent discovery, false zero-members stop, duplicate callback, over-target stop, released UNKNOWN capacity and falsely confirmed UNKNOWN close. These are explicit evaluator self-tests, not candidate faults or additional model attempts.

## Risks and next package

This is benign deterministic process lifecycle evidence only. No model adapter/backend was executed; artifact/rights/template/tokenizer/preprocessing/resource readiness and dedicated backend stop evidence remain separate root gates. No stateful UI, source-authority vector, quota, current-store continuity, rollback, protected enforcement, original R1, production sandbox or canonical qualification is claimed. Same-account full-access roles still do not establish protected evaluation enforcement.

Return this native slot. Root can use the exact stable runtime evidence for its bounded MODEL-READY prerequisite assessment, then schedule model-specific ownership/stop work and later QA-E2E independently. All first failures remain visible; changed supervisor/worker bytes require an affected recheck. Added usage: **0 model calls, 0 final deterministic suite starts**. Publication is root-owned; no Git or PR actions were performed.

## Final owner-closed runtime recheck

Owner reported final supervisor change after the initial stable candidate. QA independently compared actual bytes: `_accept_candidate` added strict result-schema rejection. A new unchanged snapshot was taken, all eleven existing measured cases were rerun, and malformed-first-result plus malformed-duplicate nonregression cases were added. Actual command `python -B run_faults.py` produced **13/13 PASS** at `<evaluator>/lifecycle_obs/runs/20260929T045903.582547Z/`; source before/after hashes matched. `python -B verify_oracle.py 20260929T045903.582547Z` produced **21 passed in0.16s**, including the eight corruption-rejection mutations. These are development runs, not final deterministic suite starts. Earlier attempts and reports remain private originals; no earlier PASS is inherited onto these bytes.

Tested supervisor SHA256: `9713cac68f27ca627780334e27f2637fc258711da2e8072cd70b6f2cd1ff1437`.

Tested worker SHA256: `db2a24a67de03080aeb5e8ce16942e8f4ef4b37ccc3b4f7b021f2dbdfff50d3d`.

Tested root launcher SHA256: `5ee9fb5f92c9977be4754675ebe136bd13bf42758207a98abad907b065a9a656`.

Owned changed paths are limited to `<evaluator>/lifecycle_obs/**` and `<campaign>/reviews/LIFECYCLE-OBS/**`. `ARTIFACT_MANIFEST.json` in the private evaluator directory and `PUBLIC_SHA256SUMS.json` list exact files and SHA256. The snapshot manifests bind actual candidate source to identical evaluator copies.
