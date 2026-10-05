# Haven Model Lab — Ecosystem & Model Scout
**Research date:** 2026-10-05  
**Scope:** Windows 11 desktop, RTX 2070 Super 8 GB VRAM, 64 GB system RAM; local/private inference; Haven / PROJECT ASTRA use cases.

## Executive decision

Haven should **stop trying to win by being another general-purpose local-chat UI**.

The current Model Lab already has useful differentiators that the generic tools usually treat as secondary: explicit engine ownership, no silent cloud/CPU fallback, checksum-pinned downloads, live hardware telemetry, controlled one-request-at-a-time experiments, reproducible benchmark receipts, conservative VRAM fit gates, LAN/account isolation, and exact process cleanup.

The best direction is therefore:

1. **Keep llama.cpp as the fast local inference substrate.**
2. **Keep Haven Model Lab as the local-compute control/evaluation plane.**
3. **Borrow or integrate an established chat/agent shell rather than rebuilding commodity chat features.**
4. Make Haven's unique layer about *model selection, capability routing, experiments, provenance, privacy, hardware-fit decisions, and project-specific agents*.
5. Do not choose a foundation solely by how pretty its chat window is.

## What the mature tools already do better than our current browser shell

### Open WebUI
Very broad web product: persistent conversations, multi-model chat, attachments, web search, code execution, memory, model/agent wrappers, tools, MCP, RBAC, groups and authentication.

This is the strongest practical reference for a browser-based household/team shell. It can sit in front of an OpenAI-compatible llama.cpp server. It is not strictly OSI-open-source on current releases: v0.6.6+ adds a branding clause. The project explicitly says deployments with <=50 users can rebrand, which covers Haven's current two-person use, but the license choice matters if Haven later becomes a broadly distributed product.

Sources:
- https://docs.openwebui.com/features/
- https://docs.openwebui.com/features/extensibility/mcp/
- https://docs.openwebui.com/license/

### AnythingLLM
MIT-licensed, local-first, strong RAG/document workflows, agents, MCP and multi-provider support. The Docker/server flavor supports multi-user operation. This is a strong candidate if Haven's near-term UI centers on personal knowledge, documents and agent workspaces more than hardware experimentation.

Sources:
- https://github.com/Mintplex-Labs/anything-llm
- https://docs.anythingllm.com/

### LibreChat
MIT-licensed and a strong multi-provider/agent web shell with MCP, code execution, files, auth/SSO and memory. It is a cleaner long-term fork/integration target than Open WebUI if permissive licensing and full Haven branding become important. It is less opinionated about local model lifecycle and GPU tuning, which means Haven's Model Lab still has a clear role.

Sources:
- https://www.librechat.ai/docs/features
- https://github.com/LibreChat-AI/LibreChat/blob/main/LICENSE

### Jan
AGPLv3, genuinely open-source, local-first desktop application. Current Jan releases are especially relevant technically because Jan has already added llama.cpp Router Mode, Multi-Token Prediction controls and MCP routing/approval. It is a better reference for local-model lifecycle and advanced llama.cpp behavior than our current hand-built UI. It is less naturally aligned with Haven's two-person browser/LAN requirement because it is desktop-first.

Sources:
- https://www.jan.ai/changelog/2026-05-22-jan-v0.8.0
- https://www.jan.ai/docs/desktop/integrations/mcp-servers
- https://github.com/janhq/jan

### LM Studio / llmster
Probably the best *product* baseline for easy local inference right now: strong model management, local APIs, OpenAI/Anthropic compatibility, stateful chats, JIT model load/unload, MCP and a headless daemon. The UI/application is not the foundation to fork if the goal is open-source Haven, but we should benchmark against it because it is an excellent answer to "why not just use an off-the-shelf tool?"

Sources:
- https://lmstudio.ai/docs/developer
- https://lmstudio.ai/docs/developer/rest
- https://lmstudio.ai/docs/developer/core/headless

### llama.cpp native server UI
The lowest-overhead baseline. Modern llama.cpp already ships a competent built-in chat UI, model server and OpenAI-compatible API. If a feature is only "chat with a GGUF", Haven should not spend engineering time recreating it.

### LocalAI
MIT engine/platform with broad multimodal backends, voice, images/video and distributed inference. Interesting later if Haven becomes a heterogeneous inference fabric, but too much machinery for the present single-PC 8 GB fast path.

Source:
- https://github.com/mudler/LocalAI

### KoboldCpp / text-generation-webui
Both remain useful specialist/tinkering references with mature knobs and extensions. They are not the best architectural center for Haven's privacy, multi-user and cross-project goals.

## Recommended foundation decision

### Recommended now: hybrid, not replacement

**llama.cpp + Haven Control Plane + established chat shell**

