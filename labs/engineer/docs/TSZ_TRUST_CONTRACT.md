# TSZ trust contract: approved-node export → Haven admission

Status: **decided 2026-10-27 by the merge/deploy owner (Opus); not yet live.** No producer exists. Neither the Mac
nor Slink has `~/.config/haven-engineer/trust.json` or `~/.local/state/haven-tsz/`, so every Haven decision today
reads `source: enrollment`. Synthetic exports in tests are **not** evidence of live admission.

## Roles (one of each)

| Part | Owner | Does | Never does |
|---|---|---|---|
| Owner's trust model (separate repo/system) | owner | Decides which devices may do which work; writes the export | — |
| `ops/tsz/fleet.py sync-approved` | TSZ (Codex A for hardening) | Validates and imports the export into `inventory.json` | Issue, extend or infer approvals; dispatch work |
| `labs/engineer/trust.py` | Haven (Opus) | Reads `inventory.json` and decides per (node, role) at placement and while running | Write approvals; verify devices itself |
| `labs/engineer/scheduler.py` | Haven | The only scheduler and dispatcher; asks `trust.Gate` | — |

There is no second verifier, reservation system, dispatcher, attestation workflow or dashboard. A change that adds
one gets declined.

## Export file: `tsz-approved-nodes-v1`

The trust model writes one JSON file on the **controller host** (today the Mac, where `scheduler.py serve` runs).
It must be a regular file, owner-owned, mode 0600, and not a symlink. It is written atomically (temp file plus rename).

```json
{
  "schema": "tsz-approved-nodes-v1",
  "producer": "owner-trust-model",
  "revision": 42,
  "issued_at": 1793140000,
  "expires_at": 1793143600,
  "nodes": [
    {"node_id": "slink", "candidate_id": "neighbor-<24 hex>", "roles": ["engineering", "inference"],
     "ssh_host_key_sha256": "SHA256:..."}
  ]
}
```

| Field | Rule | Why |
|---|---|---|
| `producer` | required, `[A-Za-z0-9._:-]{1,80}`; constant for one trust model | revisions are only comparable within one producer |
| `revision` | **required**, integer ≥ 0, strictly greater than the last imported revision from this producer | stops a replayed or older export from re-granting a revoked node |
| `issued_at` | required, integer epoch seconds, ≤ now + 60 s of clock skew | freshness is measured from here |
| `expires_at` | required, `issued_at < expires_at ≤ issued_at + 86400`; **recommended ≤ issued_at + 3600** | bounds the lifetime of a grant when the producer goes silent |
| `nodes[].node_id` | TSZ id; unique | what Haven binds to |
| `nodes[].candidate_id` | must name a TSZ discovery candidate (unchanged from today) | ties the grant to an observed device |
| `nodes[].roles` | non-empty subset of `inventory`, `inference`, `engineering`, `training`; no repeats | — |
| `nodes[].ssh_host_key_sha256` | **required for any node Haven reaches over SSH**; same format as `fleet.json` `host_fingerprint` | binds the grant to the key Haven actually pins, not only to a MAC address that can be spoofed |

The export is a **snapshot**. A node missing from a newer revision is revoked. `"nodes": []` revokes every node.

## Import (`fleet.py sync-approved --file F`) — Codex A's scope

- Validate everything above. If anything fails, the whole export is rejected and the previous state stays.
- Revision handling:
  - Lower than the stored revision: reject as `stale`.
  - Equal with a different content digest: reject as `conflict`.
  - Equal with the same digest: idempotent no-op that does **not** refresh `imported_at`.
- On success, write to state:
  - `nodes` (as today, plus `ssh_host_key_sha256`)
  - `approval: {"producer", "revision", "issued_at", "expires_at", "digest", "imported_at"}`
  - an incremented `generation`
- Append one line to `<state>/import-receipts.jsonl` for every attempt, accepted or rejected: time, producer, revision, digest, outcome, reason. Rejections must be visible.
- Interface kept stable for `trust.py`:
  - `fleet.read_state(dir) -> dict` raises on any integrity failure.
  - The returned keys `nodes{id: {candidate_id, roles, approved_until}}`, `candidates{id: {addresses}}` and `generation` keep their names and meaning. New keys may be added.
