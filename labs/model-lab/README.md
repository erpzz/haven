# Haven Model Lab

A Windows browser workbench for Strata and llama.cpp CUDA. The October 4, 2026 qualification uses an RTX 2070 SUPER 8 GB, Ryzen 3900X and 64 GB RAM. This lab is separate from Haven IP-01/IP-02.

## Open the installed lab

Double-click **OPEN-LAB.cmd**. It starts the folder-local Python runtime and opens the private browser launch link at `127.0.0.1:8787`. Keep its console open. A plain URL does not grant API access; the private launch token is removed from the address bar and retained in that tab's session storage. The lab deliberately starts with no model loaded.

For the verified small-model path, choose **Model library → Qwen3.5 4B → Load on GPU**. Use **Desktop-friendly CUDA**, **4096 context**, **6 CPU threads**, f16 KV, one request and reasoning off. The existing model and CUDA files are reused. No CUDA Toolkit is needed for this official binary path.

For Strata, use **OPEN-STRATA.cmd**, then **OPEN-LAB.cmd → Setup & engines → Connect locally** with `http://127.0.0.1:8080/v1`. Strata's native UI is at `http://127.0.0.1:8080/`. Use the retained **4096 context / 2048 MiB requested VRAM reserve**, one request, images off and reasoning off. Strata qualification and its measured limitations are recorded separately in the [current PC qualification report](docs/PC_QUALIFICATION_v2.md); installing files alone does not establish inference success. Avoid loading two models on this 8 GB GPU.

**STOP-LAB.cmd** stops the lab and its owned llama.cpp process tree. **STOP-STRATA.cmd** requests native unload and stops only the Strata process tree created by its matching launcher. The UI's **Exit lab** also stops the lab; **Unload owned engine** releases its llama.cpp model. Disconnecting an attached Strata server leaves that separate server running. The stop controls authenticate to loopback controllers and use Windows Job Objects; they never kill every process with a matching name.

`START-HERE.cmd` and `START-STRATA.cmd` are compatible aliases. On a fresh checkout, START-HERE first offers the pinned folder-local Python runtime download. A PowerShell alternative, `./launch.ps1 -Kind lab`, opens with a hidden controller; add `-Stop` to stop the corresponding controller, or `-NoBrowser` for automated qualification.

## Home-network access and invite-only accounts

The qualified loopback workflow above remains the default. To use the same running Model Lab from a MacBook or iPhone on the same trusted home/private network, first run **ENABLE-LAN-FIREWALL.cmd** once as administrator, then run **OPEN-LAN.cmd** instead of OPEN-LAB. The firewall helper creates a narrow inbound rule for TCP 8787 only, scoped to the Windows Private firewall profile, LocalSubnet, and this installation's folder-local Python executable. **DISABLE-LAN-FIREWALL.cmd** removes that named rule.

The first LAN launch opens a private one-time owner-setup link on the Windows PC. Create the owner/admin account there. After that, the launcher prints one or more private-IP URLs such as `http://192.168.x.x:8787/`; open that URL from the MacBook or iPhone while both devices are on the same home network. LAN access is **invite-only**: there is no public registration. From the Account panel, an administrator can create a single-use invite link that expires after 24 hours. The invitee chooses their own username and password.

Passwords are stored locally with per-user scrypt salts/hashes. Invite and session bearer tokens are stored only as SHA-256 digests in `.local/auth.sqlite3`; the browser session uses an HttpOnly, SameSite=Strict cookie plus a per-session CSRF token. Five failed logins from one source address within five minutes are throttled. Member accounts can chat and view ordinary model state, but only administrators can install/import models, connect/disconnect engines, inspect engine logs/benchmarks, create/disable accounts, or shut down the lab. Generation-job status/cancellation is scoped to the account that created the job.

The LAN server accepts only loopback/private source addresses, rejects cross-origin requests, and requires a private-IP/localhost Host header. It deliberately **does not provide TLS and is not intended for port-forwarding, public Wi-Fi, VPN-wide exposure, or the public internet**. The inference backends themselves remain bound to `127.0.0.1`; only the Haven web UI/API listens on the LAN. Strata's native UI therefore stays on the Windows host rather than being directly exposed.

The UI includes a 390×844 iPhone-sized browser regression covering owner setup, invitation redemption, member-role restrictions and horizontal-overflow checks. Narrow-screen CSS uses safe-area insets, 44 px controls and 16 px form text to avoid iOS Safari auto-zoom. `tests/browser_lan_smoke.py` is a test-double/browser check, not real-model qualification.

## Fresh installation

