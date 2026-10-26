# HS-01 v2 — Linux/X9 migration delta (2026-10-25)
Classification: Proposed architecture and user-confirmed preparation only; no remote host inspection or deployment in this GitHub publication.

## Explicit change since HS-01 v1
v1 recommended retaining Windows as headless execution host and launching Codex there. **The operator subsequently selected Linux as the primary server OS**, keeping the original Windows disk bootable as fallback. This v2 records that operator direction without rewriting or superseding any historical v1 bytes, Windows Model Lab qualifications, or the separate M0/NIGHT-01 workspaces.

### Current reported state, not proof of implementation
- Hardware baseline: AMD Ryzen 9 3900X, NVIDIA RTX 2070 Super 8 GB, 64 GB desktop RAM. Validate live CPU, driver, RAM and device ownership.
- Disk: Crucial X9 portable external SSD, 1 TB. The operator wiped/deleted existing volumes via the ThinkPad. No verified ISO-write, Ubuntu installation, boot, server profile, SSH, Tailscale, CUDA or benchmark record yet.
- Intended OS: Ubuntu Server 24.04 LTS on **external X9**; independent UEFI boot from that disk. Preserve existing Windows drive and its partitions.
- Admin path: MacBook SSH into `haven-core` through private network (Tailscale first, WireGuard/Headscale optional later); Mac-hosted Codex CLI / Claude Code as human-supervised engineering workers.
- Other nodes: ThinkPad and MacBook optional task-level workers, not pooled GPU memory. Enroll only after inventory and user action.

## Migration plan and acceptance gates
1. **Preflight**: baseline motherboard firmware USB boot and USB port/cable controller, UEFI, backup coverage and BitLocker key availability. Protect Windows by disconnecting its disk during first Linux installation when practical. Identify target by stable disk properties, not `/dev/sdX` assumption.
2. **Install**: Ubuntu Server 24.04 LTS with its own EFI system partition and ext4 root on X9. If encryption is desired, document the headless unlock/reboot design before selecting it. Record partition UUIDs. No requirement to preformat X9 on ThinkPad. Keep a separate USB installer.
3. **Bootstrap**: operator verifies boot locally, updates packages, enables OpenSSH, confirms keys/host fingerprint, tests remote login on LAN, then restricts ingress and joins private mesh. Document SSH alias `haven` *as proposed until tested*.
4. **Headless reliability**: power recovery, reboot, disk reconnect behavior, USB link resets/UAS errors, journald persistence, temperature, sleep and service startup. A removable USB SSD is acceptable for a pilot but not assumed as stable as internal NVMe for a permanent 24/7 database or training host.
5. **CUDA / inference**: Ubuntu-native NVIDIA driver, validated kernel compatibility, Docker Engine + GPU container runtime when approved. Run exact-version model tests, note compute capability and driver. Compare to historical Windows pinned Strata / llama.cpp results; models and launch scripts may be Windows-specific.
6. **Haven migration**: keep inference on loopback, expose only authenticated Haven gateway on private network, durable jobs with backup/recovery; copy selected data after inventory. Don't commit model files, weights, prompts, session logs or databases to Git.
7. **Federation**: independent Mac/ThinkPad job workers with scoped identities, health checks, resource-aware routing and graceful node loss.
8. **Research/training**: controlled comparisons + eligible teacher datasets, reviewed SFT pilots based on PR #29; validate on frozen holdouts, never claim 8 GB GPU supports unqualified GKD.

## OS/platform choice
Linux is preferred here for remote automation, supervised services, native GPU containers and headless management. This is **not** an assertion of faster tokens/sec versus an optimized Windows CUDA workload. Same-model benchmarks decide speed. 64 GB system RAM supports CPU offload but does not become VRAM.

## Secure agent operations
- Do not forward port 22 or inference ports through the router.
- Install SSH keys on the *MacBook*, never commit private keys. Host-key verify out of band before first connection. A designated `havenadmin` and host `haven-core` are **proposed names**, not current observations.
- Use minimum required shell permissions and individually approved privileged commands. Treat `docker` group as root-equivalent. Use Mac-side explicit approvals for CLI agent tool calls.
- Never put credentials in prompts, PR comments or Git. Private Tailscale networking and Mullvad Internet egress solve different problems; no VPN provides anonymity for an authenticated account.
- Separate personal, partner, and shared household material in stores, caches, embeddings, model training and session handling; preserve consent boundaries.

## Concrete rollback
Before changing Windows or the boot default, finish independent Ubuntu-on-X9 boot and a clean Windows boot test. If Linux fails, shut down, disconnect X9 if necessary, select the intact Windows drive in UEFI, and review USB/EFI changes offline. Restore Linux from tested external backup if needed. A deleted X9 volume is not itself evidence of a full backup, and separate Windows and Linux installations do not share live databases automatically.

## Provenance/gaps
Main reference `4a73a55bfc263d53b8e657403a693004e2871ef6` (observed 2026-10-25). v1 HS-01: `design/hs01-headless-federation-20261025` PR #34. Bakeoff PR #28 open; distillation PR #29 open and stacked. Main Model Lab contains Windows qualification, not Ubuntu bare-metal qualification. This v2 records **planning**, not live execution or tested interoperability.