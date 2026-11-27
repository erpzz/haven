# Meridian Research 02 — Specialist Brains: A Modular 4B Cyber Capability Fabric

Status: research design note, 2026-11-26.  
Checkpoint: MERIDIAN-02.1.  
Scope: additive research only. This does not alter frozen W2 evaluation, training, reserve, promotion, or runtime policy.

## Executive conclusion

Haven should not initially build eight independent cyber models or one increasingly overloaded "universal cyber 4B."

The highest-value Track-2 architecture is:

```
shared 4B backbone
  + independently trained specialist LoRA adapters
  + host-owned routing
  + shared typed evidence/state substrate
  + deterministic verification first
  + selective top-2 specialist consultation on hard cases
```

The default unit of specialization should be the **bounded decision**, not the whole user session and not individual tokens.

Fine-grained token-level adapter mixtures are promising, but they should be tested only after the simpler architecture establishes an oracle-routing ceiling. This avoids confounding routing gains with adapter-composition complexity.

The current primary research backbone should remain Qwen3.5-4B so the specialist study compounds existing Haven/W1/W2 work rather than resetting it. Alternative 3–4B models belong in later substrate controls, not in the first specialist experiment.

## Why this direction is credible

Recent research gives four unusually strong signals.

1. **Specialization can beat scale.** MoLoRA reports Qwen3-1.7B with routed specialist adapters exceeding Qwen3-8B across four reasoning benchmarks. LoRA-Mixer and LD-MoLE independently report gains from dynamically routed LoRA experts.

2. **A narrow 4B can approach frontier systems when the task is verifiable.** PrivEsc-LLM reports a post-trained 4B reaching 95.8% on held-out Linux privilege-escalation scenarios versus 97.5% for Claude Opus 4.6.

3. **Tool behavior itself is highly trainable at 4B scale.** EffectWorld reports a Qwen3-4B adapter moving in-domain task success from 53% to 99%, held-out task-kind success from 52% to 81%, and unseen-domain success from 74% to 83%, while reducing output tokens.

4. **Small-model verification remains a major weakness.** "Blind Spots" finds repeated sampling narrows but does not eliminate the SLM/frontier solvability gap, while the verification and calibration gaps remain substantial. Haven should therefore not assume that a small critic can reliably choose among small-model candidates.

These findings point toward modular specialist generation plus external verification, rather than naive multi-agent voting.

## Track-2 research hypothesis

For bounded enterprise-security tasks, a shared 4B backbone with specialist adapters can recover more capability per active parameter than:

- one general 4B;
- one monolithic cyber fine-tune;
- or several independent full model copies,

provided that:

- task/evidence routing is mostly host-owned;
- specialist outputs use typed claims and evidence references;
- tool authority stays outside the model;
- and verification uses deterministic evidence whenever possible.

## Meridian specialist population

The initial population should preserve the previously proposed Meridian roles.

### Sentinel — Microsoft identity

Primary domain:

- Active Directory;
- Entra ID;
- authentication;
- authorization;
- Conditional Access;
- identity graph;
- privilege relationships;
- service principals;
- role assignments.

Primary evidence:

- directory graph records;
- BloodHound/Haven graph edges;
- Entra/Azure metadata;
- authentication evidence;
- policy state.

Primary tools:

- graph queries;
- directory lookup;
- policy inspection;
- safe read-only Microsoft APIs.

### Watchtower — detection and SOC reasoning

Primary domain:

- alert triage;
- SIEM evidence;
- event correlation;
- detection logic;
- investigation sequencing.

Primary evidence:

- normalized event/log records;
- detection metadata;
- temporal chains;
- entity relationships.

This is a high-priority specialist because investigation graphs and structured evidence are unusually compatible with small-model reasoning.

### Scalpel — application security

Primary domain:

- source-code vulnerability reasoning;
- static-analysis findings;
- patch hypotheses;
- code-to-finding correlation;
- repair planning.

Execution should remain verifier-driven: compilation, tests, analyzers, and exact diffs should decide whether an artifact is acceptable.

### Atlas — networking

Primary domain:

