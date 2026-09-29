**CODE-EARLY: unresolved findings; DEVELOPMENT candidate only.** Independent static review, not final qualification. No candidate execution, tests, server requests, edits, Git, delegation, protected-oracle access, or messages were performed.

`<campaign>` denotes the supplied checkout. Paths below are relative to it.

Reviewed candidate `f2acfb050b709c948a06cc090a74a974f5814515`, using setup `8e1304caf82c0a889eeaea7691db7b9d7b98c526` and research baseline `6bc1c8df1218ceb0e0d8709adee65d1e44634047`. Commit attribution comes from the supplied receipt; I did not independently inspect Git.

The receipt `campaigns/IP-01/ip01-v2-20260929/receipts/DEVELOPMENT_CANDIDATE_01.json` has SHA256 `ba322121cc65c719083b0424824c9c3374585008ce077707008dd378d778afa2`, with source-manifest hash `da21f32c0fac50e5c7c0faf445af60b72f60d20d8231a675d8b1cfcca7637918`. At **05:18:46Z**, 24 of its 25 source-file hashes still matched. The sole difference was the disclosed launcher amendment below. No APP/RUNTIME owner-source drift was observed.

The following are source-supported defects. Proposed tests were **not executed** by this reviewer.

1. **CE-F01 — HIGH: the model egress check precedes asynchronous preparation, allowing stale input transmission.**

   Locations: `labs/ip01/haven/app.py:98`; `labs/ip01/haven/model_adapter.py:270`, `:278`, `:315`; `labs/ip01/haven/supervisor.py:522`, `:534`.

   APP performs its “egress” check inside initial admission. Runtime subsequently awaits artifact verification and backend startup, then sends the sealed context without another current-authority callback. Revoking a grant, correcting an uncited ancestor, rotating the session, or allowing a grant to expire during that interval does not prevent the later model request. Release can reject the resulting answer, but the stale inputs have already reached inference.

   **Minimal repair:** add a fresh APP-owned egress authorization for the existing admitted attempt after backend readiness and immediately before dispatching context. Recheck the complete vector, time and fences without minting another resource token or grant charge. Preserve the explicitly bounded race after that ordering point.

   **Independent test proposal:** hold execution after admission but before context dispatch; separately revoke, correct an uncited parent, and expire the session/grant. Resume toward an instrumented generation transport and assert zero generation sends, no output release, retained admission accounting, and observed cleanup. This initial regression needs no real inference.

2. **CE-F02 — MEDIUM: delayed responses can repopulate Person A’s content after switching to Person B.**

   Locations: `labs/ip01/haven/static/app.js:24`, `:26`, `:35`.

   `refresh()` and `consume()` apply their responses to global state and the DOM without checking which session initiated them. Switching people clears displayed answers, but does not invalidate outstanding operations. An A refresh delayed until after B’s refresh can overwrite the B workspace with A’s notes/drafts/jobs. A delayed A consumption response can similarly render after the switch and attempt its observation using B’s current session.

   **Minimal repair:** introduce a session-generation fence, invalidate it when switching begins, and discard stale responses before any state update, rendering, or observation. Clear persona-specific collections and pending dialog state. Cancellation of fetches alone is insufficient.

   **Independent test proposal:** delay an authenticated A `/api/notes` response, complete the switch and refresh as B, then deliver the A response. Assert that A’s private marker never appears under B. Repeat with a delayed consumed-answer response; assert no stale rendering or cross-session acknowledgment.

3. **CE-F03 — MEDIUM: terminal runtime outcomes do not consistently settle APP’s durable job projection.**

   Locations: `labs/ip01/haven/supervisor.py:538`, `:568`, `:589`; `labs/ip01/haven/app.py:145–157`.

   A running worker that reaches its deadline without a candidate becomes runtime `INCONCLUSIVE`, but emits only stop events; APP updates compute state while leaving disposition `QUEUED`. First-result schema rejection likewise emits `RESULT_REJECTED_SCHEMA`, which APP does not handle. These jobs can remain queued indefinitely, keep browser polling active, and eventually consume the 32-job queue allowance. Additionally, runtime admission `UNKNOWN` is emitted as `ADMISSION_DENIED`; APP maps it to `FAILED`, losing the uncertainty distinction.

   **Minimal repair:** deliver an explicit, identity-bound terminal outcome and map it into APP without conflating disposition with termination. Preserve UNKNOWN as INCONCLUSIVE and prevent late events from regressing settled jobs.

   **Independent test proposal:** connect actual APP callbacks to the benign runtime harness. Exercise deadline-without-result, malformed first candidate, and UNKNOWN admission. Assert matching durable HTTP dispositions, independently correct compute states, released or retained capacity as appropriate, and no regression from malformed duplicates. Existing runtime tests chiefly inspect runtime snapshots through stub callbacks.

4. **CE-F04 — MEDIUM: shared-ancestor memoization can bypass the depth-16 bound.**

   Location: `labs/ip01/haven/authority.py:54–78`, particularly the early return at `:62–63`.

   Previously visited sources are skipped without considering their remaining ancestor depth. Construct `c16 → c15 → … → c0`, then a new root with parents `{c8,c16}`, ordered so `c8` is visited first. The cached `c8` stops traversal when reached through `c16`, allowing a longest path of 17 edges. This remains within the source and edge-count limits. The existing linear-chain test does not cover this graph.

   **Minimal repair:** validate longest-path depth independently of closure deduplication, using cycle-aware memoized ancestor height or equivalent bounded graph validation.

   **Independent test proposal:** use deterministic fixture IDs ordering `c8` before `c16`; assert rejection of the 17-edge redundant-parent graph, acceptance at 16, and identical decisions under root/parent ordering permutations. No disclosure bypass is established by this finding; the confirmed defect is admission-bound enforcement.

