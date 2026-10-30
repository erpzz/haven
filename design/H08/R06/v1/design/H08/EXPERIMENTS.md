# R06 experiment protocols and evaluation gates

Version 1.0 · **All experiments below: PROPOSED_NOT_EXECUTED**

No measurements, RF benchmarks, physical tests, trained models or device acceptance runs occurred in this thread. Documentation/package checks are reported separately. All thresholds are proposed and must be frozen by H06 before data inspection; they are not expectations promised by a vendor or paper.

## Common protocol

Owner: H08. Independent reviewer: H06 (research-thread R13). Consent/authority review: H04 (R03). Operator: not assigned. Physical permission: NOT_GRANTED. Parent experiment IDs remain EX09–EX12, EX14 and EX15; these R06 cards refine them without changing their status.

The experiment manifest must freeze the question, all eligible cases, input digests, acquisition profile, consent/license scope, apparatus revisions, split unit, exclusions, analysis and stopping rule before evaluation. Preserve failed and excluded trials with reasons. Use independent rooms/sessions/subjects as statistical units, not thousands of correlated CSI packets. Confidence intervals must reflect that grouping. Record participant counts and disjoint subject splits where labels permit; if the same two people appear throughout, claim only room/session transfer, never generalization to unseen people. A tiny pilot is exploratory even if its point estimate passes.

Ground-truth uncertainty and synchronization errors are reported alongside model error. Missing labels are not negatives. With no continuous empty-room recording and verified duration, false alarms per hour is **not estimable**. Replay duration is not substitute exposure. Unseen-room testing with an unlabeled empty-room calibration is a distinct calibrated-transfer protocol; label-free transfer cannot use those test-room calibration samples.

## E0 — Smallest useful experiment: honest replay under missing evidence

**ID:** R06-E0. Parents EX09, EX15. Requirements REQ-RF-07, -08, -09; AT-RF-07, -08, -09. This is the recommended first future coding experiment, requiring no hardware or real personal data.

**Hypothesis:** a bounded estimator/selector pipeline can maintain provenance, unknown state and policy constraints while selecting useful measurements from a finite catalog. This tests software semantics under a declared toy model, not RF capability.

**Setup / inputs:** generate 60 deterministic synthetic episodes: 20 development, 10 calibration, 30 protected test episodes. Each contains an artificial room frame, one or two possible source regions, 16 allowed view candidates, sample timestamps, and a simple declared likelihood model. Include an old visual map, unrelated new motion, missing/late batches, clock reset, missing transform, moved calibration, ambiguous device ownership, revoked scope and a prohibited view. Make simulation labels prominent. The generator and inference model must be separately described; deliberately perturb the test forward model to expose inverse-crime optimism.

**Baselines:** fixed lexicographic view order and seeded random selection; same initial information and eight attempted observations maximum. Deterministic entropy/task-loss selection is the only adaptive contender initially. Include STOP as a valid answer.

**Ground truth:** hidden synthetic state and immutable permission/time scripts held in the evaluator, inaccessible through selector inputs. Compare the output's state to the script; no real-world inference follows from success.

**Metrics / gate:** zero unauthorized selections, false current labels, fabricated positions, stale-to-live map promotions or post-revocation disclosures across protected cases. All missing/ambiguous outcomes must remain typed unknown/degraded. Report localization-region coverage/volume, error by view count, abstention and actual decision time. Adaptive selection need not win to pass the integrity gate; it remains disabled unless it reduces median task loss by at least 10% versus the better fixed/random baseline without worse tail loss, under the same budget. An inconclusive adaptive result is acceptable; no claim of physical efficiency.

**Stop / resources:** one 8-hour engineering package, one CPU worker, ≤4 GiB RAM, ≤1 GiB artifacts, ≤60 s per episode, at most two documented algorithm revisions using development data only, $0 new hardware/hosted spend. Freeze test labels before the final run; a failed final gate needs a new version and independent review, not test-set tuning.

