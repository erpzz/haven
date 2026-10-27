# Trusted Slink Zone — Haven integration runbook

**2026-10-27 / draft PR #58:** implementation and local integration verified; not
deployed. Claude remains the sole merge/deploy owner. Preserve active inference,
GPU experiments and other agents' worktrees. This branch adds TSZ components to
Haven's existing engineering system; it does not add an executor or dashboard.

## What works

- `fleet.py`: passive, explicitly scoped neighbor-cache discovery and private
  network-inventory import. Sightings are always unverified candidates.
- `sync-approved`: replacement snapshots from the owner's separate permission
  model. TSZ does not issue approvals or run an attestation workflow.
- `worker_runtime.py`: owner-invoked local telemetry and an inert batch planner.
- `haven_adapter.py`: intersects external approvals with explicitly bound,
  already enrolled Haven nodes; uses the existing local/SSH fleet observers;
  maintains persistent resource reservations; hands one fixed read-only
  diagnostic to the caller's existing Haven `Executor.call`.
- `labs/tsz/placement.py`: offline sharding feasibility estimates only.

The initial vertical slice accepts only `list_dir` with `path="."`, `depth=1`,
role `inventory` or `engineering`, one CPU accounting slot and 16–256 MiB of
memory accounting. It does not grant shell execution, writes, training,
inference, model loading or service management. Resource accounting is admission
control, **not an OS CPU/RAM quota**. CPU telemetry is logical core count, not a
measurement of idle cores. Existing non-TSZ CPU activity can compete with jobs.

## Verify the exact checkout

```sh
python3 -m unittest discover -s ops/tsz/tests -v
python3 -m unittest discover -s labs/tsz/tests -v
```

Executed on this implementation: **79 ops tests, 12 placement tests, all PASS**.
Baseline PR58 `cc6cf1874254bcd1dbeea57f554eaf2a7ea08322` passed 42 and 9;
there were no baseline test failures. Added regression tests cover bugs found
in review, including concurrency, revocation, stale reports and malformed input.

To verify the handoff against an exported copy of Claude's implementation:

```sh
python3 -m ops.tsz.verify_haven --engineer-dir /path/to/export/labs/engineer
```

This executed successfully against branch `claude/agentic-workspace-20261027`,
commit `67029918ae5f05c7a86ef005f718bb2956edcc10`. It uses **synthetic approval
and binding fixtures**, real current local telemetry, and the real existing
Haven executor/receipt ledger in a temporary workspace. It makes no model calls
or SSH connections, and does not modify the supplied engineer source tree.
It is not acceptance of a real external trust export or a two-host deployment.

## Discovery and external approvals

```sh
python3 ops/tsz/fleet.py discover --interface en0
python3 ops/tsz/fleet.py discover-import --file /private/router-inventory.json --interface home-lan
python3 ops/tsz/fleet.py inventory
python3 ops/tsz/fleet.py sync-approved --file /private/approved-nodes.json
```

Replace the example interfaces/paths with the intended private inputs. Discovery
reads existing caches only; import makes no probes. An inventory export has
`schema: tsz-network-inventory-v1`, `source`, `observed_at` epoch seconds (at most
one hour old, never future), and up to 2,000 `devices` with `address`, `mac`,
`interface`. Source capture times are preserved when importing sightings.

Approved-node exports have `schema: tsz-approved-nodes-v1`, `expires_at` epoch
seconds (future, no more than 24 hours), `revision` (monotonically increasing
nonnegative integer from the existing permission producer), and `nodes` entries
with `node_id`, `candidate_id`, `roles`. Roles remain
`inventory/inference/engineering/training`. Missing nodes revoke future work.
Node-to-candidate bindings are retained after revocation to prohibit silent
reuse of a node ID for a different candidate.

`revision` is an additive producer contract. Exact retries of the same revision
are accepted; older revisions, conflicting content at the same revision, and
removal of the revision after adoption are refused. Legacy exports without a
revision remain usable by the old inert planner; **the executor adapter refuses
unversioned approvals**. The existing permission producer must supply this
ordering field before production integration. Persist the coordinator state;
deleting it also deletes revision history and replay protection.

All JSON inputs must be owner-owned regular mode-0600 files, with one hard link,
no symlinks, at most 1 MiB, unique JSON keys and finite values. State directories
must be owner-owned mode 0700. Use owner-controlled parent directories. Reads
validate the opened file descriptor, and writes replace atomically after fsync.
Cooperative writers must use the same `.fleet.lock`; do not unlink that lock.

## Existing Haven interfaces

The adapter consumes the existing `labs/engineer/fleet.py` registry shape:
`{"nodes": [{"name", "kind", "roles", "trust", ...}]}`. It neither calls `enroll`
nor overwrites Haven's registry. A separate private binding map, maintained by
the owner/integration configuration, associates an external approved ID with an
existing Haven enrollment. A synthetic local example is:

```json
{
  "example-node": {
    "candidate_id": "neighbor-aaaaaaaaaaaaaaaaaaaaaaaa",
    "haven_name": "example-local",
    "kind": "local"
  }
}
```

