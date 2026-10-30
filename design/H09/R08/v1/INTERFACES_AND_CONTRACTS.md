# R08 — proposed interfaces and shared-contract changes

**DESIGN_PROPOSAL · No operational schema or adapter implemented · Revision 1**

## 1. Baseline conflict and migration rule

The source documents describe future engineering states that the deliberately inert v1 schemas cannot represent. That is a staging boundary, not permission to loosen validation.

| Existing file / v1 restriction | R08 consequence |
|---|---|
| `agent_job.schema.json`: only PROPOSED/MOCK_RUNNING/MOCK_COMPLETED/MOCK_FAILED/CANCELLED; physical execution and external network fixed false | A real CAD worker or physical controller needs an approved operational job mapping, not a flipped flag |
| `experiment.schema.json`: state PROPOSED_NOT_RUN; physical permission NOT_GRANTED | Keep original synthetic fixtures; introduce separately reviewed experiment observations and lifecycle |
| `design_artifact.schema.json`: qualification_state UNQUALIFIED; limited artifact kinds; additional properties forbidden | Add independent operational manifests for assemblies, process profiles and specimens; do not broaden v1 in place |
| `evidence.schema.json`: origin/claim/time/frame/calibration present; physical-action qualification fixed false | Measurement metadata is an extension proposal, not permission conveyed by an evidence record |
| `spatial_estimate.schema.json`: metres; limited estimate kinds; safe-route claims false | CAD coordinates cannot be blindly inserted; full pose/calibration needs an explicit H08 type/mapping |
| `physical_action_proposal.schema.json`: PROPOSED_NOT_AUTHORIZED; execution false | An inert proposal remains inert. A trusted domain controller must resolve a separate authorization transaction |
| `capability_qualification.schema.json`: UNKNOWN/PROPOSED_TEST/DOCUMENTED_NOT_TESTED/MOCK_ONLY; real-world eligibility false | Real qualification requires a new reviewed record and authorization policy, never a migrated true flag |
| `context_packet` / `consent_proposal` | Context is not a transferable grant; a proposal is not actual consent |
| `delivery_receipt` | Communication-only. No printer completion state is added here |

Suggested new type namespace: `haven.engineering.proposed.v0`. This is a documentation identifier, not a deployed API or a claim that a schema is registered. H00 must select the operational version and approve adapters. Preserve original URNs, examples and negative tests. Never infer real identity, consent, calibration or action eligibility from synthetic records. New validators must enforce cross-record semantics, not just JSON shape.

## 2. Common envelope and primitive types

Every mutating request carries `request_id:UUID`, `job_ref:RecordRef`, `campaign_ref:RecordRef`, `expected_revision:uint`, `idempotency_key:string`, `deadline_at:UTC timestamp`, `cancel_epoch:uint`, and `payload_digest:SHA256`. The server derives `authenticated_principal_id` from its authenticated channel; a client-provided name cannot override it. Record `actor_service_id`, `actor_role`, `sponsor_id`, `subject_ids[]`, `owner_scope`, `purpose`, `audience_ids[]`, and authoritative `grant_revision_refs[]` separately. The backend checks them; the model does not manufacture an effective identity or permission.

A `RecordRef` is `{type, id, revision, content_sha256}`. An `ArtifactRef` adds `{media_type, byte_length, storage_object_id}`; it does not permit an arbitrary host path or remote URL. The storage service resolves authorized content and verifies bytes. Foreign, missing, inaccessible and tampered references have distinct internal errors without exposing another user's private metadata.

Time fields are RFC3339 UTC with explicit offsets normalized to UTC. Capture/sample interval and ingestion time remain distinct. Duration uses seconds and a monotonic clock within a declared `clock_epoch`; record `clock_uncertainty_s` or UNKNOWN. A reboot invalidates process-relative deadlines and volatile physical leases. Historical measurements do not become false merely because they are old: acquisition-time calibration validity and current-use eligibility are separate checks.

