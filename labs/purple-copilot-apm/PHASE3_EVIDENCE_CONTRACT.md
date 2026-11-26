# Purple Copilot APM — Phase 3 offline evidence contract (proposal v1)

> Status: **PROPOSED / NOT_EXECUTED**. Documentation-only engineering contract. No adapters installed, no live sources connected, no additional model experiments, no credentials, and no runtime changes are asserted by this PR.

## 0. Scope and review handback

- Workstream: Purple Copilot APM, blue/purple identity exposure management; owner decision pending.
- Repository: `erpzz/haven`.
- Exact reviewed base: PR #109, `feat/purple-apm-path-evidence`, commit `6a07130f3ed1b7e1aca987eb38e42cc6652c53cb`, itself stacked on PR #108.
- Read: `AGENTS.md`, `PRECEDENCE.md`, `START_HERE.md`, `coordination/PROTOCOL.md`, PR #108, PR #109 and `PHASE2.md`.
- Allowed change: this single public-safe proposal under `labs/purple-copilot-apm/`; no modification of existing behavior, schema or requirements.
- Publication: all IDs/examples below are intentionally synthetic. No tenant exports, source graphs, private telemetry, local inventory or credentials.
- Review decision requested: accept/amend/defer the offline evidence schemas, join semantics and test gates before any live integration work.
- Tests: **NOT_EXECUTED**. The table below is a proposed acceptance plan, not a test report. No runtime evidence is published in this document.
- Dependencies: PR #108's historical secret-alert disposition and PR #109's independent review remain separate. Do not rewrite published commits or merge either PR without operator approval.

## 1. Decision: deepen blue-team evidence before enabling another agent framework

Do **not** immediately turn on Microsoft Graph, Azure ARM, remote AI, tenant-wide scanning, Sentinel forwarding or BloodHound extension writes.

The smallest useful Phase 3 implementation is a **purely offline, deterministic importer** of:
1. EntraOps **already-classified** Privileged EAM / BloodHound OpenGraph exports.
2. Maester **already-produced** JSON test results plus optional affected-object exports.

The importer must run without Microsoft credentials, PowerShell, BloodHound, or an LLM. Both adapters feed a new provenance-preserving enrichment store, not the authoritative path-history lifecycle. Tests must be able to run on a small Linux CPU host with no model loaded.

Why: EntraOps is a privilege/assignment-context overlay on AzureHound, while Maester independently evaluates posture. Neither should silently create, remove or certify the directed membership paths tracked in Phase 2.

Primary upstream references, checked 2026-11-21:
- EntraOps BloodHound integration: https://github.com/Cloud-Architekt/EntraOps/blob/main/Integrations/BloodHound/README.md
- EntraOps deployable schema: https://github.com/Cloud-Architekt/EntraOps/blob/main/Integrations/BloodHound/OpenGraph_EntraOps_Extension_Schema.json
- Maester 2.x stable docs: https://maester.dev/docs/2.x/intro
- Maester 3.0 preview result schema (NOT the 2.3 stable contract): https://maester.dev/docs/result-schema
- Maester affected objects and redaction: https://maester.dev/docs/export-results
- Existing internal contract: `PHASE2.md` in PR #109.

**Versioning guard:** the Maester website currently presents 3.0-preview schema details while offering 2.3.0 stable. The importer must detect actual exported shape and reject unknown incompatible variants. In particular, do not assume preview-only `SchemaVersion`, `CatalogVersion`, `Severity` or affected-object shape exists in all 2.x results. Preserve unknown fields as source evidence rather than guessing their meaning.

## 2. Separation of truth and inferred risk

| Layer | Source of truth | May do | Must not do |
| --- | --- | --- | --- |
| Directed graph membership | BloodHound + independently acquired membership inventory | Verify documented edges and paths | Infer privilege solely from labels |
| EntraOps classification | Classified EAM export, preserved verbatim | Attach tier, role-system, active/eligible and assignment context | Treat eligibility as active role execution |
| Maester posture | Test-result JSON and optional affected-objects artifact | State that a particular check passed/failed/was skipped at a particular time | Assert an attack path exists or was remediated solely from a test result |
| Correlation engine | Typed stable-key joins with provenance | Produce contextual overlays and deterministic review flags | Silently merge different tenants, runs, IDs, or RBAC systems |
| Local model | Bounded immutable evidence from the above | Interpret and propose validation/remediation hypotheses | Write source facts, change lifecycle, invoke unrestricted tools or certify closure |

Terminology: the 27 findings documented in Phase 2 are **directed membership paths**, not yet general Azure/Entra compromise or effective access paths. Reports must retain this distinction.

## 3. Canonical evidence envelope (proposed)

