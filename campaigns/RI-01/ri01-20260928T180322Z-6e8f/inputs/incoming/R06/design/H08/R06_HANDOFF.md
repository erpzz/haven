# Specialist handback

Thread / owner / task ID: **R06 — RF/Wi-Fi Sensing, Presence, Localization & Through-Wall Spatial Research / H08 / R06-DESIGN-001.** Integrator H00; independent review H06; consent/authority review H04. Date: 2026-09-28 UTC. Status: **DESIGN_PROPOSAL — ready for integration review, not accepted or qualified.**

Input repository version and hashes: **HAVEN_ASTRA_Cumulative_Starter_v1.0.zip**, SHA-256 `55f693f64c56a9d8f13a6cd5725ab4c427af6ade2e127fe8e71829eca1f1d412`. The attached **HAVEN_Research_Thread_Prompts_v1(2).zip**, SHA-256 `78794dc12f03c905811a8dddb7cf51de700dcb72a221196c4375458b52ae79df`, contained research prompts rather than the repository. The named cumulative starter was located among supplied project files and read separately. Its required context and actual `agents/HANDOFF_TEMPLATE.md` govern this handback. Per-file input hashes and required-read coverage are in [INPUT_AUDIT.json](INPUT_AUDIT.json). No more recent live application state is inferred from this archived starter.

Requirements covered (retain IDs): **REQ-RF-01 through REQ-RF-10**, with corresponding **AT-RF-01 through AT-RF-10**. Parent experiments EX09–EX12, EX14 and EX15 are retained. Detailed proposed register rows are in [INTEGRATION_AND_PACKAGES.md](INTEGRATION_AND_PACKAGES.md). All other cumulative branches remain in scope.

Actual work performed versus proposed: read the starter and relevant branch/contracts/research context; reviewed current primary public documentation and papers; wrote architecture, field-level interface proposals, staged protocols, source findings and future package definitions. Extracted inputs and performed document/hash checks. **No implementation, RF capture, dataset benchmark, native/phone test, physical test, trained model, hardware purchase or device/account connection. No additional agents.** The active M0 workspace was neither supplied nor accessed; no M0 test result is claimed.

Owned paths changed: new standalone documentation under **`design/H08/`** in this delivery, plus delivery-only README and integrity manifest. The extracted starter remains byte-for-byte unchanged. No shared contract, root project document, baseline pin or application file was edited. These are proposed integration artifacts, not a merged repository change.

## Decisions

**Recommendation:** accept the local, replay-first design in [ARCHITECTURE.md](ARCHITECTURE.md). Start with evidence integrity and honest motion/unknown semantics; use cooperative ranging for enrolled-device localization; preserve geometry and semantic understanding as explicit later targets. Presence is useful infrastructure, not proof the same radio can reconstruct a room.

The [one-page integration summary](INTEGRATION_SUMMARY.md) is the concise handback for H00. Supporting documents are indexed in the delivery [README](../../README.md).

Prefer a fixed documented CSI configuration for the first eventual acquisition study. A qualified mmWave presence sensor is a bounded alternative if still-presence utility matters more than CSI research. Phone-only capabilities are conditional on actual platform APIs. Phone/accessory, handheld, fixture, rover and drone arrangements remain distinct options. Buy nothing at this gate; the shortlist and planning ceilings are contingent, not quotations or spending authority.

Logical boundaries are acquisition → admission/calibration → scoped evidence → estimator → R07 projection → finite next-observation proposal → authenticated authority/domain execution. Deterministic code owns permissions, time, transforms, budgets and basic analysis. Use a qualified small local model only for measured benefit; hosted reasoning receives only privacy-eligible minimized material. No unrestricted agent or shell is proposed.

Preserve measured support, inferred structure, learned completion, historical information and unknown areas as separate representations. Every estimate remains unsuitable for a safe-route claim. An RF silence, device position or generated image cannot establish room emptiness, personal identity or a safe action.

Required future approvals belong to specific gates: H00 contract reconciliation; H04 policy and data scope; H06 frozen protocols and independent qualification; operator authorization of a bounded coding package; later exact equipment/site/participant authorization before acquisition. None is requested as a prerequisite to completing this already authorized design task.

## Evidence

[EVIDENCE_REGISTER.md](EVIDENCE_REGISTER.md) contains **22 primary-source records**, dated 2026-09-28, with document/version access and limits. Key decisions trace to:

- R06-S01/S22: IEEE 802.11bf publication and sensing-procedure scope; standardization does not establish installed hardware/API availability.
- R06-S02–S09: documented CSI, phone ranging/direct-view APIs and accessory/radar paths; exact owned hardware and native behavior remain unqualified.
- R06-S11–S17: tomography, diffraction, RF pose and recent geometry/scene reconstruction; specialized apparatus, priors, data and evaluation constrain applicability.
- R06-S18/S19: dataset corrections, differing license statements and restricted-use terms keep measured-data work conditional.
- R06-S20/S21: exact UWB operating category and aircraft restrictions are gates, without generalizing them to all Wi-Fi/radar sensing.

Not all sources were fully accessible: Apple TN3111 was checked through its official indexed excerpt; the final IEEE standard PDF and RISE proceedings file were not retrieved. RISE analysis uses the read v1 preprint. Mutable repository/SDK pages were reviewed but not pinned to build commits. No author benchmark was reproduced, dataset downloaded or price verified. These limitations are retained rather than hidden behind a broad “state of the art” claim.

