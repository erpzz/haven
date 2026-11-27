# Meridian Research 04 — How Good Could This Truly Get?

Status: research forecast, 2026-11-26.
Checkpoint: MERIDIAN-04.1.
Scope: additive research only. This does not alter frozen W2 evaluation, training, reserve, promotion, or runtime policy.

## Executive answer

There are two very different answers.

### Current-technology answer

With 2026 open models, current post-training methods, deterministic tools, structured evidence, specialist adapters, verifier-backed search, persistent external state, and scale-aware routing, a Meridian-like system could plausibly become **frontier-equivalent on a substantial subset of bounded, verifiable enterprise-security tasks**.

That does not mean universal frontier-model parity.

The strongest current opportunity is where:

- task semantics are narrow;
- the environment is instrumented;
- relevant evidence can be externalized;
- correctness is cheaply testable;
- workflows can be decomposed;
- specialist data can be generated;
- and latency can be traded for verification/search.

On such tasks, current evidence already includes 4B systems approaching or exceeding frontier systems.

### Rapid-development answer

If current work on specialization, verifiable RL, learned inference routing, test-time compute, memory-aware agents, and distributed verified search compounds over the next model/research generations, it is scientifically plausible that a **heterogeneous 4B/9B local fabric could deliver frontier-like operational capability across most structured enterprise-security workflows**, while escalating only a minority of irreducibly open-ended tasks to larger models.

The strongest version of the thesis is not:

> a 4B becomes universally as intelligent as a frontier model.

It is:

> a system with very few active neural parameters at any one time can exhibit much greater effective capability by accumulating specialists, external knowledge, verified experience, search, and heterogeneous compute.

The remaining ceiling is likely to be tasks dominated by novel abstraction, open-ended causal reasoning, weakly verifiable synthesis, and genuinely unfamiliar long-horizon planning.

## What is already demonstrated in 2026

### Narrow security specialization can nearly close the frontier gap

PrivEsc-LLM post-trains Qwen3-4B using SFT and RL with verifiable rewards.

Reported held-out Linux privilege-escalation results:

- vanilla Qwen3-4B: 40.8%;
- SFT: 79.2%;
- RL-trained 4B: 93.3% in the latest reported evaluation;
- Claude Opus 4.7: 100% at the same primary budget.

Earlier paper versions report 95.8% versus Claude Opus 4.6 at 97.5%.

The important signal is not the version-specific number. It is that a 4B model moved from roughly 40% to the mid-90s on an interactive, multi-step security domain because the task supported procedural generation and exact rewards.

### Cybersecurity specialists already beat much larger models on some tasks

CyberPal 2.0 spans 4B–20B.

Its ICML 2026 paper reports:

- its best 20B model ranks first on core threat-investigation tasks against GPT-4o, o1, o3-mini and Sec-Gemini v1;
- the smallest 4B model ranks second on those same core tasks;
- the family outperforms nearly all tested frontier models on cyber threat-intelligence knowledge tasks.

This is direct evidence that parameter count is not the dominant variable on sufficiently aligned domain distributions.

### Small subagents can replace expensive frontier subagents

Terminus-4B specializes Qwen3-4B for terminal execution.

Microsoft reports that it can reduce main-agent token usage by up to ~30% with no benchmark-performance loss and can close or exceed the gap to frontier execution subagents such as Claude Sonnet/Opus and GPT-5.3-Codex for its specialized role.

This supports heterogeneous cognitive hierarchies.

### Specialized 4B/9B systems can already approach proprietary agents

Microsoft Fara1.5, built on Qwen3.5, reports:

- 4B: 80.8 WebVoyager / 57.3 Online-Mind2Web;
- 9B: 86.6 / 63.4;
- 27B: 88.6–89.3 / 72.3 depending the reported table/version;
- OpenAI Operator reference: 87.0 / 58.3;
- FaraGen1.5 GPT-5.4 solver: 93.4 / 83.4.

The 4B is already essentially at Operator's reported Online-Mind2Web score; the 9B exceeds it there and nearly matches the WebVoyager result.

This is not general intelligence, but it is clear domain-specific frontier-equivalence.

### Adapter specialization can beat much larger raw models

MoLoRA reports Qwen3-1.7B with per-token routed LoRA specialists exceeding Qwen3-8B across four reasoning benchmarks.

Again, this is not evidence of universal capability. It demonstrates that modular specialization can move the model-size frontier substantially.

### Tool-integrated verification can invert model-size ordering

