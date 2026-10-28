# R02 — Checked primary-source evidence register

**Checked:** 27 September 2026, America/New_York (28 September UTC). **Method:** public primary documentation/repository pages and a primary research paper abstract; no accounts, inference, installs or model downloads. These are source-reading findings, not reproducible local performance measurements. Mutable documentation and model aliases must be rechecked and pinned where possible before implementation. Source IDs are local proposals, not changes to `research/sources.json`.

Dates below distinguish an identifiable publication/release date from the date checked. A live page without a pinned commit is a limitation, not a fabricated source revision. URLs are supplied for integration and independent review.

## Frameworks and product boundaries

### R02-S01 — Hermes Agent repository
- Primary URL: https://github.com/NousResearch/hermes-agent
- Type/version: official software repository, mutable main reviewed; no release installed or selected.
- Finding: MIT-licensed agent software with provider integrations, tools, memory/skills and agent-loop facilities.
- Limitation: a framework is not a free model; repository availability is not proof of household isolation or suitable resource use. Treat optional broad capabilities as an integration surface, not requested Haven permissions.
- Design impact: bounded challenger to the thin coordinator, not owner of domain authority.

### R02-S02 — Hermes model/provider guide
- Primary URL: https://hermes-agent.nousresearch.com/docs/integrations/providers
- Type/version: official live product documentation; release mapping unverified.
- Finding: documents local/custom endpoints and a minimum **64,000-token configured context** for tool-using agents; smaller configured windows are rejected according to the guide.
- Limitation: this is not a statement that every prompt is 64k tokens or every call is charged for 64k. Runtime, model, KV implementation and actual request size determine resource use.
- Design impact: test complete framework overhead; never silently lower its documented requirement to pass the comparison.

### R02-S03 — Hermes memory and review controls
- Primary URL: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory
- Type/version: official live documentation.
- Finding: memory snapshots are session-scoped; built-in memory/profile stores, external-memory tools, automatic post-turn reviews and skill/memory write approvals have separate controls. Disabling automatic reviews does not disable manually requested refinement.
- Limitation: configuration semantics require release-specific verification; the page is not an independently validated tenant-isolation guarantee. The archived same-home concurrent-writer warning was not reconfirmed here.
- Design impact: Haven remains canonical memory; disable learning/review/tool surfaces in the synthetic framework trial and verify effective behavior, not just config text.

### R02-S04 — OpenClaw security boundary
- Primary URL: https://docs.openclaw.ai/gateway/security
- Type/version: official live security documentation.
- Finding: describes one trust boundary per gateway; not a hostile multi-tenant boundary. Mixed-trust operation should separate gateways and credentials, preferably OS users or hosts. Message-tool access can cross conversation/provider boundaries unless restricted.
- Limitation: separate processes do not by themselves protect against a host administrator.
- Design impact: a household gateway is not sufficient evidence for independent private users.

### R02-S05 — OpenClaw multi-agent routing
- Primary URL: https://docs.openclaw.ai/concepts/multi-agent
- Type/version: official live software documentation.
- Finding: documents multiple agent configurations and per-agent tool/sandbox considerations.
- Limitation: configuration separation must not be confused with an adversarial security boundary or measured low overhead.
- Design impact: keep OpenClaw as the single bounded alternative framework; no parallel deployment is proposed now.

### R02-S06 — Meta Muse announcement
- Primary URL: https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/
- Type/date: vendor product announcement, **8 September 2026**.
- Finding: describes a personal agent running on a dedicated VM and powered by Muse Spark.
- Limitation: an announcement is not evidence of an interchangeable Haven inference API, downloadable weights, self-hostable runtime, or independently proven safety. No broad “first” marketing claim is adopted.
- Design impact: product-experience inspiration, not a fourth framework to integrate.

## Local inference and speech

### R02-S07 — Qwen3.5-4B model card
- Primary URL: https://huggingface.co/Qwen/Qwen3.5-4B
- Type/version: official Qwen model card; weights/configuration published; downloaded artifact digest not obtained.
- Finding: a 4B language model with vision encoder; card identifies Apache-2.0 licensing.
- Limitation: family-level marketing and vendor benchmark tables do not establish quantized runtime performance, local GPU fit or Haven task reliability.
- Design impact: first local candidate, separate from unchanged M4.

### R02-S08 — Gemma 3 model card
- Primary URL: https://ai.google.dev/gemma/docs/core/model_card_3
- Type/version: official Google model card for Gemma 3; 2025 model family, live card checked now.
- Finding: includes the 4B text/image model and its input/output characteristics; Gemma has its own usage terms rather than an assumed Apache model license.
- Limitation: advertised context capacity is not a promise that the local host can serve it at that size or speed. Runtime/quantization/terms need qualification.
- Design impact: second compact local candidate, not proof that more parameters/context is better value.

