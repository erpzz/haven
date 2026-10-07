# R06 component and contract proposals

Version 1.0 · **PROPOSED_NOT_IMPLEMENTED** · H00 review required

This is an interface specification, not executable schemas or an authorization implementation. It preserves the starter's `urn:haven:draft:*:1` schemas unchanged. All R06 names below are proposed domain records under `urn:haven:r06:proposal:<name>:1`. H00 assigns canonical names only after R03/H04 and R07 review.

## 1. Findings in the actual starter

| Existing contract | Existing constraint / gap | Proposed disposition |
|---|---|---|
| `spatial_estimate.schema.json` | v1 has frame/map/calibration, point triples, untyped numeric uncertainty parameters, evidence/time. No availability, presence state, expiry, polygon topology, uncertainty coverage, clock bounds or grant dependencies. `supports_safe_route_claim` is fixed false. | Keep v1. Require a paired `SpatialSemantics` sidecar for R06 consumers; no lossy downcast for occupancy/semantics. Later v2 is an H00 change request. |
| `evidence.schema.json` | Claim class and capture origin are different axes; only one calibration/frame field, no acquisition geometry, payload locator or grant dependencies. Physical qualification fixed false. | Content hash can bind an R06 record in the scoped evidence store; retain raw/derived parents. Sidecar supplies additional semantics. Store resolves IDs; no user/model-selected file path. |
| `context_packet.schema.json` | `contains_real_private_data=false`; one grant revision is insufficient for multiple independent household subjects. | Synthetic context only with v1. Real RF summaries wait for R03/H04's reviewed grant dependency design; do not mislabel as synthetic. |
| `consent_proposal.schema.json` | `PROPOSED_NOT_GRANTED`; no production authenticated consent service exists here. | R06 references future grants but never converts this proposal to a grant. |
| `physical_action_proposal.schema.json` | Domain is FLIGHT/ROBOT/FABRICATION/RELAY; state proposed, execution false. No fixed-sensor acquisition domain. | Use `ObservationProposal` for acquisition intent. R07 coordinates a future sensing executor; carrier motion stays with its existing domain. No invented RELAY mapping. |
| `agent_job.schema.json` | Mock-only states, no actual lease/cancellation fields, network and physical execution false. | RA04 view proposals and RA06 analysis fit only mock/replay. Production lifecycle requires R02/H02 review, not a flipped boolean. |
| `experiment.schema.json` | State fixed `PROPOSED_NOT_RUN`, physical permission `NOT_GRANTED`. | Keep experiment cards inert. Execution results are separate future records; do not overwrite the experiment as PASS. |
| `capability_qualification.schema.json` | Only unknown/documented/mock states, real execution eligibility false. | External documentation can populate `DOCUMENTED_NOT_TESTED` later. Physical qualification needs a reviewed successor, separate from this report. |
| `design_artifact.schema.json` | Units mm/m permitted, qualification fixed `UNQUALIFIED`. | Fixture metrology and analysis refs can connect later; design completion is not fixture calibration. |

**Compatibility rule:** none of these records enters M0's SQLite database, request body, receipt protocol or incident state machine in this package. M0 accepted-source/request idempotency and expiry behavior remain authoritative for M0. R06 uses its own proposed IDs, lifecycles and storage.

## 2. Common types and invariants

`ID` is a nonempty opaque identifier (maximum 128 UTF-8 bytes); it is neither a URL nor an authentication token. `Digest` is SHA-256 of canonical metadata or exact artifact bytes, with the canonicalization version recorded. `Timestamp` is RFC3339 UTC with explicit precision; null is allowed only where stated. Numeric values are finite, with no NaN/Infinity. Metric units are m, s, Hz, rad, m/s, J and bytes; RSSI is dBm and SNR is dB. Raw scaled CSI values retain a declared scale rather than pretending to be volts.

All records have `schema_version=1`, `record_id:ID`, `record_revision:uint>=1`, `producer_id:ID`, `producer_version:string`, `created_at:Timestamp`, `experiment_id:ID|null`, `owner_scope` from the existing four-value enum, and `data_class` from `SYNTHETIC|PUBLIC_LICENSED_RESEARCH|PRIVATE_SPATIAL|EXPLICIT_SHARED_SPATIAL`. Public human datasets are not `RESEARCH_SYNTHETIC`: in an offline workspace use a separately reviewed owner binding, never lie to fit v1's scope vocabulary. This is CR-R06-02 below.

