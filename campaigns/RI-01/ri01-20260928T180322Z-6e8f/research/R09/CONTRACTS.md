# R09 proposed skill, evidence and command contracts

Namespace `ri01.proposed.r09.v1`; proposals only. No shared schemas, APIs or implementation are changed. All refs are immutable `(type,id,revision,sha256,canonicalization_version)`; opaque IDs confer no authority. Unsupported old/unknown profiles reject `UNSUPPORTED_PROFILE`. A physical path remains disabled in P0 even if a caller submits seemingly valid fields.

## C01 — EmbodimentProfile and QualificationProfile

H10 owns embodiment; H09 supplies measured fixture/material/enclosure evidence; H08/R07 and perception owners supply compatible spatial/evidence profiles. H00 owns domain grants and H06 independent acceptance. Profile binds robot/device pseudonym; simulated versus physical origin; controller, firmware, bridge/OS/library revisions; boot identity; motor/joint order and units; absolute/delta/velocity action meaning; joint zeros/ranges and sign; gripper opening/closing convention; kinematics; sensor/camera revisions and pixel transforms; hand-eye/extrinsic/intrinsic calibration; clocks; tool/end-effector and fixture/enclosure/material/process/assembly revisions; power; communication; stop/watchdog/takeover; exact tested environment and allowed task family.

QualificationProfile references independent evidence separately for payload mass/center of mass, retention, contact/force, workspace/footprint, speed/acceleration, stopping distance/time, stability, floor/slope/cliff coverage, latency/watchdog, calibration uncertainty, localization and recovery. Every required limit has numeric value/unit, measurement uncertainty, test method, domain and expiry/applicability; UNKNOWN rejects that physical claim. Numeric limits must be frozen before physical dispatch qualification, not invented from these reports. A source payload rating is DOCUMENTED, not a measured task envelope.

Invalidation is scoped but conservative: fixture reseat or enclosure/material/process change invalidates affected calibration/geometry/retention/measurement applicability; camera movement changes hand-eye; tool/payload changes alter dynamics and collision footprint; firmware/configuration/boot changes require declared revalidation. Old results remain immutable historical records and do not imply current eligibility. R08-P00 scalar repeatability can support only its one-axis quantity under its own exact fixture/calibration profile. It cannot fill six-axis covariance, force, contact, retention or sensor-effect evidence. Its E01 estimand/bootstrap/uncertainty gates remain before E01 protocol freeze; P0 cannot mark those physical gates passed.

## C02 — SkillSpec and task-qualified library

A library entry has skill/version/digest, owner, typed task objective, input/output schemas, candidate controller/policy artifact, exact compatible EmbodimentProfile set, environment and object class, qualification evidence, parameter ranges, required observation/action-space/calibration profile, required authority operation, resource ceiling, deadline, stop/recovery profile, success/failure/unknown oracle and invalidation dependencies. A policy checkpoint name is not a qualified skill.

Initial named proposals:

| Skill | Minimum conditions and distinct outcome |
|---|---|
| `inspect_fixed_view` | Eligible camera view and task-qualified recognition; observed evidence/answer, no carrier motion implied |
| `parked_telepresence` | Enrolled output audience, separate audio/video capture and playback permissions; call/stream state is not participant awareness |
| `point_fixed_light` | Only a separately qualified bounded actuator/template if movement needed; permitted illuminated area and energy/thermal conditions; observed light state |
| `carry_secured_inert_kit` | Qualified base, retained payload and traversable operating envelope; sealed tray/phone retention and actual delivery observation; not medical intervention or guaranteed help |
| `transfer_inert_object_between_trays` | Qualified bench/arm/gripper, contact/force and workspace limits, task-specific demonstrations; observed placement plus intervention/force/recovery records |

All physical entries are `RESEARCH_CANDIDATE`, not executable. Composition does not union their authority or qualifications: a carry-then-transfer mission needs each stage's current preconditions and the combined payload/arm stability profile. Failure terminates elective continuation and selects only the prequalified device-specific recovery. No generated arbitrary skill, trajectory or destination enters the dispatch surface.

## C03 — SkillEvidenceBundle

Preserve six layers rather than a prose state:

1. **Observation:** original source record, raw measurement/native unit, capture support interval, receive/process times, boot/clock mapping and uncertainty, source revision/hash, provenance and current CORE closure.
2. **Interpretation:** task-qualified detection/anonymous association or state estimate; model/preprocessing/calibration references, supported spatial interval/mask and uncertainty. Label scores are not pose covariance; current visual track is not identity.
3. **Intent:** typed skill and bounded parameters, expected task benefit and explicit unknowns; no dispatch.
4. **Dispatch:** independent domain-admission and actual transport record; send certainty and exact command/boot/config/lease identity.
5. **Outcome:** attributed device ACK plus independently observed task state with support/quality; ACK, inferred success and measured placement are distinct.
6. **Recovery:** request, ACK and observed recovered/unknown state, with retained physical exclusions.

R07 observation pairing preserves `p_parent=R*p_child+t`, normalized xyzw, parent-left SE(3) covariance `[tx,ty,tz,rx,ry,rz]` and m²/rad²/m·rad. Scale, frame/map/calibration and source support must match the consumer. Missing joint covariance cannot be replaced by confidence. Shared image/crop/caption and correlated estimates do not become independent witnesses.

