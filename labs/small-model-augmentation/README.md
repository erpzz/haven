# Small-model augmentation — model admission, runtime observation and tool visibility

Workstream: [#126](https://github.com/erpzz/haven/issues/126). Base: `53387e74a0ad90786ac3ea16753c8ad99142e9df`. Author: Astra (ChatGPT), 2026-11-25. Review-only; Claude retains integration/merge ownership.

## Inventory and integration summary

Do not create parallel stacks. Existing work includes Cyber evidence and registry (#105, `69f7ae3`), Forge (#106, `2dd9c4b`), Hermes operator (#107, `a643257`), HARE (#115, `7f5af0d`), deterministic queries (#118), Purple integration (#122, `f701cd7`), and weight experiments (#123–125). The targeted source review included #122's `labs/purple-copilot-apm/ops/review.sh`, HERMES_RUNBOOK.md and `tests/hermes_review.py`. The launcher currently accepts an already-running model server from a health response; health alone is not model identity. A running MCP process also does not prove its tools were successfully discovered and exposed to the model. No active integration files are changed here.

The runtime observer is written against the exact llama.cpp revision used by #122, `b11146`: its server documentation says `GET /v1/models` returns the loaded model and honors `--alias`, and `GET /props` exposes `default_generation_settings.n_ctx`. Source: https://raw.githubusercontent.com/ggml-org/llama.cpp/b11146/tools/server/README.md.

The tool-visibility probe is written against Hermes `v2026.9.24`, the version pinned by #122. Its native MCP reference says startup discovery connects configured MCP servers, calls `list_tools()`, and registers tools using `mcp_{server}_{tool}`; missing the optional MCP package silently disables discovery. Its toolset reference says each configured MCP server creates a dynamic `mcp-<server>` toolset and the bare server name is also an alias. Sources:
- https://raw.githubusercontent.com/NousResearch/hermes-agent/v2026.9.24/skills/autonomous-ai-agents/hermes-agent/references/native-mcp.md
- https://raw.githubusercontent.com/NousResearch/hermes-agent/v2026.9.24/website/docs/reference/toolsets-reference.md

## Model admission contract

`preflight.py` accepts a JSON document via stdin, provided by a trusted launcher, with exactly four keys: expected model, requested model, observed model ids and observed effective context. Exact case-sensitive match is required; singleton inventory only; missing or malformed observations block. CLI exits 0 on pass or 2 on block and returns fixed diagnostic codes without echoing input. The minimum context is 64,000 tokens, matching the documented Purple/Hermes requirement. This contract is deliberately restricted to a dedicated single-model server.

`observe_llama.py` obtains those runtime observations without an LLM:
- only an explicit `http://127.0.0.1:PORT` root is accepted;
- environment proxies are disabled and redirects are never followed;
- `/v1/models`, `/props`, then `/v1/models` are read with timeout and response bounds;
- duplicate/malformed JSON and invalid schemas block;
- a changed model inventory during the check blocks;
- a pass sets `live_endpoint_verified=true`, meaning only that the targeted local endpoints responded consistently and passed the contract, not that weights were authenticated.

## Launcher-owned dedicated model lease

`owned_llama.py` closes the largest gap between a good-looking loopback endpoint and the process the launcher actually intended to trust.

For the strict profile it:

1. refuses an already-occupied loopback port instead of reusing an unknown server;
2. SHA-256 checks the exact llama-server executable and GGUF file before launch;
3. launches a new session/process group with fixed model, loopback host, port, context, parallelism, Jinja mode and alias arguments;
4. deliberately rejects an arbitrary llama-server argv tail, because a later `-m`, host, port, context or alias flag could override the values that were just admitted;
5. waits for the same `/v1/models` + `/props` runtime admission used by `observe_llama.py`;
6. requires the listening socket to belong exactly to the child PID (production probe: `lsof`);
7. while the lease is active, rechecks child liveness, server/model file identity, listener ownership and runtime identity/context;
8. can run a guarded Hermes command in its own process group; loss of the model lease blocks the run and terminates the guarded process group;
9. stops the dedicated model server on every guarded-command validation/launch/guard exit.

The strict helper currently rejects all `--server-extra` values. Performance flags can be added later as explicit typed launcher options after they have individual tests; an unstructured argv escape hatch is intentionally not part of the security boundary.

This is stronger than an alias check, but it is not OS attestation. The initial port-free check has an ordinary bind TOCTOU window that is closed only by the later listener-PID check. A malicious same-user actor that can replace files while preserving identity metadata, interfere with `lsof`, ptrace/inject into the process, or otherwise race the launcher is outside this prototype's qualified threat model. The real Mac integration must test `lsof` behavior and the actual llama-server process architecture before this lease is called production-qualified.

## Model-visible Hermes tool probe

`tool_visibility.py` answers a different question: **what tools did Hermes actually send to the model?** It does not infer success from process listings or `hermes mcp list`.

The probe:
1. requires an explicit Hermes executable and explicit `HERMES_HOME`, preventing an accidental test of the default profile;
2. starts a temporary loopback OpenAI-compatible scripted endpoint;
3. runs the real Hermes CLI with the caller-selected toolsets, while overriding only inference to the temporary endpoint using the pinned CLI's explicit custom `--base-url` / `--api-key` path;
4. the scripted endpoint replies `OK` and never requests a tool call;
5. captures the first model request and validates the exact OpenAI `tools` array;
6. requires caller-specified direct tool-name families and returns only counts/fixed errors, never raw schemas, stderr, profile paths or credentials.

Required prefixes are attributed to the most-specific match, so overlapping names such as `mcp_haven_` and `mcp_haven_cyber_` cannot false-pass when only Haven Cyber is visible. A Tool Search bridge by itself does **not** satisfy a direct-MCP requirement.

Example for the isolated profile, after checkout on the Mac:
```sh
python3 tool_visibility.py \
  --hermes "$HERMES" \
  --hermes-home "$STATE/hermes-pentest" \
  --toolsets haven,haven-cyber \
  --require-prefix mcp_haven_ \
  --require-prefix mcp_haven_cyber_ \
  --cwd /path/to/purple-copilot-apm
```
The exact toolset names and prefixes must match the profile's configured MCP server names. This command can start configured MCP server subprocesses during Hermes startup discovery, but the scripted model never invokes any tool.

## Mandatory second-pass test receipt

Linux CPU sandbox, Python standard library, no real model inference/GPU and no real Haven MCP processes. Exact executable/test bytes were compiled and exercised with deliberately broken HTTP proxy environment variables:
```sh
python3 -m py_compile *.py
HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 ALL_PROXY=http://127.0.0.1:9 \
  python3 -m unittest -v
```
Observed for the original admission/observer/visibility package: **40/40 test methods pass in 26.493 s**.

The launcher-owned lease was then added and tested separately from exact GitHub blobs. `git hash-object` matched the published blobs for `owned_llama.py`, `test_owned_llama.py`, `observe_llama.py` and `preflight.py`; `py_compile` passed and **19/19 lease tests passed** in the Linux sandbox. The prior 40-test files were unchanged, so this branch now has 59 recorded regression methods across two exact-blob author receipts rather than one claimed monolithic rerun.

Published/tested Git blob IDs:
- `preflight.py`: `c979fcf49a281c87ac18023a71a6842aad142670`
- `test_preflight.py`: `eb9baf988486af23f3a48431ac941e72b33df099`
- `test_preflight_review.py`: `16c131bba10e3db71338dc0a1d33d89c051b4e81`
- `observe_llama.py`: `bcaa1577a0df14713570eb01be2ec7a8c82f0288`
- `test_observe_llama.py`: `acb32d97c3f2716464797ea16c13947ed7534598`
- `tool_visibility.py`: `fdde655af8c00ebbe33d99ad8d17a7a8d0561402`
- `test_tool_visibility.py`: `c06d126053d1015355b665df44797763c49a6227`
- `owned_llama.py`: `e9b9e44103d32382bd94f02cc5666910859ef068`
- `test_owned_llama.py`: `e0172cde565fa1c3042a414ed3f7cba833a8cd25`

Tool-visibility adversarial coverage includes direct-family success; missing family; overlapping-prefix false-pass prevention; Tool Search-only rejection; unknown toolset; nonzero/no-request behavior; malformed and duplicate tool schemas; explicit-profile validation; timeout; exec failure; malformed model request; fixed/redacted CLI receipts; and the distinction between pre-launch validation and actual Hermes execution. These are producer tests, not independent qualification.

## Remaining blockers / next gates

**Model/process binding:** the dedicated-process lease prototype now rejects pre-existing ports, hash-checks the server/GGUF, proves listener ownership and supervises a guarded command. Product admission is still incomplete until the actual review launcher uses this path and the named Mac verifies real `lsof`, real llama-server startup/replacement/death behavior and the enrolled binary/model hashes. Same-user hostile races/OS injection remain out of scope for this prototype.

**Actual Haven/Haven Cyber visibility:** the harness is implemented, but the real isolated profile has **NOT been probed from this environment**. Do not mark MCP availability complete until the Mac run captures the actual first model request and shows both intended families directly visible. A failed probe is a useful result and should remain failed until configuration is repaired and rerun.

**Independent review and integration:** author second-pass review is not independent qualification. CI, macOS, real Hermes/Haven MCP startup, integrated launcher wiring, and post-merge tests remain unexecuted here.

No private transcripts, credentials, real host paths, reserve cases or training data are published. No deployment, M4 qualification or self-merge is claimed.