- topology;
- routes;
- flows;
- DNS;
- service exposure;
- packet/connection reasoning;
- network-change consequences.

Atlas should receive normalized topology/state rather than raw command transcripts whenever possible.

### Citadel — cloud control plane

Primary domain:

- cloud IAM;
- configuration;
- policy relationships;
- resource exposure;
- control-plane evidence.

Initially treat Azure/Entra overlap explicitly rather than pretending the Sentinel/Citadel boundary is obvious. Routing data should determine whether these specialists eventually merge.

### Stratum — host and low-level systems

Primary domain:

- Linux;
- Windows host state where it is not identity-specific;
- processes;
- services;
- filesystem/permissions;
- low-level execution state.

### Archivist — DFIR and historical reconstruction

Primary domain:

- timeline reconstruction;
- provenance;
- evidence preservation;
- artifact correlation;
- uncertainty and contradictions.

Archivist should be optimized for "what happened and what proves it?" rather than action selection.

### Harbinger — adversarial hypothesis generation

Primary domain:

- authorized Red-Factory challenge generation;
- counterexamples;
- failure hypotheses;
- validation plans;
- robustness testing.

Harbinger should initially be trained/evaluated in fixtures, simulations, and authorized lab tasks. It should produce challenge hypotheses and test plans, not hold execution authority.

## Non-specialist cognitive roles

Do not create a separate 4B for every cognitive function.

### Conductor — host-owned router/controller

Conductor should initially be deterministic or a small classifier, not another generative agent.

Inputs may include:

- task family;
- evidence types;
- visible tool classes;
- target environment;
- workflow state;
- prior failure class;
- specialist calibration;
- specialist availability.

Outputs:

- top-1 specialist;
- optional top-2 specialist;
- allowed evidence packet;
- allowed tool subset;
- compute/verification budget.

### Arbiter — verifier role

Arbiter is not allowed to be the sole correctness authority.

Verification priority:

1. exact/deterministic verifier;
2. executable test or replay;
3. evidence/claim consistency checks;
4. independent specialist critic;
5. model judge only for residual ambiguity.

This follows the empirical observation that small models can generate useful candidates while remaining poor at recognizing the correct candidate.

## Why one backbone first

A common backbone has several advantages.

### Capability inheritance

Every specialist inherits improvements from:

- W1/W2 training;
- tool syntax;
- shared instruction behavior;
- evidence formatting;
- state representation;
- general cyber knowledge.

A full-model specialist fleet would duplicate these improvements and make comparison harder.

### Adapter isolation

Each specialist can be trained and promoted independently.

A bad Watchtower update should not require retraining Sentinel.

### Resident-memory efficiency

Serving systems such as vLLM already support multiple LoRA adapters on one shared base model. The practical serving model therefore matches the research abstraction: one loaded backbone, many lightweight specialists.

### Cleaner science

With one frozen base model, the specialist lift is attributable primarily to the adapter and router rather than hidden differences among base models.

## Why not token-level mixtures first

MoLoRA, LoRA-Mixer, LD-MoLE, and hard-routed reasoning-LoRA work make fine-grained mixtures attractive.

But starting there would obscure the first question:

> Does domain specialization itself close meaningful Haven capability gaps?

The first Track-2 study should therefore use sequence/decision-level adapter routing.

Only after the oracle-routing experiment should Haven test:

- top-2 adapter mixtures;
- token-level routing;
- layer-dependent routing;
- adapter switching inside one trajectory.

SLAaaT is particularly relevant to the last case: it reports that an agent allowed to switch LoRA adapters as a tool can compose specialized capabilities while reducing the capability tax associated with one permanently specialized adapter.

## The bounded-decision abstraction

The specialist should not own an entire task.

A Haven task should be decomposed into bounded work items such as:

```json
{
  "work_id": "w-...",
  "goal": "determine whether principal X has effective access to resource Y",
  "domain": "identity",
  "evidence_ids": ["ev-12", "ev-18"],
  "open_questions": ["does inherited scope apply?"],
  "allowed_tools": ["graph_query", "directory_read"],
  "effect_budget": "read-only",
  "required_output": "ClaimBundle"
}
```

