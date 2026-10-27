# Agent and model compatibility (2026-10-27)

"Observed" means a real run in this branch's work with an independently checked outcome.

| Agent | Where inference runs | Where tools run | Haven executor path | Tool calling | Engineering outcome | Notes |
|---|---|---|---|---|---|---|
| Qwen3.5-4B Q4_K_M | Mac M4 Metal (llama.cpp b11669, port 8892) | Mac, Seatbelt | `loop.py` | native via `--jinja` | observed: fixed+tested+committed (146 s); E1 transfer tasks 3–4/4 per arm | ~5–50 s per step on the Mac; wastes early steps finding the test command; ignored an offered skill tool 4/4 times |
| LFM2.5-8B-A1B Q4_K_M | Mac M4 Metal (port 8893) | Mac, Seatbelt | `loop.py` | native | see `research/e1-inheritance.json` | Slink round 1: 2.4x Qwen decode; tool suite 54/110 (74 with runtime receipts) |
| Qwen3.5-4B (Model Lab) | Slink RTX 2070 Super | — | not wired: the Lab engine is the owner's live backend | — | not run | needs a GPU lease and an SSH-tunnelled endpoint; one enrollment entry in `agents.json` |
| Claude Code 2.1.310, Opus | Anthropic, owner's Pro plan | Mac, Seatbelt (through MCP) | `hosted.py` + `mcp_server.py` | MCP | observed: fix in 13 s; supervisor of a local child in 82 s; authored the admitted `run_tests` skill (31 actions) | `apiKeySource=none` checked per run; built-in tools disabled so every action is receipted |
| Codex 0.164.0 | OpenAI, owner's ChatGPT plan | Mac (through MCP) | `hosted.py` + `mcp_server.py` | MCP | blocked: plan usage limit (reset reported by CLI) | shell tool disabled; read-only sandbox for its own tools |
| OpenCode 1.19.0 | local endpoint only (`enabled_providers`) | Mac (its own tools) + Haven MCP | MCP | native | not run end to end | its own bash/edit tools bypass Haven receipts; use `permission` patterns or disable them |
| Open WebUI Computer 0.9.21 chat | local Qwen via OpenAI connection | Mac (Haven MCP) | MCP stdio tool server | native | observed: Haven `git_status`/`run_command` receipts from a cptr chat | cptr adds its own Allow/Deny before Haven's policy |
| Child agents (`delegate`) | any configured local agent | parent's host, leased files | `runtime.delegate` | — | observed: Qwen child under Opus | child mode ≤ parent; depth ≤ 3; own ledger linked by `parent_id` |
| Inherited skill (no model) | — | Mac or Slink (Landlock) | `skills.py run-remote` | — | observed on Slink | node suites need node on the node |

## Hosts

| Host | Sandbox | Enrolled | Observed role |
|---|---|---|---|
| Mac M4, 16 GB | Seatbelt (`sandbox-exec`) | local | tools, Metal inference, console, cptr |
| Slink, Ryzen 9 3900X, 64 GB, RTX 2070 Super 8 GB | Landlock ABI 4 + no_new_privs | `OWNER_SSH`, pinned host key | skill execution with no model; Model Lab owns the GPU |
| ThinkPad, others | — | not enrolled | appear only as passive candidates if in the ARP cache |
