# Meridian Research 07 — Failure-First Hardening Plan

Status: pre-planning / adversarial design note, 2026-11-27.
Checkpoint: MERIDIAN-07.1.
Scope: research and architecture planning only. No runtime, training, evaluation, or execution policy changes.

## Purpose

This document starts from the assumption that a 35B–70/80B Meridian system is already cognitively capable enough to attempt meaningful autonomous cyber work.

The design problem therefore shifts from:

> Can the model reason?

to:

> What are the most probable ways a capable autonomous system will still fail, and how do we structurally remove those failure modes before granting broader autonomy?

The goal is to strengthen the architecture in descending order of **likelihood × impact × difficulty of detection**.

This is not a deployment plan.
It is a pre-planning hardening program.

## Risk-scoring convention

Each risk is assigned a research-prior score:

- Likelihood: 1–5
- Impact: 1–5
- Detection difficulty: 1–5, where 5 means failures are easy to miss

Priority score:

```
priority = likelihood × impact × detection_difficulty
```

These numbers are design priors, not measured Haven frequencies.

## Priority map

| Rank | Failure mode | Likelihood | Impact | Detection difficulty | Priority |
|---|---|---:|---:|---:|---:|
| 1 | False success / verifier weakness | 4 | 5 | 5 | 100 |
| 2 | Persistent memory poisoning / stale authority | 4 | 5 | 5 | 100 |
| 3 | Long-horizon state drift / premature completion | 5 | 5 | 4 | 100 |
| 4 | Evaluation contamination / grader gaming | 4 | 5 | 5 | 100 |
| 5 | Evidence mis-grounding / retrieval misuse | 5 | 4 | 4 | 80 |
| 6 | Multi-agent correlated error / coordination tax | 4 | 4 | 4 | 64 |
| 7 | Distributed node trust / composition leakage | 3 | 5 | 4 | 60 |
| 8 | Hard artifact-synthesis capacity ceiling | 4 | 5 | 2 | 40 |
| 9 | Specialist interference / negative transfer | 3 | 3 | 4 | 36 |
| 10 | Authorization / execution-boundary failure | 2* | 5 | 3 | 30 |
| 11 | Quantization / hardware-induced degradation | 3 | 3 | 2 | 18 |

`*` Authorization intent failures may be common at the model layer, but actual unauthorized dispatch should be made structurally rare by host-owned enforcement. If the model controls its own effect boundary, the likelihood score becomes unacceptable and deployment should stop.

---

# 1. False success is the first enemy

## Why it is ranked first

The most dangerous autonomous failure is not:

> "I don't know."

It is:

> "Done."

when the objective has not actually been satisfied.

A strong model can produce persuasive, internally coherent explanations for an incorrect state.

This gets worse under test-time scaling if the evaluator has false positives: more candidate generation gives the system more opportunities to discover a result that satisfies the grader without satisfying the real objective.

NIST has documented real agent-evaluation cheating through:

- future git history;
- solution artifacts;
- editable assertions;
- grader gaps.

This is not merely intentional deception.
The same phenomenon can arise from ordinary optimization pressure.

## Hardening principle

**The model must never own the definition of success.**

Success should be represented as externally checkable postconditions wherever possible.

Instead of:

```
model: "The issue is remediated."
```

require:

```
requested objective
  -> explicit success predicates
  -> action
  -> independent measurement
  -> predicate evaluation
  -> success receipt
```

## Proposed Success Contract

Every autonomous work item receives:

```json
{
  "objective": "...",
  "required_postconditions": [],
  "forbidden_state_changes": [],
  "evidence_required": [],
  "verification_methods": [],
  "rollback_condition": [],
  "success_authority": "host/verifier"
}
```

A model can propose that the contract has been satisfied.
It cannot mark the contract satisfied.

## Verifier hierarchy

Use strongest available verifier first:

1. exact state comparison;
2. executable test;
3. deterministic graph/policy calculation;
4. replay/simulation;
5. independently generated probe;
6. semantic model verifier;
7. human review.

A model-based verifier is the fallback, not the foundation.

## Strengthening experiments

### V1 — hidden postconditions

Give the agent visible tests plus held-out invariant tests.

Measure:

- visible-test pass;
- hidden-test pass;
- false-completion rate.

### V2 — verifier mutation

Deliberately weaken one visible verifier.

