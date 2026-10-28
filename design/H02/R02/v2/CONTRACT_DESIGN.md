# R02 — Proposed runtime interfaces and shared-contract changes

**DESIGN_PROPOSAL; not schemas, implementation, production authorization or an M0 amendment.** Names below are proposed stable boundaries for H00 review. Existing contracts remain byte-for-byte unchanged. Versions identify data meaning, not permission to execute.

## 1. Baseline discrepancies that must be resolved explicitly

| Existing source | Actual baseline | Proposed disposition |
|---|---|---|
| `contracts/agent_job.schema.json`, `urn:haven:draft:agent_job:1` | States are PROPOSED, MOCK_RUNNING, MOCK_COMPLETED, MOCK_FAILED, CANCELLED; `physical_execution_enabled` and `external_network_enabled` are constant false | Retain v1 fixtures. Propose a separate runtime JobSpec v2; do not widen v1 state enums/flags |
| `docs/13_RUNTIME_AGENTS.md` | Rich lifecycle includes CREATED, ELIGIBLE, RUNNING, waiting/suspended states and OUTCOME_UNKNOWN | Adopt these semantics in the reviewed runtime design; distinguish them from mock state labels |
| `context_packet.schema.json`, `urn:haven:draft:context_packet:1` | One `grant_revision`; coarse owner scope; evidence IDs; cloud allowlist; input cap; expiry; real private data constant false | v2 needs per-grant revisions, subjects, audience, purposes, versions/hashes, token/media accounting and publication recheck |
| `evidence.schema.json`, `urn:haven:draft:evidence:1` | Capture/receive time, origin, claim class, parent hashes/IDs, freshness, frame/calibration; physical qualification constant false | Preserve fields; add provenance resolution and explicit temporal/uncertainty metadata through reviewed v2 extension |
| `consent_proposal.schema.json` | `PROPOSED_NOT_GRANTED` only | Never treat this as a granted authorization object; H04 must define authoritative grants separately |
| Daily and physical proposal schemas | `execution_enabled: false`; physical state `PROPOSED_NOT_AUTHORIZED` | Proposal interpretation only; actual execution requires the existing or separately approved domain transaction |
| `capability_qualification.schema.json` | UNKNOWN/PROPOSED_TEST/DOCUMENTED_NOT_TESTED/MOCK_ONLY; real-world eligibility false | Do not infer production qualification from schema validation or external docs |
| `delivery_receipt.schema.json` | Test relay/storage states; `is_real_dispatch: false` | Not a universal connector receipt and not proof of real emergency delivery |
| `contracts/README.md` | JSON Schema 2020-12 design examples with subset validator | A future maintained full validator plus semantic/authorization checks is required; no parser success becomes a security claim |

A synthetic v1 → internal lab mapping must be explicit and versioned. It preserves synthetic origin and inert flags. It must never manufacture a real grant, current sensor capture, production identity or observed execution from mock data.

## 2. Common envelope and invariants

Every runtime record has a versioned type, immutable record ID, `created_at_utc`, producer ID/version, correlation references and an owner/access scope. IDs are opaque, unique and non-authorizing. Reuse existing `event_id`, `incident_id`, conversation, task and action IDs whenever applicable; an ordinary daily request must not create an OUTSIDE_CHECK event. Do not collapse ASTRA's incident/action records into a universal new job database.

Proposed normalized times are timezone-aware RFC 3339 UTC strings. Human appointments additionally preserve the IANA timezone, original local time and ambiguity-resolution choice. Durations are nonnegative integer milliseconds. Source capture, receive, observation, validity and derivation times are different fields. Unknown capture is null with freshness UNKNOWN, not replaced by receive time. Use a trusted wall clock for cross-process deadlines and monotonic elapsed time with `boot_id` for in-process budgets. Monotonic values cannot be compared across hosts or reboot. Clock uncertainty is carried explicitly; an unresolved skew invalidates operations needing freshness.

