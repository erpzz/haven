# R03 — Two-person privacy and cross-domain authority

Thread R03 / ownership H04 / RI-01 issue #17. Author `/root/ri01_privacy`, 2026-09-28. Base `376031e182c57495912baf6727093b0b188da568`, as recorded by supervisor; exact input identities in INPUT_USE.json and INPUT_RECEIPT.md. Owned output: this R03 directory, version 1. Public-safe synthetic design. **DRAFT_READY; independent review requested; NOT_UPLOADED by child.** No implementation, model evaluation, account enrollment, sensor activation or physical acceptance. Exact model not exposed.

## One-page integration summary

Recommend one trusted authorization decision path with explicit person, device, service and job identities; separate private A, private B and deliberately shared data. Use the existing thin coordinator and SQLite direction. A family relationship, shared computer, consent proposal, authenticated login, available tool or model answer creates no cross-person grant. Consent governs permitted processing; it is not a universal ownership assertion, copyright license, device-control right or clinical authorization.

Share a versioned dependency vector across R02 C01/C02/C10, R06 AccessBinding and R08 C05. Keep publication, provider egress, digital writes, sensing and physical dispatch as different operations with different consumption points and receipts. Each derives authority from the exact sources, subjects, purposes, recipients, destination and policy. A grant for one operation never converts into another. The proposed SQLite release transaction orders local authority; it does not atomically transact with a remote screen, printer or aircraft.

The smallest useful slice is a deterministic two-user synthetic note/image-reference question with one authenticated mock output sink, joint-source intersection, correction/revocation/cancellation races, honest unknown delivery and backup restoration into review-only state. Existing v1 mock schemas remain inert. No identity provider, broker fleet, vector database, paid inference or physical hardware is prerequisite. Later independently enrolled humans may opt into a narrow selected-record local read/summary slice after security, deletion and output-device acceptance. Stronger privacy against a shared host administrator requires moving plaintext/key control to a separately trusted endpoint, with availability and usability costs.

All fifteen upstream CRs have a disposition below. R02 F01 receives an ordering design; F02–F06 retain explicit implementation/evaluation obligations. R06's deadline and cessation amendments are carried. R08 metrology, pose, evaluator independence and stop semantics remain domain obligations. No absent historical review is reconstructed and no prior test count becomes a privacy guarantee.

## Decisions

### D01 — Identity, subjects, stewardship and audience

`principal` is the authenticated actor requesting an operation. `subject` identifies a person to whom information relates; it is not necessarily the recorder, requester or account holder. `resource_steward` is the account/storage controller allowed to administer that resource under its own rules. `rights_binding` separately records applicable license, third-party restrictions and the required decision makers. `audience` is the complete intended recipient set, including a shared endpoint's allowed exposure class. `sponsor` pays/budgets a job; `service` performs a narrow function. None substitutes for another.

A photo captured by A may concern A, B and a bystander; A's capture does not establish B's consent or the bystander's release. A shared calendar event may contain another person's private note. Unknown subject association is UNKNOWN and cannot be filled from face/speaker/RF recognition. For anonymous sensing, use an approved participant/area/session scope; do not fabricate identified subjects. Public human datasets keep `PUBLIC_LICENSED_RESEARCH` plus documented rights and restrictions, never `RESEARCH_SYNTHETIC`.

Independent enrollment must let B decline, pause, inspect and withdraw without A granting on B's behalf. A may manage the host but cannot manufacture B's authenticated consent receipt. In a shared-admin prototype this is an application promise, not protection from a malicious administrator. Passkey-style authentication is a candidate for later enrollment: WebAuthn credentials are relying-party scoped and server origin checks matter, but successful authentication alone is not transaction consent [S04]. Recovery/device replacement must not silently transfer the other person's grants.

### D02 — Joint sources and explicit purpose

The effective policy for a derived result is the intersection of every contributing parent's operations, purposes, audiences, provider/endpoint classes, area/session and retention constraints, plus the actor's capabilities and destination policy. Every required subject/rights-holder decision must resolve. A permitted provider for A and a different permitted provider for B yields no hosted route; a permitted local route may remain. Expiry/retention is the earliest applicable limit. A restrictive denial overrides a permissive grant. Required grants must all be current; multiple alternative grants can satisfy one requirement only through an explicit policy rule, not a union of privileges.

