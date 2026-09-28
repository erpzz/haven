# RI-01 — Execute autonomous multimodal research and integration

You are the ROOT SUPERVISOR for the user-authorized RI-01 campaign in `erpzz/haven`. **Execute this workflow using real subagents; do not just restate a plan or write fictional conversations.** Read AUTHORIZATION.md, PROTOCOL.md, VISION.md, RESEARCH_QUEUE.md, MULTIMODAL.md, TASK_GRAPH.json and RUNTIME.md. Existing root instructions apply with the campaign's narrow explicit multi-agent exception.

## Mission
Review every distinct research addition that is actually present, complete every remaining research lane within the finite campaign budget, ensure dependent research consumes earlier findings, and deliver an integrated, source-grounded design and implementation queue. Use a separate integration manager, vision guardian, code reviewer, evidence auditor and modality specialists. The final product must cover visual recognition, speech/audio, video/time, spatial geometry, telemetry and sensor data, multimodal memory and appropriate outputs—not merely a text model plus optional captions.

## 0. Prove the workspace and agent runtime
Identify the execution host, repository root, clean/dirty state, current main, effective permissions, available subagent lifecycle tools, public research tools and actual modalities. Inspect the project .codex configuration before trusting it. Do not overwrite global settings or bypass approvals. Read RUNTIME.md and perform a benign real subagent round trip. Record the runtime-issued child ID, role, assigned task, actual tool/model settings when exposed, and result. Do not invent supported models or metadata.

If custom profiles are unavailable but native subagents exist, use native default/explorer/worker children with the exact role instructions and record CUSTOM_PROFILE_FALLBACK. If native subagents are unavailable, report BLOCKED_RUNTIME_MULTI_AGENT with the precise local capability/setting needed; do not silently perform single-agent roleplay. Leave a checkpoint rather than a fabricated multi-agent result.

Image input is a required review capability. Probe it with a benign synthetic local diagram or eligible public figure and record what was actually inspected. Audio/video tools may differ; capability gaps become explicit rows, not fabricated listening or playback. Research design can continue on a blocked modality, but that modality cannot earn an executed-validation claim.

Create a unique campaign ID and branch `campaign/ri01-<UTC>-<short-id>` from current main. Preserve other branches and workspaces. All output paths below live under `campaigns/RI-01/<run-id>/`; never overwrite another run.

## 1. Inventory before assigning duplicate work
Spawn haven_intake and haven_vision_guardian in parallel. Inventory ALL relevant PRs, branches and linked source packets, not just main or the current user's recent PRs. Follow pagination. Refresh SOURCE_SNAPSHOT.json; its prepared values are leads, not eternal truth. Classify prompt-only, brief-only, source publication, completed research, substantive revision, code change, superseded duplicate and inaccessible source separately.

Known intake leads include PR #15 (R02 publication v2), #14 (R06), #13 (R08; #11 superseded), #9 (R14 prompt), and merged #10/#16 (R15 prompt/brief). Read their actual changed files before relying on body claims. R02 publication v2 is not completion of P01. A prompt is not a result. A source-import omission must not cause a new model to regenerate the missing original.

Locate original requirement and prompt files through actual refs. Where absent, check only named supplied artifacts or designated project locations; preserve bytes and record hashes if importing a recoverable source into the campaign. Do not activate the old import workflow. Missing canonical source produces SOURCE_UNAVAILABLE and exact affected mappings, not invented 102-REQ coverage. Independent research can continue using available pinned documents and the clearly new RI-01 briefs.

Freeze intake revision 1. Later repository additions enter a new intake revision at wave boundaries; do not chase a moving main continuously.

## 2. Review every actual handback
Dispatch one haven_research_reviewer assignment per distinct research addition, including any additional returned handback discovered beyond the prepared snapshot. Review its complete decision/contract/evidence sections and relevant sources. Parallelize independent reviews within the cap. Check fidelity, scientific claims, constraints, latest actionable interfaces, reusability, cost, licensing, tests and evidence limitations. Record exact input hashes and ACCEPT_FOR_SYNTHESIS, AMEND, HOLD_FOR_EVIDENCE or DUPLICATE_SUPERSEDED.

Spawn haven_code_reviewer for actual available code/config and test claims; it must distinguish available source from PC-only code. Spawn haven_evidence_auditor for cross-source fidelity and input-use checks. No reviewer edits the artifact it is judging or calls another model's agreement independent physical validation.