For `kind: ssh`, also bind the exact existing `ssh` alias and `host_fingerprint`.
Aliases must be simple configured SSH names, never addresses learned from ARP
or arbitrary SSH options. The registry must carry `trust: OWNER_SSH`; the adapter
calls Haven's `observe_ssh(node)`, retaining its BatchMode/StrictHostKeyChecking
and pinned-key verification. Local nodes require `trust: LOCAL_HOST` and an
explicit host-local binding. Duplicate local hosts or SSH fingerprints cannot
multiply schedulable capacity. SSH aliases/pins remain private.

Role mapping is explicit: TSZ `inventory` and `engineering` require Haven
`tools`; `inference` requires Haven `inference`. No mapping admits training.
The telemetry adapter never asserts inference readiness or free GPU memory.
Remote Linux memory uses Haven's MemAvailable observation; the local Mac uses
TSZ's conservative free+speculative estimate. Remote Mac capacity is unavailable
until a conservative authenticated memory probe is integrated.

Integration call sequence, from the trusted Haven runtime (not model-authored
arguments), using a caller-created executor with its existing scope and ledger:

```python
from pathlib import Path
from ops.tsz import fleet as tsz_fleet, private_io, haven_adapter

state_dir = Path("/private/tsz")
registry_path = Path("/private/haven-fleet.json")
bindings_path = Path("/private/tsz-bindings.json")
coordinator = haven_adapter.Coordinator(
    state_dir,
    registry=lambda: private_io.read_json(registry_path),
    bindings=lambda: private_io.read_json(bindings_path),
)
# Synchronize the external approval export with fleet.py sync-approved first.
# Haven registry/binding updates must use this same lock as approval updates.
with tsz_fleet.fleet_lock(state_dir):
    reports = haven_adapter.collect(
        tsz_fleet.read_state(state_dir),
        private_io.read_json(registry_path),
        private_io.read_json(bindings_path),
        haven_fleet_module,  # existing labs/engineer/fleet.py module
    )
reservation = coordinator.reserve({
    "id": "unique-owner-job-id", "role": "inventory",
    "cpu_cores": 1, "memory_mib": 16,
    "tool": "list_dir", "args": {"path": ".", "depth": 1},
}, reports)
if reservation["status"] == "RESERVED":
    result = coordinator.dispatch_local(
        reservation["job"]["id"], reservation["token"],
        existing_executor, haven_fleet_module,
    )
```

The caller must supply the executor belonging to that local node's approved
workspace; TSZ does not construct scopes, override policy or select a workspace.
Use fresh provider functions, not cached registry/binding snapshots. Do not
pass untrusted model-created telemetry into the admission API.

## Accounting, dispatch and recovery

All schedulers for this fleet must share one coordinator directory on a local
POSIX filesystem. Reservations survive process restarts and subtract from CPU
and memory capacity across calls. Fresh telemetry does not erase reservations;
subtracting reservations from measured available RAM is conservative and may
double-count running usage. This is not a multi-coordinator distributed lock.

Reservations expire after 1–60 seconds (default 30), clipped to approval and
telemetry expiry. Only unstarted reservations can be cancelled or expire.
Before dispatch, the adapter re-reads approval, roles and binding, probes the
chosen host again, then re-reads eligibility and checks expiry and remaining
capacity. It holds the coordinator lock through the fixed read call. Integration
callbacks must not re-enter the same coordinator while it holds that lock.

`RUNNING` is persisted before the executor call. A known terminal executor
receipt releases capacity; crashes, exceptions and unknown outcomes retain
capacity as `RUNNING`/`UNKNOWN`, even after TTL. Completed/cancelled job IDs remain
as replay tombstones. There is no automatic retry or forced cancellation of
running work. Reconcile unknown outcomes against the real executor ledger with
the integration owner before releasing accounting; no automatic recovery tool
is claimed here. Tombstone compaction is not implemented; the state size bound
will eventually require owner-coordinated archival rather than deleting replay
history. Never reset accounting merely because a worker stopped responding.

## Remaining integration gates

1. The external permission producer must provide a real private, versioned
   export and the owner must bind it to an existing Haven node. The successful
   integration check used synthetic grants; no real producer output was used.
2. Claude must adopt this adapter in the console/runtime entry points and make
   registry/binding writers participate in the coordinator lock. Current console
   enrollment and runtime launches do not automatically pass through TSZ.
3. Claude's branch has local `Executor.call`, but no remote engineering executor
   RPC. Remote telemetry can use its existing SSH observer; remote dispatch is
   deliberately refused, with no local fallback. The existing Model Lab
   inference federation socket is not a general engineering RPC. Add any remote
   handoff through the existing authenticated SSH federation under Claude's
   ownership; do not add an exposed service or a competing executor.
4. Live SSH dispatch, real approved-node acceptance, distributed cancellation,
   GPU/model placement and multi-host inference remain unverified/unsupported.
   Merge and deployment remain with Claude after review and coordination.

Detailed findings, exact source hashes and handback: [INTEGRATION_20261027.md](INTEGRATION_20261027.md).
