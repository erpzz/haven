# Haven Model Lab — local Windows setup and qualification

Prepared 2026-10-04. This is an operator-launchable setup assignment, not evidence an agent has started. Open the extracted Model Lab folder in a coding agent executing on the target Windows PC. Do not run this assignment only in a remote/cloud workspace and call that PC acceptance.

## Goal

Turn the supplied source preview into a working, easy-to-reopen local model playground on the operator's reported Windows 11 PC: RTX 2070 Super (8 GB VRAM), Ryzen 9 3900X, 64 GB RAM. Verify the actual hardware rather than treating those reported specifications as observations.

Complete one coherent setup session with review checkpoints: inspect and address narrow installer/test defects; establish a small-model CUDA baseline; separately install and qualify Strata after the operator approves its large download; hand back useful start/stop controls and measured results. This is a separate lab, not a restart of Haven IP-01/IP-02 or JEV-01. No Jev, hosted inference, new agent framework, or agent-to-agent protocol is needed to run the local model lab.

## Exact input and current evidence

Input archive: `Haven-Model-Lab-v0.1.0-Windows.zip`

SHA-256: `e1896c14a8a6513cd1a7f24754684b224099a80af87547f2e13166f8d833f6c0`

The archive contains a `haven-model-lab/` directory with README, bootstrap/Strata PowerShell helpers, Python backend, browser assets, catalog and tests. The archive is supplied as a chat attachment; do not assume that its source is already published to the Haven GitHub repository or that a `sandbox:` link can be opened from the PC agent.

The preparing assistant reopened the archive, verified 29 entries in `MANIFEST.sha256`, and reran `python -m unittest discover -s tests -v`: 46 passed on Linux in 12.644 seconds. These are same-author software checks, not independent review, Windows acceptance, or real model benchmarks. Windows setup, CUDA inference and Strata inference remain unverified. A hash establishes byte identity, not software trustworthiness.

Read `README.md`, `docs/REFINED_PROMPT.md`, `docs/TEST_REPORT.md`, `docs/EFFICIENCY.md`, `bootstrap.ps1`, `strata-setup.ps1`, `labcore.py`, `process_gate.py`, `winjob.py` and the tests before installation.

Known first-PC review items:

- `tests/test_lab.py::ProcessTests` skips its three process tests on Windows. Add bounded Windows-specific benign tests for the actual launcher/Job Object; skipped tests are not passes.
- `tests/browser_smoke.py` assumes the GPU indicator contains `GPU telemetry` (the missing-GPU condition). On a real NVIDIA machine, either isolate that expectation with a clearly marked test hardware fixture or assert the appropriate actual state. Do not erase the meaningful startup checks.
- That browser script passes `--no-sandbox`. Do not reuse this container-style option on the PC; use normal supported browser sandboxing. Also ensure services are cleaned up when a browser is absent or fails to launch, not only after page navigation.
- Verify the exact Python archive, import path, SSL support and ability to create a Strata venv with pip. Do not assume an embeddable Python distribution has full development features. Verify upstream Strata setup arguments and dependency sources before executing them.

## Authority and work organization

This document grants no execution by its mere presence. Begin only after the operator explicitly asks the local agent to follow it. Use normal tool approvals and the selected project workspace, not unrestricted machine access. A root installer may use one actual independent read-only reviewer or test child if supported; record who did what. Do not invent child activity or claim the original author is an independent certifier. One owner changes scripts; one installer/download stream and one GPU model run at a time.

The selected extracted folder is the writable project scope. Use `.local/setup/<run-id>/` for records, temporary files, patches and logs. Do not search unrelated personal directories for models, keys or credentials. Existing models may be used only at exact paths selected by the operator. Preserve the original archive and manifest; record before/after file hashes and diffs for narrow fixes. Do not regenerate the old manifest to hide changed bytes.

Start with read-only preflight and a proposed grouped installation plan. Ask once before the initial runtime/CUDA/model downloads, and separately before Strata's large download. After each approved phase, proceed with routine local fixes/tests inside its scope without per-line operator handoffs. A changed dependency source, broken checksum pin, exhausted resource envelope, external disclosure or system-level change requires a new decision, not automatic acceptance.