Token counts are nonnegative integers with tokenizer/estimation method; media includes bytes, pixel dimensions, frame counts and audio milliseconds. Currency accounting uses integer micro-USD plus a rate revision; retain original invoice currency separately. Energy is measured Wh, or null plus `ESTIMATED`/`UNKNOWN`; never substitute zero for missing measurement. Spatial units/frames/calibrations remain H08-owned.

All enums reject unknown values at a trust boundary. Non-finite numbers, duplicate conflicting IDs, unresolved references, cross-user refs, oversized collections and expired objects are rejected. A content digest proves identity/integrity against known bytes, not truth, permission or freshness. `allowed_capabilities` in an untrusted/model-authored record can only narrow the trusted effective set, never widen it.

## 3. Exact proposed component contracts

### C01 — TrustedRequestContext v1 (H04 → coordinator/brokers)

**Required:** `request_id`, `principal_id`, `authenticated_session_ref`, `device_id`, `device_binding_revision`, `auth_strength`, `domain`, `purpose`, `conversation_id?`, `turn_id?`, `requested_audience_ids`, `received_at_utc`, `grant_refs[{grant_id,revision}]`, `policy_revision`, `trace_id`.

The authenticated transport/security service supplies these fields; user text and models do not. `principal_id` is the requester, not automatically the data subject. Tokens/credentials stay outside model context. An opaque reference must resolve at the intended broker; possessing its ID conveys no authority. Missing/expired identity returns `IDENTITY_UNKNOWN`/`AUTH_EXPIRED`; no anonymous fallback to household private data. H04 owns authentication and revocation semantics; R02 does not implement an identity provider.

### C02 — RetrieveContext / ContextPacket v2 (coordinator → context service → inference)

**Request:** trusted context reference, `job_id`, `task_class`, query or exact `source_refs`, domain/purpose, required freshness profile, permitted evidence kinds, `max_input_tokens`, `max_media_bytes`, `max_frames`, `deadline_at_utc`, cancellation reference.

**Result:** `packet_id`, `job_id`, `principal_id`, `subject_ids`, `audience_ids`, `owner_scope`, `purpose`, `grant_refs[{id,revision}]`, `policy_revision`, `source_refs[{evidence_id,revision,content_sha256}]`, bounded excerpts, `memory_refs[{id,revision}]`, `freshness_summary`, `unknowns`, `conflicts`, `omitted_refs_and_reasons`, `effective_capability_ids`, `tool_catalog_digest`, `cloud_eligibility`, `token_accounting`, `media_accounting`, `assembled_at_utc`, `expires_at_utc`, `content_sha256`, `cancel_epoch`.

`cloud_eligibility` identifies exact providers/endpoints and approved data classes/purposes; it is an evaluated restriction, not an access token. Egress re-resolves every grant. Cache key includes principal, audience, purpose, source revisions, grant revisions, policy and model/prompt/tool versions. No private semantic-result cache may be shared across principals. A newly revoked or corrected input makes the packet unusable. `STALE_CONTEXT`, `CONTEXT_OVERFLOW`, `SOURCE_UNAVAILABLE`, `AUTH_REVOKED` are explicit failures. Missing optional evidence may instead return a partial packet with declared omissions.

### C03 — EvidenceRef v2 / ClaimEvidenceBinding v1 (sources → evidence service → validators)

Retain v1 evidence fields. Proposed additions: `revision`, `source_uri_or_local_ref`, `source_type`, `subject_ids`, `published_at_utc?`, `retrieved_at_utc?`, `valid_from_utc?`, `valid_until_utc?`, `derived_at_utc?`, `time_uncertainty_ms?`, `freshness_profile_id`, `source_authenticity_status`, `transformation_chain`, `measurement_uncertainty`, `source_terms_ref`, `retention_policy_ref`, `consent_refs` and `supersedes_ref?`.

A claim binding includes `claim_id`, visible claim text, `claim_class`, supporting evidence refs and excerpt/frame locators, contradictory evidence refs, temporal scope, uncertainty category and validation result. A calibrated probability is optional and includes its calibration-set/version; a model's self-reported confidence is not evidence. A research source's URL is not itself proof of a claim; retain the permitted relevant excerpt and retrieval/version context. Unknown or redacted sources are not reconstructed from model memory.

