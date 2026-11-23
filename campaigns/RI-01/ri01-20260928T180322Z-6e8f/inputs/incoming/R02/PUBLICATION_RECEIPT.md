# R02 / H02 — Exact-source publication receipt

**Publication date: 2026-09-28. Scope: source preservation and GitHub handback publication only.**

## Metadata

- Thread / ownership: R02 / H02. Related coordination task: [issue #2](https://github.com/erpzz/haven/issues/2); its P01 reconciliation is not performed by this upload.
- Operator request: add this conversation's R02 deliverables to `erpzz/haven` through the GitHub connection.
- Pinned base: `dd7e7e3d8a01d5773424678376e1e52d71723da7`; base tree `e2b67f4d70ca43fb9ff01ed875b20b01a31bce1b`.
- Owned branch: `research/r02-handback-publication-v2`.
- Outputs: new `design/H02/R02/v2/` publication and `design/H02/R02/README.md` index only. Existing `v1/`, baseline, coordination records and other owners' files are retained.
- Inputs read: pinned repository `AGENTS.md`, `START_HERE.md`, `PRECEDENCE.md`, `CURRENT_STATUS.md`, `coordination/PROTOCOL.md`, `coordination/THREAD_STATUS.md`, `coordination/HANDBACK_METADATA.md`; existing R02 tree and benchmark text; issue #2 assignment; the delivered ten-file R02 ZIP. The existing workflow trigger was inspected to avoid starting the source importer.
- Source: `HAVEN_R02_Intelligence_Runtime_Handback_v1.zip`, 52,543 bytes; SHA-256 `19c7ad35e53b95442e7fc4b2c4cb54658a5a01821546a1c10b1be67adf83de8e`.
- Classification: public-safe publication delta. No new personal records, secrets, account access, household recordings, employer data or host inventory are introduced. The source delta from the existing public R02 import is the safety sentence below; all other source bytes already matched that import.
- Requirements and local identifiers: unchanged. CR-R02-01 through CR-R02-05, R02-Pxx, R02-Txx and R02-Sxx retain their original proposed meaning.
- Disposition requested: review the source publication and its fidelity. No new design acceptance, coding authorization, model qualification or physical acceptance is claimed. Verified commit and PR receipts are posted to issue #2 after remote read-back.

## Why there is a publication v2

The original handback is research revision 1.0. Its text, dates, README, input audit, sources and checks are preserved, not regenerated. Here, `v2` means a second **repository publication edition**. It does not claim a second research study.

At the pinned base, all ten filenames existed under `v1/`. Nine Git blob IDs matched the delivered source exactly. `BENCHMARK_AND_EXPERIMENTS.md` differed by a single 46-byte sentence in section 6, Stage B:

> A completed print is not an accepted fixture.

Deleting that sentence, including its leading space, from the delivered bytes exactly reproduces the existing GitHub blob `c7997f67b62eb0a05e9553ee87e3a8e4b4162fa5` (20,738 bytes). The complete original is blob `37458330d305b6bea09759d08968cef71914b6e1` (20,784 bytes). The earlier import retained the original manifest, so that one manifest entry does not match its benchmark file. The cause of the earlier omission is unknown.

No earlier file is overwritten. This publication supplies all ten exact delivered files together so their local links and original manifest work as a unit. Nine existing Git blobs are reused directly; only the complete benchmark source needs a different blob. The original ZIP itself is not duplicated as an opaque binary: every archive member is available as readable, versioned source, with the ZIP's identity recorded above.

## Checks actually performed

In the chat working container, Python `zipfile` and `hashlib` were used to enumerate and extract the ten regular archive entries, verify the nine original SHA-256 manifest entries, calculate each Git blob ID, and compare those IDs with the pinned GitHub tree. The source packet contains Markdown, JSON and a checksum manifest, with no nested archives or executable application files. Local relative Markdown links were checked and none were unresolved.

Results before commit: **10 source files accounted for; 9/9 original manifest entries passed; 9/10 existing v1 files matched; the sole 46-byte difference was reproduced exactly.** The complete benchmark blob returned by GitHub on upload matched the locally calculated source blob ID.

Reproducible source-manifest check after checkout:

```sh
cd design/H02/R02/v2
sha256sum -c MANIFEST.sha256
```

Expected: nine `OK` entries. Actual equivalent local Python checks: nine passed. The original `MANIFEST.sha256` covers the original nine other source files; it does not claim coverage of this new receipt or `PUBLICATION_SOURCE_AUDIT.json`. The new audit supplies all ten source identities and the earlier-import comparison.

Remote tree read-back and the PR changed-file list are checked after publication, with the verified commit/PR posted to issue #2. Those publication checks establish source fidelity, not scientific truth or runtime correctness.

## Integration summary and stop gate

Use [INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md) for the original one-page architecture summary and [CONTRACT_DESIGN.md](CONTRACT_DESIGN.md) for exact interface proposals. The recommendations, uncertainty, no-model-first routing, independent authority boundaries, two-user privacy requirements and bounded experiments are unchanged.

The next design gate remains the separately scoped R02-P01 reconciliation and relevant H00/H04/H06 decisions; no P01 evidence mapping is claimed here. Actual NIGHT-01/R1 results and M0 acceptance were not inspected by this publication task. No source claim, model ID, API behavior or price was refreshed; source dates must not be interpreted as current verification.

Application tests, model/framework benchmarks, private-account tests and physical experiments: **NOT_EXECUTED**. No application code, shared schemas, M4 model selection, workflow, repository setting or external execution flag is changed. No agent, paid call, installation or physical operation is started. No PR is self-merged. The broader repository migration is outside this audit; this receipt makes no claim that it is complete.
