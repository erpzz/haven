# R03 proposed authority contracts v1

DESIGN_PROPOSAL; not executable schemas, production permissions or changes to inert starter v1. Logical components can remain in one process/database. H00 owns canonical integration after H02/H04/H06/domain review. All IDs are opaque references, not bearer grants. Integrity/authentication is supplied by the trusted service/channel; a JSON signature-shaped field or SHA-256 alone provides no authority.

## A. Common values and trust boundary

Use `{type,id,revision,sha256}` references, UTC RFC3339 times, nonnegative integer milliseconds for durations, and exact enum/version checks. Unknown is explicit null plus reason, never revision0 or fake identity. Epochs/revisions are nonwrapping positive integers scoped to a named authority instance; duplicates/conflicts/overflow fail closed. Canonicalization version is bound to digests. Bounds for P0: 2 synthetic people, 32 sources, 16 required grants per result, 128 lineage edges, depth16, 64KiB metadata and 256KiB output; oversized/incomplete closures are denied, not truncated. Production scale needs separately reviewed bounds.

Identity fields: authenticated `actor_principal_ref`, `session_ref`, `device_ref`, `service_ref`, `job_ref`, `sponsor_ref`; data fields: `subject_refs`, `resource_steward_refs`, `rights_binding_refs`, `audience_refs`, `source_refs`. Authenticator owns the first set; source registry resolves the second. Models cannot set trusted fields. Error messages must not disclose whether another person's private source exists. Internal scoped audit distinguishes inaccessible, absent and corrupt refs.

## B. GrantRecord and RightsBinding

`GrantRecord` required fields:

- `grant_id`, `revision`, `revocation_epoch`, `authority_instance_epoch`, issuer identity and authority reference, authenticated approval receipt, required subject/rights-holder requirement it satisfies.
- actor/service scope, exact resource/source/area/session scope, allowed operation IDs, purpose IDs and versions, allowed audiences, providers/endpoints/data-processing profiles, output-channel classes, derived-use permission.
- `not_before`, `expires_at`, retention-policy reference, `max_uses` or explicit recurring limit, current use count, status (`ACTIVE|REVOKED|EXPIRED|SUSPENDED`), predecessor/supersession refs and policy revision.

A grant is issued only by an authenticated authorized human or separately approved standing-policy path. A model may produce the unchanged inert `consent_proposal` only. One use of a release operation does not consume an unlimited recurring read grant; count-limited grants update use counters in the same admission transaction. Grant changes require compare-and-swap; broadening creates a new authenticated approval. Revocation applies to the named purpose/operation/resource grant, not silently to all unrelated personal activity.

`RightsBinding` includes steward, known subjects or approved anonymous participant/area scope, decision requirements, license/terms refs, allowed data class, obligations and unresolved status. Resource stewardship is operational control, not proof of copyright ownership or consent. A required consent unknown is denial for the affected operation. Public licensed material may use a reviewed rights policy instead of fictitious subject grants; existing privacy/terms restrictions still apply.

## C. AuthorityVector

```
vector_version
authority_instance_epoch, restore_epoch
policy_ref, purpose_definition_ref, rights_policy_refs[]
principal_ref, session_revision, device_binding_revision, device_epoch
service_capability_revision, tool_catalog_digest
grant_dependencies[{id, revision, revocation_epoch}]
source_dependencies[{id, revision, sha256, lineage_epoch, authenticity_epoch}]
subject_scope_revision, participant_area_scope_revision
job_ref, lease_fence, cancel_scope_epochs[{scope_id, epoch}]
destination_ref, destination_epoch, audience_revision, route_profile_revision
provider_data_policy_revision (explicit NOT_APPLICABLE when local)
dependency_closure_digest, canonicalization_version
```

This is a versioned equality/precondition vector, not a globally meaningful scalar clock. Every dependency used to obtain or derive output appears in the closure, including uncited model context, transforms/calibration where they change claim eligibility, summaries and cached intermediates. Some fields may be explicitly NOT_APPLICABLE only under a registered operation profile. Omitted unknown fields, unknown versions and unrecognized semantics reject.

A freshness-sensitive operation also checks authoritative current time, clock uncertainty and expiry at admission; equality of revisions alone cannot keep an expired grant valid. A lineage index may optimize closure checks only if root revision/generation maintenance is atomic with every dependency change; an eventually consistent index is not a security boundary. Source content is immutable under a revision and a correction appends a successor.