T1 reports a Llama-3.2 1B under tool-integrated test-time scaling outperforming Llama-3.1 8B on MATH.

The mechanism is important for Meridian: deterministic tools remove memorization/exactness burden from the small verifier.

### Model routing and test-time scaling are becoming one optimization problem

UniScale formalizes joint routing across different model sizes and varying test-time compute.

Its result supports a core Meridian design principle: do not choose model size globally. Learn whether the next unit of computation should be another sample, another model, another verifier, or a stronger model.

### Memory can turn past failures into future capability

Google ReasoningBank reports gains from persistent experience memories and memory-aware test-time scaling.

The system extracts lessons from both successful and failed trajectories, and the reported experiments show improved success and reduced execution steps.

This supports the idea that a persistent local system can accumulate effective capability that does not live in its base weights.

## Current-reality forecast for Meridian

The following are **research priors**, not measured Haven results.

They represent my estimate of what a well-built system could plausibly achieve with currently available 2026 technology after specialist training and architecture maturation.

Use "frontier-relative" to mean performance relative to a strong contemporary frontier agent exposed to a comparable interface and evidence environment.

### Task class A — bounded and exactly verifiable

Examples:

- identity graph questions;
- policy/scope evaluation;
- configuration verification;
- known Linux/Windows workflow;
- code repair with strong tests;
- exact alert/evidence correlation;
- known network reachability;
- structured remediation validation.

Current realistic ceiling:

- 4B Meridian: roughly 85–98% of frontier operational performance;
- 9B Meridian: roughly 90–100%+;
- hybrid Meridian: frontier-equivalent or occasionally superior on cost/latency/reliability.

Why the range is high:

- exact verifiers remove one of the largest weaknesses of SLMs;
- specialist training has already demonstrated very large gains;
- much domain knowledge can be externalized;
- tool/state burdens can be host-owned.

### Task class B — structured but partially ambiguous

Examples:

- SOC investigations;
- incident timelines;
- cloud/identity causal chains;
- code triage where tests are incomplete;
- multi-source evidence synthesis;
- remediation planning with several valid choices.

Current realistic ceiling:

- 4B Meridian: ~70–90% of frontier;
- 9B Meridian: ~80–95%;
- hybrid: ~85–97%.

The principal residual deficits are:

- ambiguity;
- verifier weakness;
- long-horizon planning;
- evidence-utilization failures;
- subtle causal inference.

### Task class C — open-ended hard cyber reasoning

Examples:

- unfamiliar vulnerability research;
- novel exploit/artifact construction;
- unusual cross-domain attack chains;
- architecture design with weak feedback;
- investigation where neither evidence nor success criteria are clear.

Current realistic ceiling:

- 4B Meridian: ~40–70% of frontier;
- 9B Meridian: ~55–80%;
- hybrid: ~65–88%.

This is where raw model capability remains important.

### Task class D — genuinely novel research

Examples:

- inventing a new exploitation technique;
- new theoretical security reasoning;
- solving a poorly specified problem with no verifier;
- open-ended scientific or engineering synthesis.

Current realistic ceiling:

- 4B/9B Meridian: materially below frontier;
- architecture can improve search and evidence quality but cannot reliably manufacture abstractions that no worker can produce.

This is the current hard ceiling.

## Why these estimates are not absurdly optimistic

The highest bands are already partially observed in narrow domains:

- PrivEsc-LLM 4B reaches the 90s against frontier;
- CyberPal 4B ranks near the top against frontier models on selected cyber tasks;
- Terminus-4B can substitute for frontier execution subagents;
- Fara1.5 4B/9B competes directly with proprietary computer-use agents.

Meridian would attempt to combine several mechanisms that those systems mostly explore separately:

- specialist training;
- adapter routing;
- deterministic evidence compilation;
- external state;
- verifier-backed search;
- scale-aware escalation;
- persistent experience memory.

There is no proof that the gains add linearly.
They probably do not.

But the ingredients individually have enough empirical support to make a strong integrated result plausible.

## Why current Meridian would still fail

### Small models remain poor verifiers

SLMs can generate a correct candidate without recognizing it reliably.

Hence deterministic verification must dominate wherever possible.

### Generic RAG is dangerous below ~7B

Current empirical work finds severe utilization and distraction failures in <=7B models even with oracle passages.

Meridian must compile evidence aggressively for 4B rather than copy-paste documents.

### Coordination can destroy capability

Google's 2026 study reports:

- +80.9% gain for centralized multi-agent coordination on a parallelizable finance task;
- 39–70% degradation on a sequential planning task;
- independent multi-agent errors amplified up to 17.2x;
- their predictive model selected the optimal agent architecture for 87% of unseen task configurations.

