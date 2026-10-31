# Architecture research: fast specialist models, routing, and long-term memory

**Date:** 2026-10-31  
**Status:** RESEARCH PROPOSAL — NOT ACCEPTED, TRAINED, DEPLOYED, OR PROMOTED  
**Repository base inspected:** main at 53387e74a0ad90786ac3ea16753c8ad99142e9df  
**Implementation authority:** None. This note does not authorize model spending, training, host changes, auto-merging, or deployment.  
**Scope:** Extends Haven's architecture/morphogenesis research without superseding historical requirements, approved decisions, or the separate Model Lab and existing Engineer executor.

## Executive decision

**Primary hypothesis:** A fast local model, a bounded tool executor, source-grounded episodic memory, verified procedural skills, and selective fallback to a stronger model can outperform a larger always-on general model on *verified real tasks per joule* and *per wall second*. This is an empirical hypothesis, not a capability already observed.

**Recommended architecture to test first:**
1. Retain the existing Haven Engineer executor, sandbox, signed receipts, Model Lab, GPU lease, and private federation.
2. Start with one already-qualified Qwen3.5-4B resident on Slink, not a new cluster of continuously loaded models. A 0.8B/2B model is a candidate for a cheap classifier and narrowly trained worker, not an assumed replacement for 4B.
3. Add deterministic eligibility-and-evidence routing. A learned router is *conditional on collecting outcome labels*, not a prerequisite.
4. Compare verified skills, time-indexed memory, and optionally one domain-specific LoRA adapter before training multiple stand-alone models. Same-base adapters avoid duplicating full base weights.
5. Escalate difficult or uncertain work to a qualified stronger existing model or an explicitly owner-permitted provider; no unapproved metered fallback.
6. Only after a genuine memory problem remains should we study neural memory such as Titans, Hope/Nested Learning, or Mamba-3 on *small controlled models*. None is a drop-in modification to Qwythos GGUF.

**Three non-equivalent meanings of “experts”:**
- **Task router over separate models:** one request selects an entire independent model; easy to isolate, but multiple loaded checkpoints cost memory, and switching costs latency.
- **Single-base adapter experts:** one base model plus multiple LoRA modules; may be activated per request or per token in a custom runtime. A collection of LoRAs is not by itself a learned MoE.
- **Sparse neural MoE:** top-k experts are embedded and jointly trained *inside* the model. Fewer active parameters per token does not eliminate the need to store or move total expert weights. It cannot be retrofitted into a dense model without architecture and training work.
- **Verified executable skills:** not model weights at all; reusable programs executed behind the policy boundary, potentially offering the largest gain for deterministic tasks.

## Ground truth: what Haven already has

The current repository contains more than an inference dashboard.

