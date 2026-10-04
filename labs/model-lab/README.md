# Haven Model Lab

A runnable Windows-first browser workbench for **Strata + llama.cpp CUDA**, built for an RTX 2070 Super 8 GB, Ryzen 3900X and 64 GB RAM. This is actual application source, not a coding-agent handoff. It is a separate development lab: it does not modify or resume Haven IP-01/IP-02.

## Start on your PC

1. Extract this entire folder somewhere roomy and not synced, such as `D:\AI\haven-model-lab`. Do not run files inside the ZIP. Keep all files together.
2. Double-click **START-HERE.cmd**. On the first run, approve a folder-local, SHA-256-pinned Python 3.13.16 download from python.org. No existing Python or PATH is changed. The app itself needs no pip packages.
3. The browser opens your private launch link at **127.0.0.1:8787**. Keep the console open. The token is removed from the address bar and held in tab session storage. A plain URL without a launch session cannot operate the API.

**Strata path — the requested new engine:** run **SETUP-STRATA.cmd**, read the RAM/disk/driver warning and type `STRATA` to approve its large upstream installation. Then run **START-STRATA.cmd** and choose **Setup & engines → Connect locally** in the lab (default `http://127.0.0.1:8080/v1`). You can also open Strata's native UI. Use a roomy SSD: the helper requires 100 GiB free to allow the roughly 70 GB model plus preparation/headroom. Nothing large downloads merely by opening this lab.

**Small-model CUDA path:** in **Setup & engines**, click **Install pinned CUDA engine** (~645 MB, official llama.cpp + runtime DLLs), then **Model library → Qwen3.5 4B → Download** (~2.74 GB). After download/hash verification, click **Load on GPU**. Begin with the default Desktop-friendly profile, 4K context, f16 KV. Check GPU readings and the engine log. No CUDA Toolkit or compilation is required for this path.

For repeat visits, run START-HERE.cmd. Installed files stay in `.local/`; no download is repeated unless the file is missing or a verification step requires attention. The lab intentionally does not auto-load a model. Strata runs in its own console, and its upstream downloader supports resume. Existing GGUF models can be registered by exact file path without copying/scanning your disk.

## What works in this version

- Streamed text chat through Strata or another explicitly selected literal-loopback OpenAI-compatible server.
- llama.cpp CUDA model launch/unload with one request slot, full-layer offload requested, and Windows Job Object ownership for processes created by this lab.
- A four-model checksum-pinned starting catalog (two 2026 Qwen3.5 candidates and two established Qwen3 baselines), resumable downloads, and local GGUF registration.
- NVIDIA GPU utilization/VRAM/temperature, available system RAM and disk measurements; missing readings are unknown, not zero.
- Backend-specific reasoning controls, output limits, repeatable benchmark prompts, raw result exports and conversation export.
- Explicit no-cloud/no-account design, no CDN assets, token and same-origin checks, inert model output, no automatic code/tool execution, no automatic downloads on app startup.

**Not yet PC-validated:** automatic Windows setup, official Windows binary execution, Windows Job Object semantics on your host, NVIDIA driver/model compatibility, real Strata generation and performance. The included HTTP tests execute actual local software behavior with a clearly labelled fake inference server. Live browser navigation was blocked by this environment; only separate in-memory static layout renders were inspected; see `docs/TEST_REPORT.md`. This is a development preview, not an independent security audit or a tested installer on your PC.

## Your hardware: sensible defaults

Strata's pinned docs list RTX 20 support, but call 8 GB slow. It can consume roughly 35–55 GB system RAM. This is the large-model experiment, not a guarantee of a 5070's throughput. The helper starts with **8K context, one request, image input off and 1024 MiB display reserve**. Its source is pinned at v0.1.39. Actual upstream package/model downloads are handled by its installer, not by an invented llama.cpp compatibility layer. The installer is third-party code; review its prompts and decline system build-tool changes.

Small 4B Q4 GGUF models leave more GPU headroom. The lab asks for `--n-gpu-layers 999 --device CUDA0` (or the first detected NVIDIA GPU), so CPU-only fallback is not silently chosen. Runtime logs still determine what actually offloaded. Model file size is not total runtime VRAM. The launch memory check is a conservative heuristic, not a model-specific allocator prediction. Qwen3.5 9B can be tight on 8 GB; shorter context or the 4B model is preferable to paging.

