# Meridian Research 03 — Test-Time Compute: Trading Time for Capability

Status: research design note, 2026-11-26.  
Checkpoint: MERIDIAN-03.1.  
Scope: additive research only. This does not alter frozen W2 evaluation, training, reserve, promotion, or runtime policy.

## Executive conclusion

Meridian should not treat "4B" as a permanent model-size target.

The correct research target is a **compute ladder**:

```
deterministic software
    ↓
4B specialist, one pass
    ↓
4B specialist + verification
    ↓
4B specialist + alternate specialist / second sample
    ↓
4B multi-candidate search
    ↓
9B escalation
    ↓
larger local / frontier escalation only when justified
```

The system should learn when each additional unit of compute is worth spending.

The key question is therefore not:

> Is 4B better than 9B?

It is:

> For this task state and this available evidence, what is the cheapest next computation that maximizes expected verified success?

This is Track 3's central thesis.

## Why 4B remains important

4B is useful because it creates the strongest architectural stress test.

If a capability can be recovered at 4B, then the result is likely attributable to architecture, specialization, tools, memory, verification, or test-time search rather than simply to adding parameters.

4B also offers operational advantages:

- lower weight memory;
- more room for KV cache and context;
- more endpoint coverage;
- more parallel candidate generation per device;
- faster adapter swapping;
- higher throughput;
- easier local deployment;
- cheaper experimentation;
- more freedom to keep multiple specialist calls within the same wall-time budget.

For rough intuition, 4-bit weights alone scale approximately with parameter count:

```
4B  -> ~2 GB raw weight payload
9B  -> ~4.5 GB raw weight payload
```

Real serving requires additional memory for quantization metadata, runtime buffers, vision components if enabled, and KV cache, so these are not deployment-memory guarantees.

## Why 9B may be better on important task classes

The same Qwen3.5 family shows material but uneven gains from 4B to 9B.

Official model-card results include:

- GPQA Diamond: 76.2 -> 81.7;
- LiveCodeBench v6: 55.8 -> 65.6;
- BFCL-V4: 50.3 -> 66.1;
- HMMT Feb 2025: 74.0 -> 83.2;
- LongBench v2: 50.0 -> 55.2.

Yet some agentic tasks are nearly tied:

- TAU2-Bench: 79.9 for 4B vs 79.1 for 9B;
- DeepPlanning: 17.6 vs 18.0.

This suggests model-size gain is highly task-dependent.

A second important result comes from ICLR 2026's "Not All Bits Are Equal." It finds a scale-dependent memory tradeoff: below an effective threshold around 8-bit 4B, small reasoning models often benefit more from spending memory on additional model capacity than on longer generation. Above that threshold, test-time compute becomes more attractive.

This creates an important Meridian research constraint:

> Do not assume extra samples from a weak 4B are always a better use of memory/compute than one stronger 9B inference.

The correct answer must be measured by task family.

## Recommended model-size architecture

Use model size as another routed resource.

### Tier M0 — deterministic

No generative model if software can answer exactly.

Examples:

- graph traversal;
- schema validation;
- authorization checks;
- compiler/tests;
- exact lookups;
- replay;
- policy evaluation.

### Tier M1 — 4B specialist

Default reasoning worker.

Use for:

- structured evidence interpretation;
- bounded tool planning;
- known workflow decisions;
- domain-specialized hypothesis generation.

### Tier M2 — 4B deliberation

Spend additional 4B compute when:

- candidate diversity has demonstrated value;
- verification is cheap;
- evidence is sufficient;
- the failure mode is search rather than missing capability.

### Tier M3 — 9B specialist/generalist

Escalate when:

- 4B historical solvability is low;
- the task requires harder code synthesis;
- the 4B verifier is poorly calibrated;
- multiple 4B specialists converge on uncertainty;
- task novelty is high;
- the oracle model-size study says 9B dominates 4B search in this region.

### Tier M4 — large local / frontier reference

Reserve for:

- research;
- teacher generation;
- high-value unresolved tasks;
- open-ended synthesis where smaller tiers hit a measured ceiling.

The operating objective is not to avoid larger models.

It is to make larger-model use **earned by evidence**.

## Track-3 central hypothesis

The best test-time scaling policy for Haven will be heterogeneous.

For some tasks:

```
4B × 1
```

will be optimal.

For others:

```
4B × 3 + deterministic verifier
```

will beat:

```
9B × 1
```

