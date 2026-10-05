LOCAL MODEL EFFICIENCY — OCTOBER 4, 2026
Target: RTX 2070 Super 8 GB / Ryzen 3900X / 64 GB RAM

THE TWO PATHS ARE DIFFERENT

Strata is a specialized hybrid inference engine for Qwen3.8-Flash-Next and selected related packs. It is not a generic GGUF GUI. The reviewed upstream version is v0.1.39, commit 6f32ec070f23ced9f50e704d854d775da52591ab. Its docs list RTX 20 support and a contributor test on an RTX 2070, but explicitly warn that 8 GB is slow. Upstream 5070/3090 numbers are NOT predictions for your card.

llama.cpp is the separate flexible GGUF path. This lab pins the CUDA 12.4 Windows build b11146 referenced by its v0.5.0 stable release. It requests all layers on CUDA explicitly. A 4B model is the first-fit experiment; 8–9B Q4 models can be tight once KV cache, compute buffers and your Windows desktop are included. Installation does not prove CUDA offload: inspect the engine log and actual NVIDIA memory/utilization.

The UI itself does not accelerate matrix multiplication. It makes the engines easy to start, compare and observe. 64 GB RAM does not become 64 GB VRAM. The objective is useful answers sooner with the desktop responsive, not a permanently full utilization bar.

RECENT IMPROVEMENTS: WHAT IS REAL, AND WHAT TRANSFERS?

1. HOT-EXPERT CACHING + HYBRID MoE EXECUTION [upstream implementation]
Strata places model work across GPU and host memory, keeping useful experts in a GPU cache. That can make a model whose total weights exceed VRAM usable. Active parameters reduce computation, not the total storage or memory traffic needed. Your 3900X, memory bandwidth, SSD, available RAM and 8 GB cache all matter. More host-to-GPU traffic can leave the GPU underutilized even when working correctly.
Source: https://github.com/Niko1221/Strata/blob/6f32ec070f23ced9f50e704d854d775da52591ab/README.md

2. MTP / SPECULATIVE DECODING + LESS LAUNCH OVERHEAD [implemented; model-specific]
Strata v0.1.39 documents fewer launches/host round trips, staged inputs and batched MTP work. Its authors measured roughly 2.5–7% decode gains over v0.1.38 in specific 5070 cases, with conditions. They also document an opt-in Turing FP16 tensor-core prompt path, STRATA_BF16_TC=1, based on an RTX 2080 Ti report; it changes rounding and is NOT enabled by this lab. No speed or quality guarantee transfers automatically to the 2070 Super.
Source: https://github.com/Niko1221/Strata/releases/tag/v0.1.39

Speculative decoding proposes several draft tokens and verifies them against a target. Depending on the method, exact verification can preserve the target sampling distribution; pruning experts or changing numerical paths is a different claim. Extra draft weights/work can lose on an 8 GB card by evicting target/KV/expert data. This first release does not download a second draft model or invent a universal speculative flag.

3. HYBRID ATTENTION / RECURRENT STATE [model architecture, not a magic runtime switch]
Qwen3.5's architecture combines Gated DeltaNet and attention blocks. This can reduce the growth of certain state relative to an all-attention design, but does not mean context is free or that every variant has identical memory behavior. The 4B dense model is not the same parameter layout as the large MoE model. We deliberately start at 4K, not the model card's maximum window.
Sources: https://huggingface.co/Qwen/Qwen3.5-4B
https://unsloth.ai/docs/models/qwen3.5

4. QUANTIZATION + KV CACHE COMPRESSION [supported where kernels/model permit]
Q4_K_M reduces weight storage; f16 KV is the conservative baseline here. The separate q8_0 KV preset aims to free memory at longer context. Quantization does not necessarily make a kernel faster. Turing, head shapes and the exact build determine whether a fast path exists. A failure stays visible; there is no quiet retry with weaker settings. Inspect logs for CPU attention/fallback and compare actual prefill/latency, not just weight size.
Sources: https://github.com/ggml-org/llama.cpp/blob/7fe450e19305b828c199d602c23a8337aaa1f03b/tools/server/README.md
https://github.com/ggml-org/llama.cpp/issues/24485
The issue is a user report on other hardware, not an independent finding about this PC.

