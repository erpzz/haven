# Meridian Research 06 — Raising the Ceiling: 35B–80B Local Frontier Systems

Status: strategic research note, 2026-11-26.
Checkpoint: MERIDIAN-06.1.
Scope: additive research only. This does not alter frozen W2 evaluation, training, reserve, promotion, or runtime policy.

## Core shift

The Meridian program should no longer treat 35B–80B models primarily as rare emergency fallbacks.

They should be studied as **senior local cognition tiers** that receive the same architecture advantages proposed for 4B/9B:

- specialist post-training;
- adapter routing;
- typed evidence;
- external state;
- deterministic verifiers;
- adaptive test-time compute;
- persistent experience memory;
- bounded multi-agent decomposition;
- scale-aware routing;
- distributed compute.

The research question becomes:

> How close can a fully local 35B–80B system get to frontier operational capability when the model is embedded inside an architecture designed to remove avoidable cognitive burdens and spend additional computation only where it produces verified value?

A second, more ambitious question is:

> Can architecture amplify a 35B–80B model enough that it is not merely cheaper than frontier inference, but **better on selected long-running, organization-specific, tool-mediated workloads**?

## Why this is now credible

### 35B agentic specialization already reaches frontier-scale benchmark territory

Agents-A1 is a 35B-A3B agentic model trained with:

1. full-domain SFT;
2. domain-level teacher models;
3. domain-routed on-policy multi-teacher distillation.

Its training infrastructure uses long knowledge-action trajectories averaging roughly 45K tokens.

The authors report results including:

- GAIA: 96.04;
- Seal0: 56.36;
- FrontierScience-Olympiad: 79.0;
- FrontierScience-Research: 40.0;
- IFBench: 80.61;
- IFEval: 94.82.

On several of these reported evaluations it matches or exceeds much larger proprietary systems, while remaining weaker on some engineering tasks.

This is not proof of universal frontier parity. It is strong evidence that a well-post-trained ~35B sparse agent model can already cross into frontier-scale performance on selected long-horizon/research workloads.

### Qwen3.6-35B-A3B is already a serious agent substrate

Qwen3.6-35B-A3B has:

- 35B total parameters;
- ~3B activated parameters per token;
- 262K native context;
- optional extension to ~1M context;
- explicit tool-calling / agent support.

Reported evaluations include roughly:

- SWE-bench Verified: 73.4;
- SWE-bench Pro: 49.5;
- Terminal-Bench 2.0: 51.5;
- GPQA Diamond: 86.0.

At Q4_K_M, current GGUFs are around 20.5–22.1 GB depending on conversion.

This is an important hardware/capability point:

> a model can have a 35B stored capability space while spending only ~3B active expert parameters per token.

That makes sparse MoE one of the most promising architectures for local senior agents.

### 80B total / 3B active is already real

Qwen3-Next-80B-A3B has:

- 80B total parameters;
- 3B activated;
- 262K native context;
- official extension guidance to ~1M context.

The official model card reports that its base model outperforms Qwen3-32B-Base while using 10% of the total training cost and achieving ~10× inference throughput for contexts above 32K, and that the instruct model is on par with Qwen3-235B-A22B-Instruct-2507 on selected benchmarks.

Its Q4_K_M GGUF is approximately 48.4 GB.

This is a concrete demonstration of the architectural direction Meridian should take seriously:

> total stored model capacity and active per-token compute are decoupling.

### Dense 70B remains a powerful control

DeepSeek-R1-Distill-Llama-70B demonstrates a different route: distilling reasoning behavior from a much larger teacher into a dense 70B model.

Dense 70B models remain useful controls because they remove MoE routing as a confound and provide high per-token representational capacity.

## Revised Meridian cognitive hierarchy

The new target architecture should be:

```
Tier 0 — deterministic
graphs, policy, tests, simulation, authorization

Tier 1 — 2B–4B
micro-specialists, extraction, cheap bounded work

Tier 2 — 9B
general local workers / mid-level specialists

Tier 3 — 27B–35B
senior local agents, planning, synthesis, code, investigation

Tier 4 — 70B dense / ~80B sparse
deep local reasoning, artifact synthesis, difficult verification, research

Tier 5 — frontier external
optional teacher/reference/exception path
```

The objective should be to drive the Tier-5 invocation rate toward zero **where empirical evidence permits**, not to eliminate it by ideology.

## 35B should become a default senior tier

A 35B-A3B model is particularly attractive because it combines:

- high total capacity;
- low active expert count;
- manageable quantized storage;
- strong agentic post-training;
- long context;
- local deployment.

Meridian should test a 35B senior model for:

- multi-domain investigation planning;
- final synthesis;
- difficult code reasoning;
- tool-sequence planning;
- residual semantic verification;
- complex evidence conflicts;
- supervisor role for 4B/9B workers.

