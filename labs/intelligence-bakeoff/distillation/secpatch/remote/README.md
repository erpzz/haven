# R02 external GPU execution package

The original cloud session reported **BLOCKED / NOT_EXECUTED**. That historical
authentication observation is environment-specific and must be rechecked; no
adapter or model-quality result is claimed. This package wraps the merged
#75/#82/#84 pipeline without changing its architecture, tasks, training recipe,
graders or promotion rules.

## Original cloud connection blocker

Kaggle CLI **2.2.5**, installed in a separate environment, was actually invoked:
`kaggle quota --format json` exited **1**, reporting
**“Authentication required to call the Kaggle API.”** No Kaggle access token,
legacy key, OAuth credential file or alternate configuration directory was
available. Connect the **existing authorized Kaggle account** with
`kaggle auth login` in an accessible interactive session, or bind its token as
`KAGGLE_API_TOKEN` using the environment's secret configuration. Keep credentials
outside Git and notebook cells. Never paste them into chat or public artifacts.
Successful authenticated quota retrieval, GPU eligibility and private notebook
access must be verified before submission. A nominal free tier is insufficient.

Lightning AI and Modal had no configured credential variables or credential
files in this environment. No account balances, included credits or hard spending
caps could be established. Do not launch there without those observations; do
not enable payment, purchase credits, auto-reload or another account. Provider
priority remains Kaggle → existing Lightning credits → Modal included credits.

The original cloud environment also lacked the real secpatch dataset and its
OSV/harvest provenance. The repository has unrelated synthetic fixtures, which
are **not** substitutes. Supply and independently check the original private
data and provenance files before running `prepare.py`.

## Existing gates and qualification limits

The unchanged `gpu_campaign.qualify_data` requires >=25 distinct train fix keys,
>=8 held-out fix keys, disjoint train/held-out repositories and keys, recorded
commit/parent/advisories, one of the existing permissive licenses, verification
flags, train-only targets, held-out prompts without assistant answers and a
grader. Fix-key counts are not proof of statistical independence.

Before creating a payload, `prepare.py` additionally hashes the original OSV
archive and replays **the existing `build.py`**, with original candidates,
harvest order, Bandit 1.9.4, cutoff 2025-07-01 and near-duplicate threshold 0.8.
All seven original output files must reproduce, including the manifest apart from
its `built_at` field.
This exercises the actual repository hash partition, time split, normalized-AST
deduplication and training-to-dev/held-out vulnerable-function similarity filter.
The replay covers all original outputs, but the private payload contains only the
train, held-out evaluation and manifest files, campaign execution code, and the
attribution and provenance needed for those inputs. Original license and notice
bytes are retained per fix, alongside commit and advisory attribution. No data is
harvested, fabricated or relabeled by this wrapper. No original training/evaluator
file is edited.

This reproduces pipeline provenance; it does not independently authenticate a
maliciously forged source collection or constitute legal review. The existing
license classifier is heuristic. Check license text **at each fix commit** and
OSV advisory licensing/attribution if upstream provenance is incomplete; stop if
unresolved. Provide `--source-check` with the independently collected private
audit (`haven-secpatch-fix-source-check-v1`): it must cover each exported fix,
the commit/parent and vulnerable/fixed blobs, and all license and notice files
at the root and along the affected source path at that commit. Each original
notice is included as base64 in `notice_texts`, keyed by its SHA-256, and linked
from the fix's `notices` entries. Package manifests are similarly retained in
`metadata_texts` and per-fix `metadata` entries, with Git blob and SHA-256 identities.
The audit records `package_metadata_at_commit`. The wrapper reads these files as
data, checks the nearest package declarations and deeper source-license precedence,
and rejects declarations outside the existing campaign allowlist. It verifies
original notice bytes and rejects non-permissive or unclassified source-path licenses. A consistent audit file
is not, alone, independent proof that its collector checked the upstream Git
objects. The deduplication policy concerns vulnerable functions, not all
possible semantic or fixed-code leakage. The cutoff does not prove absence from
the pretrained model's undisclosed training corpus.

An admission correction preserves the original artifacts. In copied harvest
records, set `checks.permissive_license` to false for independently established
source-path license conflicts; retain the original license field and add the
exclusion evidence. Rebuild with the unchanged builder. The source-check receipt's
`input_correction` records original/corrected file hashes, exact changed records,
excluded keys and reasons. Its ordered corrected hashes must match `--harvest`.
Do not delete rows from a built dataset, rewrite a restrictive license as MIT,
or expand the campaign allowlist. Report all rebuilt differences: the builder's
seeded decoy choices may change other SFT rows when a fix is excluded.

## Prepare, authenticate and submit once