Each action-bearing observation references a reviewed `freshness_policy_ref` defining `max_age_s`, `max_clock_uncertainty_s`, permitted origins and required machine boot/configuration identity. The trusted controller evaluates age and clock uncertainty at dispatch, not when the model first saw the observation. Missing policy, unresolved time or stale evidence yields UNKNOWN/ineligible and blocks the affected action. No universal telemetry lifetime is invented before the machine is selected.

Require finite numeric values, explicit units and dimensional compatibility. No NaN, infinity or magic sentinel zero. Unknown values are null with a reason/status, never a numeric substitute. Requested design dimensions use millimetres; canonical spatial positions use metres; angles use radians. Retain raw values/units as received and record conversions. CAD units never silently become map units.

## 3. Exact proposed records

### C01 — CampaignProtocol (H09 proposal; H06/H04 approval)

Required fields: `protocol_id`, `revision`, `requirement_refs[]`, `goal_statement`, `hypothesis`, `scope_of_use`, `risk_class`, `baseline_method`, `baseline_artifact_refs[]`, `independent_variables[]`, `fixed_constraints[]`, `outcome_metrics[]`, `measurement_plan_ref`, `analysis_plan_ref`, `holdout_policy_ref`, `inclusion_exclusion_rules`, `max_candidate_revisions`, `max_fabrication_attempts`, `max_measurement_events`, `no_progress_limit`, `hard_stop_conditions[]`, `budget_lease_ref`, `reviewer_principal_ids[]`, `protocol_sha256`, `status` and `created_at`.

Each independent variable has name, type, unit, allowed range or enumerated values and rationale. Each metric specifies formula/version, direction, threshold, uncertainty treatment and whether it is primary or a guard. `risk_class` initially allows only `PASSIVE_LOW_RISK_BENCH`; a different class requires an owner decision, not a model edit.

Status is `DRAFT | REVIEW_PENDING | LOCKED | CLOSED | SUPERSEDED`. LOCKED requires authenticated review of the exact hash. A change after observations exist creates a new protocol/campaign lineage; it cannot retroactively relabel a failed trial. The proposer cannot edit holdout membership, raw test data or the decision rubric. H06 controls protected evaluation access independently from RA05.

### C02 — CampaignBudget / ResourceLease (reuse H02, domain allocation only)

Required allocation: `budget_id`, `parent_job_budget_ref`, `currency`, `provider_spend_cap`, `reserved_spend`, `confirmed_spend`, `unknown_spend`, `cpu_time_s_cap`, `wall_time_s_cap`, `memory_bytes_cap`, `artifact_bytes_cap`, `model_call_cap`, `candidate_cap`, `print_attempt_cap`, `material_g_cap`, `estimated_machine_time_s_cap`, `operator_session_limit_s`, `expires_at`, `lease_epoch`, `logical_resource_ids[]`, `issuer_id` and `revision`.

Admission atomically reserves an attempt and its resource allowance before work starts. Failed candidates and failed prints still count. Unknown machine material/time use remains reserved or conservatively bounded, not reset to zero. Budget growth requires the original authorization path. Context-window limits and cloud eligibility come from H02/H04, not a second R08 model router. No model calls or purchases are authorized by this specification.

### C03 — DesignRevision / AssemblyBOM (CAD worker → H09 registry)

Required: `design_id`, `revision`, `campaign_ref`, `protocol_ref`, `parent_design_refs[]`, `author_service_id`, `authoring_mode` (REVIEWED_TEMPLATE or SANDBOXED_GENERATED_SOURCE), `template_ref`, `parameter_values[]`, `source_artifact_ref`, `toolchain_manifest_ref`, `constraint_report_ref`, `drawing_ref`, `geometry_export_refs[]`, `cad_frame_ref`, `assembly_bom_ref`, `estimated_properties[]`, `review_state`, `created_at`.

The toolchain manifest records actual software/kernel/runtime versions and artifact hashes, operating environment, export/tessellation options and reproducibility tolerances. A drawing defines datum features, critical dimensions, tolerances, interfaces, keep-outs and intended assembly. Estimates carry model/assumption/evidence references and uncertainty status; no estimated value is labeled measured.

