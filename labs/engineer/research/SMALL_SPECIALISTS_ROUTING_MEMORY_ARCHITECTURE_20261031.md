# H02/R02 architecture research — small specialists, adaptive routing, and persistent memory

**Status:** research proposal only; no training, deployment, routing promotion, account expenditure, or hardware change.  
**Date:** 2026-10-31. **Repository basis:** Haven main at 53387e74a0ad90786ac3ea16753c8ad99142e9df.  
**Scope:** primarily the architecture and memory discussion, extended to specialist training and hardware-aware placement.  
**Companion protocol:** [SPECIALIST_MEMORY_EXPERIMENT_PROTOCOL_20261031.md](SPECIALIST_MEMORY_EXPERIMENT_PROTOCOL_20261031.md).  
**Evidence convention:** observed Haven results below are taken from existing receipts/documents; published third-party results are *upstream claims* and not independent Haven reproductions. Planned work must not be described as executed.

## Executive decision

Favor a **verified capability cascade**, not an eagerly loaded fleet of unrelated models or a new giant foundation model. Start with one competent local backbone (the currently qualified Qwen3.5-4B), deterministic tool/skill and retrieval specialization, and a gate that escalates only when the task or verification outcome merits it. Add a second resident model, a learned router, or domain LoRA adapters *only when a matched experiment beats the simpler option on verified end-to-end task success, latency, memory residency, and useful work per joule*. Preserve one strong-model fallback and abstention.

This is different from a neural mixture-of-experts (MoE). An **external system router** chooses which model/tool/adapter runs a task; an **internal MoE** activates learned expert sub-networks *inside a trained model* per token. Running several separate models is not automatically MoE, and sparse activation does not imply low peak VRAM, zero cold starts, or low WAN latency.

Immediate priorities, in order:
1. Reproduce and strengthen Haven's existing deterministic routing baseline using actual task outcomes, not PR-title categories.
2. Test executable procedural memory and evidence-grounded episodic retrieval *before* training extra model weights.
3. Compare a small task-specific adapter against its identical unadapted base and retrieval/skill-only controls.
4. Explore memory-controller learning with a narrow, well-labeled task, not a new Titans/Hope model from scratch.
5. Only then attempt joint routing and hardware scheduling or more exotic recurrent neural memory.

## 1. Evidence from Haven: do not restart work already done

Haven already has infrastructure that typical agent-harness comparisons miss:

| Finding | Existing evidence | Implication |
| --- | --- | --- |
| Qwen3.5-4B completed **76/110** held-out verified tool-use episodes; the prepared Strata large teacher completed **55/110** on that set | [START_HERE](../../../START_HERE.md), [distillation](../../intelligence-bakeoff/distillation/tool_sft/RESULTS.md) | Larger model does not guarantee better *particular* tool behavior; beware teacher refusal mismatch and task-specific scorers. Neither figure measures general intelligence. |
| A 0.6B student's tool SFT went **14/110 to 38/110**, but tied the scripted-oracle training arm at 38/110 | same results | Fine-tuning is feasible, but the expensive teacher did not add measured aggregate value over rule-derived trajectories in this experiment. Demand teacher-value controls. |
| Haven Engineer has an actual local model edit/test/commit acceptance, sandboxed executor, MCP interface, child-agent lineage, receipts and approvals | [Engineer README](../README.md), [acceptance](../ACCEPTANCE_20261027.md), [MCP server](../mcp_server.py) | Use that executor and ledger as the common task substrate; reuse external agent harnesses rather than recreating shell permissions and scheduling. |
| Small router trained on **36 PR titles** scored **6/8**, simple rules **7/8**, chronological holdout | [router lab](../router_lab/README.md) | The trained head is *not* promoted. Labels were coarse code-path proxies, not measured model-quality or task-outcome labels. |
| d1-2B zero-shot router scored **7/8** on the same chronological subset; 4.4s median CPU per request, and abstained on its four incorrect answers over 36 titles | [specialist acceptance](../../model-lab/specialists/README.md) | An abstaining non-generative expert is interesting, but its overhead can erase a speed advantage; same tiny/biased test is not independent qualification. |
| Morphogenesis E5 controller improved observed success **3/18 to 12/18** on a controlled task family; E2's exploratory gains failed to replicate as a clear general success effect | [Morphogenesis](../morphogenesis/README.md) | Deterministic verified procedures may outperform adding parameters, but preserve independent reruns and negative results. |
| One GGUF Lab-owned engine at a time; single 8 GiB NVIDIA GPU and 64 GiB host RAM in historical Slink setup | [federation](../../../ops/haven-core/FEDERATION.md), [Linux Lab](../../../ops/haven-core/LINUX_MODEL_LAB.md) | Multi-model residency must be measured. Repeated swapping can dominate token-generation savings. Do not unload an owned engine or evict active research jobs. |
| HIVE PRs #100–#102 are open draft pilots, not integrated in main | [#100](https://github.com/erpzz/haven/pull/100), [#101](https://github.com/erpzz/haven/pull/101), [#102](https://github.com/erpzz/haven/pull/102) | Do not treat synthetic split inference or a simulated performance gate as real Qwythos WAN inference. |

