# HS-01 v2 — publication and scope receipt
Date: 2026-10-25. Owner H02 / HS-01. Class: PROPOSED / HANDOFF_AVAILABLE / NOT_EXECUTED.

## Reason for v2
The operator switched from HS-01 v1's Windows-first headless execution plan to Ubuntu Server 24.04 LTS on a Crucial X9 1 TB external SSD, with the existing Windows disk preserved. The MacBook will operate Codex CLI and/or Claude Code over verified SSH/private mesh; the ThinkPad and MacBook are optional later workers.

## Exact published files
- `CLAUDE_START_HERE.md` — self-contained Claude handoff and first prompt.
- `LINUX_X9_DELTA.md` — Linux boot, networking, CUDA and rollback changes from v1.
- `CODEX_SESSION_RECONCILIATION.md` — verifiable GitHub history vs missing local agent sessions; export and redaction protocol.
- This publication receipt.

## Evidence limits
Source checked: repository main, AGENTS.md, PRECEDENCE.md, START_HERE.md, CURRENT_STATUS.md, coordination/PROTOCOL.md, HS-01 v1 files and open PR #28/#29/#34 states (as of 2026-10-25).
Not checked: local Codex/Claude transcripts, Windows/ThinkPad/Mac disks, actual Linux installation, network or device hardware. Prior HS-01 v1 is preserved byte-for-byte. No app source, shared requirements/contracts, imported materials or tests changed.

## Authority
This is an operator-requested documentation and Claude handoff publication. It is **not** permission for an agent to modify other agents' branches, merge PRs, push private data, make a purchase, conduct third-party testing, change boot firmware, install kernel drivers or operate real devices without the user's separate approval. An agent may prepare offline plans and carry out individually approved local implementation through an authenticated operator-run session.

## Expected next outputs from Claude
1. Current exact Git/PR/worktree audit and sanitized Codex session inventory status.
2. Observed desktop/Mac reachability and OS installation state, not assumptions.
3. Proposed deployment changes with rollback and approval points.
4. Actual command and test receipts for approved steps, with explicitly labeled missing evidence.
5. A separate implementation PR after tested work, without self-merging pending research PRs.

No review or automated validation of host changes is claimed by this packet.