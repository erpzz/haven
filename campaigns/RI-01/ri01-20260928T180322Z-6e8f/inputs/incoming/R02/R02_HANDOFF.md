# Specialist handback

**Thread / owner / task ID:** R02 — Intelligence Stack, Model Routing, Memory & Autonomous Agents / proposed H02 ownership; H00 integration review.  
**Input repository version and hashes:** `HAVEN_ASTRA_Cumulative_Starter_v1.0.zip`, SHA-256 `55f693f64c56a9d8f13a6cd5725ab4c427af6ade2e127fe8e71829eca1f1d412`. The later `HAVEN_Tonight.zip` contains an identical copy of all 146 starter entries. Individual reviewed-file hashes are in `INPUT_AUDIT.json`.  
**Requirements covered (retain IDs):** primary `REQ-AI-01`–`09`; supporting `REQ-PRIV-01`–`09`, `REQ-DAILY-03/04/06/09/10`, `REQ-RESEARCH-02/03/04/06/07`; cross-domain coverage is in `INTEGRATION_AND_PACKAGES.md`. Other cumulative requirements remain in scope with their existing owners.  
**Actual work performed versus proposed:** read source documents and draft schemas from the actual archives; compared nested archive bytes; researched primary documentation; calculated illustrative costs; authored and checked this documentation package. No PC/runtime/model/framework/connector/device benchmark was executed. No current application commit was inspected.  
**Owned paths changed:** only this new handback directory in the chat working container. Proposed destination, after review: `design/H02/R02/`. No original archive, shared schema, M0 code, M4 configuration, provider policy or active coding workspace changed.  
**Research date:** 27 September 2026 US Eastern; corresponding evidence timestamps may be 28 September UTC.

## Decisions

### Executive conclusions

1. **Recommendation:** use one thin Haven coordinator with durable bounded jobs and replaceable inference adapters. Keep trusted state, consent, budgets, evidence and outcomes under Haven ownership.
2. **Recommendation:** deterministic code first; qualified local inference next; privacy-eligible low-cost hosted inference next; bounded stronger reasoning only when it can improve the task. This is a routing policy, not a requirement to call every model in sequence.
3. **External finding:** Hermes supports local/provider options but its reviewed tool-use guide requires a configured context of at least 64,000 tokens. That is a compatibility/performance gate, not proof it sends or charges 64,000 tokens every turn. [R02-S01–S02]
4. **External finding:** Hermes documents mutable memory/skills and automatic post-turn review, with controls to disable or gate them. OpenClaw documents one trusted security boundary per gateway, not hostile multi-tenant separation. Neither becomes Haven's authority service by adoption. [R02-S03–S04]
5. **Source finding:** the starter's job and context schemas are intentionally mock/synthetic, whereas its runtime prose describes a richer lifecycle. Propose new operational contract revisions alongside the frozen examples; do not enable execution by changing a Boolean.
6. **Recommendation:** researchers, readiness checks, perception investigations and logistics are mostly jobs, not independent personalities or permanent processes. Separate processes where privilege, native dependencies, resource isolation or fault containment justify them.
7. **Recommendation:** measure accepted task outcomes, privacy failures, interruption, tail latency and all retries—not only tokens per second or advertised model benchmarks. No local-model winner or purchase is established here.
8. **Recommendation:** reconcile any actual NIGHT-01 N1/N2 results first. Extend that isolated lab with a privacy/cancellation experiment; do not build its assistant core a second time. Stop at this design handback.

### 1. Architecture and deployment boundaries

Haven should be a useful daily assistant even when aircraft, sensors, fabrication equipment or the internet are absent. Intelligence is a replaceable advisory subsystem within the broader platform, not the platform's universal controller.

The request path is: **authenticated interaction → task/consent checks → scoped retrieval → no-model handler or inference → validated answer/proposal → fresh authorization checks → appropriate domain service → durable observed outcome.** A model can propose an action. It cannot create the identity, grant, approval or execution receipt that makes the action valid.

Use these logical modules, initially within a small application rather than independently deploying every box:

