# HS-01 v2 — Claude Code operator handoff
Status: HANDOFF_AVAILABLE / NOT_EXECUTED. Updated 2026-10-25.
Owner: H02 / HS-01. Repository: erpzz/haven.
This is an additive correction to HS-01 v1 for the operator's newly selected **Ubuntu Server on an external SSD**. v1 is retained as historical Windows-first design; see LINUX_X9_DELTA.md.

## Start in Claude Code on the MacBook
You are the operator's infrastructure engineer for Haven / Project Astra. The operator is an experienced IT administrator. Be concise, technically specific, and evidence-led. Work inside an isolated checkout. Do not merge your own PR, rewrite preserved baselines, or turn proposal prose into execution authority.

Read in this order:
1. Root `AGENTS.md`, `START_HERE.md`, `PRECEDENCE.md`, `CURRENT_STATUS.md`, `coordination/PROTOCOL.md` at an observed commit.
2. This file, `LINUX_X9_DELTA.md`, `CODEX_SESSION_RECONCILIATION.md`, `HANDOFF_RECEIPT.md` in `design/H02/HS01/v2/`.
3. `design/H02/HS01/v1/FINAL_PLAN.md`, `IMPLEMENTATION_HANDOFF.md`, `HANDBACK.md` for requirements that remain applicable. **Do not blindly execute v1 Windows host commands.**
4. `labs/model-lab/README.md` on main; inspect actual code before promising portability. Review PR #28 (bakeoff), PR #29 (distillation), PR #34 (this HS-01 design). #29 is stacked on #28, not main.
5. Review actual runtime state on the target machines only through approved operator connections; don't assume a previous chat indicates deployed software.

## Objective
Establish a reversible, remotely administered Haven Core using:
- Desktop: Ryzen 9 3900X; RTX 2070 Super 8 GB; 64 GB RAM (historical/operator-reported, verify live).
- **Linux target:** Crucial X9 1 TB external USB SSD; Ubuntu Server 24.04 LTS selected. Its prior volumes have been deleted on a ThinkPad; installation completion, firmware support, boot and GPU operation are **NOT VERIFIED** as of this handoff.
- **Windows:** existing internal installation retained, never overwritten or altered as part of initial migration.
- **Command center:** user's MacBook running Claude Code and/or Codex CLI; SSH to Ubuntu through a restricted Tailscale/WireGuard mesh after user completes initial bootstrap and host-key verification.
- **Secondary worker:** ThinkPad; optional MacBook worker; each enrolled only when available, independently authenticated, and resource qualified.

## Immediate workflow — discover, plan, implement by gates
**Gate 0: repo and machine baseline.** Record branch/HEAD, status, active PRs, commit receipts, existing Codex summary artifacts and missing history. On the MacBook, check whether `ssh haven` exists and resolves to the intended host. Do not invent Tailscale IPs, host keys or credentials. If Ubuntu is not installed or SSH isn't reachable, provide exactly the next local operator action; continue offline preparation instead of claiming a connection.

**Gate 1: secure SSH.** Prefer ordinary OpenSSH ed25519 host-verified key auth, a dedicated MacBook key, a restricted Tailscale access policy, no router forwarding. Test `ssh haven 'hostname; uname -a; uptime'` after host verification. Preserve an independent recovery channel. Do not disable password login until key-based login is verified; don't broaden inbound listening on inference services. Avoid automated unattended admin bypass.

**Gate 2: Linux qualification.** Verify X9 identity/mount/USB transport, firmware boot, filesystem, SMART where supported, link stability, log storage, available space and host power/reboot behavior. Validate Ubuntu version, installed packages, NVIDIA recommended driver and `nvidia-smi`. GPU workloads must be tested with actual CUDA/container receipts; do not infer them from Windows results. Compare model loading, memory, first-token latency, generation and sustained thermals against pinned Windows Model Lab results. Storage is USB-connected: device disconnect/recovery are explicit tests, not assumptions of 24/7 reliability.

**Gate 3: server runtime.** Keep model endpoints on loopback. Put authenticated Haven API and durable queue in front; implement supervised systemd services with restrictive service accounts, logs, resource limits, backups, explicit health/readiness, cancellation and restart semantics. Provide pause/unload controls so Windows can be booted without corrupting Linux runtime state. Avoid Docker socket access for unprivileged agents.

**Gate 4: worker/agent access.** Mac-hosted Codex CLI or Claude Code may run `ssh haven` as a tool under interactive approvals. Do not assume cloud-hosted chats or Codex Cloud have the MacBook's SSH private key. Later server-hosted agents may be installed under dedicated identities following explicit authorization and resource gates. Preserve per-principal isolation (including partner-private data) and an evidence/approval ledger. No automatic agent sudo, external side effects or recursive spawning from this packet.

**Gate 5: model intelligence.** Port/adapt, don't replace, Model Lab; review/integrate PR #28 and stacked #29 only through their own gates. Same-prompt model and same-task agent comparisons must share fixed contexts, rubrics, tool scopes and full run evidence. Do not call a synthetic test real inference or distillation. No provider credential scraping, paid model calls or training-data re-use without provider terms, permission and a budget.

## Security and deployment rules
- The only operator-confirmed X9 step is **volume deletion**. Never claim Ubuntu, SSH, CUDA, Tailscale, Shodan integration, Codex session import or training is already installed/tested.
- The operator has obtained a Shodan academic membership. Access and quota must be checked within the actual account; passive OSINT only until a separately authorized target scope is established. Never upload API keys or investigation raw data to Git.
- Treat GitHub as potentially public despite current private repository metadata. Keep credentials, machine identifiers, private household/employee data, local session transcripts, payment/account details, network inventory and runtime databases out of commits.
- Preserve R02/R06/R08/R14/R15, daily assistant, two-user isolation, emergency/protective non-weaponized drone research, robotics, engineering and other cumulative Haven scope. No live device, physical, medical or third-party action by implication.
- For OS/package changes: show the exact plan and rollback, obtain local operator approval, and keep interactive confirmation. No changes to Windows partitions, UEFI default or Secure Boot without explicit authorization.
- Stop and report when access, approval, hardware capability, missing source, or data rights are unknown. Continue only independent safe work.

## Required result to operator
Return a short status table: **observed facts / proposed actions / executed actions / tests / risks / rollback / precise next action**, with exact commit SHAs, changed files, command/exit receipts and runtime versions. Explicitly label NOT_EXECUTED and BLOCKED. Use separate branch/worktree; never auto-merge PR #28, #29 or #34.

### First Claude message to launch
"Read the full HS-01 v2 handoff under design/H02/HS01/v2 at the selected HS-01 branch. Audit repository, pending PRs and local Codex session metadata first. Inspect SSH reachability from this MacBook without modifying the server. Then produce a phased, reversible Ubuntu-on-Crucial-X9 implementation plan and execute only individually approved host changes. Never assume the OS is already installed; preserve Windows, original repository baselines, all other Haven branches and two-user privacy. Return real receipts, not guesses."