# labs/hermes: Hermes operates Haven

This lab is an MCP server, `haven`, that gives the Hermes agent one tool per Haven operation. It is a thin facade over Haven's existing controllers, not a new one:

- `labs/engineer` remains the only fleet controller.
- The Model Lab remains the only GPU owner, reached through `labctl` over ssh, so its token never leaves Slink.

The server uses only the standard library and runs with system `python3`. It builds on PR #105's tool-registry pattern; [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) explains what changed and why.

## Tools

| Kind | Tools | What happens |
|---|---|---|
| Read (`readOnlyHint`) | `haven_status`, `haven_gpu`, `haven_models`, `haven_sentinel`, `haven_brief`, `haven_fleet`, `haven_jobs`, `haven_lab_job`, `haven_tasks`, `haven_approvals`, `haven_receipts`, `haven_check_answer`, `haven_tools` | Answers from records or a live read-only probe |
| Change | `haven_model_use`, `haven_model_unload`, `haven_strata_connect`, `haven_job_submit`, `haven_job_cancel`, `haven_task_start`, `haven_task_cancel`, admitted `skill_<name>` | The owner approves each call in Hermes, and each call gets a signed receipt |
| Create | `haven_tool_propose`, `haven_tool_request_admission` | Writes a candidate tool and tests it in the OS sandbox. The tool runs only after the owner admits it on held-out cases |

The owner keeps these actions; none is exposed as a tool:
- deciding approvals
- fleet enrollment and scope
- Sentinel baselines
- GPU training windows
- model downloads and installs
- anything needing sudo or systemctl

## Safety model

**1. Hermes asks the owner first.** Hermes is configured with `trust: untrusted`, so it asks before every tool that is not annotated read-only. That prompt goes straight to the owner: Hermes's smart-approval model never answers it, and it fails closed in cron and `-q` runs.

**2. Launch mode.** `--mode observe` hides change tools entirely. `--allow-strata` is a separate launch grant. No tool can change either.

**3. Receipts.** Every change is a hash-chained, HMAC-signed receipt in an engineer task ledger, so it shows in the Haven console:
- it moves through proposed, authorized, executed, then succeeded, failed or unknown
- it is marked refused instead when it was blocked before acting
- a timeout is recorded as `unknown`, never as success

**4. Guards from the controllers themselves:**
- a model load is refused while any non-Lab process holds the GPU, and the Lab's own lease refuses too
- the scheduler places CPU jobs only
- jobs never run on the Mac (`local`) while its compute is off
- engineer tasks queue their own risky steps for the owner
- tasks can only use agents listed in the owner's `~/.config/haven-engineer/hermes.json` `task_agents`

## Run

```bash
cd labs/hermes
python3 -m unittest discover -s tests     # 26 tests, stdlib only, fake Slink + temp engineer state
python3 scripts/smoke.py                  # offline MCP smoke
python3 scripts/smoke.py --live           # spawns the server in observe mode; read-only calls to Slink
scripts/install.sh <commit>               # release + Hermes config + skill (see the script header)
hermes mcp test haven
```

**Owner settings** (private, optional) go in `~/.config/haven-engineer/hermes.json`:
- `task_agents`: engineer agent ids that `haven_task_start` may use (default: none)
- `allow_local_jobs`: set it when the Mac takes jobs again

## Layout

- `haven_hermes/registry.py`: tool specs, recursive validation, effect classes, persisted rate limits, audit
- `haven_hermes/receipts.py`: change receipts in a lazily created engineer task session
- `haven_hermes/mcp_stdio.py`: stdlib MCP stdio loop (annotations, `tools/list_changed`)
- `haven_hermes/backends.py`: ssh to Slink with quoted fixed argv
- `haven_hermes/slink_probe.py`: read-only probe sent over ssh stdin
- `haven_hermes/tools/{observe,operate,forge}.py`: the tools
- `haven_hermes/task_launcher.py`: detached runner for Hermes-started engineer tasks
- `skill/haven-operator/SKILL.md`: the Hermes skill with the operating rules
- `eval/`: ops scenarios that measure whether Qwythos actually calls these tools