This means a swarm is not inherently intelligent.

### Test-time compute has capacity ceilings

UniScale explicitly notes diminishing returns and capacity ceilings for single-model test-time scaling.

No practical amount of 4B resampling guarantees a solution that lies outside the model's candidate-generation distribution.

### Verifiers themselves can be wrong

An incomplete test suite or flawed gold turns search into reward hacking.

The entire thesis depends heavily on verifier quality.

## Rapid-development forecast

This is the second answer: what appears scientifically plausible if several currently active directions improve quickly.

This is not a prediction of what will definitely happen.

## Development vector 1 — specialist routing becomes native

Current MoLoRA-like work makes specialization modular.

Likely near-term evolution:

```
shared 4B/9B backbone
+ hundreds of small adapters
+ learned token/layer routing
+ capability registry
+ automatic expert composition
```

If routing overhead falls and adapter training becomes cheap, total stored expertise could grow dramatically without increasing active parameters proportionally.

This could create systems whose **capability library is much larger than their active neural footprint**.

## Development vector 2 — verifiable RL expands beyond toy/narrow domains

PrivEsc-LLM demonstrates the recipe where success can be procedurally generated and verified.

Rapid development is likely in:

- code;
- configuration;
- infrastructure;
- cloud;
- identity;
- networking;
- policy;
- query generation;
- repair.

As more environments become simulatable, more intelligence becomes trainable with exact outcomes rather than subjective reward models.

The frontier-equivalent region should therefore expand.

## Development vector 3 — test-time compute becomes learned rather than heuristic

UniScale and related work are early versions of a compute market.

A mature system could learn:

```
given state S:
  retrieve?
  run tool?
  generate another candidate?
  ask alternate specialist?
  invoke 9B?
  run deterministic verifier?
  simulate?
  stop?
```

This should make extra compute substantially more efficient than naive "think longer."

## Development vector 4 — memory becomes accumulated competence

ReasoningBank demonstrates an early form of this.

A mature persistent Meridian could accumulate:

- local environment knowledge;
- failure patterns;
- trusted procedures;
- calibration histories;
- which specialist succeeds where;
- negative lessons;
- organization-specific semantics.

This creates a dimension absent from stateless benchmark comparisons:

> lifetime experience.

A 4B/9B system with years of well-curated organization-specific experience might outperform a stronger stateless model on that organization's environment.

## Development vector 5 — distributed search gets better verifiers

Google's November 2026 Antigravity /teamwork work shows the frontier version of the same general pattern:

- parallel exploration;
- long-running agents;
- dedicated falsifiers such as formal proof checkers, tests, simulators and hardware counters.

Their reported projects use frontier models, not small local models, so this does not establish Meridian's thesis.

But it is evidence that **parallel search + strong falsification** is becoming a productive architecture even at the frontier.

If small specialists become sufficiently capable, this architecture can migrate downward in model size.

## Development vector 6 — model generations themselves improve

A future 4B is not today's 4B.

Fara1.5 illustrates how much capability can move within a similar size class through stronger base models, better environments, synthetic data and verifiers.

Therefore Meridian receives two compounding gains:

```
better small base model
×
better system architecture
```

This is important when forecasting.

## Plausible accelerated-development ceiling

If the above trends compound strongly, my research prior for a mature heterogeneous Meridian is:

### Bounded enterprise cybersecurity

Potentially **near-universal frontier parity** on tasks with:

- explicit evidence;
- available tools;
- simulatable environments;
- good verifiers.

A 4B specialist may handle most routine work.
9B may handle ambiguity.
Larger models become rare escalation paths.

### Broad enterprise security operations

Potentially **85–95% of contemporary frontier operational capability** at the system level, depending on the benchmark definition.

This does not mean identical reasoning style.

It means comparable verified task outcomes over the organization's real task distribution.

### Hard novel cyber research

Potentially **70–90% of contemporary frontier capability** if:

- search is parallelizable;
- partial progress is verifiable;
- specialist diversity is real;
- external tools can expose errors.

Still likely lower where novel abstraction dominates.

### Universal open-ended frontier reasoning

No strong scientific basis currently supports claiming that tiny active models plus orchestration will reach universal frontier parity.

There may be irreducible per-step representation/reasoning requirements that cannot be recovered cheaply through decomposition.

The correct research posture is to locate that boundary empirically.

## The most ambitious plausible architecture

A mature Meridian could look like:

```
persistent evidence/memory substrate
         │
         ▼
compute-market controller
         │
         ├── deterministic engines
         │
         ├── 1–2B micro-specialists
         │
         ├── 4B domain specialists
         │
         ├── 9B senior reasoners
         │
         └── rare large-model escalation
         │
         ▼
parallel candidate generation
         │
         ▼
formal / executable / deterministic falsifiers
         │
         ▼
verified synthesis
         │
         ▼
experience consolidation
         │
         ▼
future routing/training
```

Only a small fraction of the total stored intelligence is active at one time.

The system grows by accumulating:

- adapters;
- memory;
- procedures;
- verifiers;
- datasets;
- calibration;
- environment knowledge.

This is a fundamentally different scaling axis from "make one neural network larger."

## The strongest scientific possibility

The most interesting possibility is that **effective intelligence becomes increasingly separable from active parameter count on domains with strong external structure**.

For such domains:

```
effective capability
≈
base reasoning ability
× specialization
× evidence quality
× search
× verification
× memory
× tools
```

This is not literally a validated multiplicative law.

It expresses the architectural thesis.

If several factors can be supplied externally, the neural model only needs to provide the residual generative reasoning.

## The strongest scientific limit

Architecture cannot recover a candidate that no component can produce.

If:

- no specialist generates the correct abstraction;
- no retrieval source contains it;
- no search branch discovers it;
- no verifier provides informative gradients;

then additional orchestration only rearranges failure.

This is the likely irreducible role of larger/better foundation models.

## What I would bet on

### With 2026 technology

I would bet that a serious Meridian build can make:

- 4B specialists frontier-like on several narrow cyber verticals;
- 9B Meridian highly competitive with frontier models across a broader structured-security distribution;
- the mixed 4B/9B system substantially better than either raw model and cheaper/local/private compared with using frontier inference everywhere.

I would **not** bet that it matches frontier models on arbitrary cybersecurity research.

### If the current research directions accelerate

I would bet that within this architectural paradigm, the amount of enterprise security work requiring a frontier-sized model shrinks dramatically.

The most likely end state is not "tiny model replaces frontier AI."

It is:

> Most work never reaches the frontier tier because specialist local intelligence, exact tools, persistent memory, and verification already solve it.

That is a much more achievable and operationally consequential form of frontier-equivalent capability.

## Experimental requirement

Meridian must measure this rather than narrate it.

The eventual study should produce a heatmap:

```
                         4B     9B     hybrid    large    frontier
identity                 ...
SOC                      ...
cloud                    ...
network                  ...
code                     ...
DFIR                     ...
host                     ...
hard research            ...
```

for:

- raw;
- specialist;
- Meridian-lite;
- full Meridian.

Then calculate:

- frontier-relative performance;
- cost;
- latency;
- active parameters;
- device-hours;
- escalation rate;
- verifier coverage.

This will tell us exactly how much of "frontier" is actually necessary.

## Sources

- CyberPal 2.0 / Toward Cybersecurity-Expert Small Language Models, ICML 2026: https://proceedings.mlr.press/v306/levi26a.html
- PrivEsc-LLM / Post-Training Local LLM Agents for Linux Privilege Escalation with Verifiable Rewards, 2026: https://arxiv.org/abs/2603.17673
- Terminus-4B, Microsoft Research 2026: https://www.microsoft.com/en-us/research/publication/terminus-4b-can-a-smaller-model-replace-frontier-llms-at-agentic-execution-tasks/
- Fara1.5, Microsoft Research 2026: https://www.microsoft.com/en-us/research/articles/fara1-5-computer-use-agent/
- MoLoRA, Microsoft Research 2026: https://www.microsoft.com/en-us/research/publication/molora-composable-specialization-via-per-token-adapter-routing/
- T1, ICLR 2026: https://proceedings.iclr.cc/paper_files/paper/2026/hash/776a5f2c7d6dd4b0d83145fc044e2726-Abstract-Conference.html
- UniScale, ICML 2026: https://proceedings.mlr.press/v306/huang26bd.html
- Can Small Language Models Use What They Retrieve?, 2026: https://arxiv.org/abs/2603.11513
- Google Research, Towards a Science of Scaling Agent Systems, 2026: https://www.research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/
- Google Research, ReasoningBank, 2026: https://www.research.google/blog/reasoningbank-enabling-agents-to-learn-from-experience/
- Google Research, Antigravity /teamwork, 2026: https://research.google/blog/advancing-science-engineering-with-antigravitys-teamwork-feature/