Each BOM line has `line_id`, `part_id`, `revision`, `quantity`, `unit`, `make_or_buy`, `material_spec_ref`, `supplier_part_number` or null, `supplier_lot` or null, `license_or_usage_terms_ref` where applicable, `approved_substitutions[]`, `inspection_requirements[]`, and optional dated quote/currency. Assembly records orientation, fasteners and reviewed assembly procedure; no invented tightening torque. Substitution requires explicit review and may invalidate qualification. The system proposes a BOM; it never orders it.

Review state: `PROPOSED | GEOMETRY_CHECKED | ENGINEERING_REVIEWED | REJECTED`. None means fabricated, measured or qualified. Parent lineage must be acyclic and resolve to exact revisions.

### C04 — FabricationPlan / SealedJob (preparation worker → review/controller)

Required: `fabrication_job_id`, `revision`, `campaign_ref`, `design_ref`, `final_toolpath_ref`, `geometry_input_refs[]`, `slicer_project_ref`, `slicer_manifest_ref`, `resolved_process_profile_ref`, `logical_machine_id`, `machine_configuration_ref`, `firmware_ref`, `nozzle_profile_ref`, `material_spec_ref`, `material_lot_id`, `build_orientation`, `quantity`, `estimated_material_g`, `estimated_duration_s`, `approved_command_dialect_ref`, `resolved_macro_manifest_ref`, `preflight_requirements[]`, `inspection_plan_ref`, `supervision_policy_ref`, `budget_lease_ref`, `sealed_manifest_sha256`, `state`.

`state = PREPARED | REVIEW_PENDING | REVIEWED | SUPERSEDED | REJECTED`. REVIEWED is not a start grant. Everything affecting physical execution, including start/end sequences and printer-resident macros, must be resolved and bound to a known configuration. An unknown machine-dependent instruction blocks preparation. Editing a filename or remote file beneath an approved name must not change the sealed bytes. Geometry-only and slicer-project 3MF references remain distinct.

### C05 — FabricationGrant and DispatchReceipt (trusted authority/controller only)

The grant records `grant_id`, `issuer_principal_id`, `operator_principal_id`, `job_ref`, `sealed_manifest_sha256`, `logical_machine_id`, `machine_boot_epoch`, `machine_configuration_ref`, `allowed_operation` (initially STAGE or START_ONCE), `not_before`, `start_expires_at`, `maximum_attempts=1`, `supervision_session_ref`, `resource_lease_ref`, `revocation_revision`, `consumed_at` and authenticated integrity information controlled by H04.

A start grant is not transferable between machines, operators, profiles or job hashes. Approval to prepare/design is not approval to start. Check authority and consume the grant at the authoritative dispatch ordering point. Revocation before that point blocks dispatch; revocation after it invokes the reviewed in-progress handling policy. Do not promise instantaneous physical recall through a partitioned network.

The receipt records `attempt_id`, `job_ref`, `grant_ref`, `request_id`, `machine_boot_epoch`, `intent_committed_at`, `dispatch_started_at`, `api_response_received_at` or null, `device_observation_refs[]`, `reported_file_identity`, `outcome_state`, `error_code`, `stop_request_ref` or null, and `reconciliation_state`.

Outcomes: `NOT_DISPATCHED | DISPATCHING | COMMAND_ACCEPTED | DEVICE_REPORTED_RUNNING | DEVICE_REPORTED_COMPLETE | STOP_REQUESTED | DEVICE_REPORTED_STOPPED | DEVICE_REPORTED_FAILED | OUTCOME_UNKNOWN`. These are attributed device/control observations, not an engineering verdict. A declared completion yields only a fabrication-attempt record until a person or qualified measurement system identifies the actual specimen.

### C06 — Specimen and InspectionRecord (operator/inspection system → ledger)

A specimen records `specimen_id`, `design_ref`, `fabrication_attempt_ref`, `material_lot_id`, `physical_label`, `assembly_revision`, `custody_events[]` and `status`. Custody events identify who moved or modified it and when. Mixed-up or unidentifiable specimens are quarantined, not guessed from appearance.

