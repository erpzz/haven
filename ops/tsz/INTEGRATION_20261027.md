# Specialist handback

- Thread / owner / task: Codex TSZ continuation, PR #58; Claude is merge/deploy owner.
- Repository/base: `erpzz/haven`, `cc6cf1874254bcd1dbeea57f554eaf2a7ea08322`, owned branch `codex/tsz-passive-fleet-inventory-20261027`.
- Read inputs: root AGENTS/START_HERE/PRECEDENCE/CURRENT_STATUS, coordination/PROTOCOL, TSZ runbook/tests, morning runtime receipt; Claude interfaces at `67029918ae5f05c7a86ef005f718bb2956edcc10`.
- Owned output paths: `ops/tsz/`, `labs/tsz/`; no files in `labs/engineer/` changed.
- Actual work: input/state hardening, persistent admission accounting, existing-executor adapter, regression tests and real local integration check. No architecture-only substitute, model calls, production changes, merge or deployment.
- Dependencies received: committed Haven fleet observers, `Executor.call`, ledger and policy. Pending: external versioned real approvals, owner binding, Claude console adoption and remote executor transport contract.
- Requirements/contract IDs: preserve existing `tsz-fleet-v1`, `tsz-approved-nodes-v1`, `tsz-network-inventory-v1`, `tsz-worker-heartbeat-v1`; additive approval `revision`, persisted historical bindings, `tsz-reservations-v1`. No changes to historical REQ/AT/EX records.
- Publication classification: public-safe; synthetic identities, no host inventory, runtime databases, private paths, credentials or raw local observations.
- Review disposition: implementation available for Claude review; no self-approval.
- PR: https://github.com/erpzz/haven/pull/58 (draft, unmerged).

## Decisions

Consume the independent permission model. Intersect that authorization with an
explicit binding to an existing Haven enrollment. Use the existing authenticated
SSH/local observers and hand a single fixed read operation to the existing
executor. Keep the old batch planner inert; use durable reservations for any
handoff. Preserve uncertain execution capacity rather than retrying or declaring
it free. No competing enrollment workflow, executor, dashboard or listener.

## Evidence

Executed locally on macOS with Python 3.9.6:

| Command/check | Expected | Actual |
|---|---|---|
| Baseline `python3 -m unittest discover -s ops/tsz/tests -v` | full original suite | 42 PASS |
| Baseline `python3 -m unittest discover -s labs/tsz/tests -v` | full original suite | 9 PASS |
| Final `python3 -m unittest discover -s ops/tsz/tests -v` | full expanded suite | 79 PASS |
| Final `python3 -m unittest discover -s labs/tsz/tests -v` | full expanded suite | 12 PASS |
| `python3 -m ops.tsz.verify_haven --engineer-dir <export>/labs/engineer` | real API/receipt compatibility | PASS: synthetic grant, real current local telemetry, actual existing executor, succeeded ledger receipt, replay refused |
| `git diff --check` | no whitespace errors | PASS |

The integration check exports the pinned branch's engineer subtree into a
separate scratch directory; no merge, cherry-pick or edit of Claude's working
tree is required. All executor writes use a temporary fixture workspace and
scratch home. The receipt check verifies the existing ledger's succeeded record,
not merely a mocked return value. It does not assert a live approved two-node job.

SHA-256 of the actual integration source inputs:

| Claude file | SHA-256 |
|---|---|
| `labs/engineer/fleet.py` | `932104e0dc61708f8e5ea2a5235d8d17d08d5f944cf182e98ada2bb420bab2b7` |
| `labs/engineer/executor.py` | `916fb88d7d33d7443760e83a5643b51be15644b800e32e2564cfaf79ead06a48` |
| `labs/engineer/policy.py` | `3361ebbc3b914a1d03e641c2deeae51e1dbf34642a19fb0de3f8c37b29587337` |
| `labs/engineer/ledger.py` | `bd27ac869b0080a3b71b53d7b427452dd2202e849f47c40fb380b7c83b7f2f4d` |

Bugs fixed (the original suites passed, so these are review/regression findings):

- File permission/type validation used pathname stat followed by a separate
  open, permitting replacement between checks. Reads now validate the descriptor,
  bound bytes, reject links/FIFOs and reject changes during a read.
