# Opus: continue Haven Core

## Live continuation checkpoint — 2026-10-25

The operator continued this session and explicitly authorized autonomous Haven
work except spending money or wiping drives, including bounded Strata/training
work if resources permit. The original approval pauses below are a historical
handoff boundary; this live operator instruction superseded them for the current
run. A future agent must obtain its authority from the operator's actual handoff,
not treat this file as a credential or self-issued grant.

The signed headless NVIDIA driver is installed and active after a successful
reboot, with Secure Boot preserved. The existing Model Lab restarted at boot.
Linux archive installation is implemented with pinned assets and internal shared
library aliases materialized as regular files; focused archive checks pass.
The first pinned model download is in progress. Real inference is not yet claimed.
Work is being checkpointed on this branch/PR rather than deferred to Opus.

**Ship one real local-model response through the existing Linux Model Lab.**
The control panel is already deployed. Spend this session connecting real
inference to it, with the operator's required approval for GPU installation and
downloads. Do not restart architecture research or another infrastructure audit.

## Slinky and Opus are peers

Slinky prepared SSH and the running Linux service. Opus owns the next engineering
deliverable with the same standing and freedom to make reversible implementation
choices inside the approved scope. Neither needs the other's permission for
routine work. The human operator approves consequential machine changes.
Use Git commits and short receipts to coordinate. If working concurrently, use
separate branches; do not edit one checkout or operate one GPU job simultaneously.

## Start with these inputs

- Branch: `codex/slink-linux-model-lab-20261025`, based on the bootstrap branch
  `implementation/hs01-ubuntu-bootstrap-20261025` (PR #35).
- Read this file, root `AGENTS.md`/`PRECEDENCE.md`, and
  `ops/haven-core/LINUX_MODEL_LAB.md`. Follow root navigation requirements, but do
  not reread every historical handback or reproduce missing archives.
- Relevant implementation: `labs/model-lab/{server.py,labcore.py,catalog.json}`,
  `ops/haven-core/open-lab.py`, and the systemd unit beside this handoff.
- HS-01 v2 in PR #34 is the architecture reference if a design question arises.
  PR #28 is the later bakeoff; #29 is stacked distillation work. Neither is the
  next installation task. Preserve their work and historical manifests.
- The operator has a **private connection appendix** on the administration Mac.
  It contains current access and package-plan details. Credentials stay in the
  system's SSH/Keychain mechanisms. Cloud access is not implied by this document.

## Already achieved on the real target

- `ssh haven` works with a dedicated encrypted key. Password recovery remains.
- Package audit was clean. The purple console dialog was stale screen content;
  a clean local login screen is available. No font/package repair was necessary.
- Model Lab runs as an ordinary systemd user service, enabled with lingering.
  The UI listens only on `127.0.0.1:8877`; the Mac reaches it through owned SSH
  forwarding. It survives an administration-session disconnect.
- A private mode-0600 launch file replaces bearer URLs in the service journal.
  `open-lab.py` reads it, verifies the authenticated API, and opens the UI.
- The live browser showed actual Linux telemetry and the Linux engine controls.
  **No inference engine/model is connected. Real GPU inference is not qualified.**
- Bootstrap `--apply`, OS upgrades, Tailscale, Docker, training and model downloads
  were not run. Package indexes were refreshed; maintenance upgrades remain.

## The next deliverable

1. Read the private appendix and confirm only branch/worktree state plus
   `ssh haven 'systemctl --user is-active haven-model-lab.service'`. Continue from
   the existing result. Do not inventory the whole computer again.
2. Implement Linux engine installation using the existing ownership, checksum
   and explicit-confirmation boundaries. `Lab.install_llama()` currently rejects
   non-Windows automatic installation. Extend it rather than writing a new lab.
   The proposed official Linux release bytes are pinned in
   `linux-inference-plan.json`; the first model is existing catalog ID
   `qwen35-4b`. Keep runtime files outside Git.
3. **Obtain one grouped operator approval before** installing the proposed
   headless NVIDIA packages, rebooting, or downloading the approximately 0.76 GB
   engine/runtime archives plus 2.74 GB model. The current handoff is not that
   approval. The private appendix includes an already simulated, signed-module
   package route. Preserve Secure Boot, disks, Windows and the bootloader. Do not
   install a desktop stack, global CUDA Toolkit or heavy Python AI framework.
4. Once approved, install the bounded dependencies, reconnect after the approved
   reboot, install/verify the pinned runtime and model, and load one GPU model
   through the existing UI. Use 4K context, one request and the existing modest
   thread profile. Keep inference APIs on loopback and access through SSH.

## Enough verification to ship

- Confirm the NVIDIA driver sees the device and the engine actually uses CUDA.
- Get one real answer through the browser and record reported timing/VRAM once.
- Cancel a request, run one follow-up, then unload/stop the owned backend. Verify
  recovery without killing an attached or unrelated process.

Run focused tests for code changed. Add a small security regression if handling
archives/processes changes; do not repeat the whole suite or a model bakeoff
without a new failure. One short bounded attempt per configuration is enough to
expose a concrete blocker. Preserve errors and fix the cause; no speculative
retry loops, fictional benchmarks or CPU fallback described as CUDA success.

Prior evidence: the new supervised-launch subprocess/API test passed on Ubuntu;
existing non-Windows process/lab checks passed. One inherited auth-test helper
incorrectly decoded HTML as JSON; fixed it and all 10 auth tests passed. Seven
Windows-only tests were skipped. The Mac's system Python lacked `hashlib.scrypt`;
that is a local test-environment limitation, not a reason to alter Linux auth.

## Checkpoint and stop point

Push small code commits and update this handoff/PR with the resulting behavior,
exact revision, a few executed checks, limits and next action. Keep machine
inventories, tokens, private links, saves and raw transcripts out of GitHub.
Do not merge your own PR or silently bypass approval/security controls.

Success is usable local inference in the existing interface. Then return control
with one concise receipt. Docker, mesh access, large Strata downloads, additional
models, training and the full #28/#29 campaigns are later work packages.