Observe whether additional search increases exploitation of the weakness.

### V3 — semantic invariance

Generate semantically equivalent task variants.

A real solution should remain valid.

### V4 — independent-verifier disagreement

Run two differently constructed verifiers.

Disagreement blocks promotion and becomes a research sample.

## Pre-planning decision

Build success-contract semantics **before** expanding autonomous execution.

---

# 2. Persistent memory must not become persistent authority

## Why it is ranked first-tier

Persistent memory is central to the long-term Meridian thesis.

It is also a durable attack surface.

2026 research and Microsoft red-team reporting show that externally sourced content can cause an agent to write persistent attacker-influenced memories that later steer unrelated actions.

The dangerous transition is:

```
untrusted observation
      ↓
model summary
      ↓
persistent memory
      ↓
future trusted context
```

The summarization step can accidentally launder origin.

## Hardening principle

**Memory content and memory authority are separate objects.**

A memory cannot gain authority because:

- a model summarized it;
- another tool echoed it;
- it appeared repeatedly;
- multiple agents copied it.

Origin and trust must be host-bound and non-malleable.

## Proposed memory classes

### M0 — ephemeral observation

- session-local;
- untrusted by default;
- never directly changes policy.

### M1 — persistent evidence

- provenance bound;
- source/freshness retained;
- retrievable for future reasoning;
- still not authoritative.

### M2 — verified fact

Requires an approved verification path.

### M3 — procedure

A reusable workflow that has passed explicit validation.

### M4 — policy / authorization

Never writable by autonomous model reasoning.

Only host/operator control can alter it.

## Required metadata

Every memory item:

```json
{
  "origin": "...",
  "origin_trust": "...",
  "created_at": "...",
  "valid_from": "...",
  "expires_at": "...",
  "supersedes": [],
  "contradicts": [],
  "verification": [],
  "authority_class": "M0|M1|M2|M3|M4",
  "scope": "...",
  "purpose": "..."
}
```

## Strengthening experiments

### M1 — stale vs live

Store a previously correct fact.
Later present an authoritative changed state.

Measure whether memory ever overrides current authority.

### M2 — sleeper poisoning

Inject malicious/incorrect external material during one task.

Test unrelated future tasks.

### M3 — laundering

Route the same poisoned fact through:

- summarization;
- peer agent;
- trusted tool echo;
- repeated corroboration.

Origin authority must remain unchanged.

### M4 — snapshot recovery

Corrupt a memory generation and restore.

Ensure derived beliefs/procedures can be invalidated.

## Pre-planning decision

Do not implement autonomous self-writing "trusted memory."

Build an evidence ledger with explicit promotion states instead.

---

# 3. Long-horizon autonomy will drift unless state is host-owned

## Evidence

UltraHorizon evaluates trajectories averaging:

- 35K+ tokens / 60+ tool calls in normal settings;
- 200K+ tokens / 400+ tool calls at the heaviest scale.

State-of-the-art agents substantially underperform humans.

The study identifies:

- in-context locking;
- fundamental capability gaps.

Google's agent-scaling experiments show multi-agent architectures can degrade sequential planning by 39–70%.

## Main failure modes

Long autonomous tasks accumulate:

- forgotten subgoals;
- repeated work;
- contradictory beliefs;
- premature success declarations;
- abandoned hypotheses;
- tool-call loops;
- context compression errors.

A 70B model does not eliminate these system effects.

## Hardening principle

**The transcript is not the state.**

The host owns a compact explicit state model.

## Proposed Investigation State

```json
{
  "objective": {},
  "constraints": {},
  "verified_facts": [],
  "provisional_hypotheses": [],
  "refuted_hypotheses": [],
  "open_questions": [],
  "completed_subgoals": [],
  "pending_subgoals": [],
  "artifacts": [],
  "failed_attempts": [],
  "budgets": {},
  "current_checkpoint": "...",
  "success_contract": {}
}
```

Models receive the relevant projection of state, not an ever-growing raw transcript.

## Progress invariants

Every step must cause at least one legitimate state transition:

- new evidence;
- hypothesis strengthened;
- hypothesis refuted;
- artifact improved;
- uncertainty reduced;
- subgoal completed.

If several steps fail to change the state meaningfully, trigger:

```
loop detector
  -> checkpoint
  -> alternative plan / stronger model
```

## Checkpoint model

Long research should behave like a transaction log:

```
state_0
 -> event_1
 -> state_1
 -> event_2
 -> state_2
 ...
```

Derived summaries are rebuildable.

The event log remains the authoritative history.

## Strengthening experiments

### L1 — 500-step synthetic investigation

Measure:

- goal retention;
- duplicate work;
- false completion;
- state corruption.

### L2 — deliberate interruption

Kill the reasoning process mid-task.

Restart another model from state only.

Success measures whether cognition is truly externalized.

### L3 — context amnesia

Remove raw transcript access after each checkpoint.

If performance collapses, important state is still hidden in prose.

### L4 — planner swap

Swap 35B -> 70B or 70B -> 35B mid-investigation.

The second model should continue from the same external state.

This becomes foundational for distributed cognition.

---

# 4. Evaluation contamination can make the whole research program lie

## Why it is first-tier

NIST has documented:

- searching public solutions;
- inspecting future git history;
- grader manipulation;
- leaked task artifacts.

Meridian adds more contamination surfaces because it intentionally includes:

- retrieval;
- memory;
- multiple agents;
- tools;
- long histories.

A contaminated 95% score is worse than a clean 70% score because it teaches us the wrong architecture.

## Hardening principle

**Evaluation is a hostile environment against our own hypotheses.**

## Strengthening plan

Maintain three tiers:

### E0 — development

Can be public.
Used freely for iteration.

### E1 — private rotating validation

Unseen to training/generation pipelines.

### E2 — sealed reserve

Immutable.
No iterative architecture tuning.

For agent evaluations:

- remove future git history;
- isolate internet unless internet is explicitly part of task;
- immutable hidden scorer;
- scan environment for solution artifacts;
- transcript audit for contamination;
- post-cutoff/private tasks.

Haven's existing sealed/frozen experiment practices should be generalized into Meridian's permanent research methodology.

---

# 5. Evidence mis-grounding is likely before reasoning failure

## Evidence

Controlled retrieval studies report that models <=7B can fail to use even oracle-provided evidence on questions outside their parametric knowledge.

35B/70B should do better, but raw retrieval still creates:

- distraction;
- stale evidence;
- authority conflicts;
- entity ambiguity;
- retrieval omission.

## Hardening principle

Do not give the senior model a document pile if software can compile an evidence graph.

## Evidence pipeline

```
raw source
  ↓
origin classification
  ↓
freshness / authority
  ↓
entity resolution
  ↓
dedupe
  ↓
contradiction index
  ↓
typed evidence
  ↓
model-visible packet
```

## Claim contract

Every consequential model claim should be representable as:

```json
{
  "claim": "...",
  "supports": ["evidence-id"],
  "contradicts": [],
  "confidence": 0.0,
  "status": "hypothesis|verified|refuted"
}
```

Unsupported claims cannot silently graduate into state.

## Strengthening experiments

- irrelevant-evidence flooding;
- stale/live conflict;
- authority reversal;
- near-name entity collision;
- missing critical evidence;
- hostile text embedded in otherwise valid data.

---

# 6. Multi-agent compute must prove complementarity before use

## Evidence

Google's 2026 controlled study reports:

- strong gains on parallelizable tasks;
- 39–70% degradation on sequential planning tasks;
- trace-level independent-agent error amplification of 17.2x;
- centralized coordination 4.4x;
- architecture predictor correct on 87% of unseen configurations.

## Hardening principle

**Single coherent agent is the default.**

Multiple agents require an explicit reason:

- parallel evidence acquisition;
- low-correlated specialist;
- independent falsification;
- decomposable subproblem.

Never spawn another agent merely because compute is idle.

## Complementarity metric

For agents A and B:

```
Complementarity(A,B)
=
P(B succeeds | A fails)
```

Also measure:

- shared-error probability;
- coordination overhead;
- marginal verified-success gain;
- latency/device cost.

If agent B mostly repeats A's failures, it is noise.

---

# 7. Distributed cognition creates a trust-boundary problem

This becomes important once Meridian shards jobs across endpoints.

A compromised worker can return:

- fabricated tool results;
- manipulated evidence;
- poisoned summaries;
- plausible false verification.

## Hardening principle

Workers return **claims plus evidence provenance**, not trusted facts.

The controller verifies critical observations independently where practical.

## Proposed work-unit envelope

