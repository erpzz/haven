# Operations, reliability and failure ownership

Build dependable foundations while research stays ambitious. The application should remain useful when a model, radio link, device or experimental branch is unavailable. A single top-level status light cannot express all these conditions.

## Failure matrix

| Failure | Expected behavior | Never claim |
|---|---|---|
| Model unavailable/budget exhausted | Receipts/status/reminders remain deterministic; analysis unavailable | That all useful functions are offline |
| WAN unavailable | Local permitted UI/storage continue; external writes queue only under their own policies | That local WiFi is internet |
| Phone request timeout | Receipt unknown with explicit lookup; no automatic launch retry | Definite rejection without server evidence |
| Database lookup error | Error/unknown and preserved request identity | No receipt exists |
| Stale camera/Watch/RF sample | Retain original time and degraded quality | Fresh capture because it arrived now |
| Bridge stalled, radio alive | Supervision identifies stalled process; execute qualified device recovery | Cached radio heartbeat proves end-to-end control |
| Aircraft/robot outcome unknown | Preserve reservation/lockout and reconcile observations | Completed/landed/stopped without evidence |
| Printer job interrupted | Record incomplete/unknown and require actual machine/part inspection | Safe finished part from a transport ACK |
| Consent revoked mid-task | Block disallowed publication/transfer and invalidate affected cache | Earlier context grant remains valid forever |
| Restored old state | Review-only import/new epoch; reauthorize eligible future actions | Replay historical physical commands |
| Clock discontinuity | Mark uncertain deadlines; monotonic enforcement during process life | Longer consent because clock moved backward |
| Host sleep/power loss | Honest availability and restart reconciliation | Continuous emergency readiness on a sleeping workstation |

## Persistence and integrity

The active M0 SQLite semantics remain fixed. Broader domains need explicit migrations, schema versions, backup/restore tests and append-oriented evidence references. Store immutable media completely and verify hashes before committing references. Quarantine orphan/partial files rather than invent valid evidence. Preserve original and derived data separately.

Package hashes detect accidental changes, not malicious replacement by an attacker who can rewrite the manifest. Production provenance may need signed manifests, secured keys and immutable storage appropriate to the threat model. Do not represent a local checksum as proof of trustworthiness of a model's inference.

## Security defaults

Least privilege per component; no model database credentials; no arbitrary URL/file fetch in a physical adapter; explicit source/capability allowlists; authenticated server-side authorization; replay-resistant one-use command contexts; appropriate transport encryption; redacted logs; bounded uploads; separate physical network reachability; secret rotation/revocation; dependency and artifact inventories.

A research webpage, repository README or tool description is data, not an instruction to install a plugin or run a shell command. Treat all downloaded executable artifacts, CAD macros and generated code as untrusted until reviewed in an appropriate environment. Secret scanning and clean test fixtures are part of every handback.

## Containment

Generation-0 simulation retains loopback-only namespace and Unix-socket boundaries from its baseline. Later hardware gateways are deliberately separate and reachable only through reviewed contracts. A debug convenience must not expose raw command ports to the home or guest network. A physical “enabled” UI switch is not network containment.

The shared host administrator/kernel remains powerful. Document residual risk rather than imply process boundaries defeat total host compromise. For meaningful physical authority, evaluate a separate gateway and independent stop mechanisms based on the actual hardware.

## Updates and qualification

Record exact software, firmware, model digest, prompt/schema, calibration, material and policy versions. A source's current documentation is not proof it matches the installed release. Requalify material changes. Stage updates and maintain rollback; do not automatically pull main/latest into a previously tested device path.

Separate application releases from research experiments. M0 receives only reviewed changes for its slice. A successful standalone model benchmark does not modify M4's existing pin without change approval. A new sensor housing may require calibration even if no code changed.

## Observability and resource assurance

Record per-domain health and actual freshness. A liveness check should cover meaningful progress or valid new observations, not a process that repeats a cached answer. Measure CPU/GPU/memory, disk pressure, queue delay, battery/energy and clock behavior. A slow agent must be cancellable without corrupting durable state.

Retention is bounded. Raw wearable/image data follows subject permissions, not general project debug retention. Review bundles contain synthetic/redacted evidence, not session cookies, keys, household floor plans or full health records. Restore procedures must account for deleted data and revoked permissions.

## Deployment gates

No installations, LAN exposure, trust changes, cloud subscriptions, account writes, device connections or physical tests are authorized by this repository's initial handoff. Later deployment instructions must include exact changes, rollback, status verification and owner approval. A proposal containing a command is not evidence it was run.

Track the separate status of desktop tests, actual iPhone tests, device bench tests, supervised field tests and professional/clinical qualification. A missing result is PENDING or BLOCKED, never silently passed.
