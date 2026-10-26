# HS01 Overnight Peer Lab — Codex × Claude
Status: OPERATOR_LAUNCH_REQUIRED / NOT_EXECUTED by this GitHub publication.
Date: 2026-10-25 (UTC activity may fall on 2026-10-26).
This package prepares bounded work for Codex CLI and Claude Code on the operator's MacBook. Reading or merging this file **does not** start an agent, access Slink, grant a credential, or schedule background work.

## Why we're doing it
Improve a real user-facing capability on the deployed Ubuntu AI server **Slink**, not a demo score. Strata's real documented first start took 868 seconds (836 loading ~33.02 GiB experts); the local fast 4B has real CUDA inference, but actual tool-driven diagnosis and durable assistant-task completion are not yet qualified. Concurrent Claude work on branch `claude/opus-tool-distill-20261026` explores verified teacher-to-student tool learning. We should challenge each other's hypotheses with actual receipts.

## Sources of truth / boundaries
- [Real-system diagnosis challenge](https://github.com/erpzz/haven/blob/review/hs01-evidence-gates-20261025/review/HS01/EXPERIMENT_01_SLINK_COLD_START_DIAGNOSIS.md), independent review [PR #38](https://github.com/erpzz/haven/pull/38)
- [Live Slink runtime](https://github.com/erpzz/haven/pull/36) PR #36 stacked on [bootstrap](https://github.com/erpzz/haven/pull/35) #35
- [Executed small LoRA pilot](https://github.com/erpzz/haven/pull/37) PR #37 stacked on #29 → #28
- [Claude's active experiment](https://github.com/erpzz/haven/tree/claude/opus-tool-distill-20261026) separate branch. **Check head before making assumptions.**
- Main still contains historical Windows Model Lab; never assume unmerged work is on main.
- No independent live Mac process/session visibility in this publication. Check locally for running Claude/Codex before starting another copy.
- Keep Windows partitions/bootloader, USB-root drive and other research branches unchanged.

## Defined worker ownership
**Codex lead:** own a new `codex/hs01-real-diagnostics-*` branch/worktree based on the actual runtime implementation branch (#36). Read-only diagnostic evidence on Slink first, then if needed implement the smallest fixed, safe, read-only host tool through the *existing* Model Lab; run one real end-to-end diagnostic question through model -> actual tool -> source-backed answer, record errors. No arbitrary shell exposed to the model. Investigate availability of unused internal SSD storage **read-only** only. Report if a real mount/copy/restart/SSD migration requires operator approval; no write to Windows or internal disks while asleep.

**Claude peer:** preserve existing `claude/opus-tool-distill-20261026` worktree and do not start a second competing experiment when its session is active. Finish or meaningfully checkpoint the existing teacher-SFT vs oracle-control evaluation on Slink **only when a bounded GPU lease is available**. Fix explicit verifier false-positive cases on its own branch with disclosed scoring amendments; preserve frozen original set/hashes, run matched 110-episode held-out evaluation or explicitly state incomplete. Independently review Codex's diagnosis and tool/evidence contract using actual receipts. If Claude is not running and direct CLI peer launch is permitted and authenticated, Codex may prepare and launch **one** Claude background session using the CLAUDE_PEER.md task after inspecting the local CLI help/permissions; otherwise publish the handoff and continue Codex's work.

**Two-way critique:** Codex audits Claude's data separation, provenance and denominators; Claude audits Codex's root-cause claims, permission boundary and evidence flow. Never let one agent's approval substitute for measured results. Peers exchange **short, sanitized, linked receipts** in this campaign's issue/PR comments or their designated handoff files, not in untracked shared edits. Check GitHub at checkpoints only; no unlimited polling.

## Working gates (in priority order)
1. **Preflight (no GPU):** identify active `claude`/`codex` sessions and separate worktrees; confirm `ssh haven` and checked-in PR evidence. Verify disk mount/root, negotiated USB link, existing Strata run's expert-load counters, free storage, USB errors; keep private IDs/logs off Git.
2. **Real diagnosis test (no Strata cold restart):** collect fixed read-only host data. Run the fast 4B locally against the real fixed tools (if absent, engineer the minimum tool route). Compare its answer against actual evidence. Explicitly classify `HOST_READ_ONLY` vs `REAL_END_TO_END`.
3. **Independent Claude review and learning:** share actual evidence; allow Claude to finish its previously started 550-episode campaign when GPU is available. Claude must not call its scripted oracle's 550/550 a model score. Disclose the amended verifier and its effect on 217 cases after a reference run. Do not train on held-out cases, tune to the final score, or promote an adapter from synthetic performance alone.
4. **One reversible improvement candidate:** after measurements, choose ONE effective next action. For changes requiring root, firmware, storage mounts or copying 68 GB, stop for operator consent. A no-modification diagnostic report is a valid useful output.
5. **Peer challenge / integration:** each peer reviews the other's actual findings and offers one prioritized correction. Codex submits measured final findings, a scoped PR (draft), before/after only if actually performed, logs/rollback, open questions and a compact morning briefing.

## Concurrency, spending and safety
- **Max 2 top-level sessions** (one Codex, one Claude). No recursive agent spawning, no auto-launch storm or unattended agent loops.
- Before any GPU operation check existing running processes and acquire a cooperative Linux `flock` covering its **entire operation** at an operator-controlled path under `~/.local/state/haven/`. A file lock covers only cooperating processes; verify `nvidia-smi` and existing user services as well. Do not stop an unowned job to claim the GPU.
- Cap cold Strata starts at **zero by default**. A single controlled retest requires a concrete reversible hypothesis and the operator's prior explicit approval.
- Do not erase, partition, resize, format, write to NTFS/BitLocker drives, disable Secure Boot, change SSH/UFW access, change power/boot policy, overwrite model weights, promote an adapter, or merge PRs unattended.
- No cloud/paid training jobs, new subscriptions, billable hosted inference, third-party network scans, live smart-device actions, purchases, or public service exposure. No personal/partner/employer data ingested into models or Git.
- Safe independent Git edits, read-only SSH diagnostics, private synthetic test runs and already-authorized bounded local model experiments are suitable tasks **only when the configured CLI permissions allow them**. If blocked for approval while operator sleeps, publish blocker + continue independent no-side-effect review; never bypass controls.
- **Stop criteria:** complete two substantive deliverables and one cross-review, or hit a configured duration/usage ceiling, or encounter human-only decision. End with stable service state and checkpoints. No claim that work continues if the host/session sleeps or authentication fails.

## Evidence contract
Only these classifications are accepted: PROPOSED, STATIC_TEST, HOST_READ_ONLY, SYNTHETIC_MODEL_RUN, REAL_GPU_RUN, REAL_END_TO_END, INDEPENDENTLY_VERIFIED, BLOCKED.
- Include UTC timestamp, precise code commit/branch, exact command/tool contract, test input identifiers, exit state, raw private receipt/hash, aggregates and failed cases.
- Never claim a *real* AI tool test merely because a scripted oracle or unit test called the dispatch function.
- Model quality and safety require independent answer assessment, not regex scores alone. A control arm is required to attribute gains to training.
- Scripted oracle 550/550 is a verifier self-check; held-out generalization within one procedural generator is not independently validated real-world skill.
- Leave runtime recoverable with known-good fast 4B available. If a service was touched, validate it is healthy; rollback only owned changes.
- Morning briefing must say what's newly usable, what's measured, what failed, whether storage relocation seems justified, what Claude/Codex each challenged, exact PR/commit and next operator decision.

## Launch
Use `CODEX_LEAD.md` in the existing Mac CLI session after checking your account/permissions. If Claude is not already running, initiate `CLAUDE_PEER.md` as **one separate** Claude CLI background or interactive worktree session only after local process check and consent. Avoid running both on the same Git worktree; publish both branches to GitHub for asynchronous peer review.