The quantized-KV preset is explicitly experimental. Flash-attention and q8_0 KV require compatible model/build kernels. An error stays an error; change the profile deliberately. Do not run Strata and another loaded model at once. GPU utilization is device-wide (other apps count) and full utilization is not the optimization objective.

## Stop, privacy, and local files

Use **Unload owned engine** for a llama.cpp process created by this lab. Use **Exit lab**, or Ctrl+C in its console, to stop the lab and its owned engine. The Windows process gate assigns the child to a kill-on-close Job Object before allowing the engine to launch. That path is source-implemented but requires Windows verification. No process-name-wide kill is used.

**External Strata is never killed by the lab.** Stop it in its own console. Chat cancellation closes the local HTTP stream; it does not independently prove the external backend stopped computation. The UI says so. An interrupted result is not automatically replayed.

Chat is held in tab/process memory during the session; export is explicit. Benchmark files record prompt hashes, settings, outcomes and hardware metadata, not prompt contents. Upstream model logs may contain their own data. `.local/engine.log`, model paths, API-key file and benchmarks stay local and are gitignored. The lab transiently accepts a backend key in process memory; it is never sent to the browser again. Do not place real secrets/bank data into a development model test. This is not multi-user authentication, a hostile-local-user boundary, or a production internet server.

Initial installs use internet downloads. Inference requests use literal 127.0.0.1 only, with no proxy/redirect/cloud fallback. Upstream engines have their own behavior; we do not claim OS-level egress isolation. No startup service, scheduled retry, driver update, overclock, pagefile edit, firewall exception, or LAN/tunnel exposure is created. Windows script policy is bypassed for the current helper process only; nothing persistent is changed. Do not bypass an organizational execution denial.

## Troubleshooting

**NVIDIA telemetry missing:** run `nvidia-smi` in a terminal. The lab will not silently choose CPU. Driver updates are your action, not performed by these scripts.

**llama-server fails to load a DLL:** inspect `.local/engine.log`; a current Microsoft Visual C++ runtime may be needed. No runtime or driver installer is silently added. CUDA 12.4 requires a compatible installed driver.

**Strata driver warning:** the helper follows the upstream CUDA 12 option for drivers below 580 (minimum 528 checked); otherwise upstream chooses its normal path. This is not assurance every older driver supports every feature. Stop on a mismatch instead of forcing a driver change.

**Port 8787 already used:** close your earlier lab console or run `python server.py --port 8788 --open` from this folder. Nothing occupying that port is killed. For Strata, adjust the actual setup port and type that same literal-loopback address in the UI.

**Checksum mismatch:** download remains uninstalled. Remove the affected `.part` file after inspecting it and retry explicitly, or register a separately downloaded verified local GGUF. Catalog URLs use `main` but SHA-256 pins the bytes; a moving upstream file cannot silently become an update.

**Memory error or desktop slowdown:** unload the engine, stop other model servers, reduce context, and use 4B. Strata's upstream pagefile advice is not an instruction for this lab to change Windows. Do not continually retry a heavy failing load.

**Installer scripts:** PowerShell was not available in the development container. Read `bootstrap.ps1` and `strata-setup.ps1`; neither was executed on a Windows PC in this delivery. The Python metadata and official CUDA release hashes were verified against primary sources. Strata source uses a pinned commit archive; its archive hash is recorded at installation, not pre-verified from an upstream published digest.

## Tests / development

With Python 3.11+ in this folder: `python -m unittest discover -s tests -v`.
Optional browser checks require an existing Playwright + Chromium installation; they are development-only, not runtime dependencies. `python tests/browser_smoke.py` is the live-browser test script for a permitted development host; it was blocked here before page navigation. `python tests/render_static.py` separately renders the actual HTML/CSS in memory, without navigating or running the app, and writes screenshots under `artifacts/`. Static renders are not live browser acceptance.

The refined implementation brief is `docs/REFINED_PROMPT.md`. Research, source links, and proposed—not proven—efficiency hypotheses are in `docs/EFFICIENCY.md` and in the UI. No coding agent or real model has been falsely credited with executing the local fixture tests.
