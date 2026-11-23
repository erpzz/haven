# Current approved M0 context — derived from the conversation

**Provenance:** user pasted the local coding agent's M0 implementation/acceptance plan, then approved proceeding with review clarifications. This is a faithful requirements summary, not a copy of current source code or a test report. The original exact first assignment remains in the Generation-0 baseline.

## Prerequisites and environment

The previously approved command is `wsl --install -d Ubuntu-24.04 --no-launch`. The operator completes first-launch setup. Do not remove Kali. Verify Ubuntu 24.04, WSL 2, x86-64, Linux Python 3.12, venv, SQLite, space and local Linux filesystem. Separate approval applies to additional system packages/host changes. The current installation result is unknown here.

Preserve Downloads originals; inspect `~/projects/project-astra` before copying. Create a local Git baseline and project-local environment if absent, without publishing. Resolve only M0 dependencies, lock exact versions/artifact hashes and verify a clean installation. Windows Python is not silent substitution for the planned runtime.

## Accepted slice

FastAPI, Pydantic 2, Jinja2, one Uvicorn worker and Python SQLite. Only identity/session, incident, accepted event and schema-version data needed for this slice. Local operator initialization, Argon2id password hash, stable principal ID; server sessions and Secure/HttpOnly/SameSite cookies; bound CSRF, exact permitted Origin, authenticated ownership; reject unexpected fields.

`POST /api/requests`, authenticated receipt GET by request UUID, incident/timeline pages and read-only export. Body: schema version, request UUID, OUTSIDE_CHECK type, issue and expiry. Deduplication is persisted authenticated source + UUID; canonical normalized UTC payload hash excludes session tokens/formatting. Authenticate and validate CSRF/origin before processing. Within the transaction, look up accepted requests before freshness: same payload returns original receipt even after expiry; conflicting reuse rejects without rewriting accepted data.

New requests have positive validity <=60 seconds, reject expiry/issue age >60 seconds and future issue time >5 seconds. Use BEGIN IMMEDIATE, DELETE rollback journal, FULL synchronous, foreign keys and bounded waits. Configure required pragmas on every connection before transaction. Commit accepted event and incident association before successful HTTP reply. Database constraints enforce unique source/request key and a single active OUTSIDE_CHECK incident; new fresh IDs add provenance to the active incident.

Initialize schema1 transactionally, refuse unsupported versions without data reset. Responsive page always says SIMULATION — NO REAL AIRCRAFT. After a five-second uncertain transport timeout show Receipt unknown; retain request ID across refresh for explicit read-only lookup. No automatic queue/resubmission. A failed lookup is not an absent receipt. No incident-closing, model, mission, approval, aircraft, Watch or later-stage feature.

## Execution/evidence boundary

Real loopback Uvicorn subprocesses, isolated on-disk DBs and run IDs. T01 durable relationships/timeline/latency; T02 retries, suppressed responses, canonical equivalence and conflicts; T03 test-only barriers immediately before commit and after commit/before reply, actual process termination and restart; T04 authentication/CSRF/origin/expiry/identity/access rejection. Additional concurrency, reauthentication, read-only, migration/restart and database-error tests.

Loopback HTTPS uses test certificates trusted by test clients only; no Secure-cookie downgrade or disabled certificate verification. Test controls absent from normal entry points. Desktop browser mobile-width evidence stays labeled desktop. Separate approval for missing browser system dependencies. Stop test processes and verify listeners gone.

Retain commands/exits/UTC times/versions, effective SQLite settings, latency, redacted HTTP and rejection logs, crash points/termination evidence, counts/relationships, browser evidence and hashes. Export isolated successful fixture data only; exclude secrets and private keys. Complete review and accurate status with EXECUTED_PASS/FAIL/BLOCKED/PENDING_OPERATOR subtests. Do not claim iPhone acceptance from loopback success.

SQLite DELETE/FULL process-crash qualification is not a claim of whole-PC power-loss durability. Do not perform disruptive power-cut tests. Caddy/iPhone port8443/forward/firewall/trust setup remains an unexecuted proposal including `skip_install_trust` and rollback; no networking/trust changes through M0 automation.

## Stop

Stop for human review with changes, exact dependency lock, tests, redacted incident export and report. M1 has not been authorized by the cumulative starter. No remote deployment, equipment connection, new AI/simulator integration or external emergency adapter. The latest user report says implementation is underway; success is not yet evidenced.
