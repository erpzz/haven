# Specialist handback — R07 world model, revision 1

Thread / owner / task ID: `/root/ri01_world`, actual `haven_researcher` fallback profile / R07, H08 with H05 / issue #6. H10, H01, H09 and H00 ownership remains unchanged.
Repository: erpzz/haven. Campaign base commit `376031e182c57495912baf6727093b0b188da568`, read from frozen run metadata; no Git command executed by this author. Current source bytes are pinned in INPUT_USE.json; a base commit alone does not identify uncommitted campaign inputs.
Authorized output: only this `research/R07/` directory. Status DRAFT_READY, independent review requested; NOT_UPLOADED by author. Public-safe original research prose; no household layout or third-party media copied.
Actual work: document/source reading, current public primary-source checks, input hashing, one direct benign image inspection, contract and experiment design. No application/model/package/device/private-account operation, deployment, physical qualification or research experiment executed.
Dependencies: accepted CORE and bounded REV-R06 consumed; R10 and exactly R12 O03/O04/O05 consumed as soft inputs. MM-VISION/MM-FUSION/R09/R15 are future consumers, not already consulted or implemented. Original R07 prompt ZIP and hub R07 prompt remain SOURCE_UNAVAILABLE per frozen INTAKE and supervisor clarification; this report uses the actual authorized RI-01 R07 brief and recovered original REQ/AT/EX. It does not reconstruct or claim to have read missing originals.

## Decisions

Recommend a small typed evidence projection with immutable map revisions and separate support layers. The useful first product is a replay inspector that answers what evidence supported a region at a selected time, what is unknown, and which permitted view could resolve a conflict. It should return positive supported answers, not merely refusals. It need not reconstruct a whole home or deploy robotics to be useful.

D07-01: retain the Python 3.12/FastAPI/Pydantic 2/Jinja2/SQLite foundation as compatibility context. The first proposed package is an offline, in-process projection library plus synthetic fixtures; no framework migration, broker, vector database, live M0 route or simulator change. A licensed original image plus selected region and an evidence-linked question can later feed CORE's useful first path without requiring global mapping.

D07-02: represent the world as source-supported claims, geometry and relations, not one photorealistic truth mesh. Separate raw observations from estimators and semantic hypotheses. Source modality (RGB, depth, RF, IMU, telemetry), path (direct/through obstruction/other-side), capture origin (simulated/prerecorded/manual/live device), processing mode (replay/live), support type, availability and temporal state are independent axes. A fresh RF event does not refresh an old wall; a VLM label does not turn a depth prediction into measurement.

D07-03: use late fusion first. Keep contradictory hypotheses and source dependencies visible. Raw-level camera/IMU or coherent RF fusion remains a specialized qualified estimator with its own calibration and correlation model. General language reasoning receives selected claims, regions and source references, not all video or arbitrary RF tensors.

D07-04: accept CR-R06-01's mandatory paired SpatialSemantics envelope and exact left-parent SE(3) profile. No legacy-only operational projection, unknown-as-zero covariance or silently interpreted pose vector. Implement no shared schema change here. CR-R07-01–04 in CONTRACTS.md are proposed extensions for H00 review.

D07-05: adopt REV-R06's corrected 60-second total replay episode with at most eight attempted observations. All selector compute, unavailable/denied attempts and analysis consume remaining time/budget. Acquisition, carrier motion and publication remain distinct authorizations; stop request is not confirmed cessation. A map is never a safe-route guarantee.

D07-06: retain fixed, phone-accessory, handheld, fixture, rover and drone paths. Prefer existing synthetic replay, then separately authorized fixed/handheld measurements. R09 owns rover movement and skills; H05/R10 owns aircraft feasibility/recovery. This sequence is a cost/risk choice, not removal of distributed active perception.

### Representations and maturity

