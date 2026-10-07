# R07 proposed contracts — documentation only

Namespace `ri01.proposed.r07.v1`. Not JSON schemas, deployed endpoints or executable authority. CORE `ri01.proposed.core.v1` I01–I07 and R06's paired sidecar remain controlling inputs. Unsupported profiles fail explicitly. Existing `urn:haven:draft:*:1` contracts remain inert and untouched. All records use opaque IDs, immutable revision/digest, canonicalization version, producer/profile identity and complete CORE source/authority dependency references. No arbitrary filesystem path, shell, SQL or URL executor is introduced.

## CR-R07-01: ObservationEnvelope and MapView

Producer: specialized perception or R06 adapter. Consumer: R07 admission/projection; MM-FUSION and R15 receive authorized views.

| Field | Proposed meaning and refusal rule |
|---|---|
| observation_id/revision/raw_digest/digest_kind | Distinguish raw-byte identity from canonical metadata digest; hash match is not authenticity |
| source_record_ref, parent_refs, transform_chain_refs | Full CORE I02 lineage, including preprocessing, calibration, model priors and uncited influencing sources; reject incomplete closure |
| modality, measurement_kind, origin, delivery_mode, path_context | Independent axes, preserving native modality and direct/obstructed/other-side/history support |
| geometry_encoding, payload_ref, support_mask_ref | R06 typed geometry, not an untyped list of triples. Explicit topology/grid axes/resolution/value meaning |
| frame_id, map_revision, semantics_id/hash/version | Mandatory exact SpatialSemantics pairing for R06 spatial estimates; UNSUPPORTED_PROFILE for legacy-only consumers |
| scale_state, unit, scale_evidence_ref | METRIC_QUALIFIED / RELATIVE / UNKNOWN; relative data may be displayed in separate nonmetric view but cannot become metres |
| source_clock_id/boot, tick/sample_interval, utc_mapping/uncertainty, received_at, processed_at | Preserve separate times. CLOCK_UNKNOWN blocks current synchronized claim, not authorized source-local replay |
| calibration_refs and validity profile | Exact calibration/device/fixture/domain revisions; CALIBRATION_INVALID on violated conditions |
| uncertainty union, score_kind/raw_score | UNKNOWN(reason), bounded regions, covariance with convention, or calibrated region. A class/depth score is never covariance |
| correlation_group_refs, dependence_edges | Common raw capture/features/calibration/prior/estimator; unknown dependence prevents independent-weight fusion |
| claim_class, support_class, status, freshness_policy | Observation/estimate/hypothesis/generated/replay classification, source support and current eligibility separate |
| access_snapshot_ref, authority_vector_ref, retention_refs | Full CORE dependencies; embedded IDs grant nothing |

MapView fields: view ID/profile; request principal/purpose/destination; source/map revision; valid-time and knowledge-time selection; authorized layer/cell/claim references; excluded/unknown/conflict regions and reason codes; complete influencing closure; current eligibility check time and expiry; output digest; `supports_safe_route_claim=false`. Omitted restricted geometry must not leave leaked object counts, thumbnails, labels, bounding boxes or derived summaries. Permission-aware omissions may need a generic unavailable indication rather than a disclosure of why.

Support state is OBSERVED_OCCUPIED / OBSERVED_FREE / OCCLUDED / UNOBSERVED / CONFLICT. An inferred occupancy probability lives beside support state, with method/uncertainty; it never erases unknown support. Raster resampling and grid-resolution changes record derivation and may not invent measured coverage. Downsampling preserves conservative unknown/conflict masking. Synthetic fixture coordinates are not calibrated physical measurements.

## CR-R07-02: FrameProfile, MapRevision and CorrelationRecord

FrameProfile resolves the exact R06 transform convention; parent/child, right-handed axis description, metric/relative status, origin/datum, device boot, validity, map revision and calibration refs. The active projection view chooses one nonambiguous acyclic transform path per frame; the evidence graph may retain competing paths separately. Alternative loop-closure estimates are evidence, not simultaneous inconsistent authoritative transforms.