| Module | Responsibility | Must not own |
|---|---|---|
| Interaction ingress | Bind authenticated principal, device/session, intended audience, turn and cancellation target | Identity inferred from prompt text, voice or a model |
| Task coordinator | Durable lifecycle, deadlines, work scheduling, checkpoints, idempotent job submission and bounded child work | Connector credentials, physical control or permission creation |
| Context and memory service | Authorized retrieval, temporal conflict resolution, correction/deletion propagation and context manifests | Treating generated summaries as source truth |
| Inference gateway | Registry lookup, task-qualified routing, context sizing, provider request normalization and usage receipts | Native provider tool execution, arbitrary endpoints or fallback that widens consent |
| Tool broker | Expose a small signed-off capability catalog; validate arguments and resolve server-side identity | A general shell, arbitrary SQL, arbitrary filesystem paths or automatic skill installation |
| Outcome validator | Check schema, references, claim/evidence bindings, proposal scope and outcome status | Certifying truth merely because JSON is valid |
| Publication gate | Recheck audience/grants and publish validated output or an explicit unavailable/unknown state | Leaking private drafts through speculative streaming |
| Audit/budget ledger | Record immutable events, reservations, actual usage, unknown charges and references to evidence | Storing raw secrets or all private prompts by default |

**Where components run.** Retain the proposed Windows → Ubuntu 24.04 WSL2 / Python 3.12 / SQLite-on-Linux foundation. At the synthetic stage, reuse N1's CLI/test double and private lab database: there is no need for a listener. A later Haven UI can use the proposed FastAPI/Pydantic application, with one coordinator owner and bounded asynchronous work. Never run blocking inference or native media decoding on the request event loop.

A qualified local model server runs as a separately constrained process with no connector credentials. Media decoding and later CAD/simulation evaluation use narrowly scoped disposable subprocesses when needed. CPU, RAM and accelerator admission limits belong to the host scheduler. The initial deployment has one local inference lane, not one GPU instance for every role.

**Trusted services remain separate security boundaries.** Real connector writes, credential storage and durable reminder delivery belong to H03/H04 services once separately approved. They must not inherit framework execution permissions. The scheduler can initially be mocked in the lab; real reminders require their own qualified lifecycle and delivery process. Existing ASTRA policy, mission execution and recovery remain separately owned and unchanged. Independent alarms/manual recovery must not wait for model availability or its cloud allowance. This is not a claim that a single sleeping desktop provides high availability.

Do not add a broker, vector database, ROS 2, distributed agent mesh or general computer-use layer for this slice. Add infrastructure only when a measured constraint cannot be addressed by the present bounded design.

### 2. Build-versus-integrate decision

| Criterion | Thin Haven coordinator — preferred | Hermes Agent — bounded challenger | OpenClaw — bounded alternative |
|---|---|---|---|
| Reuse | Must implement a small job loop and adapters; matches existing foundation | Useful packaged agent loop and provider integrations | Useful packaged assistant/gateway and channel infrastructure |
| Context | Haven selects only required evidence/tools | Reviewed documentation requires ≥64k configured context for tools | Must measure actual system/tool/session overhead |
| Authoritative memory | One Haven revision/consent model | Built-in and external stores must be disabled or confined to synthetic evaluation | Do not make framework sessions the canonical two-user memory |
| Authority | Small broker contracts are designed into the boundary | All tools must pass through Haven broker; remove broad capabilities | Separate trust boundaries, credentials and restricted gateways if later used |
| Cost accounting | One ledger can attribute all calls | Account for review forks, tools, retries and delegate work | Account for gateway/background activity and provider use |
| Main risk | Underestimating reliability and maintenance engineering | Adapting a broad agent without secretly widening authority or memory retention | Treating one household gateway as adequate privacy isolation |
| Verdict | Build only the next bounded slice, not a new general framework | Evaluate in isolation only after separate install approval | Keep as the third comparison; do not install in parallel now |

The Hermes facts above come from its official repository/provider guide. Its memory documentation also describes built-in store switches, external-memory distinctions, review controls and staged writes; revalidate these against the exact eventual release. [R02-S01–S03] OpenClaw's security guidance explicitly recommends separate gateways/credentials and preferably OS users/hosts when trust boundaries differ. Its multi-agent features are not themselves a household privacy proof. [R02-S04–S05]

**Hermes evaluation configuration requirement, not an installation recipe:** disable automatic post-turn reviews; disable built-in memory/profile stores and external-memory tools; expose only the reviewed synthetic broker tools; disable skill modification, installation, scheduling, shell/browser/computer control and delegation. Confirm the effective runtime catalog and absence of hidden calls. If a selected release cannot satisfy these conditions, classify it **INELIGIBLE_FOR_THIS_EVALUATION** rather than weakening Haven's boundaries. Do not shrink its documented minimum context to manufacture a win.