The specialist returns structured output:

```json
{
  "claims": [
    {
      "text": "...",
      "evidence_ids": ["ev-12"],
      "confidence": 0.83
    }
  ],
  "open_questions": [],
  "proposed_next_actions": [
    {
      "tool_class": "graph_query",
      "purpose": "...",
      "target": "..."
    }
  ],
  "stop_reason": "evidence-complete"
}
```

The host—not the model—decides whether a proposed action is authorized and dispatchable.

This keeps specialist training focused on reasoning quality rather than on carrying the entire security boundary inside the model.

## Router architecture

The router should be developed in three stages.

### R-S0 — oracle domain routing

Use known development-set family/domain labels.

Purpose: estimate the maximum gain available from specialists without router error.

If specialist adapters do not beat the general 4B under oracle routing, stop. A learned router cannot rescue a non-beneficial specialist decomposition.

### R-S1 — deterministic feature router

Route from host-visible features:

- evidence schema;
- tool classes;
- environment type;
- task template;
- workflow node.

This should handle clear cases with near-zero compute.

### R-S2 — learned uncertainty router

Train a lightweight classifier only on ambiguous cases.

The objective should not merely predict a human-written domain label.

Train the router to minimize **routing regret**:

```
regret(task, chosen expert)
  = verified score of best available expert
  - verified score of chosen expert
```

This makes the router learn which expert actually succeeds, rather than which label sounds semantically appropriate.

## Multi-specialist consultation

Top-1 should be the default.

Invoke a second expert only when:

- router entropy is high;
- task spans domain boundaries;
- evidence types conflict;
- the first specialist reports low confidence;
- verification rejects the first proposal;
- historical data shows correlated failure in that region.

The second expert should not simply vote.

Use disagreement as a diagnostic signal.

Possible outcomes:

- same claim + same evidence -> confidence increases;
- same claim + different evidence -> evidence union, then verify;
- conflicting claim -> route to exact verifier or targeted evidence acquisition;
- both uncertain -> escalate compute or mark unresolved.

## Error diversity matters more than agent count

A fleet of eight adapters trained on the same traces can still make the same mistake eight times.

Measure pairwise error correlation among specialists.

A useful specialist should contribute one of:

- higher domain accuracy;
- a different correct hypothesis distribution;
- a different evidence-selection pattern;
- a different failure mode that an external verifier can distinguish.

If two specialists have high failure correlation and no complementary strengths, merge them or eliminate one.

## Training strategy

### Stage A — shared base competence

Keep general tool syntax, evidence contracts, scope behavior, and interaction protocol in the backbone/common training.

### Stage B — specialist positives

Train each adapter primarily on verified positive traces for its target domain.

EffectWorld's results are a warning against assuming large negative/refusal corpora are helpful: targeted positive behavior carried most of the reported gains, and poorly constructed refusal data could dramatically damage tool-use behavior.

### Stage C — near-boundary examples

Add minimal pairs that teach distinctions specific to the specialist:

- stale/live evidence;
- inherited/direct scope;
- alert correlation vs coincidence;
- code finding vs exploitable condition;
- route existence vs effective reachability.

### Stage D — failure-directed refresh

Feed each specialist examples selected from its own current failure boundary rather than continuously adding generic teacher traces.

The active synthetic-data literature suggests student-state-guided generation can outperform static generation for a fixed teacher budget.

## Preventing specialist collapse

A specialist is useful only if it gains domain competence without destroying shared behavior.

Track a **capability tax** for every adapter:

```
tax = baseline general score - adapted score
```

on unrelated control tasks.

Promotion should require both:

- domain lift >= threshold;
- general capability tax <= threshold.

Possible mitigations if tax is high:

- lower-rank adapter;
- narrower target modules;
- replay of common protocol examples;
- adapter switching instead of permanent specialization;
- explicit common-skill adapter plus domain adapter;
- hard routing rather than soft adapter averaging.

## Verification architecture

Do not train Arbiter first.