R02 C01 creates trusted context from this state; C02 copies a non-authorizing snapshot; C10 presents expected vector. R06 AccessBinding projects its grants/purpose/recipients/provider/area/retention into the same vocabulary with exact version mapping. R08 C05 adds `sealed_manifest`, machine boot/configuration, supervision, qualification and resource lease; it shares precondition semantics, not publication authorization.

## D. Effective policy algorithm

1. Authenticate actor/session/device/service; resolve the action's domain and exact destination/account. Deny unknown principal/ambiguous recipient.
2. Resolve complete immutable input closure under current policy; check source authenticity/validity and required rights/subject decisions. Detect cycles/unresolved parents.
3. For each required authority requirement, find a currently valid satisfying grant using the registered rule. Compute intersection of allowed operations/purposes/audiences/providers/area/output routes. Requested full audience must be a subset of every applicable allowlist. Retention deadline is minimum. No grant union for joint contributors.
4. Check actor capability, job lease/cancel, current time/clock bounds, budget and domain-specific prerequisites. Eligibility is tested before retrieval/ranking and before egress/release. Denied sources do not leak titles, counts, similarity scores or private error detail.
5. Bind immutable output digest, source closure and policy result; independent content validation can fail even if authorization passes. Generation using disallowed input cannot be salvaged by dropping its citation.

If source A allows `{local,P}` and B allows `{local,Q}`, a joint summary may use local only. If A permits recipients `{A,B}` and B permits `{B}`, requester A cannot receive the joint summary; an authorized B job may. If neither grants derive, separate readable inputs do not grant a combined summary. Relating anonymous RF to a named health record is a new subject-association operation requiring explicit authority and validated evidence.

## E. Release/consumption protocol and receipts

`authorize_release` input: trusted context, expected complete vector, exact output hash/ref, kind, audience/destination/route, bounded validity interval, immutable operation idempotency key. Trusted gate is sole producer; output adapter is consumer.

Proposed transaction:

1. Begin a short write transaction on the single authoritative store; acquire writer eligibility before reading mutable authority (`BEGIN IMMEDIATE` is a candidate). No network, model or device call occurs inside it.
2. Resolve current state and complete dependency closure. Compare expected vector; validate output/content state, expiry, budget/lease/cancel, destination and exact request hash. A matching old idempotency receipt is history only and must not bypass current eligibility for a new delivery.
3. Atomically consume applicable finite grant uses and unique release operation; append immutable `ReleaseReceipt` and outbox reference. Commit. Unknown commit returns `RELEASE_UNKNOWN` and requires read-only reconciliation; no send based on uncertainty.
4. Outbox adapter rechecks eligibility on dequeue. Every transfer of private bytes to an external destination has its own disclosure/egress admission. Do not put plaintext in an unauthenticated notification, URL, progress stream or queue accessible to other principals.

`ReleaseReceipt`: release ID, operation key, output digest, authenticated authorizer, authority instance, exact checked vector/digest, audience/device/route, ordered commit sequence, authority timestamp/clock uncertainty, status `RELEASE_AUTHORIZED|REJECTED`, bounded expiry, reasons, no payload plaintext. A released payload remains in a separately scoped short-lived buffer under its retention policy.

`consume_output`: destination authenticates via approved channel and requests an exact release/chunk permit with session/device/destination epoch and nonce. Authority serializes fresh validation and one-time consumption with revocations, appends `ConsumptionPermitReceipt`; destination validates current session/route, known epoch, exact payload, nonce and time bound before presenting. The authority's consumption commit consumes the operation, not proof of sensory display. Lost permit reply stays uncertain; do not remint the same permit for blind replay. A new explicit replay is a newly authorized operation after reconciliation.

`DeliveryReceipt`: release/consume/chunk IDs, adapter identity/version, destination/session/route, payload digest, transmitted time, destination-reported start/end/stop times, last acknowledged chunk, status `NOT_SENT|SENT_UNACKNOWLEDGED|DISPLAY_REPORTED|PLAYBACK_REPORTED|STOP_REPORTED|SUPPRESSED|DELIVERY_UNKNOWN`, associated revocation/correction/cancel refs and reconciliation state. Receipt authentication establishes reporter, not perception by a named human. Source/identity revision changes between release and consume cause denial. Old queued chunks on reconnect are discarded and revalidated; authority unavailable => private output unavailable. An already rendered image/audio sample may remain exposed.

The local order is revoke-first ⇒ deny release; release-first ⇒ past authorization recorded with later fencing. A later consumption check may still reject a prior release. Revoke after consumption can race remote physical presentation; report potential disclosure and best-effort halt, never erase the historical receipt. There is no atomic transaction spanning SQLite, network, native audio buffers and human perception. P0 tests model these boundaries explicitly; production maximum buffering/disclosure intervals remain unqualified.

