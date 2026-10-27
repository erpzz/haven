# Engineering frontend evaluation (2026-10-27)

Question: which browser workspace should Haven use for files, terminals, git and agent chat,
and what does Haven still need to provide itself?

## Decision

**Use Open WebUI Computer (`cptr` 0.9.21) as the workspace shell, keep Haven's own console for
agents, approvals, receipts, fleet and research, and connect the two through Haven's MCP
executor.** The Model Lab UI stays as it is: it remains the model-operations surface and the
fallback. Nothing was changed on Slink.

Why not one product for everything: cptr already does files, editor, persistent terminals, git
and chat with Claude Code / Codex / OpenCode / local models better than anything we would write.
It does not do Haven's job: per-action policy with an OS sandbox, signed receipts that survive
the model's own account of events, owner approvals for scoped actions, child agents with leases,
a fleet view, or held-out skill admission. Those stay in `labs/engineer`.

## What was actually exercised (Mac, loopback only)

| Step | cptr result |
|---|---|
| Install (isolated venv, pinned `cptr[mcp]==0.9.21`, `claude-agent-sdk==0.2.165`) | works; data in a private `CPTR_DATA_DIR` |
| First-run setup: local admin, one-time token link | works (test credential in a private 0600 file) |
| Open a Haven development workspace (fresh repo exported from this branch) | works via the workspace API; the folder picker hides dot-directories **and** symlinks |
| Browse and edit a file | works; **the rich Markdown editor rewrote 4 unrelated lines** (escaped `_` in links, dropped the final newline) for a 1-line edit |
| Terminal | real zsh in the workspace; ran `git status` and Haven's 23-test suite (OK) |
| Git status / diff / commit box / history | works, word-level diff |
| AI chat with a local model | Qwen3.5-4B on Mac Metal through an OpenAI-compatible `llama.cpp` connection: verified "Connected" |
| Real tool call through Haven | Qwen in cptr called Haven's `git_status` and `run_command` over MCP; receipts `R-fdf6…`, `R-c10a…` are in a verified Haven ledger and the task appears in the Haven console |
| Agent backends detected | Codex 0.164.0 ready; OpenCode 1.19.0 ready; Claude Code 2.1.310 ready after installing the `claude-agent-sdk` extra and starting cptr with the personal `CLAUDE_CONFIG_DIR` |
| Resume a conversation | chats persist in cptr's SQLite and reopen after reload |
| Side effect | **cptr modified the workspace `.gitignore`** (auto-ignores `.cptr`); set `CPTR_AUTO_GITIGNORE_DOT_CPTR=false` for Haven repos |

Not exercised in cptr: Claude Code and Codex *chats* inside cptr (Claude Code was exercised
through Haven's own runner instead; Codex's plan allowance was exhausted, reset reported by the
CLI as 2026-10-27 01:56 local), OpenCode end-to-end with the 4B model, cptr's own sub-agents,
browser tabs, messaging bots.

## Candidates

| | Open WebUI Computer (cptr) | OpenCode | Open WebUI + Open Terminal | Hermes Agent | Haven Model Lab (existing) |
|---|---|---|---|---|---|
| Version tried | 0.9.21 (PyPI) | 1.19.0 (npm) | not installed | not installed | `befd6ab` live on Slink |
| License | Open Use License = ELv2 + attribution; source-available, "commercial/organizational use" needs terms | MIT | Open WebUI license (BSD-3 + branding) | MIT (per docs footer) | repository |
| Files / editor / terminal / git | yes / yes / persistent / yes | TUI + web sessions, diffs; no file manager | via Open Terminal (Docker or host) | not described on the docs page read | no |
| Agents | Claude Code, Codex, OpenCode, Cursor, Gemini, Cline, own agent | its own agent (strong prompt, permission patterns) | Open WebUI tools | own agent, manages llama.cpp | text chat, fixed diagnostics |
| Local models | OpenAI-compatible, `llama.cpp` provider type | any OpenAI-compatible provider | yes | yes, manages llama.cpp itself | yes (owner of Slink runtime) |
| MCP | stdio + HTTP tool servers | yes | yes | not stated | no |
| Isolation | none: a signed-in user is the machine user; no per-user isolation | per-pattern permissions inside the agent process | Docker or bare metal | not stated | loopback, roles, no tools |
| Why / why not | best workspace shell; fits private single-owner use | best coding agent for local models; keep as a cptr backend | needs Docker (absent on the Mac); general assistant rather than workspace | desktop-first, overlaps with our runtime | keep for model ops |

OpenCode note: out of the box it offers OpenCode's hosted free models. Haven's config
(`~/.config/opencode/opencode.json`, see `opencode.example.json`) sets
`enabled_providers: ["haven-local"]`, so only the local endpoint is listed.

## Security notes and limits

- cptr is **single-owner**: anyone signed in has the host user's shell and files. Haven's
  two-person privacy boundary therefore needs one cptr instance per principal, each as its own
  OS user, or no shared instance at all. Do not expose it beyond loopback/SSH tunnel; do not put
  it behind a header-auth proxy (cptr's own warning).
- cptr asks its own Allow/Deny for MCP tools; Haven then applies its policy. Double approval is
  safe but slow; set cptr's approval for the `haven` server to auto once Haven's mode is chosen.
- Claude Code in cptr uses whatever `CLAUDE_CONFIG_DIR` cptr was started with. Start cptr with
  the personal profile; the default profile on this Mac holds an expired work login that must
  not be used.

## Install, run, rollback (Mac)

```bash
python3.12 -m venv ~/.local/share/haven-workspace/cptr-venv
~/.local/share/haven-workspace/cptr-venv/bin/pip install 'cptr[mcp]==0.9.21' 'claude-agent-sdk==0.2.165'
npm install --prefix ~/.local/share/haven-workspace/opencode-prefix opencode-ai@1.19.0   # optional backend
labs/engineer/scripts/start-cptr.sh        # loopback :8896, personal Claude profile, no auto .gitignore
```

Rollback: `pkill -f 'cptr-venv/bin/cptr run'`, then delete `~/.local/share/haven-workspace`
(venv, data, logs), `~/HavenWorkspaces` (a symlink) and, if unwanted,
`~/.config/opencode/opencode.json`. Nothing else on the Mac or Slink was changed.
