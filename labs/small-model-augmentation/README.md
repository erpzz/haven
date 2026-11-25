# Small-model augmentation — model admission prototype

Workstream: [#126](https://github.com/erpzz/haven/issues/126). Base: `53387e74a0ad90786ac3ea16753c8ad99142e9df`. Author: Astra (ChatGPT), 2026-11-25. Review-only; Claude retains integration/merge ownership.

## Inventory and integration summary

Do not create parallel stacks. Existing work includes Cyber evidence and registry (#105, `69f7ae3`), Forge (#106, `2dd9c4b`), Hermes operator (#107, `a643257`), HARE (#115, `7f5af0d`), deterministic queries (#118), Purple integration (#122, `f701cd7`), and weight experiments (#123–125). The targeted source review included #122's `labs/purple-copilot-apm/ops/review.sh`, HERMES_RUNBOOK.md and apm/review.py. The launcher uses a health response to accept an existing server; a health response is not model identity. The runbook specifies a 64,000-token Hermes minimum. No change to any of those paths or their contracts here.

## Proposed contract

`preflight.py` accepts a JSON document via stdin, provided by a trusted launcher, with exactly four keys: expected_model (operator selection), requested_model (effective request configuration), observed_model_ids (inventory from the actual selected single-model server), observed_context_tokens (effective observed context, not the advertised maximum). Exact case-sensitive match is required; singleton inventory only; missing or malformed observations block. CLI exits 0 on pass or 2 on block, returning fixed diagnostic codes without echoing input. The minimum is pinned to the documented Hermes version. This is deliberately restricted to single-model server configurations; a multi-model backend needs a different reviewed contract.

Example (synthetic):
```sh
printf '%s\n' '{"expected_model":"fixture-model-9b","requested_model":"fixture-model-9b","observed_model_ids":["fixture-model-9b"],"observed_context_tokens":65536}' | python3 preflight.py
```

The prototype does not contact an endpoint, inspect weights, validate model hashes, enforce a launch decision, check endpoint placeholders, authenticate observations, or prevent a server swap after validation. A passing result is NOT permission to execute anything. Unknown effective context must block rather than default to configured context. The future launcher must source observations independently of model output and bind them to the actual request route; it must not trust arbitrary user/model JSON as an authority. Tool visibility is the next separate work package.

## Executed test receipt

Linux CPU sandbox, Python standard library, no inference/network/GPU. Command: `python -m unittest -v` in this directory. Expected 11 pass; observed 11 pass in 1.342 s. Git blob IDs of tested bytes, re-fetched after publication:
- preflight.py: `c979fcf49a281c87ac18023a71a6842aad142670`
- test_preflight.py: `eb9baf988486af23f3a48431ac941e72b33df099`

Synthetic tests cover consistent selection, wrong request/server, ambiguous/duplicate inventory, missing/extra fields, malformed identifiers, context boundary and wrong types, case sensitivity, malformed/oversized JSON, and CLI exit/redaction behavior. These are producer tests, not independent qualification. No deployment or CI run claimed.

## Next decision and limits

Review contract with integration owner, then add an adapter and verify the actual effective Hermes model/route/context at launch with a scripted local server and later the named Mac. Fail closed on unavailable observations. No private transcripts, credentials, host paths, reserve cases, or training data published. No changes to active integration, weights work or M4 qualification; do not self-merge.
