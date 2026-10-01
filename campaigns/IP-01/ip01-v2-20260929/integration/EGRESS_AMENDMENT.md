# H00-EGRESS — narrow callback and terminal-projection amendment

Assignment 12; distinct `haven_integration_manager`, CUSTOM_PROFILE_FALLBACK, inherited model UNKNOWN. Author response to actual **Q-CODE-EARLY-01**: **yes, add the APP-owned fresh egress callback below after backend readiness and all asynchronous preparation, immediately before sealed-context dispatch. Do not admit or charge the attempt again.** This is H00's design decision for root relay, not APP/RUNTIME agreement or independent finding closure.

Bound to candidate `f2acfb050b709c948a06cc090a74a974f5814515` and root's trusted-phase `run.py` addendum. Candidate identity is supplied by root/receipt; no Git was run. Actual read-only file hashes matched the receipt for app.py, authority.py, supervisor.py, model_adapter.py and worker.py. Launcher addendum SHA256 `06d5b4db081ad196098ba2e192ba53ebc84413692523e4484a315e9c99d38b43` matches the reviewed addendum, not the earlier freeze. Inputs: current SEAM.md worktree SHA256 `09380772d5e19838950d94e4cf94e682fc41d65fed217f8587d2e53b579b0985`; CODE_EARLY_REVIEW.md SHA256 `28e4876f764a6efd30b339316afb36505d8b3729ead38456563c77fea232d1a0`; inherited SEAM references pin final-v1 I01/I04/I06 and accepted R03/P01 amendments/closures. Changed input identities require affected recheck, not inherited acceptance.

Scope: CE-F01, CE-F03 and the CE-F06/R8-F01 persistence seam only. CE-F02/F04/F05 remain owner repairs under the actual review. Root reports four prior readiness calls, 97.204 seconds, confirmed cleanup. That updates the review's historical three-call attribution; H00 did not inspect or execute those calls. All model gates are now disabled; this document authorizes no further model calls or gate changes.

## 1. Exact callback extension

```python
Supervisor(runtime_dir=..., admit_attempt=service.admit_attempt,
           authorize_egress=service.authorize_egress,
           on_event=service.on_event, on_result=service.on_result)

async def authorize_egress(job_id: str, attempt_id: str,
                           fence: int, context_digest: str) -> dict: ...
```

Add a named constructor callback, retaining the existing architecture. A default `None` may preserve benign harness construction, but a model job with no callback MUST fail closed before dispatch. APP production composition always supplies it. No HTTP authorization endpoint, worker DB access, arbitrary URL/tool authority, token selection by HTTP or callback fallback to `admit_attempt`.

Response keys (all present; nullable check evidence on DENIED/UNKNOWN):

```text
decision: AUTHORIZED | DENIED | UNKNOWN
reason: bounded machine-readable code (OK only for AUTHORIZED)
job_id, attempt_id, lease_fence, context_digest: exact requested tuple
cancel_epoch: original admitted attempt epoch, or null if unresolved
decision_id: unique APP egress observation ID, or null if not committed
checked_at: UTC Unix seconds, or null
valid_until: UTC Unix seconds, or null
authority_vector_digest: digest of the full freshly checked vector, or null
model_gate_sha256: existing admission's still-current root gate digest, or null
```

AUTHORIZED requires every field non-null, exact tuple equality and vector/gate digests matching the already sealed admission. DENIED is a known failed precondition, not a failed/unknown transaction. UNKNOWN covers timeout, exception, unavailable/corrupt state, malformed response, unresolved admission or uncertain egress-observation commit; RUNTIME retains the original tuple when synthesizing it. No response returns a replacement context, model identity, attempt token, quota claim, permission to retry, or new grant. A decision ID is audit evidence, never a reusable bearer permit.