Each imported artifact has:
```json
{
  "contract": "purple-apm-evidence/v1",
  "source": "entraops",
  "source_schema": "unverified-pinned-version",
  "dataset_id": "synthetic-tenant-a",
  "origin": "offline-fixture",
  "producer_revision": "pin-in-lockfile",
  "source_run_id": "synthetic-run-003",
  "collected_utc": "2026-11-21T12:00:00Z",
  "received_utc": "2026-11-21T12:02:00Z",
  "artifact_sha256": "<sha256-of-exact-input-bytes>",
  "complete": true,
  "coverage": {"domains": ["entra"], "partitions": ["role-assignments"]},
  "warnings": []
}
```
Here the angle-bracket hash is a **documentation placeholder, not an actual digest or credential**. Real runtime records must contain a validated 64-character lowercase hexadecimal SHA-256, and exact source bytes must remain private by default.

Requirements:
- Hash input bytes *before* parsing; record exact parser and producer versions.
- Treat `dataset_id` as an explicit authenticated namespace in the adapter configuration, not a guessed display name.
- Reject conflicting evidence that reuses `(source, dataset_id, source_run_id)` with a different digest.
- Different observed times on the same source artifact are **replays**, never new collection.
- Missing, malformed, stale, partial or unexpected artifacts produce `incomplete/unknown` and **must never close a finding**.
- Retain source URI type/path only as an opaque private artifact reference; no absolute workstation paths in public reports.
- Preserve raw upstream fields in the private evidence store and maintain an explicit normalized mapping; do not stringify away enum values.

## 4. Stable identity joins

Proposed canonical key:
`(dataset_id, provider, native_kind, native_id)`.

Allowed join result:
`exact` | `unmatched` | `ambiguous` | `cross_dataset_rejected` | `incompatible_kind`.

Rules:
- Match immutable Entra object IDs and explicitly defined source-kind mappings; never join on display name, UPN, email, title or a fuzzy model guess.
- EntraOps references may point at AzureHound-created principals/groups. Resolve as *references* and keep dangling references visible.
- Join only within the same dataset/tenant namespace. Assert source tenant identity before any graph correlation.
- Preserve `active`, `eligible`, `permanent`, `transitive` and `assignment-scope` concepts as distinct observed attributes, conditional on their presence and documented semantics.
- Preserve `admintierlevel`, `admintierlevelname`, `service`, `taggedby`, and `taggedbyrolesystem` when present; do not invent missing tiers. A tier assignment belongs to its original principal **or assignment**, as represented upstream, and carries the source RBAC system.
- An EntraOps OpenGraph edge that supplies additional context does not automatically become a BloodHound attack edge. Only documented traversable semantics can make a graph assertion.
- The OpenGraph extension schema is a separate approval-gated artifact. Offline adapter acceptance does **not** authorize installing it into CE.

## 5. Normalized enrichment rows

Represent contextual records separately from existing `path_runs` and `changes`:
```
enrichment_artifacts(
  artifact_id, source, schema_id, dataset_id, source_run_id,
  collected_utc, digest, producer_revision, completeness, warnings
)
enrichment_objects(
  artifact_id, native_kind, native_id, normalized_kind,
  join_state, matched_graph_object_id, raw_context_json
)
posture_checks(
  artifact_id, test_id, result, source_severity,
  reason_code, applicability, affected_object_refs_json
)
path_enrichment_links(
  path_run_id, path_fingerprint, artifact_id, object_ref,
  link_reason, link_confidence
)
```
Exact SQL schema, indexes and migration strategy are implementation decisions requiring code review. Foreign keys must refer to persisted immutable artifacts; corruption or missing references fail closed. Do not update Phase 2 findings while importing external evidence.

### Maester-specific handling

- Preserve `Passed`, `Failed`, `Investigate`, `Skipped`, `NotRun`, `Error` **distinctly**. Skipped/NotRun/Error are not equivalent to passed or resolved.
- Include test ID, origin, run identity, execution time and product/service scope. Use typed result metadata where available; fall back to the documented 2.x fields instead of guessing the preview shape.
- Store *affected-object* references separately. The preview docs describe `UniqueId` as derived identity; it is **not automatically** the original Entra object ID and must not be assumed to match BloodHound `objectId`.
- Correlate a failed check with a specific BloodHound asset only when an exact same-dataset object ID can be verified. If a test is tenant-scoped without an object ID, attach tenant posture context, not a fictional object link.
- Track the test catalog/module version. A missing test in a later run might be deselected or unsupported, not repaired.
- Keep free-form test messages as *untrusted text*; do not pass them as privileged instructions to the agent.
- Machine-readable Maester results and affected objects can contain identities; private by default and redacted in public evidence.

## 6. Risk and confidence must remain different dimensions

Current Phase 2 score is a useful lab triage weight, but mixing verified source confidence (+20) into risk makes a *better-collected* path appear inherently *more dangerous*.

