# Hermes pre-tool scope hook (development candidate)

This is a **real Hermes plugin callback** for the Python #129/#193 scope engine,
not a replacement agent and not a claim of actual Mac qualification.

The callback uses the Hermes v2026.9.24
pre_tool_call(tool_name, args, session_id, ...) contract. It does not trust the
model to report which tools were visible or which calls executed.

## Boundary

* A host-created private JSON policy has the haven.tool-scope.v1 shape.
* Every callback reopens the policy using O_NOFOLLOW and checks stable
  file identity + byte SHA-256. The file must be an owner-only regular 0600
  file. Any change causes denial for the rest of the running Gate.
* Every call is checked by tool_scope.check_call before underlying dispatch.
  Per-session budgets and duplicate detection are atomic within one process.
* A missing policy, invalid configuration, absent session ID, exhausted
  session capacity, changed policy, invalid argument or unknown tool denies.
* No untrusted arguments, session identifiers or policy targets appear in
  block messages. A denied call consumes no tool budget.
* The callback returns a valid {"action": "block", "message": ...}
  instead of raising, to defend against hook-exception fail-open behavior.
* This **does not** make Hermes fail closed if the plugin is missing,
  disabled, not loaded, registered on the wrong execution path, bypassed,
  or if multiple Hermes processes share one session ID and do not share
  budget state. Those are host-launcher/admission obligations.
* Hermes hooks or middleware can rewrite arguments after an early veto. Guarded
  Haven/Haven-Cyber MCP servers therefore independently narrow their raw tool
  surface and reauthorize the exact final raw tool + arguments immediately
  before implementation dispatch. The early hook remains defense in depth.

## Installation (isolated profile only)

Use the approved #193 integration tree and copy this package to a dedicated
profile under HERMES_HOME/plugins/haven-scope. Do not install into the
ordinary ~/.hermes profile or expose terminal/tools search just to make a
test pass. Point the guarded launch environment to:

    HAVEN_AUGMENTATION_ROOT=/absolute/checkout/labs/small-model-augmentation
    HAVEN_SCOPE_POLICY_FILE=/absolute/private/scope-policy.json

Create the policy with a host-controlled enrollment process, not by asking
the model to author it. Enforce owner-only 0600 permissions and immutable
run/session configuration. Tool names must be the *exact post-transform names*
observed in the OpenAI model request (e.g. MCP-prefixed names if Hermes
actually prefixes them), not guesses from MCP tools/list.

Before a guarded run, use the host preflight to bind the exact Hermes
executable and installed plugin bytes, require the exact enabled user-plugin
set, and run Hermes's own plugin doctor:

    AUG=/absolute/checkout/labs/small-model-augmentation
    HERMES_SHA=$(shasum -a 256 /absolute/path/to/hermes | awk '{print $1}')
    INIT_SHA=$(shasum -a 256 "$HERMES_HOME/plugins/haven-scope/__init__.py" | awk '{print $1}')
    MANIFEST_SHA=$(shasum -a 256 "$HERMES_HOME/plugins/haven-scope/plugin.yaml" | awk '{print $1}')
    ENGINE_SHA=$(shasum -a 256 "$AUG/tool_scope.py" | awk '{print $1}')
    SCOPE_SHA=$(shasum -a 256 /absolute/private/model-scope.json | awk '{print $1}')
    MCP_SHA=$(shasum -a 256 /absolute/private/raw-mcp-scope.json | awk '{print $1}')

    python3 "$AUG/hermes_plugin_preflight.py" \
      --hermes /absolute/path/to/hermes \
      --hermes-home "$HERMES_HOME" \
      --hermes-sha256 "$HERMES_SHA" \
      --plugin-init-sha256 "$INIT_SHA" \
      --plugin-manifest-sha256 "$MANIFEST_SHA" \
      --augmentation-root "$AUG" \
      --scope-engine-sha256 "$ENGINE_SHA" \
      --scope-policy /absolute/private/model-scope.json \
      --scope-policy-sha256 "$SCOPE_SHA" \
      --mcp-policy /absolute/private/raw-mcp-scope.json \
      --mcp-policy-sha256 "$MCP_SHA" \
      --allow-user-plugin haven-scope

