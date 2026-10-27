# Acceptance record — Haven engineer, first milestone (2026-10-27)

Branch `claude/agentic-workspace-20261027`, based on `main` 656c19e and merged with `ce27ce5`.
Raw task records, ledgers and transcripts stay in the owner's private state directory; this file
holds only sanitized outcomes. Every "observed" row was re-checked outside the agent.

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Browser engineering interface integrated with Haven | **met** | Open WebUI Computer 0.9.21 workspace (files, edit, terminal, git diff, chats that resume) with Haven's MCP executor; Haven console for tasks, approvals, fleet, lineage, research. `docs/FRONTEND_EVALUATION.md` |
| 2 | Local model completes a file-edit/test/fix cycle through tools | **met** | Qwen3.5-4B on Mac Metal: read, edit, test (exit 0), commit; 10 receipted actions, 146 s; tests re-run independently |
| 3 | Device and worker dashboard from real observations | **met** | Console Fleet view: Mac and Slink probes (CPU, memory, GPU, models, services, Slinky work), host-key-pinned enrollment, passive candidates |
| 4 | Durable, bounded agent-task system | **met** | Task directories with events, signed ledgers and records; step/time/command budgets; cancel; reconnect by byte offset; orphaned tasks marked interrupted; `cli.py brief` |
| 5 | Real child-agent execution with evidence | **met** | Opus delegated `slugify.py` to a Qwen child (lease, depth 1, own ledger); supervisor reviewed the child diff before committing |
| 6 | Model Lab and active experiments preserved | **met** | No Slink service, model, GPU job or deployment touched; the paradigms session and the later download ran undisturbed; Slink was used only for read-only probes and a 0.2 s CPU skill run |
| 7 | Opus-led coordination where the plan permits | **met (bounded)** | Claude Code (Opus) on the personal Pro plan, `apiKeySource=none`, only Haven tools; supervised a local child; authored the admitted skill. Codex blocked by its plan limit |
| 8 | Initial executable Morphogenesis experiment | **met** | `run_tests` authored by Opus, admitted 5/5 on hidden held-out cases, executed on Slink with no model; E1 preregistered and run (results below) |
| 9 | Tests for permissions and non-interference | **met** | 25 unit tests: mode decisions, deploy with health-check rollback, sandbox escape/hooks/network, ledger tampering, forged receipts, approvals, leases, child scope, pipefail, MCP, console auth/Host/paths, skill admission and tampering |
| 10 | Branch/PR, install, evidence, rollback | **met** | `README.md` (install, run, rollback), this file, PR |

## Not done (honest list)

- Deployments: local staging deploy with health check and automatic rollback is implemented and tested; no remote (Slink) or production target is wired.
- Remote tool execution on Slink by an agent (only a no-model skill ran there).
- Two-person isolation: single-owner state; cptr has no per-user isolation.
- Codex engineering run: plan usage limit.
- OpenCode end-to-end with the 4B model; Open WebUI + Open Terminal; Hermes Agent (docs only).
- MoE/placement experiments on Slink (GPU owned by the live Model Lab backend).
- Swarm scheduling across machines; ThinkPad not enrolled.

## Bugs found and fixed during acceptance

- Classifier split on `;` and newlines inside quotes, forcing needless approvals (test added).
- A failing test piped to `tail` produced a "succeeded" receipt; commands now run with `pipefail`.
- MCP results with `structuredContent` hid tool output from Claude Code (it saw receipts only and
  refused to guess); results are text only now.
- Approvals panel re-rendered every 4 s, moving buttons under the cursor.
- Child receipts cited by a supervisor were flagged as forged; checks now follow the lineage.
- Orphaned tasks showed as running.
