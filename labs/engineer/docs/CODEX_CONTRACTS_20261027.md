# Codex A and Codex B: integration contracts (2026-10-27)

Opus is the merge and deployment owner. Neither Codex lane merges, deploys, restarts services, loads models or
takes the GPU. The architecture is fixed: `labs/engineer` is the only controller, and TSZ supplies discovery and
external-approval inputs. Anything that adds a reservation system, scheduler, remote dispatcher, attestation
workflow or competing dashboard gets declined at review.

## Codex A: TSZ hardening port (PR #65, `codex/tsz-input-hardening-20261027`)

**Files you own:** `ops/tsz/**`, `labs/tsz/**`, and their tests.
**Files you do not edit:** `labs/engineer/**`. Open an issue or comment if a change there is needed.

Accepted from `93139aa`, ported onto current main:
- placement input validation: already on the PR; reviewed and fine
- private-I/O helpers (`private_io.py`): no symlinks, owner checks, size limits, atomic 0600 writes
- inventory race and lock tests
- worker_runtime input validation, which stays a library and is not wired to any runner

Approval freshness, which is the interface decision you asked about:
- Implement the import side of [`TSZ_TRUST_CONTRACT.md`](TSZ_TRUST_CONTRACT.md) "Import".
- `producer`, `revision` and `issued_at` are **required**, not optional. No producer exists yet, so this breaks nobody. The optional-revision path in `93139aa` is not accepted.
- Revision rules: lower is `stale`, equal with a different digest is `conflict`, equal with the same digest is a no-op.
- Store `approval{producer, revision, issued_at, expires_at, digest, imported_at}` in state.
- Carry `ssh_host_key_sha256` per node.
- Append to `import-receipts.jsonl` on every attempt.
- Keep `read_state(dir)` and the existing `nodes`/`candidates`/`generation` keys stable. `labs/engineer/trust.py` imports them.

Not accepted: the second dispatcher (`553046e`). Do not wire up `worker_runtime plan-jobs`, and add no polling timer for imports.

**Done when:**
- `python3 -m unittest discover -s ops/tsz/tests` and `-s labs/tsz/tests` pass.
- `labs/engineer` tests pass unchanged.
- Each rejection path has a test.
- The PR description lists the ported and dropped hunks of `93139aa`.

## Codex B: storage diagnostics and SSD/USB upgrade validation harness

**Files you own:** a new directory `ops/storage/` (scripts, schema, README, tests). Nothing else.

**Read-only.** Allowed:
- `lsblk`, `findmnt`, `smartctl -a`/`-x` (read), `udevadm info`
- `lsusb -t` (link speed)
- `/sys/block/*/queue/*` reads
- `fio` with `--readonly` against files or the raw device

Not allowed:
- any write to a block device or filesystem outside `ops/storage/` output in a private dir
- mount, umount, partition, format, `fstrim`, `hdparm` settings, `fstab`/bootloader/EFI changes
- installing packages without saying so in the PR

Facts to start from (Slink, 2026-10-27):
- Root and `/boot/efi` are on `sdb`, a **USB** Crucial X9 1 TB.
- There are internal SATA `sdc` (MX500 1 TB) and `sdd` (4 TB HDD), plus an NVMe `nvme0n1` (1.9 TB, Windows partitions).
- Strata's cold start on the current root disk takes about 15 minutes. That is the user-visible cost to measure.

What to build:
1. **`ops/storage/diagnose.py`**: one JSON report per run.
   - Per disk: transport, negotiated USB link speed (5 Gb/s or 480 Mb/s), SMART health and wear, mount role, queue settings.
   - Write serial numbers, WWNs and by-id paths only to a private file (0600, outside the repo). The public report uses stable hashed ids.
2. **`ops/storage/validate.py`**: a reproducible before/after harness.
   - Sequential and 4K random **read** throughput (fio `--readonly`, fixed size, fixed seed, direct I/O).
   - Cold model-file read time for a named model file (page cache dropped only if the owner runs that step; otherwise report warm vs cold honestly).
   - Repeat at least 3 times and report the median and spread.
   - The same command runs before and after a hardware change, and the output schema includes the host, the disk hash id and the time.
3. **A short README** listing the upgrade options the data supports (for example a different USB port or cable, or moving the model store to internal SATA), each with its measured or expected effect. No recommendation that needs a destructive step is executed.

When to run:
- Static and metadata collection may run any time.
- Any `fio` run, even read-only, competes with model loads. Run it only when `labctl state` shows no Lab job, `systemctl --user is-active haven-strata` is not `activating`, and no `haven-paradigms*`/bench unit is active. Record that check in the report.
- Never run while a model is loading.

**Done when:** tests for the parsers run on fixtures, one real `diagnose.py` report exists privately, and the PR shows the public (hashed) version.

## Coordination

- Opus posts interface decisions on your PR before you implement across a boundary. Ask on the PR first.
- Keep receipts private (`~/.local/state/...`). The repo gets only code, schemas and hashed or summary results.
