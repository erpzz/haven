# Host-owned apply/retest runner

This stacked package extends the Local Defense Factory core from PR #180. It is intentionally a separate review unit.

## Contract

The runner accepts only:

- an exact Git repository toplevel;
- an exact lowercase base commit hash;
- a patch that already passed the #180 fix-response gate and still matches its SHA-256;
- the exact touched-path receipt from that validation;
- one or more **host-created** `Recipe` objects.

The model never supplies shell text or decides which tests establish success.

## Isolation and execution

For each fix, the runner:

1. creates a disposable detached Git worktree at the exact base commit;
2. disables Git hooks for its own Git commands;
3. rejects patch targets that are missing or symlinks;
4. runs `git apply --check`, then applies the already-validated patch;
5. re-enumerates changed files and requires an exact match to the validated touched-path set;
6. executes host-owned argv arrays with `shell=False`;
7. gives each command its own POSIX process group and terminates/kills the group on timeout;
8. stores only exit/timing/byte counts and SHA-256 hashes of stdout/stderr in the retest receipt;
9. removes the disposable worktree.

A passing receipt requires every prescribed recipe to execute successfully. The receipt hash can be recorded in #180's lifecycle ledger before a finding is closed.

## Threat-model limits

This is not an OS sandbox.

- The repository and its Git configuration are trusted host inputs. Hooks are disabled, but repository/global Git filters and the Git executable itself are not independently sandboxed.
- Recipe argv is trusted host policy. A bad recipe can intentionally perform network or filesystem actions; the model cannot author the recipe.
- Output is streamed to temporary files and hashed, avoiding pipe backpressure and raw-output persistence in the returned receipt, but a very noisy trusted recipe can still consume temporary-disk space until its timeout.
- The hard process-group runner is POSIX-only in this version. Windows is unsupported rather than silently weaker.
- No live tenant/network scan, exploit action, deployment or credential access is introduced.

## Author test receipt

Local stacked run after second-pass hardening:

- 21/21 core + runner tests PASS;
- `py_compile` PASS;
- real temporary Git repositories/worktrees used in runner tests;
- timeout regression proves a descendant process is killed before a delayed side effect;
- symlink patch-target regression PASS;
- patch-hash/touched-path tamper regressions PASS.

Second pass added: mode-change rejection in the core, symlink-target refusal, hard timeouts for Git plumbing, and `core.hooksPath=/dev/null` on runner-owned Git commands.

Exact-head GitHub Actions is required before this package is called clean.