- The trust model triggers the import after each write. No new timer or scheduler is added for it. A producer that goes silent is handled by freshness (below), not by polling.

## Admission (`trust.Gate.decide(node, role)`) — Opus's scope

All of the following must hold, otherwise the decision is a denial with the reason given:

| # | Check | Denial reason |
|---|---|---|
| 1 | Haven enrollment grants the role and the SSH node has a pinned host key (unchanged) | `Haven enrollment does not grant role …` / `node has no pinned host key` |
| 2 | `inventory.json` reads cleanly | `TSZ state unreadable: …` (fail closed, no fallback to enrollment) |
| 3 | `node.tsz_node_id` is set (owner-only `fleet.py bind`) | `node is not bound to a TSZ identity` |
| 4 | the bound id is in the current snapshot | `no current approval (absent or revoked)` |
| 5 | `now < expires_at` | `approval expired` |
| 6 | `now − approval.issued_at ≤ max_export_age_s` (from `trust.json`, default 3600) | `approval stale: producer silent since …` |
| 7 | the export's `ssh_host_key_sha256` equals the node's pinned `host_fingerprint` | `approval is for a different host key` |
| 8 | the TSZ role required by `ROLE_MAP` is granted | `approval does not grant TSZ role …` |
| 9 | the node's IP, if known, is among the candidate's observed addresses (unchanged) | `binding looks wrong` |

Each decision carries `producer`, `revision`, `issued_at`, `expires_at` and `generation`. The scheduler already
records the decision in each job receipt and re-checks running jobs. A denial of a running job cancels it, as the
2026-10-27 acceptance tests show.

## Expected behaviour

| Event | What happens | When |
|---|---|---|
| Grant | New revision lists the node | Admitted from the next placement after import |
| Expiry | `expires_at` passes | Denied at the next check; running work is cancelled |
| Revocation | New revision omits the node (or `nodes: []`) | Denied from the import onward; running work is cancelled. Worst-case latency is the producer's write interval |
| Stale input (older or replayed revision) | Import rejected, receipt line written | State unchanged; existing grants keep aging under rows 5–6 |
| Conflicting input (same revision, different content) | Import rejected | As above |
| Producer unavailable or silent | No import | Grants lapse at `min(expires_at, issued_at + max_export_age_s)`, so silence fails closed within an hour by default |
| State file corrupt or unreadable | Every TSZ decision denied | Immediate. No fallback to enrollment-only |
| `trust.json` absent | `source: enrollment`; every decision says so | Today's mode |

## What the owner's trust model must provide

1. A writer for the file above on the Mac. Path suggestion: `~/.config/haven-trust/approved-nodes.json` (0600, atomic rename). It runs `python3 ops/tsz/fleet.py sync-approved --file <path>` after each write.
2. A stable `producer` name and a persistent revision counter that never goes backwards.
3. For Slink:
   - its TSZ `node_id`
   - the `candidate_id` that TSZ discovery assigns it (`ops/tsz/fleet.py discover` then `inventory` on the Mac lists candidates)
   - its SSH host key fingerprint, which must match Haven's `fleet.json` pin
   - roles `engineering` and `inference`
4. A re-issue interval shorter than `max_export_age_s`, for example every 15 minutes with a 1-hour expiry.
5. Owner-only setup steps, which agents must not perform:
   - write `~/.config/haven-engineer/trust.json` = `{"source": "tsz", "tsz_state_dir": "~/.local/state/haven-tsz", "max_export_age_s": 3600}`
   - run `python3 labs/engineer/fleet.py bind slink --tsz-node <node_id>`

## Live acceptance (only with a real export)

These count as evidence only when the export came from the owner's trust model.

1. With the real export imported, a `tools` job on Slink is admitted, and its receipt shows `source: tsz`, the producer and the revision.
2. The producer issues a revision without Slink. The next placement is denied, and a running job is cancelled with that reason.
3. Re-importing the older file is rejected as `stale`, with a receipt line.
4. With the producer stopped, admission lapses at `issued_at + max_export_age_s`.

Restore by re-issuing the grant. Rollback is to delete `trust.json`, which returns Haven to enrollment-only mode.
