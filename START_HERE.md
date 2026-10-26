# Start here — Haven

Repository: https://github.com/erpzz/haven · Treat it as public regardless of its current visibility setting. Never add credentials, host inventories, IP addresses, private paths or raw transcripts.

Every claim below is tagged **observed** (a real run with a saved receipt), **prepared** (installed, verified and ready, but not routinely running) or **planned** (design intent, no code). Missing data is unknown, not success.

## What Haven is today (2026-10-26)

Haven's ambition is a privacy-first personal assistant and engineering platform (planned; see the historical section). What exists and works today is narrower and concrete:

- **A private local Model Lab (observed).** A Python standard-library server ([labs/model-lab/](labs/model-lab/)) runs on a Linux GPU host as an ordinary systemd user service on loopback port 8877. Nothing listens on the LAN or the public internet. It is reached from the administration Mac over an owned SSH tunnel and opened in a browser with:

  ```sh
  python3 ops/haven-core/open-lab.py
  ```

  Operation, recovery and rollback: [ops/haven-core/LINUX_MODEL_LAB.md](ops/haven-core/LINUX_MODEL_LAB.md). Current peer handoff: [ops/haven-core/CLAUDE_NEXT_SESSION.md](ops/haven-core/CLAUDE_NEXT_SESSION.md).
