# RI-01 records and deliverables

Templates are schemas of the campaign record, not prefilled evidence. Never insert dummy passes or agent IDs. JSON/JSONL must parse; UTC timestamps and exact commits accompany observable state changes.

## Task dispatch
`task_id`, `role`, `objective`, `base_commit`, `hard_inputs[]` (path, commit, hash, required claims), `soft_inputs[]`, `allowed_output_prefix`, `deliverables[]`, `budgets`, `stop_conditions`, `reviewer_role`, `actual_agent_id`, `started_at`, `status`.

## Per-handback REVIEW.md
Source/edition and exact commit; scope read; input fidelity; supported findings; source-verification limits; scientific/engineering concerns; conflicting contracts; repeated work; scope omissions; test equivalence; modality actually inspected; severity-ranked required changes; disposition; affected dependents. Sign with actual role/task ID, not fabricated personal identity.

## Research handback
Use original handoff headings when available: metadata, decisions, evidence, interface changes, acceptance, risks/open questions and next package. Add the one-page summary, source register, actual-vs-proposed table, maturity ladder, affordable alternatives, exact dependency use, proposed experiment and current tool/asset limitations. Preserve negative evidence. Full report files remain in the assigned task directory; the final agent message is at most roughly 500 words plus artifact paths.

## INPUT_USE.json
Array of records: `upstream_task`, `source_ref` (repo, commit, path, optional lines/claim_id), `artifact_sha256`, `finding`, `disposition` (REUSED/AMENDED/REJECTED/UNRESOLVED), `downstream_section`, `design_effect`, `reason`, `review_state`. Naming a prior thread without a concrete effect is not completion.

## Consultation record
`question_id`, `timestamp`, `from_task`, `from_agent`, `to_role`, `to_agent`, `source_refs[]`, `question`, `alternatives`, `answer`, `answer_refs[]`, `decision_owner`, `resolution`, `affected_tasks[]`, `remaining_dissent`. Record only messages actually sent/received. Root serializes this log.

## Modality record
`asset_id`, `source`, `sha256_or_source_version`, `rights`, `original_or_derived`, `parent_asset`, `transforms[]`, `inspection_mode`, `tool_and_model_if_exposed`, `page_frame_or_interval`, `observations`, `uncertainties`, `status`. Valid examples of status: INSPECTED, TOOL_UNAVAILABLE, SOURCE_UNAVAILABLE, DOCUMENTATION_ONLY. Direct media inspection and Haven capability qualification are separate.

## Final integration files
`ARCHITECTURE.md`, `CONTRACT_CROSSWALK.md`, `DECISIONS.md`, `VISION_COVERAGE.md`, `MODALITY_MATRIX.md`, `EVALUATION_PLAN.md`, `IMPLEMENTATION_QUEUE.md`, `RISKS_AND_DISSENT.md`, `SOURCE_USE_INDEX.json`, and `DEPENDENCIES.json`.

Every work package includes owner, why useful, exact inputs, allowed paths, implementation boundary, prerequisites, expected tests, cost/resource ceiling, stop condition, review owner and explicit AUTHORIZATION_REQUIRED. Include short ready-to-paste future coding assignments, but do not run them.

## MORNING_REPORT.md
1. Actual start/end, host class and runtime (public-safe).
2. Actual subagents spawned, role/task receipts and results; no fictional team.
3. Existing research reviewed, accepted-for-synthesis, amended or held, with exact versions.
4. Remaining research actually completed; upstream findings used and where.
5. Multimodal tools actually exercised, blocked modalities and future capabilities not tested.
6. Proposed integrated design and important conflicts/reversals.
7. Independent vision/code/evidence review outcomes, with unresolved findings.
8. Files changed, local versus remote publication, commit/PR and verification.
9. Protected work left unchanged and tests not run.
10. Remaining tasks, budget stop, smallest operator decision and exact next package.

## Resume
Resume the SAME run only after checking remote/working-tree state and exact prior checkpoints. Do not rerun accepted work unless its inputs changed. Interrupted work is unknown until reconciled; do not spawn duplicate active agents. Re-establish native capabilities and public-media tools. New launch budget is explicit. Preserve source edits and all prior failure records.
