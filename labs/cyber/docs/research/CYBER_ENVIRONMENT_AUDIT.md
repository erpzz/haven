# Cyber environment audit

Audited on 2026-10-31 by running commands on each host (the command is quoted where it matters). This repository is public, so host addresses, account names and secrets are left out on purpose.

Status labels: **verified** (a command showed it), **unavailable** (checked and absent), **untested** (present but not exercised), **permission-gated** (present but needs a decision or credential the agent should not take on its own).

## Hosts

| Host | Role | Hardware | Status |
|---|---|---|---|
| Slink (Ubuntu 24.04.5, kernel 6.8) | Haven Core: Model Lab, Open WebUI, forge loop, all GPU work | Ryzen 9 3900X (24 threads), 62 GiB RAM, RTX 2070 SUPER 8 GiB (driver 580.178, CUDA 12.8 through torch), 915 GB disk (559 GB free) | verified over the existing SSH alias |
| MacBook (macOS 26.5.1) | Operator workstation, Hermes Agent, repo checkouts | Apple M4, 16 GB, 35 GB free | verified; **compute is off by owner instruction since 2026-10-27**: no Mac inference or benchmarks |
| Kaggle (2× T4 16 GB, free tier) | Training lane used by the forge loop | via the existing Kaggle account | verified indirectly (forge kernels are running); owned by the forge session |

## Model: Qwythos-9B-v2

| Fact | Value | Status |
|---|---|---|
| Architecture | `Qwen3_5ForConditionalGeneration` (`model_type: qwen3_5`): 32 layers, 24 Gated DeltaNet `linear_attention` + 8 `full_attention` (every 4th), hidden 4096, 16 heads / 4 KV heads, vocab 248,320, 1 MTP layer, 1M context (YaRN), vision tower present | verified (`config.json`) |
| Checkpoint | bf16 `model.safetensors` (19.3 GB), tokenizer, chat template | verified, on Slink under the forge models directory |
| Serving format | `Qwythos-9B-v2-MTP-Q4_K_M.gguf` (5.9 GB) on llama.cpp b11146 with `--jinja` | verified: a llama-server on port 8095 for this work, auto-fit sharing the 8 GB GPU with the forge teacher (≈4.1 GB used) |
| Licence | Apache-2.0; base `empero-ai/Qwythos-9B-Claude-Mythos-5-1M` | verified (model card front matter) |
| Chat/tool format | Qwen3.5 XML tool calls (`<tool_call><function=…><parameter=…>`), `enable_thinking` switch | verified: llama-server returns parsed OpenAI `tool_calls` |
| Same model on the Mac | Hermes is configured for `qwythos-9b-v2` on a local llama-server (port 8080, `empero-ai/Qwythos-9B-v2-GGUF:Q4_K_M`, 64K context) | verified with a `GET /v1/models`; not used (Mac compute off) |
| Prior measurement | Another session benchmarked it today on the frozen secpatch held-out set: 0.4865 (n=259), FPR 0.108, ≈48 tok/s end-to-end | read from Slink bench files |
| 9B QLoRA on the 8 GB card | **unavailable**: `forge-qlora-probe` loaded NF4 weights (3.33 GiB) and then failed in backward with `CUBLAS_STATUS_ALLOC_FAILED` (19:27Z) | verified from the unit journal |

## Agent runtime

| Item | Finding | Status |
|---|---|---|
| Hermes Agent | v0.22.5 (2026.9.24), git install, own Python 3.14 runtime and uv | verified (`hermes --version`) |
| Hermes MCP | stdio and HTTP clients; `hermes mcp add/test/list`; config key `mcp_servers` | verified; **`haven-cyber` registered and tested: connected, 4 tools** |
| Hermes skills and memory | skills directory and `memories/` present | untested for cyber content |
| Hermes on Slink | not installed | unavailable (not needed: the eval harness talks to llama-server directly) |
| MCP Python SDK | `mcp` 2.3.0 in an isolated venv (`~/.local/share/haven-cyber-venv`, made with Hermes's uv). FastMCP is renamed `MCPServer` in 2.x; the server supports both | verified (`scripts/mcp_smoke.py` passes) |

## Tooling

| Tool | Slink | Mac |
|---|---|---|
| Python | 3.12.3, SQLite 3.45.1 with FTS5 (verified) | 3.15.2 (Homebrew); 3.14.9 inside Hermes |
| uv / pipx | unavailable | uv only inside Hermes's tools directory |
| Node.js | unavailable | verified (Homebrew) |
| PowerShell (`pwsh`) | unavailable | unavailable, so **Maester cannot run locally**; results are imported instead |
| Docker | binary present, user not in the `docker` group: **permission-gated** | unavailable |
| Podman, Homebrew | unavailable / n.a. | Homebrew verified |
| Virtualization | `/dev/kvm` present, no libvirt/QEMU userland: untested | n/a |
| Security CLIs (Azure CLI, Prowler, ScoutSuite, Semgrep, osquery) | all unavailable | all unavailable |
| GitHub CLI | n/a | verified, authenticated |
| Training stacks | `forge-train-venv`: torch 2.11+cu128, transformers 5.22, peft 0.21, bitsandbytes 0.50, accelerate 1.15. `haven-training-venv`: torch 2.8, transformers 4.56, peft 0.17 | n/a |

No permanent system-level installation was made. The only addition is the user-level MCP venv on the Mac.

## Services that must not be disturbed (Slink)

`haven-model-lab` (loopback UI), `haven-openwebui` and `haven-openwebui-test` (loopback), `forge-teacher-server` (GLM-4.7-Flash on :8093, lowest priority, experts on CPU), the `haven-forge.timer` loop and the forge backup timer. This work added two transient user units: `haven-cyber-qwythos` (llama-server on :8095) and `haven-cyber-eval` (the harness). Both are stoppable and resumable.

## Existing Haven functionality reused

- **`labs/intelligence-bakeoff`:** the earlier Hermes plugin and harness pattern, plus the secpatch forge (training lane, held-out discipline, promotion gates).
- **Slink's Model Lab llama.cpp engine build:** used as-is for serving.
- **No overlap:** there was no cyber knowledge base, MCP security tooling or evidence model in `main`, so `labs/cyber` adds these without replacing anything.

## Credentials and tenants

- **Microsoft tenant:** none available. No Azure CLI login, Graph token or tenant is present, so all Entra/Azure work uses synthetic Graph-shaped snapshots.
- **Live collector:** `entra.graph.collect` is built and tested against mock HTTP responses only. It stays disabled unless `HAVEN_CYBER_ALLOW_LIVE=1` and a token are supplied by the operator.