Separate `read`, `retain`, `derive`, `share`, `cloud_transmit`, `audible_output` and `emergency_disclose`; do not overload a vague purpose string. Purpose names are registered stable IDs with versioned definitions; models cannot relabel an action to evade a restriction. Revoking sharing need not prevent an independently authorized private read. Withdrawing collection must prevent new acquisition even if retention of old observations has a separately valid policy. Corrections invalidate current-use derivatives; historical authorized review may retain clearly superseded evidence under the retention policy.

The dependency set includes all context that actually influenced generation, not only cited sources. A model cannot omit a citation to launder private information. A result generated using a disallowed parent must be discarded or regenerated from permitted parents under a fresh job; deleting a sentence or cropping an image does not establish independence. Independently reviewed nonreconstructive aggregation is a later profile, not a default exception. Acquisition footprint matters before collection: RF processing/cropping cannot make through-wall capture confined to the displayed polygon.

R01 consultation clarification: a reviewed minimized excerpt still requires its own sharing grant **and** every applicable source/subject/rights dependency. A future trusted exact-payload release flow may establish separately defined sharing semantics only with all required approvals and explicit retention/revocation consequences; automatic detachment is denied. An independently authored new statement must honestly record its origin and cannot be a model-derived excerpt relabeled to escape revocation.

### D03 — Publication, correction and cancellation

CONTRACTS.md defines a proposed `AuthorityVector` and `authorize_release` operation. In one authoritative database write transaction, resolve the complete dependency closure and compare current revisions/epochs, validate payload/destination, consume the one-use release operation and append receipt/outbox reference. Revoke, correct, delete, device/session changes and cancel update the same authoritative state. Successful commit orders **RELEASE_AUTHORIZED**. A transaction failure or unresolved commit outcome is not a send permission. SQLite documents serialized writes; use one authority database and a short write transaction, not a stale read followed by an unconstrained send [S01]. This is a design recommendation, not an executed database test.

After release, an authenticated destination requests a fresh, one-use consumption permit for exact output/chunk/device/session/audience, rechecking authority and current epochs. It must reject a locally known newer epoch, expired permit, unsupported policy or unresolved online check. Reconnect discards old queued permits and revalidates. No private plaintext in push notifications or pre-validation streaming; neutral progress is allowed. A provider request is itself disclosure and requires its own egress check before sending any input.

Offline product wording: “I can’t verify current sharing permission while offline, so this queued answer is unavailable until I reconnect.” Do not newly release or replay a private/shared cached answer without current verification. Previously shown or exported content may still exist. A future offline-permit profile would knowingly admit delayed revocation and requires its own approval/testing; it is not part of P0.

**Residual race:** a revocation can occur after the destination's authorization response but before physical display/playback; bytes already sent, screen pixels, OS buffers, human memory, screenshots and compromised clients cannot be recalled. The contract promises ordering at named authority operations and suppression when a new revocation is known, not globally instantaneous recall. Destination ACK is attributed device evidence, not proof that only the named human perceived the content. An unacknowledged send is `DELIVERY_UNKNOWN`, never safely unsent. A UI may offer a newly authorized replay after reconciliation; automatic duplicate playback is denied. For later streaming, each bounded chunk has its own permit and cancellation check; the chunk duration and measured buffering bound require modality-specific qualification.

Revocation after server release invalidates unconsumed permits, fences future use, requests cooperative removal/stop on reachable endpoints and records known/unknown exposure. Correction after release adds a linked correction notice only to an audience still authorized to receive it; do not repeat sensitive text in the notice. Deletion triggers propagation without rewriting historical disclosure facts. Cancellation of speech, reasoning, reminder and domain recovery remain separate targets. `ADMISSION_STOPPED`, `OUTPUT_FENCED`, `OWNED_COMPUTE_STOPPED`, `REMOTE_COMPUTE_UNKNOWN` and `ACQUISITION_STOP_UNKNOWN` are independent observations. A timeout or lease expiry cannot prove process death, no remote charge or physical stop.