The 35B tier may be cheap enough to use frequently rather than only as emergency escalation.

## 70B–80B should become the local frontier tier

The 70B/80B class should be used for tasks where 4B/9B failure appears capacity-bound:

- hypothesis-to-artifact construction;
- unfamiliar code/vulnerability research;
- high-ambiguity causal inference;
- difficult cross-domain synthesis;
- weak-verifier tasks;
- long-horizon planning where state cannot be cleanly decomposed;
- final review of high-consequence local actions.

The system should compare:

- dense 70B;
- sparse 70–80B with low active parameter count;
- 35B specialist + extra test-time compute.

The important metric is **verified capability per device-hour**, not raw parameter count.

## Known ceiling: selected frontier-equivalent workloads already exist

Current evidence supports a strong but bounded claim:

> 26B–35B open/local models can already match or exceed frontier models on selected controlled tool-use, agentic, and research tasks.

AgentFloor evaluates open models up to 32B against GPT-5 in a deterministic tool environment.

The strongest open model is statistically equivalent to GPT-5 in aggregate in the reported benchmark.

The important caveat is that the hard long-horizon planning tier remains unreliable for both open and frontier systems.

Thus:

- frontier equivalence on bounded tasks is already plausible;
- universal long-horizon reliability is not solved by merely reaching 35B.

## Known ceiling: post-training matters as much as raw size

Agents-A1 is particularly instructive because its result comes from **agent-horizon scaling and multi-teacher specialization**, not simply increasing base model parameters.

This supports a core Meridian hypothesis:

```
35B generic
<
35B agent-specialized
<
35B agent-specialized + Meridian architecture
```

The third term remains unmeasured.

That is the experimental opportunity.

## Unknown frontier 1 — 35B/70B + Meridian may be multiplicative

Small-model Meridian was largely motivated by compensating for weak reasoning.

At 35B/70B, many residual failures may move into a different regime:

- the model can use richer evidence without aggressive compression;
- it can maintain more coherent plans;
- it can interpret verifier feedback better;
- it can generate more diverse valid hypotheses;
- it can synthesize across specialists rather than merely route among them.

This creates the possibility that architecture and scale become **complementary** rather than substitutive.

A 70B model may gain more from Meridian than a 4B does.

That possibility must be tested rather than assumed.

## Unknown frontier 2 — local systems may beat frontier APIs on organization-specific tasks

A stateless frontier model may have stronger generic reasoning.

A mature local Meridian system may have:

- years of verified incident history;
- exact topology;
- organization-specific policy semantics;
- specialist calibration;
- environment-specific failure patterns;
- tested remediation procedures;
- local simulators;
- direct low-latency tool access.

This raises a realistic hypothesis:

> a 35B–70B persistent local system can outperform a stronger stateless frontier model on the organization it has learned deeply.

This is not because the base model is smarter.

It is because **environment-specific accumulated competence can outweigh generic scale**.

## Unknown frontier 3 — sparse 80B models may create a new local regime

Qwen3-Next-80B-A3B demonstrates an especially important configuration:

```
~80B stored capacity
~3B active experts/token
~48 GB Q4 weights
```

This creates a new local research space between:

- dense 35B;
- dense 70B;
- enormous datacenter MoEs.

Potential advantage:

- broad parametric knowledge/capability library;
- low active compute;
- fast enough inference if experts are efficiently placed/cached;
- feasible on 48–64 GB accelerator/unified-memory classes or heterogeneous CPU/GPU systems.

Potential weakness:

- all weights still require storage/memory bandwidth;
- MoE expert routing can become bandwidth-bound;
- quantized expert placement matters;
- low active FLOPs do not imply low total memory movement.

This should be a first-class Meridian systems experiment.

## Unknown frontier 4 — asymmetric 35B/70B collaboration

Do not default to two models debating.

Test explicit asymmetric roles.

### 35B proposer -> 70B critic

Useful when:

- proposal generation is cheap;
- failure cases are sparse;
- high-quality review matters.

### 70B planner -> 35B executor

Useful when:

- global decomposition is difficult;
- bounded substeps are easy.

### Several 35B candidates -> deterministic verifier

Useful when:

- correct solutions are search-limited;
- verification is strong.

### 35B specialist -> 70B artifact constructor

Especially relevant to the CyberGym failure pattern where smaller models can discover the right vulnerability hypothesis but fail to construct the final artifact.

### 70B synthesis -> 4B/9B evidence workers

Potentially the highest practical architecture for investigations:

```
70B senior
  ↓
decompose
  ↓
many cheap evidence workers
  ↓
typed evidence
  ↓
70B final synthesis
```

## Unknown frontier 5 — long-horizon local research loops

Agents-A1 suggests training on very long knowledge-action trajectories can materially change agent capability.

