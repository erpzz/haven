# Local Model Lab — refined implementation brief

Build a runnable Windows-first local model exploration workbench for a GeForce RTX 2070 Super (8 GB VRAM), Ryzen 9 3900X and 64 GB system RAM. Use the actual Niko1221/Strata project as a first-class large-model backend. Use a separate llama.cpp CUDA backend for smaller GGUF models that can fit in VRAM. Do not pretend Strata is a UI wrapper or that arbitrary GGUF files run on its specialized engine.

Deliver code now, a browser UI, double-click setup/launch scripts, a small reviewed model catalog, existing-GGUF registration, explicit engine/model downloads, live GPU/VRAM/system-memory readings, stream cancellation, and honest benchmark/export controls. Prefer folder-local dependencies, official pinned artifacts and no administrator install. No Docker, JavaScript build toolchain or system CUDA Toolkit should be needed for the lab. Keep application/UI overhead small.

Target efficiency rather than a cosmetic 100% utilization number. Start with full CUDA layer offload, one inference request, 4K context, FP16 KV and a modest batch/microbatch. Expose a separately labelled quantized-KV experiment and allow measured profile comparisons. Do not silently fall back to CPU or auto-retry a failed model launch. Do not load two engines into the 8 GB GPU at once. Flag an estimated memory fit as an estimate, never a successful allocation measurement.

For Strata, make its large download and substantial RAM use explicit; provide an opt-in helper using pinned upstream source, conservative context, reserved display VRAM and no image encoder initially. Preserve the upstream native UI for features not implemented here. Attach external servers without claiming ownership or terminating them. Keep the large-model path experimental on 8 GB.

Measure first-output latency, total latency, backend-reported token usage and decode throughput separately. Stream chunks are not tokens. Record individual outcomes, settings and prompt hashes without automatically saving chat content. Benchmark repeated same-prompt workloads and retain failures. Compare useful answer quality as well as speed.

Research recent efficiency improvements using primary sources. Distinguish shipped runtime features, research results measured on other hardware, approximate/quality-changing methods and original testable hypotheses. Do not promise another GPU's speedup on a 2070 Super. Include experiments with fixed workloads and one setting changed at a time.

Use loopback-only services, transient UI authorization, same-origin checks, inert output rendering, bounded requests and process ownership. No cloud inference, employer data integration, device actions, persistent services, driver changes, overclocking, firewalls, pagefile changes or purchases. This is a separate local model lab, not a silent resumption of Haven IP-01/IP-02 or an acceptance of those capabilities. Preserve all earlier Haven files and evidence.

Execute actual local software tests and real browser checks in the available environment. Disclose Windows/CUDA/Strata/model-download paths that cannot be exercised on this host. Ship a source ZIP with precise PC setup steps; do not label fixture inference as a real model run.
