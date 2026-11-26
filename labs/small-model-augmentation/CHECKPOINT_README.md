# Checkpoint / interruption recovery prototype

Workstream: #126. Base `53387e74a0ad90786ac3ea16753c8ad99142e9df`. Author: Astra (ChatGPT), 2026-11-25. Review-only; no self-merge.

Implementation: `checkpoint_journal.py`. Upstream audit: `CHECKPOINT_GAP_ANALYSIS.md`.

## Recovery contract

The journal is append-only JSONL with a SHA-256 event chain and an immutable `manifest_sha256` on every event.

A strict run records:

`run_started → unit_started → model/tool operation boundaries → unit_completed|unit_failed → run_completed`

`Journal.open(resume=True)` appends `run_resumed`. Attempt N+1 for an incomplete unit is legal only after such a host-declared recovery epoch. A plain reopen does not create one. The journal does not prove that an old process is dead; the runner must establish exclusive ownership before declaring resume.

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

Local Linux semantic suite after mandatory second-pass hardening: **19/19 PASS**.

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
- explicit resume epoch required before attempt N+1; plain reopen does not create one;
- retry-attempt cap;
- operation start/commit pairing;
- active unit prevents run completion;
- no events after run completion;
- 20-thread append sequencing without duplicate/gapped sequence numbers.

A 20,000-input random-byte parser fuzz probe produced **0 unhandled exceptions**.

Clean GitHub Actions qualification was added on the current branch. Workflow run `45734464838` on Ubuntu/Python 3.11 compiled the recovery sources and passed **26/26 tests** in 0.656 s. In addition to the unit contract, that run executes real child processes and sends SIGKILL at six replay-safe model/tool boundaries, verifies completed-unit skip, blocks a non-replay-safe canary from replay, enforces the attempt cap, refuses a competing live owner, and proves the POSIX lease releases after owner death.

Second-pass changes before publication:

1. attempt N+1 initially lacked a trustworthy process/recovery boundary; added explicit `run_resumed` epochs;
2. the planner alone initially blocked non-replay-safe recovery; the journal transition validator now independently refuses such restart;
3. manifest hash can no longer be the all-zero sentinel;
4. the initial payload API accepted raw objects and hashed them, which could leak low-entropy private values through offline guessing; raw payload input was removed;
5. final-diff review found that merely reopening the file was being treated as proof of a new recovery process; resume is now an explicit host decision (`open(resume=True)`), with exclusive old-process ownership/death left as an integration requirement.

## Integration order

For strict small-model/Hermes work:

`model/process admission → tool-surface/scope admission → checkpoint unit start → model request → scoped tool dispatches → verified result artifact → unit completion`.

The immutable run manifest should bind the exact model/admission receipt, executable/revision, tool policy, code head, dataset/export and question-set identity. Exact fields remain an integration-owner decision.

## Not executed / not qualified

- wiring into `h2h_run.py`, Haven Cyber eval, Hermes hooks or investigator runner;
- macOS/APFS process-kill qualification, including filesystem durability and supported-Python `flock` behavior;
- recovery while an actual local model server is hung;
- parent-directory fsync on first journal creation;
- Windows multiprocess locking;
- NFS/network filesystem semantics;
- rotation/compaction after the 64 MiB journal bound;
- authenticated/MAC-signed journal receipts;
- independent reviewer qualification.
