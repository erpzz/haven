# Tool scope enforcement gap analysis — 2026-11-25

Workstream: #126. Base main: `53387e74a0ad90786ac3ea16753c8ad99142e9df`.

This package addresses the failure seen in the recovered unattended audit: missing/placeholder targeting information was followed by endpoint guessing because the model had broad execution affordances. The fix should not be "tell the model more strongly." A strict session must be admitted only when the **host-owned tool surface and target values** match an explicit policy.

## Exact source reviewed

PR #105 head `69f7ae3725b7a4a832a4ce17317d6351eb2a5293`:
- `haven_cyber/tools/registry.py` blob `da1502b335a956778f3602ebc3e62daa2a10a490`
- `haven_cyber/mcp_server.py` blob `9ac5981d790b9f9ed80a5129e59f026ea7e6a02c`
- `tests/test_registry_and_graph.py` blob `7d71a610bf9f05b324883cc27ffa681d4ddf4151`
- `docs/research/MCP_TOOL_REGISTRY.md` blob `5850a3b32c52635fd38d9b3aecf41e43e1d38891`

PR #122 head `f701cd766e7068649c4722874a6ced1b2213fbdf`:
- Purple Copilot's strict review gate already blocks non-Purple tools, bad/extra arguments, repeated reads and excess calls for that product route. This package is a reusable host-side admission primitive, not a replacement for that gate.

## Existing strengths worth preserving

- Haven Cyber paths are resolved against configured roots and foreign Graph pagination links are rejected.
- Registry tools declare read/write class, scope, prerequisites, timeout and rate.
- Non-read-only registry tools are refused.
- Live Graph collection is separately prerequisite-gated.
- The public MCP surface is deliberately small and lazy.

## Gaps relevant to small-model scope enforcement

1. **A configured/running tool is not the same as an authorized model-visible tool.** PR #127's visibility probe handles observation. This package binds the observed set to an exact host-owned allowlist. Any extra tool, including `terminal` or Tool Search, blocks strict-session admission.

2. **Registry `scope` is descriptive, not a generic enforcement primitive.** Individual functions enforce their own scope. A small model still chooses which registry capability to dispatch through `cyber_call`. The new policy can constrain `/tool_id` to the exact approved inner capability.

3. **Dispatcher targets need nested constraints.** Constraining only top-level `cyber_call` arguments is insufficient because the actual target may be `/arguments/snapshot_path` or another nested field. `tool_scope.py` uses RFC-6901-style JSON-pointer constraints to require exact approved nested values.

4. **The registry validator is intentionally shallow.** It validates top-level required/extra keys, primitive type/enum and integer range, but it does not recursively validate array items or nested objects. A strict scope policy therefore must not assume the registry schema recursively constrains targets.

5. **Falsey arguments are normalized before validation.** `Registry.invoke()` begins with `args = args or {}`; a falsey non-object can become an empty object. The scope gate rejects non-dict call arguments before downstream dispatch.

6. **Timeout is not a hard execution stop.** `fut.result(timeout=...)` returns a timeout error but does not terminate the worker thread. A timed-out read-only operation can continue running (including a tenant read) after the agent sees a timeout. This is a runtime-control gap, not solved by this policy module; it belongs in the Codex/local integration queue and likely requires subprocess/process-level cancellation for hard bounds.

7. **Rate and call budgets are separate concerns.** Registry rate limiting is per process/tool over one minute. The model-facing session also needs a finite per-turn/session budget. The new gate maintains total/per-tool limits atomically and optionally refuses identical repeated calls.

8. **Prompt placeholders cannot define authority.** Exact target values are host policy. Placeholder-looking approved values (`<TARGET>`, `${TARGET}`, `{{target}}`, TODO/TBD/CHANGEME, empty/null) are rejected while constructing policy. A model cannot turn an absent target into authority by guessing.

## Security boundary

A strict profile should **not expose a raw terminal/shell tool at all**. This package intentionally does not attempt to parse shell commands and decide which hosts a command might contact; that is not a defensible authorization boundary. If an operation needs network or shell behavior, expose a structured tool whose arguments can be constrained and independently enforced.

The exact model-visible set should come from the PR #127 visibility probe (or equivalent host observation), then be checked by `bind_surface()` before inference. Each `pre_tool_call` should pass through `check_call()` before dispatch. A blocked call must never reach the underlying tool.

## Limits

- This is a library prototype; it is not wired into Hermes hooks here.
- Exact-value policy constrains selected JSON-pointer values but is not a full recursive JSON-schema engine. Downstream typed/schema validation remains required.
- It does not make raw terminal safe.
- Policy provenance/authentication and durable receipt storage are integration concerns.
- It does not hard-kill timed-out downstream work.
- Real Hermes concurrency, MCP behavior, macOS and local network targets are not qualified here.
