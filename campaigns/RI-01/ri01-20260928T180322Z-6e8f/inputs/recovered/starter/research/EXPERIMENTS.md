# Experiment catalog

**All experiments are proposed and unexecuted.** They are testable paths, not a mandate to run them all or promises of results. Each physical, paid, native-device or private-data step requires its own approval and review. User usefulness and retained ambition guide priority.

## EX01 — Grounded daily notebook

**Owner:** H01 · **Requirement:** REQ-DAILY-03 · **Sources:** R27

**Prerequisite:** Synthetic notes with deliberately conflicting revisions

**Hypothesis:** A scoped retrieval assistant can identify current decisions without inventing missing facts.

**Baseline:** Keyword/ID retrieval with deterministic source excerpts

**Method:** Ask a fixed set of questions; inject an old revision and unrelated note; compare evidence-linked answers.

**Measure:** Correct answer/source rate; unsupported assertions; appropriate abstention

**Boundary:** No private files or external model required. **Stop:** Stop on wrong-user disclosure; no claimed implementation results.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX02 — Two-user privacy challenge

**Owner:** H04 · **Requirement:** REQ-PRIV-01 · **Sources:** Haven design proposal / existing project baseline

**Prerequisite:** Synthetic private/shared records for two subjects

**Hypothesis:** Grant-aware context assembly prevents cross-user disclosure.

**Baseline:** Direct deterministic ACL filtering

**Method:** Request another subject's private data; revoke sharing during a queued answer; test shared speaker audience.

**Measure:** Unauthorized content count; blocked publication trace

**Boundary:** No real partner data. **Stop:** Any leakage blocks integration.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX03 — Model economics benchmark

**Owner:** H02 · **Requirement:** REQ-AI-02 · **Sources:** R25, R26, R27

**Prerequisite:** Synthetic short tasks and exact model/runtime manifest

**Hypothesis:** A compact model can complete selected tasks at lower total cost than an unrestricted strong-model workflow.

**Baseline:** No-model solution and one bounded alternative model

**Method:** Measure same task set under equal context/effort; record cold/warm memory/latency, grounding and retries.

**Measure:** Cost per accepted task; tail latency; privacy failures

**Boundary:** No paid calls or downloads before separate approval. **Stop:** Stop on resource starvation, budget or unsafe output handling.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX04 — Hermes versus thin coordinator

**Owner:** H02 · **Requirement:** REQ-AI-04 · **Sources:** R22, R23, R24

**Prerequisite:** Framework interfaces reviewed; isolated synthetic environment separately approved

**Hypothesis:** A framework saves engineering effort without unacceptable context or authority overhead.

**Baseline:** Thin coordinator design/benchmark

**Method:** Compare same minimal capabilities, isolation tests, context size, generated skill mutations and recovery.

**Measure:** Task success; context growth; maintenance surface; resource cost

**Boundary:** No unrestricted shell or real connectors. **Stop:** Do not shrink required framework context silently to fit hardware.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX05 — Durable daily reminders

**Owner:** H03 · **Requirement:** REQ-DAILY-02 · **Sources:** Haven design proposal / existing project baseline

**Prerequisite:** Separate prototype or accepted daily task module

**Hypothesis:** Reminder receipt and delivery state survive restart without inference.

**Baseline:** Deterministic scheduler fixture

**Method:** Schedule/cancel tasks across timezone transitions and simulated sleep; replay old state read-only.

**Measure:** Correct due/cancelled/missed counts; duplicate delivery

**Boundary:** Synthetic destination only. **Stop:** A duplicate or revived cancellation blocks promotion.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX06 — Voice uncertainty and interruption

**Owner:** H01 · **Requirement:** REQ-DAILY-09 · **Sources:** R37, R38

**Prerequisite:** Consented or synthetic speech fixtures

**Hypothesis:** A staged voice interface distinguishes narration from action intent.

**Baseline:** Typed reference transcript

**Method:** Test names/noise/ambiguous stop commands and interrupted responses without any physical executor.

