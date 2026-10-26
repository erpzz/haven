# Haven Core Model Lab on Linux

This deploys the existing Model Lab with Python 3.11+ and the standard library.
It starts with no inference engine or model loaded. Historical Windows GPU
qualification remains separate from Linux qualification.

The user service expects the checkout at `~/projects/haven`. Its HTTP listener
is `127.0.0.1:8877`; use an SSH local forward from the administration computer.
The launch link is a bearer credential stored with mode 0600 at
`~/.local/state/haven-model-lab/launch-url`. It is deliberately absent from the
service journal. Each restart rotates it; reopen the current link afterward.
Runtime data stays outside the checkout in `~/.local/share/haven-model-lab`.
The systemd unit reports readiness only after the private launch link and HTTP
listener are initialized, so a successful start can be followed immediately by
an authenticated request.

## Install and run

Run these as the ordinary account that owns the checkout:

```sh
install -d -m 700 ~/.config/systemd/user
install -m 644 ~/projects/haven/ops/haven-core/systemd/haven-model-lab.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now haven-model-lab.service
```

The optional pinned Linux CUDA engine also requires the Ubuntu `libgomp1`
runtime package. A minimal server may not have it. Install it through the
administrator's normal package workflow before loading a model; a missing
`libgomp.so.1` is reported in the private `engine.log`. The Lab does not silently
install operating-system packages or fall back to CPU inference.

For operation after logout and at boot, a human administrator can explicitly
enable lingering for that account with `sudo loginctl enable-linger "$USER"`.
This grants no new sudo permission. The service itself runs as the ordinary
account with `NoNewPrivileges=yes` and contains only its own process group.

From the Mac checkout, open the lab with the stdlib helper:

```sh
python3 ops/haven-core/open-lab.py
```

The helper starts the service if needed, establishes an owned loopback SSH
tunnel, reads the current private link without printing it and opens the
browser. `--prepare` prepares access without opening a browser; `--close`
closes only its tunnel. An unrelated listener on port 8877 is left alone.

For a manual session, forward the same loopback port:

```sh
ssh -N -L 127.0.0.1:8877:127.0.0.1:8877 haven
```

Read the private launch link over authenticated SSH and open it locally. Do not
paste it into a public issue, screenshot, journal or implementation receipt.
The existing browser removes its token from the address bar and keeps it in
that tab's session storage. API authentication and origin/Host checks remain
enabled. No LAN listener or public port forwarding is required.

## Choose CPU-only chat while the GPU is busy (candidate implementation)

This feature is in **feature/hs01-cpu-lane-browser-20261026**; it is **not deployed or measured on Slink yet**. Verify on the live Mac → SSH tunnel → Haven browser path before claiming success.

The Model Lab Linux **Setup → llama.cpp → Compute lane** control can explicitly choose:
- **GPU · CUDA fast path**: the existing full GPU-offload model, unchanged by default.
- **CPU only · no GPU layers**: same downloaded GGUF via the already pinned llama.cpp server with `--n-gpu-layers 0`, no `--device`, and `CUDA_VISIBLE_DEVICES=-1` scoped **only** to that spawned model process. Default CPU preset: 2K context, 6 threads, 128/64 batch, f16 KV, flash attention off; reject over 8 CPU threads or 8K CPU context.

CPU start uses available **MemAvailable** from Linux, includes an explicit conservative 4 GiB host reserve, and rejects unknown or insufficient available RAM. The GPU memory-risk override does not apply. This prevents pretending CPU mode is free when Strata or a training worker consumes most of the 64 GiB.

**Current architectural limit:** the browser's Model Lab can own only **one GGUF process at a time** (CPU *or* GPU), though separately launched Claude/Codex GPU experiments remain untouched. If the Lab already owns a GPU process, you must unload **that Lab-managed process** before CPU loading, and only if no agent depends on it. There is no automatic switch or killing external Strata/GPU workers. A true two-process, separately routable always-on CPU+GPU service is later scope.

From the **Mac**, use the documented local tunnel and private launch link; these are not LAN/public endpoints. Select the CPU lane, choose the **already-downloaded Qwen3.5 4B** in Models, click **Load on CPU**, then chat normally. The status must explicitly show **CPU-only connected**. The same launch credentials and admin/member access controls remain in force.

**Live acceptance (must be performed by an agent/operator with Slink access):**
1. Before any change, check active Claude/Codex/Lab processes, GPU ownership, Lab users and deployed commit. Do not stop a GPU job merely to test CPU.
2. Run unit regressions: `python3 -m unittest discover -s labs/model-lab/tests -p 'test_cpu_lane.py' -v`; run existing Linux integration/security tests after. Classify these as **STATIC_TEST** only.
3. Install/reload the candidate UI/runtime only with an explicit safe deployment/restart window. A restart of `haven-model-lab.service` will stop **its owned model** and invalidate its old private launch link; **never restart while any agent depends on the Lab**.
4. Start Qwen3.5 4B CPU from actual browser: verify llama arguments show `--n-gpu-layers 0` with no `--device`; inspect process environment privately to confirm `CUDA_VISIBLE_DEVICES=-1`, and verify via before/during GPU telemetry that the CPU model did not allocate VRAM. GPU may remain busy with independent owned workloads.
5. Send an actual short question; record real first output and decode throughput, model quality, CPU/RAM, port/connection auth, and host impact. Do not claim speed from simulated tests.
6. Explicitly compare unchanged GPU mode when GPU is available and safe to do so. Validate cancellation/unload, denied admin writes from member sessions, no external server disruption, no model downloads and no secret leakage.
7. Roll back the candidate commit or restore the known-good PR #36 tree if live CPU loading fails; use only owned service stopping and preserve Qwen GGUF/Strata files.

The first candidate is intentionally a **minimal isolated CPU inference choice**, not a CPU-powered autonomous agent or dual-running GGUF router. If GPU work saturates host memory or CPU, admission may correctly refuse to start or performance may be poor.

## Operate and recover

```sh
systemctl --user status haven-model-lab.service
journalctl --user -u haven-model-lab.service -n 40 --no-pager
systemctl --user restart haven-model-lab.service
systemctl --user stop haven-model-lab.service
```

An ordinary successful UI shutdown leaves the service stopped; restart it
explicitly when wanted. Unexpected process failures receive at most three
start attempts per minute. The service's stop contains its own child processes;
an attached external backend is not owned or stopped by the Lab.

Rollback: `systemctl --user disable --now haven-model-lab.service`, remove only
the installed unit and reload the user manager. Preserve runtime data. Disable
lingering only if this deployment enabled it and no other user services need it.
Stop the owned Mac SSH tunnel to close local access. No driver, model, firewall,
bootloader, global Python package or inference-framework changes are performed.