Adopt a framework later only if it passes the same privacy/authority gates and has a credible maintenance advantage. Pre-register a suggested materiality threshold: at least 25% less measured integration/maintenance effort over a representative change exercise, or a useful capability unavailable at reasonable custom complexity, without worse task acceptance or broken resource limits. This is a proposed decision threshold, not a measured result. Count the complexity of disabling features as maintenance too.

**Layer distinctions:** Qwen/Gemma/hosted models provide inference; Ollama serves models; Hermes/OpenClaw coordinate agents; Haven owns domain state and authority. Muse is a product/experience reference: Meta's September announcement describes a personal agent on a dedicated VM. That announcement does not establish an interchangeable Haven inference API or self-hostable runtime. Do not import its marketing capability claims into Haven's qualification record. [R02-S06]

### 3. Model routing and qualification

| Route | Use | Qualification or stop rule |
|---|---|---|
| N0 — no model | IDs, time conversion, timer delivery, exact scoped lookups, receipts, arithmetic, checksums, readiness rules and approved template filling | Prefer this whenever the task has an exact deterministic solution |
| L1 — compact local | Short grounded answers, intent proposals, extraction, selected-image descriptions and bounded summarization | Only task classes that pass held-out acceptance, latency and resource tests |
| H1 — cheap hosted | Eligible text synthesis or structured proposals that local inference cannot deliver sufficiently well/quickly | Per-subject cloud permission, allowed provider/endpoint and reserved cost required |
| H2 — stronger hosted | Difficult comparisons, multi-source contradictions, experiment planning or engineering explanations | One explicit escalation reason and bounded effort; no missing-data or authority laundering |
| U — clarify/unavailable | Ambiguous identity/recipient, missing evidence, forbidden egress, unsupported capability, exhausted allowance | Ask for the missing decision or return unavailable; do not spend to bypass a gate |

**Local shortlist:** first qualify **Qwen3.5-4B**, then **Gemma 3 4B** as a contrasting candidate. Official sources establish vision/text model availability; Qwen's card identifies Apache-2.0, while Gemma has its own terms. These are candidates, not demonstrated wins on Eric's machine. [R02-S07–S08] Keep M4's `qwen2.5vl:3b` unchanged; this is a different daily-assistant experiment. Prefer a reviewed quantized build for the local test, but the artifact digest, quantizer, runtime release, templates and vision preprocessing must all be pinned before testing.

**Hosted shortlist:** start with one low-cost candidate, `gpt-6-luna`, only after a separately approved synthetic benchmark. Its official page documents structured outputs and function calling; Haven would use those as proposal formats, not enable its hosted shell or computer-use tools. The reviewed page lists the model ID but does not offer a dated snapshot: record this reproducibility limitation rather than inventing one. [R02-S11] Use `gpt-6-sol` as the first stronger-tier cost candidate. Keep `gemini-3.5-flash-lite` as a later cross-provider portability check, not another account to create now. Pricing evidence is in R02-S10/S12; task superiority is untested. An even larger route should require evidence that this stronger tier fails on valuable tasks, not be the automatic default.

**Private egress:** default cloud use is denied. Consent must cover the actual subjects, purpose, selected provider/endpoint, retained data and output audience; a general household subscription is not consent. The OpenAI API documents no training by default but distinguishes abuse-monitoring and application-state retention. `store=false` is not a universal no-retention promise. [R02-S13] Gemini distinguishes paid/unpaid handling and adds conditions for grounding; do not send household private data to a free tier merely to avoid cost. [R02-S14] Search queries, thumbnails and supposedly redacted excerpts can still disclose private information. Unknown sensitivity or an unreviewed service blocks egress; it does not trigger automatic escalation.

At runtime, eligibility is evaluated **before** price optimization. The router may skip local inference for a task it is not qualified for, or when its queue cannot meet the deadline and eligible hosted inference can. It cannot skip consent. A malformed output gets at most one bounded repair; a difficult but supported task may get one escalation. The global job call cap includes both. Avoid running two strong models merely to produce the appearance of agreement.

Routing should initially be a versioned decision table, not another LLM. RouteLLM is evidence that learned stronger/weaker routing can be cost-effective in benchmark settings; it does not establish a ready-made Haven router or safety policy. Consider learning a router only after collecting enough consented, representative labels and held-out failure examples. [R02-S17]

