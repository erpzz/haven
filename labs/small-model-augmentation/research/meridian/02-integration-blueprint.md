# Meridian 02 — Integration blueprint: from upstream research to local working system

Date: 2026-11-26. Proposal, not implemented. All upstream results are author-reported. Source pages consulted on this date; dependency versions and licenses must be checked before adoption.

## Decision

The scarce resource is not the number of AI models or scanners. It is interoperability: semantic evidence, tool authority, bounded workflow state, model handoffs and verification. Integrate thin vertical slices, using upstream engines as computational specialists rather than replacing them with language-model reasoning. Do not build a parallel runtime or general SIEM.

## What Haven already has (source review)

Reviewed #216 exact head 36322d74e78a08a297ccc45ad5639e3e677c7af5:
- labs/cyber/docs/research/SECURITY_EVIDENCE_SCHEMA.md: haven-cyber-evidence-v1, artifact SHA-256, observations with JSON pointers, distinct findings and independently derived verification status.
- labs/cyber/docs/research/CYBER_ARCHITECTURE.md: versioned Markdown retrieval, compact four-tool Cyber MCP facade, offline CA/RBAC semantics, normalizers, verifier and controlled evaluations.
- labs/cyber/docs/research/OPEN_SOURCE_INTEGRATION_MATRIX.md: Maester and Prowler adapters tested on fixtures; upstream live runs not established. Existing crosswalk distinguishes policy existence from principal coverage. Preserve this nuance.
- labs/hermes/docs/ARCHITECTURE.md: operator MCP wraps engineer/fleet controllers, uses separate change tools, approvals and receipts.
- labs/small-model-augmentation/EVIDENCE_ADMISSION_README.md: strict artifact/observation/finding lineage, validation and producer-status gate; does not authenticate producer or independently establish domain truth.
- #186 HDF candidate: evidence-bound repair proposal, isolated worktree, fixed checks and landed closure.
- #189 HRF candidate: synthetic adversarial cases, intent vs actual dispatch.
- #205 controlled evaluation and receipt contract; #216 guarded runtime; #215 and #221 target-platform evidence tooling. CI does not prove actual target-Mac/model behavior. Do not assume these drafts merged or qualified.

Source links: https://github.com/erpzz/haven/pull/186 ; https://github.com/erpzz/haven/pull/189 ; https://github.com/erpzz/haven/pull/205 ; https://github.com/erpzz/haven/pull/216 ; https://github.com/erpzz/haven/pull/215 ; https://github.com/erpzz/haven/pull/221.

## Research-to-engineering translation

