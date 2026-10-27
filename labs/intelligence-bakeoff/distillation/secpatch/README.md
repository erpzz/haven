# secpatch: R02 security-specialist dataset, training and evaluation

This is the next R02 stage after [PR #45](https://github.com/erpzz/haven/pull/45). That experiment showed a 0.6B
student can learn a narrow synthetic tool task (14 → 38 of 110 held out), but its oracle control matched the teacher
and an untrained 4B scored 76. secpatch replaces the synthetic world with **real security fixes from open-source
Python projects**. Targets come from recorded ground truth, never from a model:

| source | used for | license recorded per row |
|---|---|---|
| OSV.dev PyPI export (GHSA, PyPA advisories) | advisory id, CWE, summary, details, publish date | CC-BY-4.0 |
| The fix commit and its parent on GitHub | vulnerable and fixed function, commit message, tests added by the fix | repo license **at the fix commit**, permissive only |
| Bandit 1.9.4, executed | which rule fires on the vulnerable version and stops firing on the fix | tool output |

Hosted assistants (Claude, GPT) wrote this code. None of their outputs are training targets or graders.

## Pipeline

All paths below are private host state (`~/.local/state/haven-secpatch` on Slink). Data, adapters and evaluation
outputs stay out of Git.

```bash
S=~/.local/state/haven-secpatch; C=$S/code/secpatch; B=~/.local/share/haven-secpatch-venv/bin/bandit
curl -o $S/raw/pypi-all.zip https://osv-vulnerabilities.storage.googleapis.com/PyPI/all.zip
python3 $C/osv.py --archive $S/raw/pypi-all.zip --out $S/candidates.jsonl
python3 $C/harvest.py --candidates $S/candidates.jsonl --out $S/harvest-0.jsonl --work $S/git-0 \
  --per-repo 12 --exclude-repo tensorflow/tensorflow --shard 0/4   # run shards 0..3 in parallel; resumable
python3 $C/build.py --candidates $S/candidates.jsonl --harvest $S/harvest*.jsonl --out $S/data --bandit $B
```

The harvester fetches only the fix commit and its parent (shallow, blobless) and runs nothing from the repository.
A record becomes training data only when all of these hold: one parent; a permissive license
(MIT, BSD-2/3, Apache-2.0, ISC, PSF-2.0, 0BSD, Unlicense) found in the tree at the fix; exactly one non-test
function changed in a non-cosmetic way (AST-compared); and both versions parse.

### Splits and leakage controls

* **Repository isolation:** `sha256(repo) mod 5 == 0` puts a repository in the held-out set. No code from a held-out
  repository is ever trained on, including that repository's fixes from before the cutoff.
* **Time isolation:** training uses advisories published before `--cutoff` (default 2025-07-01, after Qwen3's
  release). `dev` = training repositories after the cutoff (time only); `heldout` = held-out repositories after the
  cutoff (repository and time).
* **Deduplication:** exact duplicates by normalized AST; a training function within 0.8 token-5-gram Jaccard of any
  dev or held-out function is dropped from training.
* **Per-period cap:** at most 12 advisories per repository before and after the cutoff, so a few large projects
  do not dominate. TensorFlow is excluded because its fixes are almost entirely C++.

### Task rows

Every row carries `source` (repo, commit, parent, path, function, code license, advisory ids and licenses) and
`verification`.

| task | input | target (ground truth) |
|---|---|---|
| `detect` | vulnerable **or** fixed function | JSON verdict, CWE, changed lines (paired: both versions of each fix) |
| `root_cause` | vulnerable + fixed function | advisory CWE and text, fix commit subject |
| `remediate` | vulnerable function + reported issue | the recorded fixed function |
| `regression_test` | both versions + issue | a test function the fix commit added |
| `tool_select` | vulnerable function | the Bandit rule that actually fired on it and not on the fix |
| `finding_support` | a finding + vulnerable / fixed / decoy-name code | supported, stale (already fixed) or unsupported (cites absent code) |
| recovery events | — | logged by `repo_eval.py` when an install or test step fails and a later step recovers |

## Training

`train.py` is completion-masked LoRA SFT (QLoRA with `--qlora` for 1.5B–4B students). It refuses rows from any split
other than `train`, never truncates a target, checkpoints every `--save-steps` and resumes with `--resume`. It writes
`receipt.json` (data digest, task counts, base revision, hyperparameters, loss log, wall time, peak memory).

```bash
# CPU pipeline check (capped at 3 steps; not a training run)
CUDA_VISIBLE_DEVICES= HF_HOME=~/.local/share/haven-training-cache HF_HUB_OFFLINE=1 \
  ~/.local/share/haven-training-venv/bin/python $C/train.py --data $S/data/train.jsonl \
  --revision c1899de289a04d12100db370d81485cdf75e47ca --output $S/runs/cpu-check --device cpu --max-steps 2 --batch 2 --execute

# GPU training run: needs an approved GPU window (nothing else on the GPU)
HF_HOME=~/.local/share/haven-training-cache HF_HUB_OFFLINE=1 \
  ~/.local/share/haven-training-venv/bin/python $C/train.py --data $S/data/train.jsonl \
  --revision c1899de289a04d12100db370d81485cdf75e47ca --output $S/runs/qwen3-0.6b-secpatch-s42 \
  --device cuda --epochs 2 --batch 8 --seed 42 --execute
```

Repeat with `--seed 7` and `--seed 13` for the multiple-seed comparison.

## Evaluation

`evaluate.py` grades deterministically against recorded ground truth and re-runs Bandit on generated patches.
Arms, all on the identical `eval-heldout.jsonl` items:

```bash
E="python3 $C/evaluate.py --eval $S/data/eval-heldout.jsonl --bandit $B"
$E --backend hf --model Qwen/Qwen3-0.6B --revision c1899de... --out $S/eval/base            # untuned student
$E --backend hf --model Qwen/Qwen3-0.6B --revision c1899de... --with-tools --out $S/eval/base-tools
$E --backend hf ... --adapter $S/runs/<run>/adapter --out $S/eval/<run>                     # tuned student
$E --backend hf ... --adapter $S/runs/<run>/adapter --with-tools --out $S/eval/<run>-tools
$E --backend openai --base-url http://127.0.0.1:8877/v1 --key-file <gateway key> --model haven-slink --out $S/eval/35b
```

Reported per arm: per-task accuracy with Wilson intervals, detection recall, false-positive rate on fixed code,
paired detection (both versions of a fix right), CWE match, unsupported-assertion rate (cites a function or line
not shown), invalid JSON, Bandit-cleared remediations, latency, tokens and peak memory.

`repo_eval.py` is the repository-level experiment: for held-out fixes that shipped tests, it validates the fix's own
regression test (passes on the fix, fails on the vulnerable parent), then runs it against the recorded fix
(positive control) and each model's remediation.

## Promotion and rollback

```bash
R="python3 $C/registry.py --root $S/adapters"
$R register $S/runs/qwen3-0.6b-secpatch-s42 secpatch-0.6b-v1     # GPU runs only; names are immutable
$R attach-eval base $S/eval/base/summary.json
$R attach-eval secpatch-0.6b-v1 $S/eval/qwen3-0.6b-secpatch-s42/summary.json
$R promote secpatch-0.6b-v1 <eval_sha256>   # refused unless it beats base and FPR does not rise
$R rollback                                 # previous promoted adapter (or none)
$R card --manifest $S/data/manifest.json --out $S/specialist-card.json   # what the Haven gateway reads
```

Nothing is deployed by promotion. Serving needs the adapter converted to GGUF and loaded with `llama-server --lora`,
then routed through the Haven gateway (issue #70), which keeps user identity, scheduling and receipts.

## Limits

* Bandit flags only a small share of real vulnerabilities, so `tool_select` rows are few. A Bandit miss is not proof
  of safety.
* The fixed version is labeled `not_vulnerable` *for the reported issue*; it may contain other weaknesses.
* Repository tests run without kernel network isolation: this host forbids unprivileged user namespaces
  (`kernel.apparmor_restrict_unprivileged_userns=1`). Enabling bubblewrap is an owner security decision.
* Python only. C/C++ fixes (most of TensorFlow, Pillow's C code) need a different extractor.