APP executes one short serialized authority transaction against the **already durably ADMITTED attempt**. Check attempt ID/job/fence/cancel binding; immutable job/request/reservation/route; job still eligible to dispatch; exact stored sealed-context digest; full `auth.check_current(..., phase='egress')` including current time, session/device, fixed grants/revocations/expiry, all influencing ancestors, rights/purpose/policy, audience/destination/route, authority/restore epochs and cancel/lease fence. Check the root model gate is currently enabled, unexpired and identical to the admission gate/model/phase binding. Preserve the existing exact grant selection; do not silently rebuild stale context or swap grants to make it pass.

At initial admission APP stores `context_digest` and `model_gate_sha256` on its existing attempt record alongside its existing token/model identity. Egress reads those records; it does not allocate or claim another slot. Digest uses the existing canonicalizer over the full dispatched context excluding only its companion `context_digest` field; image bytes and derivative/preprocessing bindings remain included. RUNTIME computes the same digest before requesting authorization and never mutates that context afterward.

Append an `EGRESS_DECISION` observation in existing APP event storage with full vector reference/digest, tuple, reason/check time and gate identity. Commit is the ordering point relative to serialized correction/revocation/cancel. Return AUTHORIZED only after a known successful commit. `valid_until` is no later than job/session/grant/gate expiry and **checked_at + 1 second**, a fixed first-profile dispatch window. No model/network/process wait occurs inside this transaction. No new allocation token, ModelLease CLAIM, finite GrantUseClaim, quota debit/refund or admission rewrite occurs in this check.

## 2. Required order and dispatch fence

1. Existing APP `admit_attempt` commits once. RUNTIME validates the admitted job/context and claims the existing allocated model slot once through the current ModelLease path.
2. Verify artifacts and establish the owned backend's loopback readiness. No context or generation/preload request is sent during readiness. Start the fixed worker waiting on empty stdin; complete `PROCESS_STARTED` event delivery and other asynchronous preparation. This is real process startup, not proof generation began.
3. Prepare the exact bounded request/frame and context digest. Only now await APP `authorize_egress` with timeout `min(2 seconds, remaining monotonic job deadline)`; skip it if remaining <= 0. Timeout does not renew the original deadline.
4. After the await, validate every response binding; recheck local cancel flag, original fence/attempt identity, supervisor closed/quarantined state, UTC expiry and original monotonic deadline. Require AUTHORIZED plus still-identical context/vector/model gate. No awaited logging/event/readiness callback may intervene before scheduling the sealed write.
5. The write task itself rechecks local cancellation/fence/deadline/window immediately before its first byte, so executor scheduling delay cannot bypass the post-await check. Dispatch the prepared frame once. Never resend it after an uncertain/partial pipe write. Persist dispatch/observation facts afterward; local append/callback failure is not permission to replay.
6. The fixed worker checks the supervisor-authored handoff expiry/job deadline before its existing fixed model generation call; it receives no authority callback or tools. Any new handoff fields carry only bound decision identity/time/digest, not an HTTP-selected endpoint. Reject a delayed expired request. Existing claim-exclusive generation marker remains once only. Report actual dispatch/generation timing where observable.

The one-second dispatch window bounds intentional queuing after the ordering point; the original job deadline and owned process stop path bound subsequent work. It is not an instantaneous revocation guarantee or hard real-time OS guarantee. Revocation/correction can race after a successful check and bytes can already be in flight. Cancel/stop then fences later work/releases and records actual/unknown transmission and cleanup. Fresh release/consume checks remain mandatory. If dispatch timing/termination cannot be observed, record UNKNOWN rather than claiming the race was eliminated.

On known denial: send **zero sealed-context frames and zero generation requests**, terminate only the owned idle worker/backend, retain the admitted model slot and elapsed/unknown resource charge, emit terminal FAILED (or CANCELLED for observed cancellation), and retain the reason. On callback/commit/identity uncertainty: same no-send/cleanup behavior, terminal INCONCLUSIVE. Failed cleanup holds capacity/quarantine and blocks model admissions. Denial does not refund an already admitted attempt. It also creates no release-grant debit: finite grant charging still occurs only at release. Root gate closure before the callback must deny even if an earlier admission succeeded.

