# Specialist handback

**R08 — Autonomous engineering, CAD, fabrication and closed-loop experimentation**

**Thread / owner / task ID:** R08 / H09 / R08-DESIGN-01. Integration H00; required reviews H04, H06 and affected physical-domain owners.

**Input repository version and hashes:** `HAVEN_ASTRA_Cumulative_Starter_v1.0.zip`, SHA-256 `55f693f64c56a9d8f13a6cd5725ab4c427af6ade2e127fe8e71829eca1f1d412`. All 146 files match the starter embedded in the later Tonight bundle. Also read the supplied research-prompt archive, the saved NIGHT-01 report and independent review, the H00/R02 integration review, and the actual archived N2 notebook source. Full identities and read scope: `INPUT_AUDIT.json`.

**Requirements covered (retain IDs):** REQ-ENG-01–10 and their existing AT-ENG-01–10; EX27 and EX28. Cross-domain changes are mapped in `INTEGRATION_AND_PACKAGES.md`. All 102 original requirements retain their IDs, owners and acceptance links; unmapped requirements are not removed.

**Actual work performed versus proposed:** Read-only archive inspection, primary-source research, byte/hash comparison and production of this documentation package. No CAD compilation, slicer run, model evaluation, N1/N2 test execution, physical measurement, purchase or printer/robot operation occurred. Every proposed experiment and capability test below is NOT_EXECUTED.

**Owned paths changed:** Only this new handback's output directory. Proposed integration destination is `design/H09/R08/`, subject to H00 review; no repository branch or persistent Library file was changed. Active M0 was neither accessed nor modified.

## Decisions

### D1. Build a campaign with bounded stages, not a general-purpose workshop agent

Use RA05 Engineering Investigator for proposals and RA06 Experiment Analyst for explanations around deterministic calculation. They are bounded jobs in the proposed H02 coordinator, not new always-running agents. H09 owns the experiment notebook and engineering artifacts. H04 owns authenticated authorization. H06 owns the frozen evaluation procedure and acceptance review. A physically present operator controls every heating/printing session.

The practical loop is:

**Measurable problem → frozen protocol → measured baseline → candidate → inspectable CAD → reviewed fabrication proposal → separately approved physical attempt → inspection → measurement → independent decision.**

A campaign can end successfully with “keep the existing mount,” “the measurement cannot distinguish improvement,” or “the proposed solution is worse.” Building a new part is not the objective. The proposer must identify a requirement gap, a plausible causal change, a cheaper alternative and a measurement capable of detecting the expected gain before consuming a fabrication budget.

Keep a single domain application/ledger initially, with typed modules. Separate processes only for a justified boundary: untrusted CAD/slicer execution, device credentials, or later measurement acquisition. Do not add a message broker, ROS deployment, vector database, universal shell, agent swarm or new model stack just to run a fixture campaign. Reuse H02's approved job ownership, budget and cancellation mechanisms rather than create a competing coordinator. The newer H00 review supports this direction but is a recommendation, not operational authority. [P4]

### D2. Reuse the real synthetic baseline without promoting it

The starter's fixture is explicitly a requirement-specification placeholder: dimensions are not measured; no CAD or toolpath exists. Its draft schemas are deliberately inert. The newer NIGHT-01 delivery adds an actual synthetic notebook, supplied candidate designs, fixed arithmetic score, separate software checker and review-only selection. Its `promote` function denies physical promotion. Static inspection here confirms those boundaries; earlier passing tests remain attributed to their original reports. [P1–P3]

The next change should extend provenance, measurement ingestion and CAD preparation through a reviewed, separate operational contract. It must not remove the notebook's synthetic labels, loosen its gate, replace its score with purported physical truth or flip a fabrication flag. Before any reusable CAD/model subprocess is introduced, resolve the reviewed R1 worker-lifetime issue on the approved runtime. A fenced late result and a stopped worker are different guarantees. Documentation work can proceed while that repair remains pending. [P2, P4]

