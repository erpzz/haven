# An engineering agent that designs, tests and improves physical tools

This is a first-class requested capability, not a decorative CAD feature. Haven should eventually notice a **measurable shortfall within an approved research goal**, propose a better design or experiment, help manufacture low-risk components, inspect the result and iterate. It must distinguish design prediction, simulation output and physical test evidence.

## A concrete first campaign

Goal: improve the repeatability of a small sensor's position in an authorized bench experiment. Baseline: current mount measured repeatedly against a reference. Candidate: a parameterized stand or jig. The engineering agent may propose dimensions and a test plan; an independent review checks fit, material, constraints and safe fabrication. An approved machine job produces the part. A person assembles and measures it. The next iteration uses actual measurements, not an AI-generated success story.

Initially automate only design bookkeeping, CAD generation in a sandbox, comparisons and analysis. Human handling/measurement is a valid closed-loop component. Later, a qualified robot can automate a narrow handling step under a standing campaign policy. The end goal remains useful real autonomy, but each physical operation earns its own capability.

## Campaign state machine

DRAFT_GOAL → REVIEWED_PROTOCOL → BASELINE_RECORDED → CANDIDATE_PROPOSED → DESIGN_CHECKED → FABRICATION_PROPOSED → APPROVED_JOB → FABRICATED → INSPECTED → TESTED → ANALYZED → ACCEPTED / REVISE / STOP.

Physical steps can be unknown or failed. A printer API job completion is FABRICATED_ATTEMPT, not INSPECTED_PASS. A reviewer model's “looks safe” is not a structural test. A simulated improvement is not a physical outcome. An accepted design records the exact part/material/process/assembly and the conditions under which it is qualified.

## Roles and authority

The experiment-planning worker defines candidate hypotheses under a user-approved objective. The design worker creates parametric CAD and predicted performance. A critique worker checks contradictions and missing constraints. The deterministic validator checks format, dimensions/allowed ranges, file provenance and budgets. A human or competent specialist approves physical risk. A dedicated machine gateway executes a bounded job. An observation/analysis worker reads physical evidence. The acceptance owner reviews results independently of the proposer.

These may be jobs in one coordinated system rather than seven always-running language models. Independence comes from evidence, permissions and review, not merely naming another model “critic.” No worker can lower its own pass criteria, increase machine power limits, modify firmware/interlocks, buy missing equipment or self-authorize the next fabrication.

## Artifact chain

Retain requirement/experiment ID, hypothesis, objective and constraints, CAD source and export hashes, dependencies/toolchain, material batch, orientation/process profile, slicer version and toolpath hash, approved machine profile, fabrication receipt, inspection measurements, raw test files, analysis version and decision. Link corrected artifacts rather than overwriting the failed attempt. Any changed load, material or mounting configuration can invalidate a prior qualification.

Use a programmable CAD tool as a candidate [R17]. Prefer editable dimensions and constraints over unexplained triangle meshes. Treat imported CAD/scripts as untrusted executable input; sandbox file and network access. A file that opens and slices can still be unmanufacturable or mechanically unsuitable.

## Printable hardware priorities

Good early targets: sensor stands, alignment fixtures, calibration boards/holders, handheld enclosures, cable routing, modular rover trays, communications-case inserts and storage organizers. They create inexpensive experimental repeatability.

Higher-risk targets—flight-critical structures, high-load joints, battery enclosures near heat, human-supporting devices, clinical parts or life-safety equipment—need separate material/process and domain review. Do not use a consumer printer to bypass missing qualified parts. Printed fixtures can also affect RF, airflow or optical calibration; test that effect instead of assuming plastic is invisible.

## Machine automation boundaries

OctoPrint is one documented control-interface candidate [R18], not a universal printer gateway. Investigate the actual printer/firmware/API, local operation, authentication, state, interruption and failure semantics before purchasing. Preserve the machine's independent protective mechanisms.

The permitted job must bind machine identity, exact file/profile hashes, bounded duration/material usage, reviewed operating setup and current operator authorization. The controller rejects arbitrary unreviewed toolpaths or commands. First-launch/restart must not resume heating/motion simply because an old job file exists. Network loss and operator cancellation need a manufacturer-appropriate safe policy, not an improvised generic relay cutoff.

The printer's camera is an observation aid. It cannot replace thermal protection, proper power installation, ventilation or operator procedure. No unattended printing is authorized by this starter.

## Bounded autonomy and resource accounting

A reviewed campaign declares allowed fixtures/materials/tools, an iteration ceiling, wall-time/cost/energy limit, noise/occupancy constraints, maximum storage, stop criteria and required supervision. Exhausting a budget is a stop or review point, not permission to invent cheaper unsafe material. A no-progress sequence should stop and explain competing hypotheses instead of looping forever.

Use a simple decision utility: expected information or performance gain minus cost, time, risk and privacy exposure. Compare against a human-designed baseline. Do not reward novelty of shape or number of iterations. A useful agent can conclude that no new part is necessary.

## Verification and scientific discipline

Pre-register metrics and hold-outs. Keep separate calibration and evaluation data. Instrument identity, measurement uncertainty and repeatability matter. Blind the final evaluation where practical, and reserve a test the optimizing agent cannot edit. Failed measurements, changed apparatus and outliers need documented handling, not retrospective deletion.

NASA generative-design work [R34], NIST autonomous-lab standards research [R13] and A-Lab's loop [R14–R15] are useful precedents. Their techniques and correction history motivate requirements, independent checks and retained raw evidence; none licenses a household agent to operate a hazardous lab. This branch begins with mechanical/electronic low-risk fixtures, not chemistry, medical experimentation or hazardous materials.

## Workshop readiness

Before purchase, define the first three intended parts and a complete workspace plan: ventilation/exposure control, location, noise, electrical safety, material handling, measurement tools, spares, maintenance and waste. NIOSH's guidance is the baseline safety reference [R19]. Ask Kennedy about shared-space impacts as well as digital consent. A printer purchase is a future decision, not already approved.

The acceptance goal is not “AI created an STL.” It is “a constrained engineering workflow produced a traceable artifact that measurably solves its stated problem, with safe stopping and honest failures.”