at lower cost.

For others still:

```
9B × 1
```

will dominate any practical amount of 4B resampling.

And some tasks will be best solved by:

```
4B specialist A
+ 4B specialist B
+ exact verifier
```

because the gain comes from diversity rather than raw scale.

Meridian must learn this allocation policy empirically.

## Why naive best-of-N is insufficient

Inference scaling looks simple:

1. generate N answers;
2. score them;
3. choose the best.

But this is only useful if:

- at least one candidate is correct;
- the verifier can identify it;
- additional samples are sufficiently diverse;
- false positives do not increase faster than true solutions.

Three current results make this especially important.

### SPLIT

Microsoft's SPLIT work models the full allocation problem:

- how many candidates to sample;
- which models to sample from;
- how much verification to spend.

Across seven benchmarks, 26 models, 175 agent systems and six verifier types, SPLIT is reported within 0.02–0.8 points of the best allocation in hindsight, while every fixed heuristic loses at least 2.5 points somewhere.

The important Meridian lesson is:

> Compute allocation should be learned from a small labelled pilot, not fixed as "always sample four."

### Limits of resampling

ICLR 2026's "The Limits of Inference Scaling Through Resampling" shows a hard problem: if the verifier has false positives, more samples can eventually make performance worse.

The paper reports that optimal sample counts are often below ten because false positives begin to dominate.

This is directly relevant to cyber:

- an incomplete test suite may accept a bad patch;
- a weak security fixture may accept an incomplete remediation;
- an LLM judge may accept a plausible unsupported claim.

Therefore Meridian needs a **verifier-quality estimate** before deciding to spend more sampling compute.

### Blind Spots

Microsoft's terminal-agent study separates:

- solvability;
- verification;
- confidence.

Repeated sampling narrows the SLM/frontier gap in solvability, but a substantial verification gap remains.

This means that even if 4B can generate a correct trajectory eventually, it may not know which trajectory is correct.

Again: external verification is not optional.

## Verification-first scaling

T1 provides the best current conceptual model for Meridian.

Its pattern is:

```
candidate generation
    ↓
tool/exact filtering
    ↓
small-model residual verification
```

In T1, a Llama-3.2 1B under test-time scaling outperforms Llama-3.1 8B on MATH after external tools offload memorization-heavy verification.

The security analogue is straightforward.

### Code

```
candidate patch
 -> compile
 -> tests
 -> static analysis
 -> regression suite
 -> only then model critique
```

### Identity

```
candidate access conclusion
 -> exact graph queries
 -> scope evaluation
 -> authority/freshness rules
 -> only then residual semantic judgment
```

### Network

```
candidate reachability claim
 -> route/topology computation
 -> policy/firewall checks
 -> observed-flow evidence
 -> only then model synthesis
```

### DFIR

```
candidate timeline
 -> timestamp normalization
 -> entity resolution
 -> event consistency
 -> provenance checks
 -> only then model judgment
```

The more correctness we can calculate, the more useful small-model search becomes.

## The compute actions Meridian should choose among

Each additional unit of compute can be spent differently.

### C0 — stop

Submit the current verified result.

### C1 — deepen

Ask the same specialist to continue reasoning with the same evidence.

Use sparingly.

Longer thinking can cause overthinking and diminishing returns.

### C2 — resample

Generate another independent candidate from the same specialist.

Useful when:

- stochastic search matters;
- candidate errors are not perfectly correlated;
- verifier quality is high.

### C3 — diversify specialist

Ask a different specialist or adapter.

Useful when:

- cross-domain ambiguity exists;
- historical error correlation is low.

### C4 — acquire evidence

Spend compute on another bounded tool call or retrieval step.

This may dominate generating more prose when uncertainty is evidence-limited.

### C5 — verify harder

Use an additional deterministic check, simulation, test, replay, or independent evaluator.

Useful when candidate generation is strong but selection is weak.

### C6 — revise from verifier feedback

Return an explicit error class to the original specialist.

The verifier should expose:

- failed invariant;
- missing evidence;
- failing test;
- contradiction;

not hidden gold.

### C7 — escalate model size

Route the bounded task to 9B.

Use when additional 4B search is predicted to have low marginal value.

### C8 — decompose

Split the task into smaller subproblems and route each separately.

Often preferable to one longer chain.

## The compute-state record

Every bounded work item should carry an explicit compute state.

Example:

```json
{
  "work_id": "w-...",
  "spent": {
    "4b_calls": 2,
    "9b_calls": 0,
    "tool_calls": 3,
    "verifier_calls": 2,
    "wall_seconds": 11.4,
    "device_seconds": 18.9
  },
  "remaining": {
    "latency_ms": 30000,
    "device_seconds": 45,
    "tool_calls": 2
  },
  "state": {
    "router_confidence": 0.71,
    "candidate_count": 2,
    "candidate_disagreement": 0.54,
    "verification_state": "one-failed-one-unverified",
    "evidence_completeness": 0.82,
    "novelty": 0.31
  }
}
```

This makes "thinking harder" an auditable resource-allocation decision rather than invisible chain-of-thought expansion.

## Dynamic budget controller

The controller should estimate:

```
Expected Utility(action | state)
=
  expected improvement in verified success
  - latency cost
  - device cost
  - tool cost
  - safety/risk cost
```

Choose the action with the highest positive expected marginal utility.

If all remaining actions have negative expected utility, stop or escalate.

## Training the compute controller

Do not begin with RL.

Start with offline oracle allocation.

### Step 1 — collect a compute grid

For each development task, run bounded alternatives such as:

```
4B × 1
4B × 2
4B × 4
4B specialist A + specialist B
4B × 2 + deterministic verifier
4B + extra evidence
4B + revision
9B × 1
9B × 1 + verifier
```

Store verified outcomes and costs.

### Step 2 — derive oracle action

For a specified budget/utility function, calculate which action should have been selected at each decision point.

### Step 3 — train a cheap controller

Inputs:

- task/evidence features;
- specialist history;
- verifier state;
- confidence/calibration;
- remaining budget.

Output:

- next compute action.

This resembles current constrained compute-allocation work, which reports strong results from learning a lightweight classifier to imitate per-instance oracle allocation.

### Step 4 — online calibration

Track:

- predicted success improvement;
- actual improvement;
- cost;
- routing regret.

Recalibrate without allowing live benchmark labels into training.

## Fast path / slow path

Most tasks should never enter deep search.

### Green path

Conditions:

- evidence complete;
- specialist highly calibrated;
- deterministic verifier passes;
- no contradiction;
- low operational consequence.

Action:

```
4B × 1 -> verify -> stop
```

### Yellow path

Conditions:

- moderate uncertainty;
- incomplete evidence;
- one verifier failure;
- domain overlap.

Action examples:

```
4B specialist
 -> targeted evidence
 -> revise
 -> verify
```

or

```
4B specialist A
 + 4B specialist B
 -> exact verification
```

### Red path

Conditions:

- high novelty;
- repeated 4B failure;
- poor verifier coverage;
- high consequence;
- model-size oracle predicts strong lift.

Action:

```
9B
 -> verification
 -> optional larger escalation
```

This is analogous to a computational triage system.

## 4B versus 9B experiment

This must be a first-class Track-3 study.

### Same-family comparison

Use Qwen3.5-4B and Qwen3.5-9B under matched:

- tool interface;
- evidence contract;
- decoding mode;
- task set;
- verification;
- quantization quality as far as feasible.

### Compare equal wall-time and equal device-time views

Two different fairness regimes matter.

**Equal wall time**

How much capability can the user obtain in 30 seconds?

A 4B may generate several candidates while 9B generates one or two.

**Equal device time**

How much capability is obtained per accelerator-second?

This measures computational efficiency.

### Arms

```
A  4B × 1
B  4B × 2
C  4B × 4
D  4B top-2 specialists
E  4B adaptive compute
F  9B × 1
G  9B adaptive compute
H  4B adaptive with 9B escalation
```

The likely winner is H, not pure 4B or pure 9B.

## Quantization must be part of the experiment

Do not compare:

```
4B at high-quality quantization
vs
9B at destructive low-bit quantization
```

and conclude that 4B is intrinsically better.

Track:

- model;
- quantization;
- effective weight memory;
- KV-cache memory;
- context length;
- generation length;
- accuracy.

The ICLR 2026 scale-dependent quantization result specifically warns that memory allocation interacts with model size and reasoning budget.

## Candidate diversity

Generating four candidates is useful only if their errors differ.

Diversity sources should be compared.

### Same-model stochastic diversity

Cheapest operationally.

Likely highest error correlation.

### Adapter diversity

Same backbone, different specialist adapter.

Potentially useful because specialization changes evidence and hypothesis priors.

