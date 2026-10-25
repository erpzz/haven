# Haven Core — Ubuntu bootstrap (operator-run)
Status: offline preparation; target host NOT_INSPECTED / NOT_DEPLOYED.

Primary design handoff: [HS-01 v2](../../design/H02/HS01/v2/CLAUDE_START_HERE.md) on branch `design/hs01-headless-federation-20261025`, PR #34. This implementation branch is separate from the draft design PR and must not be merged automatically.

## Hardware and chosen topology
- Desktop (historical/user reported): Ryzen 9 3900X, RTX 2070 Super 8 GB, 64 GB RAM.
- Linux root: Crucial X9 external USB 1 TB SSD. Original Windows installation on a separate internal drive retained.
- MacBook: human-controlled command center for Claude Code and Codex CLI over ordinary OpenSSH, later through a restricted Tailscale network.
- The operator has deleted the X9's original volumes. **No installed Ubuntu, SSH connection, GPU test, or server operation has yet been verified here.**

## Installation (short version)
1. Rufus on ThinkPad: `ubuntu-24.04.5-live-server-amd64.iso`; GPT/UEFI; Rufus-recommended FAT32/NTFS and cluster size; write installer to a **separate USB stick**.
2. Connect installer USB + X9 + Ethernet to desktop. One-time UEFI boot from installer. Disconnect the Windows SSD during the initial install if convenient, so the X9 gets its own EFI system partition.
3. Ubuntu Server install: X9 whole disk with ext4, SSH server enabled, hostname `haven-core`, initial admin username `havenadmin` (names are operator choices). No automatic cloud-init or static IP assumptions. Decide headless FDE unlock separately; unencrypted root is not suitable for secrets without additional protection.
4. Boot directly from X9. Run `lsblk -o NAME,MODEL,SIZE,TRAN,FSTYPE,MOUNTPOINTS`, `findmnt /`, and `hostname -I`; record results **privately**.
5. From a working tree of this branch, run `bash ops/haven-core/scripts/preflight.sh`. It is read-only; review output locally rather than pasting sensitive identifiers in GitHub.
6. Optional local baseline bootstrap: `bash ops/haven-core/scripts/bootstrap.sh --plan`, then **explicitly approve** `bash ops/haven-core/scripts/bootstrap.sh --apply` from an interactive Ubuntu session. This only installs essential packages and enables SSH, never changes auth policy, firewall, drivers, firmware or partitions.
7. Confirm host-key fingerprint out-of-band and generate MacBook SSH key. Test LAN SSH as the operator. Install/configure Tailscale only after access/recovery is proven. No router forwarding; keep model services loopback-only.

## Operator/agent separation
Run the bootstrap with a human admin account, not with an unattended model-runner identity. Claude and Codex should begin with `ssh haven 'hostname; uptime'` only after MacBook SSH config and host trust have been verified. CLI tools running on the MacBook may use its SSH; cloud chats do not automatically have that network or private key. Normal approvals stay enabled. Do not give agent accounts root or Docker-group membership without a specific reviewed privilege design.

## What the scripts intentionally DO NOT do
No OS installation, partitioning, Git checkout, agent installation, SSH key creation, credential export, SSH hardening before test, NVIDIA/CUDA/Docker installation, Tailscale installation, blanket updates, reboots, service exposure, model downloads, cloud calls, or Codex-session uploads. These are separate gated tasks.

## Acceptance sequence
- X9 independent boot, disk ownership and USB transport confirmed; Windows boot unchanged.
- Ubuntu network + SSH connected via MacBook and host key checked.
- `preflight.sh` records actual environment privately.
- Agent/host control permissions reviewed, SSH ingress restricted appropriately.
- NVIDIA driver, native CUDA test, Docker GPU container, baseline llama.cpp/Strata workloads and RAM/VRAM performance independently qualified on Linux.
- Systemd supervision, reconnectable work, durable job store, backups, headless reboot and X9 USB-link resilience tested.
- Only then optional workers, model/agent bakeoff (#28), reviewed distillation pilot (#29).

## Cheap Claude handoff
Run Claude Code in this branch with:
> Read ops/haven-core/README.md, ops/haven-core/CLAUDE_EXECUTION_BRIEF.md and HS-01 v2 design. Do not run broad repo-wide or network scans. Confirm observed local/SSH state and inspect actual scripts. Use the smallest required set of tools; propose host modifications with rollback, execute only after my approval, and return short command/test receipts. Stop when the requested acceptance gate passes.

## Verification
`python3 -m unittest discover -s ops/haven-core/tests -v` runs only local static/plan checks; passing it does **not** mean Linux has booted on the desktop.
