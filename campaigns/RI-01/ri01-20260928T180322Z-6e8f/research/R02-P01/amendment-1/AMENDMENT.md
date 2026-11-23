# R02-P01-A1 — orthogonal publication facts

Author: /root/ri01_runtime_probe, haven_researcher. Date: 2026-09-28. Status: SUBMITTED_FOR_INDEPENDENT_RECHECK. This is author revision 1, not acceptance of its own changes.

## Scope and exact supersession

The five original R02-P01 artifacts remain byte-identical. This amendment supersedes only the definitions at the following exact pinned anchors; the 44-test crosswalk and accepted historical evidence are unchanged:

- REPORT.md SHA ac62eb73800e12b08e6fd46c9206d64bdbe8f7e28844f87cb54b46f8815197c7, line68: replace “These are reviewed design proposals” with **“These are proposed interfaces submitted for independent review.”** Upstream accepted subsets remain attributed to their actual reviews; this amendment awaits its own recheck.
- Same REPORT, F01 beginning line77, especially line81: the authoritative release/delivery relationship is the four-record model below. Other vector, transaction, expiry, privacy and physical-authority restrictions remain.
- Same REPORT, F02 beginning line87, especially the publication_state enum at line92: **delete that combined enum as an authoritative contract.** Use release receipts, consumption receipts, delivery observations and current future-eligibility decisions separately. Compute state and termination evidence remain orthogonal and unchanged.
- NEXT_PACKAGE.md SHA d278dc54606db1a50803a9b50085b25389ec515f9ea5b95aecaf4223d98c7a8f, P02-B beginning line42: replace its ambiguous publication/delivery state request at line46 and refine schedules at line48 with the bounded package delta below. Existing prerequisites, costs, paths, review gates and AUTHORIZATION_REQUIRED remain.

Required input: independent REVIEW-R02-P01, SHA1634b53af3fe0799bcabd5adfbef5658d64812e9d2425c457bc09f3e7faa8589. Its M1 is the mandatory state-model correction; L1 is the wording correction. That review accepted the historical reconciliation, accounting, modality/evaluation separation and bounded next-package direction only as an explicit subset.

R03 CONTRACTS.md SHA cfd271d1650e40daa735651ddc2ab28ca4ccdcb17f117c96cc5602975bad5eea, sections C/E, is now an exact input. It is an attributed author proposal under independent review, not independently accepted by this amendment. Section E explicitly distinguishes consumption commit from sensory display and describes destination-reported delivery. CODE-0's final report SHA066bbc38273320895dbd5cf1fc3fde31c209253103fa2e170dbf905ff8d4abc8 is a newly available exact input; CODE-H2 supports the release gap, CODE-M1 the retention distinction, and CODE-H1 preserves unknown computation.

## Authoritative proposed facts — replacement for F01/F02 publication state

No single publication enum is authoritative. Four separately retained kinds of records answer four different questions. All identifiers are opaque and confer no permission by themselves.

**1. ReleaseAuthorizationReceipt — what the server committed.** Immutable after a known successful commit. Bind release_id, operation idempotency key, exact output digest and canonicalization version, manifest of chunk IDs/order/digests where chunked, exact destination/route and audience bindings, authorizer/authority-instance identity, commit sequence, complete checked authority vector/digest, bounded expiry and decision. A committed RELEASE_AUTHORIZED receipt remains historical RELEASE_AUTHORIZED after revocation, cancellation or failed delivery. A REJECTED receipt is a separate decision record and cannot replace a previous authorization. If commit outcome is unknown, append an operation observation RELEASE_UNKNOWN and reconcile read-only by the immutable operation key; do not send or infer that an authorization exists. “No receipt observed” is not proof that no commit occurred.

**2. ConsumptionPermitReceipt — which exact one-use operation was consumed.** Immutable authority-side record bound to release_id, output digest, chunk ID/index/digest (or explicit whole-output marker), destination/session/device/route, audience, nonce, operation key, consumption sequence, complete freshly checked vector, validity interval and authority epoch. Serialize its check/use-count update/append with revoke, correct and cancel. A prior release receipt alone never permits consumption. A positive consume decision cannot be reused for another chunk, destination, output revision or reconnect. Lost permit response is unknown delivery, not unused permission; do not remint the same permit for blind replay. A later explicitly requested replay is a distinct operation after current authorization and reconciliation.

