# Windows PC qualification, v2

Status: both requested inference paths are installed and qualified on the actual PC. The source checkpoint f6272cc contains the tested runtime repairs; this final report adds measured recommendations and completed experiments. All test workloads are stopped. PR #25 remains draft. No main merge is authorized.

## Decisions

Keep the official llama.cpp everyday profile: Qwen3.5 4B Q4_K_M, 4096 context, f16 KV, six CPU threads, batch 256 / microbatch 128, one request, reasoning off. The 24 fixed-task profile checks found no useful speed improvement from larger batches/eight threads, q8_0 KV, or 2K/four threads. Warm three-task totals were 2.32–2.40 seconds; q8_0 saved about 52 MiB. These short synthetic tasks establish bounded correctness and timing, not general model quality.

Strata's initial IQ2_XS profile uses 8192 context, one request, images off, MTP depth four plus native default suffix lookup, and a requested 1024 MiB reserve. Actual device VRAM reached 7604 MiB, leaving little desktop headroom. Retain the measured 4096-context / 2048-MiB requested-reserve profile for everyday Strata use. It passed eight fixed answers, peaked at 6414 MiB device VRAM, and took 15.093 s for the warm four-task set versus 13.078 s at 8K/1024. The original configuration is backed up locally. The reserve is a requested engine setting, not a guaranteed measured free-memory floor. Keep models exclusive on this 8 GB GPU.

## Evidence

PC: Windows 11 Pro build 26200, Ryzen 3900X (12 cores / 24 threads), RTX 2070 SUPER 8192 MiB (sm_75), NVIDIA driver 591.86, 64 GB RAM. Execution, browsers, compilation and measurements stayed on this PC. No driver, pagefile, security or persistent OS setting was changed.

Folder-local Python 3.13.16 and official llama.cpp b11146 (`7fe450e19305b828c199d602c23a8337aaa1f03b`) CUDA 12.4 assets were verified before extraction. Real logs show all 33/33 starter model layers offloaded to CUDA0, with a 2603.5 MiB CUDA model buffer. Device VRAM rose from about 1.1 GiB to 4.0 GiB and returned near idle after unload. Browser chat, arithmetic 391, JSON extraction, cancellation/partial output, a subsequent answer, unload, stop and reopen passed. The first cold extraction took 50.15 s; subsequent short arithmetic requests completed in 0.15–0.18 s. Cold initialization and short warm answers are distinct observations.

Strata v0.1.39 source is pinned to `6f32ec070f23ced9f50e704d854d775da52591ab`. The official CUDA 13 Windows engine and both IQ2_XS shards passed their original published hashes. Pinned MTP checkpoint files were verified before local preparation. Actual sandboxed Chromium native and integrated browser runs passed nine workflow checks: native arithmetic and JSON, cancellation with partial output, another answer, integrated arithmetic/cancellation, disconnect/reconnect, supported native unload with Job active count zero, and reopen with another correct answer. No page errors or external browser requests were observed. Startup was 38.469 s; reopen was 23.046 s. Minimum available RAM was 14.981 GiB; peak sampled pagefile use was about 104 MiB. No pagefile configuration change was issued. Integrated arithmetic requests completed in 0.7867–1.0231 s with first output 0.6663–0.8916 s. Native browser display observations (5.42–8.41 s on these tasks) include locator polling and are recorded separately from backend prompt/decode timings.

Final source suite: 60 tests discovered, 59 passed, one skipped because Windows symlink creation requires unavailable privileges, 24.604 s. Actual native direct/nested junction rejection checks passed separately. The browser fixture passed 11 checks in sandboxed Chromium with no page errors; its inference is explicitly a test double. Real CUDA/Strata inference evidence above is separate. Independent native launcher/controller checks passed three composite tests without skips, covering authenticated stop, exact ownership, crash/reopen, stale receipt and foreign-listener refusal.

## Interface changes

OPEN-LAB / STOP-LAB and OPEN-STRATA / STOP-STRATA controls use folder-local Python, authenticated loopback controllers and exact Windows Job Object ownership. Lab starts without a loaded model. Exit lab stops its owned engine; disconnecting external Strata leaves the separately launched Strata server running. STOP-STRATA requests native unload before exact tree cessation. Foreign listeners are refused, not killed.