Inspection records `inspection_id`, `specimen_ref`, `inspection_plan_ref`, `inspector_principal_id`, `instrument_refs[]`, `observations[]`, `critical_dimension_results[]`, `defect_refs[]`, `handling_state`, `result`, `observed_at` and `evidence_refs[]`. Result is `PASS_FOR_TEST | FAIL | INCONCLUSIVE`; it grants neither general use nor production acceptance. `handling_state` cannot become `COOLED_VERIFIED` from a completed-job message alone. Safe temperature criteria come from the reviewed material/device handling procedure, not this design document.

### C07 — MeasurementRecord / CalibrationRecord (metrology → evidence)

Required measurement fields: `measurement_id`, `campaign_ref`, `protocol_ref`, `specimen_ref`, `trial_id`, `trial_sequence`, `session_id`, `operator_principal_id` or null, `acquisition_service_id`, `origin`, `quantity_kind`, `raw_value`, `raw_unit`, `canonical_value`, `canonical_unit`, `sample_interval_start`, `sample_interval_end`, `received_at`, `clock_epoch`, `clock_uncertainty_s`, `instrument_ref`, `calibration_ref`, `frame_ref`, `reference_artifact_ref`, `environment_ref`, `uncertainty`, `quality_status`, `raw_evidence_refs[]`, `correction_of` or null, `exclusion_reason` or null.

Origin remains SIMULATED, PRERECORDED, MANUAL or LIVE_DEVICE. A manual instrument reading has MANUAL origin plus the named instrument/operator; it is not an unauthenticated model-generated number. The recorder validates identity, protocol membership and evidence before committing it.

`uncertainty` includes `kind`, `standard_uncertainty`, `expanded_uncertainty`, `coverage_factor`, `unit`, `method_ref`, `contributors[]`, and correlation information or UNKNOWN. `quality_status = VALID | SUSPECT | INVALID | MISSING | UNKNOWN`. Null uncertainty does not mean zero. Calibration records include method/reference/instrument revisions, validity interval, environmental envelope, last check and traceability status. An informal check against another ruler is not automatically traceable calibration.

For a later pose measurement, propose an H08-owned `PoseMeasurement`: `parent_frame_id`, `child_frame_id`, transform convention `p_parent = R_parent_child*p_child + t_parent_child`, `translation_m[3]`, `quaternion_xyzw[4]`, calibration revision and a covariance with explicitly stated small-error convention/order `[tx,ty,tz,rx,ry,rz]` in metres/radians. A CAD nominal transform is an ASSUMPTION/PREDICTION; an experimentally established transform is separately evidenced. Do not widen v1 `spatial_estimate` to silently add pose.

### C08 — AnalysisResult / AcceptanceDecision / QualificationEnvelope

Analysis requires `analysis_id`, `protocol_ref`, `analysis_code_ref`, `input_measurement_refs[]`, `excluded_measurement_refs[]` with reasons, `environment_ref`, `random_seed` if applicable, `computed_metrics[]`, `uncertainty_results`, `baseline_comparison`, `assumption_checks`, `limitations[]`, `status` and output artifact hashes. Deterministic calculation is authoritative for arithmetic; an RA06 narrative cites it but cannot change the numbers or exclusions.

Acceptance requires `decision_id`, `protocol_ref`, `design_ref`, `specimen_refs[]`, `inspection_refs[]`, `analysis_ref`, `reviewer_principal_id`, `reviewer_authority_ref`, `independence_declaration`, `conflict_disclosures[]`, `decision`, `reason_codes[]`, `decided_at` and `qualification_envelope_ref` or null. Decisions: `REJECT | REVISE | INCONCLUSIVE | STOP_NO_NEED | OPERATOR_REVIEWED | QUALIFIED_FOR_SCOPE`.

The qualification envelope binds exact design, physical specimens/batch sampling basis, assembly, material/lot, manufacturing process, relevant firmware/profile versions, permitted loads/use/environment, performance limits, uncertainty, inspection interval, calibration requirements and requalification triggers. Initially qualification can cover only the specific tested specimen and stated bench use. It cannot imply population-level manufacturing consistency, RF transparency, electrical safety or flight approval. The proposer cannot write this record; a hash alone is not an authenticated signature or competence assessment.

## 4. Typed operations and error/retry policy

