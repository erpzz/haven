# ADR-HERMES-1: Hermes operates Haven through one audited MCP surface

## Decision

Hermes reaches Haven through one stdio MCP server, `haven`, with one tool per operation. Each tool wraps an existing controller rather than reimplementing it:

| Operation | Wrapped controller |
|---|---|
| Fleet, jobs, tasks, approvals, receipts, skills | `labs/engineer` Python APIs on the controller host |
| Model Lab | `labctl.py` on Slink over ssh (the `ops/haven-core/slink-lab.py` pattern) |
| GPU, units, Sentinel | a read-only probe sent over ssh stdin |

## Why not reuse #105's MCP shape directly

PR #105 (`labs/cyber`) exposes four fixed tools, with every registry tool reached through `cyber_call`. That is right for a 9B model reading a security knowledge base, where everything is read-only. For operations it has four problems:

1. **Approval sees only the dispatcher.** `cyber_call` is statically `readOnlyHint=True`. Hermes's per-tool approval would see one read-only tool and never ask before a change. Here, each change is its own tool with accurate annotations.
2. **Timeouts don't cancel.** `future.result(timeout=)` stops waiting but leaves the work running, and it reports `retryable`. Here, every remote action runs as a subprocess that is killed on timeout, and the receipt says `unknown`.
3. **The audit is a log, not a record of changes.** It holds a JSONL hash of the inputs, written after the call. Changes here get engineer ledger receipts, which are hash-chained, HMAC-signed and written before acting. They show in the Haven console and are checked by `Ledger.check_answer`.
4. **Validation is shallow and deployment is fragile.** Validation was top-level only (nested arrays went unchecked, and a `null` type raised `KeyError`). Hermes ran the server from a PR worktree path. The registry here validates recursively, and the installer deploys a commit export (`~/.local/share/haven-hermes/current`). The installer also repoints `haven-cyber` there.

**Kept from #105:**
- one registry
- schema-first tools
- input-hash-only read audit
- secrets only in the environment, and only on Slink
- untrusted-output wording in the server instructions
- the `prerequisites`/gating idea, now expressed as launch mode and flags

## Why stdlib JSON-RPC, not the mcp SDK

`labs/engineer/mcp_server.py` already speaks MCP 2025-06-18 with the standard library. Reusing that transport means:
- no venv
- no SDK version split (#105 needed shims for 1.x and 2.x)
- the same server runs on the Mac and on Slink with system `python3`

## Approval model

| Layer | Who decides | Enforced by |
|---|---|---|
| Change tools exist at all | owner, in Hermes config (`--mode operate`, `--allow-strata`) | this server |
| Each change call | owner, in the Hermes prompt (`trust: untrusted`) | Hermes (`tools/mcp_tool_handlers.py::_trust_gate_check`) |
| Risky steps inside an engineer task | owner, in the Haven console | `labs/engineer` policy and approvals |
| A Hermes-created tool becoming callable | owner, via `skills.py admit` on held-out cases | engineer skill admission (signed, content-hashed) |

Haven cannot observe Hermes's prompt. Receipts therefore record authorization as `mcp-client` with that note, and claim nothing more.

## Tool creation

Hermes doesn't get a second registry. `haven_tool_propose` writes a candidate in the engineer skill format (`skill.json`, `skill.py`, `recipe.md`) and runs Hermes's dev cases in the OS sandbox. It refuses to run code where no sandbox exists.

`skills.check_case` gained a general mode: `expect.result` must be contained in the skill's JSON output. The original `run_tests` contract still applies when no result is given.

Admission stays the owner's `skills.py admit` command, run against held-out cases written by the owner or an independent session. Hermes's own file and terminal tools could technically reach that directory, so the guarantee depends on who writes the cases. The admission record makes the author explicit.

## Known limits

- **Scheduler progress.** Jobs advance only while `scheduler.py serve` runs or someone runs a tick. `haven_job_submit` runs one placement tick and says whether serve is running.
- **No task agents yet.** `haven_task_start` uses only agents the owner allowlists in `hermes.json`. Today every configured agent either runs inference on the Mac, whose compute is off, or is hosted, so the default allowlist is empty.
- **Lab job polling.** The Lab job id comes from `labctl` without `--wait`; Hermes polls `haven_lab_job`.