Installer repairs keep pip/Hugging Face settings and caches inside this installation, validate junction ancestry before cleanup, block unrequested compilation/global migration, extract only needed pinned GGUF tooling, and enforce exact sizes and hashes before model promotion. Source and configuration backups and failed transfers are retained. Benchmark controls capture one selected connection/workload/settings snapshot; a changed connection is rejected. Prompt/decode durations have explicit backend provenance; chunks are not tokens. Ownership transitions now serialize unload/load/disconnect so an earlier unload cannot clear a replacement connection.

## Acceptance and independent review scope

The root agent `/root` executed actual Windows installation, browser/GPU workflows and measurements. `/root/independent_review` independently reviewed consequential installer/lifecycle/metrics changes and ran native ownership tests. It found the unload/load race; the repair and its focused concurrency regression passed. No remaining actionable source blocker was reported within that review scope. The reviewer did not independently repeat the model downloads or GPU inference. `/root/performance_research` built an isolated pinned ik_llama.cpp candidate using existing local tools; root runtime qualification subsequently passed 16/16 baseline/lookup and 16/16 MTP tasks with full CUDA offload; it was slower than the official engine on these sets.

One standalone mocked measurement operation was rejected by automatic approval review with the stated reason “blocked by policy.” It was stopped and not retried through another route. Normal authorized source tests separately cover metrics behavior. This denial is not counted as a pass.

## Risks and retained failures

Two full-size shard transfers failed their original SHA-256 checks. Both failed copies and the failed strict fresh second-shard copy remain local. Two byte differences between second-shard copies were resolved using exact remote ranged chunks into a separate candidate; the complete candidate matched the original immutable SHA-256 and an independent Windows Get-FileHash. The original pin was never changed. The corruption cause is UNKNOWN; these observations do not establish a hardware, network or storage fault. No invalid file was accepted for inference.

Initial Windows encoding, stale GPU telemetry, cmake/long-path extraction and compiler-flag failures remain recorded. Their scoped repairs were re-executed successfully. No broad cleanup or OS change was used. The original `MANIFEST.sha256`, `docs/TEST_REPORT.md` and earlier negative evidence remain historical; the original manifest passed 29/29 before edits. Use the new v2 manifest for this candidate.

Model weights, tokens, raw private logs, absolute personal paths, runtime data and experimental binaries are not public. Local detailed evidence is in `.local/setup/20261004/`; controller logs and stop receipts are in `.local/launcher-lab/` and `.local/launcher-strata/`. Accepted models and failed transfers remain available for reuse/investigation. The small GGUF is Apache-2.0; Strata's base/MTP model uses the upstream Qwen Community License 1.0 despite the quantization repository metadata listing Apache-2.0. Source publication does not redistribute weights.

## Completed performance experiments

[Sanitized per-trial measurements](evidence/PC_MEASUREMENTS_v2.json) include prompts, correctness, backend token counts/timings, first-output/wall time, sampled RAM/VRAM, immutable model identities and exact owned-stop confirmation. The official/ik/DFlash decoding comparisons used one loaded backend, 4K context, six threads, batch 256 / microbatch 128, f16 KV, flash attention on, one request, greedy sampling/seed 42 and reasoning off. Official/ik experiments requested cache_prompt=false. Strata does not implement that API flag; native default conversation caching remained enabled and actual cache counts were recorded consistently. Full artifact hashing warmed the OS file cache before these launches; startup results are not cold-SSD measurements.

| Variant | Correct / tested | Warm four-task total | Max sampled device VRAM |
| --- | ---: | ---: | ---: |
| Official, original 4B target | 8/8 | 4.4514 s | 3858 MiB |
| ik, same original target | 8/8 | 5.2711 s | 4001 MiB |
| Official prompt lookup | 8/8 | 2.9195 s | 3866 MiB |
| ik prompt lookup | 8/8 | 3.1479 s | 4379 MiB |
| Official, MTP model, MTP off | 8/8 | 4.8001 s | 3910 MiB |
| Official, same MTP model, MTP on | 8/8 | 2.9004 s | 4158 MiB |
| ik, MTP model, MTP off | 8/8 | 5.3660 s | 3983 MiB |
| ik, same MTP model, MTP on | 8/8 | 3.5654 s | 4383 MiB |
| Official DFlash target, draft off | 8/8 | 4.4306 s | 3858 MiB |
| Same target, compatible DFlash draft on | 8/8 | 2.8215 s | 4799 MiB |

