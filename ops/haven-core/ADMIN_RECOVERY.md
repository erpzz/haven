# Linux administration and recovery

This supplements the private implementation log. It contains generic procedures;
addresses, account inventory, host fingerprints, package backups and raw journals
stay in the operator's private appendix. Never attach a raw health snapshot or
agent transcript to an issue.

## Current operating boundaries

The normal administration path is the Mac's encrypted `ssh haven` identity.
Password SSH and a local console remain recovery routes. No agent received
passwordless sudo or membership in the Docker group. Do not forward the SSH agent
or copy Mac private keys/GitHub credentials to the server.

The Model Lab is an ordinary lingering user service, bound to loopback. Its
startup does not load a model. Strata is a separate user service and stays
manual-started for the initial experiment. Run one GPU workload at a time.

UFW now denies incoming traffic by default and permits SSH from the approved
administration LAN. A new independent SSH connection passed before the timed
rollback was cancelled. No inference port or router forward was opened. Mesh
enrollment remains separate; do not assume a tailnet identity exists.

Docker Engine and NVIDIA Container Toolkit use their official signed apt
repositories, with separate `Signed-By` keyrings. Docker exposes its ordinary
root-controlled Unix socket, with no TCP daemon listener. Published container
ports can bypass UFW: an `ExecStartPost` helper in Docker's system unit drops
new forwarded connections from the physical uplink in `DOCKER-USER`. Preserve
that drop-in when updating Docker. Bind any future model publication explicitly
to loopback; never use a bare public `-p PORT:PORT` mapping.

References: [Docker Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/),
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).
This setup uses the packaged headless driver; no global CUDA Toolkit is needed.

## Bounded health and logs

`haven-health.timer` creates one private snapshot every fifteen minutes. It
checks root disk headroom, the SSH socket, the Lab, package configuration and the
existing NVIDIA telemetry command. Strata is optional. It performs no inference,
repairs, downloads, external calls or repeated process/port scans.

```sh
systemctl --user start haven-health.service
systemctl --user status haven-health.timer
cat ~/.local/state/haven-admin/health.json
journalctl --user -u haven-health.service -n 5 --no-pager
```

The JSON is mode 0600 and replaced atomically. The journal reports only status
labels; detailed values stay local. A health warning is a reason to inspect that
specific check, not to reinstall the host. Stop the timer with
`systemctl --user disable --now haven-health.timer`.

Persistent system journals have a 512-MB disk budget and thirty-day retention;
runtime journals have a 64-MB budget. The drop-in is
`/etc/systemd/journald.conf.d/haven-retention.conf`. Keep model/runtime logs local:
they can contain prompts even when the control service suppresses launch tokens.

## Recovery order

1. Use a new `ssh haven` connection. If unavailable, use the local console and
   compare the current network address/SSH unit state with the private appendix.
   A changed host key is an investigation, never an automatic known_hosts edit.
2. If an experiment is consuming RAM, stop its user service first:
   `systemctl --user stop haven-strata`. The unit contains its process group and
   has a hard memory budget. For an owned GGUF, use `labctl.py unload` or stop the
   Lab service. Do not kill unrelated processes or an attached external backend.
3. Inspect only the affected journal: `journalctl --user -u haven-model-lab -n 40`
   or `journalctl --user -u haven-strata -n 40`. Reopen the Mac launch helper after
   a Lab restart because its private bearer link rotates.
4. Inspect `dpkg --audit` before a noninteractive repair. Do not kill an active
   apt/dpkg transaction or remove its lock. The private root log holds before/after
   package lists and simulated/applied plans. A package audit warning while a
   known transaction is running is not proof of corruption.
5. If a firewall change caused a lockout, use the local console and the reviewed
   private rule backup. `sudo ufw disable` is the emergency rollback. For future
   policy changes, arm a short rollback timer **before** editing, then cancel it
   only after a fresh administration connection succeeds.

Driver installation has already survived one reboot with Secure Boot enabled.
Do not disable Secure Boot, edit partitions/boot entries or reinstall a working
driver because a model fails. Package upgrades may regenerate an initramfs;
record any reboot requirement and stop experiments before rebooting.

The private storage check found a USB 2 link on the external root SSD. This is
an I/O bottleneck, not evidence of an SSD fault. Any later cable/port change must
happen with the machine shut down; never unplug the mounted root filesystem.

## Container rollback and privileges

The GPU check uses an ephemeral official CUDA base image, by its resolved digest,
with network disabled, read-only root, dropped capabilities, no host mounts and
no published ports. Keep its digest/result in the private log. A container seeing
the GPU qualifies that path only; it does not qualify a model or its outputs.

To roll back container integration, stop affected containers first, restore the
reviewed Docker daemon configuration backup, remove only the Haven ingress
drop-in/helper if retiring Docker, and reload/restart Docker. Package removal
must preserve images/volumes and the private record. Do not delete
`/var/lib/docker`, change disks, or add the agent to the Docker group as a shortcut.

## Claude Code and Codex sessions

Both CLIs are available on the administration Mac. Start from the appropriate
owned checkout, read `CLAUDE_NEXT_SESSION.md`, and use the existing SSH alias.
The server has no forwarded GitHub token: synchronize reviewed branch commits
with a Git bundle over SSH. Keep the Lab and distillation ancestry separate.
Push useful code and sanitized aggregate receipts; keep the implementation log
and connection appendix private. Neither CLI needs unrestricted sudo to edit,
test, run the user services or use local inference.