**Measure:** Intent/clarification accuracy; latency; false side-effect proposals

**Boundary:** No always-on microphone. **Stop:** Stop on a transcript being treated as authorization.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX07 — Watch stale-data semantics

**Owner:** H07 · **Requirement:** REQ-WEAR-03 · **Sources:** R39

**Prerequisite:** Synthetic health observations only

**Hypothesis:** Original sample time and availability survive ingestion and summary.

**Baseline:** Deterministic normalized display

**Method:** Deliver old/out-of-order/missing samples and simulate denied/unknown provider visibility.

**Measure:** No fabricated value/freshness; correct scope/unit/time

**Boundary:** Native collection not required. **Stop:** Any diagnosis/incapacitation claim from absence blocks.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX08 — Glasses lifecycle mock

**Owner:** H07 · **Requirement:** REQ-WEAR-06 · **Sources:** R29

**Prerequisite:** Mock wearer and feature capabilities

**Hypothesis:** Explicit capture state prevents unintended collection/disclosure.

**Baseline:** Phone explicit photo upload

**Method:** Swap wearer, pause session, remove display capability and revoke sharing mid-capture.

**Measure:** Correct capability unavailable/privacy behavior

**Boundary:** No physical glasses assumed. **Stop:** Do not count mock success as device acceptance.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX09 — Spatial origin and transform integrity

**Owner:** H08 · **Requirement:** REQ-RF-07 · **Sources:** R30

**Prerequisite:** Synthetic old scan and new RF estimates

**Hypothesis:** The map can fuse references without relabeling old geometry as live.

**Baseline:** Separate uncombined layers

**Method:** Mix missing transforms, expired calibration and disjoint timestamps; require rejected/degraded fusion.

**Measure:** Incorrect merge count; provenance visibility

**Boundary:** No real floorplan needed. **Stop:** Any fabricated current-room claim blocks.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX10 — CSI acquisition dossier

**Owner:** H08 · **Requirement:** REQ-RF-02 · **Sources:** R04, R05

**Prerequisite:** Exact candidate hardware/API documentation

**Hypothesis:** A lawful affordable acquisition path exists for an initial presence experiment.

**Baseline:** Public/offline dataset alternative

**Method:** Identify accessible measurements, software versions, calibration and permitted setup before purchasing.

**Measure:** Complete interface/unknown matrix

**Boundary:** Documentation only. **Stop:** Four-hour initial review; unverified is a valid result.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX11 — Presence baseline and confounders

**Owner:** H08 · **Requirement:** REQ-RF-02 · **Sources:** R04

**Prerequisite:** Authorized dataset or separately approved node fixture

**Hypothesis:** Presence signal survives simple environmental changes better than a trivial threshold.

**Baseline:** Fixed simple feature threshold

**Method:** Predefine sessions with no motion, moving fixture, changed furniture and consenting movement; hold out sessions.

**Measure:** False alerts/hour; misses; latency; calibration drift

**Boundary:** No covert nearby observation or deliberate RF interference. **Stop:** Stop if ground truth or lawful setup cannot be established.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX12 — Localization against measured positions

**Owner:** H08 · **Requirement:** REQ-RF-03 · **Sources:** R01, R03

**Prerequisite:** Reliable acquisition and known reference positions

**Hypothesis:** More useful localization is possible without unjustified point precision.

**Baseline:** Coarse region classifier

**Method:** Evaluate unseen placements/sessions and multiple possible sources; report regions and error.

**Measure:** Median/tail location error; uncertainty coverage

**Boundary:** Consent and permitted room mandatory. **Stop:** No identity or clinical inference.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX13 — Printed fixture repeatability

**Owner:** H09 · **Requirement:** REQ-ENG-03 · **Sources:** R17, R34

**Prerequisite:** Approved low-risk dimensions and workshop setup for physical phase

**Hypothesis:** A new mount reduces measurement-position variation.

**Baseline:** Existing mount measured with same method