## 3. CE-F03: terminal event separate from stop observations

RUNTIME emits one durable `ATTEMPT_TERMINAL` event through existing `_event`/APP `on_event` after final result disposition is known, or on **every** no-result/early-exit path. Use the normal outer event fields: unique stable `event_id`, job/request/attempt/fence/cancel identity, worker-instance/boot/nonce and actual PID/birth (explicit null before spawn). Snapshot immutable identity rather than aliasing mutable runtime state. No-admission UNKNOWN still has the submitted job/attempt tuple; do not require a successful attempt row to record that uncertainty.

Required `evidence` keys:

```text
job_disposition: SUCCEEDED | FAILED | CANCELLED | INCONCLUSIVE
reason: bounded code
result_disposition: RELEASE_ADMITTED | FENCED | REJECTED | UNKNOWN | NOT_PRODUCED
context_digest: exact digest or null before context is known
claim_id: existing model claim ID or null if none was made
admission_decision: ADMITTED | DENIED | UNKNOWN | NOT_REQUESTED
egress_decision_id: committed decision ID or null
cleanup_confirmed: true | false | null
usage: validated bounded usage object or null (never invented zero)
```

Mapping: unknown admission/egress, deadline without result, first malformed candidate, callback-unknown outcome or uncertain cleanup => INCONCLUSIVE. Known policy/egress denial or definite compute failure => FAILED. Observed cancellation => CANCELLED, with cleanup uncertainty separately visible. Validated result plus APP's known RELEASE_ADMITTED => SUCCEEDED; FENCED/REJECTED => FAILED unless cancellation explains CANCELLED; UNKNOWN => INCONCLUSIVE. A malformed or late duplicate never rewrites an earlier terminal result. Preserve specific reasons and compute/result observations rather than averaging them into success.

APP stores the event with digest/identity validation and atomically settles a matching QUEUED durable job. Known cancellation retains CANCELLED; a matching terminal event cannot regress SUCCEEDED/FAILED/CANCELLED or another settled projection. Unknown APP result callback may have committed a real release: if the DB already says SUCCEEDED with its immutable receipt, preserve that authoritative history and record the callback uncertainty separately. Later changes from INCONCLUSIVE require explicit same-identity reconciliation evidence, not a late arbitrary event.

`ATTEMPT_TERMINAL` NEVER establishes STOP_CONFIRMED or frees uncertain process capacity. Existing independent STOP_REQUESTED/STOP_CONFIRMED/UNKNOWN observations control compute state/capacity. APP must accept valid later stop evidence without reopening terminal disposition. On cancellation/fence changes, match terminal facts to the immutable attempt identity and append them to history; stale events do not overwrite the new job/fence. Queue occupancy/polling follows current disposition while owned capacity follows cleanup; those are separate counts.

Retain a terminal event whose APP callback fails as pending delivery in the runtime journal, with its exact event ID/payload. Bounded same-event redelivery/reconciliation is idempotent and must never reexecute the job or `on_result`. Do not claim durable APP settlement from a swallowed callback exception. No new shared store or broad event framework is needed.

## 4. CE-F06 / R8: runtime-owned settlement and outcome persistence

Keep the single ModelLease `SETTLE` at cleanup, preserving existing claim/charges/cleanup semantics. Replace misleading `outcome=QUEUED` on new settlements with explicit `phase=RESOURCE_SETTLED`, and `outcome=PENDING_VALIDATION` when a candidate awaits validation/APP release; otherwise record the known no-result disposition. Append a later runtime-ledger `RESULT_DISPOSITION` keyed by the same `claim_id`/attempt/context with final validation/release result and validated usage/certainty. No second SETTLE/CLAIM, refund, deleted failure or rewrite of historical four calls.

