# RI-01 — Autonomous multi-agent research and integration

The user requested a Codex-led team that autonomously reviews incoming research, completes remaining research using earlier findings, consults between agents, integrates the design, preserves the cumulative vision and independently reviews code. Visual recognition and the full multimodal suite are required.

**Setup status: PREPARED_NOT_STARTED.** Publishing the workspace is not an actual agent run.

Start with [workspace README](../orchestration/RI-01/README.md) and [the launch prompt](../orchestration/RI-01/START_CODEX.txt). The [master procedure](../orchestration/RI-01/MASTER_PROMPT.md) executes work, rather than handing assignments back to the user. The [task graph](../orchestration/RI-01/TASK_GRAPH.json) covers all R01–R15 lanes and explicit vision, audio/video and fusion tasks. The [role map](../orchestration/RI-01/ROLE_MAP.md) defines ten profiles plus the root supervisor.

## Changes to the workflow
For an explicitly launched RI-01 campaign only, the supervisor may create and coordinate actual native subagents and automatically advance eligible research tasks. This is the scoped exception to the older no-subagent/single-handback instructions. Existing safety, privacy, publication and application-ownership limits remain. Detailed scope: [AUTHORIZATION.md](../orchestration/RI-01/AUTHORIZATION.md).

The campaign reads pending PRs at their exact heads. At setup, R02 #15, R06 #14 and R08 #13 were incoming research publications; #9 was an R14 prompt, and #10/#16 published the R15 prompt/brief. These statuses must be refreshed. Do not re-run finished research merely because its PR has not merged, and do not call a prompt a completed study.

## Output
New versioned reports and state under `campaigns/RI-01/<run-id>/`, preserved originals, actual agent/consultation records, source-to-design use mapping, multimodal capability/evaluation matrix, one integrated architecture and implementation queue, independent reviews and a consolidated branch/PR. Routine documentation decisions are delegated; unresolved consequential choices are listed for one final operator review.

No new agent service, Discord integration, workflow trigger or background schedule is installed. No application implementation or device use is authorized by the campaign. The source migration, M0 and actual NIGHT-01/R1 remain separately tracked; their unverified state is not silently changed.
