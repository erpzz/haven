# Draft contracts and semantic obligations

These are JSON Schema 2020-12 **design examples** for later domains. They are not the active M0 schema, a complete production authorization protocol, or executable access control. The sample records are synthetic, explicitly unqualified and incapable of authorizing any real device through this repository, which contains no such adapter.

`registry.json` maps each schema to a positive fixture and its additional semantic rules. Negative fixtures exercise unknown fields, execution flags, missing frames, fabricated unavailable health values and false delivery claims. The package validator supports exactly the local schema-keyword subset used here, plus a few explicitly named cross-field checks; it is not a general JSON Schema implementation. Production adoption should use a maintained full validator and domain-specific authorization/storage logic after a separate review.

## Boundaries

| Contract | Producer → consumer | Important meaning |
|---|---|---|
| evidence | Adapter/perception → ledger/context | Origin, time, claim class and provenance accompany content |
| context_packet | Scoped retrieval → model | Minimal context, not a transferable consent token |
| consent_proposal | Consent UX → future consent service | Example proposal is not an actual grant |
| daily_action_proposal | Coordinator → daily policy | Draft/intent is not sent/scheduled/observed completion |
| health_observation | Native permitted bridge → private store | Measurement time differs from receipt; missing data stays unknown |
| spatial_estimate | Perception → map projection | Frame, calibration, uncertainty, evidence and time |
| agent_job | Coordinator → bounded worker | Budget/deadline/capabilities; no self-authorizing side effects |
| experiment | Research planner → review notebook | Hypothesis, baseline and protected measurements |
| design_artifact | CAD/test worker → artifact registry | Exact revisions and qualification stage |
| physical_action_proposal | Coordinator → domain review | Logical device/template only; no raw network/motor instructions |
| delivery_receipt | Communication component → UI | Local/relay/test destination states, not real dispatch |
| capability_qualification | Documentation/tests → readiness | External feature evidence is not local qualification |

## Invariants not solved by field validation

Authenticated source and subject must be established by actual services. Grants must be active for purpose, recipient, resource and provider. Content hashes must match actual files and paths must be confined. Evidence references must resolve to permitted records, calibration/frames/times must be compatible, deadlines must be enforced, and known failures must not become absence/success. Authorization needs authenticated integrity, revocation and rechecks. None of these is guaranteed by a schema-valid object.

Zero hashes in most fixtures are deliberate synthetic placeholders, not evidence of a real recorded image. The one requirement-spec design hash matches an actual inert JSON file. No real health data, keys, device identifiers, toolpaths or motion commands are included. All date strings are fixtures, not current operational status.

## Versioning and M0 coexistence

Use a domain-specific adapter and a reviewed migration plan before integrating any new record. Preserve the existing source/request idempotency and accepted receipt contract. Do not expand M0 with a universal polymorphic event store or change its approved expiry/security semantics simply because these drafts exist.
