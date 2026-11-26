# Meridian 01 — Specialist fleet and parameter-efficient cybersecurity

Date: 2026-11-26. Research synthesis of the prior Meridian discussion. All proposed callsigns, estimated size classes and priorities are hypotheses, not deployed systems or measured Haven 4B outcomes.

## Thesis

Instead of making one 4B a miniature frontier generalist, specialize by domain and cognitive function. A local system can combine compact recognition models, bounded 2–4B reasoning workers, deterministic semantic engines, external memory, typed tools and verification. Study whether useful system-level performance approaches stronger models with no neural component exceeding 4B in the primary experimental arm. Larger references or human escalation are separate arms, not hidden contributors to the 4B result.

External mixture of experts is an analogy, not an internal neural MoE. Independent workers can be replaced, benchmarked and qualified separately. Experts pass evidence IDs and bounded claims, not free-form conclusions that become facts.

## Empirical anchors

- Cisco Antares: compact 350M, 1B and 3B agentic vulnerability-localization models. VLoc benchmark file F1 reported in previous research: Antares-3B 0.223, Antares-1B 0.209, GPT-5.5 0.229. This indicates parameter efficiency on advisory-assisted localization, not solved vulnerability discovery. Low absolute F1 matters. See https://cisco-foundation-ai.github.io/antares/ and https://cisco-foundation-ai.github.io/vulnerability-localization-benchmark/ and https://arxiv.org/abs/2608.02407.
- CyberPal 2.0: 4B–20B cybersecurity-specialized family, reported strong threat-investigation results. See https://proceedings.mlr.press/v306/levi26a.html. Validate exact task, model, data and licensing before reproduction.
- EffectWorld: effect-typed tools and executable traces. Author-reported Qwen3-4B adapter success 53→99% in distribution, 52→81% unseen task kinds plus distractor tools, 74→83% unseen domain; BFCL multi-turn improvement is smaller. Preprint, not a Haven replication. See https://arxiv.org/abs/2610.35981.
- Log severity classification: reported 95.64% for retrieval-assisted Qwen3-4B; this is narrow classification, not incident investigation. See https://www.mdpi.com/2073-431X/15/7/430.
- DefenderBench: standardized task environments and interfaces for security agents. https://github.com/microsoft/DefenderBench. Treat different task families separately.
- Source/binary representation is not interchangeable. Candidate comparison: LLM4Decompile (https://github.com/albertan017/LLM4Decompile), compact domain-specialized decompilation; test functionality, not just text resemblance. Hard local vulnerability reproduction results (https://arxiv.org/abs/2611.06257) motivate separating reasoning from artifact construction. No direct numerical transfer to Haven claimed.
- Model cascades: https://arxiv.org/abs/2305.05176 (FrugalGPT). Local escalation need not incur API spend.
- Existing Haven 9B cyber results are useful priors but not 4B evidence. Adapter regression in the earlier held-out comparison makes specialization a hypothesis, not a default improvement.

## Specialist lanes

| Callsign | Scope | Representation / deterministic substrate | Initial use |
|---|---|---|---|
| Sentinel | Microsoft, Entra, AD, M365, Azure identity | tenant snapshots, principal/resource/policy graph, effective policy evaluators, Maester, ScubaGear, BloodHound, Graph | first slice: offline identity posture and evidence-backed explanations |
| Watchtower | SOC/logs/detection | OCSF events, entity and temporal joins, Sigma/pySigma, query engine | triage, corroboration, competing benign and suspicious hypotheses |
| Scalpel | application/code security | SARIF, symbols, AST/dataflow, existing analyzers and HDF | localization, evidence-bound triage, bounded patch proposals |
| Atlas | networking | topology, flow records, routing/ACL semantics, Batfish, Zeek | reachability and policy explanations, configuration-diff review |
| Citadel | cloud posture | resource graph, IAM/RBAC, Prowler, policy evaluators | configuration and permission review |
| Stratum | low-level systems | binary metadata, disassembly, xrefs, CFG, crash evidence, Ghidra | defensive reverse-engineering assistance and crash triage |
| Archivist | digital forensics | normalized artifacts, timelines, parsers, Timesketch | artifact correlation, time ordering, evidence-backed reconstruction |
| Harbinger | threat intelligence | STIX, observables, temporal validity, advisory and asset relationships | IOC/advisory correlation and grounded interpretation |

Scout/analyst/repair roles within Scalpel could be different model sizes. Recognition/extraction may need only hundreds of millions of parameters or no model at all. Tool selection may use deterministic routing, compact classifiers or the 4B. Global planning remains a likely bottleneck.

Earlier qualitative priors placed bounded identity, cloud, SOC and code localization above low-level novel reasoning and open-ended investigation. Those are not calibrated performance percentages. Measure risk/coverage curves rather than promising a universal accuracy target.

## Training design

First measure unchanged base with and without architecture. Train only residual deficits. Candidate shared-base LoRA experiments should use a pinned base/tokenizer/template, matched inference settings and individually qualified adapters. Test merged/quantized artifact behavior separately. Do not assume a trained adapter improves unrelated domains.

Teach four types of skill: declarative knowledge, procedure, counterfactual conditional reasoning and epistemic discipline. Data: verified explanations, causal successful trajectories, independently corrected failures, near-miss negatives, stale/current evidence, benign lookalikes, insufficient evidence, conflicts and unfamiliar representations. Example Sentinel variants change report-only vs enforced status, active vs expired role, included vs excluded group, identity ID vs display name; irrelevant changes should not flip the answer. Existing W1/W2 qualified trace method is the conceptual starting point, not authorization to reuse private material.

Initial 1,000–3,000 verified trajectories per specialist is a proposed learning-curve experiment, not a known sufficient quantity. Hold out task templates, source assets, time and representations. Use deterministic semantic oracles where feasible; human review for residual ambiguity.

## Fleet alternatives

Compare single specialist, shared-base adapter fleet, hierarchical delegation, independent ensemble, and selective cascade. Start with one model and sequential domain skills, not simultaneous workers. Router must choose from already-authorized skills. Use only canonical references across handoffs; independent verification must not mistake repeated model claims for multiple sources.

Raw idealized 4-bit 4B weights occupy about 2 GB decimal, excluding quantization metadata, runtime/KV, unquantized tensors and other tensors. Sequential residency is a sensible first candidate for constrained GPUs; measure actual memory, load latency, prefill/decode and tool latency. No assumption that all specialists can reside at once.

## Evaluation and roadmap

1. Architecture ceiling with frozen base (R0–R6).
2. Sentinel/Watchtower pilots with tools-only comparator and specialist adapters only for residual gaps.
3. Scalpel using source localization, independent defensive discovery (separate tasks) and HDF verification.
4. Cross-domain evidence handoffs and disagreement tests.
5. Distribution shift, missing telemetry, representation changes, harder defensive analysis.
6. Integrate qualified specialists into factory lifecycle; no autonomous promotion.

Metrics: success, source/evidence precision, novel findings, false positives and negatives, calibrated abstention, coverage, tool recall and misuse, actual dispatch vs model intent, verifier intervention, retries, compute, latency, human review. Compare deterministic tools alone, raw and scaffolded 4B, trained and untrained under the same architecture, multiple experts vs single worker at matched cost, and larger reference systems.

Use a common evidence graph and verifier, not a chat transcript as the system of record. See next installment for concrete integration contracts.