Do not alter GPU drivers, firewall, antivirus, execution policy, security/sandbox settings, pagefile, registry, PATH, power limits, clocks, shared Python environments or persistent services. The existing .cmd launchers use a process-scoped execution-policy option: inspect it and request the normal permitted action rather than extending it or bypassing an actual policy denial. Driver/VC++ runtime/build-tool requirements must be reported with their official source for an operator decision. Do not use full-access mode simply to make a failed test pass.

No purchases, extra provider credit, cloud inference, real accounts, employer/household private data, LAN/public listeners, tunnels, startup tasks, autonomous retries, or unowned-process termination. The setup assistant may itself use hosted reasoning; local model inference does not make everything the coding assistant reads private/local. Keep its context confined to this project and sanitized diagnostics.

## A — preflight and bounded repair, no heavy downloads

Verify the archive when present and its manifest before changing files. Confirm the actual Windows/native PowerShell environment, NVIDIA driver/device/VRAM through `nvidia-smi`, installed/existing Python availability, total and available RAM, project drive's available space, and whether storage type is reliably known. If SSD/NVMe type is unknown, report UNKNOWN rather than infer it from a drive letter. Check intended local ports and exact known processes without stopping anything. Avoid a broad host inventory.

Review the known harness gaps. Make narrowly justified portability fixes inside the project, with before/after hashes and retained failures. Do not install test frameworks automatically; use already available tools or include a minimal isolated developer test dependency in the operator-approved plan. Manual observed browser checks are acceptable when honestly labelled; report missing automated coverage.

Write `checkpoint-A.md`: verified input, relevant hardware facts, existing tools, free RAM/disk, fixes made, remaining blockers, proposed official artifacts and expected download/disk footprint, source/hash checks, and what needs approval. No real usernames, machine serials, API tokens, private paths or credential-bearing URLs in the shareable version. Pause for the operator to approve the initial download plan. The operator can send this checkpoint to ChatGPT for review; do not claim that ChatGPT has already read it.

## B — minimal real CUDA baseline

After the grouped approval, validate/install the folder-local Python runtime and official pinned llama.cpp CUDA assets. Reject checksum mismatch; do not simply replace expected hashes with the bytes received. If an upstream URL moved, verify the legitimate replacement provenance and obtain approval for a revised pin. Do not use a cloud model or silently switch to a CPU build.

Use the catalog's pinned Qwen3.5 4B Q4_K_M starter, or the exact operator-approved existing equivalent. Verify file size/hash and source license information. Begin at the existing Desktop-friendly profile: 4K context, f16 KV, one request, full CUDA layer offload requested. The pinned scripts and catalog, not guessed latest flags, control implementation.

Before launching the model, execute benign Windows lifecycle checks: exact owned launch/stop, duplicate-launch rejection, containment before descendant launch, parent termination/kill-on-close where safely testable, stale-owner isolation, and refusal to restart after unconfirmed cleanup. Use exact handles/birth identities and an independent bounded observer, never process-name-wide killing. If containment cannot be established, stop that launch lane and report it.

Start the actual UI. Run at least one real end-to-end browser chat, a known-answer synthetic extraction, cancellation during generation, a fresh request after cancellation, and explicit unload. The fake HTTP backend is useful for protocol tests, not evidence of GPU inference. Record actual CUDA device and offloaded-layer log evidence, baseline versus loaded VRAM, response/first-output timing, backend-reported tokens and timings, errors, and observed post-unload processes/memory. Device-wide utilization alone cannot prove which process used the GPU; distinguish reported counters from independent observations.

Start with no more than 8 short model requests and 15 minutes of inference in this phase, including failed/cancelled/repeated calls. Loading/compile/download time is separate. One failed heavy launch is a diagnostic event; inspect and repair or deliberately change one setting before at most one retry. Do not loop heavy launches until they work. If a bound prevents useful verification, report the incomplete result instead of silently extending it.

Write `checkpoint-B.md` with exact candidate/configuration, passes/failures/skips, browser observations, real GPU evidence, useful-answer correctness, and cleanup. Stop and confirm the owned llama.cpp model is unloaded before Strata uses the GPU. A residual above idle VRAM does not automatically mean a leak; Windows/display/other applications also use memory. Use process identity and a fresh baseline.

## C — Strata remains the requested target, not an abandoned optional idea

