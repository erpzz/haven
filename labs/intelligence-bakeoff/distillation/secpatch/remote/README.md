# R02 external GPU execution package

Status on 2026-10-28: **BLOCKED / NOT_EXECUTED**. No adapter or model-quality
result is claimed. This package wraps the merged #75/#82/#84 pipeline without
changing its architecture, tasks, training recipe, graders or promotion rules.

## Connection blocker

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

The real secpatch dataset and original OSV/harvest provenance are also absent.
The checked-out repository has unrelated synthetic fixtures, which are **not**
substitutes. Supply the original private data and provenance files to `prepare.py`.
Dataset size, qualification and scientific validity remain unknown until then.

## Existing gates and qualification limits

The unchanged `gpu_campaign.qualify_data` requires >=25 distinct train fix keys,
>=8 held-out fix keys, disjoint train/held-out repositories and keys, recorded
commit/parent/advisories, one of the existing permissive licenses, verification
flags, train-only targets, held-out prompts without assistant answers and a
grader. Fix-key counts are not proof of statistical independence.

Before creating a payload, `prepare.py` additionally hashes the original OSV
archive and replays **the existing `build.py`**, with original candidates,
harvest order, Bandit 1.9.4, cutoff 2025-07-01 and near-duplicate threshold 0.8.
All seven data files and the manifest (except `built_at`) must reproduce.
This exercises the actual repository hash partition, time split, normalized-AST
deduplication and training-to-dev/held-out vulnerable-function similarity filter.
Original per-fix license filenames, commit identities and advisory attribution
are retained in the private payload. No data is harvested, fabricated or relabeled
by this wrapper. No original training/evaluator file is edited.

This reproduces pipeline provenance; it does not independently authenticate a
maliciously forged source collection or constitute legal review. The existing
license classifier is heuristic. Check license text **at each fix commit** and
OSV advisory licensing/attribution if upstream provenance is incomplete; stop if
unresolved. The deduplication policy concerns vulnerable functions, not all
possible semantic or fixed-code leakage. The cutoff does not prove absence from
the pretrained model's undisclosed training corpus.

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
  --osv-archive /private/original/raw/pypi-all.zip \
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