**3. DeliveryObservation — what an authenticated destination/adapter reported.** Append-only events per exact release/consumption/destination/chunk tuple. Bind the output and chunk digest, release/consumption sequences, adapter identity/version, session/device/route, checked-vector reference, authority/cancel/restore epochs, observed and reported timestamps/uncertainty, and acknowledgment identity. Event kinds follow R03 E: NOT_SENT, SENT_UNACKNOWLEDGED, DISPLAY_REPORTED, PLAYBACK_REPORTED, STOP_REPORTED, SUPPRESSED, DELIVERY_UNKNOWN. Retain conflicting or late evidence with provenance; a materialized projection may reconcile uncertainty without deleting earlier observations.

DISPLAY_REPORTED/PLAYBACK_REPORTED means an authenticated reporter asserted that event, not proof a named human perceived it. SUPPRESSED is valid only for a specified not-yet-released/not-sent future delivery operation with evidence of prevention; it cannot overwrite an earlier sent/unknown or display/playback event. After a lost acknowledgment and later revoke, append the revoke/fence association and retain DELIVERY_UNKNOWN. Do not report NOT_SENT merely because no acknowledgment arrived. STOP_REPORTED records a stop observation for its scope and time, not erasure of earlier playback.

**4. PermitEligibilityDecision — whether another operation can be admitted now.** Evaluate complete current authority/session/device/audience/source/policy/cancel/restore/lease dependencies and expiry for the exact target operation. Record decision_id, target tuple, check sequence/time, complete current vector, triggering revoke/correct/cancel refs and result ELIGIBLE_AT_CHECK, DENIED or UNKNOWN. ELIGIBLE_AT_CHECK is an observation, not a reusable bearer grant: the actual release/consumption transaction still validates and consumes atomically. DENIED/UNKNOWN blocks new private transfers/consumption. Revocation and cancellation update authority facts and append eligibility decisions; they do not rewrite past release/consumption/delivery history.

Common binding: output_digest + canonicalization_version + chunk_manifest_digest + chunk_id/index/digest + destination_ref/epoch + route_profile_revision + audience_revision + release_sequence + consumption_sequence when present + complete checked AuthorityVector. AuthorityVector includes authority-instance/restore epochs, principal/session/device bindings, grants and revocation epochs, complete source/lineage dependencies, policy/purpose, job/lease fence and scoped cancellation epochs as R03 C specifies. Whole-output operations use an explicit whole-output marker; absent unknown fields never become wildcard matches. The binding prevents an acknowledgment for one chunk or destination from settling another.

A UI may derive a summary such as “Previously authorized; delivery unknown; future delivery denied.” That summary is **NON_AUTHORITATIVE** and must expose these separate facts. The retired combined publication_state enum must not be stored as the source of truth, drive permits, erase history or settle billing.

Computation stays independent: NOT_STARTED/RUNNING/STOP_REQUESTED/STOP_CONFIRMED/UNKNOWN plus exact execution identity and stop evidence. Denied future delivery and suppressed later chunks do not prove STOP_CONFIRMED. Confirmed local-wrapper exit does not establish remote/shared compute termination or zero cost. E0-H1/CODE-H1 remain open.

## Required proposed traces — not executed tests

### Trace A: authorized release, lost acknowledgment, then revocation

1. Under authority vector V1, transaction sequence100 commits immutable release R-A for exact output O-A/chunk1/destination D-A; decision RELEASE_AUTHORIZED.
2. A fresh V1 check at sequence101 consumes one-use permit P-A for that exact tuple. Adapter records SENT_UNACKNOWLEDGED. The destination may or may not have displayed it; acknowledgment is lost.
3. Reconciliation appends DELIVERY_UNKNOWN with P-A, sequence101 and the exact chunk digest. Neither R-A nor P-A is changed.
4. At sequence102, the relevant grant is revoked, advancing its revocation epoch to V2. Current future eligibility for this output/destination is DENIED. No new consume/replay permit is issued. Any queued unconsumed later operation is fenced.
5. Final facts: R-A RELEASE_AUTHORIZED historically; P-A consumed historically; chunk1 delivery UNKNOWN; future permits DENIED; computation/billing retain their separately observed or unknown states. A late authenticated display acknowledgment may add DISPLAY_REPORTED for chunk1, while future eligibility remains DENIED. No recall claim.

