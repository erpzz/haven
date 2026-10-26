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

## Explicit CPU-only inference in the browser (proposed branch)

The Model library now offers an explicit **Inference device** selector:

- **GPU CUDA** preserves the known-good llama.cpp path (999 offload layers and a selected CUDA device).
- **CPU-only** launches the same already-installed llama.cpp executable with `--n-gpu-layers 0`, no `--device` argument, and `CUDA_VISIBLE_DEVICES=-1` for **that child process only**. It never rewrites the NVIDIA environment of Codex, Claude, Strata or system-wide services.

Choose CPU-only in **Model library**, select a previously downloaded GGUF (the existing Qwen3.5 4B is a sensible initial test), and click **Load on CPU**. The connected-model indicator labels the selected lane. No extra model download, Windows reinstall or filesystem move is necessary.

**Important deployment status:** this feature is implemented in a separate review branch until merged/deployed; Slink's already-running binary does not change merely because the GitHub branch exists. Plan the service restart with the operator and other agent workloads. Run a live browser/inference smoke test before declaring it usable.

Resource boundaries: CPU-only clamps CPU threads to eight (default six), 8K maximum context (default 4K), 128/64 batch/microbatch, f16 KV and flash attention off. A conservative startup gate requires observed free RAM sufficient for estimated model + context overhead **plus an 8 GiB reserve**. This guard is heuristic, not actual RSS measurement. Existing GPU launch validation and VRAM fit gates are preserved; no automatic fallback from GPU to CPU.

The current Model Lab owns **one** managed llama.cpp engine at a time; CPU and CUDA can both be **selected** but are not independently simultaneous within the same Model Lab instance. To switch a Lab-owned running model, click **Unload owned engine** first and then load the new mode. This operation is explicitly operator-initiated and stops only the Lab's own process group, not another agent or external Strata. A CPU-only Lab session **can coexist with separate Codex/Claude GPU jobs**, subject to shared CPU/RAM/SSD pressure. If you need true simultaneous CPU and GPU conversations in the same browser, implement a second independently owned backend and routing rather than pretending a selector does that.

On Slink, verify CPU-only without touching another agent's GPU work:

1. Confirm the service is using the approved CPU selector branch and that the SSH tunnel is active. If Mac port 8877 already has a listener, inspect its owner before creating another tunnel.
2. In Model library choose **CPU-only** and load a downloaded GGUF; do not hit Unload while someone else is using the Lab's current managed backend.
3. Send a short real chat message. Confirm the connected badge says **CPU-only**, the engine log includes `--n-gpu-layers 0` (and no `--device CUDA0`), and an actual response succeeds through the authenticated browser. Do not infer no GPU work just from a static launch command: check the child process and `nvidia-smi` while inference runs to see whether it allocated GPU memory.
4. Compare measured response quality, TTFT, tokens per second and resident RAM against the same prompt on the existing GPU path when GPU time is available. Record slow/failed outputs as evidence, not a pass.

Rollback: unload the Lab-owned CPU process, revert the scoped PR or reset the approved deployment revision, restart only the Lab user service with coordination, and reload the prior CUDA model. No stored model/Windows partition is rewritten.

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