5. **CE-F05 — MEDIUM: an exhausted grant can shadow a newly approved usable grant.**

   Locations: `labs/ip01/haven/authority.py:38–49`, `:252–255`.

   For overlapping active grants, selection always chooses the lexicographically first ID, without considering quota for a new release. If exhausted G1 sorts before newly approved G2, a fresh answer binds G1 and fails `GRANT_QUOTA_EXHAUSTED` despite G2 having available quota. The outcome depends on generated grant-ID ordering.

   **Minimal repair:** distinguish grant selection for a new release from source reading and existing-claim redemption. Select a satisfying grant with available release quota when sealing a new operation; preserve fixed grant bindings afterward. Do **not** add an unused-quota requirement to consumption.

   **Independent test proposal:** deterministically order G1 before G2. Charge G1’s sole release but leave its slot unconsumed; approve G2; request a fresh answer. Assert that it charges G2, while G1’s original slot still consumes once at remaining zero. Further releases must fail once both grants are exhausted.

6. **CE-F06 / R8-F01 — LOW: settlement records a premature outcome label.**

   Locations: `labs/ip01/haven/supervisor.py:576–579`, `:611–619`; `labs/ip01/haven/model_adapter.py:115–124`.

   Static ordering confirms the author’s reported defect: `ModelLease.finish()` records disposition before candidate validation and APP’s result callback. A successful computation can therefore retain `SETTLE.outcome="QUEUED"`.

   **Classification:** audit-metadata defect. This trace does not establish broken slot/time accounting or false cleanup confirmation. The reported three completed calls and 61.72 settled seconds remain attributed development evidence, not this reviewer’s model verdict.

   **Minimal repair:** retain resource settlement at cleanup, use an explicit pending-validation phase where applicable, and append a later claim-linked validation/release disposition. Preserve existing ledger entries and accounting; no retry, refund, or historical rewrite.

   **Independent test proposal:** cover accepted, fenced, rejected, and callback-unknown candidates. Assert one settlement, unchanged charges, separate cleanup and result facts, and immutable prior records.

The **launcher addendum** was inspected separately. Current `labs/ip01/scripts/run.py` SHA256 is `06d5b4db081ad196098ba2e192ba53ebc84413692523e4484a315e9c99d38b43`, replacing the receipt’s `5ee9fb5f92c9977be4754675ebe136bd13bf42758207a98abad907b065a9a656`. Lines `123–124`, `148`, `159`, and `253–254` implement the reported phase mismatch rejection, explicit child-environment propagation, owner-phase record, and constrained CLI choices. Static inspection supports this bounded correction: it adds no HTTP-selected authority and leaves gate/token checks required. **No prior launcher PASS transfers to these bytes.** Independently recheck all three phase selections, same-phase duplicate start, conflicting-phase rejection, restart, and gate-closed denial.

Coverage included every `labs/ip01/haven/*.py` module, template/static assets, launcher, dependency lock, supplied APP/runtime tests and preparation fixtures. ROOT publication/freeze/snapshot helpers were supporting review only. I read the exact reviewer profile and referenced authorization/protocol, scoped IP-01 package, SEAM, I01–I06, and accepted R03/P01 amendments and closures. The five controlling contract/amendment/closure files matched their registry raw-byte pins.

Useful controls are present in the source: complete-vector equality and uncited-parent closure; transactional joint charging with distinct accounting revisions; consumption at zero remaining quota; immutable four-record history; duplicate/history paths without payload replay; session/destination/nonce checks; restart fencing and rollback quarantine; owned-process identity checks and fail-closed uncertain capacity; separate APP token binding/runtime claim; bounded image normalization; Host/Origin/CSRF checks; and inert text rendering. These observations do not substitute for execution.

Evidence limitations remain material. APP’s 124 tests, browser/restart handbacks, RUNTIME’s 18 lifecycle/13 ledger cases, and independent benign QA’s 13 scenarios/21 oracle checks were reviewed as attributed evidence. The 104 APP vector cases mutate captured vectors across four phases; they do not establish backing-state mutation coverage at actual egress. Retained QA-E2E `KeyError` findings require evaluator triage and are not independently classified here as product failures. Private logs, runtime databases, protected answers, and protected evaluator assets were not accessed.

**Q-CODE-EARLY-01, for root relay to H00/APP/RUNTIME:** will the seam add an APP-owned `authorize_egress(job_id, attempt_id, fence, context_digest)` handshake after backend readiness, without a second resource claim? SEAM requires fresh egress checks but currently exposes only admission/event/result callbacks. This is an actual open implementation question; no peer response or delivered message is claimed.

Next needed validation is independent reproduction of these findings, owner repairs, a new candidate freeze including the launcher, and affected integration/browser rechecks before the distinct CODE-FINAL review. Protection remains **NOT_ESTABLISHED**, so the final pilot must remain **EVALUATION_INCONCLUSIVE** on that basis. No production, canonical, real-authentication, OS-enforcement, original R1/M0, or final model qualification is asserted.

Signed-role: **haven_code_reviewer — Assignment 10 / CODE-EARLY — 2026-09-29.**
