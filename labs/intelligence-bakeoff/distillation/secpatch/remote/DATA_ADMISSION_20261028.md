# Specialist handback

Thread / owner / task ID: R02 / H02 / corrected secpatch admission and external CUDA campaign.
Repository: `erpzz/haven`; package base PR86 at
`51fce8857a1a9948f81b7871dc3661b8eb02fbbe`; initial PR89 at
`5479e974297a1d68734b8e981f779c291f043630`.
Read inputs: the remote package README, prepare/quota/run/verify wrappers,
SOURCE_BASE.json, unchanged original builder and campaign, and the previously
retained private source evidence. Core source hashes remain those in SOURCE_BASE.json.
Owned output: remote wrapper, its focused tests and this public-safe handback.
Private source data, correction receipts, provider account observations and downloaded
artifacts remain outside Git. No original REQ/AT/EX or R02-to-H02 mapping changed.

## Decisions

Exclude independently established package-license conflicts through the existing
`checks.permissive_license=false` admission mechanism in copied harvest records.
Keep original records and hashes, retain their historical root-license field,
and add exact source-path/package evidence. Do not rewrite GPL as MIT or expand
the campaign's allowlist. Rebuild with the unchanged builder and its cutoff,
repository partition, deduplication rules, seeds and Bandit version.

The initial conflicting LlamaIndex web-reader fix is GPL-3.0-or-later at its
recorded commit. Package metadata also exposed Sentry FSL, CKAN AGPL and
Zope/Repoze declarations outside the existing allowlist. Fourteen original
harvest records were excluded: thirteen train fixes and one held-out fix.
The corrected export has 257 train fixes / 154 repositories / 1,919 rows and
36 held-out fixes / 31 repositories / 252 evaluation rows. No new fix was admitted.

## Evidence

Original artifact hashes were verified before and after correction. All five
harvest inputs retain their original order. The corrected source check reuses
independently checked commit/parent and vulnerable/fixed blobs by exact identities,
and adds package manifests checked against Git tree blob IDs. It covers every
one of the 293 exported fixes, preserves constituent notices and advisory
attribution, and records each exclusion and original/corrected source hash.
Additional Apache, BSD and PSF notices referenced by cryptography's root license
were retained. Project files were parsed as data; no third-party tests or setup
scripts were executed.

The existing builder was replayed against corrected inputs. All six JSONL files
match exactly; the manifest matches except its build timestamp. Relative to the
original build, train loses 101 rows, held-out reference data loses eight,
held-out evaluation loses seven, and repository-evaluation candidates lose one.
Seeded decoys also change 257 surviving train rows, 230 development rows and
36 held-out reference rows. Surviving evaluation rows are unchanged.

A minimal private dataset was created, reached provider status `ready`, and
was downloaded to a fresh directory with byte-identical payload verification.
It declares the composite `other` license, retaining source notices and CC-BY-4.0
advisory attribution. Identifiers and full receipts are in the private handback.

Two submitted notebook versions terminated at the unchanged CUDA preflight,
before setup, model download or training. Requested T4 metadata was accepted,
but CUDA was unavailable; a second version's explicit GPU-image request did not
change the server-selected CPU-image path. The actual account settings page then
showed an unverified phone status and disabled accelerator choices. Stop at that
owner-operated access gate; no CPU fallback or fabricated GPU result.

## Interface changes

The source-check receipt includes `metadata`, `metadata_texts`,
`package_metadata_at_commit` and an `input_correction` receipt. The wrapper checks
ordered corrected harvest hashes, retained metadata bytes, nearest package
declarations and deeper source-license precedence. It preserves original notice
bytes and the minimal campaign payload. New notebook titles match their intended
slugs; controller commands must still use the actual provider-returned URL.
Trainer, grader, tasks, pinned model revision, thresholds and watchdog are unchanged.

## Acceptance

Eight focused wrapper tests pass, including rejection of restrictive package
metadata despite a permissive root notice, and deeper source-license precedence.
Python compilation, whitespace checks and core-source hash checks pass.
Real corrected-data qualification, builder replay, private visibility, processing
completion and upload/download integrity pass with private receipts.

NOT_EXECUTED: a CUDA optimizer, adapter creation and paired model evaluation.
Neither failed startup contains a training receipt or adapter. The watchdog
retains failed exit receipts and input-lock identity. No model-quality score,
GPU hardware observation or successful training result is claimed.

## Risks and open questions

License classifiers remain heuristic; a consistent receipt is not proof of an
honest collector or a legal opinion. Static declarations and retained notices
resolve the known admission conflicts, but do not prove semantic independence
or absence from the base model's training corpus. Provider metadata and nominal
quota do not prove accelerator eligibility or actual CUDA allocation.

## Next package

The owner completes Kaggle's Phone verify flow in the existing account, with
phone number and SMS code entered only on Kaggle. After verification, recheck
quota and terminal status, select an enabled free GPU environment, and resume
the existing locked payload for one real campaign. Success requires the unchanged
saved-weight and matched held-out verifier; stop on unavailable CUDA, exhausted
quota or any failed provenance/artifact gate. No paid fallback, production
promotion, Slink GPU use or Model Lab restart is authorized by this handback.