Current evidence suggests small-model verification is a harder frontier than candidate generation.

For Track 2:

### Deterministic first

Examples:

- exact graph query;
- schema validator;
- replay;
- compiler/test;
- static analyzer;
- fixture gold;
- authorization/effect checker.

### Evidence consistency second

Check:

- every claim cites admitted evidence;
- cited evidence exists;
- authority/freshness constraints are satisfied;
- no contradicted claim is emitted as verified.

### Independent model verification last

Use a model critic only where correctness cannot be cheaply expressed deterministically.

Model-verifier performance must be measured separately from generator performance.

## Track-2 experiment

### Base population

Use development-only tasks spanning:

- Sentinel;
- Watchtower;
- Scalpel;
- Atlas;
- Citadel;
- Stratum;
- Archivist.

Keep Harbinger as a separate Red-Factory research track initially.

### Arms

```
S0  stock/general Haven 4B
S1  monolithic cyber-adapted 4B
S2  oracle-routed specialist adapters
S3  deterministic-routed specialist adapters
S4  learned top-1 router
S5  learned top-1 + conditional second specialist
S6  best S5 + specialist switching mid-trajectory
S7  experimental token/layer LoRA mixture
```

Do not run S6/S7 unless S2 demonstrates a real specialization ceiling.

### Metrics

Per domain and overall:

- verified task success;
- specialization lift;
- routing regret;
- oracle-router gap;
- capability tax;
- pairwise error correlation;
- disagreement salvage rate;
- unsafe intent;
- unsafe dispatch;
- tool-call efficiency;
- evidence precision/recall;
- active parameters;
- adapter bytes;
- peak resident memory;
- adapter-switch latency;
- wall time;
- device-hours.

### Two important matrices

**Expert-task matrix**

Rows = specialists.  
Columns = task domains.  
Cells = verified score.

This reveals whether the intended decomposition exists empirically.

**Error-correlation matrix**

Rows/columns = specialists.  
Cells = correlation of failure events on matched tasks.

This tells us whether multi-specialist compute creates genuine diversity or merely repeats the same failure.

## Success criteria

Track 2 is promising if:

1. oracle-routed specialists materially outperform the general 4B;
2. the best adapters retain shared protocol/tool behavior;
3. router regret is small relative to the oracle specialist advantage;
4. top-2 consultation recovers failures that top-1 misses;
5. those gains survive held-out task variants rather than only in-domain examples;
6. capability gained per device-hour is competitive with simply running a larger model.

## Falsification criteria

Abandon or narrow the specialist-fleet thesis if:

- most specialists do not beat the shared generalist;
- expert boundaries collapse into one or two broad domains;
- routing error consumes most specialization gains;
- capability tax is severe;
- specialists make highly correlated errors;
- multi-expert consultation costs more compute than a larger model for less success;
- domain adapters overfit benchmark syntax rather than evidence semantics.

Negative results here would be useful: they would tell Haven where architecture cannot substitute for scale.

## Backbone decision

For the first study, retain **Qwen3.5-4B** as the shared research backbone.

Reasons:

- Haven already has active W1/W2 investment around the Qwen 4B line;
- the current Qwen3.5-4B release explicitly supports tool/agent use;
- the model supports long context and local serving;
- changing the base while testing specialists would confound the experiment.

Do not treat this as a permanent model selection.

After Track 2 stabilizes, substrate controls can compare the specialist architecture on another small backbone.

## Practical serving model

A future production-like prototype should prefer:

```
one resident base model
+ signed, versioned adapter registry
+ static/trusted adapter loading
+ request-time adapter selection
```

vLLM already supports multiple LoRA adapters sharing one base model and request-time selection.

Its runtime dynamic-loading API carries an explicit security warning, so Haven should not expose unrestricted dynamic adapter loading in a security-sensitive deployment. Adapter enrollment should instead be host-controlled, allow-listed, signed, and auditable.

## Near-term implementation plan

### Prototype P2.1 — capability registry

Define a versioned record:

```json
{
  "specialist": "sentinel",
  "base_model": "...",
  "adapter_sha256": "...",
  "domains": ["ad", "entra"],
  "evidence_schemas": ["identity_graph_v1"],
  "tool_classes": ["graph_read", "directory_read"],
  "verified_benchmarks": {},
  "capability_tax": {},
  "status": "research"
}
```

### Prototype P2.2 — deterministic router

Map existing Haven work/evidence types to specialist IDs.

No learned router yet.

### Prototype P2.3 — two adapters only

Start with the highest-value vertical slice:

- Sentinel;
- Watchtower.

Do not train the entire proposed fleet before measuring whether the architecture works.

### Prototype P2.4 — oracle specialist experiment

Run matched development tasks with:

- generalist;
- Sentinel;
- Watchtower;
- intentional wrong-specialist controls.

The wrong-specialist arm is important because it quantifies whether the adapter contains real domain specialization or merely generic additional training.

### Prototype P2.5 — conditional consultation

Only after specialist lift is demonstrated, add top-2 consultation and measure disagreement salvage.

## Recommended development order

```
Sentinel
  -> Watchtower
  -> shared capability registry/router
  -> Scalpel
  -> Atlas/Citadel boundary study
  -> Archivist
  -> Stratum
  -> Harbinger research lane
```

Sentinel and Watchtower are first because Haven already has strong identity/evidence infrastructure and because security investigation tasks have structured, verifiable evidence.

Scalpel follows because code work offers excellent executable verification.

## Connection to the larger Meridian thesis

Specialist adapters are not an end state.

They create the first measurable component of the broader capability-recovery system:

```
small shared brain
   + modular expertise
   + host-owned state
   + typed evidence
   + tools
   + deterministic verification
   + selective extra compute
```

If Track 2 works, Track 3 should ask a more interesting question:

> Given a fleet of specialists, how should Haven spend additional inference-time compute so that another 4B call buys the most expected capability?

That is the next research checkpoint.

## Research sources

- MoLoRA — Microsoft Research (2026): https://www.microsoft.com/en-us/research/publication/molora-composable-specialization-via-per-token-adapter-routing/
- LoRA-Mixer — ICLR 2026: https://proceedings.iclr.cc/paper_files/paper/2026/hash/18610cbcd1da57854aa05ebdc5cd3168-Abstract-Conference.html
- LD-MoLE — ICLR 2026: https://proceedings.iclr.cc/paper_files/paper/2026/hash/6a39cf3b666f8bdb2223f253981f3869-Abstract-Conference.html
- Hard-Routed Mixtures of Reasoning LoRAs (2026): https://arxiv.org/abs/2606.31413
- SLAaaT — Switching LoRA Adapters as a Tool (2026): https://arxiv.org/abs/2608.17034
- CyberPal 2.0 / Toward Cybersecurity-Expert Small Language Models — ICML 2026: https://proceedings.mlr.press/v306/levi26a.html
- PrivEsc-LLM / Post-Training Local LLM Agents for Linux Privilege Escalation with Verifiable Rewards (2026): https://arxiv.org/abs/2603.17673
- EffectWorld / Small agents should know what their tools do (2026): https://arxiv.org/abs/2610.35981
- Blind Spots: Where Small Language Models Fall Behind Frontier Models on Terminal Tasks — Microsoft Research / NeurIPS 2026: https://www.microsoft.com/en-us/research/publication/blind-spots-where-small-language-models-fall-behind-frontier-models-on-terminal-tasks/
- Terminus-4B — Microsoft Research (2026): https://www.microsoft.com/en-us/research/publication/terminus-4b-can-a-smaller-model-replace-frontier-llms-at-agentic-execution-tasks/
- EffGen — ICML 2026: https://proceedings.mlr.press/v306/srivastava26a.html
- ExCyTIn-Bench — ICML 2026: https://proceedings.mlr.press/v306/wu26bd.html
- Active Synthetic Data Generation — Microsoft Research (2026): https://www.microsoft.com/en-us/research/publication/towards-active-synthetic-data-generation-for-finetuning-language-models/
- vLLM LoRA serving documentation: https://docs.vllm.ai/en/stable/features/lora/