- Approval files lacked a read-size bound; JSON duplicate keys/non-finite values
  were accepted. Shared private I/O rejects all of them.
- Node ID binding disappeared on revocation. Historical binding is retained.
- Previously valid approval snapshots could be replayed after removal. Versioned
  producers now have rollback/conflict/downgrade checks; the executable adapter
  requires that versioned contract. Legacy inert usage is explicitly limited.
- Imported sightings were timestamped at import instead of source capture;
  delayed imports also could regress last-seen time. Both are corrected.
- Linux array-form FAILED/INCOMPLETE neighbor states were not filtered.
- Malformed heartbeat, role, expiry and job shapes could raise incidental type
  errors instead of rejecting eligibility. Persistent fleet state is validated.
- Staging a local worker was a read/check/write race between competing identities;
  staging and heartbeat emission now serialize on the private lock.
- Batch-only reservations vanished between calls. The adapter now accounts across
  calls/processes, rejects job replay, handles cancellation/expiry, and holds
  RUNNING/UNKNOWN capacity across crashes. Duplicate aliases cannot multiply
  host capacity. Tests exercise actual separate processes contending for one slot.
- Dispatch had no grant/capacity revalidation because it did not exist; the new
  handoff checks both before and after fresh observation and preserves executor
  policy/refusal/receipt semantics.
- Offline layer placement added a floating epsilon that could assign a layer
  exceeding reported capacity. Removed that upward rounding, validated malformed
  objects and rejected non-finite aggregate memory.

## Interface changes

The runbook documents concrete signatures and a caller sequence. Key points:

- `approved_view`: external decisions + existing Haven registry + private explicit
  bindings -> eligible TSZ view. Mapping inventory/engineering -> tools;
  inference -> inference; training receives no mapping.
- `collect`: existing `observe_local` / `observe_ssh` -> fresh heartbeat-shaped
  reports with a binding digest. No cached fleet fallback, enrollment or GPU claim.
- `Coordinator.reserve`: serialized capacity subtraction -> reservation token or
  NO_ELIGIBLE_CAPACITY. One shared local POSIX state directory; not distributed locking.
- `dispatch_local`: fresh admission -> existing caller-owned `Executor.call`.
  Fixed read-only diagnostic only. Remote targets produce an explicit error.
- `cancel`: only unstarted reservations; uncertain/started work requires owner
  receipt reconciliation. No cancellation signal is sent to existing processes.

## Acceptance

Executed: positive local handoff with actual Haven code; grant/role/binding
revocation; expiry during probe; current capacity loss; stale/future/malformed
reports; failed/refused/unknown outcomes; durable crash accounting; replay;
private file races; multiprocess inventory updates and scheduler contention;
malformed and boundary-value offline placement. SSH observer contract is tested
with doubles; no live SSH job or external producer acceptance ran. No independent
reviewer acceptance is claimed.

## Risks and open questions

Integration conflicts are semantic, with no owned file overlap: Claude's console
uses its own enrollment routes and `runtime.make_executor` is local. Those paths
must adopt TSZ admission and the shared lock. The permission producer must accept
the additive monotonically increasing revision contract. Existing inference
federation cannot receive arbitrary engineering tool calls. Treat this as a
transport integration blocker, not permission to build another executor.

Resource reservations do not enforce OS quotas or account for non-TSZ CPU work.
Only a depth-limited, output-capped read diagnostic is admitted; no general job
runner is claimed. Current telemetry is advisory and does not attest hardware.
The owner must bind a local enrollment on the correct host. Remote Mac memory
and all GPU scheduling remain unavailable. Unknown reservations and tombstone
archival need coordinated recovery; deleting state defeats replay protection.
No daemon, paid service, download or model cost was introduced.

## Next package

Claude reviews the PR, wires the console/runtime to these interfaces and the
shared lock, and coordinates a real versioned approval/binding with the separate
permission producer. Run the same bounded local diagnostic with that real grant.
For a remote job, first supply the existing SSH federation's executor handoff and
receipt/cancellation contract; then validate a single approved remote node without
loading models. Stop before merge/deploy until Claude explicitly coordinates it.