### D3. Choose CadQuery as the first authoring path; retain two bounded alternatives

**Preferred: reviewed CadQuery template plus typed parameters.** CadQuery provides script-based parametric modeling and geometry exports suitable for interoperability. Its documentation explicitly says the exported exchange formats do not retain its full parametric definition; the Python source remains essential. Save that source and the exact parameters, not just STEP or STL. [S01–S02]

For the first campaign, a human-reviewed fixture template accepts only named dimensions, clearances and layout choices inside approved ranges. The model may propose values and explain them; deterministic code checks them. The first slice does not execute arbitrary generated Python. A later generative-code mode requires a disposable, resource-limited runner with no network, credentials, printer access, privileged mounts or package installation. A Python import allowlist alone is not a security boundary.

**Bounded alternative: OpenSCAD.** Its script-oriented solid modeling is a reasonable choice for a simple CSG fixture and easily reviewed parameter files. Prefer it when the chosen fixture needs only that representation and the owner favors its workflow. Do not maintain two generation pipelines in the first slice. Exported meshes are not a substitute for the source definition or engineering drawings. [S03]

**Human review / later analysis: FreeCAD.** Its parametric history, drawing tools and Python API make it a useful independent viewing/editing station. It is not selected as an unrestricted GUI-driving agent. FreeCAD and CadQuery both use OpenCASCADE, so a successful import into FreeCAD is an interoperability check, not fully independent geometric or mechanical validation. An optional FEM/solver workflow remains separately qualified; the FreeCAD FEM wiki could not be read in this session, so this package makes no exact solver-installation or version-compatibility claim. [S01, S04]

Pin the selected CAD application, geometry kernel, Python/runtime, dependency artifacts and export settings during the later installation/qualification package. Today's rolling documentation is not an installation lockfile, and this handback does not invent a tested version combination.

### D4. Produce an inspectable engineering packet, not a pretty mesh

Each design revision should contain a requirement and constraint manifest; editable CAD source and parameter values; source and dependency hashes; a dimensioned review drawing with datums and tolerances; STEP for geometric interchange; a fabrication mesh with explicit units and tessellation settings; an assembly description and BOM; expected mass and manufacturing estimates labeled as estimates; and a test-plan reference.

A geometry-only 3MF export and a slicer-project 3MF are different artifacts. Retain both when used. Do not infer printer settings from a geometry file. STL is an explicit fallback with a unit-bearing manifest and dimensional checks; it is not the only design record. CadQuery's documented STEP/mesh export support establishes interchange possibilities, not compatibility with an unselected printer. [S02]

Check positive dimensions, bounding envelope, valid solid topology, intended clearances, cable access, keep-outs, edge/handling hazards, assembly-tool access and reviewable support strategy. Compare critical dimensions after each format conversion. Validate paths and archive members before parsing; block external references and unexpected plugins. A successful render or mesh check earns only `GEOMETRY_CHECKED`, not structural acceptance.

Preserve raw bytes and their hashes. Rebuilding may change metadata even when geometry is equivalent. Define semantic reproducibility through critical dimensions/topology and stated numerical tolerances separately from byte identity; never silently replace an approved artifact because it “looks identical.”

### D5. Start with sensor reseating, and measure the measurement system first

The first useful target is a small, passive fixture that makes a sensor or mass-matched dummy repeatably return to a reference position. The actual sensor dimensions, mass, cable forces, datum features and sensing keep-outs are currently unknown. Measure them; do not treat the starter's inert dimensions as real hardware.

Start with an existing mount and a simple manual datum-stop alternative. A reviewed datum-based support, replaceable contact pad and cable strain relief are design candidates, not validated solutions. For the smallest campaign, claim only **one-axis reseating repeatability**. Use a separate displacement measurement, not the sensor under test as its own reference. If available metrology only resolves coarse motion, narrow the claim or stop; do not substitute an AI visual judgment for missing precision.