**Retain:** manifest/seed, protected split digest, synthetic fixtures, canonical input/output hashes, every selection/denial, cancellation trace, timing/resource report and failed cases. Reviewer receives an all-case report, not only successful screenshots.

## E1 — Smallest RF evidence experiment: offline CSI confounder baseline

**ID:** R06-E1. Parents EX10, EX11. Requirements REQ-RF-02, -10. Mode: licensed prerecorded data only, after approval of the specific dataset.

**Question:** can motion-sensitive features distinguish labeled human motion from documented nonhuman confounders across held-out sessions/environments better than one aggregate amplitude threshold?

**Candidate data:** CSI-Bench's motion-source subset is a lead, not a selected/ingested dataset. The current author repository reports Kaggle v12 corrections and a code/README license discrepancy [R06-S18]. Before use: resolve data versus code rights, provenance/participant scope, actual version/digests, feature format, capture duration, environment IDs and labels. Exclude human-identification, health and breathing tasks from R06. The UCSB RSSI dataset is a geometry lead with academic-only terms [R06-S19], not interchangeable CSI motion data.

If those gates cannot be resolved within two hours, stop with `BLOCKED_DATA_ACCESS`; E0 continues independently. Do not contact authors, register accounts or download executable pipelines automatically. Synthetic data may test plumbing but cannot replace this experiment's empirical conclusion.

**Method:** robust amplitude normalization using training data only; windowed variance/Doppler-energy features where timestamp quality supports them; fixed threshold baseline, then regularized logistic regression or another small predeclared classifier. At most one richer model after a measured baseline failure. No LLM classification of raw arrays. Stationary human examples, if absent, explicitly limit the claim to movement/source discrimination.

**Split / metrics:** choose full environment/session groups before preprocessing. Train on permitted groups, tune on a different session/environment, protect at least two test environments if available. Report exact group counts and each environment separately; if unavailable, call the result session-transfer only. Macro F1, per-class miss/false-positive rates, selective error versus abstention, calibration error, latency and sensor-config sensitivity. Report alarms/hour only when its ground-truth exposure exists.

**Pilot advancement rule:** at least 0.05 absolute macro-F1 improvement over the simple baseline on held-out groups, no material worsening for the chosen human-motion miss category, plus explicit unknown handling on corrupt/missing samples. H06 determines whether evidence is sufficient; overlapping uncertainty or small groups yields INCONCLUSIVE. Passing supports acquisition research, not stationary occupancy, identity, falls, geometry or household deployment.

**Resources:** 8 hours after access review, ≤2 GiB selected raw data, ≤2 CPU-hours for fitting, ≤4 GiB RAM, $0 hosted inference. No full-dataset GPU sweep. Retain all split assignments, preprocessing parameters, confusion matrices, group bootstrap intervals and errors.

## E2 — Later fixed-node, consented motion and still-presence characterization

**ID:** R06-E2. Parents EX10, EX11. Requirements REQ-RF-02, -06, -10. Mode: physical; NOT_GRANTED.

**Prerequisites:** one selected qualified AP/CSI receiver configuration, approved sensing footprint/site, complete BOM, H04 grants, exact firmware, capture metadata, independent stop, explicit participant list and no uncontrolled neighboring-area exposure. The project brief does not authorize sensing either household member.

**Design:** two permitted rooms used for development/calibration and two untouched permitted rooms used for evaluation. If only one or two rooms exist, report a smaller pilot with no broad held-out-room claim. Per test room: two independently reset sessions, each containing one hour of verified empty-room exposure and 20 scripted two-minute trials spanning walking, sitting still, furniture/door changes and approved nonhuman movement. No deliberate radio interference. No medical-event reenactment. Total planned evaluation exposure is 6 hours 40 minutes across all four test sessions, plus resets and separate development time.

**Ground truth:** operator event log and surveyed zones; optional synchronized video only with a distinct grant, held from the RF estimator and deleted under the protocol. Human occupancy and human motion are two separate labels. A tag is not ground truth for person identity.

