# Checkpoint and interruption recovery gap analysis — 2026-11-25

Workstream: #126. Base main: `53387e74a0ad90786ac3ea16753c8ad99142e9df`.

The goal is not to preserve opaque model memory. For evaluation and strict small-model work, the safer recovery unit is a host-defined task/question: persist completed units, record operation boundaries, and restart an incomplete unit from trusted inputs only when replay is known safe.

## Exact source reviewed

PR #105 head `69f7ae3725b7a4a832a4ce17317d6351eb2a5293`:
- `labs/cyber/haven_cyber/eval/harness.py` blob `75726b368e81595fec3bdba2b89e496782d1fffd`.

PR #122 head `f701cd766e7068649c4722874a6ced1b2213fbdf`:
- `labs/purple-copilot-apm/eval/h2h_run.py` blob `7d07de7a51e7cde6c736f2fcf41d0d93eac2f1ef`;
- `labs/purple-investigator-security/local-runner.mjs` blob `a87ab2699c85beace7cbdeefcf7d6af779bc2058`;
- `labs/purple-investigator-security/runner.mjs` blob `c3b70c874fd74adca13aba9fa9ad0dd232706f1e`;
- `labs/purple-copilot-apm/tests/hermes_review.py` blob `e41d2b9b331fbc03b81769dc9a010fd2eb06c9c2`.

## Existing strengths

Both Python evaluation runners already append one JSON object per completed unit and skip completed keys on restart. The H2H runner deliberately gives each Hermes run a fresh `HERMES_HOME`, which is a good benchmark-isolation property and means recovery should restart an unfinished unit instead of reusing model/session memory.

The Purple investigator boundary is also a favorable recovery target: its tool path is host-dispatched and read-only, so integration can explicitly mark those reads replay-safe rather than guessing from model prose.

## Gaps

1. **A torn final JSONL row can break resume.** Both Python runners construct `done` by applying `json.loads` to every line in the existing results file. A process/power interruption during the final append can therefore turn a recoverable tail into a startup failure.

2. **Committed corruption is not distinguished from a torn tail.** Safe recovery should discard only an uncommitted final fragment. A malformed newline-terminated line in the middle or end must block rather than be silently skipped.

3. **The results file is not bound to an immutable run manifest.** H2H's completed key includes model/arm/rep/question id, but not the question text/hash, question-set version, export/dataset identity, Hermes binary/revision, plugin head, admission receipt or tool policy. Reusing an output path after one of those changes can mix experiments or incorrectly skip work. The cyber harness similarly rewrites `meta.json` on resume instead of proving the existing rows belong to the same run definition.

4. **Flush is not durable commit.** Both runners call `flush()` after rows but do not fsync the result file. The prototype journal fsyncs committed events by default; directory-entry durability on first creation is still an integration gap.

5. **There is no durable 'operation started' boundary.** If the process dies while waiting for a model response or immediately around a tool dispatch, the existing result row only says the unit never completed. That is enough to rerun a purely read-only unit, but it cannot distinguish 'tool definitely never ran' from 'tool may have run but its result was not committed.'

6. **Automatic restart needs replay semantics.** Restarting a whole incomplete unit repeats every earlier operation in that unit. That is safe for a model request and explicitly idempotent/read-only observations, but it is not generically safe for a write, external action, or unknown tool. The journal blocks automatic restart if an incomplete attempt ever dispatched a tool marked non-replay-safe, even when a result was recorded.

7. **A retry must prove a new recovery epoch.** The journal requires a `run_resumed` event before attempt N+1 can supersede an incomplete attempt N. This prevents a live process from accidentally opening overlapping attempts.

8. **Crash loops need a bound.** `resume_plan(max_attempts=...)` blocks repeated automatic retries once the host-defined limit is reached.

9. **Integrity is not authenticity.** The SHA-256 chain detects accidental/casual mutation, ordering errors and truncation but does not authenticate an attacker who can rewrite the whole journal. If that is in scope, receipts need a host-held signing/MAC key or external immutable storage.

10. **Checkpoint metadata can leak by hashing low-entropy secrets.** The journal API therefore does not accept arbitrary raw payloads. Callers may record zero or an already-approved opaque SHA-256 of a public/non-sensitive artifact. Do not hash private hostnames, account identifiers or similar low-entropy secrets merely to call them redacted.

## Proposed integration

For an H2H unit such as `model|arm|rep|question-id`:

1. Construct an immutable run manifest and SHA-256 it. It should bind at least code/head, question-set hash, dataset/export identity, model admission identity, relevant flags, tool-scope policy and executable/plugin provenance.
2. `unit_started`.
3. Before each model request: `model_request_started` (replay-safe).
4. After a complete response has been accepted: `model_response_committed`.
5. Immediately before dispatching any tool: `tool_dispatch_started` with an explicit host-derived `replay_safe` classification.
6. After its result is durably stored: `tool_result_committed`.
7. Durably append the result row/artifact, then `unit_completed` with the row/artifact hash if publishing that hash is safe.
8. On process restart, `run_resumed` is added. Completed units are skipped. Retryable incomplete units restart from trusted inputs as a new attempt; blocked units require operator disposition.

A model timeout/interruption with no tool dispatch is retryable. An interrupted replay-safe read is retryable. An incomplete unit that dispatched a non-replay-safe operation is not.

## Prototype limits

- Library prototype only; not wired into H2H, cyber eval, Hermes hooks or the local investigator.
- POSIX `flock` provides cross-process coordination on macOS/Linux. On platforms without `fcntl`, the current fallback is thread-only and must not be presented as multiprocess-safe.
- File contents are fsynced by default, but the parent directory is not fsynced on first creation.
- Journal size is bounded at 64 MiB and there is no rotation/compaction protocol yet.
- Filesystem/NFS semantics, abrupt power-loss behavior, Windows behavior and real Hermes interruption timing are not qualified here.
- A `unit_failed` event is terminal; policy-driven retry of explicit failures is deliberately not designed in this prototype.
