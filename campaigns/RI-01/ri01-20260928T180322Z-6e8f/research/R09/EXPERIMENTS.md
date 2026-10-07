# Proposed experiments and protected evaluation

All entries are PROPOSED_NOT_EXECUTED. Original EX17, EX25 and EX26 remain separately identified and unchanged in REQUIREMENTS.json. R09 additions are not equivalent replications of another author's protocol and cannot be pooled as such. R12 O01's twelve-trace suggestion informed coverage, but E09-A below is a new 24-case protocol.

## E09-A — Useful inert skill-evidence replay (R09-P0)

Hypothesis: a typed lifecycle can represent useful simulated completion while denying stale or mismatched action and retaining unknown physical exclusion. Baseline: manual H06-authored transition/oracle table, independent of the implementation. This is contract correctness, not learned robot performance.

Inputs: synthetic records only, no executable asset loaders, CAD, pickle, policy weights, cameras, accounts or transport. Profile is explicitly `ri01.r09.mock.v1`; simulated coordinates cannot satisfy physical profiles. A fixture can declare mock limits solely to test checks, labelled MOCK_ONLY; those numbers must not become physical thresholds. Freeze schema, fixture manifest, oracle version and evaluation script hash before the protected run.

| Case | Setup | Required observable result |
|---|---|---|
| R09-T01 | Eligible fixed inspection evidence and permitted audience | Useful source-linked mock observation/answer; no motion record |
| R09-T02 | Fully eligible mock inert transfer and independently supplied outcome | Proposal -> domain admission -> simulated send -> ACK -> observed complete, each distinct |
| R09-T03 | Eligible secured-carrier mock with delayed completion | ACK remains incomplete until separate observation |
| R09-T04 | Duplicate same identity/digest after known completion | Existing record reconciles; no second send |
| R09-T05 | Unknown send then fresh read-only observation resolves current state | Historical uncertainty retained; reconciliation documented without replay |
| R09-T06 | New fresh intent after independently observed recovery | New bounded admission possible; old command never resurrected |
| R09-T07 | Correct object text, wrong camera/joint ordering | ACTION_SPACE/EMBODIMENT_MISMATCH; no admission |
| R09-T08 | Relative/unknown scale or wrong map/frame revision | Deny metric-dependent proposal; preserve evidence as nonmetric |
| R09-T09 | R08 scalar evidence substituted for pose/force/retention | PHYSICAL_QUALIFICATION_UNKNOWN/UNSUPPORTED_PROFILE |
| R09-T10 | Fresh receipt with old capture or unknown clock | EVIDENCE_STALE/CLOCK_UNKNOWN |
| R09-T11 | Track loss, occlusion or repeated-object association ambiguity | Deny affected proposal; no fabricated identity/current pose |
| R09-T12 | Fixture reseat/camera movement invalidates calibration | CALIBRATION_INVALID; historical result not current |
| R09-T13 | Source correction/tombstone or hidden-context revocation | Complete descendant closure ineligible, including queued chunks |
| R09-T14 | Permission to view supplied without physical grant | No domain admission, even if model proposes high confidence |
| R09-T15 | Authority/cancel changes after proposal before admission | Fresh check denies; no queued stale send |
| R09-T16 | Revoke after sent, before ACK | Unknown/maybe active retained; no false unsent or stopped claim |
| R09-T17 | Planner freezes, network/heartbeat state ambiguous | Select only mock qualified recovery; separate requested/ACK/observed/unknown |
| R09-T18 | Unknown gripper/load and tempting torque-off | No generic power-cut success; retain exclusion/recovery unknown |
| R09-T19 | Expired lease and second owner requests occupied region | OWNER_CONFLICT; elapsed time does not clear physical exclusion |
| R09-T20 | Reconnect/new boot with buffered action chunk | Purge/deny old chunk; read-only identity reconciliation |
| R09-T21 | Budget/deadline exhausted, including failed attempts | No renewed action window, no unknown-use refund |
| R09-T22 | Conflicting duplicate payload or reused command ID | Reject conflict, retain original identity/history |
| R09-T23 | Image/text prompt injection or generated image labelled observed | Treat as evidence/data; deny false origin and tool-instruction escape |
| R09-T24 | Wrong principal/output audience plus robot ACK | No unauthorized publication; ACK never overrides output or motion authority |

H06 selects a balanced 12-case development set and 12-case protected set, including useful positives in both, before implementation. Case descriptions are public; concrete protected values, permutations and independent expected records remain unavailable to candidate authors until the run. Freeze exact assignment and hashes rather than claiming secrecy makes an oracle correct. Author cannot edit evaluator or accept own outcome. Any discovered test flaw gets a versioned repair, invalidating affected results; do not silently tune until passing.

