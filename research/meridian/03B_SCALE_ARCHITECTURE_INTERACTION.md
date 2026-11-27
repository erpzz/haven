# Meridian Research 03B — Model Scale × Architecture Interaction

Status: research design note, 2026-11-26.
Checkpoint: MERIDIAN-03B.1.
Scope: additive research only. This does not alter frozen W2 evaluation, training, reserve, promotion, or runtime policy.

## Executive conclusion

Meridian must compare **equally architected systems across model scales**.

The primary experiment is not:

```
raw 4B
vs
4B + Meridian
vs
raw 9B
```

It is:

```
raw 4B
4B + Meridian

raw 9B
9B + Meridian

optional larger local + Meridian

hybrid 4B/9B + Meridian
```

This allows us to answer four separate questions:

1. How much capability does model scale buy by itself?
2. How much capability does Meridian buy at each scale?
3. Does Meridian compress or amplify the 4B→9B gap?
4. Is a heterogeneous 4B/9B hierarchy better than either pure system?

The current evidence suggests the answer will be task-dependent.

## The interaction we actually need to measure

Let:

- `R4` = raw 4B score;
- `M4` = 4B under Meridian;
- `R9` = raw 9B score;
- `M9` = 9B under Meridian.

Define:

```
architecture_gain_4 = M4 - R4
architecture_gain_9 = M9 - R9

raw_scale_gain      = R9 - R4
system_scale_gain   = M9 - M4

interaction =
    architecture_gain_9
  - architecture_gain_4
```

Interpretation:

- interaction ≈ 0: architecture and scale are roughly additive;
- interaction > 0: architecture benefits the 9B more — complementarity;
- interaction < 0: architecture disproportionately helps the 4B — substitution/compression;
- both M4 and M9 improve strongly: architecture is useful at both scales.

A second useful measure is:

```
gap_compression =
  1 - (M9 - M4) / (R9 - R4)
```

when `R9 > R4`.

Positive values mean Meridian narrows the scale gap.
Negative values mean Meridian widens it because the larger model exploits the system better.

Neither outcome is inherently bad.

## Why this matters

A common small-model research mistake is to show:

```
small model + tools > large raw model
```

and stop.

That establishes that architecture matters, but it does **not** establish that the small model is the best substrate for the architecture.

The larger model may gain just as much—or more—from:

- the same tools;
- the same evidence compiler;
- the same verifier;
- the same specialist adapters;
- the same external state;
- the same memory;
- the same test-time compute controller.

Meridian should therefore optimize the **whole system frontier**, not defend a predetermined parameter count.

## Direct evidence: same agentic architecture across Qwen3 scale

Żywot et al. evaluate Qwen3 4B, 8B, 14B and 32B in the same adapted Agentic-Reasoning framework with the same search, coding and mind-map tools.

Under the same no-explicit-thinking comparison:

| model | no-tools | agentic | architecture gain |
|---|---:|---:|---:|
| 4B | 6.06 | 13.33 | +7.27 |
| 8B | 6.06 | 10.30 | +4.24 |
| 14B | 7.27 | 17.58 | +10.31 |
| 32B | 9.70 | 25.45 | +15.75 |

These results are noisy and benchmark-specific, and the raw Qwen3 models do not scale monotonically in this particular GAIA setup.

But the important qualitative point is robust:

> tool/agent architecture continues to add large absolute gains at larger model sizes.

The strongest 32B configuration is not merely a bigger raw model; it is the bigger model **inside the agent architecture**.

The paper also reports that larger models show more stable tool-use patterns, while smaller 4B models remain more search-focused and can have reasoning/action misalignment.

This is evidence for **complementarity**, not a pure substitution story.

## Direct evidence: same specialized system recipe at 4B, 9B, 27B

Microsoft Fara1.5 provides an especially useful controlled example.

The family uses the same Qwen3.5-derived computer-use recipe and fixed training-data setup at three scales:

| model | WebVoyager | Online-Mind2Web |
|---|---:|---:|
| Fara1.5-4B | 80.8 | 57.3 |
| Fara1.5-9B | 86.6 | 63.4 |
| Fara1.5-27B | 88.6 | 72.3 |

Holding the specialized training recipe fixed, performance improves monotonically with model size.

This is the exact kind of experiment Meridian needs.

The 4B system is already strong.
The 9B system is stronger.
The 27B system is stronger still.

Therefore:

> specialization and model scale can stack.

The architecture does not eliminate the value of larger backbones.

## Direct evidence: architecture may compress the scale gap

The opposite interaction also occurs.

