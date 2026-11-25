# Checkpoint / interruption recovery prototype

Workstream: #126. Base `53387e74a0ad90786ac3ea16753c8ad99142e9df`. Author: Astra (ChatGPT), 2026-11-25. Review-only; no self-merge.

Implementation: `checkpoint_journal.py`. Upstream audit: `CHECKPOINT_GAP_ANALYSIS.md`.

## Recovery contract

The journal is append-only JSONL with a SHA-256 event chain and an immutable `manifest_sha256` on every event.

A strict run records:

`run_started → unit_started → model/tool operation boundaries → unit_completed|unit_failed → run_completed`

A process restart appends `run_resumed`. Attempt N+1 for an incomplete unit is legal only after such a new recovery epoch.

Recovery is deliberately **unit-level**, not opaque conversation restoration:

- completed units are skipped;
- a pending model request is safe to retry;
- an interrupted tool dispatch is automatically retryable only when the host explicitly marked that tool replay-safe;
- if an incomplete unit ever dispatched a non-replay-safe tool, both the resume planner and the journal transition gate block automatic restart;
- repeated crash/retry loops can be capped with `max_attempts`;
- `unit_failed` is terminal in this prototype.

## Crash integrity

- A final line without a newline is treated as an uncommitted/torn tail. The next writer truncates only that tail before appending.
- A malformed **committed** line blocks recovery.
- Duplicate JSON keys, sequence gaps, event-hash changes, hash-chain changes, run/manifest changes and invalid state transitions block.
- File writes flush and `fsync()` by default.
- POSIX `flock` plus an in-process lock serializes cooperative writers on macOS/Linux.

The hash chain is an integrity signal, **not authentication** against an attacker who can rewrite the whole file.

## Privacy

Journal events contain identifiers, replay classification, counters and hashes only. The append API intentionally does **not** accept arbitrary raw payloads. It accepts either the all-zero sentinel or an already-approved 64-hex content hash.

Do not turn private low-entropy values such as hostnames, account identifiers or target names into unsalted hashes merely to call them redacted.

## Author test evidence

Local Linux semantic suite after mandatory second-pass hardening: **18/18 PASS**.

Coverage includes:

- complete unit + resume state;
- torn-tail detection and repair;
- committed corruption refusal;
- duplicate JSON-key refusal;
- event/hash-chain mutation detection;
- immutable run-manifest mismatch;
- zero/unbound manifest refusal;
- raw-payload API refusal;
- interrupted model request classified retryable;
- uncertain replay-safe tool classified retryable;
- non-replay-safe incomplete unit blocked by both planner and transition gate;
- explicit resume epoch required before attempt N+1;
- retry-attempt cap;
- operation start/commit pairing;
- active unit prevents run completion;
- no events after run completion;
- 20-thread append sequencing without duplicate/gapped sequence numbers.

A 20,000-input random-byte parser fuzz probe produced **0 unhandled exceptions**.

Second-pass changes before publication:

1. attempt N+1 initially lacked a trustworthy process/recovery boundary; added explicit `run_resumed` epochs;
2. the planner alone initially blocked non-replay-safe recovery; the journal transition validator now independently refuses such restart;
3. manifest hash can no longer be the all-zero sentinel;
4. the initial payload API accepted raw objects and hashed them, which could leak low-entropy private values through offline guessing; raw payload input was removed.

## Integration order

For strict small-model/Hermes work:

`model/process admission → tool-surface/scope admission → checkpoint unit start → model request → scoped tool dispatches → verified result artifact → unit completion`.

The immutable run manifest should bind the exact model/admission receipt, executable/revision, tool policy, code head, dataset/export and question-set identity. Exact fields remain an integration-owner decision.

## Not executed / not qualified

- exact final-head clean-checkout execution;
- wiring into `h2h_run.py`, Haven Cyber eval, Hermes hooks or investigator runner;
- real process kill/power-loss tests on macOS;
- recovery while an actual local model server is hung;
- parent-directory fsync on first journal creation;
- Windows multiprocess locking;
- NFS/network filesystem semantics;
- rotation/compaction after the 64 MiB journal bound;
- authenticated/MAC-signed journal receipts;
- independent reviewer qualification.
