# Ecosystem and model scout — refresh, 2026-10-26

Supersedes the *volatile facts* in [the 2026-10-05 scout](ECOSYSTEM_AND_MODEL_SCOUT_20261005.md);
that document's strategy is retained unchanged. Classification:
**PUBLIC_RESEARCH + STATIC source reading**. Nothing here was installed or
deployed, and no model weights were downloaded. Versions, licenses and defaults
come from GitHub/PyPI/Hugging Face APIs and from the projects' own source at the
pinned tags, all read on 2026-10-26 UTC.

## Corrections to 2026-10-05

| Claim on Oct 5 | Current primary source | Consequence |
|---|---|---|
| Jan is AGPLv3 | `janhq/jan` LICENSE is **Apache-2.0** (v0.8.7, 2026-10-20) | Jan is now permissively forkable |
| llama.cpp is a fixed reference | Releases reached **b11889** (2026-10-25). Haven pins **b11146** (2026-09-23), about 740 builds behind. Homebrew now ships `0.7.0` (the Mac worker uses it) | Two engine versions are now in the federation; record both per result |
| Gemma not in scope | **Gemma 4** (E2B/E4B/12B/26B-A4B/31B) is **Apache-2.0**, with official `ggml-org` GGUFs and Google QAT q4_0 | New small multimodal non-Qwen family |
| Granite 4.0 H-Tiny | **Granite 4.2** 3B/8B GGUF (Apache-2.0, 2026-09-02) | Replaces 4.0 as the IBM candidate |

## Interfaces versus authority

Haven's rule is that the **runtime binds identity and executes only fixed,
authorized tools; a model or UI only proposes**. A frontend is acceptable when
it stays an *interface*. It becomes a problem when it brings its own execution
authority: server-side code, shell, MCP or plugins.

| Project (pinned) | License | What it is | Authority it brings by default | Fit |
|---|---|---|---|---|
| Open WebUI **v0.12.4** (PyPI wheel sha256 `02e9caba96234db3fa17a92e56163b3f7f2b8ca8227fa886b85c178d696483f6`) | Open WebUI License: BSD-3 plus a branding clause (≤50 users may rebrand). Not OSI | Multi-user browser shell with RBAC | `ENABLE_CODE_EXECUTION=True`, `ENABLE_CODE_INTERPRETER=True` (Pyodide), `ENABLE_COMMUNITY_SHARING=True` and `ENABLE_VERSION_UPDATE_CHECK=true` are all on by default. Admins can install server-side Python tools/functions. User workspace-tool access defaults to **False**. The Docker image sets `ANONYMIZED_TELEMETRY=false`, `SCARF_NO_ANALYTICS=true`, `DO_NOT_TRACK=true` | **Best household shell. Trial it with all execution features off** (below) |
| LibreChat **v0.8.8** | MIT | Multi-provider agent shell | Agents, MCP and a code interpreter that is now a *self-hostable* Apache-2.0 service. Needs MongoDB | Best permissive fork target; more services to run |
| AnythingLLM **v1.18.0** | MIT | RAG/workspace app | README: anonymous telemetry, opt out with `DISABLE_TELEMETRY=true`. Multi-user is Docker-only. Agents can act | Good for documents; telemetry must be off |
| Jan **v0.8.7** | Apache-2.0 | Desktop app with local llama.cpp and MCP | MCP servers with approval | Good **Mac-native client** for a remote Haven endpoint; not a household server |
| LM Studio / LM Link | Proprietary app (the `lms` CLI is MIT) | Remote models over LM Link | LM Link requires an LM Studio account, Hub discovery, Tailscale and preview access | **Excluded**: external account and service dependency |
| OpenCode **v1.19.4** (repo now `anomalyco/opencode`) | MIT | Coding agent | Shell and file edits in a workspace | An **agent, not a frontend**: use only as a sandboxed worker, never with Haven host credentials |
| Hermes Agent **v0.22.5** | MIT | General agent runtime (existing bakeoff adapter) | Terminal and tools | Same as OpenCode |

### One concrete reversible trial: Open WebUI as a pure interface

This is a proposal, not executed. It needs the owner's go-ahead and runs on the
owner's schedule.

- **Install**: `open-webui==0.12.4` with the wheel hash above, in a new
  user-owned Python 3.12 venv on Slink (`requires_python >=3.11,<3.13`). This
  needs no Docker group, no sudo and no system packages. Cost: a large
  dependency download (PyTorch CPU and sentence-transformers). Record the
  resolved `pip freeze` privately.
- **Network**: bind `127.0.0.1` on a new port and reach it only through the
  existing SSH tunnel pattern. No LAN listener, no UFW change.
- **Environment** (`ENABLE_PERSISTENT_CONFIG=False`, so the environment wins
  over database state):
  - `OFFLINE_MODE=true` (sets `HF_HUB_OFFLINE=1`), `ENABLE_VERSION_UPDATE_CHECK=false`,
    `ANONYMIZED_TELEMETRY=false`, `SCARF_NO_ANALYTICS=true`, `DO_NOT_TRACK=true`;
  - `ENABLE_CODE_EXECUTION=false`, `ENABLE_CODE_INTERPRETER=false`,
    `ENABLE_COMMUNITY_SHARING=false`, `ENABLE_OLLAMA_API=false`;
  - leave `ENABLE_WEB_SEARCH` false (default), `ENABLE_DIRECT_CONNECTIONS`
    false (default) and `USER_PERMISSIONS_WORKSPACE_TOOLS_ACCESS` false
    (default);
  - `USER_PERMISSIONS_CHAT_FILE_UPLOAD=false`, because the offline RAG
    embedder is not provisioned;
  - `WEBUI_AUTH=true`, then `ENABLE_SIGNUP=false` once the owner account exists;
  - `WEBUI_SECRET_KEY` read from a private 0600 file;
  - `DATA_DIR` set to a new private directory;
  - **install no tools or functions**.