Keep this whole folder together on a roomy SSD and run outside the ZIP. Runtime files remain in `.local/`. **SETUP-STRATA.cmd** offers the explicit large Strata installation; no large download starts merely by opening the lab. The Strata helper requires 100 GiB free for model and preparation headroom. Current pinned IQ2_XS shards total 68,026,093,024 bytes, with additional MTP and prepared files.

The installer pins Strata v0.1.39 source, official Windows engine assets and model bytes. Its scoped wrapper verifies reused files, keeps packages/data inside this installation, blocks build-tool installation and global migration, and constrains cleanup to validated paths without junctions. Only the needed pinned llama.cpp GGUF Python source is extracted, avoiding Windows path-length failures. Failed transfers remain available for inspection. A checksum mismatch never becomes an accepted model.

The Python 3.13.16 runtime comes from python.org and is verified before extraction. The official llama.cpp b11146 CUDA 12.4 engine and runtime DLLs are downloaded through **Setup & engines** if absent. The model library provides checksum-pinned downloads and exact-path registration for existing GGUF files.

## Qualification and recommended settings

Actual Windows execution verified the folder-local runtime, official CUDA binary, all 33 Qwen3.5 4B layers offloaded to CUDA0, browser chat, known arithmetic and extraction, cancellation, another request, unload, stop and reopen. Device VRAM rose from about 1.1 GiB to 4.0 GiB with the default 4K profile and returned near idle after unload.

Four small-model profiles completed 24/24 fixed tasks correctly. Their warm three-task totals ranged from 2.32 to 2.40 seconds. More threads and larger batches produced no useful improvement; q8_0 KV saved about 52 MiB with no task-time improvement. Keep the everyday profile above. These are short synthetic tasks, not a general model-quality evaluation. Cold initialization is recorded separately from warm measurements.

Benchmarks capture the selected connection, workload, label and sampling settings once. Changing controls during the run does not silently switch a repetition to another backend or configuration. Records separate local first-output latency, total request time and backend-reported prompt/decode durations and rates. Stream chunks are not counted as tokens. Read the answer as well as the timings.

The original handoff and manifest remain historical evidence. `docs/TEST_REPORT.md` describes the earlier environment's limitations; it does not describe the later Windows qualification. Current results and experimental recommendations belong in the [new PC qualification report](docs/PC_QUALIFICATION_v2.md).

## Privacy and retained files

Inference backends use literal loopback addresses with no proxy, redirect or cloud fallback. The browser has no CDN assets. Account data, session-token digests, logs, model paths, benchmark runtime data, Strata data and weights remain local and gitignored. Chat stays in each browser tab's memory unless explicitly exported. Backend logs may retain their own inputs. Output is displayed as inert text; it does not execute code or tools.

Default OPEN-LAB remains a single-user loopback development mode. OPEN-LAN is an explicit multi-account trusted-home-network mode with the additional controls described above; it is still not a hostile-network or internet-facing security boundary. Initial downloads require internet access. No startup service, scheduled retry, driver update, pagefile change or reboot is created. LAN exposure occurs only when the operator explicitly launches OPEN-LAN and permits the scoped Windows firewall rule. Installer/helpers may use a process-local PowerShell execution-policy option; it changes no persistent policy.

Local evidence is under `.local/setup/20261004/`; launcher logs and final stop receipts are under `.local/launcher-lab/` and `.local/launcher-strata/`. Private launch receipts contain tokens and must not be published. Models are retained for reuse. The source report contains sanitized results only.

## Troubleshooting and development

If a port is already occupied, stop the matching launcher if it belongs to this installation. A foreign listener is not killed or reused. Lab uses ports 8787/8788; Strata uses 8080/8081. Inspect the retained launcher log if startup fails. Missing NVIDIA telemetry remains unknown, not zero. No automatic CPU fallback is reported as CUDA success.

For a checksum mismatch, preserve the failed file and obtain a fresh verified copy before retrying; do not change a pin to match a failed transfer. For memory pressure, stop the owned model and reduce context. Upstream pagefile advice does not authorize changing Windows. Do not repeatedly retry a heavy failing load.

With Python 3.11+: `python -m unittest discover -s tests -v`. Windows tests exercise actual Job Object containment and controller stop behavior. Optional `python tests/browser_smoke.py` and `python tests/browser_lan_smoke.py` require an existing Playwright/Chromium installation and label browser/inference fixtures appropriately. The LAN smoke uses a 390×844, 3× device-scale viewport for iPhone-class responsive behavior. Real model qualification is separate. Playwright is a development dependency, not a runtime dependency.

Research and upstream efficiency hypotheses remain in `docs/EFFICIENCY.md`. Upstream speed claims are not measurements on this PC. `MANIFEST_v2.sha256` is the immutable October 4 inference-qualification manifest and intentionally remains a historical baseline; the later LAN/authentication extension adds and changes files beyond that manifest rather than rewriting the already-qualified record.
