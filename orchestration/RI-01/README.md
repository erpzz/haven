# RI-01 — Autonomous research review and integration campaign

**Setup version 1, 2026-09-28.** This directory configures a future Codex campaign. Publishing it does not start that campaign. Start by pasting [START_CODEX.txt](START_CODEX.txt) into a Codex session opened on this repository.

The supervisor uses **real Codex subagents** to review each distinct research addition, perform the remaining research, consult through scoped messages, and assemble a coherent design. Separate integration, vision, code and evidence agents provide checks. These are development agents, not Haven's eventual runtime architecture.

## Read in order

1. [Authorization and boundaries](AUTHORIZATION.md)
2. [Master execution prompt](MASTER_PROMPT.md)
3. [Coordination, dependency and publication protocol](PROTOCOL.md)
4. [Cumulative vision](VISION.md)
5. [Task graph and concrete research scopes](RESEARCH_QUEUE.md)
6. [Full multimodal design and evidence requirements](MULTIMODAL.md)
7. [Observed source snapshot](SOURCE_SNAPSHOT.json), refreshed at launch
8. [Output templates](TEMPLATES.md), [runtime preflight](RUNTIME.md) and [operating checklist](OPERATING_CHECKLIST.md)

## Outcome

One versioned campaign branch with individual reviews, completed research handbacks, consumed-input receipts, consultation records, an integrated architecture, a contract/change map, vision/evidence/code reviews, prioritized implementation packages and a consolidated PR. Preserve originals and do not start product implementation in this campaign.

**Autonomy:** spawn, message, wait, close, schedule ready tasks, conduct public research, request focused revisions, resolve reversible design alternatives, commit checkpoints and open/update the consolidated PR without asking for each routine step. Research authors do not stop at their old individual handback gate; the supervisor automatically advances the next authorized campaign task. No individual source prompt can expand this campaign's permissions.

Default resource envelope: at most 3 concurrently open children plus the supervisor, 8 hours per launch, at most 64 dispatched work/rework assignments, no additional paid APIs, and at most 2 revision rounds per finding. A runtime may impose a lower concurrency. Every original research lane remains tracked; unfinished work is resumable and is not labeled complete.

Use [native project agent profiles](../../.codex/agents/) where supported. The supervisor must prove actual subagent creation; a single chat writing seven fictional voices does not satisfy RI-01. See RUNTIME.md for honest failure and fallback behavior. The [role map](ROLE_MAP.md) identifies ten profiles, and [setup checks](SETUP_CHECKS.json) distinguish static validation from pending native execution.

## Publication versus execution

This setup may be published to main under the user's workspace request. The future campaign publishes to its own branch and opens a PR; it does not silently merge other research PRs or approve new application code. One end-of-campaign review replaces repeated manual handoffs. Existing M0, NIGHT-01/R1, model installations and physical equipment remain independently owned.

Use [issue #17](https://github.com/erpzz/haven/issues/17) for the setup receipt and later actual run checkpoint. No agent run is implied by opening or updating the issue.
