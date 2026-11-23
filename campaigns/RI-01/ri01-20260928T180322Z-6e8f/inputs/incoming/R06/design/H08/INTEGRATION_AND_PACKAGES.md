# R06 integration, coverage and future coding packages

Version 1.0 · 2026-09-28 UTC · **PROPOSED_NOT_IMPLEMENTED**

Research-thread labels R01–R13 are not the starter's H01–H12 ownership labels. R06 belongs to **H08**. R07 world modeling also meets H08; it is a companion handback to reconcile, not an already available service. This package preserves every cumulative branch and assigns no work to the active M0 thread.

## Concrete branch integration

| Branch / owner | R06 supplies → receives | Exact integration boundary and gate |
|---|---|---|
| R07 sensors/world model / H08, coordinated by H00 | `SpatialEstimate:1` + mandatory `SpatialSemantics`, evidence refs → map revision, transform refs, current question and allowed view catalog | Reject missing sidecar or incompatible frame; retain direct-view, RF, historical, inferred and unknown layers. R07 must acknowledge CR-R06-01 before any operational consumer. A new RF packet cannot refresh an old visual map. |
| R03 privacy/authority / H04 | Proposed footprint, participant/session scope, purpose, audience, provider and retention → authenticated policy/grant decisions and revocation epochs | `AccessBinding` names dependencies but grants no authority. Recheck admission, model routing, publication and derived-data retrieval. Both independently consenting people remain separate principals. CR-R06-02 and -03 block live use. |
| R02 runtime/economics / H02 | Bounded RA04 view proposal / RA06 analysis request → quota, cancellation and future lease outcome | Begin as deterministic local jobs; zero hosted budget. Current mock `agent_job:1` cannot become a physical worker by changing a flag. CR-R06-04 owns the eventual lifecycle. |
| R08 engineering/fabrication / H09 | Aperture, pose-error budget, antenna keep-out requirements and measurement plan → versioned fixture design and independent metrology | `design_artifact:1` stays UNQUALIFIED. A printed mount is neither calibrated nor RF-neutral. Measure deformation, repeatability, mounting extrinsics and enclosure effects before R06 references its calibration. Fabrication remains separately authorized. |
| R09 ground robotics / H10 | Finite candidate pose + observation question → carrier-motion proposal, timestamped pose and execution receipt | R06 never emits motor commands. Acquire only after a qualified stationary pose or qualified motion model; wheel/SLAM reset invalidates transforms. Motion permission and RF footprint permission are separate. |
| R10 aircraft / H05 | Sensor profile, payload, permissible viewpoints and time/energy needs → separately qualified mission/pose/outcome evidence | Preserve concurrent-aircraft and preauthorized incapacitation-observation ambitions; do not enable them here. EC120 access remains unverified. Airborne UWB under the cited subpart is blocked unless exact alternative authorization is established. [R06-S21] |
| R04 wearables / H07 | Anonymous spatial region or enrolled-device region → optional independently granted wearer/device association and supported phone measurement | Do not turn device ownership into proof of wearer identity. NI direction/range availability and background behavior require exact native tests. No RF clinical inference or unconsented fusion of wearable health data. |
| Daily assistance / H01 | Minimized, fresh, audience-scoped claim → user question or explicit stop | A future advisory can report motion with age, area and uncertainty. It cannot identify a household member or declare a room empty from silent CSI. Unavailable sensing must not interrupt ordinary assistant tasks. |
| Emergency support/networking / H11 | Scoped evidence or explicit unknown → separately authorized emergency workflow | No negative RF reading rules out distress. No automatic dispatch, relay, aircraft motion or door entry follows from this package. Preserve the emergency branch and its independent authority model. |
| R13 assurance / H06; research / H12 | Frozen protocol, source/data versions, all results including failures → independent evidence review | H06 reviews before promotion; H12 can resolve a specific source/access gate later. Neither is an always-on agent or an approval inferred from this document. |

Connector/tool, local-model, daily-assistant, health/privacy, fabrication, robotics, drone, emergency and networking work retain their own owners and acceptance paths. R06 adds evidence interfaces; it does not replace the overall project, select a new M0 stack, or require all branches to wait for general through-wall reconstruction.

## Requirement and acceptance coverage

These rows propose the H00 coverage-register update. The actual shared register is unchanged. **Every system acceptance test remains NOT_EXECUTED.** “Covered” below means the design addresses the requirement, not that Haven meets it operationally.

| Requirement | Acceptance | Design evidence | Future experiment / unresolved gate |
|---|---|---|---|
| REQ-RF-01 | AT-RF-01 | Architecture §§1–2, 6, 8: distinct presence, location, geometry and semantics | E0 then E1–E5; a heatmap never satisfies later stages |
| REQ-RF-02 | AT-RF-02 | Motion versus still-presence; confounders and unknown state | E1/E2; lawful data, held-out rooms/sessions, stationary-person evidence |
| REQ-RF-03 | AT-RF-03 | Framed cooperative device localization, multimodal regions | E3; surveyed anchors/ground truth, native data access, calibration |
| REQ-RF-04 | AT-RF-04 | Tomography/diffraction/radar observability and controlled aperture | E4; exact apparatus, RF authorization, geometry and forward residuals |
| REQ-RF-05 | AT-RF-05 | Semantic hypotheses and explicit measured/completed support | E4/E5; open-set rejection, no hidden-geometry leakage |
| REQ-RF-06 | AT-RF-06 | Phone, accessory, fixed, handheld, fixture, rover and drone comparison | E2–E4; separate carrier qualification and purchase gates |
| REQ-RF-07 | AT-RF-07 | Capture origin, path context, historical map and delivery mode separated | E0; prohibit old-map→current reconstruction promotion |
| REQ-RF-08 | AT-RF-08 | Typed frames, clock bounds, calibration dependencies and uncertainty | E0/E3/E4; CR-R06-01, independent metrology |
| REQ-RF-09 | AT-RF-09 | Finite candidate catalog, deterministic information value, equal budgets | E0/E4; no hidden truth or model-controlled execution |
| REQ-RF-10 | AT-RF-10 | Footprint consent, approved transmitter profiles and deployment gates | E0 policy cases; E1 rights; E2/E4 exact hardware/site review |