Proposed independent outputs:
- `impact_tier`: derived from operator-owned critical asset designation (never inferred by model).
- `exposure_context`: exact observed path type/depth and any *verified* active/eligible privilege context, with unsupported semantics marked unknown.
- `posture_context`: relevant Maester result(s), with scope and timestamp.
- `evidence_confidence`: verified / limited / unknown, including age, coverage and exact join quality.
- `review_priority`: deterministic and explainable **queue order**, not a probability of compromise. Unknown confidence must trigger review/coverage action, not decrease exposure severity by itself.

Define weights only after synthetic acceptance fixtures demonstrate correct ordering and no false effective-access claims. Do not count unique directed graph routes as independent compromise opportunities without validating edge semantics.

## 7. AI analyst boundary and repeatable purple tests

Retain `finding_mcp`'s independent tool-selection policy and no-write rule. The model may read normalized evidence, never untrusted raw HTML, CLI output or arbitrary graph query text as instructions.

Suggested new read-only tools:
- `path_context()` — immutable selected path + exact object references.
- `identity_tier_evidence()` — linked EntraOps context, including join state.
- `posture_evidence()` — relevant Maester checks and eligibility/coverage.
- `collection_quality()` — completeness and timeliness from each source.

Tool outputs must carry distinct citations (`G#`, `E#`, `M#`); a citation always identifies the underlying artifact and snapshot. Model prose may say "may" or "requires review", but cannot claim a role is exploitable when only eligibility is observed.

Prompt-injection regression: place synthetic administrative instructions in the source artifact's human-readable description. Assert that no additional tool names, Graph writes, network calls, or lifecycle changes occur. These decisions must be enforced by the gateway and verified from tool-call receipts, not merely based on output text.

## 8. Acceptance matrix — proposal, not executed

| ID | Proposed test | Required outcome |
| --- | --- | --- |
| P3-01 | Import one synthetic, schema-valid EntraOps artifact twice | One artifact, replay detected |
| P3-02 | Same run identity with different content hash | Conflict rejected; original preserved |
| P3-03 | Cross-dataset matching ID | No join; explicit rejection |
| P3-04 | Name-only match / missing native ID | No graph join |
| P3-05 | Dangling/stub EntraOps reference | Unmatched, not silently discarded |
| P3-06 | Eligible PIM vs active assignment | Different states; no automatic active privilege |
| P3-07 | Two RBAC systems assign different tiers | Keep both scoped claims; no cross-system overwrite |
| P3-08 | Incorrect/unknown extension edge kind | Preserve source but do not assert traversable attack edge |
| P3-09 | Maester 2.x fixture and 3.0-preview fixture | Parse only documented supported shapes; version recorded |
| P3-10 | Maester Failed -> NotRun -> Skipped | No false remediation |
| P3-11 | Maester failed tenant-wide check with no object ID | Tenant context only; no direct asset join |
| P3-12 | Affected object UniqueId that differs from native object ID | No inferred identity equality |
| P3-13 | Wrong collector run, older UTC time or missing partitions | Mark limited/unavailable; preserve previous state |
| P3-14 | Ingest imported enrichment while path_history run is fixed | Byte-for-byte same graph findings/lifecycle |
| P3-15 | Malicious instructions in a result description | No unauthorized tool, mutation or outbound request |
| P3-16 | Corrupt JSON, oversized file, duplicate IDs, malformed timestamp | Explicit error; no partial committed evidence |
| P3-17 | Sample artifact includes a real-looking email or key string | Never publish raw identity/token in report or PR |
| P3-18 | Model unavailable during enrichment | Deterministic ingestion and reporting still succeed |
| P3-19 | EntraOps source is missing; Maester reports a pass | Missing privilege evidence stays unknown |
| P3-20 | Current graph differs from the historical finding snapshot | Preserve both timestamps and say historical, not presently confirmed |

The code owner must add executable fixtures and run these tests; this document does not count them as passing.

## 9. Minimum implementation package for Codex (deferred)

Only after this contract is reviewed:
1. Create private, bounded JSON fixture readers and a normalized SQLite schema; do not change existing `path_runs` rows.
2. Implement pure offline EntraOps classification enrichment and Maester result import.
3. Add all negative/ambiguity tests above and prove that an importer cannot alter graph fact or remediation state.
4. Produce one deterministic synthetic combined report with separate graph, tier, and posture citations.
5. Then (as a separate approval gate) add the four scoped MCP read tools and a small-model integration benchmark.
6. No live Entra/Graph access, privileged tenant app, CE extension installation or remediation in this package.

## 10. Review handback: next decision

**Recommended:** accept the offline-adapter-first approach and the requirement that confidence, exposure semantics and posture remain separate.

**Not requested:** merge, deploy, rewrite PR #108 history, procure licenses, grant privileges, enable tenant collection or start a long-running task.

**Expected/actual:** architecture and source inspection completed; the proposed acceptance tests are **NOT_EXECUTED**. No data was collected and no system was altered by writing this document. This PR is for review, not acceptance or implementation authority.