The proposed E01 protocol tests instrument adequacy, records a baseline, admits at most five candidate revisions and at most two human-approved print attempts, then evaluates one locked candidate on fresh held-out remounts. A proposed target is at least 30% lower reseating variation with absolute error and bias guards. These numbers are engineering trial assumptions awaiting H08/H06 approval, not a requirement inferred from an unidentified sensor. All thresholds are frozen before outcome data are examined. Full formulas, uncertainty handling and stop rules appear in `EXPERIMENTS_AND_ACCEPTANCE.md`.

NIST's gauge-study framework supports checking repeatability and reproducibility of the measurement process itself. Its use here is methodological; Haven has not established traceable calibration by citing a handbook. [S09]

### D6. Separate design, fabrication, measurement and acceptance authority

| Component | May do | Must not do |
|---|---|---|
| Engineering proposer, RA05 | Submit requirements, bounded candidate parameters, expected gains and next-test proposals | Edit locked objectives, approve a print, alter raw observations, certify its own design |
| CAD / preparation worker | Build reviewed templates, validate geometry, produce a sealed job proposal | Hold machine credentials, install dependencies, send G-code or change safety settings |
| Fabrication controller | Verify a specific authorized job and exact device state; collect truthful attempt receipts | Infer consent from prose, accept a different file under the same grant, declare inspection or qualification |
| Measurement system / recorder | Record attributed observations, calibration and uncertainty; retain failures and corrections | Manufacture missing values, use predictions as measurements, rewrite a candidate to improve its score |
| Independent evaluator and human acceptance owner | Recompute frozen metrics, review held-out evidence and issue a scoped decision | Accept by trusting the proposing model or silently redefine success after results |

These are authority boundaries, not a requirement for five microservices. For an initial human-mediated bench test, a human may operate the measuring tool; the observation records must say so. The independent acceptance owner must be distinct from the proposing runtime identity and control the protocol/checker. Ideally a separate reviewer assesses the evidence. When one person designed, operated and reviewed the part, retain that limited independence and label the result `OPERATOR_REVIEWED`; do not advertise independent mechanical qualification. A second LLM is not an independent acceptance authority.

### D7. Use supervised, manual-first fabrication with a narrow future gateway

**Phase 1:** offline slicing and an inspection packet; a human transfers and starts the exact approved file while present. No printer adapter is necessary to prove a useful measured improvement.

**Phase 2:** qualified read-only telemetry from an exact owned/borrowed machine. **Phase 3:** only after a separate machine-specific safety and authority review, a gateway may stage a job and accept a local, single-use start authorization while the operator is present. This progression never permits unattended heating/printing.

PrusaSlicer documents a command-line interface and print-instruction preview; it is a suitable preparation candidate, subject to an actual supported machine profile and pinned runtime. Disable network sending, unreviewed post-processing and imported custom executable behavior in the preparation environment. Do not assume any slicer brand is safe merely because it is open source. [S05]

OctoPrint exposes job status and start/cancel/pause operations. Crucially, a pause request without an explicit action defaults to toggling, which can resume a job. Use explicit job-bound semantics; never a generic “toggle” or automatic “restart.” Its broad printer-control interface is not an acceptable model tool. [S06–S07]

Moonraker documents separate print actions and direct G-code access, with many requests passed to Klipper. That is another possible device-specific adapter, not a safety arbiter. PrusaLink is a further candidate only if a future selected machine explicitly supports the required interface. No API choice establishes present ownership, interoperability, supervision or certified emergency-stop behavior. [S08, S19]

A sealed fabrication job binds final toolpath bytes, resolved start/end behavior, geometry, slicer settings, exact machine/firmware/configuration, nozzle, material/lot, orientation, quantities, operator, supervision window and budget. Any change requires a new review and grant. Unknown macros or commands cannot be allowed merely because a static scan found no familiar dangerous text. First qualification uses a tightly defined dialect and fully reviewed profiles; unfamiliar behavior is blocked.

### D8. Make unknown physical outcomes explicit and non-replayable