### Model-size diversity

4B + 9B.

Useful when model-size errors are complementary.

### Procedure diversity

One candidate is model-generated.

Another uses a deterministic workflow/template.

### Evidence diversity

Different candidates operate over differently selected but valid evidence subsets.

This must be carefully controlled so omission does not masquerade as independence.

## Disagreement as information

Do not majority-vote by default.

Disagreement should change the next action.

Example:

```
Sentinel says YES
Citadel says NO
```

Potential next actions:

- find the disputed predicate;
- identify differing evidence references;
- issue one exact query;
- recompute conclusion.

This is much cheaper and more reliable than asking a third model "who is right?"

## Search trees

Tree search should be reserved for tasks with:

- meaningful intermediate states;
- cheap partial verification;
- recoverable branches;
- nontrivial planning depth.

Good candidates:

- code repair;
- investigation planning;
- constrained remediation;
- multi-hop graph investigation.

Bad candidates:

- simple factual extraction;
- tasks where branch quality cannot be assessed;
- tasks with expensive or irreversible actions.

The node value should be grounded in verified progress, not pure model confidence.

## Sequential reflection

The agent-scaling literature suggests reflection is useful when applied selectively.

Meridian should not run generic "reflect on your answer" loops.

Reflection prompts should be triggered by explicit evidence:

- failed test;
- contradiction;
- missing prerequisite;
- duplicate action;
- unsupported claim.

This gives reflection a concrete error signal.

## Model confidence is not enough

Small models are often overconfident.

Use confidence as one feature, not the stop rule.

A better stopping function combines:

- calibrated historical success;
- evidence completeness;
- verifier result;
- contradiction state;
- specialist agreement;
- novelty;
- task consequence.

## Test-time training as a later research branch

ICLR 2026 reports that for long-context tasks, generating more thinking tokens can show rapidly diminishing returns, while targeted test-time training on the provided context improves Qwen3-4B substantially.

This is potentially relevant for:

- very large incident datasets;
- giant codebases;
- environment-specific documentation.

But it introduces much more state and contamination risk.

Do not add test-time training to the first Meridian prototype.

Keep it as Track 3B after standard compute scaling is measured.

## Distributed-compute implication

Track 3 is the bridge to the endpoint fabric.

If compute actions are explicit and independent:

```
generate candidate A
generate candidate B
run graph query
run static analyzer
run verifier
```

then they can later be scheduled across machines.

The distributed scheduler does not need to shard every neural layer.

It can dispatch independent cognitive jobs.

This is likely much more tolerant of:

- heterogeneous hardware;
- intermittent endpoints;
- ordinary LAN latency;
- endpoint churn.

Track 3 therefore defines the job primitives needed for the future distributed intelligence fabric.

## Track-3 prototype

### P3.1 — compute ledger

Add research-only instrumentation for:

- model calls;
- adapter;
- model size;
- tokens;
- wall time;
- device time;
- tool calls;
- verifier calls;
- outcome.

### P3.2 — fixed compute grid

On development tasks, measure:

- 4B × 1/2/4;
- specialist combinations;
- 9B × 1;
- deterministic verification variants.

### P3.3 — oracle allocation

Determine the best action under:

- low-latency budget;
- low-device-cost budget;
- maximum-accuracy budget.

### P3.4 — learned cheap router

Predict the oracle action from host-visible features.

### P3.5 — online adaptive policy

Permit sequential allocation:

```
4B
 -> verifier
 -> if failed, evidence
 -> if unresolved, alternate specialist
 -> if unresolved, 9B
```

### P3.6 — distributed execution

Only after P3.1–P3.5 are understood, schedule independent compute actions across available endpoints.

## Primary metrics

- verified success;
- success per wall second;
- success per device-hour;
- success per joule where measurable;
- additional-success probability per extra model call;
- verifier false-positive rate;
- verifier false-negative rate;
- candidate error correlation;
- oracle allocation regret;
- learned allocation regret;
- model-size escalation rate;
- 4B-only solve rate;
- 9B salvage rate;
- larger-model salvage rate;
- human intervention rate.

## Capability accounting

Track 3 should allow a decomposition such as:

```
raw 4B                             52%
+ specialist routing              61%
+ evidence shaping                67%
+ deterministic verification      74%
+ adaptive 4B test-time compute   79%
+ 9B escalation                   86%
frontier reference                91%
```

Then report:

- architecture recovered X% of the raw-to-frontier gap;
- test-time compute recovered Y%;
- model-size escalation recovered Z%.

This is far more informative than saying "our agent scored 86%."

## Falsification criteria

The Track-3 thesis should be rejected or narrowed if:

- repeated 4B inference has low candidate diversity;
- verifier false positives increase with sample count;
- 9B × 1 dominates 4B search across most relevant domains;
- dynamic compute routing cannot beat a simple fixed policy;
- routing overhead consumes the savings;
- small models remain unable to use verifier feedback productively;
- system complexity grows faster than capability.

A result that says "use 9B for most hard tasks" is scientifically acceptable.

The goal is not to prove 4B wins.

## Recommended operating hypothesis

For Meridian's likely enterprise-security workload:

```
4B specialists = broad default workforce
9B             = local senior escalation tier
35B/local large = offline teacher / difficult research tier
frontier        = optional external reference/escalation
```

The most interesting system is therefore not a 4B-only swarm.

It is a **heterogeneous cognitive hierarchy** in which small models handle most bounded work and stronger models are invoked precisely where measured marginal value justifies them.

## Next checkpoint

Track 4 should examine the other half of parameter efficiency:

> What knowledge should not live in neural weights at all?

That means externalized semantic knowledge, environment state, episodic/procedural memory, evidence compilation, contradiction tracking, and context compression.

This is where Meridian can potentially make a 4B or 9B behave as though it has access to an enormous domain-specific "effective memory" without requiring those facts to be carried parametrically.

## Research sources

- Qwen3.5-4B model card: https://huggingface.co/Qwen/Qwen3.5-4B
- Qwen3.5-9B model card: https://huggingface.co/Qwen/Qwen3.5-9B
- Not All Bits Are Equal: Scale-Dependent Memory Optimization Strategies for Reasoning Models, ICLR 2026: https://proceedings.iclr.cc/paper_files/paper/2026/hash/71f003060ce1e8b6b4856023b67cda5d-Abstract-Conference.html
- T1: Tool-integrated Verification for Test-time Compute Scaling in Small Language Models, ICLR 2026: https://proceedings.iclr.cc/paper_files/paper/2026/hash/776a5f2c7d6dd4b0d83145fc044e2726-Abstract-Conference.html
- Sample, Mix, or Verify? Allocating Test-Time Compute under Imperfect Verifiers, Microsoft Research 2026: https://www.microsoft.com/en-us/research/publication/sample-mix-or-verify-allocating-test-time-compute-under-imperfect-verifiers/
- Blind Spots: Where Small Language Models Fall Behind Frontier Models on Terminal Tasks, Microsoft Research / NeurIPS 2026: https://www.microsoft.com/en-us/research/publication/blind-spots-where-small-language-models-fall-behind-frontier-models-on-terminal-tasks/
- The Limits of Inference Scaling Through Resampling, ICLR 2026: https://proceedings.iclr.cc/paper_files/paper/2026/hash/95591b7557edea46ae1d90b0e9e825c5-Abstract-Conference.html
- Variation in Verification, ICLR 2026: https://proceedings.iclr.cc/paper_files/paper/2026/hash/ea21628f0fc0de542373be4c88343478-Abstract-Conference.html
- Inference Scaling Laws, ICLR 2025: https://proceedings.iclr.cc/paper_files/paper/2025/hash/8c3caae2f725c8e2a55ecd600563d172-Abstract-Conference.html
- Pushing Test-Time Scaling Limits of Deep Search with Asymmetric Verification, ICLR 2026: https://proceedings.iclr.cc/paper_files/paper/2026/hash/bc26087d3f82e62044fc77752e86737e-Abstract-Conference.html
- Adaptive Test-Time Compute Allocation for Reasoning LLMs via Constrained Policy Optimization, 2026: https://arxiv.org/abs/2604.14853
- UniScale: Adaptive Unified Inference Scaling via Online Joint Optimization of Model Routing and Test-Time Scaling, ICML 2026: https://proceedings.mlr.press/v306/huang26bd.html
- Scaling Test-time Compute for LLM Agents, 2025: https://arxiv.org/abs/2506.12928
- Let's (not) just put things in Context: Test-time Training for Long-context LLMs, ICLR 2026: https://proceedings.iclr.cc/paper_files/paper/2026/hash/b619cd6dcc986856b8a8da2b08d89396-Abstract-Conference.html