### R02-S09 — Ollama structured outputs
- Primary URL: https://docs.ollama.com/capabilities/structured-outputs
- Type/version: official live serving-software documentation.
- Finding: documents schema-constrained structured outputs; explicitly notes that Ollama Cloud does not currently support them.
- Limitation: valid JSON does not verify truth, authorization or evidence. Feature parity cannot be assumed across compatible APIs.
- Design impact: route capability conformance and independent validation are mandatory.

### R02-S15 — whisper.cpp
- Primary URL: https://github.com/ggml-org/whisper.cpp
- Type/version: official implementation repository; mutable main, no build executed.
- Finding: local Whisper inference implementation with Apple/platform examples and published model memory guidance.
- Limitation: example platforms and memory tables are not real-device latency/accuracy evidence for this household. Native build/runtime/weights and recording consent require separate approval.
- Design impact: local speech-recognition candidate; test consequential word/intent errors, not only average transcription quality.

### R02-S16 — Kokoro-82M
- Primary URL: https://huggingface.co/hexgrad/Kokoro-82M
- Type/version: author's model card; published v1.0 dated **27 January 2025**, card checked now.
- Finding: open-weight 82M-parameter speech synthesis model with Apache-licensed weights.
- Limitation: model-weight licensing does not by itself resolve every runtime/voice dependency. No local speech quality, interruption or energy measurements ran.
- Design impact: local TTS candidate after approved text publication, not a reason to enable continuous audio capture.

## Hosted models, economics and privacy

### R02-S10 — OpenAI API pricing
- Primary URL: https://developers.openai.com/api/docs/pricing
- Type/version: official live price schedule; **Standard / short-context** column used for the examples.
- Finding: supplies distinct input, output, cache and processing-tier prices for the selected GPT-6 candidates.
- Limitation: rates are not task costs. Tool charges, reasoning, context tier, cache writes, regional processing and taxes can change totals; published prices do not prove model quality or account availability.
- Design impact: worked arithmetic in `BENCHMARK_AND_EXPERIMENTS.md`; reverify before paid tests.

### R02-S11 — GPT-6 Luna model reference
- Primary URL: https://developers.openai.com/api/docs/models/gpt-6-luna
- Type/version: official model documentation; advertised request ID `gpt-6-luna`.
- Finding: structured outputs and function calling are documented. The reviewed snapshots section supplies the model ID but no dated immutable snapshot.
- Limitation: enabled product capabilities are not permissions for Haven; actual access, rate limits, latency and task qualification are untested.
- Design impact: first cheap hosted candidate for a future synthetic test, with alias-drift monitoring and hosted execution tools disabled.

### R02-S12 — Gemini API pricing
- Primary URL: https://ai.google.dev/gemini-api/docs/pricing
- Type/version: official live schedule; Standard paid tier used.
- Finding: current `gemini-3.5-flash-lite` token rates and `gemini-3.5-transcribe` estimated speech economics are published. Separate grounding/cache/storage charges and other tiers exist.
- Limitation: published older cheaper models are not automatically the correct long-lived target; recheck lifecycle and measured quality. A quoted per-minute estimate depends on audio/output token assumptions.
- Design impact: later portability/speech comparator, not an account or paid-call authorization.

### R02-S13 — OpenAI API data controls
- Primary URL: https://developers.openai.com/api/docs/guides/your-data
- Type/version: official live API policy documentation.
- Finding: API data is not used for training by default; abuse-monitoring logs may retain content for up to 30 days, subject to documented exceptions. Endpoint/application-state and approved retention controls have additional conditions.
- Limitation: `store=false` is not a universal no-retention guarantee; third-party tools and different endpoints can have different handling. Zero Data Retention cannot be assumed for this user.
- Design impact: provider/endpoint-specific consent and retention review precedes private egress.

### R02-S14 — Gemini API terms
- Primary URL: https://ai.google.dev/gemini-api/terms
- Type/version: official live API service terms.
- Finding: distinguishes paid and unpaid data handling. Paid prompts/responses are not used to improve products under the stated terms, but abuse/security handling remains; grounding has additional retention/use conditions.
- Limitation: billing activation, region and service choice matter; no-training is not no-retention and user consent is still required.
- Design impact: do not route household private data through a free-tier endpoint merely because it is cheaper. Review permitted caching/evidence retention before enabling native grounding.

## Research and evaluation prior art