**Evidence debt:** the 36-title route classification and tiny held-out split cannot decide whether a learned policy selects the best actual specialist. Train only after collecting task traces with several candidate routes and independent outcome judgments. Do not optimize the test set or repeatedly re-label it to obtain a win.

## 2. Candidate execution architectures, ranked

### A. One small backbone + verified tools + retrieval (first baseline)

One fast local model handles bounded tasks; code and tests, factual retrieval, policy checks, and remembered procedures are deterministic tools. An abstention gate escalates unclear or failed tasks. This avoids concurrent model residency, adapter compatibility, and extra context transfer. The neural model should *propose* operations; the executor checks permissions and runs them; the verifier judges actual postconditions.

Why first: Haven's E5 controller and skill-inheritance work already suggests useful procedural scaffolding can dominate fancy routing on constrained engineering tasks. It also minimizes architectural novelty, enabling clean measurements.

Failure mode: a model may not choose the right tool, may misuse retrieved evidence, or may require broad reasoning outside its domain. Address with explicit typed dispatch and verification-first escalation rather than simply larger prompts.

### B. Small-fast/strong-slow model cascade (second baseline)

Route low-risk/low-uncertainty tasks to a small model; call a stronger local/remote model when policy, input complexity, uncertainty, or *verified failure* warrants it. FrugalGPT (2023) and RouteLLM (ICLR 2025) show that model cascades and learned routing can improve cost–quality tradeoffs on their benchmarks; Cascadia (ICLR 2026) shows that model placement and routing must be co-optimized under serving constraints. None establish savings on Slink without measured workload distribution and cold-start data. [1][2][3]

Two types of route are different: **predict-before** (cheap rule/classifier estimates best target) and **adaptive** (execute cheap candidate, inspect result, escalate if needed). A hybrid avoids paying for an extra router on every trivial request and allows error recovery. High-risk permission decisions stay deterministic and refuse unsupported actions.

### C. Shared backbone + domain LoRA adapters (preferred *training* experiment)

Train small, independently versioned LoRA adapters for one well-bounded task family (e.g. tool-call serialization or security-patch evidence extraction) while sharing the underlying base weights. This is a *portfolio of policies*, not a set of separately loaded 4B models. S-LoRA and Punica demonstrate multi-adapter efficiency on compatible serving hardware, and current llama.cpp documents request-specific adapter scales; vLLM supports per-request LoRA where architecture compatibility is established. [4][5][6][7]

Important Slink-specific caveats:
- Do **not** assume llama.cpp b11146 in the live Lab implements the current upstream adapter controls or fully supports a proposed Qwen3.5 adapter. Test a pinned engine on an isolated idle worker before touching the Lab.
- A model + two adapters may fit where two full 4B models do not, but adapter RAM, GPU buffers, prompt cache invalidation, and switches still cost time.
- Distinct model architectures cannot generally share a LoRA adapter. Quantized inference GGUF and QLoRA training formats are not interchangeable; conversion and correctness checks are needed.
- Request-level LoRA variants may disrupt batching; current llama.cpp upstream explicitly warns that different LoRA configurations are not batched together. [6]

### D. Separate specialist models, each with its own base (only after evidence)

