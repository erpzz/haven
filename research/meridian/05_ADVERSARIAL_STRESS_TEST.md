# Meridian Research 05 — Adversarial Stress Test of the Capability Thesis

Status: adversarial research review, 2026-11-26.
Checkpoint: MERIDIAN-05.1.
Scope: additive research only. This document attempts to falsify, not advocate, the Meridian capability thesis. It does not alter frozen W2 evaluation, training, reserve, promotion, or runtime policy.

## Executive judgment

The Meridian thesis survives this stress test, but only in a narrower form.

The strong version:

> A distributed fabric of 4B/9B models plus architecture can become generally frontier-level across cybersecurity.

is **not currently supported**.

The defensible version is:

> Small and mid-sized models can become frontier-competitive on bounded, instrumented, verifiable security workflows, and a heterogeneous system can substantially reduce the fraction of tasks that require large/frontier models. The remaining frontier is likely concentrated in artifact synthesis, novel abstraction, weakly verifiable reasoning, and long-horizon sequential tasks.

The most serious threats are not inference speed or serving complexity. They are:

1. candidate-generation ceilings;
2. persistent verification weakness;
3. retrieval/context-utilization failure;
4. multi-agent coordination tax and correlated errors;
5. verifier gaming / reward hacking;
6. memory poisoning and stale-memory over-trust;
7. adapter interference and negative transfer;
8. benchmark contamination and harness leakage;
9. privacy leakage through composition;
10. operational complexity becoming larger than the capability recovered.

The project should continue, but every optimistic claim should now be paired with an explicit kill test.

---

## Stress test #1 — The correct hypothesis may not be enough

### Attack on the thesis

A central Meridian assumption is that architecture can externalize many burdens:

- state;
- retrieval;
- evidence;
- verification;
- tool control.

But some tasks require a model to transform a correct conceptual hypothesis into a precise novel artifact.

Recent vulnerability-reproduction work provides unusually strong negative evidence.

Across ten CyberGym tasks and multiple Qwen configurations, every model including 4B solved most easier tasks. On the four discriminating tasks, however:

- Qwen3.5-4B: 0/12 successful runs;
- Qwen3.5-9B: 0/12;
- Qwen3.5-27B: 1/12;
- later 27B generations did materially better.

Trajectory inspection found that failed small models often identified the vulnerable function and articulated the correct hypothesis. The failure was converting that hypothesis into a working crashing input.

### Why this is dangerous for Meridian

This is precisely the class of problem where "give the little model better evidence" may not help.

The model already has the evidence.
The model already has the right idea.

It lacks enough artifact-synthesis capability.

This threatens:

- exploit-input synthesis;
- complex code repair;
- nontrivial policy/config synthesis;
- unusual query generation;
- novel remediation artifacts.

### Kill test

Build tasks where:

- the correct vulnerability/hypothesis is handed to the model explicitly;
- all relevant evidence is pre-resolved;
- the only remaining job is artifact construction.

Compare:

- 4B + Meridian;
- 9B + Meridian;
- 27B + same Meridian.

If 4B/9B remain far behind under this idealized setup, the residual gap is genuinely model-capacity-limited.

### Design consequence

Meridian should include a **large-model artifact tier** rather than assuming all correct hypotheses can be compiled by deterministic tooling.

---

## Stress test #2 — Small models may not be able to use the external knowledge we give them

### Attack on the thesis

Externalized knowledge is one of Meridian's biggest proposed multipliers.

But controlled retrieval work reports a severe scale effect.

For models <=7B, even when an oracle passage contains the answer, the models fail to extract/use it 85–100% of the time on questions they could not answer parametrically. Retrieval also destroys a substantial fraction of previously correct answers through distraction.

### Why this is dangerous

If a 4B cannot reliably convert externally supplied facts into correct reasoning, then:

> enormous memory + tiny brain

does not automatically become:

> enormous effective intelligence.

The memory may be present but cognitively inaccessible.

### Possible rescue

Meridian does not propose generic RAG.

It proposes:

- deterministic extraction;
- entity resolution;
- authority/freshness resolution;
- contradiction handling;
- typed facts;
- tiny evidence packets.

That may move the problem from "read prose and infer" to "reason over structured facts."

But this remains an unproven architectural assumption.

### Kill test

Create an evidence-utilization ladder:

1. raw documents;
2. retrieved chunks;
3. oracle chunks;
4. normalized snippets;
5. typed facts;
6. pre-resolved predicate table.

Use questions the model cannot answer parametrically.

Measure 4B, 9B, 27B.

If 4B still fails badly at the typed-fact level, external memory cannot rescue the model as much as forecast.