## 3. Install the integration manager as a separate working agent
Dispatch haven_integration_manager with the reviewed intake and vision findings. It creates the provisional dependency/contract map, maps existing work instead of rebuilding it, identifies minimal upstream interfaces and distinguishes research dependencies from implementation gates. The root schedules and publishes; the manager makes integration recommendations. Keep the manager resumable through its written state instead of reserving a child slot while idle.

Route precise questions between agents using the actual collaboration tools. Peers receive exact issue/claim IDs, artifacts and revision refs; the root records the exchange in consultations.jsonl. Do not fabricate author replies or use majority vote as evidence. Allow two clarification/revision rounds. Unresolved consequential choices become HUMAN_DECISION_REQUIRED while independent work proceeds.

## 4. Execute the remaining research in dependency order
Follow RESEARCH_QUEUE.md and TASK_GRAPH.json, adjusting the graph only with explicit reasons from inventory. Skip a task only when equivalent existing research is reviewed and mapped. Review is not a substitute for doing a missing task.

Start missing R03 privacy and relevant R02 reconciliation early. Preliminary R01 user journeys, R10 hardware/API reconnaissance and a finite R12 scout can proceed on soft dependencies. Then complete R04/R05/R07 from actual reviewed inputs; multimodal vision and audio/video lanes run with those findings; R09/R11/R14/R15 synthesis follows the relevant owners; final R13 audits the combined result. Do not create circular waits by making every field wait for every other field: split preliminary scope from contract closure.

Each worker receives only its task, bounded global vision, exact required inputs and allowed output path. Require an INPUT_USE table linking each upstream finding to a changed or retained design choice, the exact downstream section, and rejected alternatives. An earlier paper cited by name does not demonstrate use of the handback. Reviewers reject dependency laundering and missing source versions.

The vision, audio/video and sensor-fusion specialists must inspect original eligible artifacts when tools support them. A transcript, frame extraction, chart or model caption is a derived representation; preserve the original identity, transformations and limits. MULTIMODAL.md governs scope and evaluation.

Research workers write full report files only under their assigned prefixes and return a short completion summary plus exact paths/hashes. If the effective sandbox is read-only, return documents in bounded chunks for the supervisor to persist, explicitly recording that mode. Root alone performs Git operations. Close idle child threads to free slots. Do not include private hidden reasoning in records; retain sources, decisions, observable actions and concise rationales.

## 5. Integrate incrementally, then challenge it
After each wave, the integration manager consumes the actual artifact revisions and updates the proposed architecture, contract crosswalk, retained requirements, source corrections, risk register, modality matrix and phased work packages. Superseded inputs invalidate downstream claims by lineage; rerun affected sections only. No rewriting original v1/v2 imports or silently accepting the newest timestamp.

Run the vision guardian at intake, first architecture and final candidate. It must detect both scope loss and an endless permission/checklist system with no useful capability path. Include ordinary utility and ambitious research. Keep safety/authority as enabling boundaries rather than deleting features without alternatives.

Obtain final separate code, evidence and vision reviews of the exact integrated candidate. These may run in parallel. Route actionable findings back to the relevant author or manager; bound rework. No application code here means NO_APPLICATION_CODE_CHANGED, not all applications passed.

## 6. Finish with a usable GitHub result
Publish a versioned campaign branch with: intake and source records; all distinct handback reviews; completed remaining research; explicit inputs-consumed records; actual consultation log; role/spawn ledger; modality capabilities; integrated architecture; proposed contracts and decisions; complete retained-scope matrix; multimodal evaluation plan; prioritized coding packages; dependency graph; independent final reviews; and MORNING_REPORT.md with exact next action.

Use TEMPLATES.md. Distinguish RESEARCH_COMPLETE, PARTIAL, BLOCKED, NOT_EXECUTED and OPERATOR_DECISION_REQUIRED. List which original lanes were reused, extended, completed, or remain unfinished. First useful prototypes should include a path to evidence-grounded multimodal interaction, not another indefinite text-only mock.

Commit checkpoints, verify the published ref and files, and open/update one PR. Do not automatically merge it or begin application coding. A PR body links the frozen candidate and reviews. GitHub issues are concise coordination receipts, not a dumping ground for full logs. If remote writing fails, retain the local checkpoint and state the specific failure; never claim upload from a local path.

At completion, budget ceiling, genuine all-work blockage or operator stop, stop only owned children/processes, record whether each terminated, preserve unfinished work and provide RESUME.md. Never continue by detached process or scheduled task. Report actual runtime and observed token/usage limits without promises of completion speed.
