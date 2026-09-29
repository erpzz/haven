# RUNTIME answer to Q-SEAM-01

Assignment 4, ip01_runtime_engineer, CUSTOM_PROFILE_FALLBACK, inherited model UNKNOWN. Answer at 2026-09-29T04:27Z to H00 native 01a0eb61-9f2d-72c2-9acc-e1ac3845f9d7, via root relay.

YES: implement the exact injected async `admit_attempt(job_id, attempt_id, fence)` immediately before owned process/backend admission. No interface amendment is needed. APP is the sole SQLite writer and authority; runtime keeps private append-only lifecycle evidence and passes only attributed, validated candidates to async `on_result`. Runtime never releases to the browser.

Windows topology: an owned kill-on-close Job Object, with atomic job membership at process creation, contains worker and (for a later authorized model attempt) dedicated backend descendants. Admission callback failure/UNKNOWN denies process start; local cancellation is checked again after the await and before launch. Parent death closes the last non-inherited job handle. Confirmation requires observed zero active job processes and signaled owned process handles; uncertain cleanup retains capacity. Initial development will prove these with benign workloads, then independent QA must repeat. No model inference is authorized in this assignment.

Callable target remains `Supervisor(*, runtime_dir, admit_attempt, on_event, on_result)` with async start/submit/cancel/snapshot/close as in SEAM section 5. Concrete implementation and preparation evidence follow in RUNTIME_HANDOFF.md and MODEL_PREPARATION.md. This answer is an implementation commitment, not a completed lifecycle qualification.

## Actual answer to Q-APP-01

To APP native 01a0eb68-1eef-7890-a6bb-4d1dc1bc5a57, received through root: YES to the requested callback ordering and identity preservation. Runtime awaits APP admission, then checks the local cancellation signal/epoch and immutable lease fence before process admission; no process/backend launch occurs on denied/unknown/failed admission. Results bind attempt, lease/cancel, request/context digests and attributed process identity. Stale/duplicate results cannot cause a second callback release. APP remains responsible for its fresh release-authority check. Release FENCED is never STOP_CONFIRMED; only observed zero active job processes plus signaled owned handles permits confirmation. Unknown cleanup retains capacity and blocks further admission. These are implementation invariants to be tested, not independent qualification.

Root's venv-shim observation is acknowledged. Runtime will use the actual base interpreter for its stdlib-only worker and observe total active Job Object membership, including descendants, independently of wrapper exit. Runtime stop target is separately frozen from its benign probe before measured faults; root's app topology retains its own fixed 20-second bound. No target is enlarged after failure.

## Actual answer to Q-MODEL-SEAM-02

Adopt root's bounded-token-pool solution. Root's private gate authorizes finite opaque slots by allocation and exact model identity/synthetic scope. Trusted APP reads `ModelAdapter.gate_snapshot()`, selects an unused authorized slot in its admission transaction, and durably binds it to its actual immutable job/attempt/fence/cancel/request tuple. It returns `limits.model_attempt_token`, `model_allocation`, `model_binding_id`, and `model_gate_sha256`. Runtime globally locks, compares root gate digest, checks allocation/expiry/caps and atomically appends one fsynced claim containing the full actual job binding before backend admission. Duplicate tokens reject. Public callers/model cannot choose those authority fields. This supports UI requests and the 72-call runner without per-call root file edits. Exact paths/schema are in MODEL_PREPARATION.md; gate remains absent/closed and call count zero. Supersedes only the earlier prebound-token wording, not SEAM's async callback signatures.

LOCALAPPDATA integration finding resolved: `model/runtime-pin.json` supplies the preparation-pinned installed executable and its hash to the trusted app. No ambient LOCALAPPDATA dependency is needed by model runtime, and no such value is restored to workers.

## Actual answer to Q-QA-LIFECYCLE-01 / benign fault readiness

Confirmed **3.0 seconds** for this Windows Job Object topology, frozen before measured development faults in `.ip01-runtime/runtime-dev/STOP_TARGET_FREEZE.json`. The separate root app retains 20 seconds. Confirmation requires zero active Job Object processes and signaled owned handles. No backend inference is included in this benign freeze, and no target increased after failure.

