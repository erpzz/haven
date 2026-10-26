# Specialist handback

Thread / owner / task ID: HS-01 / H02 intelligence continuation; operator request on 25 October 2026. Related work: R02, Model Lab, PR #28 and PR #29. No new agent campaign launched.

Input repository version and hashes: erpzz/haven main 4a73a55bfc263d53b8e657403a693004e2871ef6; bakeoff db93c5f857550b7f8104e41bba1b7167fd3327e7; bakeoff review 495583a1782e4d97d0e30b18c939929c2c4c8cde; distillation 2073c4d912af6f8c43554440863c28eacad2db7b. See SOURCES.json for source blob identities.

Requirements covered (retain IDs): additive R02 intelligence/runtime scope and ARCH-R02-001 direction. All existing REQ/AT/EX and Rxx-to-Hxx mappings retained. Missing COVERAGE.md prevents asserting a complete requirement-ID reconciliation.

Actual work performed versus proposed: inspected current main, branches and PR states; read relevant source/evidence; checked current primary model/framework documentation; produced an implementation-ready architecture and desktop-local handoff. No models, credentials, devices, services or training jobs were started.

Owned paths changed: new design/H02/HS01/v1 packet only. No preserved baseline or existing v1 handback is rewritten. No shared runtime schema or application file changed.

Publication classification: sanitized design and synthetic examples only. Hardware classes are operator-reported or already recorded in the inspected qualification report. No credentials, host identifiers, private prompts, household recordings or raw runtime data included. Repository metadata currently reports private while historical prose says public; visibility is not changed and the packet follows the stricter publication boundary.

## Decisions

Keep the existing Windows desktop as primary compute, thin Haven coordination and independent optional laptop workers. Reuse Model Lab and review/integrate the existing unmerged bakeoff/distillation work. Separate model/agent comparisons. Prefer offline verified teacher-answer SFT before genuinely on-policy token supervision. Use Sol 6.1 Max for implementation; Astra review is optional.

This finalizes the preparation requested by the operator. It does not claim operator acceptance of every proposed interface or authorize execution merely because a document exists.

## Evidence

Read pinned root AGENTS.md, START_HERE.md, PRECEDENCE.md, CURRENT_STATUS.md, coordination/PROTOCOL.md, THREAD_STATUS.md, HANDBACK_METADATA.md, DECISIONS.md, original HANDOFF_TEMPLATE.md, original intelligence chapter, Model Lab README and PC_QUALIFICATION_v2.md.

Read bakeoff README on its implementation and review branches and distillation README plus train_sft.py/train_opd.py at their pinned branch head. Historical Library master-design, R02 assignment and low-cost research were read as context, not live execution authority.

The PC report records historical real inference qualification. PR #25/#26 are merged; #28/#29 are open as observed. Main currently lacks baseline/cumulative-v1.0/scope/COVERAGE.md. Training completion, present machine state, optional node performance and new hosted evaluations are not established.

## Interface changes

Proposed only: node/lease metadata, durable jobs, scoped case/run records, comparison runners and dataset/promotion lineage. Existing shared contracts are unchanged. Fields and identity/error/cancellation/resource semantics are specified in FINAL_PLAN.md for subsequent implementation review.

## Acceptance

Executed in the planning workspace: documentation consistency checks, source-identity manifest construction and remote publication verification when recorded by the publishing turn.

NOT_EXECUTED: Windows headless/reboot tests, laptop enrollment, model/agent comparisons, credentialed provider calls, dataset import, GPU training and adapter promotion. No second AI review or physical qualification is claimed.

## Risks and open questions

Present memory/storage and exact laptop inventories require P0 observation. Current LAN access is explicitly not TLS/internet-ready. PR #28/#29 need integration and runtime qualification. Training and inference have different memory envelopes; the existing GKD gate must not be bypassed as a substitute for evidence. Data deletion/consent extends into caches and derived datasets.

## Next package

Launch IMPLEMENTATION_HANDOFF.md in Codex on the actual desktop. Complete P0/P1, then comparison and optional-node work, then the student pilot under explicit local execution and resource settings. Consequential host changes and hosted spend receive concrete local approval; reversible scoped code work proceeds. Return actual results and rollback instructions. No main merge or self-promotion.
