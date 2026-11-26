# Purple Copilot runtime assurance v2 / HARE contract proposal

Stacked on draft #114 at b46c64e8e0f3876baa24c91ecfb9e4a4332a7e8d. Additive opt-in modules under v2; original v1 and its receipts intentionally unchanged. Consumers must explicitly import v2. No application integration, approval, merge or deployment. This is author self-review and needs Codex/Claude independent challenge.

## Controls

- Early deny before reading evidence in openSession; the application must separately authenticate/authorize before fetching configuration or vault data. The boolean is a trusted host input, not authentication. Denial receipts contain no evidence counts.
- Per-topic supplied/rejected counts, partial/unavailable status, explicit assessment completeness not established, and a priority-one verification task when input was rejected. Report counts are private to the authorized host. A surviving record never implies completeness.
- Strict raw JSON validation for duplicate keys, escaped duplicate keys, depth and byte limits at dispatcher, answer, tool arguments and HTTP ingress. The inherited transport still parses validated text; injected callbacks must provide equivalent strict raw ingress. Malformed UTF-8/JSON HTTP responses produce protocol_json; network failures remain transport_error. Non-finite numbers are rejected.
- Expected exact model ID compared to each reported ID; duplicate tool call IDs and explicit refusals block release. Per-turn usage is validated and aggregated only when complete. Label equality is not artifact attestation. No verified model provenance claimed.
- A module-private WeakSet brands deep-frozen release objects. verifiedPlan and hypothesis functions reject forged/deserialized copies. This proves only in-process origin from this module, not authorization, signature, persistence or authenticity of upstream evidence; retain the original branded object inside the trusted host. The v1 exported planner is not a secure integration entry point.
- Bounded hypothesis vocabulary and independent premise checks over actually released observations. Verification is rule-derived, not the benchmark grader or reserved answers. Accepted proposals are unresolved supported interpretations, not verified causal claims. Suggested priority is advisory. Proposed collection actions and escalation never execute or convey authorization.

## HARE/Purple contract (proposed, model-agnostic)

Reviewed HARE System 0 #115 at 5f088677fb08701562d9bd0236e23eb9b3aa4e50: annotations derived from request and retrieved data are useful hints, not enforcement. No edits to HARE or Codex files. The following separates HARE policy/routing from Purple evidence and authorization. Current module implements the observation/candidate/release subset; cross-process adapter and durable receipt schema are proposals, not implemented.

| Type | Fields / ownership |
|--|--|
| Scope | version, run, tenant, dataset, finding, snapshot, asOf; host binds principal and authorization independently |
| Typed evidence | opaque ref, topic, observation state, observed time; host-only artifact/record lineage, source tenant, receipt time, scope and coverage; raw description stays untrusted |
| Validated proposition | source observation: ref + state; host reconstructs canonical report; producer authentication and completeness separate |
| Hypothesis candidate | run, proposals[] with kind, refs[], priority 1..3; never authoritative; no arbitrary commands or free-form claims |
| Verification result | accepted[] with supported_interpretation_unresolved_hypothesis, refs, suggestedPriority, meaning; rejected[] with index/reason; invalid_candidate for schema/parse failure |
| Investigation action | kind, authorization not_granted, execution not_executed; a future centralized host would issue an expiring capability bound to scope, principal, operation and parameters after policy evaluation |
| Escalation | requested, reason, authorization not_granted; HARE selects bounded candidate route; host decides budget, data scope and egress before invocation |
| Execution receipt | run/snapshot, actual dispatch events and returned refs, denied count/overflow; owned by dispatcher; durable version must bind scope/principal, exact input/output hashes and monotonic event sequence |
| Inference receipt | expected/reported model, per-turn wall time and usage or null; verified backend artifact hash/runtime/quantization and egress attestation separate; no missing usage as zero |

System 0 may enumerate choices or annotate observations; Tier 1/2 may select and rank candidate hypotheses. The verifier accepts evidence-supported possibility, not causality. Unsupported proposals remain visible in private receipts. Never give a model direct access to the host's authorized flag, release constructor, tool dispatch methods, arbitrary artifact pointers or credentials. Cross-process transport needs an authenticated session, signed/bound receipts, replay protection, explicit schema and host re-verification. This is not a new common runtime.

## Reproduce (Node 22, no dependencies)

From labs/purple-investigator-security:
    for f in test-boundary.mjs test-runner.mjs test-transport.mjs test-triage.mjs test-integration.mjs test-mutations.mjs; do node "$f" || exit 1; done
    node v2/test-v2.mjs
    node v2/test-campaign.mjs
    node v2/run-v2.mjs deterministic base

The original six scripts ran 101 checks and 9 detected mutations; v2 ran 18 tests, 9 new mutations detected, and three real ephemeral loopback HTTP assertions (scripted responses, no inference). See execution receipt. Five public variants exercise base, conflict, partial, missing and passing posture. The scripted subset produced zero novel hypothesis kinds beyond exhaustive enumeration; no actual model comparison has been conducted. One deterministic CLI run: four claims, four verification tasks, four enumerated hypothesis types, 1.911676 ms baseline calculation and 26228 KiB process peak RSS on isolated Linux Node 22.16.0; single run, not hardware qualification.

Only on the approved already-running local backend, after confirming model residency and no remote forwarding:
    umask 077
    node v2/run-v2.mjs observe base LOCAL_MODEL_ID PORT > private-observe.json
    node v2/run-v2.mjs hypotheses conflict LOCAL_MODEL_ID PORT > private-hypotheses.json

Use actual model ID and port; no service start or model load implied. The runner saves responses from parsed transport (not raw wire bytes), usage when available, timings and client process RSS; server RAM/VRAM require independent telemetry. Repeat both arms for all five cases with randomized/alternating order and stable configuration; compare meaningful additional hypotheses, missed questions, unsupported proposals, task priority utility and false refusals on benign cases. These cases are public and suite-aware, not held-out. Independent adjudicators need separate frozen cases and a broader typed relationship vocabulary. No model access from this session. PyRIT/garak not installed in the sandbox; no integration compatibility or framework runs claimed.

## Remaining gates / stop conditions

Do not promote v2 until independently reviewed. Closed vocabulary is enumerable: **deterministic enumeration is the default**; model accuracy or additional utility has not been shown. The verifier currently checks coarse state compatibility, not same-assignment identity, temporal overlap, causal linkage or sufficient context. Do not infer compromise, activation or remediation. Candidate priorities are unverified. No free-form log channel or general injection robustness claimed. Runtime egress policy must independently constrain the backend, including gateway forwarding; loopback alone does not prove local inference. Authenticate source artifacts and repair #112's source-tenant discrepancy before connecting real adapters. Enforce process isolation and whole-session deadlines, quotas, context/response budgets and bounded concurrency; the inherited HTTP per-call limit is not a total session budget. Audit strict JSON parser further (including numeric precision and Unicode semantics) and use reviewed parser or schema tooling in production. Instrument protocol vs transport failures, authorized action execution, verified model provenance, durable receipts and raw evidence redaction before production. No changes to existing application runtime. No auto-merge or deployment.