| Upstream | What to adopt | What not to infer | Candidate destination |
|---|---|---|---|
| Antares (https://cisco-foundation-ai.github.io/antares/) | Specialized locator/ranker and evaluation methodology; bounded advisory-assisted repository navigation | F1 parity on one localization benchmark is not general bug discovery or patch verification | Scalpel benchmark/optional candidate |
| CyberPal 2.0 (https://proceedings.mlr.press/v306/levi26a.html) | Domain-specialized small-model comparison, structured threat-investigation tasks | No guarantee on our tenant data or tool protocol | Harbinger/Sentinel comparative model/data study |
| EffectWorld (https://arxiv.org/abs/2610.35981) | Effect typing, explicit resource identity and deterministic trace replay, near-miss training | Model compliance is not authorization | Existing guarded runtime + development trajectory generation; no new authority |
| SWE-agent ACI (https://arxiv.org/abs/2405.15793) | Treat interface design as an experimental variable; compact, actionable tool responses | Full shell access is not necessary or appropriate in strict profiles | Domain skills and evidence views |
| ALERT-BENCH/AIDA (https://arxiv.org/abs/2610.10608) | Independent challenge, append-only investigation ledger, higher burden before dismissal | Not a 4B result; one study cannot establish production generalization | Watchtower selective review |
| SIR-Bench (https://arxiv.org/abs/2604.12040) | Measure evidence newly discovered beyond the initial alert, tool appropriateness, false-positive rejection | Author benchmark uses LLM-based judging and release availability must be checked; not an independent deterministic oracle | Watchtower evaluation |
| DefenderBench (https://github.com/microsoft/DefenderBench) | Standard task environment/agent interface and separate capability categories | Not an apples-to-apples score without environment and model controls | Development-only adapter |
| Agent Skills (https://github.com/agentskills/agentskills) | Progressive disclosure of domain workflow knowledge | SKILL.md is not a permission grant | Existing Haven skill system |
| LangGraph checkpointing (https://docs.langchain.com/oss/python/langgraph/persistence) | Durable graph state, explicit interrupts and recovery pattern | Do not run a second agent runtime by default; side effects must be reconciled | Reference for existing engineer/checkpoint controller |
| OpenHands SDK (https://github.com/OpenHands/software-agent-sdk) | Modular tool/agent interfaces as a comparative scaffold | No broad shell agent for strict profiles; no dependency until need proven | Reference/optional development comparison |

AIDA authors report 1,247 alerts from a multi-stage scenario; five comparison approaches miss at least 40.4% of attack alerts. Their proposed independent-challenge workflow reports F1 0.958 vs 0.371–0.744, 3.1% false-negative rate and 18.4% analyst escalation. Same-context review had negative net correction. These are study-specific results, not proof of 4B parity. SIR-Bench reports 794 cases from 129 anonymized patterns; their agent reports 97.1% true-positive detection, 73.4% false-positive rejection, 5.67 novel key findings per case and 41.9% novel-finding coverage on TP cases. Investigative depth matters even when disposition accuracy looks high. Start with a deterministic challenge checklist; evaluate independent model review only where residual ambiguity justifies the compute.

## Standards are complementary, not interchangeable

- OCSF (https://github.com/ocsf/ocsf-schema): security event/finding vocabulary. Use for imported event/finding records, not the entire investigation database.
- SARIF (https://docs.github.com/en/code-security/reference/code-scanning/sarif-files/sarif-support): scanner locations/rules/fingerprints. Preserve original location and source bytes; canonicalization is reversible, not a replacement for evidence.
- STIX 2.1 (https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html): threat intel interchange, observed data vs indicators; not proof an asset is compromised.
- W3C PROV (https://www.w3.org/TR/prov-dm/): conceptual Entity/Activity/Agent provenance; use its concepts without requiring RDF deployment.
- OpenTelemetry (https://opentelemetry.io/docs/specs/otel/logs/data-model/): correlate system runs/logs/spans; not the security evidence itself. Separate operational telemetry from evidence; redact and keep private by default.
- MCP (https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/): tool transport/discovery. Hints are not trustworthy authorization; host owns policy. OWASP guidance: https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html.
- OPA (https://www.openpolicyagent.org/docs): useful reference for decision/enforcement separation; defer installing until policies outgrow existing exact-target gates.

## Domain tool reuse

| Domain | Candidate upstream | Import/adapter boundary |
|---|---|---|
| Microsoft | Maester https://maester.dev/ ; ScubaGear https://github.com/cisagov/ScubaGear ; BloodHound https://github.com/SpecterOps/BloodHound ; Graph https://learn.microsoft.com/en-us/graph/overview | Read-only snapshots / JSON / identity graph; existing Maester normalizer first |
| Cloud | Prowler https://github.com/prowler-cloud/prowler | Existing OCSF importer; independent criterion-level verification |
| Code | SARIF/CodeQL/Semgrep | Scanner output and exact commit/file/line evidence; use HDF for candidate verification |
| Logs/network | Zeek https://docs.zeek.org/en/current/tutorial/logs.html ; Sigma https://sigmahq.io/docs/digging-deeper/backends ; OCSF | Bounded event queries, normalized results and explicit time/coverage |
| Network config | Batfish https://github.com/batfish/batfish ; https://batfish.readthedocs.io/en/latest/notebooks/differentialQuestions.html | Offline snapshots, deterministic reachability/config change analysis; only supported semantics |
| DFIR | Timesketch https://github.com/google/timesketch | Import/export forensic timeline records, retain original evidence |
| Low-level | Ghidra https://github.com/NationalSecurityAgency/ghidra | Static analysis artifacts and defensive crash triage; deferred until a qualified lab |
| Threat intel | STIX 2.1, MITRE ATT&CK, vendor advisories | Stable IDs and observation validity; no unsupported attribution |

Adopt no dependency solely because it is popular. Record source revision, license and data terms, output schema, side effects, prerequisites, supported coverage, cost, fixture tests and replacement plan. Prefer offline import before executing upstream tools. Treat the 2026-10-31 Haven upstream matrix as historical; do not silently refresh versions without review.

## Six contracts (conceptual, not frozen schemas)

1. Artifact/Evidence: extend or wrap existing haven-cyber-evidence-v1 rather than invent a conflicting format. Raw artifact digest, namespace, observation pointer, source/tool version, event time vs collection time, asset and principal scope, completeness and privacy. Derived facts reference input observation IDs and evaluator version. Preserve unrecognized fields in source artifact, not lossy flattening.
2. Claim: typed subject/predicate/object or bounded domain claim, evidence IDs, counter-evidence IDs, as-of time, status (proposed/corroborated/refuted/insufficient), limitations. Only independent verifier changes verification status. Do not treat a second model repeating a claim as corroboration.
3. Skill: host-reviewed input/output schema, supported domain, allowed effects, target constraints, preconditions, timeout, maximum calls/bytes, verifier, recovery policy. Policy can only narrow the already approved set. A schema, skill instruction or tool annotation does not grant permission.
4. Work item: goal, case/run identity, open questions, permitted evidence references, dependencies, budget and current stage. Scheduler chooses eligible skill, never model-authored unrestricted commands. External workers cannot see private/unrelated state.
5. Handoff: producer/model/adapter identity, exact task and evidence refs, proposed claims, unresolved questions, requested next skill, verification result. Receiver rechecks artifact identity, source authority, authorization and applicability. No shared unbounded conversation; lineage must prevent circular corroboration.
6. Receipt: exact input/state/policy/model/tool identities, proposals and dispatches separated, observations, output, verification and resource use. Idempotency key and durable transitions. Unknown effects after interrupted execution require reconciliation, not blind replay. Hashes provide integrity, not truth or authentication.

Canonical asset resolution must use tenant/namespace + stable object ID; similar display names are not joins. Stale records remain available with time/authority labels. Empty result, query failure, incomplete collection and verified absence are different. Cross-domain evidence joins require identity/time compatibility; ambiguity is surfaced instead of silently resolved.

## Proposed local architecture

    Upstream artifact / live read adapter (later, separately authorized)
      -> raw immutable artifact store
      -> domain normalizer
      -> evidence admission
      -> domain semantics engine / independent re-derivation
      -> compact model-facing evidence view
      -> bounded skill (existing base or qualified specialist)
      -> proposed claim / next evidence request
      -> guarded dispatch and verification
      -> persistent case state + receipt
      -> optional independent challenge / escalation
      -> verified report / authorized remediation proposal
      -> HDF verification or human review where appropriate

Use SQLite for case state/index only if existing controller cannot provide it. Content-addressed files for raw private artifacts. Views are derived, rebuildable, bounded; prefer FTS and typed filters before embeddings. Event-sourced state need not mean a distributed event bus. No Kafka, vector DB, new framework, multi-agent fleet or cloud API required for initial slice.

## First vertical slice: Sentinel + Watchtower (offline)

Input: existing synthetic tenant snapshot and scanner exports plus a small independently generated synthetic event timeline. User question: explain an identity-control finding and whether the relevant observed activity corroborates it; distinguish control weakness from actual compromise. No live tenant or production data.

1. Use existing Maester/Prowler/Haven fixtures and normalizers; preserve source check IDs and raw pointers.
2. Independently compute the relevant CA/RBAC facts; distinguish criterion existence vs coverage.
3. Add a thin timeline-import adapter for a documented subset of OCSF or native event records, with source and time mapping tests.
4. Join on stable synthetic tenant/principal/device IDs; retain unmatched/ambiguous events explicitly.
5. Construct small evidence views and bounded read-only tools using existing guarded runtime; reuse existing Cyber facade, do not expose raw shell.
6. Same unchanged 4B uses Sentinel skill to propose a finding and Watchtower skill to interpret corroborating observations. Can run sequentially under one model lease; independent context for challenge only.
7. Host verifier checks claim pointers, semantics, freshness and scope. Challenge ambiguous dispositions with a separate context restricted to same evidence; no evidence-free dismissal. Output verified facts, proposed conclusions, missing data and next checks.
8. Record intent, actual dispatch, verifier outcome, time/tokens and exact fixture/source hashes. Never use reserve cases.

Acceptance tests (development only): stale evidence; same display name/different IDs; missing event collection; contradictory sources; policy existence vs coverage; benign event vs confirmed observation; tool failure vs zero records; injected instruction as data; permission/target mismatch; interrupted run and duplicate suppression. Invalid or unsupported cases must remain unknown. No unauthorized dispatch. No inference of actual compromise solely from configuration weakness. Verification must not read hidden gold at runtime.

Second slice: Scalpel/HDF, using authorized defensive code fixtures and SARIF adapter. Keep advisory-assisted localization distinct from discovery. Fixed host test recipes, independently validated patch and exact landed verification. No automatic code merge/deployment.

## What to measure

Primary comparison (fixed weights and matched budgets): deterministic tools only; raw 4B; existing Haven baseline; evidence-shaped + bounded skills; cross-domain handoff; selective independent challenge; full integrated system. Then remove-one ablations. Compare natural-budget separately. Run equal-cost single-model retry vs two-role review to test whether independent context adds value. Run 4B specialist training only after W1/W2 qualification and separate authorization. Evaluation references may include larger local models, not required for early development.

- correct disposition and source-level claim precision/recall
- discovery of new validated facts beyond initial alert
- abstention coverage, false negatives/positives, escalations
- join accuracy and handoff loss / contradictory claims / circular support
- model-proposed vs actual calls; target/effect violations
- verification and recovery salvage, latency, tokens, peak RAM/VRAM
- no-model baseline and human-review workload
- distribution shift across generator templates, source formats and time

Preregister case strata, sample sizes, fixed cost/tool budgets, failure handling, review criteria before execution. Report intervals and per-family results; no extrapolation of external study scores. For reproducibility, freeze adapters and fixtures, check for evaluation leakage, preserve actual receipts and independent review. Do not train on held-out benchmark examples.

## Delivery sequence and stop conditions

M0: schema/interface audit and mapping table against exact candidate source; decide reuse vs adapter vs defer. M1: offline Sentinel/Watchtower two-skill slice and deterministic tests. M2: unchanged local 4B real run under admitted runtime; compare no-model and current baseline. M3: independent challenge ablation and failure catalog. M4: add Scalpel/HDF integration only after earlier runtime qualification; add Atlas/Citadel as demonstrated demand. M5: evaluate specialists/adapters independently and cross-domain fleet only if architecture-only baseline leaves a meaningful gap.

Stop on missing qualified runtime, invalid evidence, ambiguous authority, state/receipt mismatch, unsupported schema, or material test defects. No W2/training/reveal/qualification changes, reserve access, live tenant access, automatic remediation, arbitrary offensive execution or merge authority from this research note.

## Open questions

- Can existing evidence-v1 represent temporal joins without loss, or is a small envelope extension needed?
- Which existing engineer/recovery interfaces should own the case state? Avoid a second scheduler.
- How much of the result is deterministic tools alone? What useful marginal decision does a model contribute?
- Are independent challenges worth their latency on the actual 4B? Can deterministic coverage checks handle most?
- What is the smallest useful evidence view for each domain? Measure recall and distraction before introducing new retrieval infrastructure.
- Which tool/benchmark releases and licenses actually allow local reproducibility and adaptation?

These are next research/engineering questions, not established results.
