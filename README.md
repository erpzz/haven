# Haven

Haven is a local-AI project: today, a private Model Lab running open-weight language models on a single Linux GPU host, reached from a Mac over SSH, plus a small training lab that measures whether a local small model can learn tool use from a local large one. Its ambition is wider: a privacy-first personal assistant and engineering platform (spatial perception, wearables, robotics, drones). That ambition is design intent, not shipped capability.

**Start with [START_HERE.md](START_HERE.md).** It separates what is observed, prepared and planned, lists every measurement with its source, and shows where the work lives.

## What works today (2026-10-26)

- **Private Model Lab** — Python standard-library server ([labs/model-lab/](labs/model-lab/)) as a loopback-only systemd user service on a Linux GPU host; opened from the Mac with `python3 ops/haven-core/open-lab.py`. Operation: [ops/haven-core/LINUX_MODEL_LAB.md](ops/haven-core/LINUX_MODEL_LAB.md). *Observed running.*
- **Fast backend** — Qwen3.5-4B (GGUF) through pinned llama.cpp with CUDA, all layers on GPU. *Observed.*
- **Strata runtime** — pinned, checksum-verified large model; one real response through the Lab; selectable through the prepared runtime controls; cold startup can take about 15 minutes. *Observed; current active backend is shown in the browser.*
- **Verified-teacher tool-SFT lab** — frozen 550-episode synthetic tool-use benchmark with a deterministic verifier; Strata as teacher, Qwen3-0.6B as student. *Observed, in progress.*

Headline single-run numbers (details and caveats in [START_HERE.md](START_HERE.md#measured-so-far)): the 4B scores 76/110 on the frozen held-out tool-use set, Strata 55/110, the 0.6B student 14/110 before and 38/110 after teacher SFT. A control trained on scripted trajectories also reaches 38/110, so the teacher added no aggregate value. One run each; no model has been promoted on these results.

For the latest measured federation, diagnostic and discovery outcomes, read the [morning receipt](ops/haven-core/MORNING_20261026.md).

## Where the work is

The working integration is on `main` through PR48 (merge `41f15d4`). The following PRs record its component provenance; open component PRs are not separate installations:

- Runtime, merged: [PR #35](https://github.com/erpzz/haven/pull/35) (Ubuntu bootstrap) and [PR #36](https://github.com/erpzz/haven/pull/36) (Model Lab on Linux, CUDA installer, Strata service).
- Training: [PR #37](https://github.com/erpzz/haven/pull/37) (bounded LoRA pilot) and [PR #45](https://github.com/erpzz/haven/pull/45) (verified-teacher tool-SFT lab and results).
- Coordination: [issue #40](https://github.com/erpzz/haven/issues/40). In-flight features: [#41](https://github.com/erpzz/haven/pull/41), [#42](https://github.com/erpzz/haven/pull/42), [#43](https://github.com/erpzz/haven/pull/43).

Rules for agents and contributors: [AGENTS.md](AGENTS.md), [PRECEDENCE.md](PRECEDENCE.md). Owned branches, reviewable PRs, no self-merge, no pushes to `main`.

## Historical design and coordination (Sept 2026)

Before the runtime existed, Haven was a cumulative design and coordination hub (R01–R15 research threads, the RI-01 multi-agent campaign, the Observatory brief). Those documents are preserved as written and still describe the project's scope:

- [Current status](CURRENT_STATUS.md) and [thread queue](coordination/THREAD_STATUS.md)
- [Observatory entry point](coordination/R15_OBSERVATORY.md) · [Full R15 prompt](prompts/R15_GODS_EYE_OBSERVATORY_AND_OPEN_TOOLS.md) · [Issue #12](https://github.com/erpzz/haven/issues/12)
- [Prompt index](prompts/README.md) · [Protocol](coordination/PROTOCOL.md) · [Decisions](coordination/DECISIONS.md)
- [Preserved cumulative starter](baseline/cumulative-v1.0/START_HERE.md) · [All cumulative requirements](baseline/cumulative-v1.0/scope/COVERAGE.md)
- [R02 intelligence handback](design/H02/R02/v1/INTEGRATION_SUMMARY.md) · [R06 RF/spatial](design/H08/R06/v1/design/H08/INTEGRATION_SUMMARY.md) · [R08 engineering](design/H09/R08/v1/INTEGRATION_SUMMARY.md) · [H00 review of R02](design/H00/reviews/R02_v1.md)
- [NIGHT-01 review](review/NIGHT-01/independent/HAVEN_NIGHT01_Independent_Review.md) · [Plain-English explanation](baseline/cumulative-v1.0/family/HAVEN_IN_PLAIN_ENGLISH.md)

No research specialty replaces the project, and no publication grants device, account, purchase, deployment or coding authority. The original R14 prompt remains at [its pinned commit](https://github.com/erpzz/haven/blob/cffc1168255f600206c53fd63d1ad3ffd963121d/prompts/R14_HUMAN_AUGMENTATION_CYBERNETICS.md).

## Repository boundaries

Imported source documents are preserved, not rewritten: `baseline/`, versioned `design/`, `review/` and `snapshots/` keep their recorded provenance; corrections go in new versions. See [import status](coordination/IMPORT_STATUS.md). The earlier complete-source migration remains unverified, so some historical links may be missing; say so rather than recreating them. The ASTRA M0 application is not this repository, and the NIGHT-01 code here is a historical synthetic snapshot.

Treat this repository as public regardless of its visibility setting. Do not upload secrets, health records, household recordings, network inventories, IP addresses, private paths, model weights, adapters, runtime databases, raw model or agent transcripts, employer data or unreviewed exports. Original authorship and source-license conditions remain attached to imported material; no blanket license is inferred.
