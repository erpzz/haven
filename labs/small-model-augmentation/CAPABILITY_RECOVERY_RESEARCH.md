# Capability Recovery Research — How Much Can Architecture Recover for a 4B Local Model?

Status: research design note, 2026-11-26. This document is additive and does not alter frozen evaluation, reserve, promotion, training, or runtime policy.

## Research question

> **How much of the capability gap between a 4B local model and a frontier model can system architecture recover?**

This question should be measured as a systems problem, not answered by a single benchmark score.

A local 4B model may be weak because it lacks knowledge, cannot use provided evidence, loses state, selects the wrong tool, cannot translate a correct hypothesis into an artifact, loops after an error, cannot verify its own result, or simply lacks the reasoning capacity for the task. Those are different deficits and should not be collapsed into "the model is too small."

The Haven program should isolate them.

## Gap-recovery metric

For a task family and fixed evaluation budget:

- `P_raw4B` = raw 4B performance;
- `P_arch4B` = same 4B with a specified architecture layer;
- `P_ref` = stronger reference system under a matched interface and budget.

Define architecture gap recovery:

```text
Recovery = (P_arch4B - P_raw4B) / (P_ref - P_raw4B)
```

Interpretation:

- 0.0 = architecture recovered none of the gap;
- 0.5 = architecture recovered half the gap;
- 1.0 = architecture closed the measured gap;
- >1.0 = the 4B system beat the reference on that task family.

Do not aggregate this number across radically different capability families until the per-family results are reported.

A second utility view should include cost:

```text
Utility =
  task success
  - unsafe execution penalty
  - human intervention penalty
  - latency/compute penalty
  - evidence/provenance violation penalty
```

A 4B architecture can therefore be preferable even when raw accuracy is slightly lower if it is cheaper, private, bounded, and independently verifiable.

## The central hypothesis

A large portion of the *operational* gap is likely architectural, while a smaller but important portion is irreducibly model-capability-limited.

The strongest expected recoverable areas are:

- bounded tool invocation;
- exact evidence lookup;
- state persistence;
- scope/authorization;
- deterministic verification;
- retries/recovery;
- decomposition into narrow subtasks;
- fixed-domain specialization.

The hardest areas are likely:

- novel long-horizon planning;
- ambiguous causal inference;
- open-ended synthesis;
- unfamiliar-domain generalization;
- constructing complex artifacts when feedback is weak;
- tasks whose verifier cannot cheaply expose the error.

## Current empirical anchors

These are external research results, not Haven results, and should be treated as hypotheses-generating evidence.

### 1. Tool access can dominate scale

"Can Small Agent Collaboration Beat a Single Big LLM?" (arXiv:2601.11327, 2026) evaluates Qwen3 models from 4B to 32B. The authors report that tool augmentation provides the largest consistent gains and that a 4B tool-augmented configuration can outperform a 32B model without tools on GAIA.

The same work finds that system performance is planner/orchestrator limited: stronger global planning helps more than scaling execution sub-agents. Structured memory also reduces repeated-context growth.

Implication for Haven: do not spend 4B capacity re-reading history, discovering tools, or doing bookkeeping that the host can represent explicitly.

### 2. Small models can be excellent at bounded tool calls but weak at multi-turn orchestration

The Berkeley Function Calling Leaderboard V4 shows a useful shape for Qwen3-4B-Instruct-2507: strong single-turn function-calling sub-scores but much weaker multi-turn/agentic scores.

The lesson is not the absolute rank. The important diagnostic is that low-level tool syntax can be much less of a problem than maintaining state, choosing when to call, and coordinating a sequence of calls.

Implication for Haven: narrow the tool surface, persist state outside the model, and make the model solve one bounded decision at a time.

### 3. Naive RAG may hurt sub-7B models

"Can Small Language Models Use What They Retrieve?" (arXiv:2603.11513, 2026) reports severe retrieval-utilization failures for models <=7B, even under oracle retrieval, and large distraction effects on questions the model already knew.

This is a warning against the simplistic architecture:

```text
retrieve 10 chunks -> paste them into the 4B prompt -> hope
```

Haven should instead test:

```text
retrieve
  -> deterministic filtering
  -> evidence normalization
  -> authority/freshness labels
  -> compact structured facts
  -> model
```

The host should pre-compute what it can without smuggling the answer itself.

### 4. Verification is a capability multiplier, but test-time compute has a price

AgentV-RL / Agentic Verifier (ACL Findings 2026) shows that a 4B verifier benefits substantially from multi-turn tool-augmented verification and test-time scaling. The reported verification configuration uses materially more tokens/rounds/latency than the base path.

Implication for Haven: use deterministic verifiers whenever possible and spend model-based verification only on residual ambiguity. Verification should be a routing layer, not an unconditional second full agent run.

### 5. Some hard tasks still show a real model-size threshold

"Analysis of Local Open-Weight LLM Agents on Vulnerability-Reproduction Tasks" (arXiv:2611.06257, Nov. 2026) is particularly relevant. In the Qwen3.5 family, the 4B model solved many easier runs but 0/12 discriminating hard runs. The paper observes that failed runs often identified the vulnerable function and formed the correct hypothesis; the failure was translating that hypothesis into a working crashing input.

Implication for Haven: architecture may recover the hypothesis-to-artifact gap using typed artifact builders, targeted inspection, deterministic feedback, state, and specialized verification. But the result also warns that some tasks cross a genuine model-capability threshold.

### 6. Specialization can move the threshold dramatically

"Towards Reliable Local Security Agents: Verifiable Post-Training for Linux Privilege Escalation" (arXiv:2603.17673, ACSAC 2026) reports a 4B model reaching 93.3% on a held-out 12-scenario privilege-escalation benchmark after SFT plus RL with verifiable rewards.

"Toward Cybersecurity-Expert Small Language Models" (arXiv:2510.14113) reports strong cybersecurity results from specialized 4B-20B models.

"Internalizing Tool Knowledge in Small Language Models via QLoRA Fine-Tuning" (arXiv:2605.17774) reports that ~4B models trained on roughly 1,700 tool examples can outperform an informed unfine-tuned baseline for fixed-catalog tool planning while greatly reducing tool-schema prompt overhead.

Implication for Haven: system architecture and post-training should be evaluated separately and then together. W1/W2 training may move the model frontier, while the factory architecture reduces the amount of intelligence the model must supply at runtime.

## Haven's own prior evidence

The current Qwythos cyber capability matrix is a 9B result, not direct evidence about the 4B model, so it must not be used as a 4B claim.

It is still a useful systems prior.

In `labs/cyber/docs/research/CYBER_CAPABILITY_MATRIX.md`, the Qwythos-9B-v2 baseline shows:

- thinking-off condition A: 38/55;
- thinking-off condition C: 41/55;
- thinking-on condition C: 49/55;
- thinking-on C made only one tool call;
- the analysis attributes many remaining failures to orchestration rather than missing knowledge;
- thinking increased latency by roughly an order of magnitude.

That pattern motivates the exact Haven hypothesis: replace expensive free-form thinking with deterministic orchestration and selective tool use where possible.

## Capability decomposition

### A. Parametric knowledge

Question: does the model know the relevant concept without external evidence?

Architecture can help only indirectly through retrieval, structured evidence, or training.

Expected recoverability: medium.

### B. Evidence utilization

Question: once the correct evidence is present, can the model use it without being distracted or reverting to priors?

Architecture can improve this by:

- slicing evidence;
- labeling authority/freshness;
- separating trusted observations from untrusted text;
- removing irrelevant chunks;
- presenting typed facts;
- forcing claim/evidence references.

Expected recoverability: medium to high for narrow tasks, but this must be measured because standard RAG can fail badly at 4B scale.

### C. Tool selection and argument construction

Question: can the model identify the right tool and construct valid arguments?

Architecture can:

- route/narrow the catalog;
- expose only authorized relevant tools;
- use host-curated route metadata;
- bind argument values;
- use typed schemas;
- reject malformed/unknown calls.

Expected recoverability: high for bounded tools.

### D. Multi-turn state

Question: can the model remember what has happened and avoid loops/repeated work?

Architecture can externalize:

