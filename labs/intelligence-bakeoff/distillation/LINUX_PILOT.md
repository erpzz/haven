# Executed Linux LoRA pilot — 2026-10-25

The existing 0.6B recipe completed on CUDA. It did **not** improve synthetic
fact recall or compositional skill. The saved adapter remains an experiment;
Haven's GGUF inference model was neither trained nor replaced.

The [sanitized result](results/linux-pilot-20261025.json) records the pinned base,
data/probe hashes, precision, seed, elapsed time, CUDA peak allocation and all
group scores. Raw answers, logs, weights and adapter files remain private.

| Frozen group | Before | After |
| --- | --- | --- |
| Compositional skill | 0/4 | 0/4 |
| Learned-fact transfer | 0/3 | 0/3 |
| Retrieval-grounded | 1/2 | 2/2 |
| Unknown-fact control | 2/2 | 2/2 |

Three training examples contain invented facts with the answers already in the
training prompts. The low training loss demonstrates fitting that copying task;
the differently worded probes show no factual transfer. One changed retrieval
answer among two probes is not evidence of generalized improvement. Do not tune
the recipe against these frozen probes to manufacture a positive result.

## Reproduce a bounded run

Use an isolated Python 3.12 venv, with no GGUF/Strata engine loaded on the GPU.
Install `torch==2.8.0` from the official CUDA 12.8 wheel index, followed by
`requirements-pilot.txt`. The actual run resolved PyTorch `2.8.0+cu128`,
Transformers `4.56.2`, PEFT `0.17.1` and Accelerate `1.10.1`. Keep the resolved
dependency receipt locally. A full CUDA Toolkit, TRL and bitsandbytes are not
needed. See [official PyTorch wheels](https://pytorch.org/get-started/previous-versions/)
and the [Qwen model card](https://huggingface.co/Qwen/Qwen3-0.6B).

From this directory, with a **new private output directory** and operator
authorization for downloads/execution:

```sh
umask 077
pilot_dir="$HOME/.local/state/haven-admin/my-new-lora-pilot"
mkdir -p "$pilot_dir"
model_revision=c1899de289a04d12100db370d81485cdf75e47ca
python evaluate_hf.py --revision "$model_revision" --output "$pilot_dir/before.jsonl" --execute --allow-download
python train_sft.py --revision "$model_revision" --data fixtures/knowledge_sft.jsonl --output "$pilot_dir/adapter" --max-steps 40 --max-length 512 --seed 42 --execute
python evaluate_hf.py --revision "$model_revision" --adapter "$pilot_dir/adapter" --output "$pilot_dir/after.jsonl" --execute
python evaluate.py compare --before "$pilot_dir/before.jsonl" --after "$pilot_dir/after.jsonl"
```

Use one consistent `HF_HOME` for all commands if relocating the cache. The first
command explicitly permits the separate training checkpoint download; the later
commands use cached files only. `--execute` is required for each GPU operation.
The training base remains fp32 with fp16 Trainer autocast and LoRA q/v matrices;
evaluation uses fp16. Both use non-thinking templates and completion-only labels.
The 40-step training took 18.016 seconds, with 1,146,880 trainable parameters and
2,826,555,904 peak allocated CUDA bytes. It stayed inside an 8-GiB memory budget.

## Tool-use work and the next useful experiment

A separate real 4B GGUF run produced eight synthetic tool trajectories. The
original interface achieved 2/8 mechanical passes. The schemas omitted discoverable
resource identifiers, and a scorer rejected `executed: false` because of JSON
whitespace. The follow-up documents identifiers and preserves false semantics;
its one bounded run achieved 3/8 passes, 7/8 tool selections and 8/8 completed
transports. This changes the interface/scorer, so it is **not** a training delta.

The existing exporter retained two verified training rows, excluded two holdout
task IDs and left four failures in the private review queue. No failed trajectory
was approved as a target; no foresight or GKD run occurred. Two successful rows
are not a useful policy-training corpus. Improve tool contracts and gather a
larger consented, task-separated corpus before another adapter campaign.

Rollback is to unload the experiment and keep the base model. No merge into base
weights, deployment promotion, global Python change or background training timer
was performed. Keep the receipts when archiving an adapter; do not erase another
run's output or silently reuse its directory.