Keep separate records for `COMMAND_ACCEPTED`, `DEVICE_REPORTED_RUNNING`, `DEVICE_REPORTED_COMPLETE`, `FABRICATED_ATTEMPT`, `INSPECTED`, `MEASURED` and `QUALIFIED_FOR_SCOPE`. API acceptance is not proof that motion occurred; endpoint completion is not proof that the correct part exists; a physical part is not proof of fit or function.

Before dispatch, persist the intent, single-use grant and exclusive resource lease. If the gateway loses contact after dispatch, record `OUTCOME_UNKNOWN`, withhold new starts and preserve the reservation until reconciliation. Do not resend a start simply because a response was lost. Many consumer APIs do not supply transactional exactly-once execution; Haven must not claim they do.

Reboot, stale device identity, changed firmware, ambiguous selected file, failed supervision check or revoked start authority inhibits new physical actions. For an ongoing job, apply only the independently reviewed, device-specific safe-stop policy and notify the operator. Never assume network loss safely turns off heaters; never invent a universal relay cutoff that may disrupt required cooling. A pause may retain heat. Confirmed stop and confirmed safe handling temperature are separate observations.

Cancelling an AI job cancels computation and blocks new proposals; it does not magically stop an existing printer. Physical stop requests use the domain controller's separately authorized policy and report observed versus unknown outcomes. No automatic resume after application/device restart, consent restoration or budget renewal.

### D9. Use simulation as a screening instrument, not an acceptance shortcut

For a simple fixture, start with geometry checks and hand calculations. A beam-deflection estimate may help identify whether stiffness is a plausible limiting mechanism, but its loads, supports, elastic assumptions and material properties must be explicit. Move to finite-element analysis only when a defined decision benefits from it.

A simulation artifact records geometry and mesh revisions, boundary conditions, loads/units, solver/version, material assumptions, convergence checks and sensitivity analysis. Printed specimens can differ from ideal bulk materials and from one process configuration to another; do not accept an isotropic material number selected by the model as a measured property. Keep predicted and measured results side by side and retain discrepancies.

NASA's evolved-structures guide distinguishes optimization models, detailed analysis, fabrication and inspection, including refinement/convergence considerations. It is evidence for a disciplined separation of stages, not a consumer-printer standard or flight certification pathway for Haven. No NASA safety factors or approved-material status are transferred to this fixture. [S11]

### D10. Gate hardware and household operation before spending

The supplied records establish existing personal computing hardware as reported project context; no printer, metrology kit or workshop robot is established as owned or qualified. A local CAD trial should start with a small CPU-only resource envelope on the reported desktop after permission and fresh capacity checks. No GPU/model purchase is justified for fixture bookkeeping or deterministic CAD.

Do not buy a printer to discover whether there is a useful problem. First identify three genuinely useful parts, establish their dimensions/tolerances/material and maximum envelope, compare a manual/borrowed/service option, and obtain a complete workshop plan. A service bureau still needs human purchasing authorization, confidentiality review and incoming inspection; it is not a way around approval.

The purchase packet must include the exact model/revision, vendor-supported local interface, full machine/material/inspection/tooling/ventilation costs, consumables and spares, maintenance burden, replacement part availability, supported firmware policy, warranty constraints, placement, electrical supply, noise and supervision availability. Quotes must be dated at that future gate; this handback gives no current retail prices or authorization to order.

Both residents independently consent to relevant shared-space effects and recordings. Workshop suitability is not inferred from ownership of an apartment or a printer enclosure. NIOSH documents emission and other hazards and controls that depend on process and setting. No printing material is assumed emission-free, and a camera is not a substitute for ventilation, appropriate placement or an attending operator. No resin, solvent process, hazardous material, mains modification, medical device or safety-system component enters the initial campaign. [S10]

### D11. Protect privacy, evidence and ordinary daily utility

Private goals, household imagery, dimensions of living spaces and prototype files retain subject, owner, audience and purpose labels. Use synthetic or cropped object-only evidence where practical. Shared-space permission is distinct from permission to send a photo or CAD packet to a hosted model. Recheck grants and revisions before retrieval, model egress, publication and fabrication authorization. Revocation prevents future eligible use; previously delivered files cannot be promised to be recalled.