**Method:** Generate CAD; independently review; human prints/assembles after approval; repeat measured placement blinded where practical.

**Measure:** Position error and repeatability; material/time

**Boundary:** CAD-only phase first; no real print now. **Stop:** Stop on unsafe setup, poor fit or maximum trial/time budget.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX14 — Controlled edge reconstruction

**Owner:** H08 · **Requirement:** REQ-RF-04 · **Sources:** R02

**Prerequisite:** Qualified measurement model and synthetic known geometry

**Hypothesis:** Edge-oriented reconstruction supports a narrower claim than full scene imagery.

**Baseline:** Simple occupancy/edge baseline

**Method:** Use known shapes, held-out placements and measurement noise; compare geometry without generative fill.

**Measure:** Edge error; false geometry; uncertainty

**Boundary:** Simulation/datasets until hardware/radio category reviewed. **Stop:** Do not label letters as arbitrary document reading.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX15 — Adaptive next observation

**Owner:** H08 · **Requirement:** REQ-RF-09 · **Sources:** R01, R06

**Prerequisite:** Finite prerecorded/synthetic observation set

**Hypothesis:** An adaptive policy reduces uncertainty using fewer or equal permitted observations.

**Baseline:** Fixed scan schedule with same budget

**Method:** Hide reference result from selector; allow only pre-enumerated views; compare held-out tasks.

**Measure:** Error versus measurement count/energy; denied-scope attempts

**Boundary:** No actual motion. **Stop:** Stop if selector accesses hidden ground truth or changes budget.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX16 — Sensor enclosure effect

**Owner:** H09 · **Requirement:** REQ-ENG-08 · **Sources:** R17

**Prerequisite:** Exact sensor and approved enclosure fixture

**Hypothesis:** A protective housing does not materially degrade the measurement under defined conditions.

**Baseline:** Bare sensor in same environment

**Method:** Compare bare/enclosed repeated sessions; record temperature/airflow/optical/RF effects relevant to that sensor.

**Measure:** Bias/repeatability and useful response time

**Boundary:** Safe ambient conditions only. **Stop:** No smoke/gas/hazard exposure generation.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX17 — Multimodal degradation replay

**Owner:** H10 · **Requirement:** REQ-RF-08 · **Sources:** R06

**Prerequisite:** Synthetic/authorized aligned streams

**Hypothesis:** Fusion can detect when one modality becomes misleading.

**Baseline:** Best single-sensor baseline

**Method:** Remove/corrupt one stream, drift timestamps and invalidate calibration; require explicit degraded state.

**Measure:** Error and time to detect invalid modality

**Boundary:** Offline only first. **Stop:** No averaging inconsistent evidence into false safety.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX18 — EC120 compatibility dossier

**Owner:** H05 · **Requirement:** REQ-DRONE-02 · **Sources:** Haven design proposal / existing project baseline

**Prerequisite:** Exact labels/manual/app identity supplied by owner

**Hypothesis:** A documented usable interface may exist, but must be demonstrated in sources.

**Baseline:** Manual-only evidence role

**Method:** Four-hour official-source review of control, telemetry, video, auth and offline requirements.

**Measure:** Documented/contradicted/unverified per capability

**Boundary:** No device connection or reverse engineering. **Stop:** Time cap or absent official evidence yields unverified, not project failure.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX19 — Budget aircraft qualification plan

**Owner:** H05 · **Requirement:** REQ-DRONE-01 · **Sources:** Haven design proposal / existing project baseline

**Prerequisite:** Candidate complete configuration and fresh official documentation

**Hypothesis:** A lower-cost system can meet a defined read-only evidence role.

**Baseline:** Keep EC120/manual or simulator only

**Method:** Resolve controller/bridge/video/takeover/support/parts and true total cost; plan returnable supervised tests.

**Measure:** Requirement coverage and unknowns; complete BOM

**Boundary:** No purchase in this study. **Stop:** Stop candidate promotion when needed interfaces remain unsupported.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX20 — Concurrent simulator reservations