Variation in Verification reports that, using the same verifier setup, the post-verification gap between Gemma2-9B and Gemma2-27B can shrink by 75.7% in some tested settings.

This demonstrates a different regime:

> external verification can disproportionately help a weaker generator and compress the model-size gap.

This is exactly why one scalar claim such as "architecture helps small models" is inadequate.

Different architecture layers may interact with model size differently:

- tools may help all scales;
- retrieval may require enough model capacity to exploit context;
- verification may compress the generator-size gap;
- long free-form reasoning may favor larger models;
- specialization may stack with scale;
- parallel candidate generation may favor smaller models under fixed compute.

Meridian must measure these layers separately.

## Retrieval may produce a threshold effect

"Can Small Language Models Use What They Retrieve?" evaluates models from 360M through 8B under no retrieval, BM25, dense retrieval and oracle retrieval.

The reported result is a warning: models of 7B or smaller frequently fail to use even oracle-provided evidence on questions they cannot answer parametrically, while retrieval can also distract answers they previously knew.

This implies a possible **capacity threshold** for generic retrieval utilization.

Meridian's evidence compiler is deliberately designed to be better than generic "paste chunks into prompt" RAG, so this result does not prove 4B will fail.

But it creates a major hypothesis:

> 9B + Meridian may benefit more from rich external memory than 4B + Meridian because the 9B may cross a context-utilization threshold.

If true, evidence compilation should be progressively stronger at 4B:

```
4B:
raw documents
 -> deterministic extraction
 -> normalized typed facts
 -> very compact packet

9B:
may tolerate richer evidence packets
 -> more ambiguity left for model reasoning
```

This is an example where the architecture itself may need to differ by model scale.

## Architecture should not be assumed scale-invariant

AgentArch evaluates 18 combinations of:

- orchestration;
- ReAct vs function calling;
- complete vs summarized memory;
- thinking integration.

Its central result is that architecture preferences are **model-specific** and use-case-specific.

Larger models are more robust across architectures, while smaller models can match them on simpler tasks under their own best architecture.

This strongly argues against benchmarking one fixed Meridian scaffold and assuming it is equally fair to 4B and 9B.

We need two views:

### Fixed-architecture comparison

Same exact Meridian configuration for both model sizes.

Purpose:

- clean scientific interaction measurement.

### Best-architecture-per-scale comparison

Tune only on a development set, independently for 4B and 9B.

Purpose:

- answer the deployment question:
  "What is the best system I can build with each scale?"

Both are necessary.

## Strong negative evidence against naive swarms

"Can Edge LLMs Team Up?" tests orchestrator-worker teams at multiple edge-model scales.

Its tested teams do not beat matched single-model baselines at any scale, and do not beat the oracle-aided best-of-N reference.

This is useful negative evidence.

It tells Meridian not to assume:

```
more small agents = more capability
```

The multi-agent layer must create one of:

- true task decomposition;
- error diversity;
- context isolation;
- specialized expertise;
- better verification;
- parallelizable search.

Otherwise coordination overhead simply consumes compute.

Google's controlled agent-scaling study reaches a compatible conclusion: parallelizable tasks can gain substantially from multi-agent systems, while sequential tasks can degrade; independent multi-agent errors can amplify dramatically, while centralized orchestration contains some of that amplification.

## A key hybrid result: strong main model + specialized 4B worker

Terminus-4B is especially important for Meridian's heterogeneous design.

Microsoft uses a post-trained Qwen3-4B as a terminal-execution subagent beneath a stronger main coding agent.

On a TerminalBench 2.0 ablation where all terminal work must flow through the subagent and Claude Opus 4.6 is the main agent:

| execution subagent | resolve |
|---|---:|
| no subagent | 58.7 |
| Opus | 58.7 |
| Sonnet | 57.3 |
| vanilla 4B | 60.0 |
| SFT-4B | 60.0 |
| Terminus-4B | 62.7 |

The specialized 4B subagent also reduces expensive main-agent token use substantially.

This demonstrates an important architecture:

```
strong planner / integrator
      ↓
small specialist worker
      ↓
tool/environment
```

A weak model does not need to replace the stronger model globally to create major system value.

## Meridian should therefore test four system families

### Family A — 4B Meridian

```
4B specialist backbone
+ specialist adapters
+ evidence compiler
+ external state
+ deterministic verifier
+ adaptive test-time compute
```

Objective:

- maximum capability per active parameter;
- broad endpoint deployability;
- high parallelism.

### Family B — 9B Meridian

Same conceptual architecture:

```
9B specialist backbone
+ specialist adapters
+ evidence compiler
+ external state
+ deterministic verifier
+ adaptive test-time compute
```

Objective:

- determine whether the larger SLM can exploit the architecture more effectively;
- find tasks where 4B hits a capability or evidence-utilization ceiling.

### Family C — asymmetric hybrid Meridian

```
9B planner / verifier / synthesis
            ↓
      4B specialists
            ↓
 deterministic tools
```

or selectively:

```
4B specialist
    ↓
if uncertain / verifier fails
    ↓
9B reviewer
```

This may be the cost-optimal architecture.

### Family D — role-reversed hybrid

Also test:

```
4B router/planner
      ↓
9B bounded specialist
```

This may work when routing is simple but domain reasoning is hard.

Do not assume the larger model belongs at the top of the hierarchy.
Measure role-specific marginal value.

## Role × scale matrix

The real study should assign model scale independently by role.

| role | deterministic | 4B | 9B |
|---|---:|---:|---:|
| routing | ✓ | candidate | candidate |
| planning | — | candidate | candidate |
| specialist generation | — | primary | candidate |
| evidence extraction | ✓ | candidate | candidate |
| verification | ✓ first | candidate | candidate |
| final synthesis | — | candidate | candidate |
| tool execution | ✓ host | no authority | no authority |

This yields architectures such as:

```
R0: deterministic router + 4B worker + deterministic verifier
R1: deterministic router + 9B worker + deterministic verifier
R2: 4B planner + 4B worker + deterministic verifier
R3: 9B planner + 4B worker + deterministic verifier
R4: 4B planner + 9B worker + deterministic verifier
R5: 9B planner + 9B worker + deterministic verifier
R6: 4B worker + 9B residual verifier
R7: 9B worker + 4B residual verifier
```

This decomposes "model size" into **where model capacity matters**.

## My strongest current hypothesis

The optimum is unlikely to be homogeneous.

I expect three task regimes.

### Regime 1 — architecture-dominated

Examples:

- exact evidence lookup;
- known graph workflows;
- tool syntax;
- state management;
- bounded investigation.

Likely winner:

```
4B + Meridian
```

9B may add little.

### Regime 2 — scale-and-architecture complementary

Examples:

- evidence-heavy synthesis;
- ambiguous causal reasoning;
- harder code reasoning;
- richer retrieval utilization.

Likely winner:

```
9B + Meridian
```

The 9B may exploit the same evidence/memory/tools better.

### Regime 3 — heterogeneous

Examples:

- long investigations;
- code/terminal workflows;
- high-volume evidence processing.

Likely winner:

```
4B specialist workers
+ 9B planner/verifier
+ deterministic execution
```

This is analogous to Terminus-style subagent specialization.

## A model of where architecture gain comes from

Let total task difficulty be decomposed into:

```
D =
  K  knowledge burden
+ E  evidence-utilization burden
+ P  planning burden
+ T  tool/orchestration burden
+ S  state/memory burden
+ V  verification burden
+ A  artifact-synthesis burden
```

Architecture can strongly reduce:

- T;
- S;
- parts of K;
- parts of E;
- parts of V.

Model scale remains more important for:

- residual E;
- P;
- A;
- open-ended V;
- novel abstraction.

Therefore increasing model size after architecture should still matter, but primarily on the residual difficulty dimensions.

This predicts that model-size gains will become **more concentrated by task family** after Meridian is added.

That is an experimentally testable prediction.

## Architecture can create a stronger 9B, not merely rescue a 4B

This is a conceptual correction to the original capability-recovery framing.

Instead of:

```
frontier
  ↑
architecture tries to drag 4B upward
```

use:

```
raw 4B ──────> Meridian 4B
raw 9B ──────> Meridian 9B
raw 27B ─────> Meridian 27B

              ↑
       same architectural ideas
```

The research question becomes:

> How does each architectural component change the scaling curve?

For example:

- does external state flatten the curve?
- does retrieval steepen it?
- does deterministic verification flatten it?
- does specialist training shift the entire curve upward?
- does test-time search help 9B more after the 4B saturates?
- does multi-agent decomposition help only above a coordination threshold?

This is much more scientifically valuable than a single 4B-vs-frontier comparison.

## Experimental design: scale × architecture factorial

The minimum first serious study should include:

### Model axis

```
4B
9B
```

Optional later:

```
~27B / large local
```

### Architecture axis