Use when a domain genuinely benefits from a different architecture (e.g. non-generative decision model, embedder/reranker, compact code model, recurrent 1B specialist). Avoid treating marketing benchmark claims as Haven qualification. Resident RAM/VRAM and model-load latency must be included in routing optimization. A 2B classifier taking 4.4 seconds per CPU call is not necessarily a faster router than a cheap rule.

### E. Token-level routing or globally sharded neural MoE (research only)

R2R (NeurIPS 2025) explores selective token-level use of small and large reasoning models, but this requires aligned generation, a learned token policy, and costly implementation/testing; it is not an external model switch. [8] WAN layer sharding increases per-token communication and is most justified when the model cannot fit otherwise. The HIVE pilots remain correctness research. Reserve full internet-native sparse-MoE or hybrid recurrent memory architecture training for a clear prior failure of simpler systems.

## 3. What the router should decide

The route key must include task family **and** execution conditions, not prompt keywords alone:

- **Eligibility:** model/tool ownership, principal grant, privacy/egress, license/data provenance, allowed hardware, provider hard spend caps, no secretly charged fallback.
- **Fit:** observed VRAM/RAM and context capacity, currently loaded weights/adapter, cold-start, concurrency, GPU lease, expected tool context length.
- **Capability:** per-family verified success probability with confidence intervals; tool compatibility and schema adherence; whether a deterministic skill/validator is available.
- **Outcome:** postcondition pass/fail, evidence validity, unit/integration results, failure category, retries and semantic uncertainty.
- **Latency/energy:** dispatch + retrieval + cold start + prefill + generation + tool latency + verification + retries, p50 and p95 plus joules if calibrated sensors are available.
- **Risk:** severity of a wrong answer or unverified tool action; changes to permissions/host configuration must remain behind owner/policy gates.

Proposed objective for eligible route r and task x:

**Choose argmin_r E[wall time + λ·energy + μ·money + ν·error loss | x,r], subject to privacy, authorization, verified task quality, deadline, memory, and spend limits.**

This is a research objective, not a calibrated production loss function. Never combine heterogeneous quality scores into a fake universal “IQ.” A latency-only router can be confidently wrong, and an accuracy-only router can be too slow to be useful. Measure the full useful task (verified postcondition), not only tokens/sec.

Simplest implementable policy (control arm):
1. Reject unauthorized routes and stale telemetry.
2. Use existing deterministic skill/tool first when exact postconditions apply.
3. Run the ready small model if recent per-task-family evidence satisfies the confidence/risk threshold.
4. Verify the result independently. If it fails, retry using *a different* procedure or a stronger model once within a strict budget.
5. Abstain with an honest failure record when neither route is qualified; never report simulated or model-claimed success.

Use the fixed policy as the primary baseline. Only try supervised route prediction or contextual bandits when there are enough labeled actions and a genuine deployment tradeoff. A learned router's own inference cost belongs in the comparison. Avoid online exploration of destructive actions.

## 4. Training specialists: what to teach and in what order

Train for **verified behaviors**, not “expert personality”:
- Tool selection and argument schema with valid JSON + unauthorized-tool refusal.
- Verifiable bug repair and test triage in sandboxed sample projects.
- Security patch extraction with source commit attribution and independent tests; check nested licenses and repository isolation before training.
- Retrieval-supported “I don't know” with citations, temporal validity, and contradiction detection.
- Structured plans that yield executable steps for approved, resource-bounded jobs.

Recommended curriculum:
1. **Rules/skills-only baseline:** same underlying model, verified tools, no training. Store trace receipts with train/eval origin, task type and exact model+engine hashes.
2. **Supervised fine-tuning of one 0.5–4B student:** imitate *verified* decisions and tool trajectories; preferentially train on hard negatives including failed execution, wrong-tool choice, refusals and stale-source cases. QLoRA permits frozen quantized backbone + small adapter under limited VRAM, but actual fit for each architecture must be measured, not inferred from parameter count. [9]
3. **Ablation against scripted-oracle traces:** the previous 0.6B experiment already showed teacher labels may not beat scripted trajectories. Do not repeat the same blind spot.
4. **Calibrated abstention:** reward/select based on independently verified outcome; prevent false confidence from dominating apparent accuracy. Test false-success rate explicitly.
5. **Optional task-constrained preference or reinforcement tuning:** only if a verifier is resistant to shortcut exploitation and held-out repo/family evaluation supports it. Do not optimize a lexical grader that can be gamed.

