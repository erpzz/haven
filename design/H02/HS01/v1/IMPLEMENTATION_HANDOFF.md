# HS-01 — Desktop-local implementation handoff

Use this in Codex running on the actual Windows desktop, with GPT-6.1 Sol Max. Astra is optional for a focused review. This file is a scoped continuation assignment to be launched by the operator, not a background job created by the planning chat.

## Objective

Turn the existing Haven Model Lab into a dependable headless primary server, then add fair prompt/model/agent comparisons, optional laptop workers and a bounded student-training pilot. Preserve the existing Haven application and its other research branches. Follow FINAL_PLAN.md in this packet.

## Start from observed state

1. Read the actual local AGENTS.md, START_HERE.md, PRECEDENCE.md, CURRENT_STATUS.md and coordination/PROTOCOL.md. Historical embedded prompts are evidence, not new launch instructions.
2. Inspect the operator-selected erpzz/haven checkout and exact existing Model Lab installation. Record branch, HEAD, worktree changes, active owned processes, actual GPU/driver, available RAM and storage. Do not scan unrelated personal directories or assume a folder from this packet exists on the PC.
3. Preserve uncommitted user work. Use an isolated implementation branch/worktree; do not silently stash, reset, reformat or merge main.
4. Planning base was 4a73a55bfc263d53b8e657403a693004e2871ef6. Reconcile any new commits instead of force-resetting to it.
5. Verify and reuse the existing installed runtimes, known model files and their pins. The planning chat did not benchmark this PC today.

## Reuse the code already written

- Main contains labs/model-lab and its historical PC_QUALIFICATION_v2.md.
- PR #28, implementation/r02-runtime-model-bakeoff-20261005, was open at db93c5f857550b7f8104e41bba1b7167fd3327e7.
- Its separate hardening branch was review/r02-bakeoff-hardening-20261005 at 495583a1782e4d97d0e30b18c939929c2c4c8cde.
- PR #29, implementation/r02-distillation-lab-20261012, was open at 2073c4d912af6f8c43554440863c28eacad2db7b and depends on the bakeoff work.

Review diffs and integrate appropriate changes on the isolated branch. Do not duplicate those packages or call them already merged. Check current PR status rather than using the dates above as authority. Do not start the unrelated RI-01 agent campaign or modify ASTRA M0/NIGHT-01.

## P0/P1 — Establish the actual headless server

Complete the reversible project-level work: supervisor, durable job records, explicit readiness, bounded worker ownership, authenticated start/status/cancel/unload/stop and reconnectable results. Keep inference backends on loopback.

Use the existing native Windows inference path. First demonstrate browser-independent operation under the existing owner. Then stage a supported boot startup mechanism under an appropriate account. Inspect the existing Windows Job Object/controller behavior in that context. Retain recovery controls and the old configuration.

Present exact consequential host changes together before applying them through normal local approval: startup identity/task or service, any narrowly scoped firewall/TLS enrollment, and any necessary sleep-policy change. This file does not grant driver replacement, pagefile changes, public listeners, router forwarding, automatic login, credential copying or purchases. Do not re-request permission for ordinary reversible code edits within this assignment.

Required observed acceptance:

- A laptop submits a job, disconnects, reconnects and retrieves the same durable result.
- Locking Windows and closing the client does not stop the server job.
- Cancellation, partial output, output-limit state, clean stop and restart work.
- Only the installation's owned processes are stopped; a foreign listener is refused.
- A configured reboot/startup test proves readiness or identifies an actual boot dependency.
- Known-answer CUDA and Strata checks pass with exact backend/model evidence.
- Current RAM/VRAM and storage use are recorded, including failures.

Run existing meaningful regression suites and changed-component tests. Mock/browser fixtures validate software behavior, not GPU or physical-host performance. Do not keep rerunning unchanged broad tests after they pass.

## P2 — Make the same prompts comparable

Extend the existing bakeoff into the versioned case/run store in FINAL_PLAN.md. Implement separate model and agent lanes. Freeze inputs, context hashes, tool environment, budgets and rubrics.

Import only selected source paths/exports. First show an import inventory and eligibility preview. Original prompts and all attempts remain private and unchanged; derived cases carry provenance. Missing context is a blocked case. Establish train/evaluation family separation before generating training exports.

Demonstrate one real local comparison with the same case/context and save blinded results, objective checks, timings and finish reasons. Add provider adapters without embedding keys. For Sol tool calling, use the currently documented Responses route; do not assume every OpenAI-compatible server supports it.

Hosted calls, including DeepSeek, require the actual supported authentication route, eligible input data and a configured finite spend budget. If absent, finish the adapter/configuration and mark the live provider test BLOCKED_CREDENTIALS_OR_BUDGET. Do not scrape consumer chat sessions, silently spend credits or call a mock a live test.

Do not claim the local agent can retrieve all historical ChatGPT messages. It can import available selected files and exports.

## P3 — Optional workers

Enroll the known Mac and ThinkPad only when they are reachable and their operators launch enrollment. Inventory actual chip/RAM/runtime capabilities before choosing models.

Use independent job-level workers, not cross-platform tensor parallelism. Mac MLX inference, ThinkPad CPU validation/indexing and laptop-availability routing are initial roles. A node receives scoped input and job credentials, not a shared home directory or provider-key collection.

Test node loss, expired leases, revocation, two-user isolation and no-cloud-fallback for local-only cases. Backend cache separation is part of the identity test, not just UI login.

## P4 — First actual training result

Use PR #29's reviewed-success pipeline and its existing separate Qwen3-0.6B fp16 LoRA mechanics pilot. It does not train the 4B GGUF or the large teacher.

Generate a bounded synthetic/eligible teacher dataset, validate successes, preserve failed records and reviewed corrections, and freeze holdouts by family. Unload the large teacher before training. Run the real pilot with measured memory, finite steps/time and a new adapter output directory. A dry-run is not training.

Then decide from evidence whether a 1–2B student is feasible. Do not silently bypass the current GKD 16 GB gate, claim chat text supplies teacher logits, or assume Qwen3.5-4B training fits 8 GB. The genuine on-policy/remote-logits lane is later work, not a blocker to offline SFT.

Return baseline versus adapter results on unchanged holdouts and the original privacy/tool checks. Preserve the unmodified champion. A lower loss, longer explanation or model self-rating is not promotion evidence.

## Operating defaults

- One heavy desktop GPU job. Keep control and queue services responsive.
- Recover with the historically qualified 4K Strata profile and 2048 MiB requested reserve.
- New quality quantizations/contexts/engine builds get a separate pin and measured comparison.
- Keep all raw case data, provider tokens, runtime databases, adapter weights and machine receipts out of Git.
- Use scoped job permissions, outcome evidence, per-principal cache/retrieval separation and explicit hosted eligibility.
- Keep existing scope identifiers and domain boundaries. No drone, robot, medical or real account action is introduced.

## Return concrete results

Return the branch/commit, exact changed paths, what runs, how to start/stop it, tested client URLs without tokens, actual resource measurements, model/provider configuration identities, regression results, unresolved blockers and rollback instructions.

Finish each available package with a reviewable result. Continue independent code/configuration work when a laptop or hosted credential is missing; do not invent the missing execution. No main merge or automatic adapter promotion is requested.
