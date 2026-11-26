# Cross-stage controller and replay guard

This is the third sequential Local Defense Factory package, stacked on the core (#180) and isolated apply/retest runner (#181).

## Why it exists

A hash-valid runner receipt is not enough on its own. Without a host-owned cross-stage contract, a receipt from one finding, patch, base commit, or retest policy could be presented while closing another finding.

The controller binds the lifecycle end to end and is deterministic: it executes no scanner, model, patch, test, Git command, network request, or deployment action.

## Workflow contract

`build_workflow_contract()` binds:

- finding ID;
- exact fix-packet SHA-256;
- exact patch SHA-256;
- exact base commit;
- canonical touched paths;
- exact host recipe-policy SHA-256;
- ordered host recipe IDs.

The contract is itself canonicalized and SHA-256 bound.

## Receipt verification

Before a ledger transition, `verify_run_receipt()`:

- requires the exact runner receipt schema;
- recomputes the receipt hash;
- checks finding / packet / base / patch / recipe-policy / touched-path bindings;
- validates every per-command receipt and numeric type;
- requires recipe order to be a prefix of the host policy;
- rejects empty receipts;
- rejects an incomplete receipt that stops after a successful recipe;
- recomputes `passed` from command exit/timeout state instead of trusting the field.

## Ledger advancement

`DefenseWorkflowController.record_proposal()` records the complete workflow binding with the pending fix proposal.

`record_run()` then verifies:

1. the finding is actually awaiting that proposal;
2. the latest proposal payload exactly matches the workflow contract;
3. the runner receipt has never been consumed anywhere in the ledger;
4. the receipt passes all cross-stage checks.

Only after those checks does it append `fix_applied` and `retested`. A passing run may close the finding; closure can also be deliberately deferred for another human/independent review gate. A failed run remains revisable through the core's explicit revised-proposal transition.

## Security and evidence limits

- SHA-256 chaining and binding are tamper-evident, not authenticated against a hostile actor who can rewrite all local state and recompute hashes.
- The controller proves consistency of host-provided artifacts; it does not prove scanner correctness, model quality, OS isolation, or that a repository commit is trustworthy.
- Recipes remain host-owned policy and execution remains in #181.
- Untrusted third-party repository execution remains under the existing secpatch disposable-runner contract rather than this package.
- No reserve data, training authority, deployment, live tenant/network action, or model promotion is introduced.

## Qualification

The branch workflow compiles and executes the core + runner + controller suite on Python 3.11 and 3.13. Exact-head CI is required before this package is considered repo-side qualified.

The next useful integration after this controller is not another generic scanner. It is an adapter/evaluation package that exercises the existing 4B against evidence-bound findings and routes accepted real-security-fix evaluation through Haven's existing secpatch lane.
