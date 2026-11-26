# Dynamic tool-context routing prototype

Workstream: #126. Base `53387e74a0ad90786ac3ea16753c8ad99142e9df`. Author: Astra (ChatGPT), 2026-11-25. Review-only; no self-merge.

Implementation: `tool_context.py`. Upstream audit/design: `TOOL_CONTEXT_GAP_ANALYSIS.md`.

## Contract

The router takes four trust inputs from the host:

- a current catalog of exact **post-transform model-visible** tool definitions (not merely the MCP source objects);
- explicit host-curated lowercase routing terms for each tool;
- the already-authorized tool names;
- allowed effect classes (`read` by default).

It returns a deterministic subset. It cannot add tools outside the authorized set.

Routing terms and model-visible definitions are deliberately separate. Free-form descriptions/schema text never participate in relevance scoring.

## Failure direction

- unknown authorized name → **block**;
- required tool not authorized → **block**;
- required effect not permitted → **block**;
- required tools exceed count/byte budget → **block**;
- bound catalog hash changed → **block**;
- no lexical route match → required/core tools only, never full-catalog fallback;
- optional relevant tools that do not fit → omit them, set `budget_limited=true`, and report the exact omitted-relevant count.

Change/create tools are filtered out by default even when they are in the authorized set. Relevance cannot grant effect authority.

## Catalog binding

`catalog_sha256()` binds:

- tool name;
- effect class;
- host routing terms;
- exact model-visible definition.

Hashing sorts cards by tool name, so a harmless `tools/list` reorder does not change the fingerprint. Any definition/routing/effect change does.

A dynamic `tools/list_changed` event should invalidate the current selection before the next model turn. Integration should also re-check the bound catalog immediately before dispatch to close the route→call change window.

## Context budget

The router counts the exact canonical JSON **bytes** of the returned definitions. It does not claim those bytes equal model tokens. Integration must separately measure actual tokenizer/context cost on the admitted model.

Individual definitions and the whole catalog are bounded before routing.

## Author test evidence

Author-side semantic reproduction before the final zero-tool refinement: **24/24 PASS**. The final review then added an explicit zero-authorized-surface regression; exact final-head clean-checkout execution is intentionally left to Codex/local validation rather than claimed here.

Coverage includes:

- selection is a subset of authorization;
- an explicitly empty authorized surface is valid and remains zero-tool;
- an unauthorized matching tool is never added;
- tool description text cannot cause routing;
- unknown/duplicate authorized names fail closed;
- required authorization/effect constraints;
- change tools filtered by default;
- required count/schema budgets block instead of truncating;
- exact returned-definition byte accounting;
- optional count/byte budget omissions are reported;
- zero-match does not expose the full catalog;
- deterministic tie breaking;
- order-independent catalog fingerprint;
- fingerprint sensitivity to routing metadata and model-visible definition;
- expected-catalog mismatch invalidation;
- duplicate tool / definition-name mismatch;
- strict host routing-term format;
- query text is not echoed or hashed into the receipt;
- malformed query/effect/authorization inputs fail closed;
- deterministic required-tool ordering;
- bounded definition/catalog inputs.

A separate malformed-input fuzz probe exercised **30,000** randomized catalog/query/authorization shapes with **0 unhandled exceptions** in the author semantic reproduction.

Second-pass refinements before publication:

1. free-form description/schema text was explicitly excluded from scoring;
2. no-match fallback was made fail-narrow rather than full-catalog;
3. catalog fingerprinting was made order-independent but content-bound;
4. required tools were made fail-closed under count/byte budgets;
5. optional budget omissions were made explicit;
6. effect filtering was separated from relevance;
7. byte accounting was defined over the exact returned model-visible definitions, not an estimated token count;
8. final review corrected an over-strict validator that rejected a legitimate empty authorized tool surface.

Published code/test blobs at this review point:
- `tool_context.py`: `f2a23c7de281944d2b3fdaab2fe13b40b493338e`
- `test_tool_context.py`: `7127c27bec27c6f59e05098ef0c49cdce3d8ad92`

**Exact committed-head clean-checkout execution is NOT claimed.** Git/raw GitHub resolution is unavailable from this sandbox; Codex/local validation must run the committed bytes.

## Intended composition

For Haven operator / Hermes:

`current MCP catalog → host authorization → tool-context routing → exact selected-surface admission (#129) → verify first model request (#127) → model/tool loop → checkpoint manifest (#130)`

For Haven Cyber, keep #105's compact four-tool lazy facade unless evaluation demonstrates a need to change it.

## Not executed / not qualified

- exact committed-head clean-checkout suite;
- actual PR #107 catalog converted into route cards;
- actual Hermes first-request byte/token savings;
- Qwythos accuracy/latency comparison with full vs narrowed tools and tokenizer-level context measurement;
- dynamic `tools/list_changed` live behavior and route→dispatch catalog-change race;
- owner-signed provenance for route terms;
- sanitization/minimization of a selected dynamic skill's description/schema;
- privacy disposition for persisted selected-tool names, which can reveal coarse task intent even though the query is not stored;
- macOS integration;
- independent review.
