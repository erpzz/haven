# Engineering backlog (dependency-ordered)

Each item names what done looks like. Nothing here is implemented unless stated.

## Product (Stream A)

1. **Deployments.** `deploy` tool backed by a `deploy.json` manifest per workspace
   (`build`, `deploy`, `health`, `rollback` commands, `target` names). Policy already routes
   `deploy` to ask/allow by `deploy_targets`. Done = a harmless sample service deployed to a
   staging port on Slink, health-checked, rolled back, all receipted.
2. **Remote executor.** Run `mcp_server.py` on an enrolled node over SSH stdio (no key handed to a
   model), so tools execute on Slink/ThinkPad. Requires the repo on the node (bundle transfer as
   today). Done = a local-model task whose tools run on Slink, visible in the console fleet view.
3. **Slink inference for agents.** Owner-approved GPU lease + SSH-tunnelled endpoint for the
   Model Lab's Qwen; add to `agents.json`. Done = same E1 tasks run with Slink inference.
4. **Two-person isolation.** Per-principal state dirs, console tokens and cptr instances under
   separate OS users; tasks, ledgers and approvals never shared. Done = tests that one principal's
   console cannot list or approve the other's tasks.
5. **Console polish.** Live token streaming; a terminal link into cptr per workspace; per-node
   placement controls (pause/assign) backed by real scheduling (#2).
6. **cptr settings for Haven.** Auto-approve the `haven` MCP server once a Haven mode is chosen
   (avoid double approval); disable the rich Markdown editor for repository docs.
7. **Codex lane.** Re-run the engineering task when the plan allowance resets.

## Swarm (Stream B)

8. **Scheduler.** Place child agents by role, free memory and GPU lease state from `fleet.observe`.
   Done = a parent spawns two children on two nodes, with a measured comparison to one node.
9. **Bulk enrollment.** `fleet.py enroll` from an owner-signed list of SSH aliases + fingerprints.

## Morphogenesis (Stream C)

10. **Make inherited skills get used.** Qwen ignored the offered `skill_run_tests` tool 4/4 times.
    Compare: tool description wording, putting skills first, the E2 controller (runtime invokes the
    skill), and a router that maps task text to skills deterministically.
11. **Automatic limitation mining.** Scan ledgers for repeated failed command patterns and draft
    briefs; the owner or Opus picks which to commission.
12. **Second skill family** (e.g. `localize_failure`: map a failing test to the suspect function)
    with its own held-out set, to test whether VEI generalizes beyond test running.
13. **Premature-finish guard.** Tested in the E2 rerun: not supported. It made LFM2.5 act more, not succeed more.
14. **Reasoning-budget exhaustion.** Recovery (reasoning tail back, thinking off one turn) tested in E5: the mechanism works (39/39 vs 23/39 non-empty followups, no run ended on empty replies) but the success gain, 4-0, is inconclusive. Next: make it the default and test it with the outcome as the primary, more units, and an arm that separates the reasoning carry-over from turning thinking off.
15. **Harder tasks for Qwen.** Done in E5: on tasks Qwen solves 3/18 unaided, the test-driven controller is supported (12/18, 9-0, p=0.002). Next: make the controller the default engineer mode for small local models.
15a. **Unattended approvals in bench runs.** One E5 run waited 1800 s on an approval nobody could answer and overran its 1200 s limit, because the loop checks time only between steps. Bench runs should deny escalations at once, and the time limit should bound approval waits.

## Inference (Stream D)

16. **E4 task throughput on Slink** once the GPU lease is free: LFM2.5-8B-A1B vs Qwen3.5-4B on
    the E1 tasks, end-to-end wall time and success, not tokens/s.
17. **MLX on the Mac** for LFM/Qwen vs llama.cpp Metal on the same tasks.
