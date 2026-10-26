# HS01 overnight — initial measured checkpoint

- Ownership / task: Codex lead, HS01, issue #40.
- Base: PR #36 `bac21a453f1f3a98765633c4847ada4d31779422`.
- Mission packet: `db1ef9116eea7ab0c218b0cc4f8a1f3eece84770`, all four
  `orchestration/HS01-OVERNIGHT/` documents. Review: PR #38
  `23d5964c279feaee246be8ec6e06c1052092535d` and experiment #01.
- Owned changes: `labs/model-lab/{diagnostics,gpu_lease,haven_runtime}.py`,
  narrow core/server/UI integration, focused tests and `ops/haven-core/` receipts.
- Actual: read-only Slink observations and static implementation checks. Live
  model acceptance is pending Claude's explicit GPU release. No root changes,
  disk mounts/writes, new cold start, paid calls or merges.
- Classification: public-safe aggregate findings; raw host records withheld.
- Requested disposition: independent peer review; no self-approval/promotion.

## What is newly known

The preserved first service journal independently reconstructs 868 seconds from
start to readiness, 33.02 GiB experts / 836 seconds, and a whole-service CPU
total of 87.292 seconds with zero recorded swap peak. The CPU/swap totals cover
the complete service invocation, including its short response, not only loading.
This weakens CPU-only initialization and swap-thrashing explanations, without
establishing a physical read rate.

Current sysfs and kernel data agree on a 480-Mbit/s root USB link. The storage
driver already uses UAS. A boot-log USB disconnect concerns a different device;
it is not evidence of a root-SSD reset. USB 3 controllers exist, but the currently
negotiated root link remains USB 2. No cable, port or mounted root device was
changed.

Internal nonrotating candidates have unmounted NTFS filesystems. Their free
space, hibernation/encryption state and suitability for Linux model writes are
not established. They are not an approved empty model volume.

The ranked hypothesis is an I/O-path bottleneck; effective initialization is
about 40.4 MiB/s, close enough to practical USB 2 rates to justify a bounded
direct file-read comparison. That probe waits for peer release, because even a
read-only throughput test can interfere with an active experiment. No migration
or faster-port performance improvement is yet claimed.

## Implementation and remaining evidence

The [fixed diagnostic/tool and runtime contract](HOST_DIAGNOSTICS.md) documents
the new routes, authorization, saved evidence, startup/cancel ownership and
ordinary user-service controls. The operator explicitly requested eliminating
manual Strata command/browser startup during the campaign. This is scoped user
application work; privileged host setup is neither needed nor performed.

Independent falsification of the peer scorer uses
`peer-verifier-challenge.py`. It must run against recorded source revisions:
Claude was already repairing its verifier when the first challenge executed.
Do not report a stale source finding as a current failure, or conflate a
crafted invalid record with an observed model exploit. Final peer critique and
morning receipt will retain the positive control and all negative controls.

Private source bundle hashes and exact output/exit receipts are retained on the
administration Mac. No machine inventory, raw logs or model answers are included
in this checkpoint. Final real-world diagnosis, probe results and model/tool
comparison remain explicitly unexecuted here.