**Owner:** H05 · **Requirement:** REQ-DRONE-08 · **Sources:** Haven design proposal / existing project baseline

**Prerequisite:** Accepted original Gen0 baseline and separately authorized S1

**Hypothesis:** Two simultaneous simulated aircraft keep isolated identities and reserved recovery space.

**Baseline:** Single-vehicle/sequential scheduler

**Method:** Use original S1 plan; remove one telemetry stream; test occupied landing resource and wrong target.

**Measure:** Conflicts/cross-target calls; unknown reservation preservation

**Boundary:** Original loopback-only simulator isolation. **Stop:** No real aircraft or unreviewed new pins.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX21 — Independent synthetic help

**Owner:** H11 · **Requirement:** REQ-EMERG-01 · **Sources:** Haven design proposal / existing project baseline

**Prerequisite:** Separately authorized S2 and test-only inbox

**Hypothesis:** Help communication is independent of optional AI/aircraft outcomes.

**Baseline:** Same trigger with all optional components available

**Method:** Stop AI, deny mission, exhaust optional budget and replay trigger under expired/revoked policy.

**Measure:** Mock deadline, duplicates and eligibility

**Boundary:** No real recipients or clinical events. **Stop:** No local inbox labeled real dispatch.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX22 — Ground illumination and message usefulness

**Owner:** H11 · **Requirement:** REQ-EMERG-05 · **Sources:** R31

**Prerequisite:** Reviewed ground light/speaker setup with safe limits

**Hypothesis:** A controllable light/message improves observation or understanding.

**Baseline:** Existing ambient view/ordinary phone audio

**Method:** Compare permitted light angles or messages against predefined visibility/intelligibility tasks.

**Measure:** Useful image improvement; glare/noise; energy/heat

**Boundary:** No aircraft payload, road traffic or emergency scene. **Stop:** Stop unsafe output/heating or poor human comprehension.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX23 — Offline guest portal

**Owner:** H11 · **Requirement:** REQ-COMMS-01 · **Sources:** Haven design proposal / existing project baseline

**Prerequisite:** Isolated synthetic guest/control networks after separate permission

**Hypothesis:** A local service remains useful without claiming internet.

**Baseline:** Static offline page

**Method:** Disable upstream, test guest resources and privacy routes; no real emergency intake.

**Measure:** Truthful service state; denied internal access; minimal usability

**Boundary:** No public LAN exposure during design. **Stop:** Any control/private reachability blocks.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX24 — Relay and data-ferry replay

**Owner:** H11 · **Requirement:** REQ-COMMS-06 · **Sources:** R20, R21

**Prerequisite:** Synthetic contact schedule and test recipients

**Hypothesis:** Store-and-forward can improve deadline delivery under intermittent contacts.

**Baseline:** Stationary relay-only schedule

**Method:** Inject duplicate/lost contacts, expiry, cancellation and recipient nonacknowledgement.

**Measure:** Delivery by deadline; duplicate suppression; accurate status

**Boundary:** No radio/flight required. **Stop:** Do not infer internet or human help from relay receipt.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX25 — Robot safe-state mock

**Owner:** H10 · **Requirement:** REQ-ROBOT-03 · **Sources:** R08, R09

**Prerequisite:** Mock adapter and defined device-specific state model

**Hypothesis:** Each task has a deterministic safe recovery contract.

**Baseline:** Manual operator reference sequence

**Method:** Freeze planner/network or inject unknown gripper/pose; verify the design refuses unsafe continuation.

**Measure:** Correct recovery/unknown states; no second owner

**Boundary:** No actuator connection. **Stop:** No universal motor-off behavior across all devices.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX26 — Teleoperation and bounded inert-object skill

**Owner:** H10 · **Requirement:** REQ-ROBOT-02 · **Sources:** R07, R09

**Prerequisite:** Separately reviewed complete platform and physical stop

**Hypothesis:** A small household-relevant skill can be learned or replayed safely in a controlled workspace.

**Baseline:** Supervised teleoperation