Executed local operations used `rg`, file reads, ZIP inspection/extraction, SHA-256 comparison and Python 3.12 standard-library document checks. No project code or starter tests were run. Exact verification commands and scope are retained in [VALIDATION.md](VALIDATION.md), with [VALIDATION.json](VALIDATION.json). These results establish package integrity only.

## Interface changes

[CONTRACT_PROPOSALS.md](CONTRACT_PROPOSALS.md) defines the proposed producer/consumer boundaries, fields, units, errors, expiry and retry semantics. Its draft namespace is `urn:haven:r06:proposal:<name>:1`; current shared `urn:haven:draft:*:1` remains unchanged.

`RFObservationBatch` carries profile/device revisions, boot/sequence identity, original capture and receipt clocks, path context, quality, typed payload and access dependencies. `FrameTransform` and `CalibrationRecord` bind metric frames, normalized quaternions, covariance convention and validity. Mandatory `SpatialSemantics` pairs with the legacy estimate by ID/hash and supplies unknown/availability, typed topology, support masks, freshness and uncertainty coverage. Legacy-only callers must receive an unavailable result rather than a fabricated point.

`ObservationProposal` names a finite candidate, exact profile, scope, budget, expiry and cancellation scope. It is not authority. `ObservationOutcome` distinguishes acknowledgement from admitted observation and an unknown outcome. Retrying uncertain effects requires reconciliation; acquisition and carrier movement need separate authorization. R06 cannot invent live leases or grants from the inert starter's mock/proposal records.

Five change requests go to H00 and relevant owners: **CR-R06-01** spatial semantics; **02** multi-subject/public-data scope and lineage; **03** observation authority; **04** runtime lifecycle; **05** qualification/result successors. There is no M0 API/database integration in this package. Concrete R07, H04, H09, H10/H05, H02 and daily-assistant links are specified in the integration document.

## Acceptance

| Check / protocol | Expected result | Actual state / evidence | Reviewer |
|---|---|---|---|
| Documentation package integrity | Required sections, resolving internal links, complete source/requirement mapping, unchanged starter | Executed document checks; exact results in VALIDATION.json. Not RF or M0 acceptance. | Author check; independent review pending |
| AT-RF-01 / AT-RF-06 | Beyond-heatmap scope and distinct carriers retained | Addressed by design; system acceptance **NOT_EXECUTED** | H00/H06 |
| AT-RF-02 / AT-RF-03 | Held-out motion/presence and framed localization against ground truth | E1–E3 **NOT_EXECUTED** | H06 |
| AT-RF-04 / AT-RF-05 | Supported geometry, semantic abstention, no generated-as-measured output | E4/E5 **NOT_EXECUTED** | H06 |
| AT-RF-07 / AT-RF-08 / AT-RF-09 | Origin, time/frame/calibration integrity and budgeted adaptive views | E0/E4 **NOT_EXECUTED** | H06 |
| AT-RF-10 | Deny unapproved sensing/area/profile and enforce revocation | Future policy/physical tests **NOT_EXECUTED** | H04/H06 |

[EXPERIMENTS.md](EXPERIMENTS.md) freezes proposed hypotheses, baselines, ground truth, grouping, metric definitions, resource caps and stop conditions. E0 is synthetic software semantics. E1 is conditional licensed-data motion research. E2/E3 require independent acquisition authorization. E4 is the ambitious controlled-geometry experiment; E5 preserves room-level semantics. All real-device capability qualification remains unknown/documented-only and ineligible for physical execution.

## Risks and open questions

Technical uncertainties: exact phones/OS/accessories, accessible raw fields, oscillator/array/pose calibration, still-person observability, multipath/domain shift, sparse geometry, and current host/GPU capacity. Exact source pins and build environments are deferred to the selected coding package; no implementation stack has been installed.

Privacy/authority uncertainties: sensing footprints can cross property/room boundaries; cropping an output is not containment. Both household principals, other participants and affected areas require their own valid scope. Public dataset availability alone does not settle licensing or participant provenance. Background/native behavior and grant revocation need qualification. No private training or personal identity inference is proposed.

Security/maintenance risks include malformed samples, spoofed sources, replay, dropped/late packets, hidden calibration drift, deleted-parent derivatives and unknown physical outcomes. Typed errors, authentic transport, immutable lineage, bounded buffers, abstention and separate recovery owners reduce but do not eliminate these risks. An RF signature is not authenticated identity.

These issues block live sensing, useful geometry claims and physical promotion. They do **not** block a separately authorized synthetic P0. A failed or inconclusive experiment should narrow the claim or end that path, not trigger unrestricted data collection, hardware escalation or endless research.

## Next package

**P0 / E0 — typed synthetic replay integrity**, H08-owned in a future isolated research checkout: `research/r06_replay/`, `tests/r06_replay/`, `design/H08/results/P0/`. First reconcile CR-R06-01 and synthetic bindings with H00; H06 freezes protected cases. Do not touch the active M0 application.

One eight-hour engineering package; one CPU worker; at most 4 GiB RAM and 1 GiB artifacts; $0 new hardware or hosted inference. Sixty synthetic episodes, finite candidates and equal budgets compare fixed/random/deterministic adaptive selection. Zero unauthorized selections, fabricated coordinates, false freshness or post-revocation disclosure; preserve every failed case. Adaptive performance is a separate optional promotion gate. Stop at budget or integrity failure and return evidence.

Requested permission for a future run: authorize **only P0 after design review**, if desired. **No implementation is started or permission assumed here. This R06 task is complete at the design/research handback gate.**