5. CUDA GRAPHS / FUSED OPERATORS [shipped, architecture-dependent]
The September llama.cpp release includes CUDA graphs for MTP drafting and backend fusion/performance work. These reduce framework/launch overhead on supported paths. Merely installing a new build does not force every model onto every optimized kernel. Use the pinned baseline first, then evaluate an explicitly changed engine version rather than silently auto-updating during a benchmark.
Source: https://github.com/ggml-org/llama.cpp/releases/tag/v0.5.0

6. NEW SPECULATION RESEARCH [papers, not implemented in this lab]
MoE-Spec (Feb 2026) budgets the expert set used during verification and reports 10–30% higher throughput against its baselines at comparable quality. It explicitly trades accuracy for tighter budgets; it is not automatically lossless speculative decoding.
https://arxiv.org/abs/2602.16052

SpecMoE (Apr 2026) uses self-assisted speculative decoding with CPU offload and reports up to 4.30x in its experiments. That is not a 2070 Super benchmark or a drop-in binary offered here.
https://arxiv.org/abs/2604.10152

LibraSpec (Aug 2026) chooses diffusion-drafter verification length by marginal expected speedup rather than assuming longer drafts are always better. Its multi-model research results are promising, but neither its drafter nor its kernels are integrated here.
https://arxiv.org/abs/2608.08721

ORIGINAL HYPOTHESES TO TEST — NOT MEASURED RESULTS

H1. On this desktop, a fully GPU-resident 4B model can deliver useful responses sooner than Strata's much larger model on routine questions, even if Strata wins hard tasks. Test each on the same small tasks; score correctness/usefulness, first output and total completion time. Do not decide by model parameter count alone.

H2. Keeping 0.7–1 GiB of display headroom and a short context may outperform aggressively filling every byte of VRAM once Windows shared-memory spill and responsiveness are considered. Test identical prompts at 2K, 4K and 8K, with other apps kept constant; stop on allocation errors rather than increasing load indefinitely.

H3. Six or eight CPU threads may beat all 24 logical threads for GPU-resident inference because the CPU is feeding the GPU, not doing all matrix work. Test 4, 6, 8, 12 threads with the same model/context/batch. The largest setting is not inherently fastest. Do not infer the same optimum for Strata's CPU expert work.

H4. Shortening unnecessary reasoning and repeated context can improve time-to-useful-answer more than a modest kernel gain. Compare reasoning-off and reasoning-on with a correctness rubric. Different output content means this is a workflow/quality tradeoff, not a pure engine speedup.

H5. Speculative decoding is valuable only when saved target passes exceed draft cost plus memory/cache disruption. An adaptive policy could use recent acceptance, verification time and available VRAM to stop drafting earlier. This is inspired by current literature, not a novel proven algorithm or an implementation in this release.

H6. A future two-tier policy could keep the small model as default and load Strata only for cases where measured task success justifies switching cost. This release offers manual switching. It does not keep both models resident or call the policy 'optimal' without evidence.

HOW TO MEASURE

Use one model at a time. Record model hash/quant, engine build, context, cache types, batch, threads and reasoning setting. Run a smoke test then three comparable trials. Distinguish cold loading, prompt processing, decode and network/UI overhead. The Experiment view uses backend token counts when supplied; unavailable counts remain unknown. No stream-chunk-as-token estimates. No hidden warm-up. llama.cpp benchmark requests disable prompt caching; attached Strata cache policy must be recorded separately. A repeated prompt is not a cold-load test.

Use medians and keep failed/cancelled trials. Compare exact same prompts and output bounds, then inspect answer quality. Energy efficiency requires integrated power/time measurements; the dashboard's instantaneous GPU power/usage is not an energy benchmark. A faster but wrong answer is not a win.

LIMITS OF THIS BUILD

This build has no actual measurements from your Windows PC, no Windows/CUDA execution proof from the development container, no real Strata model run, and no general claim of image or tool-use qualification. Browser and mock-backend integration tests are described separately in TEST_REPORT.md. Native Strata supports additional features through its own UI; this first workbench exposes text inference only. All source claims are dated observations, not evergreen promises.