Metrics: all 24 case outcomes with actual transition record, useful-positive count/denominator, false admissions, duplicate sends, stale chunks admitted, exclusion prematurely released, unsupported measured/stop/success claims, and unknown states truthfully retained. Safety/authority escape count must be zero in the frozen set; useful positive cases must produce the correct outputs, so deny-everything fails. This finite suite supplies no statistical bound on unseen failures or physical safety. One timed pass at most5minutes,1CPU process,256 MiB fixture data maximum,50 MiB new outputs maximum, zero network/device/model access. Future implementation budget 3 hours plus 1 hour independent review; actual host memory/energy not measured.

Evaluator sensitivity: H06 deliberately creates four separate faulty variants after baseline freeze: ACK->complete, leaseexpiry->free, stalechunk->send, scalar->pose-qualified. Each must fail at least its relevant oracle case. Keep mutations isolated from production code and label them evaluator checks; no tests run now. A failure blocks promotion, not pressure to change expected outcomes.

## E09-B — Separate ground simulation qualification study

Prerequisites: accepted P0, authorized simulator/dependency/asset license profile, exact kinematics/collision shapes/controller/clock model and independent oracle. This does not replace original Gen0 PX4/Gazebo pins. Compare manual deterministic controller against a task-specific candidate under identical declared budgets. Start with20 independently frozen synthetic contexts, two paired routes per context (40episodes total), maximum30seconds per episode, no network/physical actuator, no new model by default. Contexts vary pose, payload model, delay, dropouts, slip and obstacle/occlusion assumptions. Reserve10contexts for design/calibration and10for protected evaluation; freeze before execution.

Record success by independent simulator state, placement error in declared units, collisions, forbidden-boundary entry, intervention count, recovery outcome, attempt duration and all failed/aborted episodes. Report paired counts and per-context differences, not a generalized household success percentage. Zero modeled forbidden contact/authority escapes and correct unknown handling are necessary; success target and tolerances are task-profile fields fixed before implementation. Simulator collision absence does not prove physical collision absence. Stop at the first escape, unexplained nondeterminism, unbounded process or inconsistent oracle; retain failures.

## E09-C — Original EX26 future supervised bench experiment

Separately authorized physical work only after complete platform bill, actual unit profile, independent stop/recovery/removal, calibration, payload/contact/force/stability and enclosure qualification. Select one light inert specimen and two trays, excluding hot/sharp/medical/human-support work. Use supervised teleoperation as baseline, local-only rights-cleared demonstrations and independently measured placement/outcome. Proposed ceiling:20 demonstration episodes plus 20 matched teleop and 20 candidate evaluation episodes, maximum 60 episodes/one supervised session; final per-episode duration, force/speed/placement limits and operator stop criteria are mandatory unresolved profile fields. Training is a separate bounded compute package; no implicit GPU purchase.

Held-out object positions/sessions are selected by H06; do not split near-identical adjacent frames into train/test. Freeze baseline/candidate order randomization, apparatus calibration, measurement uncertainty and pass thresholds first. Count every attempt, boundary/force/stability stop and human intervention; retain paired placement measurements and uncertainty, success/failure/unknown and observed recovery. A small finite study can establish only the selected configuration/task envelope and cannot certify general household use. Stop on any force/boundary/stability violation, unexpected person/pet entry, calibration change, loss of stop availability or ambiguous physical state. No retry until authorized reconciliation.

## E09-D — Original EX17 degradation and future modalities

Use the same typed synthetic task while removing vision/state, drifting clocks, corrupting calibration, injecting contradictory RF support and repeating a correlated source. Compare best available single-source baseline with typed late fusion; measure error/unknown count and detection delay against frozen mock truth. Do not average inconsistent evidence into apparent safety. Initially 12 synthetic traces/5 minutes/zero hardware; additional R06/R07 fusion methods remain separately versioned. Future tactile/event/perching comparisons require own physical apparatus and rights review; documentary leads do not bypass EX25/EX26 or sensor-effect qualification.

## Retained ownership

EX25 remains H10 safe-state mock with no actuator connection and no universal motor-off. E09-A refines one proposed implementation, not completion of EX25. EX26 remains H10 supervised inert skill; E09-C is a candidate protocol pending thresholds. EX17 remains H10/RF multimodal degradation. EX24 remains H11 relay/data-ferry work: kit delivery or network receipt does not prove internet or human help. EX16 remains H09 sensor-enclosure work: repeatable reseating alone cannot establish sensing benefit. H06 independent acceptance is required for every later promotion.

