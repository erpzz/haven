# R12-P01 — Small synthetic geometry evidence package

**AUTHORIZATION_REQUIRED. PROPOSED_NOT_EXECUTED.** R12 authoring and independent review do not authorize coding, model execution or device activity.

Owner: H08/R07 for observation semantics, H00 for shared schema integration. Review owner: a different H06/R13 validation agent plus the responsible H08/H00 contract owner. R12 author cannot independently approve this package.

Why useful: a selected-image answer can distinguish predicted shape from measured dimensions and explain which permissible next observation could resolve uncertainty. This is a small precursor to canonical EX09/EX15/EX17/EX31 and does not qualify a physical experiment.

## Exact inputs and prerequisites

Freeze reviewed R12 REPORT.md, OPPORTUNITIES.json, INPUT_USE.json and source register at the hashes in HANDOFF_MANIFEST.json. Also consume the exact REV-R06 REVIEW/SOURCES and VISION-0 canonical paths/hashes in INPUT_USE. Before implementation, R07/H00 must choose and freeze the actual Observation/SpatialSemantics schema ID/hash/version; the scout does not invent the final schema. Review current CORE/R03/P01 bindings if their authority objects are exercised; unresolved finite-grant semantics stay out of this slice.

Source-specific VGGT examples need only the documented coordinate convention. No code, weights or dataset needs downloading. If owners later want an actual model adapter, that is a separate package requiring exact immutable source/checkpoint hashes, applicable code/weight/data rights and host resource qualification.

## Allowed paths and implementation boundary

Proposed sandbox namespace: `research-prototypes/R12-P01/` in an owner-approved isolated worktree, with a schema-note file, static JSON cases, a small standalone validator and its tests. The path is a proposal, not current write permission. Do not edit existing runtime/domain contracts, M0, model registry, scheduler, consent engine, device drivers or deployment configuration. No Git publication delegated here.

Ready-to-paste future assignment:

> After explicit authorization and H08/H00 schema selection, implement only the offline R12-P01 fixture validator under the approved prototype prefix. Reuse the frozen paired SpatialSemantics contract. Create twenty synthetic cases covering the matrix below, preserving inferred/measured/historical class, source dependencies and unknown metrology. Emit structured results and retained failure records. Do not install dependencies, call models, access networks/devices, alter production schemas or run physical commands. Stop at the stated ceiling and hand the complete result to an independent reviewer.

## Finite case matrix and expected tests

Exactly20 cases, each with a precommitted expected verdict and owner-reviewed rationale:

1. Four frame/unit cases: valid parent-from-child transform, inverse-convention mismatch, quaternion ordering mismatch, incompatible length units.
2. Four metrology cases: measured scale with known calibration, unknown scale, stale calibration, learned confidence falsely presented as covariance.
3. Four provenance cases: independent measured sources, two derivatives of one image, explicit optical prior in RF inference, historical revision incorrectly offered as current.
4. Four support/time cases: supported region, extrapolated region without support, stale capture time despite new processing time, clock uncertainty exceeding comparison tolerance.
5. Four next-observation cases: eligible request, no eligible view, revoke before admission, exhausted60-second/eight-attempt episode.

Baseline: static owner-approved table lookup. Candidate: typed validator against the same cases; no learned geometry inference occurs. All error cases must produce the specified rejection/unknown result; valid cases must preserve every relevant provenance and frame field. Measure false admission, false rejection, missing-field preservation and total CPU time, memory and output bytes. A perfect score qualifies only these synthetic semantics. No accuracy on real geometry, closed-loop information gain or physical stopping is inferred.

Have H06 prepare or conceal four additional mutation cases after the author freezes the validator, within the total resource ceiling; record them separately as holdout tests rather than quietly adding them to the original20. This does not grant the author access to evaluator internals. Unexpected failure stays in the record; no benchmark-targeted revision without a new version and fresh review.

## Cost ceiling and stops

Proposed maximum90 minutes implementation and30 minutes independent review, one existing workstation CPU core, peak process memory512MiB, output records10MiB, no binary datasets/models, no packages/accounts/subscriptions, zero new purchases, zero paid calls. These are ceilings, not measured estimates. Existing host energy is UNKNOWN until metered; record wall time and available resource observations honestly. No new private assets; campaign asset budget consumption remains0 bytes.

Stop immediately on a need for a model/package/device/network service, missing final schema, rights ambiguity requiring artifact reuse, accidental write outside the prototype, a disclosure or physical-command path, or any resource ceiling. Return the partial record and blocker rather than widen scope.

## Acceptance and later progression

Acceptance requires independent review of the frozen validator/cases, zero unjustified admission, preserved negatives/unknowns and clear source-versus-measurement labels. It does not approve a scientific hypothesis or qualify Haven generally. A later model-specific replay, active-view simulation, RF acquisition, human interface or embodiment experiment needs a separate exact package and authorization.