Use an ordinary CPU environment for packaging. Install the official CLI and the
same static analyzer in an isolated environment:

```bash
python3 -m venv /path/outside-git/r02-tools
/path/outside-git/r02-tools/bin/pip install kaggle==2.2.5 bandit==1.9.4
```

Commands below use that environment's `python`, `kaggle` and `bandit` on PATH.
Set `REMOTE` to this directory, `PRIVATE` to a new private directory outside Git,
and `OWNER` to the existing authorized Kaggle username. These are paths/identity
selectors, never credential values. Keep original shard order from the build.

```bash
umask 077
python "$REMOTE/prepare.py" --data /private/original/data \
  --candidates /private/original/candidates.jsonl \
  --harvest /private/original/harvest-0.jsonl /private/original/harvest-1.jsonl \
            /private/original/harvest-2.jsonl /private/original/harvest-3.jsonl \
            /private/original/harvest.jsonl \
  --osv-archive /private/original/raw/pypi-all.zip \
  --source-check /private/original/fix-source-check.json \
  --owner "$OWNER" --output "$PRIVATE/package"

# Login only if the existing account is not already connected.
kaggle auth login
python "$REMOTE/quota.py" --output "$PRIVATE/quota-before.json" \
  --require-remaining-seconds 18000
```

The 5-hour remaining-quota requirement is a conservative admission reserve for
a 2-hour job on a T4×2 allocation plus startup; it is **not** a claim that Kaggle
always charges both GPUs or that 5 hours will be consumed. Verify that GPU
eligibility, private datasets/notebooks and internet access are enabled on this
account. Stop at phone/account verification or exhausted quota; no workaround.
An authenticated quota response does not prove accelerator eligibility. An
unverified account can accept GPU notebook metadata and still execute without
CUDA. Check the account's Phone verification status and enabled GPU choices
before submission; keep phone numbers and SMS codes on Kaggle, outside chat.
Run no other GPU sessions during the experiment if quota attribution is needed.

`prepare.py` generates a private notebook, exact input lock and allowlisted
payload ZIP container (`haven-secpatch.payload`). It never uploads, submits or contains provider credentials. Review
the generated files and confirm that the notebook metadata has `is_private:true`.

```bash
# Private is the CLI default. Never add --public or -u.
kaggle datasets create -p "$PRIVATE/package/dataset"
# Check the created dataset's private visibility in the authorized account.
# Then submit exactly once; this command requests actual GPU execution.
kaggle kernels push -p "$PRIVATE/package/kernel" --accelerator NvidiaTeslaT4
kaggle kernels status "$OWNER/haven-r02-secpatch"
```

Inspect provider-reported private visibility after creation/submission. Do not
publish the input dataset, notebook or outputs. Avoid unrelated broad source
archives; the ZIP contains only pipeline Python files, frozen dataset and source
provenance. The public Qwen snapshot needs no Hugging Face token. CLI credentials
stay on the controller; do not attach Kaggle Secrets to this notebook.
Use the actual notebook URL returned by `kernels push` for later commands. For
new notebooks Kaggle derives the slug from the title; the generator keeps them
aligned. Requested `enable_gpu`/`machine_shape` metadata is not CUDA evidence.

## Runtime, retrieval and acceptance

The notebook selects GPU 0 and requires >=4 GiB free CUDA memory, installs the
existing Transformers/PEFT/Accelerate versions, caches the immutable Qwen model
revision `c1899de289a04d12100db370d81485cdf75e47ca`, then calls the unchanged
`gpu_campaign.py --execute --max-steps 60 --max-length 1536`. It uses Kaggle's
preinstalled CUDA PyTorch, records its version and never replaces the torch wheel.
If the image lacks compatible PyTorch/driver support, retain the failure and stop.

The 7,200-second process-group watchdog covers dependency setup, download,
training and both evaluation arms. Failure or timeout kills descendants and
retains partial files. Provider startup/finalization and allocation shutdown are
outside that watchdog: inspect final session status and stop the session if it
remains allocated. A process runtime is **not** the provider's quota measurement.
No paid provider fallback, local GPU call, service restart or promotion exists.

```bash
# Only after provider status is complete; failure outputs remain useful evidence.
kaggle kernels output "$OWNER/haven-r02-secpatch" -p "$PRIVATE/download"
python "$REMOTE/quota.py" --output "$PRIVATE/quota-after.json" \
  --before "$PRIVATE/quota-before.json"
python "$REMOTE/verify.py" --result "$PRIVATE/download/result" \
  --expected-lock "$PRIVATE/package/expected-lock.json"
```