## F. Revocation, correction, deletion and restoration

`change_authority`: authenticated actor, operation, target scope, expected revision, reason, idempotency key. Transaction advances relevant epochs and appends change receipt; prevents future admission under old vector. Cancellation hierarchy includes ancestors: job children cannot evade a parent cancel epoch. Different scope types prevent stop-speech from silently becoming a physical kill command.

`correct_source`: authorized edit, expected source revision, new immutable bytes/ref, source/subject impact, retention decision; append successor and advance lineage epoch atomically. Derived invalidation can propagate asynchronously because fresh release checks resolve changed roots before use. Preserve superseded historical data only when still authorized and clearly labeled; new derived output requires regeneration/revalidation.

`delete_source`: tombstone and deny use atomically; queue per-storage deletion. `DeletionReceipt` includes source reference without deleted payload, affected storage/derivative classes, local deny commit, request/ACK/confirmed outcomes, backup expiration, provider/recipient unknowns, exceptions with authority/review/expiry, next reconciliation. `INACCESSIBLE` and `ERASURE_VERIFIED` are distinct, with actual technique/evidence needed for the latter.

Scope also includes request text, input context packets, rejected/raw model outputs, attempts, timestamps, backend identity and exports—not only the source and successful answer. Request metadata itself can reveal sensitive activity. Minimize by default; content necessary for a debugging trial needs explicit purpose/retention and separate access. Restored backups must not re-enable old jobs, tokens, timers, output permits or physical attempts. Fresh authority-instance/restore epoch, trusted latest revocation reconciliation and review-only default are mandatory; inability to establish latest authority denies reuse.

## G. Accounts, dispatch, cancellation and accounting

`AccountBinding`: person, provider issuer, logical account, resource audience, token-secret reference, granted provider scopes, Haven operation/purpose restrictions, connector revision, status/revocation generation. Token material resolves only at a broker authorized for that issuer/audience. A provider token may be broader than Haven policy; broker enforcement must narrow it. Never pass a token to a model or reuse another principal's credential because a tool is read-only.

`DispatchPermit`: common authority vector + exact sealed payload/resource/configuration/boot, qualified action template, supervising operator/session, not-before/start expiry, maximum attempts1, parent resource budget and recovery policy. Domain's short authoritative admission transaction consumes one attempt and records intent. Send and physical effect are separate; uncertain sends never auto-retry. Restoring a database cannot restore an unconsumed physical right. Motion and sensing remain independent permits even when coordinated by one proposal.

`CancelOutcome` has separately nullable observations: request received; new admission fenced; output fenced; owned process termination confirmed; provider cancellation acknowledged; remote compute/billing unknown; acquisition cessation reported/verified/unknown; recovery request/result. Worker-parent death containment requires separate qualified supervisor evidence, not a `finally` assumption. Concurrent use of a shared inference server must be tested without terminating unrelated users' work.

Reservation expiry releases only unused, never-admitted capacity. Admitted uncertain work retains worst-case exposure pending conservative terminal reconciliation. Settlement uses immutable provider request ID, original usage categories/rate revision, integer monetary units, explicit rounding and idempotency; repeated cancellation/receipt cannot double-release budget. Provider usage/cost unknown stays unknown. H02 owns arithmetic/profile specifics; H04 denies a request if its admission budget condition is unresolved.

## H. Required errors and retry classes

`IDENTITY_UNKNOWN`, `AUTH_EXPIRED`, `AUTH_REVOKED`, `SUBJECT_SCOPE_UNKNOWN`, `RIGHTS_UNRESOLVED`, `AUDIENCE_DENIED`, `PROVIDER_DENIED`, `SOURCE_COMPROMISED`, `STALE_CONTEXT`, `REVISION_CONFLICT`, `LINEAGE_INCOMPLETE`, `UNSUPPORTED_PROFILE`, `LEASE_LOST`, `CANCELLED`, `DEADLINE_EXCEEDED`, `BUDGET_EXHAUSTED`, `RELEASE_UNKNOWN`, `DELIVERY_UNKNOWN`, `ACQUISITION_STOP_UNKNOWN`, `OUTCOME_UNKNOWN`, `RESTORE_QUARANTINED`.

Unknown/denied authority is not a prompt-repair opportunity. Identical request/key reads existing receipt; changed payload conflicts. Read-only reconciliation requires current read authority and never replays side effects. Pure recomputation gets a new bounded attempt/current vector. Physical unknown locks affected resource pending domain reconciliation. Public error strings are content-minimal; internal receipt access stays scoped.