- **A fast 4B backend (observed).** Qwen3.5-4B (Q4_K_M GGUF) through pinned llama.cpp b11146 with CUDA 12.8, all 33 layers offloaded. This is the model loaded for normal use.
- **A prepared Strata runtime (prepared, one observed response).** Strata v0.2.6 / Control 0.1.51 / signed engine 0.1.50 with the pinned `Qwen3.8-Flash-Next IQ2_XS` shards downloaded and SHA-256 verified. It produced one authenticated answer through the Lab, was stopped cleanly, and stays stopped for normal operation because its cold start is slow (see below). Details: [ops/haven-core/STRATA_LINUX.md](ops/haven-core/STRATA_LINUX.md) and the sanitized [receipt](ops/haven-core/linux-strata-result-20261026.json).
- **A verified-teacher tool-SFT training lab (observed, in progress).** A frozen, machine-verified tool-use benchmark (550 synthetic episodes; 110 held-out) and a train/evaluate loop that uses Strata as a local teacher and a cached Qwen3-0.6B as the student. It lives in [PR #45](https://github.com/erpzz/haven/pull/45) (branch `claude/opus-tool-distill-20261026`, stacked on the earlier bounded LoRA pilot in [PR #37](https://github.com/erpzz/haven/pull/37)); results are in its [RESULTS.md](https://github.com/erpzz/haven/blob/claude/opus-tool-distill-20261026/labs/intelligence-bakeoff/distillation/tool_sft/RESULTS.md).
- **Not on `main` yet.** Everything above is on open draft PRs and branches. `main` still holds only the September 2026 design and coordination documents.

What Haven is **not** today: not a deployed assistant, not multimodal, not spatial, no drones, robots, wearables or memory system. Those remain planned (historical section). The host diagnostic tools, prepared runtime switching and CPU-only lane in PRs [#41](https://github.com/erpzz/haven/pull/41), [#42](https://github.com/erpzz/haven/pull/42) and [#43](https://github.com/erpzz/haven/pull/43) are implemented on GitHub with unit tests but were not live-verified at the time of writing.

## Measured so far

Each row is a single observed run, not a benchmark campaign. None qualifies general model quality or sustained speed.

| Measurement | Result | Status | Source |
|---|---|---|---|
| 4B warm browser response (llama.cpp b11146, CUDA) | 0.17 s first output, 91.25 decode tok/s; one cold arithmetic answer was wrong | observed, one run | [PR #36](https://github.com/erpzz/haven/pull/36), [CLAUDE_NEXT_SESSION.md](ops/haven-core/CLAUDE_NEXT_SESSION.md) |
| Strata authenticated response through the Lab | 27 tokens, 0.834 s first output, 27.7 backend decode tok/s; unauthenticated chat 401 | observed, one run | [receipt](ops/haven-core/linux-strata-result-20261026.json), [PR #36](https://github.com/erpzz/haven/pull/36) |
| Strata cold service start to API readiness | 868 s (836 s reading 33 GiB of experts); 870.6 s on the second observed start | observed, two runs | [receipt](ops/haven-core/linux-strata-result-20261026.json), [issue #40](https://github.com/erpzz/haven/issues/40) |
| Qwen3.5-4B on frozen held-out tool-use set | 76/110 (verifier v1 and v2 agree) | observed, one run | [issue #40](https://github.com/erpzz/haven/issues/40) checkpoint 2026-10-26 04:04 UTC |
| Strata as teacher on the same held-out set | 55/110; 0 % on execute-refusal episodes (it substitutes a proposal) | observed, one run | [RESULTS.md](https://github.com/erpzz/haven/blob/claude/opus-tool-distill-20261026/labs/intelligence-bakeoff/distillation/tool_sft/RESULTS.md), [PR #45](https://github.com/erpzz/haven/pull/45) |
| Qwen3-0.6B base on the same held-out set | 14/110 | observed, one run | [issue #40](https://github.com/erpzz/haven/issues/40) checkpoint 2026-10-26 04:04 UTC |
| Qwen3-0.6B after verified-teacher SFT, same held-out set | 38/110 (from 14/110); the oracle-control arm trained on scripted trajectories for the same episodes also scores 38/110 | observed, one run, single seed | [RESULTS.md](https://github.com/erpzz/haven/blob/claude/opus-tool-distill-20261026/labs/intelligence-bakeoff/distillation/tool_sft/RESULTS.md), [PR #45](https://github.com/erpzz/haven/pull/45) |
| Earlier 0.6B LoRA pilot (3 copying examples, 40 steps) | 18.016 s, 2.63 GiB peak CUDA; facts 0/3→0/3, skills 0/4→0/4, retrieval 1/2→2/2 | observed, one run, negative | [PR #37](https://github.com/erpzz/haven/pull/37) |
| 4B on the legacy hand-written 8-task tool set | 3/8 passes, 7/8 tool selections, after an interface/scorer fix (was 2/8) | observed, one run | [PR #37](https://github.com/erpzz/haven/pull/37) |

Read the tool-SFT numbers with their disclosed limits: the verifier is lexical and was amended three times, with disclosure, before any trained-student result; denominators and data hashes are preregistered. The student's gain met its preregistered criteria, but the oracle control ties it, so the teacher added no aggregate value over scripted trajectories, and the untrained 4B is still about twice as good. No adapter has been promoted into the Lab.

## Where the work lives

- **Runtime:** [PR #36](https://github.com/erpzz/haven/pull/36) `codex/slink-linux-model-lab-20261025` (stacked on bootstrap [PR #35](https://github.com/erpzz/haven/pull/35)). Model Lab on Linux, pinned CUDA installer, Mac launcher, Strata service. Verified running checkpoint `23408d3`.
- **Training:** [PR #37](https://github.com/erpzz/haven/pull/37) `codex/slink-distillation-pilot-20261025` (bounded LoRA pilot, HF adapter evaluation) and the tool-SFT lab in [PR #45](https://github.com/erpzz/haven/pull/45) `claude/opus-tool-distill-20261026`, stacked on #37. These paths are not on PR #36's ancestry; use a separate checkout.
- **Overnight coordination:** [issue #40](https://github.com/erpzz/haven/issues/40) is the task board (one GPU owner at a time, checkpoints, release receipts). Mission packet: [PR #39](https://github.com/erpzz/haven/pull/39).
- **In flight, stacked on PR #36:** [PR #41](https://github.com/erpzz/haven/pull/41) read-only host diagnostics and prepared runtime switching; [PR #42](https://github.com/erpzz/haven/pull/42) and [PR #43](https://github.com/erpzz/haven/pull/43) two overlapping CPU-only inference lanes (one is to be selected).
- **Architecture reference:** HS-01 v2 in [PR #34](https://github.com/erpzz/haven/pull/34); intelligence/memory intent in [design/H02/R02/v1/INTEGRATION_SUMMARY.md](design/H02/R02/v1/INTEGRATION_SUMMARY.md). Dated recommendations there are not deployment facts.
- **Rules:** [AGENTS.md](AGENTS.md) and [PRECEDENCE.md](PRECEDENCE.md). Use an owned branch, open a PR, do not merge your own PR, do not push to `main`, do not rewrite preserved baseline/design/review files.

For an agent starting work: read this file, `AGENTS.md`, then the two `ops/haven-core` documents above. Read a specific implementation only when changing it. Do not repeat package, GPU or security audits, cold Strata starts or the training smoke tests; read the saved receipts instead.

## Historical research coordination (Sept 2026)

The text below is the original coordination entry point from September 2026, kept verbatim. It describes the R01–R15 research threads, the RI-01 multi-agent campaign and the Observatory brief. That work produced design documents and prompts, not code, and none of its embedded instructions is a current assignment. It remains the record of Haven's wider ambition.

Repository: https://github.com/erpzz/haven

1. Read `AGENTS.md`, `PRECEDENCE.md`, `CURRENT_STATUS.md` and `coordination/PROTOCOL.md`.
2. Read `coordination/THREAD_STATUS.md` and the issue for your exact assignment. Rxx research IDs are not the same as Hxx ownership IDs.
3. Record the actual `main` commit you read. Fetch exact files at that commit; do not infer content from an index or another conversation's memory.
4. Read the original cumulative scope at `baseline/cumulative-v1.0/scope/COVERAGE.md` and the relevant original design documents.
5. Use your repository-linked assignment in `prompts/`. Read only its required handbacks and relevant contract sections; avoid copying every branch into your context.
6. Return a versioned handback on an owned branch and open a pull request when the available tools and assignment permit writes. Otherwise return the same files as a packet and mark them NOT_UPLOADED. Do not claim a PR or commit exists unless verified.

### Original sources and current authority

The imported documents are historical evidence and design proposals. Their embedded instructions describe the scope at the time they were written. They do not authorize you to repeat NIGHT-01, restart M0, download models, change host settings or operate hardware.

The root coordination documents describe how to use those sources now. An accepted research PR accepts a design record, not its implementation or its performance claims. Only a separate explicit operator-approved work package authorizes coding, installation or physical activity.

### First assignments

- R03: start the privacy/authority review using R02, the H00 review, and the R06/R08 contract requests.
- R02: continue the existing intelligence thread with P01 reconciliation; do not redo broad research.
- R06 and R08: their saved v1 handbacks are available here; proceed only with focused review responses, not automatic implementation.
- R13: independently map evidence and acceptance gaps; do not act as a second implementer.
- R07: use R06's proposed observation/transform semantics to design the shared world-model boundary after the first review.

The R1 lifecycle repair and M0 acceptance remain separate coding tracks. Read their actual latest evidence from the authorized owners before asserting progress.

### Observatory and additional exploration

For R15, use [coordination/R15_OBSERVATORY.md](coordination/R15_OBSERVATORY.md), the [full prompt](prompts/R15_GODS_EYE_OBSERVATORY_AND_OPEN_TOOLS.md) and [starting message](prompts/R15_START_MESSAGE.txt). The [prompt index](prompts/README.md) also links R14 and the existing issue roster. R14/R15 add to the project; they do not cancel prior priorities or launch research automatically.

The Observatory source brief is under `design/H00/R15/brief-v1/`. Completed research, when produced and authorized for publication, belongs under its own unused version directory, not in the brief. Actual GEV integration, models and devices remain unimplemented by this publication.

The older complete-source import remains unverified. Some historical paths referenced above or inside issues may be missing; check the tree and state missing evidence explicitly. Do not re-create originals from summaries or call an input read when only its title was available. This limitation does not prevent a self-contained public-source R15 study from proceeding with declared assumptions.

### Autonomous research team — RI-01

The user has requested an autonomous, dependency-aware multi-agent campaign, including full multimodal design and visual inspection. Use [the RI-01 workspace](orchestration/RI-01/README.md), [launch prompt](orchestration/RI-01/START_CODEX.txt), and [coordination page](coordination/RI01_MULTI_AGENT.md). This is a new way to execute the remaining research, not a replacement for its vision or original handbacks.

The setup authorizes delegation only when the campaign is explicitly launched. It has ten role profiles, three-child concurrency, real source/agent receipts, scoped autonomous consultation, separate integration/vision/code/evidence reviews, and checkpointed branch/PR delivery. Inspect pending PRs as well as main; the source snapshot is a dated lead, not a claim all research is merged. Existing M0, NIGHT-01/R1, physical testing and later coding remain separate.