### 4. Context assembly and memory

Keep four different stores: **source evidence**, **user-controlled durable memory**, **operational state**, and **ephemeral working context**. A model-generated summary is a derived memory item, not a replacement for its sources. A pending action or sensor's current state belongs in operational records, not an agent's conversational notes.

Retrieve in this order: exact IDs and revision references; authorized structured queries; tags/full-text search; then optional semantic retrieval only if benchmarked recall justifies it. Authorization and subject/purpose constraints filter candidates before ranking, not after private snippets enter the prompt. Search infrastructure must prevent unauthorized term statistics, cached answers or result counts from becoming a side channel; isolated per-user indexes are a reasonable first design. Shared records live in an explicitly granted collection, not a union of the two private stores.

A context packet contains the minimum current user turn, relevant verified preferences, a short conversation continuation, source excerpts with timestamps/revisions, known unknowns, and only the tool schemas required for that task. Exclude credential material and internal audit details the model does not need. Retrieved text/media/tool results are labeled untrusted data, never elevated to policy.

**Proposed starting allocation:** an 8,192-token local window, with at most 6,144 total input tokens, 1,024 reserved output tokens and 1,024 headroom. Input includes policy, schemas, history and media-token estimates—not just source text. Start at 4,096 total if hardware measurements demand it, with corresponding smaller allocations. These are planning caps, not guaranteed hardware fit. Actual adapter tokenization/preprocessing controls admission. Too much context triggers deterministic omission with an omission manifest, a narrower question or an eligible larger route, never silent truncation of policy/provenance.

Memory records need owner, subjects, purpose, source refs, valid-from/valid-until, recorded time, uncertainty, retention rule, revision and correction/tombstone lineage. Preserve both the event time and when Haven learned it. Conflicting records remain visible until a rule or person resolves them; recency of ingestion alone does not prove truth. Durable sensitive inferences require explicit consent and should generally remain proposals rather than quietly saved facts.

Correction and deletion invalidate derived summaries, embeddings, answer caches, queued packets, tool results awaiting publication and framework snapshots. Restore replays the current revocation/tombstone ledger before serving historical content. Keep only approved minimal audit metadata; evidence traceability is not permission to retain deleted content forever. Deletion from a third party has its own confirmation/retention status. Information already shown to a person or already transmitted cannot be retroactively undisclosed.

Do not fine-tune shared weights on the household's private history. Do not use a framework's automatic learning loop as an alternative memory writer. Public system-prefix caching may be shared; private prompts, sessions and KV/cache namespaces must be scoped and invalidated. LongMemEval supplies useful temporal/update/abstention dimensions; its newer V2 adds memory about changing environments and workflows. Neither proves two-person revocation safety. [R02-S18–S19]

### 5. Vision, speech and tool selection

**Vision:** begin with a user-selected image or explicitly captured short clip. Store source/crop hashes, source device, owner/subjects, capture time or UNKNOWN, receive time, image dimensions, transformations and parent evidence IDs. Start with at most two selected stills per interactive job; clip/frame limits need their own reviewed profile. Text seen in an image is untrusted content. Claims identify supporting frames and distinguish observations from interpretation; absence outside the frame is not proof of absence in the room. No face identification, unseen-space reconstruction, clinical inference or physical permission follows from a caption. H08 owns spatial calibration/uncertainty; H05/H10 own movement to obtain another view.

**Speech:** use an explicit push-to-talk path first. Candidate local transcription is whisper.cpp with a small qualified model; candidate local synthesis is Kokoro-82M. Their official projects establish offline-capable implementation/model availability, not acceptable latency, voice quality or two-user performance here. [R02-S15–S16] Evaluate native phone speech separately with H07 rather than assuming browser audio equals a native Watch/glasses experience.

Transcription produces tentative words, timestamps and uncertainty; diarization does not authenticate the speaker. Names, recipients, quantities and consequential commands get confirmation when uncertain. Bind the authenticated device session to the user, not acoustic similarity. Pause recording visibly; default raw-audio retention to none after processing unless specifically authorized. TTS receives only publication-approved text and a permitted output device. Private content must not play through a shared speaker by accident.