```
A0 raw/minimal
A1 evidence compiler
A2 + tool narrowing
A3 + external state
A4 + bounded workflow controller
A5 + deterministic verifier
A6 + adaptive test-time compute
A7 + specialists
A8 full Meridian
```

This creates a 2 × 9 grid for the initial 4B/9B study.

Do not need to run every cell on every task.

Use staged screening and then full matched runs on high-information cells.

## Add the hybrid axis after the pure systems

Only after `M4` and `M9` are characterized should we test:

```
H1  4B default, 9B escalation
H2  9B planner + 4B workers
H3  4B planner + 9B hard-task worker
H4  4B generators + 9B verifier
H5  9B generator + 4B verifier
```

H4 is particularly interesting because verification ability generally correlates with problem-solving ability, while weak generators can sometimes approach stronger generators after good verification.

## Fixed architecture vs optimized architecture

For scientific clarity, report two leaderboards.

### Leaderboard 1 — identical system

Same:

- evidence representation;
- tools;
- controller;
- memory;
- verifier;
- compute budget;
- decoding.

Only model size changes.

This estimates the pure scale interaction.

### Leaderboard 2 — size-optimized system

Allow development-set tuning of:

- context compression;
- test-time compute budget;
- specialist routing;
- memory detail;
- verifier assignment.

This estimates the best deployable system at each scale.

AgentArch strongly suggests these two rankings may differ.

## Quantization becomes part of the scale surface

Do not define "4B" and "9B" independently of precision.

Compare configurations by:

```
effective weight memory
+ KV cache
+ runtime buffers
+ adapter memory
```

The ICLR 2026 memory-optimization result suggests that for sufficiently small reasoning models, spending fixed memory on **more model capacity** can beat spending it on longer reasoning.

Therefore a fair 8 GB comparison might include:

```
4B higher precision + large KV
4B lower precision + very large KV
9B Q4 + smaller KV
9B lower precision + larger KV
```

The winner is an empirical question.

## Three fairness budgets

Every scale comparison should report three views.

### 1. Equal task interface

Same task/tools/evidence.
No cost equalization.

Question:

> Which system is strongest?

### 2. Equal wall time

Example:

```
30 seconds per task
```

A 4B may fit more calls.

Question:

> Which system feels best interactively?

### 3. Equal device compute / energy

Normalize device-seconds or estimated joules.

Question:

> Which system produces the most verified capability per unit of compute?

These answer different deployment questions.

## Model-size escalation should be learned, not hard-coded

UniScale is directly relevant.

It unifies:

- routing among different model sizes;
- test-time compute within each model.

This matches the Meridian problem almost perfectly.

The controller's action space should eventually include:

```
4B one pass
4B additional sample
4B alternate specialist
4B + stronger verifier
9B one pass
9B specialist
9B + additional search
stop
```

The controller should learn this from historical outcome/cost data.

## Why 9B may become the actual default

There is a credible possibility that 9B + Meridian wins so decisively that 4B becomes an edge tier rather than the main brain.

Reasons:

1. better raw reasoning;
2. stronger function-call performance on some benchmarks;
3. potentially better external-evidence utilization;
4. better residual verification;
5. enough local deployability on common 12–16 GB systems;
6. test-time compute may become more effective above the small-model scale threshold.

If that is what the data shows, Meridian should adopt it.

The 4B research remains valuable because:

- it maps the architecture's true recovery power;
- provides cheap distributed workers;
- enables edge endpoints;
- may dominate specific specialist roles.

## Why 4B may still remain strategically important

Even if 9B is the best single-node Meridian model, a distributed fleet may prefer many 4B jobs because:

- more endpoints can host them;
- more candidates can run concurrently;
- adapters swap cheaply;
- task sharding reduces wall time;
- specialized workers can be disposable/stateless;
- stronger nodes can reserve 9B for synthesis/verification.

Thus the distributed system may use both scales heavily.

## Prediction: Meridian may create a "cognitive hierarchy"

A plausible final topology is:

```
Tier 0
deterministic software
exact checks / graph / policy / execution

Tier 1
2B–4B micro-specialists
classification / extraction / narrow tool work

Tier 2
4B specialist reasoners
most domain tasks

Tier 3
9B senior reasoners
planning / ambiguity / synthesis / verification

Tier 4
large local MoE / dense
rare hard local escalation

Tier 5
frontier external
optional teacher/reference/exception path
```

The system routes **work**, not user sessions, through the hierarchy.

A single investigation may move repeatedly among tiers.

## New core metric: marginal intelligence per compute

For every additional action `a`, estimate:

```
MIC(a) =
  P(verified success after a)
  - P(verified success before a)
  --------------------------------
  incremental device cost
```

Compare:

```
another 4B sample
another 4B specialist
one 9B call
one verifier
one retrieval/tool action
```

The optimal Meridian policy selects the action with the highest positive MIC.

This makes the 4B-vs-9B decision just one instance of a general computation market.

## First empirical milestone

Before training a full specialist fleet, run a matched development pilot with:

```
Qwen3.5-4B raw
Qwen3.5-4B + Meridian-lite

Qwen3.5-9B raw
Qwen3.5-9B + Meridian-lite

4B + 9B escalation
```

Meridian-lite should include only:

- compact evidence shaping;
- external task state;
- narrowed tool surface;
- deterministic verification;
- fixed small retry budget.

No elaborate multi-agent system yet.

This gives an early answer to the architecture × scale interaction before we invest heavily.

## Second milestone

After Sentinel/Watchtower adapters exist, repeat:

```
4B general + Meridian
4B specialists + Meridian

9B general + Meridian
9B specialists + Meridian

4B specialist -> 9B escalation
9B planner -> 4B specialist
```

This will show whether specialization lift itself scales with backbone size.

## Third milestone

Add adaptive compute allocation and learn:

```
when to:
- stay 4B;
- spend another 4B call;
- diversify specialists;
- ask 9B;
- stop.
```

This becomes the first real Meridian compute market.

## What would falsify the hierarchy thesis

The mixed-scale hierarchy should be rejected if:

- 9B + Meridian dominates all 4B configurations at similar real cost;
- 4B workers introduce context/coordination overhead larger than their savings;
- model-switch latency dominates;
- 4B outputs are too unreliable for a stronger planner to use;
- deterministic decomposition does not create stable bounded tasks;
- cross-scale routing errors erase the gains.

Conversely, a pure 4B system should be rejected as the primary target if:

- the 4B repeatedly fails to use high-quality evidence that the 9B uses correctly;
- 9B inference is cheaper than repeated 4B search for the same success;
- 4B verification/calibration remains too weak;
- specialist adapters fail to close those residual gaps.

## Current research judgment

The original "4B capability recovery" question remains valuable, but it is now a **sub-question**.

The broader Meridian research program should ask:

> What combination of model scale, specialization, architecture, external cognition, verification, and test-time compute yields the highest verified operational capability under a given hardware/time budget?

That is the actual optimization target.

Current prior:

- 4B + Meridian: likely strongest on capability/parameter and edge deployability;
- 9B + Meridian: likely strongest general local tier;
- hybrid 4B/9B Meridian: likely strongest cost-adjusted architecture;
- larger local + Meridian: important control and rare escalation tier.

These are hypotheses, not findings.

## Sources

- Żywot et al., Can Small Agent Collaboration Beat a Single Big LLM? (2026): https://arxiv.org/abs/2601.11327
- Microsoft Fara1.5 (2026): https://www.microsoft.com/en-us/research/articles/fara1-5-computer-use-agent/
- Fara-1.5: Scalable Learning Environments for Computer Use Agents (2026): https://www.microsoft.com/en-us/research/publication/fara-1-5-scalable-learning-environments-for-computer-use-agents/
- Qwen3.5-4B model card: https://huggingface.co/Qwen/Qwen3.5-4B
- Qwen3.5-9B model card: https://huggingface.co/Qwen/Qwen3.5-9B
- Can Small Language Models Use What They Retrieve? (2026): https://arxiv.org/abs/2603.11513
- Variation in Verification, ICLR 2026: https://proceedings.iclr.cc/paper_files/paper/2026/hash/ea21628f0fc0de542373be4c88343478-Abstract-Conference.html
- Terminus-4B (Microsoft Research, 2026): https://www.microsoft.com/en-us/research/publication/terminus-4b-can-a-smaller-model-replace-frontier-llms-at-agentic-execution-tasks/
- UniScale, ICML 2026: https://proceedings.mlr.press/v306/huang26bd.html
- Not All Bits Are Equal, ICLR 2026: https://proceedings.iclr.cc/paper_files/paper/2026/hash/71f003060ce1e8b6b4856023b67cda5d-Abstract-Conference.html
- AgentArch, AACL-IJCNLP 2026: https://aclanthology.org/2026.aacl-long.44/
- Google Research, Towards a science of scaling agent systems (2026): https://www.research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/
- Can Edge LLMs Team Up? A Fine-Grained Diagnosis of Multi-Agent Tool Calling (2026): https://www.mdpi.com/2079-9292/15/21/5119
