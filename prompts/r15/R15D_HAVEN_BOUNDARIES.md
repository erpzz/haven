# R15D — Haven/GEV contracts, privacy and view-versus-action boundaries

Design a narrow integration between an Observatory frontend and Haven's evidence, context and domain services. Do not build a universal admin endpoint or replace the thin coordinator selected for investigation.

## Inputs

Pin https://github.com/erpzz/haven main; read root instructions, `coordination/R15_OBSERVATORY.md`, the full R15 prompt, issue #12 and `design/H02/R02/v1/CONTRACT_DESIGN.md` plus `design/H00/reviews/R02_v1.md`. Read available R03/H04 decisions and R15A/B/C outputs by exact version; treat absent ones as owner questions. Inspect the actual `erpzz/gods-eye-view` application, source, search, voice/action and server/provider seams and SECURITY.md at a separately pinned fork revision.

## Work

Specify three flows: public observation to evidence/view; authorized private record to scoped projection/publication; user intent to view operation, bounded analysis or separately governed action proposal. Establish authoritative owners and proposed producer/consumer contracts, failure semantics, deadlines, cancellation, grants/revisions, idempotency and outcome evidence. A renderer must not own consent, a scene URL must not restore a physical grant and a voice/model tool must not acquire arbitrary destinations or credentials.

Inspect private information potentially exposed by tile/viewport requests, geocoding, logs, referrers, browser keys, deep links, scene exports and model context. Define public wall-display, private desktop and shared field-view boundaries. Separate permission to display from permission to transmit to a provider. Resolve publication/revocation ordering with H04 rather than inventing an answer.

Compare integration without a new service mesh: existing Python boundaries plus a source-pinned JS frontend or sidecar. Account for lifecycle cleanup, same-origin/iframe limitations, shared model-server cancellation and source freshness. Existing synthetic schemas stay inert; propose typed successors only where necessary.

## Return and boundaries

Proposed output `design/H00/R15/inputs/R15D/v1/`: BOUNDARIES.md, CONTRACT_CROSSWALK.md, THREAT_MODEL.md and SUMMARY.md. Include a finite set of CR-R15 proposals, exact owners, proposed acceptance tests and the minimum subset for one public/synthetic demo. State which later private, paid and physical integrations need stronger gates.

No code, settings, grants, real user data, provider connections, model downloads, deployments, workflow runs or repository writes. A source read is not a security audit pass. Finish at review; do not enable mock flags or amend M0/NIGHT-01/M4.
