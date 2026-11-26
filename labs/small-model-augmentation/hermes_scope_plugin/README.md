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
* A different Hermes pre_tool_call hook returning a tool-argument modify directive
  may change arguments after this veto has examined them. Host launch must
  exclude such modifier hooks or independently reauthorize final arguments at
  the actual dispatcher. This plugin alone does not prove hook ordering safety.

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

The fixture-level test runs with:

    python3 -m unittest discover -s labs/small-model-augmentation -p 'test_hermes_scope_plugin.py' -v

The separate scope/router suites are also run in CI on this branch.

## Required real-Mac demonstration (NOT EXECUTED HERE)

1. Start from an isolated HERMES_HOME and exact pinned Hermes v2026.9.24;
   show that the plugin is discovered and the pre_tool_call callback fires.
2. Guard the run under #127's owned llama-server process with enrolled
   executable/GGUF bytes, admitted model alias and >=64K effective context.
3. Capture the **actual first** post-client-transform model-visible tool
   definitions with #127's no-tool-call visibility probe or the Red Factory
   capture proxy. Run exact surface admission and reject missing/excess tools.
4. Route the already host-authorized set with #131. The routed definitions
   must match the actual model request. Never widen on routing miss.
5. In the real Hermes call loop, propose a hidden zero-side-effect
   write_canary plus wrong nested target, duplicate and over-budget calls.
   Prove no denied dispatch appears in the independent synthetic MCP log,
   including concurrent requests; verify an approved read still works.
6. Check the plugin-load-negative test: disable the plugin deliberately,
   verify the *supervisor* refuses to start the supposedly guarded session,
   and retain an explicit block receipt. A callback alone cannot detect
   its own absence.
7. Record exact process, plugin, policy SHA-256, model-visible catalog hash,
   Hermes/MCP revision, platform, signed-off owner and distinct intent vs
   actual-dispatch counts in private receipts; redact names/targets publicly.

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
