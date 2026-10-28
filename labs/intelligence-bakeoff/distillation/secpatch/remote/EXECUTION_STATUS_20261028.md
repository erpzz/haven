# Specialist handback

Thread / owner / task ID: R02 / H02 / External GPU Training Execution.
Coordination issue: #40; pipeline PRs #75, #82, #84.
Repository: `erpzz/haven`; actual base read:
`eaa76f834bc9f64fe9aada542fdf3c00ba9a6f55`.
Input repository versions and SHA-256: [SOURCE_BASE.json](SOURCE_BASE.json).
Read inputs additionally include root `AGENTS.md`, `START_HERE.md`,
`PRECEDENCE.md`, `CURRENT_STATUS.md`, `coordination/PROTOCOL.md`,
`coordination/HANDBACK_METADATA.md`, original handoff template and
`ops/haven-core/MORNING_20261026.md`, at that base.

Requirements covered: operator's seven execution steps and R02→H02 ownership
retained. No original REQ/AT/EX identifier, shared contract or model architecture
changed. New version: external execution package v1.

Actual work: connected-source and credential-readiness checks; official Kaggle
CLI installation in an isolated CPU environment and actual failed quota request;
pipeline gate review; private execution-wrapper preparation and offline checks.
Proposed/pending: real-data qualification, cloud submission, CUDA fine-tuning,
base/adapter held-out evaluation, output retrieval and usage measurement.
Owned paths: `secpatch/remote/` and `tests/test_secpatch_remote.py` only, beneath
`labs/intelligence-bakeoff/distillation/`. Original pipeline files are unchanged.
Publication classification: public-safe source/docs; account snapshots, datasets,
weights and runtime logs remain outside Git. No raw private account evidence
is included in this handback. Review requested; no self-approval or promotion.

## Decisions

**BLOCKED / NOT_EXECUTED.** Stop cloud execution at the authentication gate.
Kaggle remains first priority; no authenticated free GPU was accessible.
The exact observed blocker is **“Authentication required to call the Kaggle API.”**
The existing account must be connected with official OAuth or a secret binding
before GPU eligibility, quota or private notebook authorization can be verified.
No new account, credential extraction, paid provisioning or quota bypass was
attempted. Lightning AI / Modal were not authenticated and cannot be treated as
usable merely because they offer included credits.

## Evidence

Observed on 2026-10-28:

| Check | Actual result | Limit |
|---|---|---|
| Cloud Environment readiness | Connected; current observations; enforced unrestricted HTTP; no secret bindings, runtime variables or outbound identities | Environment availability does not establish provider authorization |
| Kaggle CLI 2.2.5 | `kaggle quota --format json` exited 1 with authentication required | No GPU quota/account eligibility observed |
| Provider credential presence | No Kaggle/Lightning/Modal credential variables or standard local credential locations | Does not assert those accounts do not exist elsewhere |
| Connected provider tools | No applicable Kaggle/Lightning/Modal execution or connected-browser-session tool available | No authenticated browser account/quota inspection possible |
| Dataset | No real secpatch data or original OSV/harvest provenance attached or in checkout | Counts, licenses and isolation of an actual dataset remain unqualified |
| Required source | #75/#82/#84 confirmed merged; original pipeline hashes recorded | Prior code/CPU tests are not real GPU evidence |

| Requested experiment output | This task |
|---|---|
| Provider actually allocated / GPU hardware | None / not observed |
| Jobs submitted / experiment GPU runtime | 0 / 0 |
| Account quota balance / account-level consumption | Unknown; unauthenticated |
| Paid calls, charges authorized or incurred by this task | None |
| Adapter bytes, hashes, optimizer receipt | Not produced |
| Base-versus-adapter held-out results | Not executed; no numbers invented |
| Slink GPU / Model Lab | No connection, GPU query, model load or restart |

Private controller evidence: readiness result, credential-presence checks and
CLI exit/output. Public-safe report deliberately omits account identifiers and
host inventories. Required Stripe Directory setup documentation was consulted;
Directory CLI was absent and no account/provisioning setup was pursued. Provider
choices came directly from the operator. No broader vendor search was needed.

## Interface changes

Only an environment wrapper is added. `prepare.py` takes original data,
candidates, ordered harvest shards and matching OSV archive, replays the existing
builder, then emits an allowlisted private payload and notebook outside Git.
It retains the original 25/8 minimums, cutoff, deduplication policy and licenses.
`run.py` refuses local execution and calls unchanged `gpu_campaign.py` on Kaggle.
The notebook watchdog bounds descendants to two hours; the provider allocation
must also be observed to end. `quota.py` records precise provider usage before
and after; `verify.py` checks downloaded weights and exact paired evaluation
identities against the original local lock. Output errors remain failures.
No automatic retry, promotion, application interface or production deployment.

## Acceptance

Executed in the managed CPU workspace:

```bash
python -m unittest discover -s labs/intelligence-bakeoff/distillation/tests -p 'test_secpatch_remote.py' -v
python -m py_compile labs/intelligence-bakeoff/distillation/secpatch/remote/*.py
git diff --check
```

Expected/actual: five offline wrapper tests pass; Python sources and generated
notebook code compile; patch whitespace clean. Tests check original core hashes,
rejection of altered/unsafe payloads, local execution refusal before CUDA import,
unexecuted notebook generation and refusal of absent real data. No model,
CUDA mock, fake adapter or simulated training campaign is used.

**NOT_EXECUTED:** positive original-dataset replay, successful upload/private
visibility check, provider CUDA run, actual watchdog timeout on Kaggle, output
download, successful real-artifact verification and quota-delta attribution.
No independent reviewer or scientific acceptance is claimed.

## Risks and open questions

Both authentication and original data are required. Pipeline reproduction is
stronger than trusting row flags but does not independently authenticate forged
upstream sources or prove legal compliance. Fixed-code/semantic overlap and
pretraining contamination are not fully controlled by the existing split policy.
Provider image compatibility and GPU allocation remain untested. Timeout may
leave a partial adapter; it is not a completed experiment. Quota deltas cannot
be attributed through a reset, delayed accounting or concurrent GPU sessions.
The single seed and up-to-12-fix evaluation are pilot evidence only.

## Next package

Connect the existing authorized Kaggle account securely; verify eligible free
GPU quota and private visibility; attach original data/provenance. Follow
[README.md](README.md) to prepare and submit once with a conservative quota
reserve and two-hour process budget. Success is verified saved adapter bytes,
observed CUDA optimizer steps, matched held-out base/adapter results and a
provider usage receipt. Stop on any failed gate; no paid fallback. If successful,
the next experiment is seeds 7 and 13 on the same frozen data under a separately
bounded free-quota budget. Reviewable source is delivered on an owned branch;
the merge/deploy owner retains integration authority.