NeurIPS 2025 Agent Distillation provides a direct precedent for teaching smaller models *tool-using trajectories*, not simply chain-of-thought text. [10] Whether such an approach wins for Haven remains empirical.

**Specialist admission:** a trained adapter can be registered only with SHA/revision, license and provenance checks, a reproducible held-out comparison, non-regression on unrelated families, measured resident/cold memory, and a rollbackable promotion gate. Never replace the baseline because a single prompt looks impressive.

## 5. Memory: distinguish context, retrieval, procedure, and neural state

“Memory” refers to several non-substitutable mechanisms:

| Mechanism | Persists across sessions? | What it buys | Main risk |
| --- | --- | --- | --- |
| Attention/KV cache | Usually active session; optional persisted cache | Fast reuse of the *same* prompt prefix | Staleness; enormous context; does not train model |
| Recurrent state (Gated DeltaNet, Mamba-family) | Usually sequence scope | Subquadratic context update, potentially efficient long sequences | State drift, information compression, difficult recovery |
| External episodic memory | Yes | Records *what happened* with timestamps and evidence | Privacy, stale or hallucinated summaries |
| Semantic/temporal store | Yes | Queryable relationships and correction/supersession | Entity collision, contradictory facts, retrieval errors |
| Executable procedural memory | Yes | Reusable verified actions and tests without an LLM | Incorrectly promoted skills, environmental drift |
| LoRA/weight updates | Yes | Internalized domain behavior | Forgetting, data contamination, uncontrolled adaptation |
| Learned test-time neural memory | Within model-specific mechanism | Updates internal memory during inference | Stability, compute cost, auditability; cannot retrofit arbitrary GGUF |

Haven's unique raw material is **receipted experience**. Hindsight (ACL 2026) explicitly separates world, experience, observation and opinion networks with retain/recall/reflect; Mem0 (2025/2026) investigates structured and graph memory over long conversations. Their reported benchmarks are not Haven results and depend on their evaluators. [11][12]

Proposed local memory record schema (conceptual, not implemented):
- **identity:** immutable record ID, principal/scope, topic, event time and ingest time, content hash;
- **epistemic type:** owner assertion / model conjecture / tool observation / independently verified outcome;
- **provenance:** source commit, receipt ID, tool and verifier hashes; no publishing private transcript or secret;
- **temporality:** valid-from, valid-until or superseded-by, retrieval-at and expiry policy;
- **confidence:** confidence only in its narrow meaning (source quality, status), not model-generated ground truth;
- **action:** link to an admitted, hash-addressed skill if one exists.

Retrieval must preserve authorship and privacy. A tool result can become evidence of an observation, not authority to change policy. Contradictory records are versioned, not silently rewritten. Memory should cite the raw receipt or source at answer time, with explicit unresolved status.

### Memory experiments before new neural architectures

Hold the model, context budget and task set constant. Compare:
A. no carried memory;  
B. full transcript truncated to equal context;  
C. compact human/deterministic summary;  
D. plain BM25/SQLite FTS retrieval with source links;  
E. structured temporal memory (Hindsight-like or a small typed store);  
F. E plus existing verified executable skills;  
G. optional learned retrieval/writing controller.

Tasks: multi-session bug fixes, previously discovered false test claims, changed/obsolete service settings, conflicting facts, user/agent permission separation, and transfer to a fresh process. Measure correct recall **and correct forgetting**, citation accuracy, false-memory introduction, token cost, latency and independently verified task success. Memory should never become a channel for one principal to access another principal's information.

Long contexts are not automatically reliable memory; “Lost in the Middle” documents position-dependent retrieval failures. [13]

## 6. Neural memory and alternative backbones: research watchlist, not a migration plan

