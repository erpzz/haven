# HS-01 v2 — Codex/Claude session and worktree reconciliation
Status: PARTIAL_INDEX / LOCAL_SESSION_EXPORT_NOT_AVAILABLE (2026-10-25)

## What was actually inspected
GitHub repository `erpzz/haven` on main and open PR metadata. Main at `4a73a55bfc263d53b8e657403a693004e2871ef6` and HS-01 draft PR #34 at `899013d48d79adc0f365409206d1d7413096031c` before this v2 update.
- Main: Model Lab's Windows qualification, Continue flow and ecosystem scout are committed. Do not substitute a local GPU test today.
- PR #28: `implementation/r02-runtime-model-bakeoff-20261005` at `db93c5f857550b7f8104e41bba1b7167fd3327e7`; open, not merged.
- PR #29: `implementation/r02-distillation-lab-20261012` at `2073c4d912af6f8c43554440863c28eacad2db7b`; open, **based on #28**, not merged.
- PR #34: HS-01 v1 Windows-first/federation plan, draft and open.
- Existing `.codex/agents/` RI-01 profiles are **configuration**, not proof that a named agent session ran. RI-01 execution receipts require independent inspection.
- Repository contains historical research branches and proposals; they are not all accepted, merged or executable.

## What has *not* been read, and must not be claimed synced
Full local Codex CLI/Desktop/IDE chat sessions, archived sessions, unsent prompts, shell history, uncommitted worktrees and raw local logs on the MacBook, ThinkPad or Windows desktop are not accessible to this GitHub-only publication. ChatGPT conversation summaries are not raw Codex session exports. GitHub search did not locate a complete indexed session archive. Existing library references cover a few historical handback artifacts; they are not the full history.

**Never upload raw `~/.codex/sessions/**/*.jsonl`, Claude transcripts, auth/config JSON, agent environment dumps, .env files, browser profiles, SSH keys, full prompt history, screenshots or private household/employer records.** Private GitHub visibility is not permission to publish them.

## Claude: local reconciliation procedure (operator-authorized)
1. Work in isolated clone/worktree and record `git rev-parse HEAD`, `git status --porcelain=v1`, `git worktree list`, `git branch -avv` and `gh pr list --state open`. Fetch before asserting any remote state. Preserve uncommitted data.
2. On the **MacBook where Claude runs**, ask operator before reading local Codex history. Inventory only the known, app-supported user-owned locations, e.g. `$CODEX_HOME` if defined, otherwise `$HOME/.codex/`; `$HOME/.claude/` is separately sensitive. Search session metadata only, avoid contents by default. Do not scan unrelated folders or another user's account.
3. On Windows/ThinkPad, inspect equivalent user-profile Codex locations only through explicitly approved SSH/remote sessions or an operator-provided export. Do not assume the MacBook has other hosts' session files.
4. Build a **private** manifest with session ID or pseudonym, timestamp, agent/client version when actually available, relevant repo/worktree, linked PR/commit SHA, outcome, source-path hash, redaction status, and gaps. Do not infer execution from an instruction prompt.
5. For each session the operator selects, produce a short **sanitized evidence summary**: objective, actual commands/actions, changes and their reviewed diffs, tests with exit evidence, blockers, unresolved questions, artifacts and exact commit refs. Strip credentials, auth headers, IPs, hostnames, personal/chat/employer data and tool secrets. Distinguish agent narration from system-observed results.
6. Only after manual review, commit the sanitized summary to a **new versioned `review/HS-01/session-receipts/` path on an owned branch**, or link an already-public/approved GitHub receipt. Do not auto-push local history. Keep raw session evidence outside Git in separately approved encrypted storage.
7. Compare all sanitized receipts against open PRs, current code and changed files; mark conflicts / detached worktrees / orphaned changes explicitly. A missing session cannot be reconstructed as if observed.

## Minimum receipt template
```markdown
# SESSION_RECEIPT — [sanitized-id]
Source: local operator-approved session (path stored privately; sha256 recorded privately)
Observed date/UTC: [value or UNKNOWN]
Agent/runtime: [version or UNKNOWN]
Repo/worktree: [sanitized label]; branch [name]; commit [SHA]
Authority/scope: [operator task and allowed paths]
Executed: [only observed commands and outputs, or NOT_VERIFIED]
Changed: [paths + diff/commit refs]
Tests: [command, environment, actual result]
Claims not verified: [...]
Sensitive omissions: [categories only]
Conflicts/blockers: [...]
Review: PENDING / ACCEPTED / CHANGES_REQUIRED
```

## Explicitly outstanding
- Raw Codex session archive unavailable; **not fully synchronized**.
- Linux installation, private SSH access, NVIDIA CUDA and model launches: NOT_EXECUTED_BY_THIS_HANDOFF.
- Main's older source import completeness remains an independently tracked gap; root `CURRENT_STATUS.md` is dated 2026-09-28.
- No main merge, PR acceptance, agent dispatch, model training or deployment caused by writing this document.

## First reconciliation task
Before implementing HS-01, have Claude inventory only the operator-provided local Codex session locations and open GitHub worktrees. Produce a private manifest, offer sanitized summaries for review, map them to #28/#29/#34, and report which sessions remain missing. Continue the independent Ubuntu readiness plan regardless of unexportable private sessions.