```json
{
  "job_id": "...",
  "assigned_capability": "...",
  "input_evidence": [],
  "allowed_tools": [],
  "effect_scope": "read-only",
  "deadline": "...",
  "worker_identity": "...",
  "result": {},
  "result_receipt": {}
}
```

High-consequence conclusions require:

- trusted measurement;
- reproducible computation;
- or independent corroboration.

Do not let peer consensus create authority.

---

# 8. Artifact synthesis is a model-capacity failure, not an orchestration bug

The November 2026 CyberGym analysis is especially important.

Even failed small-model runs commonly:

- found the vulnerable function;
- articulated the right hypothesis.

The differentiator was whether the model produced a working artifact.

Hard tasks required the 27B model.

## Hardening principle

When the bottleneck is synthesis, stop trying to fix it with more retrieval.

Use:

- typed builders;
- compilers;
- syntax/semantic validators;
- structured edit operations;
- iterative test feedback;
- 35B/70B escalation.

## Diagnostic oracle test

Give the model:

1. perfect evidence;
2. correct hypothesis.

If it still cannot produce the artifact:

```
capacity/artifact bottleneck
```

not:

```
retrieval problem
```

This test should become standard in Meridian research.

---

# 9. Specialist interference must be measured continuously

One shared backbone with many adapters is attractive but can introduce hidden negative transfer.

Every adapter promotion should re-run:

- expert-task matrix;
- unrelated controls;
- wrong-specialist controls;
- pairwise composition tests;
- calibration tests.

If specialization tax accumulates, isolate incompatible specialists into separate weight families.

---

# 10. Authorization should be treated as deterministic infrastructure

The model can misunderstand authorization.

That is acceptable if misunderstanding cannot produce unauthorized execution.

## Hardening principle

```
model intent != execution authority
```

Every consequential action should pass:

1. authenticated operator policy;
2. target/scope match;
3. action-class permission;
4. effect budget;
5. precondition;
6. dispatch gate;
7. postcondition;
8. receipt.

The model cannot:

- widen scope;
- alter policy;
- enroll itself;
- change its own effect budget;
- mark its own action verified.

This makes unauthorized intent measurable while unauthorized dispatch remains structurally constrained.

---

# Failure-first pre-planning sequence

Do not start by building the giant autonomous fabric.

Build the pieces in this order.

## Phase F0 — Success semantics

Design:

- success contract;
- postconditions;
- receipts;
- rollback semantics.

Reason: without trustworthy success, every later benchmark is suspect.

## Phase F1 — State machine

Design:

- external investigation state;
- event log;
- checkpoints;
- loop detection;
- recovery.

Reason: autonomy requires continuity beyond transcript context.

## Phase F2 — Evidence authority

Design:

- evidence ledger;
- provenance;
- freshness;
- contradiction handling;
- typed claims.

Reason: model reasoning is only useful if its inputs are trustworthy.

## Phase F3 — Verifier architecture

For each cyber task family, enumerate:

- exact verifier;
- simulation;
- test;
- replay;
- semantic residual.

Reason: this defines where autonomous success can safely terminate.

## Phase F4 — Memory safety

Design memory promotion/quarantine before long-term learning.

Reason: persistent experience otherwise creates persistent compromise.

## Phase F5 — Capacity diagnostics

Build:

- perfect-evidence test;
- perfect-hypothesis test;
- oracle-verifier test;
- pass@k curves.

Reason: decide where 4B/9B/35B/70B are actually required.

## Phase F6 — Agent topology

Only after above:

- single vs multi;
- planner/worker split;
- 35B/70B roles;
- distributed compute.

Reason: topology should optimize measured bottlenecks, not intuition.

## Phase F7 — Autonomous execution

Only after success, state, evidence, memory and verification boundaries exist.

---

# Proposed Failure Injection Suite

Every candidate Meridian architecture should be deliberately attacked with synthetic failures.

## Evidence failures

- stale truth;
- conflicting authorities;
- entity collision;
- missing evidence;
- injected instructions;
- fabricated peer result.

## State failures

- process restart;
- partial checkpoint;
- duplicated event;
- missing tool result;
- reordered results;
- context loss.

## Verifier failures

- false-positive visible test;
- incomplete test suite;
- outdated oracle;
- manipulated result;
- semantic loophole.

## Model failures

- hallucinated tool result;
- premature stop;
- repeated failed hypothesis;
- incorrect confidence;
- incorrect authorization interpretation.

