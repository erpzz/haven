# Dynamic tool selection / context optimization gap analysis — 2026-11-25

Workstream: #126. Base main: `53387e74a0ad90786ac3ea16753c8ad99142e9df`.

The objective is to reduce the small model's tool-context burden without turning a router into a new authority source. The router may only **narrow** tools that the host has already authorized. It must never reveal an unapproved tool merely because model text, tool description text or a retrieval result mentions it.

## Exact source reviewed

PR #105 head `69f7ae3725b7a4a832a4ce17317d6351eb2a5293`:
- Haven Cyber registry `labs/cyber/haven_cyber/tools/registry.py` blob `da1502b335a956778f3602ebc3e62daa2a10a490`;
- Haven Cyber MCP facade `labs/cyber/haven_cyber/mcp_server.py` blob `9ac5981d790b9f9ed80a5129e59f026ea7e6a02c`;
- registry design `MCP_TOOL_REGISTRY.md` blob `5850a3b32c52635fd38d9b3aecf41e43e1d38891`.

PR #106 head `2dd9c4b3a7a88a84b8238653b4eeb03713d55085`:
- Forge fail-closed synthetic router blob `6646c53e9527bbcad7f398fd383163b137b5b9d3`;
- Forge offline knowledge index blob `43d5652e0f9deff6cff4f7b5a7ca7e64f9d44f`.

PR #107 head `a643257f4c4b5495c2b3c3b96f504373f6d90587`:
- Haven operator registry blob `e2936595dfdeda3e37003b225476e7522f288f49`;
- MCP stdio server blob `9490369377231806024542de53543f7626e725df`;
- server assembly blob `0c54fc1b05b1a9da83c845a0a944d5233af1f266`;
- built-in read tools blob `b7bbddb60b1bf88fcdad7e4c12ecc0bbdda65c9b`;
- change tools blob `c316ee3f1d255ad54b79963160424d5f224f98d4`;
- dynamic admitted-skill bridge blob `5dae99a2fbb6f5ea88343d9ac8804a56de3b20ad`.

PR #118 head `5276673c9c43c6030ca7202690229cb149fb617d`:
- query-writing harness blob `b69359a8ca50c160a2e1bb08cdd73d0512d09bba`;
- research README blob `86c2beadeb38b4a7b0def2bf05bdaf8db4ba9e77`.

## Existing patterns to preserve

### Haven Cyber (#105)

Haven Cyber already solves much of the **schema-context** problem well. Its public MCP surface stays at four tools regardless of registry size: search, capabilities, describe and call. The model sees compact capability cards first and asks for a full schema only when needed. Do not replace this with a second large top-level router unless measurement proves a need.

For strict sessions, PR #129 can constrain the inner `cyber_call` target and nested target arguments. That gives us compact discovery plus explicit authority.

### Forge (#106)

Forge's `route_synthetic()` is a good pre-model routing pattern: narrow known scope, fail closed on mutation/unknown cases, dispatch through a caller-supplied authorized executor and independently verify the result. The generic context router follows the same failure direction: a routing miss removes capability instead of exposing everything.

### Haven operator (#107)

The operator is different: `tools/list` returns the full name, description and input schema for every currently visible registry tool. In operate mode this includes reads plus change/create tools; owner-admitted skills may dynamically appear and trigger `notifications/tools/list_changed`.

This is the main integration target for context narrowing on a small model.

## Gaps / design decisions

1. **Selection is not authorization.** The router input contains an already-authorized set. Output is always a subset. An unknown authorized name blocks rather than being invented or ignored.

2. **Free-form descriptions are not routing metadata.** Tool descriptions can be long and dynamic; admitted skill metadata can originate in model-authored candidate content before owner admission. The prototype scores only explicit host-curated lowercase `route_terms`. Description/schema text is carried to the model only after the tool is selected.