Do not delete Model Lab. Reframe it.

- **llama.cpp** owns direct GGUF execution.
- **Haven Model Lab** owns model provenance, downloads, fit tests, profiles, telemetry, experiments, benchmark evidence, engine ownership, per-user job policy and model-routing metadata.
- **An established shell** owns commodity chat history, markdown, attachments, search, knowledge/RAG, MCP presentation, message editing/branching and polished mobile interaction.

For a quick practical household deployment, Open WebUI is the strongest shell candidate.  
For a stricter permissive-open-source/forkable Haven product, compare LibreChat and AnythingLLM first.  
For a desktop-local product or advanced llama.cpp reference, Jan is the strongest reference.

This means our work to date is not wasted: the interesting pieces become the layer *under/alongside* the shell instead of competing with every chat UI on basic UX.

## Model scout: candidates worth testing on this PC

The catalog should not grow by popularity alone. A model earns a pinned Haven download only after a repeatable Haven task suite and license/quant/hash review.

### Tier A — GPU-resident daily-driver candidates

#### Qwen3.5 4B
**Keep as current default / champion to beat.**

Why:
- Already pinned and qualified in Haven.
- Fits the fast path comfortably at Q4.
- Recent community reports continue to treat it as one of the best small general/tool-use assistants.
- A September 2026 LocalLLaMA thread specifically asks whether anything has actually displaced it for fast local-assistant use; the premise itself matches Haven's needs.
- A recent local meeting-assistant project retained Qwen3.5 4B after testing smaller/faster alternatives because reliability mattered more than a small latency gain.

Use cases: general assistant, routing, notes, structured output, modest coding, tool selection.

#### Ministral 3 3B Instruct
**Highest-priority new challenger.**

Official GGUF model card:
- Q4_K_M about 2.15 GB; Q8_0 about 3.65 GB.
- Vision-capable architecture.
- Native function calling and JSON-output positioning.
- 256k advertised context.
- Apache-2.0.
- Explicit edge deployment target; FP8 fits in 8 GB and quants are smaller.

For Haven, that combination makes it more interesting than a generic benchmark winner. Test it specifically for tool selection, JSON arguments, system-prompt obedience and vision when our UI gains a multimodal path.

Source:
- https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512-GGUF

#### Phi-4 Mini Instruct 3.8B
**Strong compact reasoning/coding baseline.**

Common GGUF Q4_K_M is about 2.5 GB; Q5/Q6 remain small enough for this GPU. It has a mature prompt/tool format and is worth keeping as a non-Qwen comparison so Haven does not accidentally optimize its prompts/routing around one model family.

Source:
- https://huggingface.co/tensorblock/Phi-4-mini-instruct-GGUF

#### SmolLM3 3B
**Open/reproducible small-model baseline.**

Apache-2.0, official ggml-org GGUF, hybrid reasoning, llama.cpp support and a relatively transparent training story. Probably not the first choice for Haven's best assistant, but excellent as a lightweight baseline and for measuring whether larger small models are actually buying us useful quality.

Source:
- https://huggingface.co/ggml-org/SmolLM3-3B-GGUF

#### NVIDIA Nemotron 3 Nano 4B
**Interesting architecture; do not promote on benchmark hype alone.**

Official GGUF exists and runs through llama.cpp. Community sentiment is unusually mixed: one April 2026 small-model benchmark ranked it first in a narrow task suite, while detailed LocalLLaMA reports found Qwen3.5 4B substantially more reliable on complex instruction and Home Assistant/tool-control tasks.

This is exactly why Haven needs its own task-based evaluation instead of a popularity score.

Source:
- https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF

#### IBM Granite 4.0 H-Tiny
**Useful enterprise/agent baseline.**

Despite the "tiny" name, the GGUF is roughly 7B total; Q4_K_M is about 4.23 GB. It is still plausible on 8 GB with a bounded context and gives Haven a different model family to test for structured enterprise-style tasks and tool use.

Source:
- https://huggingface.co/ibm-granite/granite-4.0-h-tiny-GGUF

### Tier B — tight 8 GB candidates

#### Qwen3.5 9B
Already in Haven's catalog. Community reports commonly find the 9B class noticeably more capable, but 8 GB users hit the usual trade: weights + KV/context can push the model into partial offload or force lower quantization. Keep it as the "quality vs responsiveness" test, not the default.

#### Ministral 3 8B Instruct
Official Q4 GGUF exists and the model includes vision. It is an excellent comparison against Qwen3.5 9B, especially for tool calling and multimodal work. Treat context length conservatively on the 2070 Super even if the architecture advertises much larger maximums.

Source:
- https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512-GGUF

### Tier C — RAM-assisted specialist experiments