### R02-S17 — RouteLLM
- Primary URL: https://arxiv.org/abs/2406.18665
- Primary project: https://github.com/lm-sys/routellm
- Type/date: primary research paper, first posted **26 June 2024**; official project repository checked now.
- Finding: studies learned routing between stronger and weaker models using preference data and reports favorable cost/quality tradeoffs on its benchmarks.
- Limitation: dataset/model-pair transfer does not establish privacy-aware routing, downstream task success or safe physical decisions for Haven. No headline savings percentage is projected onto this project.
- Design impact: start with a deterministic router; consider learning only after task-specific labeled evidence exists.

### R02-S18 — LongMemEval
- Primary URL: https://github.com/xiaowu0162/LongMemEval
- Type/date: authors' benchmark repository, ICLR 2025 work; updated dataset history noted in repository.
- Finding: evaluates extraction, multi-session reasoning, updates, temporal reasoning and abstention.
- Limitation: conversational memory accuracy does not test all privacy, revocation, malicious-source or side-effect constraints.
- Design impact: memory rubric dimensions; keep correct abstention distinct from task fulfillment.

### R02-S19 — LongMemEval-V2
- Primary URL: https://github.com/xiaowu0162/LongMemEval-V2
- Type/date: authors' current research repository; original project announces V2 in May 2026; V2 page notes an August 2026 update.
- Finding: evaluates compact evidence retrieval over histories of multimodal agent trajectories, including dynamic state, workflow knowledge, environment-specific pitfalls and premise awareness.
- Limitation: substantial published configurations/histories are not a requirement for Haven. Benchmark memory performance is not proof of reliable autonomous learning or safe retention.
- Design impact: later project/workflow memory experiments; do not download its tooling or adopt automatic runbook writes now.

### R02-S20 — AgentDojo
- Primary URL: https://github.com/ethz-spylab/agentdojo
- Type/version: ETH Zurich/Invariant Labs research software and evaluation environment, mutable main.
- Finding: evaluates prompt-injection attacks and defenses for tool-using agents.
- Limitation: a finite attack suite cannot prove immunity; the package API is described as under development. Its tools are not automatically safe Haven tools.
- Design impact: adversarial source/tool fixtures and a protected regression suite.

### R02-S21 — τ³-bench in the tau2-bench repository
- Primary URL: https://github.com/sierra-research/tau2-bench
- Type/date: Sierra research benchmark; current page announces τ³-bench and a **July 2026 v1.0.1 grading update**.
- Finding: includes voice/full-duplex and knowledge retrieval evaluation; documents that an affected domain's scores across the grading correction are not directly comparable.
- Limitation: customer-service simulation, real-time providers and its adapters do not qualify Haven's two-user or physical domains.
- Design impact: freeze task/grader versions, test voice/tool outcomes and keep corrected results explicit.

### R02-S22 — Anthropic multi-agent research system
- Primary URL: https://www.anthropic.com/engineering/multi-agent-research-system
- Type/date: vendor engineering report, **13 June 2025**.
- Finding: describes deployed parallel research, checkpoint/recovery engineering, evaluation and significantly greater token use in its observed multi-agent workloads.
- Limitation: vendor task/evaluation/architecture-specific observations, not a universal multiplier or evidence every task benefits from subagents.
- Design impact: parallel workers need a measured benefit, scoped context, finite budgets and durable recovery.

### R02-S23 — MCP security best practices
- Primary URL: https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices
- Discovery URL: https://modelcontextprotocol.io/specification/latest/basic/security_best_practices
- Type/version: official protocol security guidance; discovery URL redirected to the **2026-07-28** documentation path.
- Finding: explains audience-validation failures, explicitly prohibited token passthrough and confused-deputy/SSRF risks.
- Limitation: protocol compliance is not authorization policy, trustworthy tool content or complete runtime isolation.
- Design impact: optional reviewed transport only; no direct token passthrough, automatic tool discovery/installation or authority expansion.

## Evidence discipline and limits

External findings are labeled DOCUMENTED_EXTERNAL, not Haven EXECUTED_PASS. Vendor capability/benchmark claims were not independently reproduced. No complete claim that this is the globally newest/best agent architecture is made; this is a decision-oriented current primary-source review of the selected options. Living source pages may change after checking. Framework release/commit pins, local model digests and actual provider availability remain prerequisites to future qualification.

Claims about the starter are based on the exact locally inspected archive members and their hashes in `INPUT_AUDIT.json`, not on substitute documents with similar titles. Source archives were not changed. Main handback conclusions separate recommended design from observed source facts. This documentation package does not introduce external research as an authorization dependency for active M0.