RUNTIME owns ledger writes, phase/outcome ordering and bounded usage validation in supervisor.py/model_adapter.py. Send the same claim-linked outcome/usage in `ATTEMPT_TERMINAL` (or the existing `RESULT_DISPOSITION` event with matching fields) so APP's existing event storage durably retains it. APP needs only identity validation/storage and terminal projection; it must not write the model ledger or recalculate charges. Backend-reported token/time usage remains BACKEND_REPORTED; absent/failed/callback-unknown data remains unknown. A crash between SETTLE and later outcome leaves PENDING_VALIDATION for read-only reconciliation, never an implicit success or retry.

## 5. Disjoint repairs and required independent barriers

| Owner | Narrow files and changes |
|---|---|
| APP | `haven/app.py`: add callback, admission binding fields, constructor wiring, terminal projection/event storage; `authority.py` only if needed for complete current preconditions; `contracts.py` response/event types if used; APP-owned tests. No runtime ledger edits. |
| RUNTIME | `haven/supervisor.py`: constructor extension/order/dispatch guards/all-path terminal events; `model_adapter.py`: settlement and appended outcome/usage; `worker.py`: fixed handoff expiry check only; RUNTIME-owned tests. No APP/authority/DB edits. |
| root | Relay this actual H00 answer, obtain real APP/RUNTIME responses, schedule repairs, update shared ledgers/freeze and control gates. Trusted phase CLI stays root-owned. |
| QA | Independent harness in evaluator sibling; actual APP callbacks plus benign/instrumented runtime, not stub authority decisions. Read-only candidate. |

All initial regression barriers below require **no model inference**; use an instrumented fixed transport/benign owned workload and frozen synthetic fixtures. Root may reopen gates only under the existing work package after owner repairs and independent evidence; this amendment itself does not authorize that.

| Barrier | Required observations |
|---|---|
| E1 — preparation race | Pause after durable admission/backend readiness before egress callback; separately revoke grant, correct uncited ancestor, expire session/grant, rotate session, cancel, change route/fence or disable gate. Zero context frames/generation calls/releases; attempt charge retained; actual owned cleanup. Include a positive unchanged-authority control that dispatches exactly once to the instrumented transport. |
| E2 — callback/write race | Callback DENIED, UNKNOWN, exception, timeout, unknown commit, wrong job/attempt/fence/digest/vector/gate and cancellation/deadline during await all prevent send. Delay write-task scheduling beyond valid_until: zero first-byte write. Mutate context after seal: reject. Duplicate callback observation cannot create another dispatch/claim. |
| E3 — post-check limitation | Force cancellation/revocation after first-byte dispatch; retain possible/in-flight disclosure, deny stale release, observe owned stop. Never assert zero sends or recall in this branch. |
| T1 — durable terminal | Actual APP callbacks + benign runtime: deadline/no result, malformed first candidate, admission UNKNOWN, egress UNKNOWN/denial and callback-unknown result yield prescribed HTTP dispositions; no permanently QUEUED job. Test duplicate/stale terminal/stop events, cancellation and already-committed release with lost callback reply. |
| T2 — capacity distinction | Confirmed cleanup releases owned capacity; unknown cleanup retains it/quarantine even after terminal HTTP disposition. APP callback failure retains pending same-ID event; later metadata-only redelivery settles once without result/job replay. |
| S1 — audit settlement | Accepted/fenced/rejected/callback-unknown outcomes each keep one claim/SETTLE, unchanged charges, separate resource/result phases and preserved prior entries. Usage is validated or explicitly unknown; claim-linked final facts reach APP event history. |

Root freezes repaired source/config plus the launcher addendum and routes candidate-bound evidence to the independent reviewer for affected CE-F01/F03/F06 closure. Other findings and protection NOT_ESTABLISHED remain; no canonical/production/original-R1 qualification is conferred. Existing final suite/model budgets and deadline remain unchanged. H00 read source/documents and wrote only this new file; no source/runtime execution, Git, model calls, shared-state edits or independent acceptance. Return to root and yield the slot.
