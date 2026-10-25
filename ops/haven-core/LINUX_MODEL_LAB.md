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