- **Backend**: only the Lab-owned loopback llama-server, with its existing key,
  as one OpenAI connection. **This bypasses Haven's authority and routing**,
  which is exactly what the trial must measure: what the shell adds (history,
  editing, mobile UI) against what Haven would need to expose. The minimal
  missing piece is a Haven OpenAI-compatible facade that accepts
  `ENABLE_FORWARD_USER_INFO_HEADERS=true` identity (`X-OpenWebUI-User-Id`)
  *only* from the shell's loopback origin plus a shared secret, and binds the
  principal itself.
- **Acceptance**:
  - one authenticated chat;
  - unauthenticated requests rejected;
  - no outbound connection during a session, checked with `ss -tnp`;
  - the code/tool UI is absent;
  - a second, non-admin account cannot see the owner's chats.
- **Rollback**: stop the process and delete the venv and data directory.
  Nothing else changes.

## Model shortlist (metadata only; no weights downloaded)

All of these architectures already had llama.cpp support before the b11146 pin
(Gemma 4 April 2026, LFM2/SmolLM3 July 2025, Mistral3 2025). Loadability on
b11146 is still **unverified until loaded**. Gemma 4's 2026-10-19 MTP sidecar
GGUFs may need a newer engine. Sizes are file sizes.

**Mac worker (Apple M4, 16 GB unified, Homebrew llama.cpp 0.7.0)**: non-Qwen,
at least 8K usable context, replacing the 2024-era SmolLM2 1.7B (2K context)
after the Haven suite runs.

| repo @ revision | license | variant and size | notes |
|---|---|---|---|
| `ibm-granite/granite-4.2-3b-GGUF` @ `c40945d71cd9` | Apache-2.0 | Q4_K_M 2.24 GB (Q8_0 3.89) | 128K ctx, tool-calling focus, text |
| `mistralai/Ministral-3-3B-Instruct-2512-GGUF` @ `eb599d408350` | Apache-2.0 | Q4_K_M 2.15 GB, plus BF16 mmproj 0.84 GB | 256K ctx, function calling, vision |
| `ggml-org/gemma-4-E2B-it-GGUF` @ `6938c58e6985` | Apache-2.0 | Q4_0 2.84 GB, plus mmproj Q8_0 0.56 GB | Multimodal; E4B Q4_0 is 4.59 GB if memory allows |
| `ggml-org/SmolLM3-3B-GGUF` @ `4965cb60b150` | Apache-2.0 | Q4_K_M 1.92 GB | Open-data baseline, 64K ctx |

**Slink GPU challengers to the incumbent Qwen3.5-4B Q4_K_M**: Ministral 3 8B
Q4_K_M 5.20 GB, Granite 4.2 8B Q4_K_M 5.35 GB, Gemma 4 E4B Q4_0 4.59 GB. Run
them on the frozen `tool_sft` held-out suite (PR #45) under identical settings.
The 4B's measured weakness there is substituted proposals on execution
requests.

**Trainable HF students** (parameter counts from safetensors metadata):

- `Qwen/Qwen3-1.7B` @ `70d244cc86cc`: 2.03B, text-only. The cleanest next
  student.
- `Qwen/Qwen3.5-0.8B` and `Qwen3.5-2B`: 0.87B and 2.27B. These are
  image-text-to-text checkpoints, so text-only LoRA through them needs
  verification.
- `Qwen/Qwen3.5-4B`: 4.66B, the deployed family. fp16 alone is about 9.3 GB,
  so on 8 GB it is only an NF4/QLoRA *feasibility measurement*, never an
  assumed fit.

**Hold pending license review**: `LiquidAI/LFM2.5-*` (license `other`) and
`nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF` (license `other`). Phi-4-mini has no
first-party GGUF (`ggml-org/Phi-4-mini-instruct-GGUF` is not public), so it is
deprioritized on provenance.

## Critique of PR #44 (registry / reverse SSH / routing) @ `cbf11f2`

Strengths:

- server-side owner-only gate: a non-admin `provider_id` other than `managed`
  returns 403, and that includes `auto`;
- literal-loopback endpoints and provider IDs only, never URLs;
- a fresh authenticated probe at every dispatch;
- fail-closed, with no cloud fallback;
- `ExitOnForwardFailure=yes`;
- the secret travels over SSH stdin, not argv;
- enrollment only from private admin files, so a model cannot enroll a worker.

Issues:

1. **The digest is worker-declared, not verified on Slink.** The probe checks
   only that the alias `haven-mac-smollm2` is listed. `model_sha256` comes from
   the enrollment payload, verified on the Mac by `prepare()` with a size/mtime
   cache. Label it `WORKER_DECLARED` in the UI and receipts rather than letting
   it read as Haven-verified.
2. **The bearer key goes to whatever listens on 127.0.0.1:8890.**
   `ExitOnForwardFailure` protects tunnel setup. After the tunnel drops, any
   local process that binds 8890 receives the worker key at the next probe.
   The risk is low on a single-user host, but cheap to close: before sending
   the key, check that the listening socket belongs to the owner's `sshd`
   session (inode → PID → UID), or use challenge-response so the key never
   leaves.
3. **The 2048-token context limits usefulness more than speed does.** One of
   the 3B entries above at 8K is a better test of real federation value on
   16 GB.
4. `auto` adds a probe round-trip to every request. That is acceptable, but
   record per-message `route_reason` in the user-visible transcript, not only in
   job state, so a silent model change mid-conversation is visible.
