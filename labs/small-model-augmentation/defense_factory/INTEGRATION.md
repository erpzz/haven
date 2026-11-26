# Landed-commit verification and closure

This is the fourth sequential Local Defense Factory package, stacked on #182 / #181 / #180.

## Why this exists

A patch that passes in a disposable worktree is only a **verified candidate**. It is not proof that the authoritative repository contains the fix.

This package is the separate closure gate.

## Verification algorithm

`verify_landed_fix()` requires:

- the exact workflow contract from #182;
- the exact validated fix from #180;
- the same host-owned recipe policy used by #181/#182;
- an exact integration commit.

It then:

1. proves the integration commit descends from the workflow base commit;
2. creates a detached expected worktree at the exact base;
3. reapplies the validated patch there;
4. creates a detached landed worktree at the exact integration commit;
5. requires every touched path to be an existing non-symlink regular file;
6. compares every touched file byte-for-byte by SHA-256 between the expected patched tree and integration commit;
7. allows unrelated changes outside the touched-file set;
8. reruns the exact ordered host recipe policy on the landed commit;
9. emits a canonical integration receipt bound to finding, workflow contract, fix packet, patch, base, integration commit, recipe policy, touched paths, touched-file hashes and recipe results.

## Closure revalidation

`close_verified_finding()` does not trust even a self-consistent stored receipt by itself.

Before appending `closed`, it:

- reconstructs and verifies the finding ledger chain/state;
- verifies the integration receipt hash and all workflow bindings;
- reopens the exact integration commit through Git;
- independently re-hashes each touched blob and compares it to the receipt;
- verifies each touched Git entry is a regular file;
- rechecks that the integration commit descends from the workflow base;
- requires every prescribed recipe receipt to be present and passing;
- requires the finding to already be in `verified` state from the matching workflow contract.

The resulting ledger closure stores the integration receipt SHA-256 and exact integration commit, which are the fields required by the #180 core lifecycle.

## Deliberate strictness

For a touched file, the integration commit must byte-match the file produced by applying the validated patch to the exact workflow base. If the same file receives additional edits before closure, this verifier fails closed and requires a new validated workflow contract.

Unrelated files may change in the integration commit.

## Limits

- Git repository/configuration and the Git executable remain trusted host inputs. Runner-owned Git commands disable hooks, but this is not an OS sandbox.
- SHA-256 receipts are tamper-evident; repository integrity still ultimately depends on trusted Git storage and host control.
- This package does not merge PRs, push commits, deploy code, scan networks, invoke live tenant tools, or authorize a model to close findings.
- Untrusted third-party repository execution remains under the existing secpatch disposable-runner contract.
- No reserve data, training, model promotion or deployment authority is introduced.

## Qualification target

The package uses real temporary Git repositories/worktrees in tests and must pass the full HDF core + runner + controller + landed-integration suite on Python 3.11 and 3.13 before repo-side qualification.