Rigid transform inverse and composition must use the declared convention. Uncertainty propagation requires declared Jacobian/convention and correlation. If joint covariance is unavailable, P0 keeps separate outputs or an explicitly selected single estimate and marks FUSION_WITHHELD; it does not add inverse covariances. A six-number vector with no convention is UNSUPPORTED_PROFILE. Monocular scale alignment is separately typed and not accepted by an SE3-only consumer.

MapRevision: `revision_id`, `parent_revision_refs`, `event_sequence`, `builder_profile`, `input_closure_digest`, `transform/calibration_refs`, `valid_interval`, `built_at`, `knowledge_cutoff`, `layer_refs`, `conflict_refs`, `unknown_extent_ref`, `correction_of/supersedes`, `status`, `authority_dependencies`. Change transactions use expected-current-revision compare-and-swap; no last-writer-wins collapse of competing geometry. A restart must read committed revisions and reconcile unknown commit, not fabricate success or apply the same update twice.

CorrelationRecord: `group_id`, `relation_type` (SAME_CAPTURE, DERIVED_FROM, SHARED_CALIBRATION, SHARED_PRIOR, SAME_ESTIMATOR, CROSS_COVARIANCE_KNOWN, DEPENDENCE_UNKNOWN), exact member revisions, method/evidence, statistical model reference or UNKNOWN. Membership does not make estimates independent of other groups. Repeated video frames can also share temporal estimation error even without a common crop parent.

## CR-R07-03: NextObservationRequest and outcomes

Producer R07/MM-FUSION; consumers R06 fixed acquisition, H10/R09 carrier, H05/R10 carrier. Extend rather than duplicate R06 ObservationProposal/Outcome and CORE I04/I05/I07.

Request binds question/target ambiguity, immutable map/source revision, candidate catalog and exact candidate, allowed footprint/participant-area scope, proposed sensor/profile, required pose and independent carrier-motion proposal reference, expected gain method/unit or UNKNOWN, estimated compute/time/bytes/energy, reservation/lease/cancel scope, remaining episode deadline/attempts and complete access vector. State PROPOSED_NOT_AUTHORIZED. Catalog includes acquisition footprint plus motion requirement; crop bounds are not acquisition bounds. No arbitrary generated viewpoint is silently admitted.

Selector objective is original proposed design: choose among eligible finite candidates by declared expected uncertainty reduction minus weighted time/energy/storage burden, or STOP. Weights and gain estimator freeze before held-out evaluation. Unknown gain cannot be presented as calibrated benefit; a deterministic coverage heuristic is the P0 baseline. Viewpoint suggestions never access protected ground truth. Failures consume the attempt and elapsed budget; no renewed 60-second period for every selection.

Return separate analysis compute state (CORE I04), acquisition state (NOT_STARTED, ACQUIRING, STOP_REQUESTED, STOP_ACKNOWLEDGED, STOP_CONFIRMED, UNKNOWN), carrier domain outcome and publication records (CORE I06). STOP_CONFIRMED requires attributed independently observed cessation under the exact acquisition profile; acknowledgement, host sleep, lease loss, process-wrapper exit and blocked publication are insufficient. ObservationOutcome OBSERVED requires admitted source records. Cancelled eligibility does not erase previously admitted observations or imply their hardware stopped. Unknown dispatch/acquisition is read-only reconciled; never replay as an automatic new acquisition.

## CR-R07-04: replay, deletion and restoration

ReplayQuery includes selected valid time/interval, knowledge cutoff, requested map revision/layers, purpose, current principal/session/device/destination, and query budget. Historical authority snapshots are explanatory metadata only. Resolve current CORE I01 AuthorityVector, full equality/preconditions, operation/purpose, expiry/time uncertainty and complete closure at retrieval, context creation, egress, release and consumption. Offline private/shared replay cannot create a fresh release without current verification. I06 release/consume receipts stay immutable and are separate from delivery observations and current permit eligibility.