### D04 — Retention, deletion, backups and restoration

On authorized deletion, atomically tombstone the source, advance its lineage epoch and deny current access before asynchronous deletion begins. Traverse raw payloads, derivatives, transcripts, thumbnails, embeddings, summaries, semantic/result caches, indexes, output queues and provider storage references. Maintain a content-minimal propagation receipt with target class, request/ack/result, deadline and unresolved copies. Opaque identifiers and hashes can still be linkable personal data; keep those receipts scoped and time-bounded too. Do not publish raw sensitive content to make audits immutable.

Define a concrete per-class retention schedule before real enrollment. The synthetic first slice proposes active fixtures for the test run, no private provider storage, and disposable synthetic backups; production durations are not selected here. Live deletion means inaccessible through the application, not proven forensic erasure. SQLite's `secure_delete` has ordinary-table and virtual-table limitations; database/WAL files, snapshots, caches and storage media require separately validated handling [S08]. Media sanitization is a distinct program whose current NIST revision is SP 800-88 Rev.2 (2025) [S05]; this report does not prescribe or claim an SSD erase.

Backups awaiting expiry must be excluded from normal access and subject to the documented destruction/replacement schedule. ICO's backup guidance is a useful design reference for placing data beyond operational use and explaining retention limits; it is UK-specific guidance, not a determination of Haven's legal obligations [S06]. Provider deletion requests and copies already exported to recipients remain separately reported, never a universal completion claim.

Restoration is review-only with a newly generated authority-instance/restore epoch; no credentials, old execution permits, jobs, reminders or output buffers resume. Reconcile current revocations/tombstones from a trusted source newer than the backup before exposing restored personal data. If trustworthy latest state is unavailable, quarantine and require renewed independent grants; the restored database cannot attest that its own old grants are current. Key destruction is meaningful only if all relevant key copies and plaintext replicas are covered. A shared admin who previously read plaintext remains outside a retroactive erasure guarantee.

### D05 — Devices, private outputs and account credentials

Device possession, watch proximity, voice similarity, glasses identity and nearby UWB do not authenticate the current person. Bind an independently authenticated session to a device revision and output route; borrowed/lost/replaced device changes advance epochs. Private output defaults to the authenticated unlocked personal application. Lock-screen notifications use neutral text; shared speakers/displays require explicit audience permission. Route changes (headset disconnect, casting, shared audio, user switch, lock) fence queued private output. Physical bystanders remain a residual observation risk; offer tap-to-reveal and explicit playback. Haptics are also output and can reveal status; choose low-information private cues under the same policy. Native output routing/lock behavior requires actual later device tests.

Provider-account tokens live in a dedicated credential boundary, never prompts, source documents, public logs, output artifacts or generic worker environment. Broker resolution binds person + issuer + account + scopes + resource audience + connector revision; a visible MCP tool is no grant. Use OAuth authorization-code protections including PKCE where applicable, exact redirect validation, narrowly scoped access and provider-supported refresh-token protection. RFC 9700 is the 2025 security BCP; deployment support must be checked per provider [S02]. Do not treat OAuth resource-owner vocabulary as universal ownership of every record's subjects.

Disconnect immediately disables Haven-side use and starts provider revocation/deletion reconciliation. RFC 7009 permits revocation propagation delays and a successful invalid-token response, so record local fence and provider result separately [S03]. Do not infer an external write failed because its token was later revoked; reconcile the original operation without replay. MCP security guidance rejects token passthrough and calls for per-client consent and audience separation [S07]. Personal enrollment explicitly excludes employer/customer contexts; the same human's work-admin role is not transferable personal authority.

### D06 — Compromised evidence and trustworthy outcomes

HTML instructions, image text, audio commands, CAD metadata, tool descriptions and retrieved memory are data. Models can propose typed actions but cannot change grants, destination, evaluator, tool catalog or execution identity. Validate evidence authenticity status separately from hash integrity, time/calibration and claim correctness. A perfectly hashed false record remains false. Mark compromised sources/issuers SUSPECT or REVOKED, invalidate affected descendants and qualification dependencies, fence output/dispatch and require independent read-only reconciliation. Preserve minimal necessary incident evidence under a scoped policy; compromise does not license indefinite retention of everything.