Advisory R02 output never changes `qualified_for_physical_action` to true. A domain qualification is a separate result owned by that domain. An old photograph may be valid historical evidence but invalid evidence of present readiness.

### C04 — MemoryItem / MemoryChange / MemoryReceipt v1 (user-facing flow → memory service)

**Item:** `memory_id`, `revision`, `owner_principal_id`, `subject_ids`, `share_scope`, `purpose_ids`, `kind` (preference/project/episodic/derived), value or encrypted payload ref, source refs, `recorded_at_utc`, valid-time interval, uncertainty, retention rule, grant refs, `supersedes_refs`, tombstone status.

**Change:** `change_id`, authenticated requester context, operation (propose/create/correct/delete/share/unshare), target ID and expected revision, proposed value/ref, exact intended purposes/audience/providers, source refs and confirmation ref when required. **Receipt:** committed/rejected/pending status, new revision, actual commit time, invalidated derived refs, propagation status and remaining third-party/backup restrictions.

Explicit authorized user corrections may commit atomically after identity and target resolution; model-inferred additions remain proposals until the relevant policy allows them. No “remembered” statement without a committed receipt. Concurrent correction uses compare-and-swap, returning `REVISION_CONFLICT`. A model is not permitted to remove a tombstone or broaden sharing. Deletion propagation is auditable without retaining the deleted plaintext. Operational tasks/receipts are not overwritten as preferences.

### C05 — JobSpec / JobStatus v2 (sponsor → coordinator → bounded worker)

**Required specification:** `job_id`, `parent_job_id?`, `sponsor_principal_id`, `trusted_context_ref`, RA01–RA08 `runtime_role`, domain, purpose, input refs with revisions/hashes, `output_contract_id`, `effective_capability_ids`, `tool_catalog_digest`, grant/policy refs, `budget_reservation_ref`, priority class, `max_iterations`, `max_model_calls`, `max_tool_calls`, input/output/media limits, `created_at_utc`, `deadline_at_utc`, `elapsed_limit_ms`, checkpoint policy, `idempotency_key`, cancel reference and `resource_requirements`.

**Status:** state, state revision, `attempt_number`, worker/lease owner, fencing token, checkpoint refs, counters, usage refs, output refs, last error, `cancel_requested_at_utc?`, `cancel_epoch`, `outcome_scope` (analysis/digital/physical observation), and `outcome_certainty`.

Use the prose lifecycle: CREATED → ELIGIBLE → RUNNING → COMPLETED/FAILED/CANCELLED/OUTCOME_UNKNOWN, with WAITING_FOR_INPUT, WAITING_FOR_APPROVAL and SUSPENDED as bounded intermediate states. Waiting has an expiry; it does not imply forever-active compute. A completed research job does not mean an approved or executed mission. An unknown external outcome is reconciled by a separately identified read/reconciliation job; it is not resolved by replaying the write. State changes are transactional and append audit events.

Duplicate submission with identical immutable payload returns the same job; reuse with a different payload returns `IDEMPOTENCY_CONFLICT`. A crashed worker can re-run pure analysis from immutable input under a new lease, after rechecking grants/budget. It cannot automatically replay an external side effect. Child jobs inherit narrower permissions/deadline and explicit portions of the same reserved budget. Children are disabled in the first prototype.

### C06 — InferenceRequest / InferenceResult v1 (coordinator → model adapter)

**Request:** `inference_id`, job/packet refs and digests, `task_class`, registry route/model revision, response-contract ID, bounded text/media inputs, approved tool-proposal schemas, input/output/reasoning limits where supported, sampling/effort settings, deadline, cancellation token, usage-reservation ref, data-policy revision and `store_policy`.

