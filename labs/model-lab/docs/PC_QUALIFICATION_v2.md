# Windows PC qualification, v2

Status: both requested inference paths are installed and qualified on the actual PC. The first source checkpoint includes the repairs and baseline results; post-baseline performance experiments and the final handoff are still in progress. PR #25 remains draft. No main merge is authorized.

## Decisions

Keep the official llama.cpp everyday profile: Qwen3.5 4B Q4_K_M, 4096 context, f16 KV, six CPU threads, batch 256 / microbatch 128, one request, reasoning off. The 24 fixed-task profile checks found no useful speed improvement from larger batches/eight threads, q8_0 KV, or 2K/four threads. Warm three-task totals were 2.32–2.40 seconds; q8_0 saved about 52 MiB. These short synthetic tasks establish bounded correctness and timing, not general model quality.

Strata's initial IQ2_XS profile uses 8192 context, one request, images off, MTP depth four plus native default suffix lookup, and a requested 1024 MiB reserve. Actual device VRAM reached 7604 MiB, leaving little desktop headroom. A 4K/2048-reserve comparison is pending before the everyday Strata recommendation is finalized. Keep models exclusive on this 8 GB GPU.

## Evidence

PC: Windows 11 Pro build 26200, Ryzen 3900X (12 cores / 24 threads), RTX 2070 SUPER 8192 MiB (sm_75), NVIDIA driver 591.86, 64 GB RAM. Execution, browsers, compilation and measurements stayed on this PC. No driver, pagefile, security or persistent OS setting was changed.

Folder-local Python 3.13.16 and official llama.cpp b11146 (`7fe450e19305b828c199d602c23a8337aaa1f03b`) CUDA 12.4 assets were verified before extraction. Real logs show all 33/33 starter model layers offloaded to CUDA0, with a 2603.5 MiB CUDA model buffer. Device VRAM rose from about 1.1 GiB to 4.0 GiB and returned near idle after unload. Browser chat, arithmetic 391, JSON extraction, cancellation/partial output, a subsequent answer, unload, stop and reopen passed. The first cold extraction took 50.15 s; subsequent short arithmetic requests completed in 0.15–0.18 s. Cold initialization and short warm answers are distinct observations.

Strata v0.1.39 source is pinned to `6f32ec070f23ced9f50e704d854d775da52591ab`. The official CUDA 13 Windows engine and both IQ2_XS shards passed their original published hashes. Pinned MTP checkpoint files were verified before local preparation. Actual sandboxed Chromium native and integrated browser runs passed nine workflow checks: native arithmetic and JSON, cancellation with partial output, another answer, integrated arithmetic/cancellation, disconnect/reconnect, supported native unload with Job active count zero, and reopen with another correct answer. No page errors or external browser requests were observed. Startup was 38.469 s; reopen was 23.046 s. Minimum available RAM was 14.981 GiB; peak sampled pagefile use was about 104 MiB. No pagefile configuration change was issued. Integrated arithmetic requests completed in 0.7867–1.0231 s with first output 0.6663–0.8916 s. Native browser display observations (5.42–8.41 s on these tasks) include locator polling and are recorded separately from backend prompt/decode timings.

Final source suite at this checkpoint: 60 tests discovered, 59 passed, one skipped because Windows symlink creation requires unavailable privileges, 24.604 s. Actual native direct/nested junction rejection checks passed separately. The browser fixture passed 11 checks in sandboxed Chromium with no page errors; its inference is explicitly a test double. Real CUDA/Strata inference evidence above is separate. Independent native launcher/controller checks passed three composite tests without skips, covering authenticated stop, exact ownership, crash/reopen, stale receipt and foreign-listener refusal.

## Interface changes

OPEN-LAB / STOP-LAB and OPEN-STRATA / STOP-STRATA controls use folder-local Python, authenticated loopback controllers and exact Windows Job Object ownership. Lab starts without a loaded model. Exit lab stops its owned engine; disconnecting external Strata leaves the separately launched Strata server running. STOP-STRATA requests native unload before exact tree cessation. Foreign listeners are refused, not killed.

Installer repairs keep pip/Hugging Face settings and caches inside this installation, validate junction ancestry before cleanup, block unrequested compilation/global migration, extract only needed pinned GGUF tooling, and enforce exact sizes and hashes before model promotion. Source and configuration backups and failed transfers are retained. Benchmark controls capture one selected connection/workload/settings snapshot; a changed connection is rejected. Prompt/decode durations have explicit backend provenance; chunks are not tokens. Ownership transitions now serialize unload/load/disconnect so an earlier unload cannot clear a replacement connection.

## Acceptance and independent review scope

The root agent `/root` executed actual Windows installation, browser/GPU workflows and measurements. `/root/independent_review` independently reviewed consequential installer/lifecycle/metrics changes and ran native ownership tests. It found the unload/load race; the repair and its focused concurrency regression passed. No remaining actionable source blocker was reported within that review scope. The reviewer did not independently repeat the model downloads or GPU inference. `/root/performance_research` built an isolated pinned ik_llama.cpp candidate using existing local tools; its inference qualification remains pending at this checkpoint.

One standalone mocked measurement operation was rejected by automatic approval review with the stated reason “blocked by policy.” It was stopped and not retried through another route. Normal authorized source tests separately cover metrics behavior. This denial is not counted as a pass.

## Risks and retained failures

Two full-size shard transfers failed their original SHA-256 checks. Both failed copies and the failed strict fresh second-shard copy remain local. Two byte differences between second-shard copies were resolved using exact remote ranged chunks into a separate candidate; the complete candidate matched the original immutable SHA-256 and an independent Windows Get-FileHash. The original pin was never changed. The corruption cause is UNKNOWN; these observations do not establish a hardware, network or storage fault. No invalid file was accepted for inference.

Initial Windows encoding, stale GPU telemetry, cmake/long-path extraction and compiler-flag failures remain recorded. Their scoped repairs were re-executed successfully. No broad cleanup or OS change was used. The original `MANIFEST.sha256`, `docs/TEST_REPORT.md` and earlier negative evidence remain historical; the original manifest passed 29/29 before edits. Use the new v2 manifest for this candidate.

Model weights, tokens, raw private logs, absolute personal paths, runtime data and experimental binaries are not public. Local detailed evidence is in `.local/setup/20261004/`; controller logs and stop receipts are in `.local/launcher-lab/` and `.local/launcher-strata/`. Accepted models and failed transfers remain available for reuse/investigation. The small GGUF is Apache-2.0; Strata's base/MTP model uses the upstream Qwen Community License 1.0 despite the quantization repository metadata listing Apache-2.0. Source publication does not redistribute weights.

## Next package

Finish finite supported Strata/MTP/lookup and isolated ik comparisons, conditionally evaluate explicitly compatible DFlash if it fits, retain a stable everyday recommendation, publish sanitized measured results, and confirm all task-owned workloads stopped. Jev is not a dependency. No cloud environment or paid inference is used.