- **Titans/MIRAS (2025):** combines attention with neural long-term memory updated during processing; published long-context language/retrieval gains. Strong architectural inspiration, but building it into Qwythos would entail training and kernel/serving work. [14]
- **Nested Learning / Hope (2025):** treats components as nested optimizers with memory systems updating on different timescales; promising for continual learning but research-stage and distinct from agent memory files or LoRA. [15]
- **Mamba-3 (ICLR 2026):** inference-first state-space improvements to long-range state tracking and memory-efficient decoding; at 1.5B the authors report a +1.8 percentage-point combined improvement over a Gated DeltaNet comparison on their measured suite. These are upstream numbers and not a Haven task result. [16]
- **Hybrid attention/recurrent architecture:** already present in Qwen3.5/Qwythos. Prefer measuring its real tool/context behavior to assuming all-Transformer norms.

**Decision:** Do not pretrain a novel architecture or attach test-time memory to an incompatible pretrained backbone now. If external/procedural memory saturates, train a *small memory admission/retrieval controller* using verified provenance and delayed-recall tasks first. Compare against simple recency, BM25, and temporal-rule controls. If neural memory is still justified, run a sub-billion-parameter architecture ablation on the same tokenizer/data/task budget with paper implementations, not a bespoke production model.

## 7. Shared infrastructure to adopt, not rebuild

