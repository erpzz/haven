# Secpatch repository evaluator: disposable runner contract

Status: **not an approved production sandbox**. The evaluator executes third-party
`pip install` build hooks and `pytest` code. Neither a virtual environment,
scrubbed environment variables, a dead proxy, a Docker command, nor
`--acknowledge-isolated-runner` proves kernel-level confinement.

## Separate owner-controlled runner required

The runner must be provisioned independently of the evaluator and Slink's
Model Lab. Before executing any untrusted repository setup or tests, its owner
must verify all of the following and retain the results outside Git:

1. Disposable VM or equivalent isolation boundary with **no host home, SSH
   agent, Git credentials, cloud credentials, Docker socket, sensitive mounts,
   or access to the Slink GPU/runtime**. Use a non-root guest identity.
2. OS-enforced network denial **during editable installs, build hooks and
   pytest**. The evaluator's HTTP proxy variables are not enforcement.
3. No writable host bind mounts. Give the guest only disposable working
   storage, read-only wheelhouse/input artifacts and a dedicated output path.
4. Independent memory, CPU, process-count, disk and wall-clock limits. Reap
   descendants and destroy the guest after the evaluation.
5. **Real negative probes** run from inside the same guest identity and
   restrictions used for the third-party code: attempt to read a deliberately
   placed host-only sentinel, connect to a controlled external endpoint, and
   write to a host-only directory. All three must fail for confinement reasons.
   Preserve exit codes, effective mount/network configuration and guest
   lifecycle receipts. Do not probe actual secrets.
6. Explicit owner review of the above before supplying
   `--acknowledge-isolated-runner`. That flag is a declaration, not a
   security primitive or an attestation.

## Staged acquisition and offline evaluation

The evaluator still fetches a pinned GitHub commit over HTTPS before executing
repository code. Perform that fetch in the disposable guest with restricted
egress; never pass host tokens or Git config to the subprocess.

Prepare a **trusted, pre-provisioned offline wheelhouse** in a separate
dependency-acquisition stage. Mount it read-only in the evaluation guest.
The evaluator now requires `--wheelhouse /path/to/wheels` and sets
`PIP_NO_INDEX=1` and `PIP_FIND_LINKS` for every install attempt. A missing
wheel is a hard install failure, not permission to enable a network index.
Requirements files and build hooks may still contain direct network requests:
**only the OS network boundary can block them**.

Example invocation *inside a verified disposable guest only*:

```sh
python3 secpatch/repo_eval.py \
  --candidates /input/candidates.jsonl \
  --sandbox /scratch/secpatch \
  --out /output/repo-eval.jsonl \
  --wheelhouse /input/wheels \
  --acknowledge-isolated-runner
```

## Additional input defenses

Candidate records are checked before subprocesses: GitHub owner/repo shape,
immutable commit/parent hashes, advisory workspace IDs, Python source/test
paths and pytest function names. A source or test path that resolves through a
symlink is refused after checkout; source paths are checked again after the
vulnerable-parent checkout. Clone subprocesses receive a scrubbed environment
without host tokens or user Git configuration.

These defenses **do not replace** the guest boundary and do not prove that
third-party code cannot escape it. No real untrusted project was installed or
tested in this PR. Live confinement acceptance is blocked until an authorized
isolated runner and negative-probe receipts exist.