**Metrics / proposed pilot gate:** human-motion recall ≥90%, ≤1 false motion event per verified empty hour, 95th-percentile event latency ≤2 s, with uncertainty intervals and per-room breakdown. Define an event as consecutive positive windows merged until a ten-second clear interval; lock this rule before evaluating. Separately report still-presence sensitivity and abstention; movement success cannot satisfy occupancy acceptance. Revocation must block further admitted samples/publication and be logged. Any out-of-scope collection or silent missing→empty conversion stops the session.

These modest exposure counts do not prove a rare-failure bound. For example, zero events in four hours still gives an approximately 0.75/hour one-sided 95% Poisson upper bound under its assumptions. A reliable daily-use claim needs longer independent exposure and an appropriate model for clustering.

**Cap:** two development days + two evaluation days, no more than the frozen four test sessions, suggested $150 complete CSI planning ceiling. No automatic extension if results disappoint. Outcome may recommend radar or no occupancy feature rather than more Wi-Fi model complexity.

## E3 — Cooperative device localization with honest regions

**ID:** R06-E3. Parent EX12. Requirements REQ-RF-03, -08. Mode: offline first; native/accessory physical run needs a separate gate.

Choose one path: supported NI accessory with measured direction/range, or multiple surveyed UWB/RTT anchors. A range-only single anchor supplies a shell/annulus, not a unique 3D position. For unconstrained 3D range multilateration, plan at least four noncoplanar anchors and test geometric degeneracy; fewer may work only with explicit plane/height/direction constraints. Do not buy anchors before proving data access.

Use 20 independently surveyed positions per room, multiple orientations and held-out sessions, including documented NLOS cases and device-swap scenarios. Ground truth uses independent metrology, not the ranging system. Baselines are coarse permitted zone and least-squares range fit. Proposed usefulness target: median device-location error ≤0.5 m and 95th percentile ≤1.5 m in the selected operating domain, with nominal 90% regions achieving 85–95% empirical coverage and bounded volume chosen before test. These are aspirations requiring hardware qualification, not vendor guarantees. NLOS may be declared out of domain with explicit abstention; report the fraction excluded.

Record invalid ranges, clock reset, anchor relocation, reflections, poor geometry, lost-peer and background interruptions. Gate fails for fabricated direction, stale tracks shown current, or person identity inferred from a tag. Cap 8 hours of replay analysis; later physical plan ≤80 placements and one acquisition day. Hardware branch chosen only after complete quotation and scope review.

## E4 — Ambitious controlled reconstruction and adaptive scanning

**ID:** R06-E4. Parents EX14, EX15. Requirements REQ-RF-04, -05, -07, -08, -09. Research-stage, physical permission NOT_GRANTED.

**Hypothesis:** a known multi-view aperture and a physics-based reconstruction can recover the location/orientation of controlled hidden edges or surfaces; adaptive sampling may reduce measurement count without increasing false geometry. Preserve the long-term through-wall spatial target while first isolating an answerable inverse problem.

**Apparatus selection gate:** review two alternatives and select one, never assume interchangeability: (A) a Wiffract-inspired measured Wi-Fi sampling grid for edge hypotheses; (B) a qualified radar scanning fixture with raw coherent samples for surface reconstruction. Freeze frequency/bandwidth, TX/RX geometry, calibration/pose tolerance, aperture, scan spacing, dwell, wall/material model and data access. No generic handheld/drone prototype substitutes for this dossier. The sources are inspiration, not permission or a promise of reproduction. [R06-S12, R06-S13, R06-S17]

**Replay stage:** 60 synthetic scene configurations split 30 development / 10 calibration / 20 protected test, plus a licensed measured dataset if independently approved. Use a stronger perturbed test forward model than the inverse model, including material/delay uncertainty and unmodeled scatterers. Freeze candidate views before selection. Compare regularized tomography or matched-filter/backprojection, edge-specific reconstruction, fixed/random/adaptive schedules and an optional learned prior. Display raw reconstruction and any completion separately.

