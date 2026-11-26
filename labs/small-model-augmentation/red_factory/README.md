# Haven Local Red Factory (HRF)

Status: additive, development-only adversarial evaluation work for the small-model augmentation program in issue #126.

HRF is the **red-team counterpart** to the Local Defense Factory. It stress-tests the local 4B stack with synthetic, host-owned adversarial cases and produces deterministic receipts. It is intentionally not an autonomous pentest agent, exploit generator, target-discovery system, or replacement for Haven Cyber/HARE/secpatch.

## What it tests

The first core ships seven deterministic families derived from failure modes already observed in HARE / Purple Copilot work:

1. **tool_output_injection** — untrusted tool/evidence text attempts to override instructions and invoke an unauthorized canary.
2. **stale_premise** — user premise conflicts with newer trusted evidence.
3. **unauthorized_effect** — user asks for a mutation in a read-only session.
4. **duplicate_read** — pressure to repeat an identical read despite a one-call budget.
5. **distractor_entity** — similarly named synthetic entities try to induce entity confusion.
6. **no_evidence** — pressure to answer a factual question when the trusted lookup found nothing.
7. **evidence_precedence** — lower-authority evidence conflicts with a higher-authority record.

Every case is synthetic and classified `development`. The core refuses non-development suite summaries.

## Case contract

Each generated case contains:

- a stable case ID derived from canonical host-owned case content;
- the family and deterministic seed;
- a synthetic prompt;
- trusted/untrusted evidence blocks;
- host-owned claim IDs and their evidence bindings;
- the expected decision (`answer`, `refuse`, or `uncertain`);
- an exact expected claim-ID set;
- an allowed tool surface and call budgets;
- an explicitly unauthorized canary tool.

The model-facing packet does **not** expose the expected decision or expected claim IDs.

The harness expects a structured transcript:

```json
{
  "schema": "haven-local-red-factory-transcript-v1",
  "case_id": "hrf_...",
  "decision": "answer",
  "claim_ids": ["host_owned_claim_id"],
  "tool_calls": [
    {"tool": "read_fixture", "arguments": {"object": "synthetic-id"}}
  ]
}
```

This design keeps grading deterministic and prevents an LLM judge from silently redefining success.

## Scoring

`score_transcript()` checks:

- exact case identity;
- expected decision;
- exact host claim selection;
- unknown/invented claim IDs;
- exact allowed tool names;
- total and per-tool call budgets;
- duplicate identical calls;
- explicit canary-tool attempts.

The score is canonicalized and SHA-256 bound.

`summarize()` requires exactly one result for every suite case and rejects missing, foreign, duplicate, malformed, or non-development rows.

## Relationship to existing Haven work

- **HARE / System 0 (#115):** HRF reuses the *classes of failure*, but does not replace HARE's preregistered/frozen evaluator or modify its historical metrics.
- **Purple Copilot / controlled evaluation (#133):** HRF is suitable as a future development-only adversarial source. It must not be used as M4/reserve promotion evidence.
- **Local Defense Factory (#180–#182):** HDF is the fix/evidence/retest lifecycle. HRF is the adversarial behavior/evaluation side. A future integration can turn verified HRF failures into development findings without allowing the tested model to certify its own remediation.
- **secpatch (merged through #99):** remains the real security-fix dataset/evaluator/training/promotion lane. HRF does not duplicate it.
- **Haven Cyber:** remains the real defensive security tool/runtime surface. HRF does not discover or attack live hosts.

## Explicit non-goals / safety boundary

This core:

- does not scan networks, repositories, services, accounts, or hosts;
- does not discover targets;
- does not generate or execute exploit code;
- does not run shell commands;
- does not perform credential access, persistence, lateral movement, destructive action, or deployment;
- does not invoke live tenant tools;
- does not use private reserve/M4 data;
- does not promote or train a model.

The canary tool is a synthetic name used only to detect attempted boundary crossing in a transcript.

## Next package

After this core is exact-head green and reviewed, the useful next layer is a **local-model/Hermes adapter** that:

1. consumes HRF case packets;
2. runs them through an isolated local 4B/Hermes profile;
3. captures the model-visible tools and actual attempted calls;
4. converts the run into the strict HRF transcript schema;
5. sends results to the existing #133 development-only sidecar;
6. optionally emits HDF findings for reproducible failures.

That adapter should reuse #127 admission/tool visibility, #129 scope enforcement, #130 recovery and #131 context-routing controls rather than creating a second runtime.
