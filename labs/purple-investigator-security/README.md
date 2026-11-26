# Purple Copilot — Investigator Trust Boundary (experimental)

**Status: isolated working prototype; NOT production-qualified.** Stacked on #113 at 67e091104b7c78472edc217aa4627ff171216ef1. All changes reside in this new directory. No modifications to APM, active Codex adapter files, deployment, production identity systems or existing model services.

## What is implemented

- A dependency-free, single-session, in-process read boundary over four enumerated topics: path context, identity tier evidence, posture evidence and collection quality.
- Host-provided dataset, tenant, source tenant, snapshot, finding, as-of clock and authorization policy. Source observations outside the scope, lacking source tenant/lineage or received after the clock are withheld. Duplicated lineage fails closed. Input bounds and immutable scope. Unknown evidence remains explicit.
- Model projection exposes opaque per-session references, enumerated observation states and timestamps; no raw source text, native IDs, artifact pointers, URLs or arbitrary display names. The host report restores the original artifact/record pointers.
- A bounded dispatcher with no write, shell, filesystem, network or arbitrary graph query capability. It owns actual read/denial receipts and does not accept model-authored trace/effect assertions.
- Strict structured release gate: each claim requires a successful scoped read and an exact state match, every selected observation must be represented, no prose or extra fields are accepted. Re-render from host records. A denied attempt blocks release; no remediation assertion.
- Native OpenAI-compatible tool-call orchestrator, single call per turn, validated argument schema, explicit errors for incomplete/malformed output, no retransmission of arbitrary assistant prose.
- Explicit loopback-only HTTP client (no redirects or retries, timeout signal per call, bounded request and response). A local model ID and port are operator input. Optional existing gateway bearer authentication via PURPLE_LOCAL_TOKEN; never place real tokens in files or arguments.
- Deterministic report and source-cited verification plan in both modes. The priority is verification order, not measured risk or effective access. Conflicting modes remain independent observations and may concern distinct entitlements.

## Reproduction

Node.js 22 recommended. No packages to install.

```sh
cd labs/purple-investigator-security
for f in test-boundary.mjs test-runner.mjs test-transport.mjs test-triage.mjs test-mutations.mjs test-integration.mjs; do
  node "$f" || exit 1
done
node local-runner.mjs synthetic-config.json --deterministic
# Only if the owner-approved local endpoint is already running and idle:
node local-runner.mjs synthetic-config.json YOUR_LOCAL_MODEL_ID 8080
```

The endpoint is fixed to http://127.0.0.1:<port>/v1/chat/completions. No new service start, installation, port forwarding, model load or external connection is requested. For Haven/Hermes integration use the existing approved gateway; this CLI itself is restricted to local IPv4 loopback. The model needs native tool-call support. The current strict protocol is deliberately conservative: parallel calls, truncated outputs, denied operations or malformed JSON fail release instead of being silently repaired. Local output includes private lineage and scope; redact before sharing real data. Use a new unique run ID per experiment.

## Executed evidence

| Campaign | Result | Scope |
|---|---:|---|
| Boundary regressions | 54/54 | Actual JS function bodies |
| Native tool loop | 15/15 | Scripted model-shaped outputs |
| Local transport | 11/11 | Mock fetch, timeout-signal factory and UTF-8 decoder |
| Verification planner | 13/13 | Synthetic trusted release objects |
| Pipeline parity | 8/8 | Exact fetched function bodies; one shipped synthetic fixture |
| Targeted code mutations | 9/9 detected | Regression suite catches deliberately removed authorization/scope/grounding controls |

101 checks passed (93 component + 8 pipeline); 9 additional targeted mutants were detected. The first 48-check boundary result was superseded by the 54-check run. Exact committed function bodies were executed using an isolated JavaScript runtime, not the Node CLI. Recorded receipts are in this directory. The pipeline fixture required zero model calls in deterministic mode and five scripted calls in model-shaped mode, with identical canonical reports and verification plans. This is NOT a measured model-quality or latency improvement.

No real model inference, real HTTP requests, native Node filesystem CLI, timeout enforcement on a live connection, MCP integration, PyRIT, garak, production collection, or adversarial model behavior executed. No security certification.

## Trust assumptions and limitations

The application host must authenticate and authorize the user and bind the scope before creating the investigator, supply plain parsed JSON (not executable objects) and trusted normalized adapter assertions, verify artifact digests/lineage, keep the receipt/report private, and prevent access to dispatcher host methods from arbitrary code. The model must not supply config or choose scope. The prototype does not provide a full process sandbox, signed or durable audit logging, producer authentication, a publication sanitizer, a verified collector, tenant authorization, or attestation of the adapter. The in-memory receipt is host-owned, not cryptographically authenticated. Raw evidence must remain in the upstream private vault; it is not preserved here.

In particular, #112 must resolve its source-tenant attribution discrepancy before a bridge can map real EntraOps rows. Do not infer an object's source tenant from its artifact tenant. Unknown/ambiguous source tenant may remain unknown rather than being joined. Only use actual independent graph receipts for path evidence. The current scope and lineage rules are not a substitute for upstream validation.

Strict enumerated projection intentionally discards administrative prose and reduces prompt-injection exposure at the cost of context. This is not a general prompt-injection defense or classifier benchmark. The release gate currently asks the model to reproduce facts, so it offers no demonstrated added value over deterministic mode. Preserve the baseline and add carefully scoped model hypotheses/ranking only if an independent evaluation demonstrates value. The next extension should allow a separate untrusted textual evidence channel, not bypass these invariants. No classifier gets authorization authority.

## Cross-review and next acceptance gates

1. Independent reviewer reruns native Node scripts and inspects permission/scoping, lineage, errors, report release and transport bounds. Validate actual socket/timer behavior in a disposable local environment.
2. Codex runs the synthetic fixture on the already-approved local gateway with one small and one existing larger model, preserving raw private transcripts and independent host receipts. Compare success/false refusal, latency, peak RAM/VRAM, inference calls and token usage to the deterministic arm. No new models loaded or resources allocated without explicit operator approval.
3. Design the Phase 3 report bridge only after source-tenant attribution, verified lineage, adapter-level auth and time semantics are settled. Validate with synthetic pinned exporter captures and independently frozen #113 cases; maintain the reviewer-reserved qualification set outside the development branch.
4. Add PyRIT application testing via a target adapter with a distinct mock service and deterministic receipt-based scorer, and focused garak local-model comparison. Pin versions and ensure local execution. No real exfiltration, offensive actions, tenant targets or cloud inference. Use benign controls and false-refusal scoring; evaluate lightweight classifiers as advisory signals only.
5. Do not auto-merge, deploy, or promote a model. Native CLI/live gateway results and independent review are prerequisites, not implied by this PR.

