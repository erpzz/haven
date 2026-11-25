# Strict model tool-scope prototype

Workstream: #126. Base: `53387e74a0ad90786ac3ea16753c8ad99142e9df`. Author: Astra (ChatGPT), 2026-11-25. Review-only; no self-merge.

Implementation: `tool_scope.py`. Source audit and design boundary: `TOOL_SCOPE_GAP_ANALYSIS.md`.

## Contract

A strict session has a host-owned `haven.tool-scope.v1` policy:

- **exact tool surface** — the model-visible tool names must equal the policy allowlist; an unexpected `terminal`, Tool Search bridge, new MCP tool or missing expected tool blocks session admission;
- **explicit budgets** — every allowed tool has a per-session maximum and the policy has a total maximum;
- **explicit argument keys** — extra top-level keys are refused and required keys must be present;
- **exact scoped values** — selected top-level or nested values are constrained by RFC-6901-style JSON pointers, e.g. `/tool_id` and `/arguments/snapshot_path`;
- **placeholder refusal** — host policy cannot approve obvious unset values such as `<TARGET>`, `${TARGET}`, `{{target}}`, TODO/TBD/CHANGEME, empty string or null;
- **duplicate-call control** — optional identical-call refusal uses SHA-256 fingerprints, so the state does not retain raw arguments;
- **atomic budget accounting** — concurrent calls share a lock, so parallel dispatch cannot race total/per-tool budgets;
- **fixed/redacted receipts** — denial receipts report only codes and counts, never target values or raw arguments.

The gate is intentionally separate from the tool's own schema validation. A strict scope policy says **which** capabilities/targets the model may ask for; the registry/tool implementation still validates argument types and semantics.

## Dispatcher example

For Haven Cyber's four-tool MCP facade, exposing `cyber_call` alone is not enough. A policy can approve only:

- `/tool_id = entra.ca.assess`
- `/arguments/snapshot_path = fixtures/tenants/approved.json`

A guessed `../../etc/hosts`, another registry tool id, or a missing constrained value blocks before dispatch.

## Author tests and second pass

Local Linux semantic run after second-pass hardening: **16/16 test methods pass**.

Coverage includes:
- exact visible surface; missing/extra/duplicate visible tools;
- unexpected raw `terminal` denial;
- wrong/missing/extra call arguments;
- exact type-strict value checks;
- placeholder/null policy rejection;
- total/per-tool/duplicate budgets;
- nested dispatcher target constraints;
- atomic concurrent budget test (20 parallel attempts, exactly 2 admitted under a budget of 2);
- state stores SHA-256 fingerprints rather than raw query/target values;
- duplicate/non-finite policy JSON;
- fixed/redacted denial receipts.

Additional author fuzz probes sent 5,000 malformed policy values through policy validation and 10,000 malformed/random call shapes through the call gate without an unhandled exception.

Second-pass changes made before publication:
1. top-level exact constraints were insufficient for a dispatcher; changed to JSON-pointer constraints so nested targets are enforceable;
2. call-budget state was made atomic under concurrent dispatch;
3. duplicate-call state changed from canonical raw call strings to SHA-256 fingerprints;
4. null was removed from allowed exact policy values so an unset target cannot be approved.

Published blobs will be recorded on the PR after the final-diff pass.

## Integration boundary

Expected integration order for a strict Hermes route:

`discover model-visible tools → exact surface admission → model turn → pre_tool_call scope check → underlying tool → existing evidence/answer verification`.

A blocked call must never reach the underlying tool. The policy must be created/selected by the host/operator, not generated or edited by the model during the session.

## Not qualified here

- no real Hermes hook is wired;
- no real `hermes-pentest` profile was tested;
- no raw terminal is made safe;
- no live network/tenant target was contacted;
- no hard cancellation for PR #105's timed-out worker thread was implemented;
- no CI/macOS/clean-checkout final-commit execution is claimed from this sandbox;
- no independent reviewer has certified the policy engine.
