# Haven Local Defense Factory (HDF)

Status: additive research/runtime-control work for issue #126. This is a first-party replacement for the **function** we wanted from Daybreak Defense Factory after the hosted Daybreak workspace returned access denied. It is not a reimplementation of Daybreak's service and does not claim parity with it.

## Purpose

Small local models should not receive a whole repository and then be trusted to discover, patch, and certify vulnerabilities by themselves. HDF keeps those responsibilities separated:

1. a scanner or deterministic analyzer produces a structured finding;
2. HDF normalizes the finding and binds it to exact repository source bytes and line evidence;
3. the host creates a narrow fix packet for one finding and an explicit file allowlist;
4. a model may propose a unified diff only within that contract;
5. HDF validates the proposal but **does not apply it**;
6. a separate host-owned runner applies the patch, executes tests/re-scan, and records an external receipt hash;
7. the finding lifecycle cannot close until a passing retest receipt has been recorded.

The 4B is therefore a bounded patch proposer, not its own scanner, authorization layer, or judge.

## Implemented in this package

- SARIF result normalization with stable finding IDs.
- Evidence references bound to full-file SHA-256 and exact line-excerpt SHA-256.
- Repository-relative path validation (no absolute paths, traversal, backslashes, or URI schemes).
- Host-owned fix packets with exact allowed files and response schema.
- Unified-diff gate that rejects creates/deletes, renames/copies, binary patches, duplicate sections, paths outside the allowlist, and oversized patches.
- Hash-chained append-only finding lifecycle ledger.
- State machine: `detected -> triaged -> fix_proposed -> fix_applied -> retested(pass) -> closed`; failed retests remain at `fix_applied`; suppression requires an explicit reason.
- No model-authored "pass", "verified", or "closed" field is trusted.

## Explicitly not implemented yet

- Scanner execution or repository crawling.
- Patch application.
- Test/re-scan command execution.
- Git branch/worktree creation.
- GitHub issue/PR automation.
- A background service, dashboard, queue, scheduler, or hosted workspace.
- Authentication/signing of receipts. The ledger is tamper-evident, not hostile-rewrite-proof.
- Symlink/TOCTOU hardening when source files are opened by a future filesystem adapter.
- Multi-location/dataflow SARIF findings. v1 fails closed unless one physical location is present.
- Any live tenant/network scan, exploit action, credential access, or deployment.

Those belong in later, separately reviewed host-runner work. In particular, command execution should reuse Haven's existing process/scope/checkpoint controls rather than create a second arbitrary-shell runtime.

## Model contract

The model receives a host-created packet containing:

- finding ID, rule, severity and title;
- exact evidence path, line range, full-file hash and excerpt hash;
- the exact allowed path set;
- a patch byte budget;
- an exact response shape: `finding_id`, `summary`, `patch`.

The response validator requires an exact finding-ID match and validates the patch against the host allowlist. A model cannot add extra status fields or self-assert that a fix passed.

## Author test receipt

Local standard-library-only run before publication:

- first pass: 11/11 tests PASS;
- mandatory second pass after hardening: 14/14 tests PASS;
- `py_compile`: PASS;
- malformed/random robustness: 40,000 inputs across path, patch and ledger parsers; 0 unhandled exceptions.

Pre-publication local SHA-256:

- `defense_factory.py`: `be4dc83be149ba90d5f58398a64aa8dd989f937e78b7a0acce081705e2f076d4`
- `test_defense_factory.py`: `94c0761def9f61e0a019d25f6cd610d18fa297055a6f62164df3c01f7156fcc8`

These hashes describe the local tested bytes. The published branch must be fetched and compared before treating them as an exact-head receipt.

## Next package if this core survives review

Build a host-owned runner that composes existing Haven controls instead of bypassing them:

- scanner adapter(s) -> SARIF/HDF findings;
- #130-style crash-safe checkpoint identity;
- #129/#131-style exact tool/effect/target scope;
- isolated worktree patch application;
- fixed allowlisted test/re-scan recipes rather than model-authored shell;
- receipt binding to repository commit, scanner version/ruleset, patch hash and executed check outputs;
- optional 4B fix proposal followed by deterministic retest and independent verifier/adjudicator;
- development evaluation in #133, reserve forbidden.

The success criterion is not "generate plausible fixes." It is: a finding with exact evidence can move to closed only after the host proves the authorized patch was applied and the prescribed retest passed.