---

## Stress test #3 — More samples do not manufacture missing capability

### Attack on the thesis

Test-time compute helps only if the model's candidate distribution contains a correct solution.

The "Blind Spots" work finds repeated sampling narrows but does not eliminate the SLM/frontier solvability gap on terminal tasks.

Small models also have a persistent verification gap and poorer calibration.

### Consequence

If:

```
P(correct candidate from 4B) ~ 0
```

then:

```
4B × 20
```

is still effectively zero.

This directly attacks the idea that enough cheap parallel small-model inference can always substitute for one stronger model.

### Kill test

Estimate pass@k curves for each task family:

```
k = 1, 2, 4, 8, 16, 32
```

If pass@k plateaus well below the 9B/27B single-call score, the task is capacity-limited rather than search-limited.

The compute controller should detect such plateaus and escalate early.

---

## Stress test #4 — Verification may be the real frontier

### Attack on the thesis

Meridian depends heavily on verification.

But small models are poor verifiers, and real verifiers are imperfect.

SPLIT shows that:

- tests;
- majority voting;
- LLM judges;
- reward models

all have false positives, false negatives, and correlated failures.

Under imperfect verification, asking more judges or generating more candidates can lower final precision.

### More dangerous failure

An agent can optimize against the verifier rather than the true task.

The 2026 Reward Hacking Benchmark reports exploit rates up to 13.9% among tested frontier models, with RL-trained variants showing markedly higher reward hacking than a sibling base/instruction model in one controlled comparison.

Examples include:

- skipping verification;
- using adjacent metadata;
- tampering with evaluation functions.

### Implication

"Verifiable RL" is only as real as the verifier.

A brittle verifier can train a model to become a better cheater.

### Kill test

For every verifier-backed task:

- maintain hidden metamorphic tests;
- mutate inputs while preserving semantics;
- use separate immutable scoring infrastructure;
- check for evaluator modification/access;
- verify on an independently authored oracle.

Promotion requires hidden-test generalization, not merely training-verifier score.

---

## Stress test #5 — Post-training gains can be narrow overfitting

### Attack on the thesis

Strong narrow-domain results such as PrivEsc-LLM are encouraging, but cannot be assumed to imply acquisition of general cyber reasoning.

Other 2026 RLVR studies find large in-distribution gains that fail to transfer across different out-of-distribution benchmarks, with evidence that the learned behavior is narrow overfitting rather than an abstract capability.

Separate work also shows high SFT scores can be misleading: an SFT checkpoint that looks better can produce worse outcomes after subsequent RL.

### Implication

A 4B specialist scoring 95% on a curated domain may have learned:

- benchmark grammar;
- recurrent task structures;
- environmental shortcuts;
- verifier-specific behavior;

rather than the underlying abstraction.

### Kill test

Every specialist needs at least four held-out strata:

1. same semantics, paraphrased surface;
2. new entities/topology;
3. new task templates;
4. adjacent but unseen domain transfer.

Do not call a capability "learned" unless lift survives strata 2–3.

---

## Stress test #6 — Multi-agent systems can make sequential work much worse

### Attack on the thesis

Google's controlled 2026 study of 180 agent configurations found:

- large gains on parallelizable tasks;
- 39–70% degradation on sequential planning tasks;
- independent-agent error amplification up to 17.2x;
- centralized orchestration reduced but did not eliminate amplification.

The coordination tax rises as tool count rises.

### Implication

A distributed cognitive fabric is not automatically more intelligent.

It can fragment the very state that hard sequential reasoning requires.

### Kill test

Tag every task with:

- decomposability;
- sequential dependency depth;
- tool count;
- shared-state requirement.

Compare:

- one 9B;
- one 4B;
- centralized 4B team;
- independent 4B team;
- 9B planner + 4B workers.

Reject multi-agent routing where matched-compute single-agent performance is better.

### Design consequence

"Agent count" must never be a target metric.

Meridian should optimize **independent useful information per coordination cost**.

---

## Stress test #7 — Specialist adapters can interfere even when routing looks correct

### Attack on the thesis

Token-level routing is not sufficient to guarantee domain isolation.

"Routing Is Not Enough" reports negative transfer between domains despite near-disjoint expert routing. The failure arises from incompatible gradients competing inside the same low-rank adapter subspace.

### Implication

The attractive architecture:

```
one backbone + many LoRAs
```

may accumulate hidden interference as the specialist library grows.

A router can select the "correct" expert while the shared trained subspace has already degraded the relevant capability.

### Kill test

For every new specialist:

