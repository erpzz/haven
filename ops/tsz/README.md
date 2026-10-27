# Trusted Slink Zone — Codex baton checkpoint

**Status (2026-10-27):** additive, unprivileged fleet prototype on branch codex/tsz-passive-fleet-inventory-20261027, draft PR #58. Not deployed to Slink or the Mac. No existing inference or Computer services changed.

The owner's external trust/attestation agent is authoritative. TSZ does not duplicate that verifier; the coordinator consumes its private approved-node export. Local network visibility is discovery only, not permission for remote installation.

## Integration (2026-10-27)

TSZ is the input layer for Haven's single fleet controller (`labs/engineer`). Discovery and the external
approved-node state stay here. Placement, reservations, dispatch, cancellation and receipts belong to
`labs/engineer/scheduler.py`, and remote transport belongs to `remote.py`. `labs/engineer/trust.py` reads
`inventory.json` read-only and never writes approvals. `worker_runtime.py heartbeat/plan-jobs` remains a library
and is not deployed. See `labs/engineer/ACCEPTANCE_TSZ_20261027.md`.

## Implemented

- fleet.py: scoped passive reads of existing Linux/macOS neighbor caches; records unverified candidates. The discover-import subcommand can also ingest owner-private router/management inventory exports through import_source.py, without network probes or automatic enrollment. Consumes owner-private upstream approved-node snapshots with identity and role validation, expiry and replacement semantics. Emits inert user-space preparation plans. CLI fleet operations serialize under an advisory file lock.
- worker_runtime.py: stages an owner-invoked local configuration only for an already approved node, then emits a private one-shot heartbeat with CPU cores, disk space and measured available RAM. Linux reads MemAvailable; macOS reads vm_stat and conservatively counts free and speculative pages. Neither platform fabricates GPU readiness.
- worker_runtime.py plan-jobs: deterministic proposals from already-collected private heartbeat files, an approved-node state and requested job records. Checks approval expiry, role permissions, report staleness, resource budgets. Returns PLANNED_ONLY or NO_ELIGIBLE_CAPACITY. Never contacts a host or runs a job.

## Operator CLI

From the branch checkout, run tests and then inspect passive discovery:

    python3 -m unittest discover -s ops/tsz/tests -v
    python3 ops/tsz/fleet.py discover --interface en0
    python3 ops/tsz/fleet.py inventory
    python3 ops/tsz/fleet.py discover-import --file /private/router-inventory.json --interface home-lan
    python3 ops/tsz/fleet.py plan

Replace en0 with the actual intended interface on your machine. Discovery reads only the OS neighbor cache and therefore does not enumerate all available devices.

Your separate verifier may export a private JSON snapshot with schema tsz-approved-nodes-v1, short-lived expires_at, and nodes entries containing node_id, candidate_id and roles from inventory/inference/engineering/training. The export must be a regular owner-owned mode-0600 file.

    python3 ops/tsz/fleet.py sync-approved --file /private/tsz-approved-nodes.json
    python3 ops/tsz/fleet.py plan

On an approved device, after your authorized management path has delivered its relevant private inventory state, run this explicitly as the device owner:

    python3 ops/tsz/worker_runtime.py stage-local --node-id mac-worker --fleet /private/inventory.json
    python3 ops/tsz/worker_runtime.py heartbeat

The default local heartbeat path is ~/.local/state/haven-tsz/worker/heartbeat.json. It is a one-shot local probe, not a background daemon or connected network worker. Reports can be transferred using existing authenticated management transport; this component does not implement transport.

A private jobs.json may contain: {"jobs": [{"id": "read-only-analysis", "role": "engineering", "cpu_cores": 1, "memory_mib": 128}]}

Once your coordinator has collected private heartbeat files as /private/heartbeats/<node_id>.json, run:

    python3 ops/tsz/worker_runtime.py plan-jobs --fleet /private/inventory.json --heartbeats-dir /private/heartbeats --jobs /private/jobs.json

Output is a plan only; nothing is executed on a remote system.

## Verification and next gates

Twenty-five worker-runtime and network-import tests passed locally on the committed source (byte-for-byte check performed). The earlier 17 tests for fleet.py are committed but have not yet been executed on this pushed branch. No live Slink/Mac deployment or true network sharding was attempted.

Next: run the whole suite on PR #58; add race and malformed-snapshot tests; integrate with Haven's existing enrolled SSH/Unix-domain worker registry; collect signed or otherwise authenticated heartbeats using that transport; run an owner-initiated bounded diagnostic job and verify expiry/rollback; then test Qwen/Liquid job routing and compare throughput. Preserve active GPU/model experiments.

Related sharding draft PR #56 is separate research; prior alternative attestation-dedicated PR #57 was closed, not merged. Follow root AGENTS.md: merge/deploy ownership remains with Claude's designated integrator.

Network inventory export schema: tsz-network-inventory-v1, source string, observed_at epoch seconds (not older than one hour), and devices list (max 2,000) of address, mac, interface. The file must be owner-owned mode 0600. Import never authorizes a device: the independent trust manager must still export approved-node decisions.