If only release was authorized and no consumption/send was yet admitted, revoke-first at consumption denies the operation; do not conflate that distinct trace with the lost-ACK trace above.

### Trace B: delivered chunk, then cancellation

1. Release R-B commits an ordered two-chunk manifest for exact destination D-B. Chunk1 consumes P-B1 under V1 and an authenticated destination reports PLAYBACK_REPORTED for its exact digest.
2. At sequence203, cancellation increments the job's scoped cancel epoch to V2. Append the cancellation event and DENIED future eligibility. Chunk2 has no consumed permit and is suppressed as a new delivery operation.
3. Chunk1's playback history and immutable R-B/P-B1 records remain. A later STOP_REPORTED event may document attempted/observed buffer interruption, but cannot change played audio into SUPPRESSED.
4. Final facts: chunk1 playback reported; chunk2 suppressed/not sent under the documented controlled boundary; future permits denied; compute STOP_REQUESTED or UNKNOWN until independent termination evidence exists. If chunk2 had already received a permit or been buffered, report potential/unknown in-flight disclosure instead of this “not sent” conclusion.

The server authorization/consumption ordering point does not create a distributed atomic transaction spanning network, device buffers and human perception. Revocation after permit consumption may race presentation. Stop best efforts and new admission separately; preserve already-issued/in-flight disclosure limits.

STATE_TRACES.json gives the same two symbolic proposed traces with per-axis terminal facts and required assertions. Digest symbols there stand for exact payload/chunk hashes in a future fixture, not hashes of real inspected media.

## P02-B supplemental implementation request

Replace “publication/delivery states” with the four-record model above. Implement immutable release/consumption receipts, append-only per-destination/chunk delivery observations and separately recomputed eligibility. If a display summary is offered, label it non-authoritative and test that it cannot grant permission or rewrite evidence.

Keep the original 12 schedule families; refine “release before revoke” and “delayed destination consume after revoke” with Trace A and Trace B, covering both no-permit and in-flight-permit branches. Also assert that duplicate acknowledgments are idempotently recorded, conflicting authenticated acknowledgments remain auditable, wrong digest/destination/sequence/vector/nonce cannot update a delivery fact, old permits are discarded on reconnect, and unknown commit never licenses send. These are focused subcases, not a new model or framework package.

Acceptance obligations: receipt bytes/history preserved through revoke/cancel; exact tuple matching; no fresh permit after a relevant denial; unknown ACK cannot become NOT_SENT; previous display cannot become SUPPRESSED; future eligibility changes independently; computation termination and monetary reconciliation remain independent. All cases are PROPOSED_NOT_EXECUTED. Existing no-provider, synthetic-only, reviewed R03/CORE prerequisite, resource ceilings and separate operator authorization remain unchanged.

## Actual work, scope retained and pending review

Actual: read the full independent P01 review, R03 C/E and exact CODE-0 report; clarify submitted design semantics; author two proposed traces and concrete INPUT_USE records; hash-check original artifacts and JSON structure. No application/schema/test execution, Git action, install, model call, account/device access or new scientific benchmark.

One early specialist question Q-R02P01-A1-R03-01 was sent through root; the question asks whether consumption means one-use authorization consumption rather than verified display. R03 E already states that distinction explicitly, so independent author work did not wait. Any subsequent actual answer is appended below with provenance.

This amendment leaves the44-method crosswalk, original102 REQ/AT scope,32EX, full multimodal program, original M4 qwen2.5vl:3b, synthetic N1/N2 scores, M0/R1 separation and missing original H00/later R1 review explicit and unchanged. No self-acceptance: the independent reviewer must decide M1/L1 closure before contract freeze.

