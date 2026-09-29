# Proposed next proof — local coding worker that returns verifiable results

PROPOSED_ONLY. Do not execute under IP-01, borrow its model allocation or assume a new grant from this document. No extra native agents are running for HW-01.

## FW-0: intake and contracts

Root obtains the actual current application handoff and operator-granted workspace. Verify OS, disk, available CPU/RAM/VRAM, thermal/competing-load constraints, installed runtime versions and supported local-agent API. Record model artifact, quantization, context, tool schema and prompt/template identity. Public records use abstract host IDs, not machine inventory/secrets.

The separate H00 integration manager proposes the small JobSpec/ArtifactSubmission adapter mapping to I01–I07. H02 reviews runtime admission/cleanup; H04 reviews authority. Do not redesign the entire intelligence stack. Keep the candidate OpenCode/Aider choice empirical where current context guidance conflicts.

## FW-1: one real job on an expendable source copy

Use a small synthetic repository or specifically approved copy. Ask the worker to add a JSON evidence-export feature with its unit tests and a simple UI affordance. It must inspect existing code, create the implementation, run the relevant commands, fix ordinary failures and return the actual diff plus results. No direct merge or production rollout.

Begin with the smallest model/context that actually meets the chosen harness profile; do not reduce a documented requirement silently. If the rich harness cannot fit, record it and compare the separately scoped smaller edit baseline. No automatic hosted fallback or model replacement outside the eventual grant.

## FW-2: independent verification and negative cases

Separate executable QA checks actual source state, API behavior and rendered UI where applicable. Include a failed test, no-op fake completion, contradictory repository instruction, stale base revision, duplicate job, worker crash and cancellation. Source documents and tool output must not override the job's authority. Reconcile unknown state before replaying effects.

The independent reviewer receives candidate/fixture hashes and observed command outputs, not just the implementer's prose. A copied report or screenshot cannot prove that a command ran. The worker has no write access to QA expectations where technical enforcement is available; otherwise honestly label the weaker evidence class.

## FW-3: feed evidence and a proposed skill into Haven

Submit an ArtifactManifest containing the job/base/candidate IDs, diff reference, test commands/exit codes, logs/screenshots, dependency changes, resource/attempt counts, known failures and proposed lesson. Verify idempotent ingestion. A proposed skill must retain conditions and verification; failed attempts remain retrievable. No weight training is implied.

Root/H00 routes findings back to the author for bounded repairs. Freeze the exact candidate before final review. Distinct code and evidence dispositions apply to that candidate; the vision guardian checks useful positive behavior and whether this remains one component of the broader Haven goal. Do not spawn every specialist for a small code change.

## FW-4: operational benchmark before buying

Compare 5–10 small, independently specified tasks across a limited model/harness setup. Use useful outcomes, correct tests and observed tool actions rather than conversational style. Freeze scope and resource ceilings before attempts, retain every failure, and distinguish local capability, tool configuration friction and model reasoning failures.

Proposed decision questions: Does the small local worker complete any useful class reliably? Does 64K context fit with the chosen tool suite? Does foreground Haven remain responsive? Is the limitation memory, compute, context management or task decomposition? Does a larger-memory machine actually improve the workload enough to justify its total cost?

Do not use an arbitrary pass percentage as a production guarantee. Basic authority/cancellation/data-boundary violations block the corresponding promotion even if other tasks work. Missing coverage is unknown, not success.

## FW-5: release and learning handoff

Deliver a reproducible setup, pinned configuration, start/stop and rollback instructions, executable test evidence, a reviewable branch, open failures and a capacity report. A staging promotion requires its own grant; production release remains separately controlled. Stop or hand over owned services exactly as authorized rather than leaving an indefinite job running by default.

## Roles and efficient scheduling

Root schedules and publishes. H00 remains distinct from root and owns integration decisions. Existing application/runtime implementation roles can use the local worker after its capability probe. H06 executable QA runs tests; code/evidence reviewers inspect frozen outputs; the vision guardian checks actual usefulness. Three roles may take turns on one inference endpoint; there is no requirement to load one model per role. Native Codex role/thread caps and the local service's model-request limits are different and must be recorded separately.

Routine file edits, local builds and authorized failed-test repairs should proceed without repeated operator questions. Stop for an actual missing permission, unsafe/unowned side effect, unresolved mandatory input or exhausted resource envelope—not merely because the task requires writing code.