Barge-in immediately stops client playback. It does not silently cancel a reminder, revoke consent or tell an aircraft to stop. Separate intents are **stop speech**, **cancel this reasoning job**, **cancel a scheduled task**, and **request domain recovery**. An ambiguous “stop” silences speech immediately, inhibits new proposals from the interrupted job and asks what else should stop. Independent physical recovery follows the existing domain's policy, never a newly improvised LLM command.

**Tools:** select from the intersection of the reviewed capability catalog, principal grants, purpose, job allowlist, domain qualification and current resource state. Distinguish reading, external egress, draft creation, state changes and physical execution. A web read can disclose a sensitive search query even though it is “read-only.” Names and JSON schemas alone are not permission. Validate target accounts/resources, exact recipients, payload hashes and versions server-side. Unknown capabilities return unavailable, not “install a skill.” MCP may later transport reviewed tools, but it is optional; its own security guidance forbids token passthrough and requires audience separation. It is not a substitute for Haven policy. [R02-S23]

### 6. Budgets, cancellation, concurrency and portability

**Budget admission:** atomically reserve a conservative maximum before any model/tool call at job, user, household and provider levels. Include input, output/reasoning, media, cache writes/storage where relevant, search/tool charges, retries and child jobs. Reserve non-overlapping child slices under the parent; a child cannot create a new allowance. Unknown pricing, unknown route or inadequate reservation blocks paid work. The starter's illustrative $10 benchmark allowance is explicitly not authorized; this thread's permitted prototype inference spend is zero.

The ledger uses integer micro-USD for runtime accounting and explicit currencies/rate revisions for invoices. Model-generated cost estimates cannot override authoritative rates. On completion reconcile against usage; on timeout retain an unresolved reservation until reliable usage/reconciliation or a conservative settlement rule. Client cancellation need not stop provider billing. Unknown reservations survive restart and cannot be recycled to exceed the allowance. Application controls cover only calls through the controlled broker; they are not a guarantee against external use of the same account.

**Scheduling:** one accelerator generation at a time initially. Each user has a separate queue and allowance. Use weighted fair selection with equal interactive shares by default; permit at most one admitted interactive model job per user and one household background job waiting/running, with one total accelerator holder. Background work runs only when no interactive work is ready, and yields at bounded checkpoints. Fairness is measured in occupied service time, not only task count. CPU-based receipts/cancellation and the independent scheduler never queue behind GPU work. Do not reserve a second GPU merely to make roles appear autonomous.

A starting policy caps one non-preemptible background inference call at ten seconds; a backend unable to stop within the required interval is not admitted to the interactive-sharing profile. Short local calls can instead return partial progress and checkpoint. Exact targets are validated by H06, not promised. Real-time physical control is outside this scheduler.

**Cancellation:** durable cancel intent increments an epoch, prevents further tool calls and suppresses late publication. Workers receive cancellation tokens and deadline signals; only the subprocesses owned by that job may be terminated. An in-flight external write moves to reconciliation, not blindly to “cancelled.” If the target system may have committed, report OUTCOME_UNKNOWN until checked. Stop physical work only through the domain's qualified recovery path. Leases use owner IDs and monotonically increasing fencing tokens; stale workers cannot publish, charge a new slice or execute after losing their lease.

**Portability:** a normalized request carries text/media refs, structured response schema, token/deadline limits and cancellation—not vendor SDK objects. Normalized output carries visible claims/proposals, usage, provider request ID, finish reason, model revision and validation status. Preserve raw provider usage fields in a restricted accounting record so normalization does not erase cache/reasoning charges. Do not store hidden chain-of-thought; keep compact decision reasons and observable evidence.

The registry records exact local artifact and runtime digests, prompt/template/tool-catalog hashes, supported modalities, context budget, schema guarantees, cancellation behavior, privacy/retention profile, price revision and task qualification. Provider switches require compatible capabilities and fresh consent. An API advertised as OpenAI-compatible is not proof of equivalent JSON, streaming, token accounting or cancellation. For example, Ollama documents local structured output support but explicitly says its Cloud does not currently support structured outputs. [R02-S09] Contract tests must expose such differences; unsupported required features make a route ineligible rather than silently degrading.

### 7. Useful autonomous workers

Keep the starter's RA01–RA08 vocabulary. “Autonomous” means a person sponsors a finite task whose bounded next steps can proceed under pre-approved read/proposal permissions; it does not mean persistent unbounded deliberation.