Supported evaluator seams are in-process harness substitutions, never a production HTTP fault endpoint:

1. Admission barrier: injected async `admit_attempt` signals an evaluator Event, waits on another Event, then returns the original complete ADMITTED mapping. Call `cancel(job_id, newer_epoch, reason)` while held, release the callback, and independently confirm no PROCESS_STARTED/PID/owned admission. Callback exceptions/UNKNOWN deny spawn.
2. Unknown observation/capacity: save `OwnedJob.stop`; the evaluator can wrap this async method, call the real stop (retaining independently observed facts), then return the same observation with `confirmed:false` to simulate lost/uncertain observer evidence. Assert UNKNOWN + capacity_held + runtime_quarantined; new submit rejects and close cannot claim confirmed. The evaluator then restores the method and reconciles/closes only those original retained handles. This proves policy on injected observer uncertainty, not a real OS termination failure. Our development example is `test_unknown_observer_retains_capacity`.
3. Real crash/delay/malformed framing: evaluator can substitute the fixed `OwnedProcess` construction in its process-local imported module with its own benign fixture executable, preserving the supplied Job Object, private env and cwd. No candidate file edits or public fault mode. `_accept_candidate` is the internal result-validation seam for controlled duplicates; it cannot bypass authority callback checks.

Supervisor/worker are now READY_FOR_INDEPENDENT_BENIGN_FAULTS at exact worktree SHA256:

- `labs/ip01/haven/supervisor.py`: `a461647d7f72f24c52a26762d1e895965345f79c429e7c6fba004d7613134a2e`
- `labs/ip01/haven/worker.py`: `db2a24a67de03080aeb5e8ce16942e8f4ef4b37ccc3b4f7b021f2dbdfff50d3d`

Development recheck: 17 tests passed, including injected unknown-observer capacity hold. `.ip01-runtime/runtime-dev/pytest-fault-02.log` retains output. Earlier 16-pass run is retained. These replace earlier transient QA-PREP candidate hashes; independent QA must hash these bytes at start/end. Separate model_adapter/preparation work continues; no inference gate is open. Any later supervisor/worker change must be explicitly relayed for affected recheck.

APP binding detail, matching its observed contracts: result `source_refs` is a list of source-ID strings; exact revisions remain in the full context/vector. Context may include its self-describing `context_digest`; runtime recomputes canonical digest excluding only that field, rejects mismatch, and echoes it unchanged. APP must seal any image bytes/digest/preprocessing fields before supplying the context. No arbitrary file path is accepted by the worker.

Runtime child hygiene: fixed base Python uses `-I -B`; private_environment explicitly sets PYTHONDONTWRITEBYTECODE=1/PYTHONNOUSERSITE=1 and private TEMP/TMP/HOME/USERPROFILE/AppData. Development commands set private pytest cache/basetemp and HYPOTHESIS_STORAGE_DIRECTORY. No candidate bytecode cleanup was attempted; root owns relocation of any preexisting caches.

### Explicit QA hash update after result-schema hardening

One subsequent supervisor-only correction validates the complete result record/outcome/usage types before callback, and ensures a malformed late duplicate cannot regress a prior successful compute disposition. **Use new supervisor SHA256 `9713cac68f27ca627780334e27f2637fc258711da2e8072cd70b6f2cd1ff1437`**; worker remains `db2a24a67de03080aeb5e8ce16942e8f4ef4b37ccc3b4f7b021f2dbdfff50d3d`. Supersedes the immediately preceding supervisor hash only. Affected malformed/duplicate assertions and a clean-restart positive were added; final runtime development recheck **18 passed** in `pytest-fault-04.log`. `pytest-fault-03.log` preserves a test-authoring failure (candidate variable referenced before construction; 17 passed/1 failed), fixed by moving the assertion after fixture construction. No target changes and no inference. Supervisor/worker are stable again for the independent measured-fault assignment.
