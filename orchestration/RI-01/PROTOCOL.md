# RI-01 coordination protocol

## One supervisor; distinct specialist agents
The root owns scheduling, task state, Git publication and stopping. The integration manager owns proposed design synthesis. Authors own their report artifacts; reviewers own their findings. Vision, code and evidence review are separate actual agent assignments from the authors they assess. Roles do not imply separate continuously running services. Keep at most three open child threads; persist and close idle ones rather than occupying all slots with supervisors.

Use native creation/message/wait/interrupt/close tools actually exposed by the harness. Do not hardcode undocumented tool JSON. Log the returned real ID and role. A fresh task can use an existing qualified role but must have a distinct task ID. Do not make a single agent claim it is its own independent reviewer. Children do not recursively delegate. Account for the root's and children's usage where exposed.

## Durable layout
Create `campaigns/RI-01/<run-id>/`:
- `state/run.json`, `state/tasks.json`, `state/agents.jsonl`: root-owned metadata and lifecycle records.
- `inputs/`: source inventories, exact commit/file/blob records, source-rights notes, immutable derived input packets.
- `reviews/<task-id>/`: reviewer findings and exact reviewed revisions.
- `research/<task-id>/`: the author's full handback, sources, experiment and INPUT_USE records.
- `integration/`: architecture, contracts, decisions, requirement/multimodal matrices and proposed work packages.
- `consultations.jsonl`: root-written question/answer/decision records with agent IDs and source refs.
- `MORNING_REPORT.md`, `RESUME.md`, `DELIVERY_MANIFEST.json`: final or interrupted-run receipt.
Keep source media private/local unless its license and publication need are explicitly established. Reports may link public source assets without copying them.

Only the root writes shared state, runs Git or commits selected paths. Writers get distinct report prefixes or independently verified worktrees. Worktree/path rules and TOML sandbox settings are not cryptographic isolation; verify actual parent permissions and prevent shared-index edits. Never clean/reset another workspace. Commit after each completed task or wave, excluding credentials, runtime databases and unreviewed assets.

## Task record and state machine
Each task has: ID, role, objective, input revision manifest, hard dependencies, soft dependencies, expected artifacts, allowed path, resource allowance, priority, assigned real agent ID, status, attempt count, reviewer, findings and next action.

`QUEUED -> READY -> RUNNING -> DRAFT_READY -> IN_REVIEW -> ACCEPTED_FOR_SYNTHESIS`.
Alternatives: `CHANGES_REQUIRED`, `BLOCKED_INPUT`, `BLOCKED_TOOL`, `HUMAN_DECISION_REQUIRED`, `SUPERSEDED`, `CANCELLED`, `PARTIAL_BUDGET`.

ACCEPTED_FOR_SYNTHESIS is an internal campaign status, not operator approval, experimental success or production permission. A hard dependency is satisfied only by the exact accepted artifact/input revision. A skipped duplicate requires an equivalent-source mapping and review. Soft dependencies permit work with explicit assumptions, followed by a focused reconciliation task when the result arrives. Never turn an absent field into an implied approval.

## Scheduling and dependency reuse
Refresh repository state at intake and wave boundaries. Freeze source versions within each task. Add a REVIEW-<id> task for every new substantive addition; publication duplicates get identity checks, not redundant literature review. Give new research only the relevant source sections, source links and accepted decisions; do not fork the full parent history by default when the harness offers a narrower context choice.

Before dispatch, verify each hard input exists/readable and record hash/commit. Each returned INPUT_USE row must name upstream finding, exact version, downstream section, accepted/amended/rejected use and reason. Evidence auditor checks this crosswalk. Findings that alter a required input trigger bounded invalidation of dependents, not silent reuse of stale conclusions. Cap rework and keep original drafts.

Keep resource slots for ready work and consultations. Do not wait for an idle reviewer when it can be resumed later. If all remaining tasks are blocked, list exact missing decisions or tooling and stop; do not invent new tasks to fill time. New tangents go to the opportunity backlog unless they materially close a scoped dependency.

## Actual consultation, not staged debate
A message contains: question ID; asking task/agent; target role; exact input/contract reference; one decision needed; evidence and alternatives; affected tasks; requested response scope. The root relays it to the real target or dispatches a bounded consultant if needed. Answers retain author identity and citations. Consultations can proceed without interrupting unrelated work. Maximum two clarification rounds per question; persistent dissent is recorded for integration or operator decision.

Do not publish private hidden chain-of-thought. Keep observed tool actions, compact rationales, evidence, alternatives and decisions. Agreement by several models is not a substitute for measurement or independent source verification.

## Independence and final reviews
Researcher != its handback reviewer. Integration manager != final vision/code/evidence reviewers. Reviewing agents may inspect each other's published evidence but cannot silently edit it. A fresh isolated review context reduces contamination; it does not establish statistical independence of model errors. Freeze the candidate before final reviews; changes afterward require affected rechecks. Unsupported strong claims or privacy leaks block the relevant promotion, not unrelated public research.

Code review must name real code and tests. Where only docs exist, report NO_APPLICATION_CODE_CHANGED. Where N1/M0 code is not provided, report CODE_NOT_AVAILABLE and do not claim a rerun. Code reviewer checks configuration and future implementation contracts, including the difference between terminated work and suppressed output.

## GitHub coordination and conflicts
Read pending research from exact PR-head refs even when absent from main. Do not equate a failed default-branch search with missing project evidence. Include PR number, head commit and publication state. Preserve originals; integration records may reference them without duplicating them. When exact archived material is recovered, import only explicit allowed bytes in a reviewed campaign commit with provenance.

Before push, fetch the campaign remote ref. No force push, unrelated merges, workflow triggers or auto-merge. If main advances, compare affected paths and revalidate inputs; do not wholesale rebase another agent's branch. The root opens one consolidated campaign PR. Existing source PRs remain separate pending review. Public issue updates are concise progress receipts, not authorization for new scope.

## Stop/resume
Checkpoint run budget, completed task revisions, open questions, real child states and next ready tasks. Stop/close owned children through supported tools and report residual unknowns honestly. A cancelled session is not proof all external work stopped. No detached services or automatic reschedules. RESUME.md re-verifies source and role capabilities, does not replay already accepted work, and requeues only interrupted or invalidated tasks with fresh run limits.