| Role | Useful bounded work and trigger | Default placement | Separate process only when… |
|---|---|---|---|
| RA01 Concierge | Answer, clarify and route a user turn | Coordinator job | Serving/inference isolation demands it |
| RA02 Research scout | Compare a finite source set; verify a changed claim; return a cited correction/brief | Job with source/query/time caps | A reviewed fetch/parser needs network or native isolation |
| RA03 Readiness steward | Recompute expiry, battery/inspection/calibration availability; report changed reasons | Deterministic event/timer job; model optional for wording | Independent uptime from conversational runtime is required |
| RA04 Perception investigator | Explain selected frames; identify missing evidence; propose one permitted next measurement | Job with media/information-gain caps | Decoder/VLM/GPU fault isolation or sensor-specific dependencies require it |
| RA05 Engineering investigator | Propose measurable design alternatives or parametric dimensions, retain provenance and stop at bounds | Coordinator campaign job | CAD/simulation tooling needs a restricted sandbox; never printer credentials |
| RA06 Experiment analyst | Apply the frozen analysis plan and report failures/uncertainty | Deterministic scoring where possible; separately reviewed result | Independent evaluator environment protects held-out criteria |
| RA07 Logistics coordinator | Compare qualified resources/time windows and prepare reservations or a bill-of-materials proposal | Job with deterministic constraints first | A solver or approved domain scheduler needs independent lifecycle |
| RA08 Communication assistant | Prepare minimal audience-appropriate drafts and explain genuine delivery receipts | Job consuming domain records | Delivery service requires independent reliability/credentials |

RA02's output is a finite evidence brief, not an endless web watch. RA03 should usually consume zero model tokens. RA04 can request information, not move a robot directly. RA05 may optimize a candidate but cannot edit its evaluator, approve its design or fabricate it. RA07 must not purchase, silently reassign a person's private calendar, or reserve a physical asset based on guessed availability. RA08 must not say “help is coming” from a local storage acknowledgment.

Start without child agents. Later parallel research is allowed only when independent subtasks justify it, each with a separately scoped packet and a budget slice; the parent gets summaries/evidence refs, not all private transcripts. Process separation alone does not make an evaluator independent: H06 or another authorized reviewer owns criteria and acceptance. Anthropic's research-system report is useful deployed prior art for parallel inquiry and checkpointing; its reported resource overhead is a warning, not a universal multiplier for Haven. [R02-S22]

### 8. Maturity and purchase gates

| Maturity | What belongs here | Haven evidence and next gate |
|---|---|---|
| Available now externally | Structured local inference, compact VLMs, local ASR/TTS, agent frameworks, retrieval/evaluation software | DOCUMENTED_EXTERNAL only; not installed or qualified by this work |
| Feasible prototype | Scoped notebook answers, deterministic readiness, correction/revocation, bounded read-only worker jobs, local/hosted routing and selected-image explanations | Synthetic lab → task benchmark → two-user/operator acceptance |
| Research-stage | Generalizing memory across workflows, learned cost-quality routing, active perception under uncertainty, bounded engineering campaigns with physical measurements | Protected objectives, held-out environments, independent evaluation and separately approved hardware |
| Speculative | Reliably self-improving general household agent, open-ended autonomous workshop, robust protective decisions from incomplete multimodal evidence | Research questions, not purchase justifications or promised features |

The starter reports a capable desktop but no qualified GPU/VRAM/driver/runtime inventory. Verify the actual Windows/WSL host, available RAM/VRAM under normal load, CPU/GPU drivers, thermal behavior, disk, sleep/network behavior and competing M0/simulator needs before sizing models. Do not infer capacity from parameter count or downloaded weight size. A server can fit weights and still fail on KV state, image preprocessing, two-user latency or native dependencies.

No purchase is needed for design or the synthetic experiment. A local benchmark needs explicit download/install permission and enough measured headroom, not a new GPU by default. Shrink context, use an already-qualified smaller model, separate heavy jobs, or use consent-eligible hosted inference before buying hardware. A purchase requires a written unmet task/SLO, a measured bottleneck, alternatives and a 12-month cost/energy/maintenance comparison. A dedicated always-on host may be an availability decision rather than an inference-speed decision. No printer, new aircraft, glasses or Watch is a prerequisite to the daily-assistant runtime.

## Evidence