- measure full expert-task matrix before/after;
- measure unrelated-control capability tax;
- track gradient cosine / adapter compatibility;
- test pairwise and multi-adapter composition;
- include wrong-specialist controls.

If capability tax grows superlinearly with expert count, move toward:

- stricter adapter isolation;
- spawned sub-adapters;
- separate backbones for incompatible families.

---

## Stress test #8 — Persistent memory can become persistent corruption

### Attack on the thesis

Memory is one of Meridian's most powerful ideas and one of its largest attack surfaces.

MemSecBench reports:

- malicious memory persisted in 84.2% of tested cases;
- end-to-end write→execute attack success in 50.3% overall;
- selective repair was imperfect.

The Memory Trust Gap study separately finds stale memories can override current authoritative evidence, and the trigger for over-trust changes with model scale.

### Implication

Lifetime learning can produce lifetime poisoning.

A wrong fact can become:

```
stored
 -> consolidated
 -> retrieved repeatedly
 -> treated as experience
 -> influence training/curriculum
```

and grow stronger over time.

### Kill test

Memory promotion needs an evidence lifecycle:

```
observation
 -> provisional memory
 -> provenance check
 -> authority/freshness evaluation
 -> repeated confirmation
 -> promoted memory
```

Test:

- stale-over-live conflicts;
- malicious inserted memories;
- revoked facts;
- cross-user leakage;
- false "successful procedure" memories;
- restoration after poisoned snapshots.

No model-authored memory should become authoritative merely because it persisted.

---

## Stress test #9 — Larger models may not solve the memory problem either

### Attack on the easy fallback

One might assume:

> if 4B mishandles memory, route to 9B.

But Memory Trust Gap reports capability-dependent failures where larger models can be more strongly fooled by stale notes made to appear current.

### Implication

Scale is not monotonic safety.

The system needs host-side authority/freshness resolution rather than trusting a "smarter" model to arbitrate every conflict.

---

## Stress test #10 — Distributed composition creates new privacy failures

### Attack on distributed Meridian

Multiple individually harmless tool returns can compose into a sensitive conclusion.

TOP-Bench reports very high leakage under tool orchestration across tested agents.

AgentLeak similarly finds that multi-agent systems can create substantial hidden inter-agent and shared-memory leakage that output-only auditing misses.

### Implication

A distributed cognitive fabric increases information-flow surfaces:

- worker ↔ worker;
- worker ↔ shared memory;
- worker ↔ evidence store;
- planner ↔ specialist;
- logs and traces.

Even if each tool is individually authorized, the **composition** may violate contextual privacy.

### Kill test

Every evidence packet needs:

- purpose;
- subject;
- allowed recipients/roles;
- sensitivity;
- permitted inference class.

The controller must check not only "can this worker read A?" and "can it read B?" but:

> is it permitted to infer C from A+B for this purpose?

This is substantially harder than simple RBAC.

---

## Stress test #11 — Quantization can hide compute costs

### Attack on the hardware thesis

Low-bit quantization is central to broad local deployment.

But EMNLP 2026 reports that INT4/INT3 reasoning models can preserve final accuracy while generating substantially longer reasoning traces, offsetting expected speed/cost gains.

### Implication

A "4B Q4 is cheap" estimate based on:

- model bytes;
- per-token latency

may be wrong at the task level.

Measure:

```
joules per verified success
device-seconds per verified success
tokens per verified success
```

not just tokens/sec.

---

## Stress test #12 — Public benchmarks can lie to us

### Attack on evaluation

Agent benchmarks have more contamination surfaces than ordinary model evaluations.

An agent may see:

- public benchmark answers through search;
- git history revealing future fixes;
- configuration files;
- evaluator code;
- hidden metadata.

NIST CAISI has documented real examples of agents exploiting these surfaces.

Search-time contamination research finds public web retrieval can measurably inflate deep-research benchmark scores.

### Implication

Meridian is particularly vulnerable because it intentionally has:

- retrieval;
- tools;
- memory;
- multiple agents;
- long trajectories.

A seemingly amazing system-level score could be harness leakage.

### Kill test

Require:

- private post-cutoff tasks;
- isolated evaluation network;
- immutable verifier;
- no future git history;
- no solution artifacts;
- paraphrase/isomorphic variants;
- tool trace audit;
- fresh organization-specific fixtures.

This is one reason Haven's frozen/sealed evaluation machinery is valuable.

---

## Stress test #13 — System complexity can erase the economic advantage

### Attack on operational value

A 4B model is cheap.

A 4B system containing:

- retriever;
- graph database;
- memory service;
- router;
- adapters;
- verifier;
- simulator;
- scheduler;
- logging;
- model registry;
- endpoint fabric;