**Result:** provider request ID, actual model ID/revision if exposed, route/runtime/template versions, normalized visible text and claim/action proposals, original usage categories, normalized cost/usage, finish reason, refusal/error, call timestamps, validation result, cancellation outcome and artifact refs. No SDK object is the domain contract. No hidden reasoning trace is required or stored. Observable decision reasons and evidence are sufficient.

The adapter cannot choose a new provider URL, add hosted tools, change principals or retrieve new private context. Missing schema/tool/media support returns `UNSUPPORTED_CAPABILITY`. Invalid output is rejected with a bounded repair decision by the coordinator. Cancellation acknowledgment is separate from confirmation that remote compute/billing stopped. Aliased cloud models without immutable revisions require drift detection and regression before continued qualification.

### C07 — ToolProposal / BrokerResult v1 (model → broker → domain)

**Proposal:** `proposal_id`, job/request refs, logical capability ID and version, bounded typed arguments, logical target account/resource IDs, exact payload hash, source/evidence refs, expected resource revision, requested effect class, idempotency key and expiry. It carries no reusable credential, arbitrary path, arbitrary SQL, raw flight command or raw printer instruction.

**Broker result:** rejected/proposed/accepted-for-processing/observed-success/observed-failure/OUTCOME_UNKNOWN, authoritative domain action ID, execution-identity reference for audit, receipt refs, observed state/time, precondition checks, retry/reconciliation instruction and safe user-visible reason. “Accepted” is not “completed.” H03 and the physical domain own exact approval and receipt contracts; their IDs/semantics are not replaced.

Initial synthetic/read-only capability catalog: `evidence.read`, `memory.search`, `capability.snapshot`, `research.read_approved_source`, `proposal.stage`, `job.status` and `job.cancel`. Memory mutations use C04, not arbitrary file tools. A later approved research fetch accepts a validated source reference; the fetcher enforces schemes/hosts, redirects, content size/type, private-network/metadata-address blocking and parser isolation. Read-only does not imply egress-free. No unrestricted `run`, `shell`, `browse_and_act` or generic `execute` tool is exposed.

### C08 — BudgetReservation / UsageSettlement v1 (coordinator ↔ ledger)

**Reservation:** ID, principal/job/parent refs, provider/project scope, price revision, currency, worst-case `reserved_micro_usd`, token/media/tool/energy caps, creation/expiry, approved allowance ref, reservation state and generation. Atomic admission checks available funds across all applicable limits. Parent and child totals cannot double-count or create new capacity.

**Settlement:** inference/tool IDs, actual usage categories, billed/estimated cost, `billing_status` (confirmed/estimated/unknown), uncertainty reserve, observed timestamps and reconciliation refs. Unknown remains reserved; a cancellation does not free it as if no charge occurred. A rate mismatch trips the circuit breaker, retains evidence and prevents additional spending. Caps include failures. Operations not passing through this ledger are outside its guarantee.

### C09 — Lease / CancellationNotice v1 (coordinator → workers/brokers)

Lease contains job/resource ID, owner, monotonically increasing fence, acquisition/expiry time, heartbeat interval, `boot_id`, and last checkpoint. A worker proves current ownership at every commit/publication boundary. Monotonic fences are stored durably; lease expiry is not permission for two executors to race.

Cancellation contains authenticated sponsor/operator context, target type/ID, reason, epoch and time. Target types are SPEECH_OUTPUT, REASONING_JOB, SCHEDULED_TASK and DOMAIN_RECOVERY_REQUEST; they are not interchangeable. Cancellation is idempotent. Receiving it stops new bounded work and suppresses late output; downstream physical recovery is governed by the domain. A stale child/fence cannot revive its parent. Persistent jobs require renewed eligibility after reboot; old physical permits do not resume.

### C10 — PublicationEnvelope v1 (validator → audience gate → UI)

Contains output ID, principal and intended audience/device bindings, job/turn refs, visible answer/summary or proposal ref, source citations, grant/source/policy revision vector, validation status, `output_kind`, expiry, cancellation epoch and publication outcome.

