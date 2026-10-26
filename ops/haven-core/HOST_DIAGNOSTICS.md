# Fixed host diagnostics and prepared runtime controls

HS01 overnight implementation, based on runtime PR #36. This adds to the
existing stdlib Model Lab; there is no new agent framework, inference listener,
installation or model download. See issue #40 for executed campaign receipts.

## User flow

On Linux, Playground offers **Use Strata**, **Use fast 4B**, and **Investigate
host** to administrators. The first two control only the already-prepared Haven
runtimes. Startup runs asynchronously and is cancellable in Setup. The private
Strata key stays on the server. Chat stays in the same Haven interface.

An active/reserved Claude experiment disables switching and diagnostic inference.
The server independently verifies peer units, actual GPU PIDs and a nonblocking
cooperative file lock. It never stops an unowned job to claim the GPU. Changing
to fast 4B explicitly stops the one named Haven Strata user unit. Generic
disconnect/unload retains its existing external-backend contract.

Cold Strata startup has a 20-minute readiness bound, with elapsed status rather
than invented percentage progress. Cancellation stops Strata only if that switch
started it; an existing external service survives cancellation. When a failed
Strata switch displaced the owned fast runtime, recovery attempts to restore the
prepared 4B without touching unrelated processes. Cleanup/recovery failures are
reported. No retry, download, install or tuning occurs.

## Diagnostic contract

`POST /api/diagnostics` accepts only `question` (1–3000 characters),
`tools_enabled` (boolean), and `deadline_seconds` (15–240; default 180). Linux
owned llama inference must be ready and the GPU lease available. The optional
no-tools mode supports the overnight comparison; it is not a host observation.

The local model can request only these functions, with **empty arguments**:

| Function | Fixed real sources | Boundary |
| --- | --- | --- |
| `haven_storage` | root `findmnt`, sysfs USB/storage mapping, `lsblk`, root free space | No mount, raw-device read, internal-drive write or user path |
| `haven_strata_history` | bounded prepared-unit journal, parsed numeric startup/CPU/swap fields | No journal text or credentials forwarded to the model |
| `haven_pressure` | `/proc` RAM/pressure, bounded kernel-error counts associated with the root device | Current counters are not historical startup evidence; unavailable is unknown |

Every result carries tool identity, UTC capture time, exact fixed argv/exit
codes, typed source measurements and a SHA-256-based evidence ID. This proves
record identity, not scientific truth. The model receives no shell, service
control, arbitrary path, network target or caller-selected principal. Tool
results are untrusted data. The loop is bounded to four calls, five model turns
and a wall deadline, with no automatic repair/reprompt.

The browser labels completion as execution status and warns about fabricated or
missing evidence IDs. Even a cited, completed answer can be scientifically wrong;
the code does not promote ID membership into a truth score.

Final text and trace are saved atomically as private receipts under the Lab data
directory. `GET /api/diagnostics/JOB_ID` retrieves the same result after browser,
tunnel or service reconnection. An interrupted process is marked `INTERRUPTED`
on restart; inference is never replayed. Cancelling closes the request, with
backend cessation explicitly UNKNOWN. Confirmed process termination still
requires stopping an owned engine.

Both new POSTs and saved diagnostic reads require administrator authorization.
The legacy job route independently rejects diagnostic access by members; general
state omits question/evidence. LAN cookie requests still require CSRF. Tokens,
raw machine evidence and transcripts belong outside GitHub.

## Validation and deployment status

Focused CPU tests cover a real loopback HTTP function-call exchange with a fake
inference server, private receipt reconnection, real `flock` exclusion, rejected
command/path arguments, cancellation ownership, and account-role boundaries.
These are `STATIC_TEST`, never real-model results. Account tests run on Ubuntu
Python with scrypt. Real Slink model/UI receipts are recorded separately only
after execution and peer GPU release.

The overnight campaign permits no new Strata cold start by default. Live cold
switch qualification is therefore separate from source/lifecycle validation;
do not manufacture a second 15-minute load for a screenshot.

`probe-strata-storage.py --run-after-peer-release` is a separate one-shot
read-only measurement: 256 MiB sequential plus 32 spread 4 KiB reads of the
existing prepared first model shard. It uses O_DIRECT and aligned buffers, has a
60-second alarm, verifies a regular file on the root filesystem, respects the
GPU/peer admission boundary, saves a private receipt, and declines to repeat an
existing receipt. It never reads a raw block device or flushes caches. Direct
I/O bypasses the Linux page cache; device and bridge caches remain uncontrolled.

On the Mac, `run-diagnostic-challenge.py --run-after-peer-release` runs the same
registered question once without tools and once with real tools through the
authenticated tunnel. It retains both failures and successes privately. After
closing and reopening the tunnel with `open-lab.py`, `--retrieve-only` compares
saved job contents using GETs and never repeats inference. These scripts are an
acceptance plan until an actual run is recorded in the overnight receipt.

Rollback: stop only an in-progress switch through its cancel control. Keep
prepared model artifacts and private diagnostic receipts. Restore the previous
runtime source revision and restart/reload the known fast 4B only at an idle
checkpoint; do not change systemd units, drivers, firewall, SSH or disks.