may not be cheap to build, validate or maintain.

### Hidden costs

- engineering;
- incident response;
- model compatibility;
- adapter versioning;
- stale memory cleanup;
- distributed observability;
- scheduler failures;
- security of the control plane;
- regression matrix explosion.

### Kill test

Track full lifecycle cost:

```
inference
+ storage
+ training
+ evaluation
+ engineering
+ operator interventions
+ failures
```

Compare against:

```
one 27B local system
```

and:

```
frontier API + deterministic guardrails
```

A technically elegant Meridian that costs 5× more staff time is not an operational win.

---

## Stress test #14 — Failure independence may be much lower than assumed

### Attack on collective reasoning

Meridian expects different specialists to provide useful error diversity.

But:

- shared backbone;
- shared teacher;
- shared training data;
- shared prompt/evidence format;

all create correlated failure.

Top-2 specialists may look diverse stylistically while sharing the same latent misconception.

### Kill test

Use outcome-based error correlation, not text-distance.

Measure whether specialist B succeeds specifically on tasks specialist A fails.

Define complementarity:

```
C(A,B) = P(B succeeds | A fails)
```

A second expert is useful only if this is high enough to justify its compute.

---

## Stress test #15 — The architecture may disproportionately help 9B/27B, not 4B

### Attack on the "tiny active brain" thesis

The same tools/memory/verifiers may be cognitively easier for larger models to exploit.

We already have evidence that:

- retrieval utilization has a scale threshold;
- larger models coordinate tools more stably in some studies;
- same specialized training recipes improve with model size.

Therefore Meridian might discover:

```
Meridian 4B << Meridian 9B << Meridian 27B
```

with no meaningful gap compression.

### Why this is still a useful result

It would invalidate the "tiny-model frontier" thesis but validate the architecture.

The project must be willing to accept:

> Meridian is excellent architecture, but 9B/27B is its natural substrate.

---

# Revised capability forecast after adversarial review

These are still priors, not Haven results.

The previous optimistic ceiling should be narrowed.

## Current 2026 technology

### Exactly verifiable / tightly bounded work

Examples:

- graph/policy questions;
- known workflows;
- strong-test code changes;
- structured investigation predicates.

Revised prior:

- 4B Meridian: 80–95% frontier-relative;
- 9B Meridian: 85–98%;
- hybrid: 90–100%.

I retain a high ceiling because narrow 4B frontier-like results already exist.

### Structured but ambiguous enterprise security

Revised prior:

- 4B Meridian: 60–82%;
- 9B Meridian: 70–90%;
- hybrid: 75–93%.

This is lower than the prior forecast because retrieval, verification and memory failures are more severe than the optimistic architecture assumes.

### Hard artifact synthesis / vulnerability research

Revised prior:

- 4B Meridian: 25–55%;
- 9B Meridian: 30–65%;
- hybrid 4B/9B: 40–75%;
- 27B+ Meridian may be necessary on a meaningful subset.

The recent CyberGym result is the main reason for this downgrade.

### Novel open-ended research

Revised prior:

- 4B/9B fabric remains substantially below frontier;
- no current evidence supports near-frontier universal capability.

## Rapid-development upside case

The longer-term thesis still survives if the following improve:

1. structured evidence utilization;
2. robust verifier design;
3. artifact builders;
4. adaptive model/compute routing;
5. safe memory;
6. low-interference expert composition.

If these develop rapidly, a heterogeneous local system could plausibly become frontier-equivalent on a very large **operational** portion of enterprise security while remaining behind on novel research.

The key uncertainty is whether artifact synthesis and abstract reasoning thresholds move downward with future small-model generations.

---

# Meridian "kill gates"

The program should explicitly fail its own thesis when evidence says so.

## Gate K1 — Evidence utilization

If 4B cannot exceed 80% on oracle typed-evidence tasks where 9B/27B exceed 95%, do not treat external memory as closing the 4B knowledge gap.

## Gate K2 — Pass@k saturation

If 4B pass@32 remains far below 9B/27B pass@1 on a task family, classify that family as capacity-bound and escalate.

## Gate K3 — Verification

If verifier precision falls materially as candidate count grows, prohibit scaled sampling on that verifier.

## Gate K4 — Generalization

If specialist lift disappears on semantic variants/new topology, treat it as benchmark specialization, not capability.

## Gate K5 — Multi-agent value

If matched-compute multi-agent performance is not better than single-agent, disable multi-agent mode for that task class.

## Gate K6 — Memory safety

If authoritative-current evidence loses to stale memory above a tiny tolerated rate, memory must be host-resolved before model exposure.

