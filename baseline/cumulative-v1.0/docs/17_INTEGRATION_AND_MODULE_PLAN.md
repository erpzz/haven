# Proposed integration structure — not a rewrite of M0

The starter is a separate planning/research repository. No current application files are present or inferred. The lead agent must inspect the actual application read-only when Eric supplies a path and authorizes that inspection, then propose the minimum integration diff.

## Logical modules for the eventual application

| Boundary | Owns | Must not own |
|---|---|---|
| identity/consent | Principal sessions, grants and privacy-filtered scope | Clinical interpretation or raw actuator commands |
| conversation/context | Turns, bounded retrieval, user-visible explanations | Canonical measurement truth or permission changes |
| daily_tasks/connectors | Drafts, schedules, provider-specific action receipts | Aircraft execution or robot privileges |
| evidence/spatial | Provenance, transforms, freshness, estimates and corrections | Invented observations from plausible generated images |
| model_router | Eligible-model selection, budgets and inference accounting | Expanding data-sharing grants or physical authority |
| incident/policy | Existing protected domain records and reviewed gates | Everyday task states forced into OUTSIDE_CHECK |
| mission/embodiment | Qualified resource scheduling and bounded execution contracts | Arbitrary model-supplied network/device destinations |
| research/campaigns | Protocols, artifacts, iterations, raw data, evaluations | Self-approval of changed pass criteria |
| fabrication_gateway | Qualified machine jobs and observed machine state | General shell access or automatic arbitrary toolpaths |
| operations | Health, backup, readiness and maintenance | Treating unavailable components as functioning |

These are logical boundaries. Start with the smallest practical application and add separate processes/accounts only for defined isolation, contention, or reliability requirements. The existing simulator namespace requirement remains unchanged. Printer/robot/device gateways eventually need their own qualification; they do not belong inside a conversational model process.

## First integration sequence

1. Compare the active M0 report and source with the approved receipt requirements; mark missing evidence pending rather than restarting it.
2. Resolve shared evidence/principal vocabulary as a proposed contract revision, not an immediate database migration.
3. Propose a small daily-use increment that can use synthetic data before connecting personal accounts.
4. In parallel, permit one separately approved read-only research/benchmark or synthetic engineering experiment in its own workspace.
5. Land independently reviewed changes one at a time. Each change has rollback, an acceptance target and an owner; no entire-system big-bang merge.

The branch plan should normally preserve app/, tests/ and existing migrations as actually found. Do not create new folders with these names over the original workspace merely because this document lists modules.

## Contract evolution

Schemas in contracts/ are DRAFT reference shapes. Unknown/error/proposed are first-class states. They are not an API server or production authorization implementation. The consuming work package defines transport, identity, time parsing, units, persistence, database constraints and access control before implementation.

A contract amendment includes affected requirement IDs, old/new schema hashes, compatibility and migration analysis, privacy/authority implications, positive and negative fixtures, and owner review. A field added for one sensor must not silently expose it to every household user or cloud model.

## Parallel ownership

Each coding package runs in a separate approved branch/worktree. Shared schema changes are proposed to H00 rather than edited concurrently. H06 reviews test independence, not just green output. The current local Codex thread remains M0's owner until Eric changes that explicitly.

## Promotion evidence

A module is eligible for integration when its exact inputs and permissions, executed tests, unresolved assumptions, dependency identities, failure/rollback behavior and operator/device-dependent checks are recorded. Simulator and fixture results do not substitute for physical acceptance. A change can be useful while still clearly marked experimental.
