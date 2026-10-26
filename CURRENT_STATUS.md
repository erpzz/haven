# Current status

## Runtime and training status — 2026-10-26

Assembled from saved receipts, PR descriptions and issue #40 checkpoints as of 2026-10-26 05:00 UTC. Tags: **observed** (real run, receipt saved), **prepared** (installed and verified, not routinely running), **planned** (no code). The older coordination table below is kept as the September 2026 historical baseline.

| Work | Status | Evidence | Next gate |
|---|---|---|---|
| Linux GPU host administration | observed: key-only SSH, signed NVIDIA driver surviving a reboot with Secure Boot, restricted ingress, Docker/NVIDIA GPU visibility test; Tailscale installed but stopped | [PR #36](https://github.com/erpzz/haven/pull/36), [ADMIN_RECOVERY.md](ops/haven-core/ADMIN_RECOVERY.md) | none required; do not repeat audits |
| Model Lab on Linux | observed: systemd user service on loopback 8877, opened from the Mac via `ops/haven-core/open-lab.py` | [PR #36](https://github.com/erpzz/haven/pull/36), [LINUX_MODEL_LAB.md](ops/haven-core/LINUX_MODEL_LAB.md) | merge of the #35/#36 stack toward `main` after review |
| Fast 4B backend (Qwen3.5-4B, llama.cpp b11146 CUDA) | observed: 33/33 layers on GPU; one warm response 0.17 s first output, 91.25 decode tok/s | [PR #36](https://github.com/erpzz/haven/pull/36) | sustained-speed and quality qualification not done |
| Strata runtime (v0.2.6, Control 0.1.51, engine 0.1.50) | prepared: shards verified; one observed 27-token response, 0.834 s first output, 27.7 tok/s; cold start 868 s / 870.6 s; stopped for normal use | [receipt](ops/haven-core/linux-strata-result-20261026.json), [STRATA_LINUX.md](ops/haven-core/STRATA_LINUX.md) | storage bottleneck diagnosis in [PR #41](https://github.com/erpzz/haven/pull/41) |
| Prepared runtime switching and read-only host diagnostics in the Lab | implemented on GitHub, unit-tested, live-unverified | [PR #41](https://github.com/erpzz/haven/pull/41) | one real 4B → Strata → 4B cycle through the browser |
| CPU-only inference lane | implemented on GitHub twice (overlapping), unit-tested and CI-green, live-unverified | [PR #42](https://github.com/erpzz/haven/pull/42), [PR #43](https://github.com/erpzz/haven/pull/43) | select one implementation; real browser → CPU response with isolation evidence |
| Bounded 0.6B LoRA pilot | observed, negative: 40 steps in 18.016 s; no fact or skill gain on 11 frozen probes; no adapter promoted | [PR #37](https://github.com/erpzz/haven/pull/37) | superseded by the tool-SFT lab |
| Verified-teacher tool-SFT lab | observed: frozen 550-episode benchmark; on the 110 held-out episodes 4B 76, Strata teacher 55, 0.6B base 14, 0.6B after teacher SFT 38, oracle-control SFT 38; one run each, single seed; verifier amended three times with disclosure before any trained-student result; teacher adds no aggregate value over scripted trajectories; no adapter promoted | [PR #45](https://github.com/erpzz/haven/pull/45), [RESULTS.md](https://github.com/erpzz/haven/blob/claude/opus-tool-distill-20261026/labs/intelligence-bakeoff/distillation/tool_sft/RESULTS.md), [issue #40](https://github.com/erpzz/haven/issues/40) | peer cross-review; next hypothesis, not a repeat of this run |
| Mac-side federated worker | implemented on GitHub, stacked on PR #41; not reviewed here | [PR #44](https://github.com/erpzz/haven/pull/44) | review and acceptance |
| `main` | holds September 2026 design/coordination documents only | — | stacked PRs #35 → #36 → … after review |
| Assistant product, memory, multimodal, spatial, robotics, drones, wearables | planned; design documents only | historical section below | separate explicit work packages |

Nothing in this table is a model-quality qualification. Every number is a single observed run. Raw prompts, answers, credentials, model weights, adapters and machine inventories stay off GitHub.

## Historical coordination baseline — 2026-09-28

Assembled 2026-09-28 from supplied documents. Not a live inspection of the PC or any running agent.

| Work | Supported status | Next gate |
|---|---|---|
| Repository publication | Authorized by operator; see import receipt for actual completed verification | Complete source/remote hash checks |
| ASTRA M0 | Separate application; supplied NIGHT-01 report says code existed and operator/iPhone acceptance was pending | Actual M0 owner report and operator acceptance; no merge here |
| NIGHT-01 N0/N1/N2 | Producer reports complete synthetic laboratory; independent review retained baseline with R1 gap | Review latest R1 evidence |
| R1 worker lifecycle | Issue documented; no accepted completion evidence supplied to this hub | Python 3.12 reproduction, fix, regression and review |
| R02 intelligence | v1 design delivered; H00 review recommends acceptance in principle | P01 reconciliation and R03/H04 semantics |
| R06 RF/spatial | Saved v1 design handback available | H00/H04/H06 and R07 contract review; no live sensing |
| R08 engineering | Saved v1 design handback available | P00 reconciliation; H04/H06 and R06 interface alignment |
| R03 privacy | No completed handback in the material imported | Next priority assignment |
| R13 validation | No completed handback in the material imported | Focused crosswalk and acceptance review |
| R07 world model | No completed handback in the material imported | Next wave after initial RF/privacy review |
| R01/R04/R05/R09/R10/R11/R12 | Retained scope and original prompts; completion not established | Schedule bounded waves, not all at once |
| Models/devices/physical capabilities | Not qualified by these imports | Separate explicit benchmark or device campaign |

Do not mark a thread running or done from a filename or this index. Actual agent status requires a task receipt. All imported tests retain their original environment and stated limits. Source research dates are not current product verification.

### Foundation preserved

The original M0 stack is Python 3.12, FastAPI, Pydantic 2, Jinja2, one Uvicorn worker and local SQLite under Ubuntu 24.04/WSL2. The current N1/N2 snapshot is a separate offline test-double library. The M4 advisory baseline remains `qwen2.5vl:3b`; model-research candidates do not replace it.

### Coding queue

R1 repair remains a separate narrow task. Finish/review M0 separately. Do not begin M1, live model integration, a framework migration or a physical campaign merely because a handback recommends it.

### R15 publication update — 2026-09-28

The original R15 Observatory prompt is now on main through [PR #10](https://github.com/erpzz/haven/pull/10), merge `bff72a5e8a2faf86a6ded43649e0a098e80337a6`; its content blob remains `28942162876c96d2c92c020ade1e5f59cca4ff02`. [The R15 entry point](coordination/R15_OBSERVATORY.md) links the supporting brief, source notes, opportunity backlog, starting message and optional R15A–F assignments. [Issue #12](https://github.com/erpzz/haven/issues/12) tracks the research handback.

This records publication of instructions and proposed ideas, not a completed R15 study, deployed Observatory, runtime test, model evaluation or device capability. No research or background agent is started by adding the files. No new PC, M0, NIGHT-01 or R1 completion state is asserted. R14 remains referenced at its pinned original prompt; no completion evidence is reviewed here.

The older full-source migration and its temporary importer are not verified or repaired by this addition. The existence of the earlier workflow is not proof that it ran. Imported baseline completeness and any remaining historical broken links stay separate from the new R15 documentation.