3. **Dynamic catalogs need invalidation.** A catalog SHA-256 binds tool name, effect, route metadata and the exact model-visible definition. The hash is order-independent so transport reordering is harmless, but any semantic/card change invalidates a bound selection. A `tools/list_changed` event must force a refresh/reroute before another model turn. The integration should also refresh/compare the bound hash immediately before dispatch so a catalog change between model request and tool call fails closed.

4. **Effects are filtered separately from relevance.** The default router admits only `read` cards. Change/create tools can be considered only when the host explicitly permits those effects *and* the tool is already authorized. Relevance never upgrades effect authority.

5. **Required/core tools are never silently truncated.** If caller-required tools exceed the count or byte budget, routing blocks. Optional matched tools may be omitted to stay within budget, but the receipt reports `budget_limited` and the exact omitted-relevant count.

6. **No-match is not full-catalog fallback.** A routing miss returns only explicitly required/core tools (or none). The caller can ask for clarification, use a compact discovery facade or choose a wider host policy. It must not silently expose the entire catalog.

7. **Budget exact serialized bytes, not guessed tokens.** The prototype counts canonical JSON bytes for the exact returned model-visible definitions. Token cost depends on the selected model/tokenizer and must be measured separately during integration; byte limits are deterministic but are not a token-context guarantee.

8. **Catalog order is not provenance.** Fingerprints sort cards by tool name before hashing. Reordering does not invalidate a run; routing terms, effect or exact model-visible definition changes do.

9. **Routing metadata needs a trusted source.** PR #107's `ToolSpec.tags` field exists but the built-ins inspected here do not populate it. Integration should add/maintain owner/code-reviewed routing cards or populate trusted tags. Do not derive route authority automatically from tool descriptions or user/model text.

10. **Dynamic skill definitions still enter model context after selection.** The router prevents their description text from causing selection, but it is not a prompt-injection sanitizer for the selected definition. If dynamic skill descriptions/schema annotations are considered untrusted despite admission, add a host-generated minimal definition or a separate sanitization contract.

11. **#118 is research, not a production selector.** Its development harness explores whether making the model write a formal query beats prose reasoning. The development suite is acknowledged as non-deciding. It supports evaluating structured decomposition later; it is not evidence to route production traffic automatically today.

## Proposed strict integration

For the Haven operator small-model route:

1. Read the server's complete current tool catalog before a model request.
2. Build trusted cards from the exact **post-client-transform definition that Hermes will place in the model request**, plus host-curated route terms/effect metadata. MCP `tools/list` source objects are not automatically identical to the OpenAI-compatible definitions the model receives.
3. Intersect with the host-authorized surface.
4. Route the current task under hard count/byte/effect budgets.
5. Instantiate/bind PR #129's exact model-visible scope to the selected names and argument constraints.
6. Use PR #127's first-request probe to verify the model request actually contains that selected set and the expected transformed definitions.
7. On `tools/list_changed` or any catalog-hash change, invalidate the selection before the next model turn; refresh the bound catalog again at pre-tool-call so a selected name cannot silently point at changed semantics.
8. Record the catalog/selection hash in PR #130's immutable run manifest when checkpointing is enabled.

For Haven Cyber, retain the existing four-tool facade unless controlled evaluation shows a material problem. Inner registry-tool choice can be narrowed through `cyber_call` plus PR #129 nested target constraints.

## Prototype limits

- It is a library prototype, not wired into Hermes or MCP.
- The lexical scorer is intentionally simple; routing recall must be measured on a non-reserve development set before adoption.
- Route terms are assumed host-curated; this prototype does not sign them.
- Serialized byte budget is not tokenizer-aware.
- It does not sanitize selected tool descriptions/schema text.
- It does not decide owner approvals or change/create authorization.
- Real first-request context size, latency and accuracy impact on Qwythos were not measured here. Persisted selected-tool names can also reveal coarse task intent even without storing the query; receipt privacy needs an integration decision.