Common `AccessBinding`: `policy_revision:ID`, `region_scope_ids:ID[]`, `subject_scope_ids:ID[]`, `grant_dependencies:[{grant_id:ID,revision:uint,revocation_epoch:uint}]`, `purpose:string`, `recipient_scope_ids:ID[]`, `provider_scope_ids:ID[]`, `retain_until:Timestamp`. Synthetic fixtures may use empty grants/subjects with a synthetic-policy marker. Anonymous sensing uses an approved **session participant/area scope**, not an inferred person identifier. A future authenticated policy service resolves these values; their presence in JSON grants nothing.

Each derived record depends on the grants and retention of all contributing inputs. Effective access is the intersection of allowed purposes/audiences/providers; no union that widens sharing. Materialization, retrieval, inference routing and publication recheck those dependencies. Deleted or revoked parents invalidate descendants unless a separately reviewed, nonreconstructive aggregate policy applies.

## 3. `RFObservationBatch` — adapter → admission / evidence

| Required field | Type and exact meaning |
|---|---|
| `session_id`, `logical_sensor_id`, `acquisition_profile_revision`, `hardware_revision`, `firmware_revision` | IDs/strings resolved against an enrolled device and approved profile |
| `boot_id`, `sequence_first`, `sequence_last`, `sample_count` | ID and uints; sequence scoped to device + boot + session; count matches payload shape |
| `measurement_kind` | `RSSI|WIFI_CSI|COOPERATIVE_RANGE|RADAR_IQ|RADAR_DETECTIONS` |
| `origin` | Existing `SIMULATED|PRERECORDED|MANUAL|LIVE_DEVICE`; replay never changes capture origin |
| `delivery_mode` | `OFFLINE_REPLAY|LIVE_STREAM|MANUAL_IMPORT`; capture origin and present delivery mode are separate. Replay cannot create a live observation. |
| `path_context` | `DIRECT_VIEW|THROUGH_OBSTRUCTION|AROUND_OBSTRUCTION|OTHER_SIDE_SENSOR|UNKNOWN|MIXED`; factual geometry basis in `path_evidence_ids` |
| `path_evidence_ids`, `calibration_ids`, `pose_record_ids` | ID arrays; missing dependencies allowed for ingestion only, not unsupported spatial claims |
| `capture_clock_id`, `capture_tick_start_ns`, `capture_tick_end_ns` | ID + uint64 monotonic ticks in the source clock; serialized as decimal strings if consumer integer precision is insufficient |
| `capture_utc_start`, `capture_utc_end`, `clock_mapping_id`, `clock_uncertainty_s` | Nullable UTC timestamps/ID/nonnegative seconds; unknown mapping forbids `CURRENT` or time-critical fusion |
| `received_at`, `ingest_at` | UTC receipt/admission times; do not replace capture time |
| `frame_id` | ID or null; scalar link evidence may lack a spatial frame and must then remain nonspatial |
| `tx_ids`, `rx_ids` | Opaque enrolled endpoint IDs; no raw MACs, SSIDs or addresses in ordinary context |
| `center_frequency_hz`, `usable_bandwidth_hz`, `sample_rate_hz` | Positive number or null if not applicable/unknown; mandatory known for algorithms that use them |
| `antenna_geometry_revision`, `waveform_profile_id`, `phase_reference_id` | Nullable IDs; coherent fusion requires a valid phase reference, not merely matched timestamps |
| `payload_ref`, `payload_sha256`, `payload_format`, `payload_shape`, `payload_units` | Opaque artifact ID, digest, allowlisted encoding, uint dimensions and unit descriptors |
| `quality_state`, `quality_reasons` | `VALID|DEGRADED|INVALID|UNKNOWN` plus enum reasons; decoder/vendor score is separate from calibrated certainty |
| `expected_samples`, `missing_samples`, `saturation_count` | Nullable uints; report denominator unknown instead of fabricated zero loss |
| `access` | Common AccessBinding |

Discriminated measurement descriptors:

- `RSSI`: pairs `(sample_tick, link_id, rssi_dbm)`; log calibration and whether source is per-packet or averaged. Never substitute signal percent for dBm.
- `WIFI_CSI`: complex tensor axis labels `sample,rx,tx_or_stream,ltf,subcarrier`; explicit subcarrier indices, complex ordering, dtype, scale, valid-index mask, packet mode/bandwidth, gain metadata when exposed. Record oscillator/phase-sanitization method and preserve the unsanitized scoped artifact if retained. Invalid leading bytes must not become valid features. [R06-S03]
- `COOPERATIVE_RANGE`: `peer_id`, `range_m|null`, `range_stddev_m|null`, `direction_unit_vector|null`, native measurement status, measurement tick, `range_method=TWR|TDOA|FTM|NI|OTHER_DECLARED`, `nlos_state=DETECTED|NOT_DETECTED|UNKNOWN`. A failed range carries no numeric distance. Vendor standard deviation is repeatability evidence, not guaranteed NLOS accuracy.
- `RADAR_IQ`: dimensions for frame/chirp/RX/ADC samples; sample rate, chirp slope Hz/s, chirp interval s, carrier Hz, TX schedule, antenna/phase calibration. The estimator requires the complete qualified profile, not a chat-specified waveform.
- `RADAR_DETECTIONS`: per-return range m, azimuth/elevation rad if available, radial velocity m/s if available, SNR dB if supplied, covariance or unknown, sensor-frame points and firmware processing revision. Point clouds are already processed data; retain the firmware's static-clutter filtering state.

Proposed bounds: at most 1 MiB inline metadata, 16 MiB per raw chunk, and a 256 MiB adapter spool. These are initial configurable ceilings requiring resource review. Overflow drops or stops according to the experiment profile and emits explicit loss; it does not block receipt services. Raw files remain opaque typed arrays with checksums; no pickle or embedded executable content.

## 4. `FrameTransform` and `CalibrationRecord`

`FrameTransform` fields: `parent_frame_id`, `child_frame_id`, `map_revision`, `calibration_id`, `valid_from`, `valid_until`, `translation_m:[3]`, `quaternion_xyzw:[4]`, `uncertainty_kind=UNKNOWN|SE3_COVARIANCE`, `covariance_6x6_row_major:number[36]|null`, `source_evidence_ids:ID[]`, `access`. The transform is `p_parent = R_parent_child * p_child + t_parent_child`.

Convention: small left perturbation expressed in the parent frame, error order `[tx,ty,tz,rx,ry,rz]`. Covariance blocks use m², rad² and mixed m·rad. Validate normalized quaternion, symmetry and positive semidefiniteness within documented tolerance. Unknown uncertainty uses null, not zeros. Composition must track correlated parents; if correlation is unknown, use a conservative method or decline the confident fusion.

`CalibrationRecord` fields: `calibration_id`, `kind=RADIO|ANTENNA_DELAY|EXTRINSIC|CLOCK|ENVIRONMENT_BASELINE|UNCERTAINTY_MODEL`, `applies_to_device_ids`, `profile_revision`, `fixture_revision`, `method_version`, `reference_artifact_ids`, `reference_uncertainty`, `fit_metrics`, `valid_from`, `valid_until`, `invalidation_conditions`, `review_state=UNREVIEWED|REVIEWED_FOR_REPLAY|REQUIRES_REQUALIFICATION`, `reviewer_ref`, `access`. No record in this design asserts physical calibration passed.

Clock calibration additionally maps source ticks to UTC with boot ID, drift model and error bound. Statistical calibration additionally records target coverage, calibration split digest, population/domain, sample count and empirical coverage. TTL alone does not keep calibration valid after an anchor moves.

## 5. `SpatialSemantics` — RF estimator → R07 projection

This sidecar pairs one-to-one with `spatial_estimate:1` using `estimate_id` and `estimate_sha256`. A consumer must resolve and validate **both**. It may not display the legacy record alone as a current operational RF claim.

| Field | Type / obligation |
|---|---|
| `estimate_id`, `estimate_sha256`, `map_revision`, `frame_id` | Must match the paired estimate and its canonical bytes |
| `status` | `VALID|DEGRADED|UNKNOWN|STALE|CONFLICT|REVOKED`; retain reason codes |
| `presence_state` | `MOTION_CANDIDATE|NO_MOTION_OBSERVED|PRESENCE_CANDIDATE|ASSESSED_ABSENCE|UNKNOWN|NOT_APPLICABLE`; first CSI baseline cannot emit `ASSESSED_ABSENCE` |
| `target_kind`, `target_ref` | `ANONYMOUS_SOURCE|ENROLLED_DEVICE|CONTROLLED_OBJECT|REGION`, nullable reference; no RF person recognition |
| `support_class` | `MEASUREMENT_SUPPORTED_ESTIMATE|PRIOR_DOMINATED|MIXED_INFERENCE|SEMANTIC_HYPOTHESIS` |
| `path_context`, `parent_observation_ids` | Same path vocabulary as input; mixed origins retain each parent mapping |
| `geometry_encoding`, `geometry_ref`, `support_mask_ref` | Typed geometry reference and support mask; null only when no geometry is claimed |
| `uncertainty` | Tagged union defined below; not a generic class score |
| `computed_at`, `valid_until`, `capture_interval`, `clock_uncertainty_s` | Capture interval matches evidence; `valid_until` is a use deadline, not a claim static geometry ceased to exist |
| `calibration_ids`, `transform_ids`, `method_version`, `model_digest`, `qualification_ref` | Reproducible dependencies; optional model digest when no learned model used |
| `coverage_region_ref`, `unobserved_region_ref`, `conflict_refs` | Explicit measured/unknown extent and competing evidence |
| `access` | Effective grant/retention dependencies |