64 GB system RAM means Haven can test models that do not fully fit in 8 GB VRAM, but these should be explicitly labeled **RAM-assisted / latency trade-off**, not mixed into the fast path.

Candidates:
- Qwen3.5 35B-A3B / newer Qwen MoE variants for stronger agent/planning tasks.
- Qwen3-Coder Next for coding-agent experiments.
- Gemma 4 26B-A4B for general/vision experiments.
- Qwen3.8 Flash Next through the existing Strata path.

Community reports show that 8 GB VRAM + 32–64 GB RAM can make large MoE models usable, but prompt processing, context and CPU/RAM offload can dominate latency. The point is not "largest model that boots"; it is "largest model that still wins the correct-task-time test."

## Haven-specific evaluation suite

Do not rank models with a single aggregate academic score. Use a small suite that maps directly to Project Haven.

Each candidate should run:

1. **General assistant:** concise factual explanation, rewrite, planning, ambiguity handling.
2. **Tool selection:** choose exactly one of 8–20 tools; no tool when none is needed.
3. **Tool arguments:** produce schema-valid JSON with no invented fields.
4. **Multi-step agent planning:** propose a bounded plan without prematurely executing actions.
5. **Coding:** understand and patch a small real Haven-style Python/JS task.
6. **Evidence fidelity:** answer only from supplied notes and explicitly say when evidence is missing.
7. **Long-context retrieval:** recover facts at early/middle/late positions without inventing extras.
8. **Conversation continuity:** follow corrections and preserve user-specific constraints.
9. **Safety/policy routing:** refuse unavailable/unsafe actions while still completing the safe portion.
10. **Latency and hardware:** TTFT, decode TPS, total correct-task time, peak VRAM/RAM, context size.
11. **Tool reliability across repeats:** at least 3 repetitions for agent/tool tasks.
12. **Human usefulness:** Eric/Kennedy preference score for actual assistant outputs, kept separate from automated correctness.

A model only becomes a "recommended Haven model" when it wins on the tasks we actually care about.

## The features that make Haven meaningfully different

These are worth building. Generic chat polish is not the moat.

### 1. Fit-aware model routing
Given current free VRAM/RAM, context requirement and task, show:
- **FAST / fully GPU-resident**
- **TIGHT / may spill**
- **RAM-ASSISTED**
- **NOT WORTH IT on this hardware**

Then recommend a model and settings from measured local history, not a static list.

### 2. Capability cards backed by evidence
For each model:
- tasks it passed locally,
- tool-call reliability,
- context tested,
- multimodal status,
- quant,
- exact model hash,
- engine version,
- hardware and date,
- known failure modes.

### 3. Correct-task-time instead of tokens/sec worship
Track whether a slower stronger model solves a task once while a fast small model needs retries. Score latency, correctness, retries and resource impact together.

### 4. Automatic A/B experiment design
"Compare Qwen3.5 4B Q6 vs Ministral 3B Q8 for Haven tool routing" should produce a pinned run plan, execute a bounded repetition set, preserve raw outputs and compute a decision summary.

### 5. Local/hosted escalation policy
Haven's router should know when the local model is good enough and when a harder request needs a stronger hosted model, while preserving user/privacy rules and showing why escalation occurred.

### 6. Two-person private capability routing
Eric and Kennedy can have different memories, permissions, tools and preferred models while sharing the same physical inference host.

### 7. Project-aware workers
Local models should be selectable as workers for Haven research, coding, observation summarization and low-risk background tasks. The UI should show *job/capability state*, not merely chat bubbles.

### 8. Hardware evolution as an experiment
When hardware changes, rerun the same retained suite and answer: "What did this GPU/RAM upgrade actually unlock for Haven?"

## Immediate next engineering experiments

1. Finish and qualify the new **finish_reason / OUTPUT LIMIT / Continue** flow.
2. Add a **model evaluation manifest** format so candidate models can be evaluated before being admitted to the pinned download catalog.
3. Test these first four challengers against Qwen3.5 4B:
   - Ministral 3 3B Instruct
   - Phi-4 Mini Instruct
   - Nemotron 3 Nano 4B
   - Granite 4.0 H-Tiny
4. Trial **Open WebUI + existing Haven llama.cpp endpoint** as a disposable shell experiment.
5. Trial **LibreChat or AnythingLLM** only far enough to compare integration cost, two-user separation and extension points.
6. Do not rewrite Haven around any shell until that comparison is measured.

## Bottom line

If the goal were merely "chat with local models", the honest recommendation would be to stop developing this UI and use an existing tool.

The reason to keep Haven Model Lab is different: turn it into the **evidence-driven local intelligence control plane for Haven**. Let mature open tools handle commodity chat features; let Haven decide what model should run, why, on whose behalf, with what hardware budget, what evidence says it is reliable, and what project capability it unlocks.
