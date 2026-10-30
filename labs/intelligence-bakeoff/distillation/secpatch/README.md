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
python3 $C/harvest.py --rescan $S/harvest*.jsonl --work-dirs $S/git $S/git-[0-3] --out $S/scope.jsonl   # records from before scope analysis
python3 $C/build.py --candidates $S/candidates.jsonl --harvest $S/harvest*.jsonl --scope $S/scope.jsonl --out $S/data-v2 --bandit $B
```

The harvester fetches only the fix commit and its parent (shallow, blobless) and runs nothing from the repository.
A record becomes training data only when all of these hold: one parent; a permissive license
(MIT, BSD-2/3, Apache-2.0, ISC, PSF-2.0, 0BSD, Unlicense) found in the tree at the fix; exactly one non-test
function changed in a non-cosmetic way (AST-compared); and both versions parse.

**Self-contained fixes (v2).** A fix that changes one function may still add a helper, an import or a constant, or
edit another source file. Then the fixed function alone is not a working patch: the repository-level positive
control failed for exactly those fixes (`name '_resolved_path_is_within' is not defined`, `name 'os' is not
defined`). The harvester records this scope, and v2 emits `remediate` and `regression_test` rows only from
self-contained fixes (`--allow-non-self-contained-targets` restores v1). Every row's `verification` carries
`self_contained` and `fix_scope`. Detection, finding-support and root-cause rows use every verified fix.

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
| recovery events | — | logged by `repo_eval.py` when an install or test step fails and a later step recovers (none in v2: the only runs were on held-out repositories) |

## Training

`train.py` is completion-masked LoRA SFT (QLoRA with `--qlora` for 1.5B–4B students). It refuses rows from any split
other than `train`, never truncates a target, checkpoints every `--save-steps` and resumes with `--resume`. It writes
`receipt.json` (data digest, task counts, base revision, hyperparameters, loss log, wall time, peak memory).

```bash
# CPU pipeline check (capped at 3 steps; not a training run)
CUDA_VISIBLE_DEVICES= HF_HOME=~/.local/share/haven-training-cache HF_HUB_OFFLINE=1 \
  ~/.local/share/haven-training-venv/bin/python $C/train.py --data $S/data/train.jsonl \
  --revision c1899de289a04d12100db370d81485cdf75e47ca --output $S/runs/cpu-check --device cpu --max-steps 2 --batch 2 --execute

# Approved GPU window: 3 seeds, held-out eval of each adapter (plain and with tools), same-device base arm, registry
$C/gpu_window.sh --approved "<who approved, when>"
```

`gpu_window.sh` refuses to start without an approval note, while any process holds the GPU, or while Strata is
active, and it never stops anything. Measured on Slink's CPU (8 threads), one optimizer step at batch 2 took about
100 s, so CPU training is a pipeline check only.

### Single-command real GPU campaign

Use `gpu_campaign.py` when the goal is **real** small-model training and
independent evaluation, not a synthetic diagnostic. It refuses an empty or
unsourced dataset, fewer than 25 distinct historical train fixes or 8 held-out
fixes, license/verification gaps, repository leakage, unavailable CUDA and
less than 4 GiB of free GPU memory. It never unloads or restarts Haven's 35B.
The model revision below is the published immutable Qwen3-0.6B commit
(`c1899de289a04d12100db370d81485cdf75e47ca`).

First harvest and build the **real** dataset described above; keep it and
the pretrained model's pinned cache private. Then:

```bash
S="$HOME/.local/state/haven-secpatch"
C="$HOME/projects/haven/labs/intelligence-bakeoff/distillation/secpatch"
PY="$HOME/.local/share/haven-training-venv/bin/python"
export HF_HOME="$HOME/.local/share/haven-training-cache" HF_HUB_OFFLINE=1
"$PY" "$C/gpu_campaign.py" --data "$S/data" \
  --output "$S/runs/real-cuda-$(date +%Y%m%dT%H%M%S)" \
  --model Qwen/Qwen3-0.6B \
  --revision c1899de289a04d12100db370d81485cdf75e47ca \
  --execute
