# R09 — Ground robotics and embodied skills

Thread / owner / task: `/root/ri01_world`, actual `haven_researcher`, R09 / H10. Date: 2026-09-28. Campaign: `ri01-20260928T180322Z-6e8f`. Supervisor-reported base: `376031e182c57495912baf6727093b0b188da568`; no Git command or verification by this author. Status: DRAFT_READY for independent review, documentary scope only. Only `research/R09/` is changed. Exact frozen predecessors and their finding-to-decision use are in INPUT_USE.json. The original R09 prompt archive is SOURCE_UNAVAILABLE; this report uses the authorized RI-01 R09 brief, recovered H10 starter and original requirement/test/experiment records, without reconstructing a missing prompt.

## Decisions

**D01. Build the smallest useful skill-evidence replay before buying a robot.** A fixed view can answer an inspection question; a parked phone can support telepresence; a ground carrier can move a secured light or inert kit; a bench arm can study bounded transfer. Choose the least complex embodiment that supplies the actual missing capability. R09-P0 proposes a deterministic mock with no model, driver or actuator. It demonstrates a useful distinction between a proposal, an admitted simulated dispatch, a device acknowledgement and observed task completion. All actual robot qualifications remain UNKNOWN.

**D02. Retain all five REQ-ROBOT/AT-ROBOT pairs and EX25/EX26, plus H10's EX17.** REQ-ROBOT-01–05 remain owned by H10 and their tests by H10 with H06 review. EX24 remains H11 and EX16 remains H09. REQUIREMENTS.json carries exact original selected records, not rewritten substitute tests. R09-specific experiments are additional proposals. No original acceptance test has run or passed.

**D03. Prefer a staged comparison.** Existing fixed camera/phone first; SO-101 follower plus leader for a future supervised bench study; TurtleBot3 Burger for a documented differential-drive sensing/secured-tray candidate; LeKiwi for a later combined mobile-manipulation study. Full prices, current interfaces and unknowns are in PLATFORMS.md. Stretch 4 is an ambitious laboratory reference whose manufacturer terms do not support household procurement. A humanoid is neither required nor selected.

**D04. Teleoperation is the baseline, task-specific imitation the first learned comparison.** Keep one trained operator, visible local state, an independent stop/recovery chain, explicit ownership and a bounded workspace before recording demonstrations. Then compare ACT to the same frozen teleoperation task; consider SmolVLA and OpenVLA-OFT only where language/visual generalization offers a measured task benefit. Model success rates from another embodiment do not qualify this robot. Any policy produces a typed candidate only, never motion authority.

**D05. Reuse the accepted seams literally.** R07 supports observed/inferred/historical/unknown evidence and explicitly denies safe-route claims. MM-VISION supplies qualified task-specific visual evidence, with capture interval, time uncertainty, calibration, association and occlusion; its accepted pilot is not robot safety qualification. R08-P00 supplies an inert one-axis provenance profile, not 6DoF, contact force, sensing benefit or physical manipulation qualification. CORE I01–I07 owns authority, resources, job/outcome and output ordering. CONTRACTS.md extends these by reference, not by editing shared schemas.

**D06. UNKNOWN physical state retains exclusion.** Expired ownership, a dead process, absent ACK or revoked permission does not prove the robot stopped, released an object or vacated a shared region. Block new elective motion, retain the conflicting reservation and reconcile through the prequalified local recovery profile or an authorized human. A generic motor-off can drop a load or collapse a gravity-loaded joint; its suitability is device/task-specific.

## Evidence

Fresh primary documentation and public store pages were inspected on 2026-09-28. SOURCES.md records URLs, edition precision, rights and limitations. Price displays are not delivered quotes; code and model cards are not executed evidence. PLATFORMS.md distinguishes source subtotals from UNKNOWN total ownership cost. No current source is used to change the original Gen0 simulator, M0–M6 or M4 image-model pins.

The strongest practical result is architectural: affordable open hardware and released policies make a bounded study plausible, but a useful application needs exact camera/action/unit/calibration and command-lifecycle compatibility. SO-101 and LeKiwi documentation expose different joints, gear ratios, supplies and control surfaces; a model's action vector is not a universal physical API. Current LeKiwi BOM and SO-101 assembly documentation need reconciliation before any complete kit is selected. Nav2 Collision Monitor is useful supplemental software, expressly without hard real-time safety certification. These facts motivate the profile and failure tests; they do not establish physical safety. [SO-101](https://huggingface.co/docs/lerobot/so101), [LeKiwi](https://huggingface.co/docs/lerobot/main/lekiwi), [Collision Monitor](https://raw.githubusercontent.com/ros-navigation/navigation2/main/nav2_collision_monitor/README.md).

## Interface changes

Proposed namespace `ri01.proposed.r09.v1`, H10 producer with H00 authority owner, H08/R07 and MM-VISION evidence owners, H09 qualification owner and H06 independent evaluator. Five explicit records are proposed in CONTRACTS.md: EmbodimentProfile, SkillSpec, SkillEvidenceBundle, SkillIntent and Execution/Reconciliation records. Physical observation, interpretation, intent, dispatch, outcome and recovery remain separate. A synthetic profile cannot match a physical device. No arbitrary shell, URL, ROS topic, raw servo command or generated trajectory becomes a model tool.

R15 can show task applicability, evidence age/uncertainty, exclusions, intervention and unknown outcome. It may not turn a route overlay green as proof of safety or present ACK as success. MM-FUSION can contribute typed claims with complete shared-source lineage, not manufacture independent corroboration from a frame and its caption. R10's published documentary findings supply the stationary/ground/air comparison and persistent occupancy concern; its original unresolved CORE/R07 fields are not retroactively claimed closed by its author.

## Acceptance

Actual work: instruction/source reads, targeted public primary-source browsing, static synthetic-image inspection, document authoring and structural/hash checks described in VALIDATION.md. No application, model, simulation engine, robot, native phone, teleoperation, force, payload, privacy deletion, throughput or stop test ran. All experiments and AT records remain NOT_EXECUTED. Image smoke success establishes only the research agent's ability to inspect one static image.

R09-P0 is a useful proposed implementation milestone: 24 frozen replay cases, useful positive traces and adversarial lifecycle failures, independently protected oracle, zero actuator/network/model paths. Passing it would support only mock contract behavior. Later physics simulation must measure its own model gap; later bench work requires its own complete configuration and operator authorization.

## Risks and open questions

Physical freshness, speed/acceleration, force/contact, allowed payload/center of mass, stopping distance, retention, stability, cliff coverage, joint limits, collision envelope and recovery thresholds are deliberately unresolved until an exact task/apparatus is chosen and independently measured. They block physical qualification, not P0. Host RAM/VRAM, model latency, training time, delivered kit costs, spare-parts availability, exact runtime/dependency/data rights and local deployment permissions also remain unknown. Mutable web versions must be pinned before adoption.

## Next package

R09-P0 is AUTHORIZATION_REQUIRED and is not started by this handback. NEXT_PACKAGE.md contains concrete paths, scope, resources, owner/reviewer, prerequisite gates and completion criteria. The ambitious ladder remains fixed sensing -> supervised ground carrier -> bench skill -> separately qualified mobile manipulation -> tactile/event-camera/perching studies. No urgent assistance path depends on successful robot dispatch or learned inference.