- **Haven Engineer:** labs/engineer/{loop.py,executor.py,runtime.py,mcp_server.py,skills.py,sandbox.py,session.py,scheduler.py}. OpenAI-compatible tool calls, OS-sandboxed tool execution, owner approvals, signed receipts, bounded child delegation, persistent task sessions, and admitted skills. Its 2026-10-27 acceptance record reports a real 4B model edit/test/commit, not just simulations: [ACCEPTANCE_20261027.md](../ACCEPTANCE_20261027.md).
- **Morphogenesis/VEI:** verified executable inheritance has real held-out skill-admission machinery. Its preregistered E2 rerun **did not show a supported success-rate advantage** (model near ceiling); E5's controller versus no-controller arm was **12/18 versus 3/18** on its targeted tasks (the recovery add-on was inconclusive). These are not universal results. See [morphogenesis/README.md](../morphogenesis/README.md).
- **Existing router pilot:** [router_lab/README.md](../router_lab/README.md) trained a small PyTorch classifier on 36 title-only PR proxy labels. Chronological holdout: learned **6/8**, deterministic rules **7/8**. It has not established outcome-aware routing. **Do not promote it.**
- **Existing tool SFT:** [START_HERE.md](../../../START_HERE.md) records 0.6B student changing **14/110 to 38/110** on a fixed held-out tool task set; an oracle scripted control also scored **38/110**, while the untrained 4B scored **76/110** and Strata teacher **55/110**. The apparent distilled gain does not prove unique teacher value; reward and grader design matter.
- **Runtime/provider constraints:** [gateway.py](../../model-lab/gateway.py) and [providers.py](../../model-lab/providers.py) retain consent, authentication and cost boundaries; [FEDERATION.md](../../../ops/haven-core/FEDERATION.md) documents a limited owner-approved worker route and actual limitations.
- **HIVE:** PRs [#100](https://github.com/erpzz/haven/pull/100), [#101](https://github.com/erpzz/haven/pull/101), and [#102](https://github.com/erpzz/haven/pull/102) are *draft, unmerged CPU pilots*, not current deployed WAN sharding or actual Qwythos distributed inference. Do not build requirements on them as if merged.

All measured results are narrow, with dated receipts. Existing static tests are not evidence of real-model inference.

## Candidate architectures: comparison and recommendation

| Option | Weight/VRAM economy | Inference latency | New training | Ability to persist skills | Position |
|---|---|---|---|---|---|
| A. Single resident 4B + fixed tools | Good | Lowest startup overhead | None | Verified programs | **Control / production-safe baseline** |
| B. Same 4B + structured memory/VEI | Good; memory outside weights | Retrieval overhead | None | Strong | **First research target** |
| C. 0.8B/2B router + same 4B worker | Router adds RAM/compute | May add overhead | Not until labels exist | Via executor | **Compare to zero-model rules** |
| D. Same shared 2B/4B base + 2–3 LoRA specialties | Usually better than separate full bases | Adapter switching cost; runtime-dependent | PEFT/SFT | Skills remain external | **Training research target** |
| E. Several unrelated specialist GGUFs | Duplicated checkpoint storage; load/evict contention | Cold swaps may dominate | Separate fine-tunes | Via executor | **Defer until throughput justifies** |
| F. Large MoE resident + task router | Total expert weights may be huge | Good when supported + resident, poor cold/CPU expert loads | Usually only model adaptation | Via executor | **Fallback/teacher candidate** |
| G. Token-level Mixture-of-LoRA | Shared base + adapter memory | Requires compatible kernels/router | Adapter/router learning | Via executor | **Research after D** |
| H. Neural test-time memory (Titans/Hope/Mamba) | Depends on state/architecture | Hardware/kernels matter | New model or major adaptation | Not automatically procedural | **Longer-horizon research** |
| I. Internet tensor/layer sharding | Shares memory across hosts | Often WAN-bound | Not necessarily | Separate problem | **Not the first efficiency move for 2B–9B** |

**Why prioritize B and D:** Training a new specialist is a much higher investment than giving an existing model a reliable tool, reusable procedure or correct memory. Use parameter updates only where inference-time scaffolding fails on *repeated, measurable* cases.

**Important constraint:** LoRA adapters must target compatible tensor names and the *same exact base model revision*. Do not expect independently trained adapters from different architecture families to share one resident model. GGUF serving, PEFT training, and Qwen3.5 hybrid/Gated-DeltaNet runtime support must be independently verified.

### What the literature actually supports — and does not

- **RouteLLM (ICLR 2025)** learns cost/quality routing from preferences for stronger vs weaker models. Claims >2x cost reduction on its benchmarks; not a guarantee for Haven's verifier-heavy tasks. https://proceedings.iclr.cc/paper_files/paper/2025/hash/5503a7c69d48a2f86fc00b3dc09de686-Abstract-Conference.html
- **Switchcraft (Microsoft Research, May 2026)** focuses specifically on *tool calling*: a light classifier in front of candidate models. Reports 82.9% benchmark accuracy with 84% cost savings; benchmarks differ from Haven's exact tool contracts and hardware. https://www.microsoft.com/en-us/research/publication/switchcraft-ai-model-router-for-agentic-tool-calling/
- **Rethinking Scale (ACL Industry 2026)** finds tool-equipped *single* small agents often provide better cost/performance balance than orchestrated multi-small-model swarms because of communication overhead. This argues against reflexively adding many agents. https://aclanthology.org/2026.acl-industry.123/
- **LatentGate (ACL Industry 2026)** shows a frozen SLM + linear probe for fast routing among many agents; its OOD accuracy is lower than in-domain, reinforcing need to abstain. https://aclanthology.org/2026.acl-industry.153/
- **Scaling Small Agents Through Strategy Auctions (ICML 2026)** offers an alternative to training a router: specialists bid plans, with cost/value arbitration. Claims decreased large-model reliance in its tests but incurs agent calls and coordination; test against a rules baseline. https://proceedings.mlr.press/v306/alazraki26a.html
- **S-LoRA (MLSys 2024)** serves many same-base LoRA adapters via efficient memory management, demonstrating that multiple specializations do not require multiple full checkpoints. Its scale/throughput results are from their infrastructure, not Slink's GPU. https://proceedings.mlsys.org/paper_files/paper/2024/hash/906419cd502575b617cc489a1a696a67-Abstract-Conference.html
- **MoLoRA (ICML 2026)** proposes per-token adapter selection; reports a Qwen3-1.7B arrangement beating Qwen3-8B on four selected reasoning benchmarks. Interesting *specific* finding, not proof a tiny model universally beats a large one. https://proceedings.mlr.press/v306/shah26d.html
- **LoRA-Mixer (ICLR 2026)** routes attention-projection adapters and studies plug-in pre-trained adapter combinations; useful as a *research design*, not a supported llama.cpp feature promise. https://proceedings.iclr.cc/paper_files/paper/2026/hash/18610cbcd1da57854aa05ebdc5cd3168-Abstract-Conference.html
- **LD-MoLE (ICLR 2026)** learns token- and layer-specific adapter activation; investigate only after simple adapter switching is qualified. https://proceedings.iclr.cc/paper_files/paper/2026/hash/6a39cf3b666f8bdb2223f253981f3869-Abstract-Conference.html
- **LoRAUTER (2026 preprint)** conditions adapter routing on task representations, but independently reproduce before using its claims. https://arxiv.org/abs/2601.21795
- **Serving support exists upstream:** llama.cpp has GET/POST /lora-adapters and per-request adapter configuration; Hugging Face PEFT supports multiple adapters per shared base; SGLang supports multi-LoRA GPU serving. Check actual release and architecture compatibility first. https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md ; https://huggingface.co/docs/peft/main/en/developer_guides/troubleshooting ; https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/lora.mdx

## Memory architecture, in ascending cost order

**Memory here has three genuinely different levels:**

1. **External agent memory**: events/facts/relationships and retrieval, stored independently of model weights; supports deletion, timestamps, citations, and conflict tracking. Can improve *long-horizon work* immediately.
2. **Procedural memory**: versioned skills/programs that the executor can call, with independent test admission. Haven already has this and should build on its receipts rather than reinvent it.
3. **Neural/recurrent memory**: state inside a sequence model, possibly updated at inference time or across training. It can improve token/context efficiency, but it is neither a trusted fact database nor an executable skill.

**Proposed first memory design: evidence-grounded temporal memory.** A private, append-only event record links: task ID, observed outcome, evidence receipt and source hash, host/runtime/model ID, timestamps, trust status, and supersession references. Derived facts must carry a provenance pointer and be retractable/superseded without deleting historical evidence. A skill proposal may use repeated, successful receipts as training data, but gets promoted only through existing independent skill-admission tests. Store raw private transcripts, host details and embeddings outside the public repo.

Retrieval should return **answerable / conflicting / insufficient evidence** with source and time. A successful command receipt is not proof that the entire task was correct; preserve independent test results. Human preference isn't an OS security grant.

**Memory benchmark options:** [LongMemEval, ICLR 2025](https://mlanthology.org/iclr/2025/wu2025iclr-longmemeval/) covers extraction, multi-session reasoning, temporal updates and abstention; [MemoryAgentBench, ICLR 2026](https://mlanthology.org/iclr/2026/hu2026iclr-evaluating/) adds test-time learning and selective forgetting; [AMA-Bench, ICML 2026](https://proceedings.mlr.press/v306/zhao26bs.html) emphasizes actual state/action/tool trajectories, a closer match to Haven's receipts. Prefer a smaller *Haven-specific* test with stale, contradictory, and falsified receipts in addition to these benchmarks.

**Neural memory shortlist:**

| Architecture | Idea | Why it matters | Near-term action |
|---|---|---|---|
| Qwen3.5 hybrid Gated DeltaNet | Hybrid recurrent linear state + attention | Already in local model family; efficiency baseline | Observe existing runtime; do not reimplement |
| Titans (NeurIPS 2025) | Learned memory updates at test time alongside attention | Capacity/forgetting tradeoffs | Read and reproduce tiny reference |
| MIRAS/Nested Learning/Hope (Google Research 2025) | Multiple update rates and nested learning | Continual learning/memory-update hypothesis | After evidence-grounded memory controls |
| Mamba-3 (ICLR 2026) | Improved recurrent state-space dynamics | Token-efficient inference, state tracking | Compare tiny trained reference with matched compute |

Sources: https://research.google/pubs/titans-learning-to-memorize-at-test-time/ ; https://research.google/blog/introducing-nested-learning-a-new-ml-paradigm-for-continual-learning/ ; https://proceedings.iclr.cc/paper_files/paper/2026/hash/8abd2043b71a074278d5f687947bff9c-Abstract-Conference.html ; https://qwen.moe/

**Do not claim:** memory read/write is "understanding"; self-updating weights avoid all forgetting; Titans/Hope are compatible GGUF LoRAs; larger theoretical context implies usable retrieved evidence; a neural state can replace mutable auditable memory.

## Training strategy: a staged ladder

1. **No training:** tools, constrained schemas, verified executable skills, simple routing, targeted retrieval.
2. **Small model SFT:** use 0.8B/2B or existing 0.6B; train on *verified* function-call trajectories, not self-claimed success. Match tool schemas and include errors/refusals.
3. **LoRA/QLoRA specialists:** keep same base revision; separately train *narrow* domains where the default model actually fails (e.g. tool schemas, structured debugging, safe source-based security patch plans). Compare no adapter, one adapter, and simple multi-adapter routing.
4. **Preference/post-training methods:** DPO for carefully annotated choices; verifier-reward optimization only if rewards are independent, robust to hacking, and pass strict heldout and exploitation tests. **Do not start GRPO/RLVR merely because GPU hours exist.**
5. **Test-time neural memory / custom architecture:** only if external memory and skills fail reproducibly on a well-isolated task family and a matched small reference model beats controls.

Reuse **TRL SFT/DPO/GRPO + PEFT/QLoRA + existing Haven verifier/training pipeline**; do not build a custom trainer. Hugging Face: https://huggingface.co/docs/trl/peft_integration and https://github.com/huggingface/trl . PEFT savings do not imply the training fits in 8 GB VRAM; measure batch, sequence, optimizer, checkpoint activations and reserved VRAM on actual hardware.

**Data admission requirements:** license at the affected source file/package (not just repository root), provenance, exact source revision, contamination review, deduplication, repository and temporal heldout isolation, signed verifier version, disjoint teacher/student evaluation, private host or account data excluded. The existing secpatch license gate proves that root-license shortcuts are unsafe.

## A router designed for real outcomes, not convincing model guesses

**Eligibility first (deterministic):** principal/permission, task family, sensitivity and allowed egress, whether weights and context fit, required tool support, measured readiness, GPU lease, provider-enforced cost ceiling, no interfering experiment. A proposed route can never expand permissions.

**Decision second:**
- Default to a cheap ready model with an admitted skill/tool on bounded tasks.
- Preserve an "unknown" classification with abstention rather than fabricate confidence.
- Evaluate the route using end-to-end *verified task completion*, not next-token accuracy or model self-rating. A single failed tool call can make an apparently cheap model expensive.
- Escalate to a prequalified stronger model when the cheap candidate fails a verifier, exceeds its attempt budget, or the task is high complexity. Require explicit authorization before cloud egress or spending.
- Store every proposed and selected route with evidence, without private prompts in Git.

**Possible score (research only):** minimize predicted total wall time and measured energy per *successful* task, subject to a hard success/safety threshold, p95 latency and a literal spend ceiling. Candidate data should include startup/eviction cost, context prefill, model tokens, tool latency, retries, verification, and provider egress. Never optimize token/s without end-to-end task success.

**Router learning order:** zero-model heuristic -> low-cost classifier/probe -> calibrated abstaining classifier (outcome labels only) -> contextual bandit with offline replay and a fixed exploration budget. A policy that cannot beat rules on an isolated chronological test is not accepted. No autonomous online exploration on privileged tool actions.

## Hardware and network reality

Slink's RTX 2070 Super has 8 GB VRAM and 64 GB host RAM; its actual free VRAM is mutable. Mac memory is shared with the OS; never assume all unified memory is free. Multiple separately hosted specialist 4B models might force paging/load churn. A shared base with small adapters *could* retain model residency; qualify actual resident VRAM and switching latency. Do not simultaneously stop or unload a live Model Lab/Strata or another owner's GPU holder.

Separate throughput tasks (batch verification/training) from latency-critical token-by-token generation. Remote volunteer nodes may be excellent for independent jobs and poor for WAN layer-by-layer 2B–9B inference. Research goal is *performance-aware decisions*, not blanket "no degradation" across unpredictable networks.

Energy measurement must separate measured power and uncertain/estimated energy. NVML availability, GPU board versus system power, CPU package/whole-host watts, idle subtraction and clock/power caps affect comparisons. Missing power data is UNKNOWN, not zero. Hardware adaptations must remain read-only until a narrow policy-granted, reversible control is explicitly approved.

## Specific non-goals and research stop rules

- Do not rebuild OpenClaw/Hermes/goose orchestration, vector stores, custom inference kernels or GPU marketplaces without a measured feature gap.
- Do not relabel dense Qwythos as an MoE; request-level specialist routing and LoRA routing are different mechanisms.
- Do not claim a model trained on test data can generalize; isolate tasks by repo/version/date and hide evaluation specifics from the learner.
- Do not train another router from 36 title-only labels while deterministic rules already outperform it.
- Reject adapters if their apparent domain gain disappears on isolated repos, worsens out-of-domain refusal/accuracy, or costs more than a proven external skill.
- Reject external memory if it increases false recall, exposes private data, or fails to improve verified end-to-end task success.
- Reject new neural memory if a simpler retrieval+skill system matches it at lower measured cost.

## Proposed finite decision sequence

**Gate A — baseline:** freeze one honest real-task set, confirm current Slink/4B and existing Engineer tool loop, record end-to-end latency/accuracy/VRAM/energy where available. No new model or deployment.

**Gate B — memory/skill effect:** compare tool-only vs +admitted skill vs +temporal episodic memory and their combination, matched model and context budget. Promote nothing until independently verified.

**Gate C — narrow training:** choose one task family where the base fails; train a 0.8B/2B SFT model or same-base LoRA on permissible verified traces. Compare against *the exact same model* with only a skill and a retrieved memory.

**Gate D — routing:** compare heuristic, trained classifier, and oracle upper bound using identical available models/skills. Include cold starts, misroutes, abstentions and correction overhead.

**Gate E — neuro-memory architecture:** only if memory failure remains, reproduce a tiny recurrent neural-memory comparison with fixed parameter, sequence, data and compute budgets. Hold out temporal-change/forgetting tasks; report whether update helps and whether it catastrophically forgets earlier ones.

Detailed experimental requirements, arm definitions, metrics, and stop criteria are in [SPECIALIST_ROUTING_EXPERIMENT_PROTOCOL_20261031.md](SPECIALIST_ROUTING_EXPERIMENT_PROTOCOL_20261031.md).

## Evidence inventory and handback

- **Observed in Haven:** 4B tool cycle, private-executor/scheduler acceptance, documented model evals and morphogenesis results, router pilot measured worse than rules.
- **Published external evidence:** links above; not verified on Haven hardware.
- **Designed, not run:** new multi-LoRA/episodic memory router, supervised specialists, learned routing, new neural memory modules.
- **Current change:** document-only proposal; no binaries, user files, keys, host state, cloud spend, or model weights affected.
- **Unresolved decisions:** task family, evaluation corpus/provenance license, permission boundaries, GPU lease window, desired first model, minimal quality and energy/latency budget.
- **Next owner decision:** accept/reject the *experiment design*, not promote a model or authorize hardware changes. Default no-cost, no-deployment.

### Source reading dates and caveat

Public sources linked above checked **2026-10-31**. Upstream benchmark wins are scoped to authors' tasks and settings; Haven replication is absent. This research note intentionally avoids copying datasets, source code or private runtime receipts into the public repository.