```

The run writes `qualification.json`, live subprocess logs, CUDA-observed
`training/receipt.json`, actual hashed PEFT adapter bytes, an unchanged-base
held-out summary, an adapter held-out summary, and `campaign-result.json`.
It evaluates the same first 12 held-out fixes in each arm (detection,
root-cause and finding-support tasks), and **does not** auto-promote a
model. A winning adapter is a candidate for further independent validation,
not a production deployment. A failed run retains its partial output and
fails visibly; use a fresh run directory rather than inventing a receipt.

The GPU-memory check is conservative but not a GPU lease. Coordinate with
Haven's existing Model Lab scheduling before starting, particularly if the 35B
is in active use. Offline CI exercises only admission logic and never claims
to have run a CUDA optimizer.

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

To compare arms run on different task subsets, re-score from the per-item files over shared ids:
`report.py --items $S/eval/a/items.jsonl $S/eval/b/items.jsonl --tasks detect,finding_support`.

Reported per arm: per-task accuracy with Wilson intervals, detection recall, false-positive rate on fixed code,
paired detection (both versions of a fix right), CWE match, unsupported-assertion rate (cites a function or line
not shown), invalid JSON, Bandit-cleared remediations, latency, tokens and peak memory.

`repo_eval.py` is the repository-level experiment: for held-out fixes that shipped tests, it validates the fix's own
regression test (passes on the fix, fails on the vulnerable parent), then runs it against the recorded fix
(positive control) and each model's remediation.

**Isolation gate:** Use `repo_eval_guarded.py` for future untrusted repository evaluations; the original `repo_eval.py` remains byte-for-byte pinned by `remote/SOURCE_BASE.json`. See [RUNNER_CONTRACT.md](RUNNER_CONTRACT.md) for the independent
disposable guest requirements, required real confinement probes and the offline
wheelhouse preflight (`--wheelhouse`). This component clones, installs, and executes third-party Python
projects. A virtual environment, scrubbed HOME, and proxy settings are not an
OS sandbox. The CLI now refuses execution by default. Only invoke it from a
disposable VM or equivalently isolated container with no mounted host secrets,
restricted network access, and independent resource limits. There, supply
`--acknowledge-isolated-runner` explicitly after checking the runner. The flag
records an operator acknowledgment; it does **not** create isolation itself.
The evaluator now rejects malformed repository/revision/source/test identifiers,
symlinked source/test paths, and missing offline wheels before untrusted install.
It still requires a separately verified OS-enforced network and filesystem boundary.
Normal dataset harvesting, static checks, trainer dry runs, and evaluator unit
tests do not require this flag.

## Promotion and rollback

```bash
R="python3 $C/registry.py --root $S/adapters"
$R register $S/runs/qwen3-0.6b-secpatch-s42 secpatch-0.6b-v1     # GPU runs only; names are immutable
$R attach-eval base $S/eval/base/summary.json
$R attach-eval secpatch-0.6b-v1 $S/eval/qwen3-0.6b-secpatch-s42/summary.json
$R promote secpatch-0.6b-v1 <eval_sha256>   # refused unless it beats base and FPR does not rise
$R rollback                                 # previous promoted adapter (or none)
$R card --manifest $S/data-v2/manifest.json --out $S/specialist-card.json   # what the Haven gateway reads
```

Nothing is deployed by promotion. Serving needs the adapter converted to GGUF and loaded with `llama-server --lora`,
then routed through the Haven gateway (issue #70), which keeps user identity, scheduling and receipts.

## Limits

* Bandit flags only a small share of real vulnerabilities, so `tool_select` rows are few. A Bandit miss is not proof
  of safety.
* The fixed version is labeled `not_vulnerable` *for the reported issue*; it may contain other weaknesses.
* `repo_eval.py` needs a disposable OS-isolated runner and refuses to run without `--acknowledge-isolated-runner`.
  Slink has none today: unprivileged user namespaces are blocked (`kernel.apparmor_restrict_unprivileged_userns=1`),
  `slinky` is not in the `docker` group, and LXD is not initialized. One validation pass ran on the host before the
  gate existed (see RESULTS.md). Choosing and provisioning the runner is an owner decision.
* Training data has 125 remediation targets (self-contained fixes only) and no recovery rows yet.
* Python only. C/C++ fixes (most of TensorFlow, Pillow's C code) need a different extractor.