- **Haven core:** [executor](../executor.py), [MCP stdio bridge](../mcp_server.py), [runtime](../runtime.py), [fleet scheduler](../scheduler.py), [ledger](../ledger.py), [skills/morphogenesis](../morphogenesis/README.md), [private federation](../../../ops/haven-core/FEDERATION.md), [Model Lab gateway](../../model-lab/gateway.py).
- **Routing reference:** [RouteLLM repository](https://github.com/lm-sys/routellm) for router training/calibration/evaluation. Do not copy its pretrained threshold to Haven's very different task population, and note some published router variants require an external embedding API.
- **Local serving:** [llama.cpp server docs](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) include schema-constrained output, speculative decoding and multiple LoRA controls in current upstream; require pin-specific acceptance before use on Haven's older runtime.
- **Multi-adapter reference:** [vLLM LoRA](https://docs.vllm.ai/en/stable/features/lora/) on eligible GPU hosts. Dynamic LoRA mutation is privileged; upstream warns it is insecure if enabled for untrusted users. [7]
- **Memory reference:** Hindsight / Mem0 evaluated *as external memory clients* behind a private boundary, not as automatically authoritative fact stores.
- **Agent frontends:** Hermes or goose as optional MCP clients. Neither should bypass Haven's policy executor with a second unrestricted shell, nor change its principal boundary.

Do not introduce a new infrastructure dependency until it wins a measured acceptance criterion. Source licenses and deployment requirements must be checked at pinned versions.

## 8. Hardware and efficiency implications

Latency is end-to-end: **router + cache/load + prefill + decode + tools + verifier + retries**. Fast tokens do not imply fast *successful tasks*. Count total model invocations. A second resident model on an 8 GiB GPU may be impossible, and repeated 5–30s model loads may be worse than a single ready 4B.

Hardware-aware placement should start **read-only**, using proven telemetry and existing GPU leases. Later a deterministic owner-controlled resource controller may adjust bounded CPU quotas/affinity or process admission; never let a model self-grant device administration, override thermal protections, write firmware, or terminate independently owned work.

Instrument wall time, p95 latency, resident memory, network traffic, measured energy where supported and calibrated, spend, cold-load frequency, and pass rate. Report **joules per verified successful task**, with an UNKNOWN state when power cannot actually be measured. Do not replace unknown energy with a fabricated zero.

## 9. Decision matrix and stop rules

| Idea | Priority | Gate for continuing | Reason to stop |
| --- | --- | --- | --- |
| Fixed small-model + tool + verifier cascade | P0 | Real task completions and refusal correctness | More false-successes or higher cost than ready 4B |
| Evidence-grounded episodic + procedural memory | P0 | Better cross-session completion/correct recall than simple retrieval | Unsupported claims, stale-memory regressions, principal leaks |
| Same-base domain LoRA | P1 | Gain against same-base prompting, skills and scripted-data controls | No held-out gain, wrong-refusal rate worsens, memory/cold cost dominates |
| Trained router | P1 (after trace data) | Better *outcome* Pareto than rules with uncertainty | Fails to beat rules, distribution shift, uncalibrated errors |
| Multiple separate resident small models | P2 | Measured benefit under real residency | GPU contention and model switching dominate |
| Recurrent/test-time neural memory | P3 | Repeated failure of cheap memory baselines on long sequences | Complexity not justified by useful-task improvements |
| Internet-sharded MoE | P3 | Hardware fit unavailable otherwise; measured full-task win | WAN token-loop latency and unreliable peers dominate |

**Near-term architectural claim is conditional:** if verified tools + memory + one small model + conservative escalation outperform the single-model baseline at matched task quality and lower resource cost, then specialists are useful. Otherwise simplify Haven. The current repository does not yet prove this hypothesis.

## Source ledger (primary/published, checked 2026-10-31)

[1] FrugalGPT (2023), https://arxiv.org/abs/2305.05176 — cascade and cost benchmark, not Haven.  
[2] RouteLLM (ICLR 2025), https://proceedings.iclr.cc/paper_files/paper/2025/hash/5503a7c69d48a2f86fc00b3dc09de686-Abstract-Conference.html — preference-based strong/weak routing; https://github.com/lm-sys/routellm.  
[3] Cascadia (ICLR 2026), https://proceedings.iclr.cc/paper_files/paper/2026/hash/b76105b94a8c1286c860ad885ec588f1-Abstract-Conference.html — joint placement and cascades; benchmark-specific claims.  
[4] Punica (MLSys 2024), https://proceedings.mlsys.org/paper_files/paper/2024/hash/054de805fcceb78a201f5e9d53c85908-Abstract-Conference.html.  
[5] S-LoRA (MLSys 2024), https://proceedings.mlsys.org/paper_files/paper/2024/hash/906419cd502575b617cc489a1a696a67-Abstract-Conference.html.  
[6] llama.cpp server docs (rolling upstream; version must be pinned), https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md.  
[7] vLLM LoRA documentation, https://docs.vllm.ai/en/stable/features/lora/; security https://github.com/vllm-project/vllm/blob/main/docs/usage/security.md.  
[8] R2R token routing (NeurIPS 2025), https://proceedings.neurips.cc/paper_files/paper/2025/hash/b39cef2ef90591cffdc9c674cd55bebe-Abstract-Conference.html.  
[9] QLoRA (NeurIPS 2023), https://papers.neurips.cc/paper_files/paper/2023/hash/1feb87871436031bdc0f2beaa62a049b-Abstract-Conference.html.  
[10] Agent Distillation (NeurIPS 2025), https://proceedings.neurips.cc/paper_files/paper/2025/hash/99263f9bf46874e2b8b7f104b5063864-Abstract-Conference.html.  
[11] Hindsight (ACL Demo 2026), https://aclanthology.org/2026.acl-demo.27/.  
[12] Mem0 (2025 preprint; 2026 publication), https://arxiv.org/abs/2504.19413.  
[13] Lost in the Middle (TACL 2024), https://aclanthology.org/2024.tacl-1.9/.  
[14] Titans (NeurIPS 2025), https://papers.neurips.cc/paper_files/paper/2025/hash/a4ca07aa108036f80cbb5b82285fd4b1-Abstract-Conference.html; MIRAS background https://research.google/blog/titans-miras-helping-ai-have-long-term-memory/.  
[15] Nested Learning / Hope (Google Research, November 2025), https://research.google/blog/introducing-nested-learning-a-new-ml-paradigm-for-continual-learning/.  
[16] Mamba-3 (ICLR 2026), https://proceedings.iclr.cc/paper_files/paper/2026/hash/8abd2043b71a074278d5f687947bff9c-Abstract-Conference.html.  
[17] A Systematic Survey of LLM Routing (EMNLP 2026), https://aclanthology.org/2026.findings-emnlp.2072/.  
[18] SWE-Bench Pro V2 validation changes (Sept 2026) illustrate benchmark leakage and invalid-task pitfalls, https://labs.scale.com/leaderboard/swe_bench_pro_public_v2.  
[19] NVIDIA perspective on small language models in agent systems (vendor analysis, Aug 2025), https://developer.nvidia.com/blog/how-small-language-models-are-key-to-scalable-agentic-ai.

## Review and boundaries

No model downloads, installs, inference, training, paid cloud jobs, Slink SSH operations, backend restarts, or hardware modifications were performed for this research note. The proposed experiments need their own execution authorization, real receipts, and independent review. Only an accepted design decision should change production routing.