| Operation | Caller → owner | Output / authority |
|---|---|---|
| `campaign.propose(protocol)` | RA05 → H09 | Draft ID; no locked status |
| `campaign.lock(protocol_ref)` | Authenticated reviewer → H06/H09 | Locked revision after approval checks |
| `cad.build(template_ref, parameters, limits)` | Admitted H02 job → isolated CAD worker | DesignRevision or typed failure; no machine access |
| `fabrication.prepare(design_ref, process_ref)` | H09 → isolated slicer worker | SealedJob proposal; no upload/start permission |
| `fabrication.stage(job_ref, grant_ref)` | Authorized domain caller → gateway | Staged-byte verification receipt only |
| `fabrication.start_once(job_ref, grant_ref)` | Present operator / trusted local UX → gateway | Attempt ID, never implicit retry/resume |
| `fabrication.observe(attempt_ref)` | Authorized reader → gateway | Attributed, timestamped observation; unknown stays unknown |
| `fabrication.request_stop(attempt_ref, reason)` | Authorized operator/policy → gateway | Stop-request receipt plus later observed outcome |
| `measurement.record(record)` | Authorized recorder → ledger | Immutable ID or rejection; corrections append |
| `analysis.run(protocol_ref, measurements)` | Admitted analyst job → vetted numerical worker | Versioned AnalysisResult |
| `acceptance.decide(decision)` | H06-authorized reviewer → acceptance store | Scoped decision or self-approval rejection |

Do not expose `shell`, `python_eval`, `raw_gcode`, arbitrary URLs, firmware writes, safety-limit setters or generic printer API forwarding to a model.

Required typed errors include `SCHEMA_UNSUPPORTED`, `UNKNOWN_FIELD`, `UNAUTHENTICATED`, `NOT_AUTHORIZED`, `CONSENT_REVOKED`, `REVISION_CONFLICT`, `HASH_MISMATCH`, `UNIT_MISMATCH`, `FRAME_UNRESOLVED`, `CALIBRATION_INVALID`, `MEASUREMENT_SUSPECT`, `IDENTITY_STALE`, `RESOURCE_BUSY`, `BUDGET_EXHAUSTED`, `DEADLINE_EXPIRED`, `CANCELLED`, `SELF_APPROVAL_DENIED`, `TOOLCHAIN_UNQUALIFIED`, `SUPERVISION_UNCONFIRMED` and `OUTCOME_UNKNOWN`.

Read-only operations may retry under a small bounded policy. A pure CAD/analysis recomputation may retry only with the same immutable inputs and a remaining budget; record a new attempt. For all mutating requests, an identical key and payload returns the stored result; a different payload under that key is a conflict. This ledger deduplication is not proof of exactly-once device execution. Unknown starts are never retried automatically. No new owner can take over a physical resource until its previous uncertain attempt is reconciled.

## 5. Five change requests and reviewers

| Change request | Proposed scope | Required review / disposition |
|---|---|---|
| CR-R08-01 | C01/C02: protected campaign plus allocation from H02 JobSpec; retain EX28 and N2 semantics | H00/H02/H04/H06/H09; PROPOSED |
| CR-R08-02 | C03/C06: inspectable source, assembly/BOM, physical specimen and inspection lineage | H00/H06/H09, H08 for reference frames; PROPOSED |
| CR-R08-03 | C07: measurement/uncertainty/calibration and explicit SI/frame adapter | H00/H04/H05/H06/H08/H09; PROPOSED |
| CR-R08-04 | C04/C05: sealed job, exact single-use grant, attempt/unknown reconciliation | H00/H04/H06/H09; H10 only for a later robot adapter; PROPOSED |
| CR-R08-05 | C08: independent decision, qualification envelope and invalidation | H00/H04/H06/H09 plus the intended-use owner; PROPOSED |

These specialize R02's proposed evidence, job and domain-mapping work; they do not replace CR-R02-01–05. Resolve shared identity/revocation/publication semantics with R03/H04. Not every future field must become mandatory in the first synthetic slice: select an approved minimal subset while keeping unimplemented types non-executable and blocked. H00 approval of a type does not itself authorize equipment, installs or model calls.