Geometry encodings are `POINT3`, `AABB3`, `POLYGON_XY_WITH_Z_BOUNDS`, `EDGE_SET3`, `VOXEL_GRID`, or `HYPOTHESIS_REGION_SET`. `POINT3` is one metric point. `AABB3` stores lower and upper triples. Polygons declare vertices, ring boundaries and holes; z bounds are explicit. Edge sets contain endpoint-index pairs, not an unordered point list. Voxel grids declare origin, axis directions, cell size, integer dimensions, per-cell value meaning and an observed mask: unknown cells never default to probability zero. Disjoint hypothesis regions have separate weights or an unknown-weight marker.

Uncertainty tagged union:

- `UNKNOWN`: no numeric parameters or nominal coverage; reason required.
- `BOUNDS`: explicit bounded regions and whether they are physical limits or statistical intervals; no implicit coverage claim.
- `COVARIANCE3`: symmetric PSD 3×3 row-major matrix in m², reference mean, estimated distribution assumptions, calibration ref. Do not use for unresolved multiple modes.
- `CALIBRATED_REGION`: explicit region refs, nominal coverage (0,1), empirical coverage plus interval, calibration set digest/count/domain, and region area/volume. Out-of-domain use downgrades status and removes the calibrated coverage claim.

For initial v1 pairing, only a documented one-point/edge representation with compatible units may mirror geometry into legacy triples. Use `uncertainty_kind=UNKNOWN` and an empty parameters array unless a reviewed v1 encoding convention exists. Rich semantics live in the sidecar; older consumers must reject an unsupported sidecar requirement. A future v2 would unify these fields under CR-R06-01.

An unavailable observation produces an explicit sidecar state with no asserted location. If a legacy-only caller cannot represent that state, return a typed unavailable result instead of fabricating an estimate at `[0,0,0]`.

Enforce pairing at the new projection boundary: return an envelope `{required_semantics_version:1, estimate_ref, semantics_ref}` only to consumers advertising that version; otherwise return `UNSUPPORTED_PROFILE`. Never publish the legacy record alone on an existing operational channel. A legacy-shaped copy is an archival compatibility artifact, not a downgrade path. In particular, unchanged old consumers cannot be assumed to discover or enforce a sidecar they do not understand.

## 6. `ObservationProposal` and `ObservationOutcome`

`ObservationProposal` fields: `proposal_id`, `principal_id`, `question_id`, `input_estimate_ids`, `candidate_catalog_id`, `candidate_id`, `logical_sensor_id`, `acquisition_profile_revision`, `target_pose_ref|null`, `carrier_motion_proposal_ref|null`, `permitted_region_ids`, `expected_information_gain|null`, `gain_method_version|null`, `gain_units|null`, `estimated_duration_s`, `estimated_energy_j|null`, `maximum_bytes`, `requested_samples`, `budget_reservation_ref|null`, `resource_lease_ref|null`, `expires_at`, `cancel_scope_id`, `access`, `state=PROPOSED_NOT_AUTHORIZED`.

A catalog entry is immutable and includes both acquisition footprint and needed motion; an approved observation does not implicitly authorize the movement required to reach it. H04's future authorization service binds the exact proposal digest, hardware/profile, area, people/session scope, action count and expiry. One exclusive acquisition owner per sensor; no second worker takes over an unresolved session.

