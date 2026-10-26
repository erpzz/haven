# Opus and Slinky: continue Haven Core

## Current checkpoint — 2026-10-25

The first milestone is complete: the administration Mac can use `ssh haven`,
and the existing Linux Model Lab has produced real GPU responses through its
private SSH tunnel. Continue implementation from these results. Do not restart
architecture research, reinstall working drivers, or repeat a broad inventory.

The operator explicitly authorized autonomous Haven work except spending money
or wiping drives, including bounded local training and Strata. This records the
scope of this session; a file is not a credential or a new grant to a future
agent. Preserve ordinary sudo boundaries, host trust, recovery and private data.

## Work and branches

- [PR #36](https://github.com/erpzz/haven/pull/36):
  `codex/slink-linux-model-lab-20261025`, stacked on bootstrap PR #35.
  Contains the running Model Lab, pinned Linux CUDA installer and Mac launcher.
- [PR #37](https://github.com/erpzz/haven/pull/37):
  `codex/slink-distillation-pilot-20261025`, stacked on distillation PR #29.
  Contains the actual bounded Linux LoRA pilot, HF adapter evaluation and summary.
  Its separate checkout avoids altering the Lab's bootstrap ancestry.
- HS-01 v2 in PR #34 remains the architecture reference. PR #28/#29 remain open
  dependencies. Do not merge these PRs automatically.
- Read root agent/precedence/navigation instructions, this file and
  [Linux operation](LINUX_MODEL_LAB.md). Read a specific implementation when
  changing it; there is no need to re-audit every historical handback.
- The administration Mac holds a private connection appendix and implementation
  log outside Git. Access credentials use SSH/Keychain and interactive sudo;
  never put them, launch tokens, inventories or raw transcripts in GitHub.

## Actual completed work

- Dedicated encrypted SSH key and convenient alias; fresh key-only access and
  separate password recovery verified. A clean local console login is available.
  The purple dialog was stale screen content; package audit was clean.
- Signed headless NVIDIA driver installed and tested after a real reboot with
  Secure Boot preserved. No disk, Windows or bootloader changes were made.
- Python stdlib Model Lab runs as an ordinary lingering systemd user service,
  on loopback port 8877. A mode-0600 launch file keeps its bearer URL out of the
  journal. The Mac helper owns only its SSH tunnel and verifies the private API.
- Pinned llama.cpp b11146 Linux CUDA 12.8 archives and existing `qwen35-4b` model
  downloaded and SHA-256 verified. The native installer rejects unsafe tar paths,
  materializes internal library aliases, validates ELF and publishes atomically.
  A minimal Ubuntu installation also needs `libgomp1`.
- Real engine log confirmed 33/33 layers offloaded to CUDA. A warm browser response
  reported 0.17-second first output and 91.25 decode tokens/second. This is one
  short observed response, not a throughput guarantee or model-quality score.
  The first cold request took 41.5 seconds and answered arithmetic incorrectly.
- Rapid user-service restart after HTTP traffic now works: explicit readiness
  notification and POSIX socket reuse address actual observed startup failures.
- The separate 0.6B LoRA pilot completed 40 steps in 18.016 seconds, with peak
  allocated CUDA memory 2,826,555,904 bytes. Three synthetic training examples;
  11 identical frozen probes before/after. Facts 0/3 -> 0/3; skill 0/4 -> 0/4;
  retrieval 1/2 -> 2/2; unknown facts 2/2 -> 2/2. No quality claim or promotion.
- Real 4B synthetic tool runs: original interface 2/8 mechanical passes; after
  documenting resource IDs and fixing a whitespace-sensitive inert-flag check,
  3/8 passes, 7/8 tool selections and all 8 transports completed. Keep failures.
  Two verified training rows survived; four failures stayed in the private review
  queue; two held-out tasks were excluded. Do not auto-approve failed targets.

## In progress: Strata Linux

The old Windows v0.1.39 pin has no Linux release assets. The separately installed
Linux path uses official release v0.2.6, Control 0.1.51 and signed engine 0.1.50.
The feed selected its CUDA 13 package, which explicitly includes sm_75 and passed
its binary version check. A model-backed run remains to be completed.

Both pinned IQ2_XS shards (68 GB total) are downloaded, SHA-256 verified and
prepared. The native profile uses 8K context, one request, no vision/MTP/hooks,
and the signed engine component. There is no need to download or hash them again.

The finite first-response job completed. Authenticated Strata generated a real
27-token answer through the existing Lab, with 0.834-second first output and
27.7 backend decode tokens/second. Unauthenticated chat returned 401. Disconnect
left the external service running; its explicit owned stop succeeded and the
existing fast 4B model was restored. See the [sanitized receipt](linux-strata-result-20261026.json).

The cold service start took 868 seconds before API readiness, including 836
seconds reading experts. This dominates first startup. One short response is not
a quality/sustained-speed benchmark. Strata stays stopped for normal operation;
its prepared model remains available. No need to repeat the cold run to confirm
this handoff. Private raw output is in the local first-response receipt.

## Focused validation and continuation

The Linux archive suite (9 checks), supervised-launch/authentication check and
10 inherited auth checks passed on Ubuntu. The distillation suite (12 checks)
and focused bakeoff suite (8 checks) passed. Historical Windows-only tests and
Mac scrypt limitations are separate; no reason to repeat them for Linux work.

For each change, exercise its affected path once and fix concrete failures.
No model is promoted by a tiny synthetic suite. Do not tune against the frozen
probes to manufacture a win. No GKD memory-gate override or 4B training occurred.

Administration completed: 27 maintenance upgrades, clean package audit,
restricted UFW ingress with a fresh-SSH check and timed rollback, bounded
persistent journals and a green private health timer. Docker/NVIDIA Container
Toolkit installed from official signed repositories; a real ephemeral GPU
container passed with no network, published ports or host mounts. No Docker
group/passwordless-sudo grant was added. See `ADMIN_RECOVERY.md`.

Tailscale server client is installed but stopped pending the intended owner's
account enrollment; no tailnet/DNS/routes were guessed. LAN SSH remains the
working administration path. Keep inference on loopback, preserve Mullvad and
ordinary SSH recovery, and scope mesh access before enabling it.

## Next useful engineering slice

Add one explicit switch between the **prepared** fast 4B model and Strata in the
existing Model Lab. The current Linux button attaches already-running Strata;
starting/stopping its prepared user service still uses the command line. Reuse
Lab jobs for visible startup/progress/cancellation, keep service names/argv fixed,
and keep keys on the server. Stop only the known Haven service when switching
back; preserve the external-backend ownership contract. No new driver, model
download, framework, training or architecture study is needed.

Use a fresh owned branch from PR #36. One actual 4B -> Strata -> 4B cycle with a
short answer and cleanup is enough acceptance for that feature. Read the saved
receipts instead of repeating package/GPU audits or the tiny training pilot.

## Peer handoff and checkpointing

Slinky and Opus are equal engineering peers. Neither needs the other's permission
for routine choices inside human-authorized scope. Use separate owned branches
and short receipts if concurrent; one owner operates the GPU at a time. Push
useful commits and update this handoff with actual results and rollback steps.
Keep runtime databases, models, adapters, private notes and raw agent/model
transcripts off GitHub. Do not merge your own PR.