Trustworthy transport authenticates who asserted an observation, not its physical truth. A compromised device may sign a false completion. High-consequence acceptance requires independently governed evidence and qualified domain verification. Semantic relevance/entailment scoring remains separate from quote and evidence-ID checks. Shared servers, local networks and asset ownership do not automatically confer trust; NIST's zero-trust abstract supports this principle, not a certified household deployment [S09]. Use practical process/account separation first and do not call it admin-proof encryption.

### D07 — Standing emergency policy and physical authority

Keep standing policies useful and explicit: exact issuer/subject, qualifying evidence, recipient/channel, data classes, location resolution, expiry/review, maximum effects, resource ceilings, cancellation and independent fallback. Each person preauthorizes their own emergency disclosure separately. A missed message is not proof of incapacitation. A model inference cannot expand emergency recipients or convert an ordinary note-sharing grant into health disclosure. If multiple people are implicated, apply the joint-source rule or create an independently permitted minimum report; do not assert an emergency exception from research prose.

Three separate future policy classes are `DAILY_ROUTINE`, `EMERGENCY_INFORMATION` and domain-specific `PHYSICAL_OPERATION`. A policy for emergency preparation/disclosure does not authorize calling a real responder, entering private space, starting a drone, driving a robot, transmitting RF or starting a printer. Physical admission also needs configured equipment, legal operating scope, capability qualification, present material conditions, recovery/supervision and domain evidence. Keep emergency help/communications independent of experimental drones and of a research-worker shutdown. A stop-speech action must not disable an independent alarm or communication pathway. This document makes no medical diagnosis, clinical treatment claim or jurisdiction-specific emergency-law determination.

R08 C05 dispatch checks shared identity/source/policy vector plus sealed manifest, machine boot/configuration, operator/supervision, budget and domain qualification. Its atomic consumption creates a dispatch attempt, not a publication receipt or proof of actual start. Lost acknowledgement yields `OUTCOME_UNKNOWN`, no automatic second START_ONCE. Revoke-before-dispatch denies; revoke-after-dispatch invokes qualified in-progress handling. Record stop request, controller ACK, observed halt and handling state separately. R06 sensing uses its own acquisition permit; carrier motion needs another permit. R06 amended E0 deadline is **60 seconds total per episode**, at most eight attempted selections, each consuming remaining time; this cannot create physical stop guarantees.

## Evidence

CODE-0 interim consultation, relayed by root from `/root/ri01_code_review`, reports that the recovered coordinator persists full context and raw backend output even after rejection/revocation; fresh-read withholding retains request text, timestamps, attempts and backend identity, and grant revocation does not erase those records. Its README explicitly confines this to synthetic audit history. Treat this as a **production-transfer gap**, not a demonstrated violation of that stated synthetic scope. R03 did not rerun or independently inspect those code lines in this assignment. CONTRACTS §F explicitly covers these content and metadata classes; final CODE-0 file/hash remains pending and must be consumed by the later package.

Fresh primary documentation reviewed: SQLite isolation/secure deletion; IETF OAuth security and revocation; W3C WebAuthn; NIST sanitization and zero trust; ICO backup erasure guidance; MCP security; Apple Data Protection overview. Sources and limits are in SOURCES.md. Apple describes per-file protection classes and key accessibility [S10]; it does not prove Haven, a borrowed phone, shared screen or unlocked inference process is private. No product pricing, phone SKU or cryptographic isolation guarantee is inferred.

| Work | Actual state |
|---|---|
| Exact upstream review hashes, canonical requirements count and contract reading | Performed with read-only file tools |
| Public primary research | Documentation/text inspected; mutable response bytes not archived |
| Source image/figure/audio/video inspection | Not needed for these protocol claims; DOCUMENTATION_ONLY. No direct media inspection claimed |
| Grant engine, release/destination protocol and tests | PROPOSED_NOT_IMPLEMENTED / NOT_EXECUTED |
| Existing synthetic lab behavior | Only reviewed reports reused; no rerun or new equivalence assertion |
| Real authentication, data deletion, native-device privacy, emergency/physical safety | NOT_EXECUTED / NOT_QUALIFIED |

