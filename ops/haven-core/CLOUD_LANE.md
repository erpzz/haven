# Cloud lane: Claude Code and Codex as explicit Haven workers

Haven stays local by default. The cloud lane adds two **explicitly selected**
workers to the existing private worker registry ([FEDERATION.md](FEDERATION.md)):
`Cloud · Claude Code` and `Cloud · Codex`. Each one runs a single finite turn
through the owner's own official CLI and plan. This is pattern C from
[SUBSCRIPTION_BRIDGES_20261005.md](../../labs/intelligence-bakeoff/SUBSCRIPTION_BRIDGES_20261005.md).

```
Browser ─▶ Slink Lab ─▶ providers/cloud-<lane>.sock ─(SSH reverse forward)─▶ Mac 127.0.0.1:8891
                                                                             cloud-worker.py ─▶ claude -p / codex exec
```

## Boundaries

- **Never automatic.** Automatic routing skips hosted lanes without probing
  them. The browser marks them "leaves this house" and shows the vendor and
  route class (`CLAUDE_CODE_PLAN`, `CHATGPT_PLAN`). Each result repeats where it went.
- **Plan only, never metered.** `ANTHROPIC_*`, `OPENAI_*` and other provider
  variables are removed from the CLI environment. The worker stops a turn if
  Claude Code reports any `apiKeySource` other than `none`, or reports paid
  overage. It never reads credential files or browser sessions.
- **No tools.** Claude Code: `--tools "" --restricted --strict-mcp-config
  --disable-slash-commands --no-session-persistence`, with a short Haven
  system prompt replacing the coding-agent prompt. Codex: read-only sandbox,
  shell/exec/apps/plugins/browser/computer-use/memories/hooks disabled, user
  config and rules ignored. The worker fails closed if it sees a reported tool,
  MCP server, tool-use block, or Codex command/file item.
- **Prompts stay off disk and out of `ps`.** Text goes over stdin; system text
  goes through a temporary 0600 file in a per-turn private directory, which is
  deleted afterwards. Receipts (`~/.local/state/haven-cloud-worker/requests.jsonl`)
  hold lane, outcome, timing, usage and a prompt hash only.
- **Bounded.** One turn at a time, a 200 s limit, and a daily request cap
  (default 50). Stop in Haven kills the CLI within about a second.
- **Owner-only, private transport.** Admin role only, as with other workers.
  Each lane terminates in a 0600 Unix socket inside the Lab's private
  enrollment directory. No TCP listener is added on Slink or the LAN.
- **Prior turns are quoted.** Conversation history is sent as quoted text and
  the model replies to the last user message. Temperature and seed are not
  applied.

## Operate

On the Mac, as the owner:

```bash
python3 ops/haven-core/cloud-worker.py configure --claude-config-dir ~/.config/claude-haven-personal
python3 ops/haven-core/cloud-worker.py serve       # or `enable` to install the login LaunchAgent
python3 ops/haven-core/cloud-worker.py enroll      # refuses unless the Lab's deployed code supports cloud lanes
python3 ops/haven-core/cloud-worker.py status
python3 ops/haven-core/cloud-worker.py disable     # stops the LaunchAgent and closes only this tunnel
```

`configure` records the stable CLI links and the Codex model named in
`~/.codex/config.toml`. The Codex lane uses `--ignore-user-config`, which would
otherwise fall back to a model that the account may not have. On Slink,
`labctl.py chat … --provider cloud-claude-code` and `labctl.py workers` drive
and list the lanes.

## Evidence, 2026-10-26 UTC

- **Static:** 13 cloud-lane tests use the real worker handler, the real Lab and
  fake CLIs that replay recorded event shapes. They include hostile variants
  (tools, MCP, API key, overage, mid-stream tool use, Codex commands), plus
  cancellation, the cap, environment scrubbing and argv privacy. All Model Lab,
  distillation, tool-SFT and bakeoff suites pass on Ubuntu 24.04 / Python 3.12.
- **Live, Claude Code 2.1.310, one session:** a request through a temporary
  integrated Lab on Slink went over the private socket and SSH tunnel to the
  Mac worker. It returned 128 tokens: first output 1.76 s, 4.08 s total,
  `apiKeySource=none`, no overage. Automatic, with only cloud lanes enrolled,
  refused and sent nothing. Stop mid-answer killed the CLI and kept the
  partial text.
- **Live, Codex 0.164.0:** the turn was correctly refused as a plan limit; the
  account's Codex allowance was exhausted. No successful Codex answer has been
  observed yet.
- **Not done:** the shared Lab was not redeployed while it was in use. The
  LaunchAgent was not installed; that needs owner approval. The CLI's
  quota-reset time is not surfaced in the browser yet.

## Rollback

Select a local worker. `cloud-worker.py disable` stops the Mac side. Delete
`providers/cloud-*.json` on Slink to remove the lanes from the registry. No
system, firewall, SSH or account settings are changed.
