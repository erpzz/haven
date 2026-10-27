# Acceptance record: Trusted Slink Zone integration (2026-10-27)

Branch `claude/agentic-workspace-20261027`. It builds on `main` `e420f4a`, which holds #59, merges TSZ #58 at
`cc6cf18`, and includes one commit authored on Slink by a Haven agent. Raw task records, ledgers and transcripts
stay in the owner's private state; this file holds only sanitized outcomes. Every "observed" row was re-checked
outside the agent.

## Architecture decision

There is one fleet controller (Haven `labs/engineer`), and TSZ supplies its inputs. TSZ (`ops/tsz`) keeps
discovery and the import of the owner's external approval export. Haven keeps enrollment, scheduling, transport,
sandboxing and receipts. TSZ's `worker_runtime` heartbeat and plan-jobs code stays as a library, not a deployed
path. Codex's draft dispatcher (`haven_adapter.Coordinator`, uncommitted) was declined on #58 as a second
controller. The contract is posted on #58.

## Results

| # | Owner priority | Result | Evidence |
|---|---|---|---|
| 1 | Computer login, Haven console and engineering paths work, no resets | **met** | Computer (cptr 0.9.21, :8896): browser session authenticated as the owner account (admin); an unauthenticated API call gets 401; Codex, Qwen and Claude Code agents listed. Console (:8895): 43 prior tasks intact; 401 without the token; Fleet shows the Mac and Slink ONLINE. Engineer suite 25/25 before any change. No database or state was reset. |
| 2 | Review and integrate TSZ discovery and enrollment | **met** | #58 re-tested in a clean checkout (ops 42/42, labs 9/9) and merged. Review posted (the whole export is rejected when one approved node is not in the ARP cache; duplicate controller; two lock implementations). `trust.py` consumes TSZ approvals and is tested against TSZ's own `reconcile_approved`. Haven discovery now uses TSZ's parsers. Live trust export: **not present on this Mac**, so the gate runs in "enrollment only" mode and says so on every decision. |
| 3 | Real engineering task on Slink from the Mac, with receipts | **met** | Claude Code (Opus, subscription) ran on the Mac; all 24 tool calls ran on Slink under Landlock ABI 4 (96 ledger lines, chain verified on the Mac). Task: give Haven one discovery implementation. Along the way it found a **real TSZ bug**: iproute2 reports `state` as a list, so FAILED neighbors passed the filter (confirmed against Slink's real `ip -j neigh`). The commit came back as branch `slink/20261027T113540-a8a16d`. Independent re-run on the Mac: engineer and scheduler 41/41, TSZ 42 + 9. Merged. Wall time 180 s. |
| 4 | Durable user-space scheduling and lifecycle | **met** | `scheduler.py` + `worker.py`. Live on Slink, job `ci-slink-net-114010` (receipt `R-2bc7d949f8`) ran Haven's suites: 42/42, TSZ ops OK, labs OK, exit 0, landlock-abi4. Live crash recovery: the controller was killed mid-start, the next tick found the worker had no record, requeued the job, and it then succeeded. Tests: 17 for scheduler, trust and discovery (lifecycle, failure, cancel, trust revocation cancels running work, headroom, stale telemetry, lost runner gives an `unknown` receipt, at-most-once start, two processes sharing one ledger). |
| 5 | Real Codex engineering through Haven | **blocked** | The same task was sent to Codex through Haven at 11:34. The Codex CLI answered "You've hit your usage limit … try again at 4:03 PM". Nothing ran (0 receipts). The path is wired and its first step was exercised. |
| 6 | Morphogenesis: skill inheritance, local-model gains | **not started** | Not run this session. Related evidence: Liquid LFM2.5-8B-A1B on the same remote path made a wrong fix (`a - b` → `b - a`), "confirmed" it with a command that ran no tests, and said "now passes". The claim checker missed "passes"; that is fixed and has a regression test. A second LFM run emitted its tool call as text and stopped. |
| 7 | Liquid and Qwen benchmark on Slink's GPU | **deferred** | Slink's GPU stayed owned by `haven-paradigms-round2` (92–94% util). It was not touched. |

## Approval relay (remote owner decisions)

A run on Slink of `rm -r` in engineer mode asked for owner approval. The ask appeared in the Mac console with
`tool_host: slink` and was rejected there; Slink's receipt reads `refused`, `decided_by: owner`. The first
attempt surfaced a stale ask left by a killed process. Pending asks now carry the waiter's pid and host, and dead
waiters' asks are dropped.

## Bugs found by running for real, all fixed with tests or a live re-run

- Remote commits on `main` waited for an approval nobody could see. Fix: task branches, plus the approval relay.
- A bundle without HEAD gave an empty clone. Then a full-history bundle of the shared repo took more than 3
  minutes. Fix: `git archive` snapshot plus patch replay, about 1 s round trip.
- `Path("../..").name` gave an invalid workspace name.
- Nested Landlock crashed listing `/`, which broke every sandboxed test inside a sandboxed job on Linux.
- The `serve` and `submit` processes shared one ledger, and `serve` used a stale copy. It crashed, and could have
  forked the hash chain. Fix: re-read under the lock.
- The console checked existence before refusing credential paths (400 instead of 403).
- `serve` probed the fleet over SSH every tick even when idle.
- The claim regex missed "passes", "are passing" and "succeeded".
- One job command (mine) swallowed its test exit code. The receipt faithfully recorded exit 0; the job spec was
  wrong, not the scheduler.

## Not done (honest list)

- No external trust export exists on this Mac. TSZ approvals are tested, not exercised live. The owner's trust
  model needs to write `tsz-approved-nodes-v1`, and the owner needs to bind Slink (`fleet.py bind slink --tsz-node ID`).
- Codex engineering through Haven: the usage limit lifts at 16:03 local.
- Verified skills are not yet available on remote tool hosts. The runtime-invoked `run_tests` controller (E2:
  6/8 vs 3/8) runs only on the Mac.
- Live events from a remote executor reach the Mac console when the task finishes, not while it streams.
- The scheduler runs as a user process started by hand (no LaunchAgent). Node runners survive it.
- GPU placement, multi-node inference and sharding are out of scope while the GPU has another owner.