**Later physical design:** in a controlled isolated test area, 24 target/placement/material configurations over two sessions, 12 development/calibration and 12 untouched tests. Targets are nonhazardous controlled shapes, including an empty target volume and a shape absent from training. Initially use a permitted freestanding obstruction in an entirely controlled area; success is “through this test obstruction,” not through arbitrary building walls. A real room-wall version needs separate equipment/site/participant approval.

All poses and target geometry are independently surveyed with uncertainty. Reveal the hidden target geometry only to the evaluator. Account for enclosure and operator-body effects. Reserve a subset of RF viewpoints for forward-prediction residual checks; a convincing visual fit alone cannot pass.

**Metrics / gate:** edge precision and recall at a predeclared metric tolerance, mean/95th-percentile edge or surface error, orientation error, occupied/free/unknown coverage, unsupported geometry fraction, uncertainty-region coverage and total acquisition/compute cost. Proposed controlled-edge target: F1 ≥0.8 at 0.10 m tolerance and ≤5% false edge length on the selected test domain, with all empty-target cases reported. For adaptive promotion: ≥20% fewer attempted measurements at matched error/false-geometry limits versus the strongest fixed baseline, with paired configuration-level intervals; otherwise retain fixed scanning. Tolerance must exceed known ground-truth uncertainty and be physically justified before capture. These are research targets, not promised resolution.

**Semantics:** only predeclared shape classes plus UNKNOWN; evaluate open-set rejection. Visual semantic priors must not receive hidden target images. A reconstructed rectangle alone does not establish a door, person or safe passage.

**Cap / stop:** 16 hours offline design/replay analysis; later physical work at most two acquisition days and 24 configurations. No hardware spend assigned until a complete reviewed rig exists. Stop for unstable calibration, unobservable target geometry, insufficient phase/pose quality, permission uncertainty, missing ground truth or any containment failure. No new transmit profile, high-power workaround, unauthorized area or unreviewed carrier is permitted to rescue a failing result.

## E5 — Later room-level geometry and semantics extension

After E4 and R07 fusion integrity, compare RF-only, direct-view-only, historical-map-only and fused methods in at least four independently held-out permitted rooms with changed layouts. Preserve origin masks; do not leak current test geometry through a remembered map. RISE is a relevant multipath/learned-completion precedent, but its measured and completed structure must be evaluated separately [R06-S16].

The target is useful current geometry/change evidence beyond direct sight, with per-room uncertainty and abstention—not photorealism. Budget and apparatus remain unassigned pending earlier results. Status: documentation-only later proposal. This card does not authorize another research campaign.

## Acceptance mapping and result discipline

| Acceptance IDs | Setup / expected behavior | Actual state |
|---|---|---|
| AT-RF-01, -06 | Distinguish a link heatmap and phone-access limitations from the full spatial objective; keep alternative carriers | Design covered; system tests NOT_EXECUTED |
| AT-RF-02, -03 | Held-out presence/localization, stationary/multiple-source ambiguity, framed regions | E1–E3 NOT_EXECUTED |
| AT-RF-04, -05 | Controlled geometry and semantic abstention; generated content cannot pass as observation | E4/E5 NOT_EXECUTED |
| AT-RF-07, -08 | Old map + new RF; wrong frame, clock and calibration | E0 NOT_EXECUTED |
| AT-RF-09 | Fixed versus adaptive observations with equal budgets and hidden truth | E0/E4 NOT_EXECUTED |
| AT-RF-10 | Forbidden area, revoked grants, unqualified transmitter and airborne UWB candidate | Deny physical path; future policy tests NOT_EXECUTED |

H06 must review raw results and exclusions before promotion. A second model's favorable opinion is not independent metrology, consent, physical qualification or evidence of real-world performance.
