# System One: real Haven task-routing pilot

**Status: RESEARCH, NOT PROMOTED.** A real linear PyTorch classifier was
trained on historical Haven work, but simple deterministic rules outperformed
it on the chronological held-out split. It is not a Jev/Clef checkpoint.

## Question and provenance

Can a tiny learned decision head select the appropriate Haven subsystem
(inference/model lab, model training/evaluation, or orchestration/executor)
without invoking a large model?

This dataset contains 36 real GitHub Haven pull requests, each with a source
link. The label is assigned from the predominant changed-code path. We
excluded doc-only and highly ambiguous changes. This is a path-based proxy
label, not a verified tool-completion outcome.

Only the PR title is used as input. No paths, PR number, source URL, label,
or future test-set features are included in the trained vocabulary.

- 25 earlier PRs (up to #64): training.
- 3 PRs (#65, #66, #68): validation, orchestration only.
- 8 newer PRs (#74–81): chronological test, inference and training only.

Some related stacked PRs are correlated. The dataset is tiny, imbalanced and
specific to one repository; it does not establish cybersecurity competence,
general routing ability, or calibrated confidence.

## Actual experiment (2026-10-27 Eastern / 2026-10-28 UTC)

- PyTorch 2.10.0+cpu; one CPU thread; seeded AdamW bag-of-words/bigrams
  (401 vocabulary items), 3 classes; 350 actual gradient updates.
- Initial train cross-entropy: 1.109034. Final: 0.000225.
- Validation: learned 2/3, rules 2/3.
- **Held-out: learned 6/8 (75%), deterministic rules 7/8 (87.5%).**
- Threshold 0.55: accepted 3/8 predictions, 2/3 correct; abstained on 5/8.
- Dataset SHA-256: ec94c3ecf8be02603a055eafcb31ca7a79bc11aee4f1243f74f122250825e371.
- Research checkpoint SHA-256: fcc0464c55e2dc9bbafeaf5c3fcf75ebf3e42eca0b8acacd36c013a57a17db19.
- Evaluation JSON SHA-256: 5a3c584b0d9a4acf8317dbf71d33bcc23c08a60bce294172a8ce4b853fcdb39e.

**No GPU run occurred.** The execution environment exposed only CPU PyTorch.
Hugging Face Jobs for the connected free account are metered; DigitalOcean
has no active instances or positive balance. No paid workload was started.
The unpromoted checkpoint and full evaluation were saved as a downloadable
experiment artifact; Git tracks the trainer, data and test harness only.

## Reproduction

From the repository root, in a Python environment with PyTorch installed:

    python3 labs/engineer/router_lab/train_router.py train \
      --data labs/engineer/router_lab/data/haven_pr_routes_20261027.jsonl \
      --output /tmp/haven-router-checkpoint.json \
      --report /tmp/haven-router-report.json \
      --device cpu --epochs 350 --seed 1729

    python3 -m unittest discover -s labs/engineer -p 'test_router.py' -v

    python3 labs/engineer/router_lab/train_router.py predict \
      --model /tmp/haven-router-checkpoint.json \
      "Fix the Open WebUI authentication gateway"

On a separately authorized CUDA machine, switch only to --device cuda. The
trainer refuses unavailable CUDA instead of reporting a CPU run as GPU.
It does not alter Slink's loaded model or any remote worker.

This prototype is a recommendation-only research module: it **never**
executes code, grants access, selects paid providers or takes GPU leases.

## Next training data that actually matters

Collect executed Haven tasks with verifiable completion results, tool choices,
candidate models, authorization scopes, resource availability, latency,
cost and independent checks. Keep task families segregated across training
and evaluation. A follow-up is justified when there is enough real evidence
to beat deterministic heuristics, not merely because free GPU time exists.

Do not auto-promote this checkpoint into the production scheduler.
