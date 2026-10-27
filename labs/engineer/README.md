# Haven engineer — local and hosted agents doing real engineering work

Slinky's engineering layer. Local open-weight models, Claude Code and Codex all act on a
workspace through **one executor** that decides, sandboxes, runs and receipts every action.
Python standard library only (3.9+), like the Model Lab.

```
                 owner (browser)                         Open WebUI Computer (cptr, optional)
                       │  private link, bearer token          files · editor · terminals · git
                       ▼                                       agent chats (Claude Code / Codex / OpenCode)
              ┌─────────────────┐   start / cancel / approve
              │ console.py      │─────────────────────────────┐
              │ tasks · fleet · │                             │
              │ lineage·research│◀── events.jsonl, ledgers ──┐│
              └─────────────────┘                            ││
   ┌─────────────────────────────────────────────────────────┴┴──────────────┐
   │ runtime.py  run_task / delegate (child agents, leases, budgets)        │
   │   loop.py  OpenAI-compatible tool loop ── llama.cpp / MLX on Mac/Slink │
   │   hosted.py Claude Code / Codex CLIs ──(MCP stdio)── mcp_server.py      │
   │                            │                                            │
   │                     executor.py  validate → policy.decide → approve?    │
   │                            │       → run (sandbox.py) → ledger.py       │
   └────────────────────────────┼────────────────────────────────────────────┘
                                ▼
          workspace (git repo)   Seatbelt (macOS) / Landlock + no_new_privs (Linux)
```

## What is real today (2026-10-27)

| Capability | Status | Evidence |
|---|---|---|
| Local Qwen3.5-4B fixes a failing test end to end (read, edit, run tests, commit) | observed | record in private state; independent re-run of tests |
| Claude Code (Opus, subscription) works only through Haven tools, plan billing checked | observed | `apiKeySource=none`, executor receipts |
| Opus supervises a local Qwen child (lease on one file), reviews its diff, commits | observed | parent/child ledgers, lineage in console |
| Owner approval round trip from the browser | observed | receipt `decided_by: owner` |
| Skill authored by Opus, admitted on hidden held-out cases, run on Slink with no model | observed | `skills/run_tests/ADMISSION.json`, run-remote output |
| Inheritance benchmark (none / recipe / skill × Qwen, LFM) | see `research/` | preregistered in `morphogenesis/PREREGISTRATION.json` |
| Codex as an engineering agent | wired, not observed | Codex plan allowance was exhausted earlier |
| Deployments | not implemented | `deploy` class exists in policy only |

## Autonomy modes (enforced in the executor, not in prompts)

| | observe | engineer | autonomous |
|---|---|---|---|
| read, search, git status/diff/log | allow | allow | allow |
| edit / write / patch inside workspace | deny | allow | allow |
| development commands (tests, builds) | read-only commands only, read-only sandbox | allow (sandboxed) | allow (sandboxed) |
| push, history rewrite, `rm -r`, `git reset --hard` | deny | **ask owner** | allow if the scope grants it (push needs a granted remote) |
| package installs / network | deny | ask, or allow with the owner's network grant | allow with grant |
| commit on `main`/`master`/`release` | deny | ask | deny |
| sudo, disk/boot tools, credential stores, host service managers | **never** | **never** | **never** |
| child agents (`delegate`) | deny | allow (child ≤ parent) | allow (child ≤ parent) |

The owner's grants live in `~/.config/haven-engineer/scope.json` (e.g. `{"network": true}`), a file
no tool can write. Hosted agents need an explicit "this leaves the house" acknowledgement per task.

## Security model

- **Sandbox.** Every command runs under Seatbelt (macOS) or Landlock ABI ≥1 with `no_new_privs`
  (Linux): writes only to the workspace, its git common dir and a private temp dir; reads of
  `~/.ssh`, keychains, cloud credentials, Claude/Codex/gh auth and Haven's private state are
  denied; network off unless granted (Landlock filters TCP by port, not UDP). Without a sandbox,
  every non-read command needs the owner and autonomous mode is refused.
- **Git hooks/config.** Agents cannot change `.git/hooks` or `.git/config` (Seatbelt deny plus an
  executor snapshot/restore on Linux); executor git calls disable hooks and fsmonitor.
- **Receipts.** `ledger.py` hash-chains and HMAC-signs every state transition
  (proposed → authorized/refused → executed → succeeded/failed/unknown). Receipt ids are keyed, so
  a model cannot mint one. Final answers are checked for forged ids, failures described as
  successes, and claims ("tests pass", "committed", "deployed") with no supporting receipt; one
  correction turn is offered, then the ledger-rendered footer is shown beside the answer.
- **Tool output is data.** It is wrapped as untrusted and instruction-like text is flagged.
- **Console.** Loopback only, bearer token from a 0600 file passed in the URL fragment, Host
  header check (DNS rebinding), CSP, no file writes. Approvals and cancels are files in the
  0700 state directory, which the sandbox denies to agents.
- **Two-person privacy.** Not yet implemented beyond single-owner state; see backlog.

## Install and run (Mac or Linux)

```bash
cd labs/engineer
python3 -m unittest tests.test_engineer          # 23 tests, no model or network needed
cp agents.example.json ~/.config/haven-engineer/agents.json && chmod 600 ~/.config/haven-engineer/agents.json
python3 cli.py sandbox                            # confirm Seatbelt or Landlock
python3 console.py serve --port 8895              # private link: ~/.local/state/haven-engineer/console-url
python3 cli.py run --workspace REPO --agent qwen35-4b-mac --mode engineer "Fix the failing test and commit"
```

A local model needs an OpenAI-compatible endpoint with tool calling, e.g. llama.cpp:
`llama-server -m Qwen3.5-4B-Q4_K_M.gguf --host 127.0.0.1 --port 8892 --api-key-file KEY --jinja -c 32768`.

Claude Code / Codex use the owner's existing CLI login (`config_dir` in agents.json selects the
personal Claude profile). Any MCP client can use the executor directly:

```json
{"mcpServers": {"haven": {"command": "python3", "args": ["labs/engineer/mcp_server.py", "--workspace", "REPO", "--mode", "engineer", "--agent", "claude-code"]}}}
```

Fleet: `python3 fleet.py enroll NAME --ssh ALIAS` (alias must already have a pinned host key),
`python3 fleet.py scope 192.168.1.0/24` for passive discovery, `python3 fleet.py observe`.

Skills: `python3 skills.py admit CANDIDATE --heldout PRIVATE_CASES --author ID`,
`python3 skills.py run-remote run_tests --node ALIAS --repo DIR`.

## Rollback

Nothing here changes the Model Lab, Strata, system services, firewall or SSH settings.
Stop the console (`pkill -f "console.py serve"`) and any llama-server you started. Remove
`~/.config/haven-engineer`, `~/.local/state/haven-engineer`, `~/.cache/haven-engineer` and
`~/.local/share/haven-workspaces` to erase all engineer state (task history and ledgers included).
Open WebUI Computer rollback: see `docs/FRONTEND_EVALUATION.md`.