`ObservationOutcome` fields: `proposal_id`, `attempt_id`, `executor_id`, `authorization_ref|null`, `started_at|null`, `ended_at|null`, `state=DENIED|EXPIRED|CANCELLED|ACKNOWLEDGED|OBSERVED|FAILED|OUTCOME_UNKNOWN`, `observation_ids`, `motion_receipt_ref|null`, `actual_duration_s|null`, `actual_energy_j|null`, `actual_bytes`, `error_code|null`, `reason`, `access`. `OBSERVED` requires admitted observations; an acknowledgement or model answer cannot satisfy it. This is a proposed successor result type, not a modification to the starter experiment record.

## 7. Narrow operations and lifecycle

The first implementation should be in-process/offline typed calls, not public HTTP endpoints. Future transport authentication is a separate integration decision.

| Operation | Request → response | Retry / cancellation |
|---|---|---|
| `admit_batch` | RFObservationBatch → evidence ID or RFError | Idempotent on sensor+boot+session+sequence range+digest. Same key/different digest rejects. Overlap rejected unless exact duplicate already admitted. |
| `estimate_from_refs` | input IDs + method/config digest + map revision → estimate/sidecar refs | Pure recomputation may retry once within lease; same immutable inputs define cache key; recheck grants before publish. |
| `propose_next_observation` | scoped estimate IDs + catalog + remaining budget → proposal or STOP | At most one accepted proposal per decision revision; no acquisition side effect. |
| `cancel_scope` | authenticated cancellation scope → acknowledgement/status | Idempotent. Cancels analysis/collection eligibility; carrier recovery remains a separate domain procedure. |
| `get_observation_outcome` | attempt ID → outcome | Read-only reconciliation; permission still required. Missing record is not proof no effect occurred. |

Proposed replay defaults: motion window 2 s, maximum observation age 5 s, track prediction horizon at most 1 s; all tuned only on validation data. Missing trustworthy capture time prevents a current claim. Offline replay is evaluated against an explicitly simulated clock and can never publish a current real-world claim, even when the original capture origin was LIVE_DEVICE. Geometry is “as of” a capture interval with a map revision, never refreshed by a new unrelated RF packet. Fusion admits only intervals/clock bounds/pose errors within the selected task's predeclared tolerance.

Analysis job limits: one concurrent CPU job, at most 4 GiB RAM, 60 s per decision, 8 selections per episode, $0 hosted spend. If exhausted, return `BUDGET_EXHAUSTED` and retain the incomplete result. These initial caps are proposals for replay, not guaranteed host performance. Live acquisition lease/heartbeat timing must be separately qualified; host sleep or lost authorization channel expires collection eligibility.

`RFError` is `{code,request_id,retry_class,dependency_refs,occurred_at,detail_code}`. Enumerated codes: `SCHEMA_INVALID`, `UNSUPPORTED_PROFILE`, `SOURCE_UNTRUSTED`, `HASH_MISMATCH`, `SEQUENCE_CONFLICT`, `CLOCK_UNKNOWN`, `STALE`, `FRAME_UNRESOLVED`, `CALIBRATION_INVALID`, `SCOPE_DENIED`, `CONSENT_REVOKED`, `COVERAGE_UNQUALIFIED`, `INSUFFICIENT_OBSERVABILITY`, `OOD`, `RESOURCE_BUSY`, `BUDGET_EXHAUSTED`, `CANCELLED`, `ADAPTER_UNAVAILABLE`, `OUTCOME_UNKNOWN`. `retry_class` is `NEVER|READ_ONLY_RECONCILE|SAFE_COMPUTE_ONCE|OPERATOR_REVIEW`. Error text contains no private raw samples.

## 8. Shared change requests

| ID | Requested review | Owners / gate |
|---|---|---|
| CR-R06-01 | SpatialEstimate semantics/sidecar requirement, topology and uncertainty; eventual v2 migration and old-consumer rejection | H00 + R07/H08 + H06; before P0 contract freeze |
| CR-R06-02 | Real/private and public-licensed-research owner bindings, multi-subject grant dependencies, footprint consent and deletion lineage | R03/H04 + H00; synthetic-only P0 can proceed without live grants |
| CR-R06-03 | Fixed observation authority/catalog and outcome records; no accidental motion authorization | R07/H08 + H04 + H05/H10; before any live adapter |
| CR-R06-04 | Production analysis job lease/cancel/quota and model qualification references | R02/H02 + H00; mock/offline first |
| CR-R06-05 | Qualification/result successors that retain inert v1 examples, reviewer identity and legal configuration scope | R13/H06 + H00; before real capability promotion |

No shared schema file, root document, active application path, M0/M4 pin, or consent record is changed by this handback.