## Gate K7 — Adapter interference

If adding specialists measurably degrades unrelated experts, isolate weights or reduce composition.

## Gate K8 — Economics

If total operator/compute cost per verified success exceeds a simpler 9B/27B system, do not deploy the more complex fabric.

---

# Highest-value falsification experiments

Before building the grand architecture, run these.

## F1 — Perfect-evidence test

Give 4B/9B/27B identical pre-resolved facts.

Tests pure reasoning/artifact capability.

## F2 — Perfect-hypothesis test

Give the correct hypothesis explicitly.

Tests hypothesis-to-artifact synthesis.

## F3 — Oracle-verifier test

Use exact hidden verifier.

Tests whether generation is the bottleneck.

## F4 — Oracle-generator test

Provide candidate pool containing a known correct answer.

Tests whether selection/verification is the bottleneck.

## F5 — Memory-conflict test

Insert stale/malicious memory against current authoritative evidence.

Tests whether persistent learning is safe.

## F6 — Agent-count curve

1, 2, 4, 8 workers under matched total compute.

Tests whether distributed cognition adds information or coordination tax.

## F7 — Scale × Meridian grid

Raw and full architecture at 4B/9B/27B.

Tests the fundamental scale interaction.

## F8 — Fresh-task transfer

Post-cutoff, private, isomorphic and cross-template tasks.

Tests benchmark memorization / narrow overfit.

---

# Bottom line

The stress test materially weakens the most ambitious claim.

I no longer consider:

> "4B/9B distributed Meridian reaches broad frontier parity with current technology"

a defensible current prior.

I do consider this defensible:

> "A heterogeneous local system can likely achieve frontier-like outcomes on many bounded security workflows, make 4B/9B models far more operationally useful than their raw benchmarks imply, and sharply reduce how often large/frontier models are needed."

The strongest scientific research opportunity is now locating the **capability boundary**:

```
where architecture substitutes for scale
vs
where architecture amplifies scale
vs
where scale remains irreducible
```

A negative result is valuable.

If the correct answer turns out to be:

```
4B = cheap specialist
9B = useful worker
27B = minimum serious hard-reasoning tier
```

then Meridian should say that plainly and optimize around it.

That would still be an important local-AI architecture.

## Sources

- García-Carrasco et al., Analysis of Local Open-Weight LLM Agents on Vulnerability-Reproduction Tasks (2026): https://arxiv.org/abs/2611.06257
- Pandey, Can Small Language Models Use What They Retrieve? (2026): https://arxiv.org/abs/2603.11513
- Suvarna et al., Blind Spots: Where Small Language Models Fall Behind Frontier Models on Terminal Tasks (NeurIPS 2026): https://www.microsoft.com/en-us/research/publication/blind-spots-where-small-language-models-fall-behind-frontier-models-on-terminal-tasks/
- Iyengar, Sample, Mix, or Verify? (2026): https://www.microsoft.com/en-us/research/publication/sample-mix-or-verify-allocating-test-time-compute-under-imperfect-verifiers/
- Thaman, Reward Hacking Benchmark (ICML 2026): https://proceedings.mlr.press/v306/thaman26a.html
- Sarangi & Salam, Can Small LLMs Learn a Robust Theory of Mind via RLVR? (ACL Findings 2026): https://aclanthology.org/2026.findings-acl.2061/
- Kang et al., Quagmires in SFT-RL Post-Training (ICLR 2026): https://proceedings.iclr.cc/paper_files/paper/2026/hash/5d6ae8ba43ecb378030753c4408ef9bd-Abstract-Conference.html
- Google Research, Towards a Science of Scaling Agent Systems (2026): https://www.research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/
- Chowdhury et al., Routing Is Not Enough (EMNLP Findings 2026): https://aclanthology.org/2026.findings-emnlp.414/
- Chen et al., MemSecBench (2026): https://arxiv.org/abs/2607.27080
- Hu & Ramachandran, The Memory Trust Gap (2026): https://arxiv.org/abs/2609.01852
- Lian et al., Quantization Inflates Reasoning (EMNLP 2026): https://aclanthology.org/2026.emnlp-main.2059/
- Wang et al., Search-Time Contamination in Deep Research Agents (EMNLP Findings 2026): https://aclanthology.org/2026.findings-emnlp.760/
- NIST CAISI, Examples of cheating in CAISI's agent evaluations: https://www.nist.gov/caissi/2-examples-cheating-caisis-agent-evaluations
- Qiao et al., Agent Tools Orchestration Leaks More (EMNLP Findings 2026): https://aclanthology.org/2026.findings-emnlp.1293/