## Interface changes

CONTRACTS.md provides `AuthorityVector`, authoritative `GrantRecord`, rights/subject bindings, release/consumption receipts, revocation/correction/deletion and account/physical specializations. Proposed namespace `haven.authority.proposed.v1`; no canonical schema or current M0 database changed. All v1 `PROPOSED_NOT_GRANTED`, real-private-data=false and execution=false invariants remain. A schema-valid synthetic identity never migrates to a real identity.

### Complete upstream CR disposition (H04 recommendation; no self-approval)

| CR | Decision | Concrete condition and deferred boundary |
|---|---|---|
| CR-R02-01 | AMEND | Reuse JobSpec direction; add vector and distinct cancel/containment states. Real worker termination awaits F02/R1 evidence |
| CR-R02-02 | AMEND | C01/C04/C10 use D01–D05 and CONTRACTS release/consume protocol; no `immediately before` ambiguity |
| CR-R02-03 | ACCEPT | Reuse provenance/validity/claim binding; add explicit subjects, all influencing parents and compromised-lineage invalidation. Physical truth/qualification deferred |
| CR-R02-04 | AMEND | Separate authority, budget and execution lifecycles; keep admitted unknown exposure reserved, idempotent settlement, conservative expiry; no spend grant |
| CR-R02-05 | AMEND | Reuse domain mapping; reject generic execution and consent-proposal conversion. Separate disclosure, digital mutation and domain dispatch consumption |
| CR-R06-01 | ACCEPT | Required paired/hash-bound sidecar and unknown states retained. Exact spatial/covariance adapter remains H08/R07-owned; no qualification |
| CR-R06-02 | AMEND | D01/D02 rights/subject/session bindings and full dependency intersection; public-human data is not synthetic; live enrollment/acquisition DEFER |
| CR-R06-03 | AMEND | Exact catalog/footprint/participant acquisition permit; motion separate; stop request/ACK/confirmed cessation/unknown distinct |
| CR-R06-04 | AMEND | 60-second TOTAL E0 deadline, eight attempted selections maximum, quotas/fences; lease expiry is not confirmed hardware stop |
| CR-R06-05 | ACCEPT | Immutable qualification successor with authenticated independent reviewer and legal/configuration scope; actual promotion/physical evidence DEFER |
| CR-R08-01 | AMEND | Protected protocol/parent budget; H04-authenticated roles and H06-held holdout; proposer cannot self-lock/accept |
| CR-R08-02 | AMEND | Preserve BOM/specimen lineage; initial template-only mode; changing material/lot/orientation/assembly invalidates affected qualification |
| CR-R08-03 | AMEND | Recorder identity plus source/subject policy; H08 exact parent-frame left perturbation and uncertainty; metrology accuracy DEFER |
| CR-R08-04 | AMEND | One-use dispatch permit separate from release; shared vector + machine/seal/boot/supervision checks; lost ACK unknown/no replay; hardware gates DEFER |
| CR-R08-05 | AMEND | Authenticated reviewer authority, competence/independence and protected evidence; exact-scope invalidation; operational acceptance DEFER |

`ACCEPT` accepts the bounded proposed concept; required cross-cutting restrictions still apply. No CR is accepted as a deployed production contract. Deferred scope has re-entry conditions in NEXT_PACKAGE.md.

### Review finding closure