- completed subgoals;
- observations;
- evidence IDs;
- tool budgets;
- failed attempts;
- open questions;
- checkpoints.

Expected recoverability: high. The model should reconstruct state from a compact host representation rather than re-reading a growing transcript.

### E. Planning/decomposition

Question: can the model break a task into productive subgoals and decide when to stop?

Architecture can supply:

- workflow templates;
- typed skills;
- deterministic prerequisites;
- required verification steps;
- bounded retry policies.

Expected recoverability: medium to high for known workflow families, lower for novel tasks.

### F. Artifact construction

Question: can a correct hypothesis become a correct patch, query, exploit input, config, or investigation plan?

Architecture can supply:

- typed builders;
- syntax validators;
- partial artifact inspection;
- small edit operations;
- structured feedback;
- diff constraints;
- exact target binding.

Expected recoverability: medium. This appears to be a major hard-task threshold in current local vulnerability-reproduction research.

### G. Verification and debugging

Question: can the system detect a wrong result and recover?

Architecture can move much of this outside the model:

- tests;
- static analyzers;
- exact graders;
- replay;
- adversarial retest;
- independent verifier;
- bounded retry.

Expected recoverability: high when the task has a cheap reliable verifier; low when correctness itself requires open-ended judgment.

### H. Authorization and safety

Question: can unauthorized model behavior be prevented?

This is mostly not a model-capability problem.

Host-owned tool visibility, target constraints, final-dispatch gates, process ownership and approval policy can make unsafe execution fail closed even if model intent is wrong.

Expected execution-layer recoverability: near-total if the enforcement boundary is complete.

Important: keep measuring unauthorized **intent** separately. A safe system does not imply a well-aligned model.

### I. Novel reasoning/generalization

Question: can the model invent a correct plan where no workflow, verifier, retrieval result, or prior pattern provides strong scaffolding?

Architecture can search and verify candidates, but it cannot cheaply manufacture missing abstractions.

Expected recoverability: low to medium. This is where model scale and better post-training are most likely to remain decisive.

## Research priors, not results

The following ranges are deliberately hypotheses to test, not claims.

| Capability family | Initial architecture-only gap-recovery prior |
|---|---:|
| authorization / execution containment | 90-100% |
| single-step typed tool invocation | 80-95% |
| state / duplicate-call / budget discipline | 75-95% |
| bounded evidence lookup and extraction | 60-85% |
| known multi-step workflow orchestration | 55-80% |
| deterministically verifiable repair/debug loop | 60-90% |
| unfamiliar long-horizon autonomous workflow | 30-60% |
| novel causal reasoning / hard artifact synthesis | 20-50% |
| open-ended unseen exploit/research synthesis | 10-40% |

These priors should be updated from Haven experiments. They are not suitable for publication as findings.

## Proposed Haven experiment: Capability Recovery Ladder

Use the same frozen task population and the same base 4B weights for architecture-only arms.

### R0 — raw 4B

Minimal task artifacts. No retrieval, no special routing, no controller, no retry beyond protocol-required parsing.

### R1 — evidence shaping

Same model plus normalized evidence packets, compact provenance, freshness/authority metadata, and irrelevant-context suppression.

This isolates evidence architecture.

### R2 — context/tool narrowing

Add trusted dynamic tool selection. The router may only narrow an already-authorized set.

This isolates context pressure and tool-choice complexity.

### R3 — external state

Add host-owned compact state:

- completed steps;
- observations;
- open subgoals;
- tool budgets;
- attempt history;
- verification status.

The model never needs to reconstruct state from full transcript history.

### R4 — bounded workflow controller

Add explicit skills and prerequisite transitions.

The controller decides which class of decision is needed; the model reasons only inside the current bounded skill.

### R5 — verifier/retry

Add deterministic verifier feedback and a fixed retry budget.

The verifier must expose an error class/evidence, not a hidden gold answer.

### R6 — full Haven architecture

Compose:

- evidence admission;
- tool narrowing;
- exact visible surface;
- target/effect scope;
- external state;
- controller;
- verifier;
- recovery;
- receipts.

No weights changed.

### R7 — trained 4B + same architecture

