# System design — a powerful local worker, not an unrestricted production brain

Status: proposal for a future scoped implementation; no endpoint or worker below is deployed by this document. Sources [Sxx] resolve in SOURCES.md.

## 1. Define the minimum useful product

The smallest integrated Haven demonstration is: two synthetic people have private/shared notes; one selected image or object has source-linked context; Haven answers a useful question; a person asks for a small software improvement; a local coding worker creates the change and executes development tests; separate QA/review inspects it; Haven receives verified artifacts and an explanation; an explicitly approved version can later be deployed to staging with rollback.

This demonstrates perception, memory, intention, delegated work and feedback. It does not require a drone, humanoid, headset, implanted interface or household-scale map. Those remain retained branches, not deleted ambitions.

## 2. Separate three logical zones

**Haven Core:** existing application/context/authority direction, a durable job ledger, source/evidence records, task-specific retrieval, reviewer dispositions and a release controller. Prefer the existing Python/FastAPI/SQLite foundation. Do not add a message broker, Kubernetes, universal agent framework or compulsory vector store for the first worker.

**Forge Lab:** one writable coding environment per active job, with its own branch/worktree or isolated checkout, development database, dependencies, browser profile, local preview and logs. It may edit code, run tests, debug, compile, install approved development packages and operate its own services. Its workspace should be disposable and reproducible. A working directory alone is not an OS security boundary.

**Model Service:** a replaceable inference endpoint. Start with one local model request at a time on the available small GPU. The model generates decisions/content; it does not itself own Git credentials, the production database or deployment rights. The job controller owns timeouts, concurrency and admission. Keep network exposure and authentication explicit: localhost inside a VM/container is not the host's localhost.

These zones may share one physical computer initially. A dedicated worker machine, separate inference host, and low-power Haven host are later placement choices. A local model served across an authorized LAN is still local to the user's environment, but the worker becomes dependent on that other machine's availability.

## 3. Agent harness recommendation

**OpenCode + Ollama is the first broad-tool candidate, not an already validated adoption.** OpenCode documents local model providers, editing/shell tools, configurable permissions, MCP tools and a headless HTTP/OpenAPI interface [S01–S05]. That API gives Haven a cleaner integration seam than scraping terminal prose. Use a version-pinned adapter and inspect the actual exposed API before implementation.

OpenCode's server supports basic authentication and defaults to loopback [S03]. Keep it private; use TLS/SSH or a separately approved protected network route between machines. Do not expose an unauthenticated model or agent endpoint to the internet.

**Aider is the focused baseline.** Its local Ollama support can serve small, explicit file-edit tasks [S08]. It is useful for determining whether the model can actually repair a repository before adopting a richer desktop-agent experience.

**OpenHands is the richer alternative.** Its SDK supports agent execution and tools, and current local-model guidance recommends Qwen3.6-35B-A3B with at least 24 GB GPU memory or 64 GB Apple unified memory for quantized variants [S06,S07]. That is project guidance, not a guarantee every quantization/context fits or that smaller models cannot do any task.

**Hermes stays optional.** Its toolsets are relevant, but do not introduce a second independent household memory, scheduler or authority system merely to add a coding worker [S21]. Haven keeps those responsibilities. A general personal-agent framework is not a prerequisite for the coding lab.

### Context caveat found in current documentation

Ollama's OpenCode integration page says 64K or higher context is required [S05]. OpenCode's own provider guide suggests starting around 16–32K when troubleshooting tool calls [S01]. Do not silently pick the smaller number and claim the documented full setup is qualified. Record exact harness/model/context, test the complete tools/system prompt, observe truncation and memory use. A small-context Aider/control-loop test is a separate baseline if the larger harness will not fit. Model-weight file size alone does not establish a usable agent.

## 4. Low-friction autonomy by design

The user's intent is ordinary engineering progress without repeated approval prompts for every file edit or test. Configure a preapproved development envelope, rather than asking the model to ignore restrictions. OpenCode supports allow/ask/deny controls per operation/agent [S02]. Those controls reduce interaction friction; they do not replace OS/network isolation or guarantee model compliance.

Automatically allow within the scoped lab: reading/editing granted repositories, terminal commands, local dependency/build tools, scratch database migrations, local browser/API tests, static analysis, profiling, local preview services and disposable test environments. For system-package experiments, a specifically granted disposable VM may have guest-admin access; this does not confer host-admin rights and is not activated by the present design.

Keep outside the worker: production secrets/data, household recordings, arbitrary host mounts, shared model-service administration, repository settings, merge/release authority, personal/work accounts and physical actuators. The root publisher can receive a patch/bundle and publish it using a scoped credential. A GitHub issue is an input queue, not an authenticated instruction source by itself.