These are four task types repeated twice: integers 1–40, copying a supplied integer line twice, exact JSON extraction with numeric code, and arithmetic 391. The sequence rubric accepts different whitespace/comma formatting. Original extraction wording produced quoted string 403 on both engines (6/8 for each of four profiles); those failures remain. A separate explicitly numeric instruction passed 64/64 across the eight official/ik variants above. DFlash then passed 16/16 with the same clarified tasks. Improved prompting is not attributed to backend acceleration.

MTP comparisons use the same MTP-equipped GGUF for off/on; the original non-MTP starter is a different file. Official MTP-off emitted 150 sequence tokens versus 111 with MTP-on, so the full task-time reduction includes shorter formatting. The equal-length 222-token copy task provides cleaner supporting evidence (two-run average 2.6341 s off versus 1.6306 s on). Arithmetic and copy first-output latency increased with MTP. Official lookup's equal-length copy task averaged 2.6681 s without lookup versus 1.0437 s with it; other task types did not improve. DFlash startup increased from 2.526 to 11.833 s and arithmetic became slower. Predictable counting/copying heavily favors speculation; two repetitions do not establish broad coding/chat improvements or statistical certainty. First output, prompt/decode rates and complete response times remain separate in the data.

Retain official llama.cpp as the stable engine. Keep prompt lookup, MTP and DFlash experiment configurations separately; do not enable them automatically for unrelated GGUFs. Official prompt lookup uses ngram-simple, n=4 / m=8 / min-hits=1 / max draft=8. Official MTP uses draft-mtp / max draft=3. The isolated ik build is sm_75 with existing CUDA 12.6/MSVC, commit 5f89bfc81268b4d56d2af63ccbed59de17c64c09; its executable SHA-256 is 1610b9691cdcc580e25187790229e03ce085a253349b3b801b7c2c7023581249. Embedded-MTP models offloaded 34/34 layers. Existing tool versions and failed build attempts remain local; source is unchanged. GPU numbers are sampled device totals including the desktop and can miss brief peaks.

The verified MTP artifact is unsloth/Qwen3.5-4B-MTP-GGUF revision 86835bf9949e4d14d6860f7910b1340ad4f271a9, 2,834,975,040 bytes, SHA-256 3874209241c9a397e2f62cd3f70f80fd2dfbf0dfccb6838416bdb48a714e8630. DFlash uses the original exact Qwen3.5 4B target, official b11146, and EntityDeletr/Qwen3.5-4B-DFlash-GGUF revision c2e6879b70f5870f389f850934b144fbdb51c8e4, 454,200,928 bytes, SHA-256 a46bda8d229760ff330de40a02d948e4d1811c4419a774321588e4355707762b. Its draft-dflash / max draft=3 / draft GPU layers=99 combination actually loaded target 33/33 and drafter 7/7 CUDA layers (2603.50 and 422.72 MiB model buffers). This establishes fit and bounded correctness for that exact combination. All experiment processes stopped with Job active count zero.

The default Strata MTP-plus-lookup warm set was 13.078 s versus 13.625 s with suffix lookup disabled; both passed 8/8. Keep native defaults because this small difference is not a strong basis for changing them. Do not claim a no-MTP baseline: this native IQ2_XS path requires speculation. Jev remains outside this task.

## Final retained-profile verification and handoff

The retained 4K/2048 Strata configuration repeated all nine native/integrated browser checks successfully, including cancellation, reconnect, native unload and reopen. Startup was 19.844 s and reopen 18.032 s with a warm file cache. Minimum available RAM was 16.059 GiB; sampled peak device VRAM was 6390 MiB; peak sampled pagefile use was 107.67 MiB. Integrated short answers completed in 0.9400–1.1405 s, first output 0.8050–1.0017 s. Native display observations again include browser polling. No page errors or external browser requests occurred, and exact owned processes stopped.

Open/stop controls, models, pinned binaries and private evidence are retained locally. Final footprint: Strata data 71.248 GiB, small/experimental GGUFs 5.616 GiB, and retained failed transfers plus setup evidence 90.217 GiB. The NVMe had about 207.95 GiB free at closure. Final authenticated Lab and Strata stops both reported native graceful API success and Job active count zero; their private live receipts were removed. No listener remained on the six tested Lab/Strata/experiment ports and no process remained under the installation executable path. The public source manifest identifies this report and sanitized evidence; the original manifest remains unchanged. Independent evidence review and runtime/source checks are distinct. PR #25 remains draft, with no merge or force-push. No cloud environment, paid inference or unexpected background service was created. The installed runtime and qualification package is complete; later broader workload tuning is optional and requires no dependency for ordinary chat.