The gate performs a fresh authorization/lineage check immediately before output. For private content, do not stream raw model tokens before validation; stream neutral progress indicators instead. Sentence-level streaming can be a later independently tested optimization with per-chunk authorization and cancellation checks. Shared speakers get only explicitly shareable output. Revocation after release cannot erase a person's memory; record the release time honestly.

### C11 — ModelQualification / BenchmarkOutcome v1 (H02/H06 → registry)

Records candidate ID, artifact/runtime/prompt/tool digests, benchmark dataset/protocol hashes, task classes, data-policy compatibility, resource envelope, measured success/failure/abstention, latency/energy/cost distributions, known limitations, assessor identity, evidence refs, state and expiry/retest triggers. States distinguish DOCUMENTED_EXTERNAL, PROPOSED_TEST, TESTED_CANDIDATE, QUALIFIED_FOR_NAMED_TASK and RETIRED. These are proposed intelligence qualifications, not modifications to the frozen physical-qualification schema.

Only the authorized review path promotes a model. A framework/model cannot grade its own production eligibility. Changing quantization, runtime, prompt, tool catalog, retention behavior, price/alias or media preprocessing triggers the relevant regression subset; critical boundary changes require full qualification.

## 4. Error and retry policy

| Error family | Visible result | Permitted response |
|---|---|---|
| IDENTITY_UNKNOWN / AUTH_EXPIRED / AUTH_REVOKED / AUDIENCE_DENIED | Cannot access or publish for this identity | Reauthenticate or request a new valid grant; no model retry |
| SOURCE_UNAVAILABLE / FRESHNESS_UNKNOWN / STALE_CONTEXT | Evidence missing/old; answer limited | Permitted refresh or historical/partial answer with explicit limits |
| PRIVACY_ROUTE_DENIED | This data cannot use that route | Local qualified route or unavailable; no provider fallback without eligibility |
| CONTEXT_OVERFLOW / UNSUPPORTED_CAPABILITY | Request exceeds qualified input/feature limits | Reduce context transparently or select an eligible qualified route |
| INVALID_MODEL_OUTPUT / UNGROUNDED_CLAIM | No accepted result | At most one bounded repair or escalation within total cap |
| RATE_LIMITED / MODEL_UNAVAILABLE / DEADLINE_EXCEEDED | Delayed/unavailable, not successful | Bounded backoff or qualified fallback within deadline; preserve reservation |
| REVISION_CONFLICT / IDEMPOTENCY_CONFLICT / LEASE_LOST | Conflicting or obsolete work | Re-read and reconcile; fence stale result; never overwrite blindly |
| BUDGET_EXCEEDED / PRICE_UNVERIFIED | Paid work not admitted | Stop/return no-model path; no self-raised limit |
| OUTCOME_UNKNOWN | Action may have happened | Domain read/reconciliation; no blind write retry |

No silent catch-all coercion into success. Raw provider errors are redacted before publication. The audit retains enough cause and correlation metadata to reproduce the failure without exposing secrets.

## 5. Proposed H00 change requests

| ID | Affected shared contract/path | Required review |
|---|---|---|
| CR-R02-01 | `agent_job` runtime v2 and explicit v1 mock mapping | H00/H02/H04/H06 |
| CR-R02-02 | `context_packet` v2; C01/C04/C10 identity, memory and publication contracts | H00/H01/H02/H04/H07 |
| CR-R02-03 | `evidence` v2 provenance, validity and claim bindings | H00/H02/H05/H07/H08/H09/H12 |
| CR-R02-04 | Intelligence registry, inference/usage/budget/lease/cancel records | H00/H02/H03/H04/H06 |
| CR-R02-05 | Broker mappings to existing daily/physical/consent/receipt contracts | H00/H03/H04 plus relevant physical owner |

Proposed future changes to `contracts/registry.json`, `docs/04_INTELLIGENCE_AND_COST.md`, `docs/13_RUNTIME_AGENTS.md`, policies and acceptance catalogs occur only through H00's reviewed integration. No changes are applied in this handback. No current M0 route, schema, database, credential or M4 model is redirected through these proposed interfaces.
