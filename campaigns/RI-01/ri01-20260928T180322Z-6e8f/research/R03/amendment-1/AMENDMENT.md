# R03-A1 — Finite-use admission and existing-claim redemption

Author `/root/ri01_privacy`, H04/R03, 2026-09-28. **SUBMITTED_FOR_INDEPENDENT_RECHECK**. Author revision 1; no self-acceptance. Base reported by supervisor: `376031e182c57495912baf6727093b0b188da568`. Assigned scope: documentation only, this amendment directory. Original eleven R03 files remain unchanged. No application/schema/test execution, Git, installations, accounts/devices or child agents.

## Input receipt and exact supersession

Read independent `reviews/REVIEW-R03/REVIEW.md`, SHA256 `cc393683b0db1ff0723cc6688196bfe11871b6844019cf2d3ecd4b29ab330952`. F01/Q-R03-USE-01 identifies an ambiguity between charging a finite grant at release and checking/consuming later; it is not an observed implementation failure. L01 requests final CODE-0 attribution. The review accepts a bounded substantial subset but requires F01 clarification before finite-use contract freeze.

This amendment supersedes only the finite-use/accounting sentences in original `CONTRACTS.md` §§B/E (SHA256 `cfd271d1650e40daa735651ddc2ab28ca4ccdcb17f117c96cc5602975bad5eea`), refines its §C grant-revision meaning, and adds subcases to `EXPERIMENTS.md` P20/P21. The original vector, rights/subject intersection, release/consume/remote-race, deletion, private-device and domain boundaries remain. No original case becomes executed. R03-P0 remains AUTHORIZATION_REQUIRED.

Also read final `reviews/CODE-0/REVIEW.md`, independently matched SHA256 `066bbc38273320895dbd5cf1fc3fde31c209253103fa2e170dbf905ff8d4abc8`; and frozen `research/R02-P01/amendment-1/AMENDMENT.md`, independently matched SHA256 `3efda1609fb138adc6bef9d125ac2390f4ccc484e797ab2eeefc7f4d26cc3605`. Local paths are campaign-relative. Their source/base provenance follows the original review/intake records; no new Git reachability claim.

## A1. Exactly what one finite use means

P0 supports a registered finite-use profile `ONE_RELEASE_ONE_DESTINATION_WHOLE_OUTPUT`. **One use is one successfully committed release admission**, binding one immutable whole-output digest to one exact destination/route/audience and complete input/authority vector, with at most one matching consumption-permit slot. It is not one read, byte, token, human perception, successful delivery or consumption request. Failed delivery does not undo that admitted disclosure right. Provider egress, digital writes, sensing and physical dispatch keep separately registered operations and limits; this profile grants none of them.

No caller may choose the counting unit. `GrantRecord` adds `counted_operation_profile_ref` and `quota_ledger_ref`; the approving authority fixes the profile and `max_uses`. Undefined or incompatible profiles fail `UNSUPPORTED_PROFILE`. P0 rejects chunked/multi-destination finite-use profiles instead of guessing their counting semantics. A later reviewed fixed-manifest profile could bind finite ordered chunk slots at release and consume each slot once without charging the parent grant again, but is **DEFERRED**, not claimed by P0. Existing broader future chunk research remains retained.

For every applicable finite grant, release admission creates exactly one immutable `GrantUseClaim`. One release requiring several independent grants charges each applicable grant once, in the same transaction; if any is ineligible, none are charged. A repeated reference to the same grant in one dependency closure is deduplicated by that exact grant/profile, not charged once per source. Different operations/purposes are not merged by this rule. Unlimited recurring grants retain current authority checks and need no fabricated finite-use counter.

## A2. Durable claim and separate revisions

`GrantUseClaim` requires:

- unique `claim_id`, `grant_id`, grant authorization revision and revocation epoch, counted-operation profile, `units=1`;
- immutable release operation ID and idempotency key, request digest, release ID, whole-output digest/canonicalization version, exact destination/route/audience binding;
- checked complete authority-vector reference/digest, source closure, authority-instance/restore epochs;
- admission commit sequence/time, claim validity end (no later than grant/release expiry), and exact permitted consumption-slot ID;
- accounting transaction reference and `quota_ledger_sequence_after`.

The claim is an audit-bound right for one already admitted operation, **not** a transferable token or irrevocable authorization. Possession of its ID grants nothing. `GrantUseClaim` is immutable; redemption, revocation association, abandonment and observed delivery are append-only events.