Raw readings are append-only with attributed correction records. Derived results reference exact source revisions and are invalidated when a correction or relevant revocation changes their basis. Do not leak another user's project metadata through error text, caches or omission counts. Host-administrator access is a real trust limitation; a local file ACL does not cryptographically isolate data from the machine owner.

Retrieved instructions, CAD comments, slicer projects, model text and imported metadata are untrusted data. No source can grant itself a tool, higher budget or printer permission. Separate log identity from display authorship, and redact credentials and irrelevant household data from export packets.

Use no model for unit conversion, hashing, eligibility, arithmetic or budget enforcement. After qualification, a local model may interpret a failure and propose a small parameter change; hosted inference requires separate data and spending eligibility. A stronger model gets no additional permissions. Defer low-priority engineering work under contention so normal assistance and independent alarm/communication paths remain usable.

### D12. Scale by preserving the loop, not by increasing blanket autonomy

| Next application | Reused pattern | New evidence/gate |
|---|---|---|
| Handheld sensor | Datum references, source CAD, BOM, strain relief and repeatability test | Grip/handling, sensor field of view or RF impact, cable access, heat and recalibration; passive mock first |
| Rover-mounted sensor | Reviewed assembly, physical specimen ID, measured transform | H10/H08 payload retention, vibration, center of gravity, collisions and pose drift; no inferred safe navigation |
| Ground lighting bracket | Approved module mount and inspection | Heat clearance, glare, tip resistance and cable routing; no mains or safety-light redesign |
| Electronics enclosure | Keep-outs, tolerances, assembly and lot traceability | Thermal/RF/ingress tests appropriate to stated use; geometry alone establishes no electrical or weather rating |
| Drone-related accessory | Ground fixture/transport aid/controller stand | H05 consequence review; anything flight-mounted gets separate mass, interference, retention and flight-risk analysis |
| Later robot-assisted workshop | Specimen custody, measurement stations and finite jobs | H10-qualified handling of already cooled, passive objects in a controlled cell; no hot-part removal or automatic print restart |

“Non-flight-critical” is a consequence assessment, not a label attached by the designer. A small accessory can obstruct a propeller, alter balance or fall away. Initial drone-related fabrication stays on the ground. Daily assistance, wearables, RF/world-model research, aircraft, emergency communications and robotics remain separate retained branches.

## Evidence

### E1. Capability maturity

| Maturity | External or project evidence | Haven disposition |
|---|---|---|
| Available now | Parametric CAD tools, offline slicers and device APIs are documented; the submitted N2 notebook is running synthetic software | Research evidence / synthetic baseline only; no owned-printer or CAD qualification claimed |
| Feasible prototype | Template-driven design, sealed fabrication packet, supervised manual build, independently recorded bench measurements | Recommended first real capability; requires sensor/metrology facts, permissions and actual testing |
| Research-stage | Text/point-cloud-to-CAD, diagnostic-guided optimization, experimental sensor-driven process tuning, robot-assisted experimentation | Evaluate narrowly against deterministic/human baselines; no direct adoption or assumed transfer |
| Speculative for this system | Broadly capable self-directed workshop that invents and validates arbitrary devices | No evidence in this package; not a milestone or authority grant |

The reviewed Text2CAD and CAD-Recode work demonstrates progress toward editable CAD generation/reconstruction, not fabricated fitness. The 2026 Text2CAD-Bench preprint broadens text-to-CAD evaluation and reports remaining difficulty on complex tasks. Samani and Atkeson's March 2026 preprint supports modular diagnostic-driven proposals, but its quantitative comparisons use an approximate evaluator; physical examples are a qualitative subset. Guidetti and colleagues report an actual sensor-guided printing experiment in a specialized material/process setting. These are different evidence classes, not a single claim of general autonomous engineering. [S12–S16]