**Method:** Collect demonstrations; test held-out inert-object positions; record every failure and intervention.

**Measure:** Task success, interventions, placement error and recovery

**Boundary:** No hot/sharp/medical/human-support task. **Stop:** Stop on boundary/force/stability violation.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX27 — Machine job provenance without a printer

**Owner:** H09 · **Requirement:** REQ-ENG-05 · **Sources:** R18

**Prerequisite:** Synthetic design/toolpath/profile IDs

**Hypothesis:** A fabricated job cannot be promoted from an unreviewed artifact.

**Baseline:** Manual approval checklist

**Method:** Change hashes, machine profile, deadline and approval state; simulate interrupted print/inspection failure.

**Measure:** Rejected unreviewed jobs; no false inspected state

**Boundary:** No actual toolpaths or heating. **Stop:** No job executor included in this repository.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX28 — Bounded engineering iteration

**Owner:** H09 · **Requirement:** REQ-ENG-09 · **Sources:** R13, R14, R15

**Prerequisite:** Protected synthetic objective and later approved physical fixture campaign

**Hypothesis:** A useful agent improves a metric while respecting uneditable test and resource limits.

**Baseline:** Fixed design or human-selected candidate

**Method:** Allow limited candidate proposals; separate hidden evaluation; introduce bad measurement and no-progress trials.

**Measure:** Accepted improvement, invalid-data detection, cost and stop compliance

**Boundary:** Synthetic stage first; physical operations separate. **Stop:** Stop cap, changed criteria, invented data or unapproved fabrication.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX29 — Readiness without inference

**Owner:** H06 · **Requirement:** REQ-EMERG-07 · **Sources:** Haven design proposal / existing project baseline

**Prerequisite:** Synthetic inventory/inspection/charge observations

**Hypothesis:** Readiness status is more reliable when computed from explicit qualification records.

**Baseline:** Manual checklist

**Method:** Expire inspection/calibration and remove fresh telemetry; keep AI offline.

**Measure:** False ready/unknown detection; explainability

**Boundary:** No genuine emergency dependence. **Stop:** Any unqualified device shown ready blocks.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX30 — Novelty and correction review

**Owner:** H12 · **Requirement:** REQ-RESEARCH-01 · **Sources:** R15

**Prerequisite:** Original headline plus correction and competing evidence

**Hypothesis:** The research agent preserves revisions and avoids overstating novelty.

**Baseline:** Human-curated source register

**Method:** Ask for a proposed adaptation and limitations; insert unverified social-media claim.

**Measure:** Supported claims and correct maturity; correction retention

**Boundary:** Public evidence only. **Stop:** No novelty certification or automatic installation.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX31 — Map uncertainty in an accessible interface

**Owner:** H01 · **Requirement:** REQ-RF-05 · **Sources:** R30

**Prerequisite:** Synthetic spatial layers and uncertainty regions

**Hypothesis:** Users can distinguish known, estimated and unobserved space.

**Baseline:** Text explanation

**Method:** Compare phone/mock-glasses presentations with old maps/conflicting evidence.

**Measure:** Human comprehension; unsafe interpretation frequency

**Boundary:** No real navigation guidance. **Stop:** Stop a display that implies safe passage without evidence.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.

## EX32 — Restore and revocation across domains

**Owner:** H06 · **Requirement:** REQ-PRIV-04 · **Sources:** Haven design proposal / existing project baseline

**Prerequisite:** Synthetic backups, tasks, grants and action histories

**Hypothesis:** Review restoration does not resurrect authority or deleted shared content.

**Baseline:** Fresh empty review instance

**Method:** Restore an old snapshot with consumed action, revoked grant and cancelled reminder; attempt review only.

**Measure:** No execution replay or privacy resurrection; intact provenance

**Boundary:** No active application overwrite. **Stop:** Any implicit external/physical effect blocks.

**Retain:** versioned protocol, actual inputs/apparatus, all trials, raw data, analysis, resource use and independent decision. **Status:** PROPOSED_NOT_EXECUTED.