| Finding | R03 response | Remaining evidence owner |
|---|---|---|
| R02 F01 | D03/CONTRACTS names release, consume and dispatch ordering, vector, races and delayed-delivery fence | R02/H04 synthetic interleaving tests; native endpoint qualification later |
| R02 F02 | D03 distinguishes suppression, owned-compute termination, remote billing and acquisition stop; parent death and shared server tests required | R1/H02; not closed by this design |
| R02 F03 | D06 and experiment E02 separate semantic task success from quote/auth checks | H02/H06 protected semantic evaluation |
| R02 F04 | D02/D05 cover all modalities and derived parents; evidence mode is explicit | MM-VISION/MM-AV/MM-FUSION native-media testing |
| R02 F05 | EXPERIMENTS freezes oracle, classes and gates before implementation tuning; count families, retain failures | H06 independent protocol/holdout control |
| R02 F06 | CONTRACTS reservation admitted/unknown handling; no release of liability by cancellation/expiry | H02 accounting implementation/test |
| R06 AMEND-01 | D07 chooses 60 seconds total / max8 attempted observations / remaining budget | H02/H06 deterministic slow-selector case |
| R06 AMEND-02 | D03/D07 explicit acquisition stop observations/unknown; late data quarantine | R06/R07 future qualified adapters |
| R08 M1–M5/L1 | Missing original audits remain attributed; retain exact pose, illustrative physical thresholds, real stop semantics, template-only and protected evaluator requirements; license layers not ownership | R08-P00/H06/H08; no physical thresholds or licenses approved here |

## Acceptance

Retain REQ-PRIV-01–09 and AT-PRIV-01–09 exactly; all remain NOT_EXECUTED. EXPERIMENTS.md supplies an explicit crosswalk and proposed cases under original EX02 and EX32. Dependencies also touch REQ-DAILY-04/06/08/09, REQ-AI-05/06/07, REQ-WEAR-06/07, REQ-RF-10 and cross-domain execution boundaries; this task does not claim their complete acceptance. Canonical register still has 102 requirements. This is not a new replacement requirement set.

The near-term useful outcome is an answer grounded in an authorized selected synthetic record with private/shared behavior and reliable receipts. The ambitious target is cooperative multimodal field assistance: independently consented wearables, recorded scene/RF/time replay, current source lineage and private haptics/AR while qualified resources act only under their domain permits. Test the boundary first without deleting that ambition.

## Risks and open questions

Input-use closeout: reused thin-coordinator/inert-v1 boundaries, source lineage, R06 sidecar semantics and R08 independent evaluator/domain permits; amended revision ordering, joint-source restrictions, budget/cancel and retention propagation; rejected consent-as-ownership, metadata-as-consent, output suppression-as-termination, cropped RF-as-contained collection and receipt-as-physical success. Unresolved: actual native endpoints, production identity/deletion/security, finite synthetic implementation results, independent R1 evidence and final CODE-0 report. These unresolved items do not authorize broader work.

Unknown real identity-provider/native client behavior, third-party account semantics, complete storage topology and retention schedules block real enrollment, not the synthetic slice. Host-admin privacy cannot be resolved by adding ACL fields. Provider support, endpoint data retention, actual recovery credentials and native output routing must be pinned at the later package. No universal bystander consent or public-dataset legal conclusion is supplied. Privacy usability can fail if every read needs confirmation; use narrow revocable standing read/summary policies with understandable active-state controls rather than a confirmation on every step.

Distributed revocation has an unavoidable already-released/in-flight boundary; represent it honestly and minimize permitted delivery duration/content. Destination compromise or physical observation can defeat intended private display. Data correction cannot rewrite what another person already saw. Minimal audit retention and source erasure have a deliberate tradeoff. Qualification claims remain invalid until independent review and actual execution evidence.

## Next package

NEXT_PACKAGE.md defines **R03-P0, AUTHORIZATION_REQUIRED**, deterministic synthetic authority/publication tests in a new approved sandbox with no external effects. Maturity: L0 reviewed design → L1 deterministic synthetic protocol → L2 authenticated local isolated trial → L3 independent two-person selected-data enrollment → L4 provider/native multimodal/partition tests → L5 separately qualified domain and emergency standing policies. Each level needs its own evidence and approval; L1 does not unlock L3 or L5.

Affordable path: existing CPU, standard-library fixtures and an approved SQLite test environment, zero additional provider spend/hardware purchases. Suggested implementation ceiling 1 GiB RAM, 100 MiB synthetic artifacts, 30-minute test run, four-hour coding timebox; these are proposed bounds, not measured resource use. Ambitious multi-endpoint experiments begin only after an inert transport simulator and successful data-control drill. A failure or unsupported privacy claim stops promotion, while ordinary public research and private-independent usefulness can continue.