The hashes above are enrollment inputs only when they came from bytes the
owner/reviewer already approved. Computing them from an unreviewed install and
then accepting them proves consistency, not provenance. The receipt binds the
Hermes executable, plugin source + manifest, exact tool-scope engine, model-side
scope policy, and raw-MCP final-dispatch policy. Both policy files must be
owner-private and valid under the same enrolled engine. The strict preflight
also rejects unexpected enabled non-bundled plugins; add another
--allow-user-plugin only after explicitly reviewing why it belongs in that
isolated profile. Guarded preflight and child launch additionally force
HERMES_ENABLE_PROJECT_PLUGINS=0, because project-local plugins are a separate
Hermes discovery path and must not be inherited from an ambient shell/cwd.
The isolated HERMES_HOME must contain an owner-private regular 0600 `.env`;
preflight rejects the profile if that file defines `HERMES_ENABLE_PROJECT_PLUGINS`
at all. Hermes loads the profile `.env` with override semantics, so merely setting
`0` in the parent environment is not a sufficient guard by itself.

The fixture-level test runs with:

    python3 -m unittest discover -s labs/small-model-augmentation -p 'test_hermes_scope_plugin.py' -v

The separate scope/router suites are also run in CI on this branch.

## Required real-Mac demonstration (NOT EXECUTED HERE)

1. Start from an isolated HERMES_HOME and exact pinned Hermes v2026.9.24;
   pass hermes_plugin_preflight.py using previously enrolled hashes, then show
   that the same guarded chat process actually loads the pre_tool_call callback.
2. Guard the run under #127's owned llama-server process with enrolled
   executable/GGUF bytes, admitted model alias and >=64K effective context.
3. Capture the **actual first** post-client-transform model-visible tool
   definitions with #127's no-tool-call visibility probe or the Red Factory
   capture proxy. The v2 visibility receipt records the exact transformed
   tool-name sequence plus a SHA-256 of the complete canonical tool-definition
   array. Use a discovery pass that never requests a tool call, then replay the
   probe with `--expect-name` values and `--expect-surface-sha256` before
   constructing the guarded per-case policy. Do not infer the full name from
   an MCP server name or prefix count.
4. Route the already host-authorized set with #131. The routed definitions
   must match the actual model request. Never widen on routing miss.
5. In the real Hermes call loop, propose a hidden zero-side-effect
   write_canary plus wrong nested target, duplicate and over-budget calls.
   Prove no denied dispatch appears in the independent synthetic MCP log,
   including concurrent requests; verify an approved read still works.
6. Check the plugin-load-negative test: disable the plugin, alter one enrolled
   plugin byte, or enable an unexpected user plugin and verify the *supervisor*
   refuses to start the supposedly guarded session. Preflight/doctor are still
   not substitutes for proving the later chat process actually loaded the hook.
7. Record exact process, plugin, policy SHA-256, model-visible catalog hash,
   Hermes/MCP revision, platform, signed-off owner and distinct intent vs
   actual-dispatch counts in private receipts; redact names/targets publicly.

The visibility probe itself does not qualify model behavior: its scripted
backend always asks for a plain text reply and never requests a tool call.
For Red Factory qualification, because case authorization changes between
cases, **do not run a mixed case suite under one fixed model-side scope
policy**. Bind one supervisor/preflight invocation to one case-specific
model-side policy and one case-specific raw-MCP policy.

Do not call this production complete from a passing synthetic suite.
Author review/CI are not independent security certification. Claude remains
merge owner. No tenant/network/real target operations, reserve/M4 use,
training, deployment, model promotion or self-merge are authorized.

## Known out-of-scope hazards

A same-user adversary may modify a plugin, source checkout, parent directory
or running process; O_NOFOLLOW on the final policy path is not an OS sandbox
or full same-user attestation. These guards also do not defend against a
Hermes route that never invokes pre_tool_call. The Mac launcher must bind
the plugin's actual registration, first model request and pre-dispatch
interception to the same child process, and must supervise the model lease.