`SOURCES.md` records primary URLs, date checked, source type, findings and limits. Its IDs are proposed R02-local evidence IDs, not replacements for the starter's R01–R39 source registry. Important current additions include Hermes review controls, explicit OpenClaw trust boundaries, current model pricing, LongMemEval-V2 and the τ³-bench update in the repository still named `tau2-bench`. No leaderboard score is imported as Haven performance.

The archived warning about multiple Hermes writers sharing one home was **not independently reconfirmed in the current memory page**. It is not repeated as a verified current limitation. The design still avoids shared authoritative framework stores on architectural grounds. The 64k configured-context requirement was reconfirmed. No paper or marketing example proves Haven has autonomous engineering, robust perception or emergency capability.

Actual checks here concern input bytes, documentation and arithmetic. All model, framework, security-containment, native phone, physical and runtime tests below remain NOT_EXECUTED. Historical starter package-test results are not rerun M0 tests.

## Interface changes

See `CONTRACT_DESIGN.md` for exact producers, consumers, required fields, units, authority, error/retry semantics and proposed revisions. All `CR-R02-*` require H00 review; identity/consent changes additionally require H04, scheduling/receipts H03, evidence/physical fields H05/H07/H08/H09 as applicable. Frozen synthetic fixtures remain inert. A new API is not authorized merely because it is described here.

## Acceptance

The smallest experiment, optional inference/framework qualification and later engineering campaign are specified in `BENCHMARK_AND_EXPERIMENTS.md`. `R02-T01`–`T12` map to the existing AT-* requirements and EX01/02/03/04/06/28/29/32. Expected results and stop conditions are specified; actual status is NOT_EXECUTED. H06 is the proposed independent acceptance owner; no additional reviewer agent was started.

## Risks and open questions

The runtime must fail locally to the affected operation, not give an uncertain component more power or collapse the entire assistant. Principal risks and required behavior are:

| Failure | Required response |
|---|---|
| Wrong/unknown user or device | Deny private retrieval and side effects; request authenticated context; voice recognition cannot substitute |
| Revoked grant during a job | Invalidate packet/cache, cancel dependent processing, suppress unpublished output, reconcile already committed effects |
| Stale/missing source or unknown capture time | Label stale/unknown, refresh only with permission; never relabel received time as capture time |
| Prompt injection in notes/images/audio/tool results | Treat as data; no added capabilities, cloud destinations, recipients, policies or skills |
| Malformed/unsupported model output | Bounded repair or unavailable; no best-effort parsing into a consequential action |
| Network/model/provider failure | Preserve drafts and state; no unauthorized fallback; independent reminder/recovery channels retain their own behavior |
| Lost write acknowledgment | OUTCOME_UNKNOWN, idempotency lookup/reconciliation; no blind retry or invented success |
| Crash, stale worker or clock jump | Expire leases; fence late results; reconcile reservations/actions; do not replay physical execution |
| Budget exhausted or GPU busy | Queue within deadline, use eligible alternative or state unavailable; do not starve the second user or safety services |
| Physical device unavailable/fault | Domain recovery/unknown status; research cannot upgrade qualification or block ordinary assistance |
| Malicious or mistaken host administrator | Application scopes do not protect plaintext in active host memory; do not promise private-from-admin isolation |

Two independently consenting people can share services without sharing private data, but the threat model must be explicit. If privacy from the host administrator is required, independent user-controlled compute/keys or another separately reviewed trust architecture is needed. Disk encryption or two database tables alone does not solve that threat. Employer/customer data and credentials remain outside this personal system.

Only material unresolved decisions: the actual N1/N2 result and paths; real hardware/runtime inventory; each person's acceptable host/cloud/output trust boundaries; the first daily-use task mix and latency goals; and whether a later framework trial is worth its integration cost. None blocks the current documentation handback or separate M0 work.

## Next package

Propose **R02-P01: reconcile existing N1/N2 evidence and finalize the typed runtime-contract change requests** under `design/H02/R02/`, followed only after approval by **R02-P02: extend the isolated lab with the no-model context/cancellation experiment**. Do not rebuild N1 if it already exists. Detailed scope, dependencies, estimated effort and stop gates are in `INTEGRATION_AND_PACKAGES.md`.

Requested next decision is H00/H04/H06 review of this design and selection of a single bounded package. It is not authorization for installation, inference, accounts, deployment or physical action. **R02 ends at this handback gate.**

## One-page integration summary

The complete paste-ready summary is in [INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md). It introduces no new scope beyond this handback.