Do not provide the host Docker socket or a privileged host-root mount to a supposedly isolated worker. Docker documents that daemon control can expose the host filesystem [S19]. Put broad development tooling inside a deliberate containment boundary, not behind a warning in a prompt.

No model/harness promises perfect obedience, zero refusals or zero errors. Evaluate instruction fidelity, correct tool use and completed tests, rather than choosing a model on an 'uncensored' label. A false 'done' is more damaging to this project than a specific, truthful blocker.

## 5. Broad catalogue, small active tool set

Maintain a large available catalogue but enable the relevant tools for each task. MCP definitions consume context; OpenCode explicitly warns that large tool collections can overflow it [S04].

Initial tool packs:

| Pack | Proposed capabilities | Scope |
|---|---|---|
| Source | shell, git diff/status, ripgrep, file patching, language-server lookup | One granted source copy; root publishes |
| Build | Python/Node compilers, dependency managers, package-local lock files | Reproducible development environment |
| Test | pytest, property tests, HTTP client, browser automation, disposable DBs | QA results independently reproducible |
| Inspect | debugger, logs, profiler, process/port/resource inspection | Owned processes and granted artifacts |
| Research | primary documentation retrieval and bounded web lookup | Retrieved content is evidence, not authority |
| Design | diagrams, later scoped CAD/3D scripts, image inspection | No fabrication/device dispatch by implication |
| Haven | take-job, read approved context, append progress, submit artifacts, propose skill | Narrow authenticated adapter, not arbitrary SQL |

Prefer documented CLI/API tools to GUI clicking. Browser automation and screenshots are important for rendered UI behavior; arbitrary desktop control is a later separately bounded pack. Do not enable every credentialed MCP server on every task.

## 6. Feedback into Haven

A proposed JobSpec includes job ID, goal, repository/base SHA, exact allowed paths and operations, context/evidence references, active tool profile, runtime/model/context identity, resource/deadline limits, verification plan and acceptance owner. It never relies solely on a natural-language 'be careful' instruction.

Append progress events and keep artifact references. Distinguish statuses such as QUEUED, RUNNING, WAITING_FOR_REVIEW, BLOCKED, FAILED, COMPLETED and CANCELLED; a status report is not proof of execution. Submission returns source diff/commit, exact commands and exit codes, test outputs, screenshots when actually captured, dependency changes, measured resources, remaining failures and a proposed reusable lesson.

Feedback has three destinations:

1. **Code:** reviewable patch or branch, not a direct overwrite of Haven's running service.
2. **Evidence:** raw/derived test artifacts with exact candidate, tool and environment identities.
3. **Memory/skills:** a reviewable note describing what worked, when it applies and what failed. Mark proposed lessons as unverified until checked. Do not place credentials or protected expected answers in general agent memory.

This is knowledge and code feedback, not automatic training of model weights. Fine-tuning is a later distinct experiment with a curated dataset and evaluation; do not silently train on every conversation or trace.

The release path is Build → independent QA → code/evidence review → staging → operator-approved promotion/rollback. The worker may propose changes to its own code, but an outside controller/reviewer applies them. A two-line bug fix need not trigger an entire research campaign; review depth should follow the affected risk and contracts.

## 7. Reuse the real role system

Preserve root scheduling/publication, separate haven_integration_manager/H00 seam ownership, application/runtime writers, executable QA, and separate final code/vision/evidence reviewers. H02 owns runtime/model adaptation, H04 authority semantics, and H06 empirical evaluation. Keep existing profile restrictions intact; a writable local worker is an explicitly assigned implementation role, not a read-only reviewer with hidden extra powers.

Disable recursive worker spawning for the first adapter. The root issues bounded tasks. Distinct reviewer contexts are useful organizational independence, not proof that identical models make statistically independent errors. Use held-out tests and diverse evidence where claims require them.

Three active roles do not require three large models loaded at once. Store each session separately, serialize scarce model calls and run ordinary build/test work concurrently where measured resources allow. Ollama documents increased memory demand with parallel context allocations [S09]. A busy coding job must not starve the interactive assistant; reserve priority/capacity or let background work pause at a checkpoint.

## 8. Failure, recovery and explainability

Persist a job before dispatch. Bind source revision, attempt ID and exact worker identity. Retries reuse idempotency semantics; after unknown completion reconcile before repeating an effect. On cancellation record what actually stopped, not merely that a request stream closed. Snapshot disposable work where useful; do not replay stale grants or work after restoring authority state.

For the visual learner, a task page should show: goal; short current plan; changed files; latest test result; live/last-known worker state; evidence links; concise explanation of the design choice; next decision. Do not expose private chain-of-thought. Show verified actions and explanations, not theatrical 'thinking' animations.