Inspect the actual downloaded layout if Kaggle flattens an output directory;
point `--result` at the directory containing `campaign/` and `watchdog.json`.
Retain the provider status response/version number and notebook execution log
alongside quota snapshots. The precision-preserving quota reader reports the
account's usage delta only within the same quota-reset window. Concurrent jobs
or delayed provider accounting prevent attribution: report unknown and retain
both snapshots rather than substitute measured wall time.

Success requires nonempty adapter bytes matching the CUDA training receipt,
60 observed optimizer steps, finite loss, positive CUDA parameter/allocation
evidence, and both base/adapter evaluations on identical ordered item IDs, seeds,
tasks and labels matching the original local lock. `verify.py` uses #82's weight
verifier, recomputes scores/FPR and rejects empty generations or model errors.
An invalid model answer remains a legitimate scored failure, not a retry trigger.
Runtime CUDA observations and SHA-256 checks are not hardware attestation.

Collect `training/adapter/`, `training/receipt.json`, `qualification.json`,
`campaign-result.json`, both `items.jsonl`/`summary.json` files, setup/training/
evaluation logs, GPU observations, `execution.json`, `verification.json`,
`watchdog.json`, `checksums.json`, the original local lock, provider job status
and quota-before/after snapshots. All remain private and outside Git.

The campaign uses detection, root-cause and finding-support tasks and the first
up to 12 held-out fixes, one training seed (42), greedy evaluation seed 0. Report
per-task scores, Wilson intervals, false-positive rate, invalid JSON and paired
detection from its summaries. A small single-seed pilot establishes neither
general security competence nor frontier-model parity. No repository tests or
35B comparison run; nothing contacts Slink. Next, if the run qualifies, use the
same frozen split for seeds 7/13 in a separately bounded free-quota experiment.

CLI behavior was checked against the official Kaggle 2.2.5 distribution on
2026-10-28: `quota --format json`, `kernels push --accelerator`, private kernel
metadata, private dataset default, `kernels status` and `kernels output`.
Sources: <https://github.com/Kaggle/kaggle-cli>,
<https://pypi.org/project/kaggle/2.2.5/>. The provider priority comes from the
operator; no third-party provisioning or paid account was used.

## Pipeline changes since the original base (re-pinned 2026-10-30)

`SOURCE_BASE.json` pins the merged R02 branch (`670117a`), advanced to `10243e3` for the CWE grading fix and to `4c1417a` for the multi-function build option below. The previous pins are kept under `previous_base`. The core files changed in ways a remote run inherits:

- **Training (`train.py`).** The loss uses only answer-position logits. It equals the default loss (verified 3.067844 against 3.067844), and it fixes the out-of-memory error on an 8 GiB card at 1,536 tokens. LoRA targets now depend on the architecture: Qwen's projection names stay the default, and other students get `all-linear`. The #82 GPU-evidence and adapter-digest checks are kept.
- **Grading (`evaluate.py`, `build.py`).** A line-number gutter that the model copies onto every line of a patch is stripped before grading. Targets are restricted to self-contained fixes (scope analysis in `harvest.py`), with `--allow-non-self-contained-targets` to opt out. Tool-augmented and case-retrieval arms were added.
- **Promotion (`registry.py`).** A candidate must also beat the base on detection discrimination (recall − FPR). The first real GPU adapter (seed 42, 2026-10-30) collapsed to a constant answer. Its score rose and its FPR fell to 0, which the old gate would have accepted.
- **Repository evaluation (`repo_eval.py`).** It refuses to run without `--acknowledge-isolated-runner`.

- **CWE matching (`evaluate.py`, `10243e3`).** `root_cause` scoring and the detect `cwe_match` compare CWE identifiers (`CWE-<n>`) extracted from each answer rather than exact strings, so "CWE-22: Improper Limitation of a Pathname…" now matches `CWE-22`. `SOURCE_BASE.json` therefore anchors `10243e3` instead of `670117a`; `evaluate.py` is the only core file that differs between them, and the replaced hash is kept under `amendments`.

- **Multi-function fixes (`build.py --multi-function`, opt-in).** Focused fixes that changed 2-4 functions become training-only detect, root_cause and finding_support rows that show every changed function. Without the flag the build output is unchanged; dev, held-out and eval files never include them.
- **Recall guard (`registry.py`, `evaluate.py`, `gpu_campaign.py`, #99).** Promotion and the campaign's `improved_vs_base` also require detection recall not to fall below the base, and both evaluations must carry matching, nonempty positive and negative detection counts. A paired held-out run had risen from 33/72 to 35/72 overall while recall fell from 10/12 to 1/12. Summaries written before this change lack the counts and must be re-evaluated before a gated promotion.

The tasks and the dataset schema are unchanged.