After the CUDA baseline, prepare Strata's installation plan from the pinned `Niko1221/Strata` source. Show the operator the approximately 70 GB model download and 100 GiB free-space requirement in the current helper; verify the actual selected artifact/dependency footprint before proceeding. Explain substantial system-RAM use and the 8 GB GPU limitation without promising another GPU's throughput. Require a separate explicit approval before this phase's download.

Review the upstream code path: no global installs, driver/system-build tools, telemetry configuration, or other side effects may be accepted just because an upstream prompt says yes. Keep upstream caches, dependencies and temporary files in the selected project-local locations. If that cannot be ensured, report the deviation for approval. Package lock/pin limitations must remain visible.

Reuse current conservative Strata settings: IQ2_XS, 8K context, one request, images off, 1024 MiB VRAM reserve. Check *available* memory before loading; report the expected peak and preserve desktop headroom. With 64 GB installed, a paging/thrashing machine is not an acceptable success. Check system commit/pagefile facts read-only if relevant; do not change them. No second loaded model at the same time.

Test Strata's native UI first, then connect Haven Model Lab to its actual literal-loopback API. Limit initial smoke testing to 8 short requests and 15 minutes of inference, including cancellation/repeats; no indefinite generation or unrequested agent tool execution. Distinguish Strata's externally owned process from the lab-owned llama.cpp engine. Disconnecting the lab or cancelling its HTTP request is not proof that Strata stopped computing. Stop it with its observed supported control and verify owned-process state. Preserve any uncertainty, partial download or failed attempt.

Write `checkpoint-C.md`: native Strata outcome, integrated UI outcome, exact model/engine/source pins, request counts, latency/quality/resource observations and separately verified shutdown for both applications. If Strata is blocked, deliver the working small-model path but mark Strata BLOCKED/PARTIAL, not completed or silently replaced.

## D — light tuning and handoff

Only after the above passes should optimization begin, with the operator approving the specific bounded comparison. Change one variable at a time; compare the same prompt and output cap, label cold/warm runs, and keep cancelled/failed results. Start with 4K versus 8K context, then f16 versus compatible q8 KV or a small thread sweep. Avoid exhaustive auto-tuning, extra model downloads, or speculative-decoding modifications during installation. A faster incorrect answer is not a performance win.

Finish with two or three measured, clearly labelled profiles, or only the verified baseline if tuning was not requested. Provide exact reopen/stop instructions and optionally user-approved launch shortcuts only for existing project scripts. Do not add a startup service or leave inference running as a surprise. Shut down after verification unless the operator explicitly requests an interactive session now. Preserve installed binaries/models for the next manual launch.

The final operator report should fit roughly one page: what works, how to open it, what was downloaded/changed, measured configurations, known gaps, where local results live, and how to stop everything. No fake benchmark numbers, summed skipped tests, claims of independent review without a real reviewer, or claims of direct live supervision by ChatGPT.

## Working with the ChatGPT project adviser

The local agent owns local execution, resources, emergency stop and permissions. ChatGPT can review checkpoint files uploaded to the chat or sanitized commits/comments in an accessible GitHub repository when the user requests a check. Neither a local file nor a GitHub comment wakes this chat automatically. No new watcher, webhook, API call to ChatGPT, or background polling is required for this setup.

For the first run, the operator can upload `checkpoint-A.md`, then B/C or any blocker. A dedicated MODEL-LAB GitHub issue can be used later with explicit publication approval. Do not reuse IP-01/IP-02's execution controls or assume an existing issue grants new work. Do not publish raw host inventory, `.local/`, model files, logs containing private prompts, keys, launcher tokens or credential-bearing URLs. A denied write stops that action; do not route around it.

Ask precise questions: symptom, exact command/version, observed outcome, hypothesis, smallest safe next test, and work that can continue. Record advice as advice and recheck it against actual evidence and the operator's permissions. Do not seek approval for every routine local fix; do pause for the initial installation plan, Strata's large download, true permission/resource changes, or uncertain process ownership.

## Reference checks

- OpenAI native Windows sandbox: https://developers.openai.com/codex/windows
- OpenAI Windows application/local environment behavior: https://developers.openai.com/codex/app/windows
- Python 3.13.16 official artifact index: https://www.python.org/ftp/python/3.13.16/
- Local package `docs/TEST_REPORT.md`, `README.md`, pinned installer code, model catalog and `MANIFEST.sha256` remain the input evidence for this assignment. Recheck volatile source availability rather than substituting guessed versions.