Meridian could push this further by separating one long agent run into a persistent host-owned research state:

```
question
 -> hypothesis set
 -> experiments
 -> observations
 -> falsification
 -> memory
 -> revised hypotheses
 -> further experiments
 -> final synthesis
```

The model need not keep the entire process in one context.

This may allow a 35B/70B local agent to work on one problem for hours or days without transcript collapse.

The real scaling variable becomes:

> verified research steps per problem

rather than:

> tokens in one completion.

## Unknown frontier 6 — capability libraries larger than one model

A 35B/70B backbone can itself carry specialist adapters.

The system could maintain:

- Sentinel-35B;
- Scalpel-35B;
- Watchtower-35B;
- Harbinger-35B;
- research/science adapter;
- verifier adapter;
- organization-specific adapter.

Only the relevant adapter is active.

The total stored specialist intelligence can therefore exceed the active model footprint substantially.

This should be treated as a **capability library**, not one static model.

## Unknown frontier 7 — local compute can be spent more aggressively

Using a paid frontier model creates marginal token cost.

Local inference changes the economics.

Once hardware exists, Meridian can afford:

- repeated candidate generation;
- overnight research;
- simulation;
- adversarial retesting;
- memory consolidation;
- curriculum generation;
- replay and regression tests.

Therefore a local 35B/70B model may deliberately trade **hours for correctness** on difficult work.

A human analyst often does exactly this.

The relevant comparison may become:

```
frontier API:
one excellent 2-minute attempt

vs

local Meridian:
35B/70B + tools + simulations + 20 verified attempts over 45 minutes
```

For non-urgent research, the latter may win.

This is one of the least explored but most important hypotheses.

## Unknown frontier 8 — local cyber research factory

A high-capacity Meridian could support a closed research loop:

```
70B research planner
     ↓
35B domain specialists
     ↓
4B/9B parallel workers
     ↓
simulators / test harnesses / graph engines
     ↓
deterministic verifier
     ↓
70B synthesis
     ↓
verified memory
     ↓
targeted curriculum
     ↓
updated specialists
```

This is not ordinary multi-agent chat.

It is a local research institution encoded as software.

The collective system can perform more total cognition than any one resident model.

## Unknown frontier 9 — model-scale routing inside one problem

A task should not be assigned one model size.

Example:

```
extract 400 log facts             -> 4B workers
normalize entities                -> deterministic
generate incident hypotheses      -> 35B
test hypotheses                   -> tools/simulation
resolve stubborn contradiction    -> 70B
write final investigation report  -> 35B or 70B
```

This could outperform a 70B-only system because the 70B spends its context/compute only on the hard portions.

## Unknown frontier 10 — large local models may become better verifiers

One of the biggest weaknesses in the small-model thesis is verification.

A 35B/70B verifier may cross a useful capability threshold.

Meridian should separately measure:

```
4B generator -> 70B verifier
35B generator -> 70B verifier
70B generator -> 35B verifier
70B generator -> deterministic verifier
```

The goal is to discover whether large local models can close the residual semantic-verification gap without external frontier inference.

## Hardware implications

Approximate current Q4 model weights:

- Qwen3.6-35B-A3B: ~20.5–22.1 GB;
- Qwen3-Next-80B-A3B: ~48.4 GB.

This means:

### 35B sparse tier

Practical on:

- 24 GB GPU with careful context/runtime management;
- 32 GB GPU comfortably;
- 64 GB system RAM with partial GPU offload;
- heterogeneous CPU/GPU inference.

### ~70B dense / ~80B sparse tier

Practical on:

- ~48 GB VRAM class for Q4 with careful headroom;
- 2 × 24 GB may be tight once KV/runtime overhead is included;
- 2 × 32 GB is much healthier;
- 64–128 GB unified/system memory for slower local inference;
- multi-device clustering.

llama.cpp can distribute model weights and KV cache across local and remote devices, but its RPC backend is currently explicitly described as proof-of-concept, fragile and insecure.

exo is pursuing automatic topology-aware local clustering and tensor parallelism.

For Haven/Meridian, **task-level sharding remains safer and more immediately useful than exposing raw llama.cpp RPC across security-sensitive endpoint networks**.

## Research program: High-Capacity Meridian

### HC0 — raw controls

Run:

- 35B generic;
- 70/80B generic.

### HC1 — Meridian-lite

Add:

- evidence shaping;
- external state;
- tool narrowing;
- deterministic verification.

### HC2 — domain-specialized

Train/route domain-specialized 35B and selected 70B adapters.

### HC3 — adaptive test-time compute

Measure:

- pass@1;
- pass@2;
- pass@4;
- verifier-assisted search;
- model-size escalation.

### HC4 — hierarchy

Compare:

- 70B-only;
- 35B-only;
- 70B planner + 35B workers;
- 35B planner + 70B artifact/verifier;
- 70B + 4B/9B evidence fleet.

### HC5 — persistent environment memory

Add:

- verified episodic memory;
- procedural memory;
- organization model;
- specialist calibration.

### HC6 — long-horizon research

Give systems:

- 5 minutes;
- 30 minutes;
- 2 hours;

on the same difficult problem.

Measure capability as a function of **research time**, not merely model size.

### HC7 — frontier comparison

Compare the best fully local system against contemporary frontier references under:

- equal task interface;
- equal evidence;
- equal wall-clock;
- natural operational budgets.

## Core metrics

Report:

- verified success;
- frontier-relative score;
- artifact validity;
- evidence precision;
- unsupported-claim rate;
- long-horizon constraint retention;
- verifier precision/recall;
- human interventions;
- device-hours;
- joules/task where possible;
- model escalation frequency;
- successful local-only rate;
- task latency;
- memory use;
- network bytes;
- accumulated-experience lift.

## New headline metric

Define **Frontier Independence Rate (FIR)**:

```
FIR =
  tasks successfully completed and independently verified
  -------------------------------------------------------
  all eligible tasks
```

with **zero frontier-model calls**.

This directly measures the operational goal.

Also report FIR by difficulty class.

A system could have:

```
routine FIR = 99%
hard FIR    = 85%
research FIR = 50%
overall FIR = 93%
```

That is more operationally meaningful than one benchmark average.

## Another new metric: Local Research Gain

For long-running work:

```
LRG(t) =
  verified success after local research budget t
  - verified success at one-pass baseline
```

Measure at:

- 30 seconds;
- 5 minutes;
- 30 minutes;
- 2 hours.

This tests the central speculative hypothesis that **time can substitute for some fraction of model scale when local inference is cheap and verifiable**.

## Falsification

The high-capacity thesis should be weakened if:

- 35B/70B gains vanish after private evaluation;
- long-horizon scaling mainly produces loops rather than progress;
- local verifiers remain too weak;
- memory poisoning outweighs experience gains;
- 70B-only beats the hierarchy at lower total cost;
- Q4 quantization materially damages hard-reasoning reliability;
- distributed orchestration overhead dominates;
- frontier systems retain a large gap even after matched architecture.

## Current judgment

### Known today

35B-class specialized local agents are already capable enough to compete with frontier systems on selected agentic/research benchmarks.

70B dense reasoning models and ~80B sparse models are locally deployable with high-end consumer/workstation hardware or multi-device systems.

Sparse MoE models are creating an especially important new regime: **tens of billions of stored parameters with only a few billion active per token**.

### Plausible near frontier

A well-built 35B Meridian system could plausibly become a primary senior cyber agent rather than a fallback.

A 70B/80B Meridian system could plausibly remove the need for frontier inference from most structured enterprise-security tasks.

### Hitherto unknown

It remains genuinely unknown whether:

- persistent experience + specialist post-training + verified search lets a 35B/70B local system outperform frontier models on its own organization;
- local long-running research can trade hours for enough compute to close hard reasoning gaps;
- an 80B-total/3B-active MoE with architecture can become a practical local "frontier workstation brain";
- heterogeneous 4B/9B/35B/70B collaboration beats one monolithic 70B;
- a local cyber research factory can compound verified experience fast enough to produce sustained capability growth.

These are now the highest-value Meridian questions.

## Recommended strategic target

Stop treating the 35B tier as merely a teacher.

Treat it as a **candidate production brain**.

Treat 70B/80B as the **local frontier research tier**.

Keep 4B/9B because they remain valuable for specialization, parallelism and endpoint distribution.

The aspirational hierarchy becomes:

```
many cheap workers
      +
35B senior cognition
      +
70/80B deep local cognition
      +
deterministic reality checks
      +
persistent experience
      =
frontier-independent security system
```

Whether that final equality holds is an empirical question.

Meridian should now try to find out.

## Sources

- InternScience, Agents-A1: https://github.com/InternScience/Agents-A1
- Agents-A1 project: https://internscience.github.io/Agents-A1/
- Qwen3.6-35B-A3B: https://huggingface.co/Qwen/Qwen3.6-35B-A3B
- Qwen3-Next-80B-A3B-Instruct: https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Instruct
- Qwen3-Next-80B-A3B GGUF: https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Instruct-GGUF
- DeepSeek-R1 / 70B distillation: https://huggingface.co/deepseek-ai/DeepSeek-R1
- AgentFloor: https://arxiv.org/abs/2605.00334
- llama.cpp RPC backend: https://github.com/ggml-org/llama.cpp/blob/master/tools/rpc/README.md
- exo distributed inference: https://github.com/exo-explore/exo