Freshness checks use the source support interval and clock uncertainty plus bounded processing/transport/actuation delay, evaluated against the selected task/domain limit. A receipt timestamp does not refresh capture. No universal millisecond limit is supplied here. Track loss, occlusion, association ambiguity, stale frame/map/calibration or unknown qualified scale blocks any physical proposal needing those facts. An ordinary task answer may instead show a bounded unknown. Perception evidence can support a proposal but never supply physical authority or establish a safe route.

Corrections, tombstones, revoked grants and changed authenticity invalidate all influencing descendants, including uncited context, policy/model state and cached embeddings where applicable. Current authority applies to historical demonstration/replay; prior permission is not a current grant. Deletion-requested, inaccessible and verified-erased remain distinct. Retaining noncontent receipts/digests needs explicit audit purpose, access and retention policy; no blanket hash-retention exemption is introduced.

## C04 — SkillIntent, admission and resource ownership

SkillIntent binds proposal ID, exact SkillSpec/Embodiment/Qualification revisions, immutable parameters/digest, environment/object/task refs, complete evidence closure, requested operator/supervision, deadline, physical exclusion/region, recovery profile and worst-case resource estimate. State begins PROPOSED_NOT_AUTHORIZED. R07 NextObservationRequest is a sibling sensing request; a new viewpoint never bundles motion authority.

CORE I01's complete canonical AuthorityVector is referenced without dropping epochs, source/grant dependencies, principal/session/device, purpose/rights, job/lease/cancel, destination/audience/route, provider policy, dependency digest and canonicalization version. For motion, require a separate current sealed physical job and domain authorization under CORE I07, not an I06 publication permit. Permission to inspect, capture, speak, retain, publish or send a digital message grants none of the others.

Resource admission uses CORE I05's parent-backed reservation, not a new independent budget: compute/attempts/elapsed time, energy, actuation duration/cycles, payload and occupancy resources each typed with source units. Cancellation or unknown execution does not refund possibly used capacity. Financial reservation is not a physical safety envelope. One physical owner is enforced with device boot/config and monotonic fence; expired logical lease does not remove physical occupancy.

Only a deterministic allowlisted template adapter may accept a SkillIntent. The model cannot select raw endpoints, arbitrary ROS topics or servo instructions, rewrite limits, accept its own qualification or mint grants. At each new admitted action/chunk, recheck complete current authority, applicability, source freshness, remaining budget/deadline, ownership and physical exclusion. The implementation must define its authoritative ordering point; no database transaction can promise atomic remote physical motion. P0 represents the ordering and residual race honestly without creating a transport.

## C05 — Execution, acknowledgement and reconciliation

Use separate append-only proposed records: DomainAdmission, DispatchAttempt, DeviceAcknowledgement, PhysicalObservation and RecoveryObservation. Bind command/run/attempt, exact payload digest, robot/profile/boot, fencing lease and origin observation, admitted expiry, transport certainty and attributed event times. Device acceptance means the command was accepted, not completed. A command timeout is OUTCOME_UNKNOWN unless positive evidence proves it was never sent.

Duplicate intents with the same identity/digest reconcile; conflicting duplicates reject. An unknown external write is never retried as a fresh command. Buffered model chunks and reconnect queues are purged/denied after cancel, expiry, new boot, profile mismatch, authority change or lost observation applicability. Reconnection first performs read-only identity/current-state reconciliation. It must not replay saved velocities or automatically resume an unfinished grasp.

On planner/network freeze, local controller/watchdog uses its independently qualified device-specific recovery policy. On operator stop, record request and observed result independently. On total power failure, document the physical passive result; do not claim the software commanded recovery. For a gravity-loaded arm or held item, immediate torque-off can be inappropriate. UNKNOWN gripper/pose/contact leaves all conflicting work excluded. Human intervention is logged and may authorize a new separately bounded recovery only after current state assessment; it is not an invisible successful autonomous outcome.

CORE I06's ReleaseAuthorizationReceipt, ConsumptionPermitReceipt, DeliveryObservation and PermitEligibilityDecision remain orthogonal to these physical records. A dashboard can truthfully show unknown physical outcome even after a delivery ACK. A revoked dashboard output does not prove motion stopped. Unknown physical exclusion is cleared only by accepted observation/reconciliation evidence under the exact profile, never merely by elapsed time, process exit, lease expiration or deleted history.

## C06 — Error vocabulary and compatibility

Minimum structured errors: UNSUPPORTED_PROFILE, EMBODIMENT_MISMATCH, ACTION_SPACE_MISMATCH, CALIBRATION_INVALID, FRAME_REVISION_MISMATCH, SCALE_UNKNOWN, CLOCK_UNKNOWN, EVIDENCE_STALE, TRACK_LOST, ASSOCIATION_AMBIGUOUS, PHYSICAL_QUALIFICATION_UNKNOWN, AUTHORITY_CHANGED, RESOURCE_DENIED, OWNER_CONFLICT, DISPATCH_UNKNOWN, RECOVERY_UNKNOWN. Separate user-safe explanation from restricted source detail.

M0 remains unchanged. R09-P0 is an inert profile and cannot emit a physical sealed job. Future native/device/profile qualification is a new authorized package. No profile silently upgrades simulation evidence into observed physical measurements or generalized household skill.