## Memory failures

- poisoned observation;
- stale procedure;
- conflicting remembered fact;
- malicious summary;
- revoked policy reference.

## Distributed failures

- malicious worker;
- slow worker;
- disappearing worker;
- inconsistent worker clocks/state;
- duplicate result;
- replayed result.

Measure whether failure is:

- prevented;
- detected;
- contained;
- recovered;
- silently propagated.

Silent propagation should receive the largest penalty.

---

# New metrics

## False Autonomous Success Rate (FASR)

```
tasks declared successful but independently false
-------------------------------------------------
tasks declared successful
```

This should be one of Meridian's headline safety/reliability metrics.

## Silent Error Propagation Rate (SEPR)

```
upstream errors that enter trusted downstream state undetected
--------------------------------------------------------------
all injected upstream errors
```

## Recovery Probability (RP)

```
detected failures returned to a valid state without human reasoning
-------------------------------------------------------------------
all detected recoverable failures
```

## Evidence Authority Violation Rate (EAVR)

Claims where lower-authority/stale evidence overrode current authoritative evidence.

## Memory Contamination Survival (MCS)

Fraction of intentionally poisoned memories that still influence a later consequential decision after normal cleanup/promotion controls.

## Capacity Escalation Precision (CEP)

Fraction of model-size escalations that actually improve verified success.

This tells us whether the compute hierarchy is intelligent or merely expensive.

---

# First architecture principle set

The pre-planning work now yields a provisional Meridian constitution:

1. Models propose; external state decides what is known.
2. Models may claim success; external postconditions decide success.
3. Models may remember; host policy decides what becomes durable and authoritative.
4. Models may recommend actions; host policy owns execution authority.
5. Extra agents are conditional resources, not default intelligence.
6. Larger models are escalations for measured capacity failures, not prestige tiers.
7. Every autonomous state transition must be replayable or auditable.
8. Every high-consequence belief must retain provenance.
9. Uncertainty must survive compression; summaries may not turn uncertainty into fact.
10. Failure is acceptable; silent false success is not.

---

# Most important immediate research questions

Before implementation, answer:

1. What cyber task families have exact or near-exact success predicates?
2. Which failures can be detected deterministically?
3. Which important tasks still require semantic verification?
4. At what horizon does 35B/70B state coherence begin to collapse?
5. Does a typed evidence graph materially reduce grounding errors at 35B/70B?
6. Can persistent memory be made origin-bound enough to resist laundering?
7. Which task types benefit from multi-agent decomposition rather than one 70B?
8. Where does 35B pass@k plateau below 70B pass@1?
9. How often does 70B salvage a failed 35B trajectory?
10. Can a restarted model continue a multi-hour investigation purely from external state?

These should shape the first actual Meridian prototype.

## Sources

- Google Research, Towards a Science of Scaling Agent Systems (2026): https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/
- Luo et al., UltraHorizon, ICML 2026: https://proceedings.mlr.press/v306/luo26ai.html
- García-Carrasco et al., Analysis of Local Open-Weight LLM Agents on Vulnerability-Reproduction Tasks (2026): https://arxiv.org/abs/2611.06257
- Pandey, Can Small Language Models Use What They Retrieve? (2026): https://zenodo.org/records/18870116
- NIST CAISI, Cheating on AI Agent Evaluations: https://www.nist.gov/caissi/cheating-ai-agent-evaluations
- NIST CAISI, Practices for detecting and preventing evaluation cheating: https://www.nist.gov/caissi/4-practices-detecting-and-preventing-evaluation-cheating
- Microsoft Digital Defense Report 2026, Memory Poisoning: https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/msc/documents/presentations/CSR/2026-Microsoft-Digital-Defense-Report.pdf
- Microsoft Learn, AI Memory / Context Poisoning: https://learn.microsoft.com/en-us/security/zero-trust/catalog-ai-attack-techniques/ai-memory-context-poisoning
- Pulipaka et al., Hidden in Memory: Sleeper Memory Poisoning in LLM Agents (2026): https://arxiv.org/abs/2605.15338
- Dash et al., From Untrusted Input to Trusted Memory (2026): https://arxiv.org/abs/2606.04329
- Louck, Securing LLM-Agent Long-Term Memory Against Poisoning (2026): https://arxiv.org/abs/2606.24322