NIST's autonomous-laboratory work addresses interoperability across instruments, samples, control and data. It is a standards-development effort, not an asserted finished standard that this design implements. Berkeley's A-Lab is a specialized materials-synthesis example, not a household fabrication recipe. Its associated 2026 author correction is listed in the source register; the correction's full text was inaccessible here, so this handback does not repeat unreverified synthesis or novelty counts. [S17–S18, S20]

### E2. What was actually checked here

Verified source ZIP hashes, CRC integrity, the 146-file starter/Tonight byte comparison, exact contract restrictions and the static N2 source. Read public primary sources; for the NIOSH and NASA PDFs, inspected relevant rendered pages as well as text. Generated and checked only documentation artifacts. No runtime or mechanical acceptance follows from these checks. Detailed primary findings, access limitations and dates are in `SOURCES.md`.

## Interface changes

Five **proposed** change requests are specified in `INTERFACES_AND_CONTRACTS.md`: campaign/protocol authority; design/assembly/BOM lineage; measurement/calibration/evidence; sealed fabrication jobs and outcomes; independent decisions and qualification envelopes.

The affected starter schemas are `agent_job`, `experiment`, `design_artifact`, `evidence`, `spatial_estimate`, `physical_action_proposal` and `capability_qualification`, plus scoped context/consent references owned by H04/H02. Their v1 restrictions remain unchanged. Operational records need separately reviewed versioned types and semantic enforcement, not new enums smuggled into the frozen fixtures. `delivery_receipt` remains a communication concept; do not repurpose it as printer success. M0 request and receipt semantics remain untouched.

## Acceptance

The authoritative existing AT-ENG-01–10 remain NOT_EXECUTED for physical/native capability. The proposed R08-T01–20 specialization in `EXPERIMENTS_AND_ACCEPTANCE.md` covers tampering, self-approval, units, holdouts, data integrity, stale identity, unknown dispatch, lifecycle failure and protected resource budgets. Previous N2 tests provide reusable evidence only where an exact case/source comparison supports equivalence; they do not satisfy new CAD or metrology requirements by name alone.

Accept this document, if appropriate, as a **design recommendation**. Separately approve each coding package, software installation, model evaluation, hardware purchase and physical campaign. A result can be `FAIL`, `INCONCLUSIVE`, `STOP_NO_NEED` or `QUALIFIED_FOR_SCOPE`; none permits automatic fabrication of another part.

## Risks and open questions

The material blockers are the actual sensor/application tolerances; an adequate independent measurement arrangement; the owner-approved latest N1/R1 state; H04/H06 acceptance of operational authority semantics; and a suitable supervised fabrication workspace if printing becomes necessary. These block their respective stages, not this handback or ordinary Haven utility.

A second acceptance identity must be established before claiming independent physical qualification. Printer/firmware/profile choice remains intentionally open until geometry and workspace needs are known. Local model ability, CAD compile resource demand, slicer compatibility, mechanical durability, RF/optical effects and robot handling remain unmeasured. No cloud service is eligible through this document.

Maintain uncertainty rather than manufacturing requirements or test results. Failed source access is recorded. General workshop autonomy and hazardous or safety-critical applications remain outside this proposal.

## Next package

**R08-P00: owner-approved documentation reconciliation and contract decision packet.** Inspect the designated current lab snapshot and any accepted R1 result; map existing N2 cases and the five proposed contract changes to exact evidence and owners. Proposed files live under `design/H09/R08/`. No M0 changes, synthetic-gate loosening, executable CAD, model download or physical adapter.

Success is a reviewed source-to-requirement/test crosswalk and an explicit accept/amend/defer decision for the minimal next slice. Suggested human effort is 0.5–1 engineering day, not an automation run-time promise. Authorized provider spend and purchases remain $0. A later P01 can add only the approved inert provenance/measurement gaps; CAD preparation and supervised bench work each need their own gate. The package sequence and exclusions are in `INTEGRATION_AND_PACKAGES.md`.

**Stop here for H00/H04/H06 design review. No next package is started.**