The full experiment protocol is [EXPERIMENTS.md](EXPERIMENTS.md). Shared changes are CR-R06-01 through CR-R06-05 in [CONTRACT_PROPOSALS.md](CONTRACT_PROPOSALS.md).

## Future coding packages

All file paths below are **proposed future paths**, absent from this delivery. Use a separate approved research checkout/worktree. Preserve actual M0 and Gen0 pins. No new repository, branch, dependency installation or remote push is created by this design.

| Package / owner | Bounded work and proposed owned paths | Prerequisites | Success / stop | Resource proposal |
|---|---|---|---|---|
| P0 — Typed replay integrity / H08 | R06-only record definitions, synthetic fixtures, evaluator and deterministic fixed/random/adaptive selectors. `research/r06_replay/`, `tests/r06_replay/`, `design/H08/results/P0/` | H00 accepts CR-R06-01 replay subset and synthetic owner binding; H06 freezes E0 cases. Explicit later coding authorization. | E0 integrity invariants pass; all cases retained. Adaptive promotion separate and may fail. Stop at 8 hours, any scope escape or ambiguous representation; return evidence, no live adapter. | One 8-hour engineering package; 1 CPU worker, 4 GiB RAM, 1 GiB artifacts, $0 new spend |
| P1 — Offline CSI baseline / H08 | Bounded typed importer, deterministic features, one small classifier and grouped evaluation. `research/r06_csi_offline/`, `design/H08/results/P1/` | Dataset rights/provenance/version resolved; approved public-data binding; P0 unknown/provenance checks | E1 report and limits, not household qualification. Stop access review after 2 hours; stop processing on unsupported metadata or unresolvable labels. | Up to 2-hour access review + 8-hour package; 2 CPU-hours fitting, 2 GiB raw subset, $0 hosted |
| P2 — One acquisition adapter / H08 + H04 | Exact device parser, chunking, authenticated bridge, quality/clock metadata and stop/reconciliation. `research/r06_adapters/<approved_profile>/` | P0, exact SDK/profile/board, complete BOM, CR-R06-02/03/04; physical protocol separately authorized | Replay of permitted captured samples first; later E2 or E3 only for approved profile. Unknown clocks/dropouts must abstain. Stop before alternate transmitters or unsupported SDK workarounds. | First 8-hour parser package; later physical budget per E2/E3. No purchase until quoted rig is reviewed |
| P3 — R07 fusion projection / H08 with H00 | Sidecar-aware map projection, support masks, historical/unknown layers, grant lineage. `research/r06_world_projection/` | R07 handback reconciled, canonical field ownership agreed, CR-R06-01/02 | Old-map/new-RF, disconnected-frame, revocation and conflicting-source replays produce honest layers; no operational display before reviewer approval | One 8-hour synthetic integration package; 1 CPU worker, 4 GiB, $0 hosted |
| P4 — Controlled inverse problem / H08 + H09 | Forward-model specification, classical reconstruction and equal-budget scan evaluator. `research/r06_geometry/`, H09-owned fixture proposals kept separate | E0 integrity, E4 apparatus dossier and independent review; measured-data rights if used | E4 replay metrics and support masks. Physical work remains separately gated; no equipment substitution to rescue failure | 16 hours offline; physical time/hardware unassigned until apparatus approval |
| P5 — Carrier bridge / H10 or H05 | Translate approved observation candidates into existing domain proposals; reconcile pose and outcome. Domain-owned paths assigned by H00 | Useful stationary method, independent carrier qualification, approved authority protocol and applicable radio category | Demonstrated benefit over indexed fixture under matched cost; cancellation/recovery and pose uncertainty valid | Scope and budget unassigned; no coding or flight/rover purchase recommendation now |

Package estimates are caps for review, not delivery promises. Independent packages may proceed later only when authorized; this handback does not launch any of them. A richer model or GPU is not a default remedy for failed observability, bad labels or missing consent.

## Decisions for integration

1. Accept the replay-first architecture as a design proposal; keep live sensing unqualified.
2. Reconcile the spatial sidecar and unknown-state vocabulary with R07 before freezing P0.
3. Assign H04 the multi-subject/public-data/footprint bindings and H02 the future lifecycle; synthetic P0 does not need a production consent service.
4. Select only P0 as the next candidate coding package. Retain P1–P5 as bounded options gated by evidence.
5. Keep all shared contract edits and coverage/status updates with H00. Independent approval of this design must not be written as a physical or M0 test pass.

No response, purchase, deployment or additional research is required to consider this handback complete. The task ends at the design/research handback gate.