Only after W1/W2 training is independently qualified.

This measures training gain on top of architecture rather than confounding the two.

### References

Run matched reference systems through the same environment where possible:

- larger local model;
- frontier model;
- optionally frontier model with and without the Haven controller.

The strongest research result may be that architecture helps *all* sizes but helps the 4B disproportionately.

## Task families for the first recovery study

The first study should not be one giant score. Use strata.

### 1. Evidence interpretation

Examples:

- stale-vs-live evidence;
- conflicting authority;
- distractor entities;
- insufficient evidence;
- authorization ambiguity.

Primary measurements:

- claim correctness;
- evidence precision;
- stale-premise failures;
- unsupported claims.

### 2. Single-tool decisions

One tool is sufficient, but the model must know to call it and construct the right arguments.

Measurements:

- applicable-tool recall;
- argument validity;
- wrong-target rate;
- unnecessary calls.

### 3. Multi-step tool workflows

Tasks require a known chain of 2-5 operations.

Measurements:

- completion;
- skipped prerequisite;
- duplicate calls;
- loop rate;
- tool calls per success;
- state errors.

### 4. Repair

Use HDF findings with fixed host recipes.

Measurements:

- valid patch rate;
- allowed-path compliance;
- verified candidate rate;
- regression rate;
- attempts per verified fix.

### 5. Red/adversarial behavior

Use HRF development families.

Measurements:

- model-intent pass;
- execution pass;
- unauthorized intent;
- unauthorized dispatch;
- evidence injection;
- stale-premise handling;
- wrong-target/duplicate behavior.

### 6. Hard open-ended tasks

Use a small development-only set where the model must create a novel artifact or investigation strategy and where larger models currently separate.

This bucket establishes the non-recoverable frontier.

## Experimental controls

Architecture-only comparisons require:

- exact same base weights;
- exact same quantization;
- exact same decoding settings;
- same task set;
- same target/environment;
- same maximum wall time;
- same maximum tool/effect budget where the arm supports tools;
- no hidden gold leakage;
- no reserve data;
- deterministic receipts.

Where architecture changes the feasible resource budget, report both fixed-budget and natural-budget results.

## Metrics

Report at least:

| Dimension | Metric |
|---|---|
| task | success / correctness |
| evidence | unsupported-claim and provenance violation rate |
| tool use | applicable-tool recall, invalid calls, wrong target, duplicates |
| safety | unauthorized intent vs actual dispatch |
| recovery | verifier-triggered salvage rate |
| autonomy | human interventions / task |
| efficiency | wall time, model calls, tokens, device time |
| context | prompt bytes/tokens by category |
| stability | variance across repeated runs |
| remediation | verified-fix and landed-fix rate |
| red loop | original failure survives remediation? |
| training | architecture-only vs post-training delta |

## The most important ablations

A pure sequential ladder is easy to read but architecture layers interact.

After the ladder, run targeted remove-one ablations from the full system:

- full minus evidence shaping;
- full minus tool narrowing;
- full minus external state;
- full minus controller;
- full minus verifier;
- full minus recovery.

This tells us whether a component is independently useful or only useful in combination.

## Expected qualitative result

The likely answer is not:

> "Architecture makes a 4B model equal to a frontier model."

A more plausible result is:

> A 4B model can approach or exceed much larger raw models on tightly bounded, externally grounded, tool-mediated tasks when the system removes state, authorization, retrieval, and verification burdens from the model. The gap reappears sharply when the task requires novel global planning or artifact synthesis that cannot be decomposed or cheaply verified.

If Haven demonstrates that result cleanly, it is valuable even without universal parity.

## Why this matters

The systems question is economically and operationally different from model scaling.

If a 4B local model can achieve high system-level reliability on a large subset of enterprise security work, then the useful comparison becomes:

```text
frontier model for every token
vs.
small local model + deterministic architecture + selective escalation
```

Potential advantages include:

- private/local data handling;
- low marginal inference cost;
- predictable tool authority;
- inspectable evidence;
- reproducibility;
- offline operation;
- model interchangeability;
- clearer failure attribution.

The architecture may therefore be valuable even if the 4B model never closes the final capability gap.
