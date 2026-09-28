# Communication protocol

## One durable hub, separate execution

The repository holds documents; issues hold questions and task receipts; PRs hold proposed changes. Agents do not need direct chat-to-chat messaging. Reading an issue is explicit work, not a subscription that wakes a stopped model. No bot, webhook, scheduled job or continuous agent is created by this protocol.

## Work cycle

1. The operator/integrator selects one prompt and its issue. An issue records the scope, owner, allowed paths and stopping point.
2. The worker records the actual main commit and relevant source/contract versions. Read before proposing changes; a file title is not evidence of its content.
3. Work in an isolated branch/check-out. Commit only allowed files. Imported historical directories are read-only.
4. Questions that affect another owner go on the relevant issue, using the short question template below. The worker may continue independent portions with explicit assumptions; it cannot invent an approval.
5. Deliver a new version under the owned destination with handback metadata and the original handoff headings. Open a PR and link it to the issue.
6. The integrator and required domain reviewers record accept/amend/defer. The operator approves consequential implementation and scope changes. Do not merge your own recommendation as its acceptance.
7. A new coding package references the accepted decision, exact contract revisions and a base commit. It is separate from the research PR.

## Required question format

- Task/research ID and current base commit
- Exact contract/path/version in question
- One precise decision needed
- Evidence and viable alternatives
- Downstream work blocked, and work that can continue
- Required owner and suggested answer-by gate (not an invented deadline)

Use issue comments for these small questions; do not paste entire reports repeatedly. Link the exact artifact. Agent prose is never an authenticated human grant.

## Status vocabulary

`UNASSIGNED`, `READY_FOR_ASSIGNMENT`, `IN_PROGRESS_REPORTED`, `BLOCKED`, `HANDBACK_AVAILABLE`, `REVIEW_RECOMMENDED`, `OPERATOR_APPROVED`, `IMPLEMENTED_REPORTED`, `EXECUTED_PASS`, `EXECUTED_FAIL`, `PENDING_OPERATOR`, `NOT_EXECUTED`, `SUPERSEDED`.

Every state includes who reported it, the source/commit, time and scope. A test-double pass is not real-device acceptance. An issue closure alone does not qualify a system.

## Versioning and conflicts

Never overwrite a v1 handback. Add v2 plus a change summary and evidence mapping. Preserve negative findings. Only H00 proposes edits to shared contracts/requirements, after affected owners review. Imported originals remain unchanged.

Branch example: `research/r03-v1`. PR example: `[R03][v1] Permission and publication semantics`. Branch names are conventions, not grants.

## Unequal tool access

A thread with read access but no write access returns a packet with intended paths and hashes marked NOT_UPLOADED. One designated importer publishes it and links the verified commit/PR. Never ask for tokens in chat. A public repo can be read without granting the reader write permission.

## Public-data boundary

Keep real medical samples, household recordings, network inventory, private account IDs, credentials, runtime databases and employer data outside this public hub. Do not make a public issue into a place to collect those inputs. Document a separately approved private evidence location only by nonsecret logical reference.

## Execution boundaries

The active M0 and NIGHT-01 workspaces are separate. Research workers do not change either. Coding agents use disjoint branches/worktrees where permitted and retain before/after evidence. No automatic merging, package installation, billing, device action or continuous polling follows from adding a file here.