Tombstone immediately makes parent and all descendants ineligible. Materializations with unavailable reverse lineage are denied wholesale pending trusted recomputation. Per-copy deletion receipts cover raw/derived/context/rejected outputs, indexes/caches, exports/providers and backups; deny-now, deletion-requested, acknowledged and verified-erased remain distinct. New restore epoch starts review-only and reapplies trusted tombstones/revocations. No replay job or device lease revives automatically.

Actual R03 author advice (`/root/ri01_privacy`, root-routed CQ-R07-01): a noncontent deletion receipt or map-revision ID may remain only under an explicit audit purpose/access/retention policy with minimization; hashes/IDs are linkable and there is no blanket exception. Such receipts exclude deleted payload and record classes, local deny, request/ACK/confirmed states, backup expiry, provider unknowns and exceptions with authority/review/expiry/reconciliation. They do not retain retrievable deleted geometry. This advice agrees with CORE I02, not a new grant.

## Interface operations and errors

| Operation | Retry/expiry semantics |
|---|---|
| admit_observation(envelope) | Idempotent exact source/boot/sequence/revision/digest; same identity different digest rejects. No overlapping batch ambiguity |
| build_projection(exact refs, profile, expected revision) | Pure deterministic replay may retry once within original budget/deadline after fresh eligibility. Cache keys bind full revisions/profile and invalidation |
| query_map(replay query) | Fresh authorized bounded query; errors do not leak inaccessible parent details |
| propose_next_view(catalog, map, remaining budget) | No acquisition side effect; at most one proposal per decision revision; STOP on insufficient eligible gain or budget |
| invalidate_source(source revision, correction/tombstone) | Authorized idempotent revision event; deny boundary synchronous, materialization/erasure propagation separately tracked |
| read_outcome(attempt) | Read-only reconciliation, still scoped; absent record is UNKNOWN |

Typed errors reuse R06: SCHEMA_INVALID, UNSUPPORTED_PROFILE, HASH_MISMATCH, CLOCK_UNKNOWN, STALE, FRAME_UNRESOLVED, CALIBRATION_INVALID, SCOPE_DENIED, CONSENT_REVOKED, COVERAGE_UNQUALIFIED, INSUFFICIENT_OBSERVABILITY, OOD, RESOURCE_BUSY, BUDGET_EXHAUSTED, CANCELLED, OUTCOME_UNKNOWN. Proposed additions: SCALE_UNKNOWN, CORRELATION_UNMODELED, MAP_REVISION_CONFLICT, LINEAGE_INCOMPLETE, MATERIALIZATION_INVALID, DATUM_UNRESOLVED. These are proposals awaiting H00 canonicalization. Error detail is minimized; missing data is never converted to location zero, free space or no effect.

## Bounds and compatibility

P0: one in-process CPU replay, 32 sources, 16 grants, 128 lineage edges/depth16, 64KiB CORE metadata/256KiB output, at most 32×32 support cells per view, two synthetic principals, finite eight-view catalog. Raw references may point only to campaign-authored fixtures; no shell/remote loader. Exceeding bounds rejects rather than truncating closure. Episode total60seconds, maximum8attempts, 4GiB process memory ceiling as proposed outer budget. Later spatial arrays may exceed CORE's metadata limit only through separately authorized bounded references, never by silently lifting the access-closure bounds.

R08 scalar-only adapter retains raw mm and exact canonical metres, frame/axis/direction, reference uncertainty/calibration or UNKNOWN, fixture/enclosure/profile revisions and measured scope. UNKNOWN stays ineligible for metric promotion; full PoseMeasurement remains UNSUPPORTED_PROFILE until exact convention/target-range work is accepted. This respects REV-R08-M2/M3 and Q-R08-01; no universal manufacturing tolerance or sensor-effect claim follows.