| Candidate | Useful role | Limitation and decision |
|---|---|---|
| Versioned scene graph plus coarse 2D/3D support cells | Query objects/regions, time and source support; deterministic first prototype | Original proposal. No learned scene completion; relations are typed hypotheses unless directly supported. |
| Occupancy octree | Later bounded free/occupied/unknown spatial representation | OctoMap documents probabilistic updates and unknown regions; library BSD, viewer GPLv2. No dynamic-scene safety or deletion lineage follows from the format. [OctoMap](https://octomap.github.io/) |
| TSDF/surface mesh | Later calibrated RGB-D surface reconstruction and inspection | Open3D 0.19 RGB-D integration documents camera poses/intrinsics and depth inputs; surfaces alone are not free-space evidence. Choose only after task/data/dependency review. [Open3D](https://www.open3d.org/docs/release/tutorial/pipelines/rgbd_integration.html) |
| Classical multi-view reconstruction | Baseline for a later selected-camera geometry comparison | COLMAP's format explicitly distinguishes camera pose and intrinsics; freeze its exact version/units/scale adapter. Reprojection error is a pixel residual, not metric covariance. [COLMAP format](https://colmap.github.io/format.html) |
| VGGT (R12 O03) | Candidate inferred camera/depth/point geometry for replay | Camera-from-world OpenCV; prediction confidence is not calibrated covariance. Original checkpoint noncommercial, commercial checkpoint separately gated, code custom license. No selected artifact or deployment clearance. [README](https://github.com/facebookresearch/vggt), [terms](https://raw.githubusercontent.com/facebookresearch/vggt/main/LICENSE.txt) |
| ActiveSplat (R12 O04) | Inspiration for bounded view selection against fixed/random baselines | Hybrid Gaussian/dense and topological planning research; MIT code does not license all data/dependencies. Author simulation and robot claims were read, no demonstration watched. No Haven motion or collision qualification. [Project](https://li-yuetao.github.io/ActiveSplat/), [license](https://raw.githubusercontent.com/Li-Yuetao/ActiveSplat/main/LICENSE) |
| RFDT (R12 O05) | Future inverse-problem identifiability comparison | Released README describes minimal conceptual notebooks, full simulator forthcoming, RayD/DrJit and CUDA. Artifact reuse license unresolved. Gradient matching does not demonstrate unique hidden geometry. Keep alternative geometries and optical-prior dependencies; no run selected. [README](https://raw.githubusercontent.com/Asixa/Mini-Differentiable-RF-Digital-Twin/main/README.md) |

A learned or splat representation may be an excellent explanatory view while unsuitable as a collision map. Visual realism, benchmark rank and triangulation residual are different from calibrated error, coverage and permitted use. The future geometry comparison should use measured scale/reference and withheld poses/objects; no model selected by this report.

### Frames, calibration, time and uncertainty

Every frame is scoped to device/boot/map revision, with named axes, handedness, unit and origin datum. A transform says `p_parent = R * p_child + t`, normalized xyzw, left perturbation in parent frame and covariance order [tx,ty,tz,rx,ry,rz], with m²/rad²/m·rad blocks. Reject wrong dimensions, unsupported convention, nonfinite numbers, non-unit quaternion, non-PSD covariance and disconnected/cyclic projection paths. Explicit numerical tolerances belong to the frozen implementation profile, not a universal physical tolerance.

ROS REP 103 supplies useful right-handed SI/body/optical conventions; REP 105 distinguishes continuous drifting odometry from map localization jumps. Haven borrows these distinctions without claiming ROS installation or treating its covariance description as proof of the R06 left-perturbation convention. [REP 103](https://raw.githubusercontent.com/ros-infrastructure/rep/master/rep-0103.rst), [REP 105](https://raw.githubusercontent.com/ros-infrastructure/rep/master/rep-0105.rst).

A relocalization creates a new transform/map revision and invalidates dependent projections; historical raw samples retain their original frames. Do not interpolate through map jumps. A spatial frame named `map` is not globally georeferenced. Earth/geospatial connection can stay absent. WGS84 longitude/latitude needs a vertical datum; relative-home height binds home-origin and boot/config and cannot be called AMSL, ellipsoid height or terrain clearance. Preserve native telemetry and normalized values together (R10/CORE advice).

For an external camera-from-world pose, a camera-to-world transform requires inversion, not a label swap; COLMAP's wxyz storage also requires explicit component conversion to R06 xyzw. Unknown reconstruction scale stays UNKNOWN and cannot enter a metric overlay. A Sim(3) alignment is a separately versioned estimate, not an SE(3) transform with fabricated metres. Store alignment evidence, fitted scale and uncertainty/unknown, held-out residuals and domain before metric use.

Calibration distinguishes intrinsic/distortion, extrinsic, depth scale/bias, clock mapping, RF antenna/phase/environment and statistical coverage. Bind device/profile/hardware/firmware, fixture/enclosure/material/assembly, reference uncertainty, method, validity interval, domain and invalidation conditions. Moving an anchor, reseating a fixture, firmware/config changes, impacts and environment departures require evaluation/requalification; TTL alone is inadequate. R08's scalar displacement-only boundary is accepted as an interface proposal; one-axis repeatability never establishes 6DoF, phase coherence or improved sensing.

Retain source ticks, clock ID/boot, sample interval, receipt and processing time, mapping revision, precision and clock error bound. For two intervals [a,b] and [c,d] with bounds u and v, worst-case temporal separation is max(abs(a-d),abs(b-c))+u+v. A task can only call them co-temporal if this value fits its frozen tolerance and the quantities actually represent compatible sample intervals. Mere interval overlap permits uncertain simultaneity, not proof. Clock reset/rollover creates a new mapping; receive-time proximity cannot substitute. Unknown mappings may support ordered source-local replay, not current synchronized fusion.

Keep model scores, measurement covariance, calibrated coverage regions, systematic bounds and clock uncertainty distinct. No scalar confidence average. Multimodal distributions retain separate hypotheses instead of a mean in an impossible location. Correlation ancestry includes common frames, parent video, crops, model features, optical priors and calibration. If cross-correlation is not modeled, the initial projector keeps estimates separate or chooses a declared single supported estimate; it does not reduce covariance by treating them as independent. Future conservative fusion requires its own proven profile and coverage tests.

### World layers, history and corrections

Projection has at least four selectable layers: observation-supported geometry/events; inferred geometry/semantics; retained historical states; unknown/conflict regions. These are views over explicit axes, not mutually exclusive storage bins: an observed old depth point is historical and observation-supported. Generated completions live in an unmistakable scenario/hypothesis branch, never an observation branch.

For each voxel/region retain support state OBSERVED_OCCUPIED, OBSERVED_FREE, OCCLUDED, UNOBSERVED or CONFLICT plus evidence locator, capture interval, estimator/calibration and validity. OBSERVED_FREE requires a qualified measurement/ray model under its range/visibility assumptions; missing return, dark pixel, RF silence and outside-view cells do not prove free space. Occupancy values have declared semantics; ROS 2's current message describes application-dependent values, so no silent 0–100/-1 convention conversion. [ROS 2 message](https://raw.githubusercontent.com/ros2/common_interfaces/rolling/nav_msgs/msg/OccupancyGrid.msg).

Separate static structure, change candidates, temporary anonymous tracks and semantic labels. A track gap makes association uncertain; it cannot attach identity, another user's health data or authority. A historical chair is not currently present without supporting recent evidence. Task-specific freshness policies can differ for walls and motion, but an expiration is a use limit, not proof the object disappeared. RF motion can annotate a broad uncertainty region without inventing a body pose or exact object.

MapRevision records immutable parent, evidence/transform/calibration refs, builder/profile, source closure, capture interval, build time, unknown extent and conflicts. Store valid-time (when a claim concerns the world) and knowledge-time (when a correction became known). A replay query specifies both, but current authorization always governs retrieval/release. A correction produces a successor; it does not retroactively overwrite the original evidence. Old authorized views may explain what was believed, not restore revoked content.

A source tombstone immediately denies further eligibility under CORE. Transitive invalidation covers dependent cells/meshes, tracks, associations, summaries, embeddings, tiles, scenario forks, exports and output contexts, including uncited influences. If contribution-level removal cannot be proven, invalidate the entire affected materialization and recompute from eligible parents. Minimized deletion receipts remain privacy-bearing and need scoped retention; physical erasure across each copy is separately tracked. Inaccessible is not erased; backups cannot resurrect prior grants after restore. CORE I01/I02/I03/I06 are authoritative for the design. No eventual index can be the security boundary.

### Fixed, handheld, rover and aircraft tradeoffs

| Embodiment | Useful affordable entry | Calibration/coverage costs | Later qualification and preserved ambition |
|---|---|---|---|
| Fixed approved sensor or phone on fixture | Stable selected-view replay; later manual selected capture | Blind spots, exposure footprint, power/storage; movement invalidates extrinsics | Multiple calibrated viewpoints and low-duty observation without implying whole-room coverage |
| Phone accessory / handheld camera or depth instrument | Human-selected additional angle and scale reference | Motion blur, rolling shutter, uncertain timestamps, scale drift, hand pose, human effort | Guided capture and conditional accessory ranging; no assumed arbitrary phone raw RF/depth API |
| Rover / telepresence carrier | Ground-level viewpoints and sensor transport after R09 review | Wheel slip, occlusion, stairs/edges, tethering, battery, localization drift and people/pets | Task-qualified sensing and later low-force skills; independent stop and carrier authority |
| Consumer drone / open aircraft | Later approved elevated view; manual image/telemetry first | Rotor vibration/noise, energy/reserve, downwash, payload/center of gravity, weather, datum/clock and link loss | Distributed overhead sensing, coverage handoff, bases and emergency observation remain H05/H11 future domains |

These are engineering comparisons, not product purchases. R10's exact compatibility dossier is the aircraft source of truth: EC120 interface remains UNKNOWN; consumer control/video/telemetry are configuration-specific; an open flight controller is not a complete camera payload. Ground-mounted lights/speakers or fixed observations can serve a question more cheaply than moving an aircraft. Broader public-world science uses licensed regional data and stated age/resolution/coverage without importing private household maps.

### Useful joined scenarios and consumer seams

1. Image follow-up: user selects a region of a licensed workshop image; MM-VISION returns a detection/segment with original frame/crop transform. R07 can answer which geometry/label is supported, explicitly leave dimensions unknown, and propose a ruler view. CORE releases to the current private destination; R08 alone handles later metrology.
2. Multisensor replay: an old depth scan supports a wall, fresh-in-replay RF supports anonymous motion nearby and a later RGB frame conflicts with the old furniture position. The inspector displays three dates, uncertain association and a gap. It never says RF saw the chair or that a corridor is safe.
3. Cooperative field view: an approved rover view and an approved elevated image have different frame/clock uncertainty. R07 aligns only if calibrated; otherwise displays separate local maps. R15 shows coverage and unknown gaps. The next-view request can suggest either platform, while R09/R10 determine eligibility and recovery separately.
4. Engineering feedback: an enclosure changed after calibration. R07 marks its derived geometry stale pending requalification, keeping the failed sensor-effect result visible. R08 may compare fixture revisions, but a mechanically repeatable mount cannot silently restore sensing quality.

MM-VISION produces region/mask/depth/pose claims with preprocessing/crop/scale and source lineage. R07 validates geometry and projection; MM-FUSION owns cross-modal association and unified temporal evidence with R07's spatial constraints. R09 consumes a MapView for advisory context plus separate qualification refs, never a motion permit. R15 consumes authorized MapView/ReplayQuery outputs with explicit support/fog-of-war layers and scenario isolation. No consumer is entitled to entire raw storage or hidden influences. Contract details and errors are in CONTRACTS.md.

## Evidence

SOURCES.md records primary sources, exact inspected editions, access/rights and unknowns. Current external pages were text-inspected on 2026-09-28; no mutable repo commit or binary model was pinned for adoption. Local source identities are in INPUT_USE.json. Development modality: DIRECT_IMAGE on R10's synthetic 240×120 smoke bitmap, whole image; red square left, blue circle center, thin descending black line right, white background. SHA256 `10468285615819f3e0946a12b149e2c67699da89002d15747856487fbd54e86f`. This says nothing about Haven VLM, camera calibration or spatial quality. An ActiveSplat image link returned only a textual reference, not inspected pixels; no figure-dependent performance claim is made. Audio/video listening/playback, waveform and real spatial-array inspection NOT_EXERCISED; no capability inferred from model name.

## Interface changes

Propose CR-R07-01 (typed projection/support and exact semantics pairing), CR-R07-02 (immutable map revisions/time/correlation), CR-R07-03 (next-view request and distinct sensing/motion/stop outcomes), CR-R07-04 (current-authority replay and invalidation closure). These extend reviewed CORE/R06 and do not supersede original schemas. H00 resolves shared changes with H08/H05/H10/H04/H06/MM owners. All profiles are PROPOSED_NOT_IMPLEMENTED; supports_safe_route_claim remains false.

## Acceptance

All scientific and product tests are PROPOSED_NOT_EXECUTED. EXPERIMENTS.md preserves original EX09/H08, EX15/H08, EX17/H10, EX31/H01, with EX14/H08 and EX16/H09 future bridges. REQ-RF-01–10 and AT-RF-01–10 stay H08; aircraft and robot requirements retain H05/H10 ownership. No new passing AT or reassigned EX is claimed. Document checks, hashing and the development image smoke check are narrow actual actions, not world-model testing.

## Risks and open questions

Strongest design risk is plausible-looking inferred geometry being consumed as measured free space. Next are hidden correlation, incomplete deletion closure, map jumps/time skew, source-person misassociation, uncalibrated scale and the inability to remove individual contributors from compressed maps. Model rights and full artifact availability are separate from research merit. Camera/RF exposure is larger than a cropped output; private spatial records need actual enrollment and purpose-specific authority later.

No runtime accuracy, latency, RAM/GPU, energy or device stop property is established. The original missing R07 prompt remains a source-fidelity gap; recovered requirements and the current explicit brief constrain this work. Scalar R08 closure can proceed independently of 6DoF qualification. VA-01 requires P01 lifecycle/containment prerequisites before an inference-pilot freeze; it does not block the no-worker replay proposal. Actual private sensing, models and a physical platform remain separate authorization decisions.

## Next package

WP-R07-P0 in NEXT_PACKAGE.md: one bounded synthetic offline evidence/map replay prototype, no model or device execution. Proposed implementation allocation 120 minutes plus 30-minute independent review, at most 4 GiB RAM, 50 MiB artifacts, zero new packages/models/purchases/hosted calls. Per replay episode 60 seconds total/eight attempted views. These are requested ceilings, not measured costs. The operator must approve the exact reviewed coding package before it starts. End at independent review and retain every failed case.

