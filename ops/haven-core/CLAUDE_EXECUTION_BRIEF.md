# HS-01 — Minimal-token Claude Code execution brief
Historical bootstrap assignment. SSH, Linux GPU inference, administration and
the bounded training/Strata runs have since completed. For the current task,
start with [the current continuation](CLAUDE_NEXT_SESSION.md) and
[the operator's Opus launch prompt](OPUS_START_PROMPT.md). Do not rerun the
bootstrap inventory or treat the old approval pauses below as the current
assignment; current direct human authorization governs the new session.

This file optimizes engineering throughput, not model usage tricks. It is an operator task request, not evidence a task has run.

## Existing sources
- This branch: `ops/haven-core/README.md` and reviewed scripts.
- Separate planning branch `design/hs01-headless-federation-20261025`, `design/H02/HS01/v2/CLAUDE_START_HERE.md`, v2 delta and session reconciliation.
- Main Model Lab historical Windows qualification. PRs #28 and stacked #29 are open; do not merge or reimplement them.
- Root `AGENTS.md`, `PRECEDENCE.md` govern repository changes.

## Engineering protocol
1. One explicitly selected acceptance gate per agent session. Read relevant paths only; do not ingest the whole repository or all past conversations.
2. First use commands and inspect evidence directly. Avoid broad speculative research, repeated planning essays or gratuitous multi-agent delegation.
3. Report read-only baseline once, then a small exact change proposal with rollback. Ask once for the consequential changes in that gate, and execute only those approved.
4. Local bootstrap on Ubuntu must never run automatically merely because this file is read. The operator runs `bootstrap.sh --apply` in an interactive session after examining `--plan`.
5. Don't install CUDA, Docker, Tailscale or agents, configure permanent SSH policy, copy API keys, change firmware or partitions until the operator gives that phase's explicit approval.
6. Run focused tests once, retain failures, and return paths/exit codes/versions; stop rather than cycling verbose speculative retries.
7. Record session receipts privately, and only commit sanitized summaries after review; raw `~/.codex` and `~/.claude` files stay off GitHub.
8. Leave this bootstrap branch reviewable and do not merge it yourself.

## Smallest first Claude assignment (AFTER Ubuntu boots)
"Confirm actual Ubuntu/X9/root mount, SSH state and local resource inventory using ops/haven-core/scripts/preflight.sh. Run the offline script sanity tests. Check if the MacBook can authenticate to the server over verified SSH. Give me a concise gap/rollback table. Do not install or modify anything without my next approval."

## Reuse after SSH works
"Inspect existing Haven services and actual RTX 2070 Super driver state. Propose an Ubuntu-native GPU qualification path, exact package versions and commands, with preflight and rollback. Pause before privileged changes. After I approve, execute focused tests and return reproducible evidence."