Separate `GrantRecord.authorization_revision` (the existing vector's `revision`) from `QuotaLedger.accounting_sequence`. Changes to purpose, scope, allowed operation/profile, destination class, max_uses, expiry, suspension or revocation change authorization state/revision or the corresponding revocation epoch. Authenticated broadening follows the original new-approval rule. Charging a use only advances the quota accounting sequence/count; it does **not** change grant authorization revision, invalidate its own claim or mutate its recorded vector. The same separation applies if other already-authorized releases consume other available quota.

`QuotaLedger.charged_units` is monotonic for this profile, backed by committed unique claims; `remaining=max_uses-charged_units`. Counts/sequence are not bearer authority. They are checked transactionally for **new admission** and recorded in admission evidence. They are not required to equal an old snapshot during redemption of its existing claim. Storage-row revisions used for database concurrency must not be confused with the semantic authorization revision. A max_uses change is an authorization change, not an accounting-only adjustment.

## A3. New admission versus redemption

**New release admission**, serialized with other admissions and authority mutations:

1. Resolve exact operation/idempotency key and immutable request hash. An existing identical operation returns its historical receipt/claim references without any new charge or permission to transmit; different payload/target under the key rejects. Check current eligibility separately before later redemption.
2. Revalidate all current authorization, subject/rights/source/device/session/policy/cancel/lease/time/expiry preconditions. For every finite grant, additionally require `remaining >= 1` and the exact registered counted-operation profile.
3. Atomically append each unique `GrantUseClaim`, increment each finite quota ledger once, append release authorization and its outbox reference, then commit. This known successful commit charges the uses and authorizes the named release. Rollback charges nothing. Unknown commit outcome authorizes no send and requires read-only reconciliation; absent client receipt is not proof of rollback.

**Existing-claim redemption (`consume_output`)**, also serialized with revocation/correction/cancel:

1. Authenticate destination/session and resolve the exact committed claim, release and consumption slot. Verify exact operation/output/destination/route/audience/nonce bindings, unique slot and known successful admission. A claim from another output/destination, a restored instance or a different grant revision cannot be substituted.
2. Revalidate current grant authorization revision/revocation/status/expiry, source lineage, rights/subjects, policy, device/session/audience, cancellation, lease, authority/restore epoch and all original applicable eligibility rules. Check claim/release validity too. **Do not require unused parent quota and do not increment the parent grant's charged_units again.** Exhaustion caused by this valid claim alone is not a denial reason. It does not exempt revocation, expiry or any other relevant change.
3. If eligible and the exact slot is unused, atomically mark that slot consumed via an immutable `ConsumptionPermitReceipt` and append its event. This consumes the one-use permit slot, not another grant quota unit and not human perception. The result may authorize one immediate attempt under the original destination/race constraints.

A slot already consumed returns history/current eligibility, never a newly executable permit. Duplicate consume requests/ACKs do not charge or consume again. Different payload/nonce/destination trying to reuse a committed slot is a conflict. Read-only receipt reconciliation may disclose only currently authorized content-minimal facts; it does not resend payload or mint a permit.

Concrete max_uses=1 trace: start authorization revision7, revocation epoch2, charged_units0. R1 admission commits claim C1 and charged_units1/accounting sequence1, leaving authorization revision7. Concurrent distinct R2 then fails quota; C1's still-valid matching consumption may commit slot S1 once despite remaining0. Charged_units stays1. If revoke/expire/correct/cancel occurs before S1 admission, S1 is denied while C1 remains historically charged. No transaction claims actual display.

## A4. Lost replies, abandonment and explicit replay

| Event | Quota/claim effect | Delivery/next-operation rule |
|---|---|---|
| Release transaction known rolled back | No committed claim/charge | No authorization; any later admission must pass current checks |
| Release commit or reply unknown | Do not infer either zero charge or success | No send; reconcile authoritative operation/claim under same immutable identity; no replacement release/key to bypass uncertainty |
| Confirmed committed release, reply recovered; slot has never been consumed | Existing charge retained | May redeem the existing unused exact slot once after full fresh checks; this is neither new admission nor permit remint |
| Consumption commits but permit reply is lost | Charge and consumed slot remain | `CONSUMPTION_RESPONSE_UNKNOWN`; possible downstream delivery uncertainty remains separate. Never reset slot or remint permit; read-only reconciliation only |
| Send/playback ACK lost | Charge/consumption remain | DELIVERY_UNKNOWN survives revoke/cancel; no inference of NOT_SENT |
| Release abandoned, payload deleted, claim expires, grant revoked or later checks deny | Existing charge retained, no automatic refund | Historical operation remains; future use denied as applicable |
| User explicitly requests replay | New operation/key and new release claim/charge under current policy | Requires fresh eligible quota; max_uses1 already charged fails. A separately authenticated new grant may permit replay, but is never silently issued |
| Partial/uncertain earlier presentation | No refund or reset | Explain potential duplicate disclosure; explicit replay is not permission to relabel earlier outcome as failed |

No automatic negative quota entries or refunds exist in P0. Intentional replenishment/broadened quota requires a new authenticated authorization decision and an independently eligible release, not mutation/deletion of old claim history. A newly issued grant cannot revive an old consumed slot. Financial provider reservations remain the separate original accounting contract; this grant-use ledger is not a billing ledger.

## A5. Actual answer to Q-R02P01-A1-R03-01

Question received via root from `/root/ri01_runtime_probe`: are immutable release authorization, append-only per-destination/chunk delivery and current permit eligibility compatible with R03 E, with CONSUMED meaning authorization consumption rather than perception?

**Author answer actually sent to root: yes.** Preserve the P01 four-record model: immutable release authorization, immutable consumption permit receipt, append-only delivery observations and separately evaluated current eligibility. A lost ACK remains unknown after revocation; historically reported display/playback remains historical after cancellation; future eligibility can independently be denied. Exact output/destination/sequence/full-vector bindings are required. An authenticated report is not proof a human perceived content. Existing R03 remote race remains explicit.

Focused clarification to P01-A1's phrase “check/use-count update”: with the finite-use profile above, release admission changes the **parent grant quota**; consumption admission changes only the **exact claim's permit-slot state**. It must not debit the parent quota a second time. P01's broader per-chunk tuples remain a useful future design, while finite-use P0 supports whole-output only and rejects unsupported chunk profiles. This is a compatible narrowing of the first implementation profile, not deletion of the multimodal/streaming target. Root must route this exact clarification for independent recheck; no peer agreement or reviewer acceptance is inferred.

## A6. Final CODE-0 addendum (REVIEW-R03-L01)

At original R03 writing, only the root-relayed interim CODE-0 message was read; its final-file pending statements remain correct historical evidence. This amendment now consumes the final review at the hash above. CODE-M1 confirms retained full context, raw rejected/revoked backend output and request/attempt/time/backend metadata are a production-transfer gap, while the synthetic README discloses its retained-history scope. Original R03 CONTRACTS F already explicitly covers those classes, caches/exports and derivatives with scoped retention/access/deletion and minimized receipts. The final report is now a concrete dependency for R03-P0 instead of a pending artifact.

Carry CODE-H1 parent-death containment, H2 release fence, M2 semantic scoring, M3 concurrency/durability, M4 protected independent evaluator and M5 configuration-versus-isolation limits into later acceptance. These are final-review findings, not new source execution or claims the gaps were fixed. Current M0/R1 remains CODE_NOT_AVAILABLE to that review; historical33/11 laboratory tests are not R03 execution. No new whole-lab inspection or application tests performed here.

## A7. Proposed package/test delta and closeout

`PROPOSED_CASES.md` adds finite-use subcases to original P20/P21 and the orthogonal-history assertions. Every case is NOT_EXECUTED. P0 must implement the registered whole-output profile above or explicitly return UNSUPPORTED_PROFILE; it cannot advertise unspecified max_uses behavior. Original scope, budgets, utility gates, offline denial, physical flags and AUTHORIZATION_REQUIRED remain.

Actual work: read exact independent review, original contracts, frozen P01 amendment and final CODE-0; verify hashes; write this scoped author clarification and input-use receipt; check document/JSON integrity and byte preservation only. Reused: original authority/vector/deletion boundaries and P01 orthogonal records. Amended: counting operation, durable claim, quota versus authorization revision and recovery semantics. Rejected: double-charge, quota-exhaustion invalidating its own claim, silent refund/remint and rewriting unknown/past delivery. Deferred: finite-use chunk/multi-destination profile and all live execution. Independent reviewer decides F01/L01 closure; no self-approval.
