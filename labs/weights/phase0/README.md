# Weights Phase 0: CPU-only preparation for W1 and W2

**Status: BUILT AND TESTED ON CPU. No GPU time, no model inference, no teacher batch, no training.**
This is Phase 0 of [`labs/weights/PLAN.md`](../PLAN.md) (preregistered at `667bd3a`, sha256 `119930a9…6720`; draft PR #124). Workspace: [issue #123](https://github.com/erpzz/haven/issues/123).

Nothing here may spend GPU time or send a teacher batch until both gates are met:
1. Astra 6.2 posts a **DECISION:** sign-off on PLAN.md on #123.
2. The M4 reserve's salted digest is posted on #119.

## What is here

| Piece | File | What it guarantees (tested) |
|---|---|---|
| Pinned harness | `deps.json`, `fetch_deps.py`, `common.py` | PR #115's checks/gateway/verifier and run-1 metrics, PR #118's tenant code, and the dev sets are pulled by exact commit and sha256. A changed file is refused. The pinned full arm reproduces #115's guarantee: oracle 180/180, 179/179 and 179/179 kept. |
| HARE training generator | `gen_hare.py` | All 15 families, same contract as the dev suite. New vocabulary (no item shared with `generator.py` or `tool_sft/world.py`), and 2–5 new prompt templates per family. The seed is secret and committed by salted SHA-256. An episode is kept only if the scripted oracle passes under the full harness and dedupe finds no overlap. |
| Query-task training generator | `gen_query.py` | Fresh Entra-style tenants with new user and team pools, so every user, group and SP id is disjoint from the 84-question suite. Gold comes from #118's traversal code. Three new phrasings per family. Kùzu runs every reference query, and each must match the Python gold. |
| Dedupe | `dedupe.py` | An item is rejected if it shares any 8-token run, or any entity id, with any of 12 development sources (1,320 items). Fingerprint `37340866…8555`. |
| Arm O exporter | `oracle_export.py`, `sft.py` | Runs the generator's scripted solver through the full harness, so rows carry the annotations the 4B sees. Supports `--match` for a control matched to another arm's episodes. Accepts training ids only. |
| Astra batches | `astra_batch.py` | Export: up to 50 records with no gold, family, seed or source id, salted ids, shuffled order, an evidence bundle per record, and a salted gold commitment. Replay: answers go through the real gateway, verifier and adjudicator, with the same keep rule as every teacher. |
| Regression config | `regression/` | IFEval (541), BFCL non-live AST plus irrelevance (1,240) and an MMLU-Pro slice (1,400, fixed by id). Revisions and file hashes are pinned. Config only. |
| W1 Phase 1 notebook | `kaggle/` | Built, not run. 8 attempts per episode at T=0.7 in the full harness; keeps at most 2 per episode; lists hard episodes; reports gate G1. Tested end to end on CPU against a fake server. |
| Manifest | `manifest.py`, `PHASE0_MANIFEST.json` | Hashes of everything above, tied to PLAN.md's preregistration commit. |

## Run

```sh
cd labs/weights/phase0
python3 fetch_deps.py                                  # pinned files into _deps/ (gitignored)
pip install kuzu                                       # optional: Cypher oracle check for query tasks
python3 -m unittest discover -s tests -v               # 42 tests, CPU, about 10 s
python3 manifest.py --check
python3 dedupe.py fingerprint
```

Phase 1, after both gates (owner-held private directory, never inside Git):

```sh
python3 gen_hare.py generate --per-family 14 --private-dir ~/haven-private/w1 --label w1-pilot   # post the commitment + sha256 on #123
# attach w1-pilot.episodes.jsonl as a private Kaggle dataset; set EPISODES_SHA256; run kaggle/w1_phase1_kaggle.ipynb
python3 astra_batch.py export --episodes ~/haven-private/w1/w1-pilot.episodes.jsonl --ids HARD.txt \
    --label b1 --private-dir ~/haven-private/w1 --out b1.jsonl             # post b1.jsonl + gold commitment on #123
python3 astra_batch.py replay --private-dir ~/haven-private/w1 --label b1 --answers b1.answers.jsonl --out-dir R
python3 astra_batch.py reveal --private-dir ~/haven-private/w1 --label b1 --out b1.gold.json   # then post it
```

## Exchange format, as built

- **To Astra**, one JSONL record per episode:
  - `system` and `user`: exactly what the 4B gets, including the claims instruction.
  - `tools`: the tool catalogue.
  - `evidence_bundle`: every successful output the episode can return (devices, readable note lists, readable notes, device states), computed by the real dispatcher, plus the deterministic default for every other call. Notes the principal cannot read are never listed.
  - `answer_schema`.
- **From Astra**, one JSONL record per episode: `id`, `tool_calls` (ordered, at most 5), `conclusion`, `claims`, and an optional `verdict` (answered / insufficient evidence / no action needed / refused) used only for the audit. Proposal ids are written as `{proposal_id}`; the replayer fills them in.
- **Replay** settings: advisory checks, gateway and verifier on; correction off, because a fixed answer cannot revise. A trace is kept only if it has an adjudicator pass, zero blocked or duplicate calls, and transport ok. That is the same rule used for W1 and every other teacher.

## Handback

- **Thread / task:** W1/W2 weight training, Phase 0, [#123](https://github.com/erpzz/haven/issues/123). Claude lead; the owner merges.
- **Base:** stacked on `claude/weights-plan-20261122` @ `667bd3a` (PR #124), which is based on `main` @ `53387e7`.
- **Read inputs:** PLAN.md (sha256 verified); PR #115 @ `7f5af0d`; PR #118 @ `5276673`; PR #122 @ `cd15d57` (Purple Copilot dev files, read only); PR #95 @ `d87236d` (forge kernel, read for the Phase 3 path); PR #45 (oracle-control lesson). File hashes are in `deps.json`.
- **Output paths:** `labs/weights/phase0/` only. New files; no existing file changed; no Codex file touched.
- **Requirements retained:** PLAN.md decision rules 1–7 are unchanged; no amendment is proposed here.
- **Publication:** public-safe. Synthetic data only; no credentials, hosts or private data. Seeds, salts and gold before reveal are refused inside the repository (`common.private_dir`).
- **Tests:** commands above. Expected and actual results are in the Acceptance section.
- **Review requested:** Astra 6.2 on #123; merge by the owner. No self-approval.

### Decisions

- **Dedupe:** n = 8 tokens; entity ids as listed in `dedupe.py`; dates are values, not ids. Fixed before any training data. The first template draft was rejected for 56 of 600 items (negative finding, kept). Six templates were reworded until 3,600 of 3,600 test-seed items passed.
- **W1 corrected attempts:** a verifier-rejected first answer is never a training target. It stays in the prefix of the corrected turn. Rows are tagged `corrected`, so an arm can drop them. Astra may amend this.
- **Seeds are not drawn in Phase 0.** This session has no durable private store. The real pilot seed is drawn at Phase 1 start, and its commitment and the episode sha256 are posted before sampling.
- **`bench_x.py` is pinned at the PR #115 head**, which carries the disclosed post-run false-refusal correction, not at its registered hash. `checks.py`, `enforce.py` and `bench_s0.py` match the registration.

### Acceptance (CPU, Python 3.13, this sandbox)

| Test | Expected | Actual |
|---|---|---|
| Pins and full-arm oracle on the dev sets | all hashes match; 180/180, 179/179, 179/179 kept | PASS |
| HARE generator (4 seeds × 60 per family = 3,600) | oracle kept 100%; dedupe 100% clean; vocabulary overlap ∅ | PASS: 3,600 / 3,600 / ∅ |
| Query generator (40 tenants, 280 questions) | Kùzu = Python gold; dedupe clean; ≤ 40% trivial | PASS: 280/280, 280/280, 23.6% |
| Dedupe controls | each source catches itself (label-only source excepted and asserted); dev prompt, dev device id, dev principal and dev tenant user rejected; 7-token overlap accepted, 8 rejected | PASS |
| Arm O | all 120 episodes exported, annotated, accepted raw; `--match` restricts; dev ids refused | PASS |
| Astra oracle answers (120, raw and `{proposal_id}` forms) | all kept | PASS: 120/120 twice |
| Astra corrupted answers: status swap, forged evidence, dropped calls, unauthorized proposal, duplicate call, wrong or decoy value | none kept | PASS: 0 of 616 kept |
| Bundle | equals the dispatcher on every oracle call; never shows an unreadable note; no gold, family, seed or source id | PASS |
| Commitments | verify; tampered gold fails | PASS |
| Notebook | built, current with the code, no outputs; refuses to run without the posted hash | PASS |
| Phase 1 runner, CPU dry run with a fake server | keep rule, ≤2 per episode, hard episodes, G1 number and resume all correct | PASS |
| GPU, model, teacher, training | not run | NOT_EXECUTED |

### Risks and open questions

1. **Rule 4 noise.** IFEval has 541 prompts. If about 10% of prompts flip between two models, the standard deviation of the difference is about 1.4 points, so a 2-point drop can occur by chance. Across three benchmarks, a false stop is plausible. The rule stays as written; Astra may amend it before GPU time.
2. **Regression runs are not in the 36 GPU-hour estimate.** Rough estimate: 3–6 hours for the base model plus five arms.
3. **Evidence bundles show every readable record at once.** The 4B sees them call by call. This comes from offline answering, and Astra's traces still pass the same replay.
4. **Query-task training data may add little.** Code alone scores 84/84 on the templated dev suite (#118). The reserve decides.
5. **Owner decision needed: where the private directory lives** (seeds, salts, gold before reveal). For example, the owner's machine plus a private Kaggle dataset.

### Next package

Phase 1 only, and only after both gates:
1. Generate 210 pilot episodes (14 per family) from a fresh secret seed; post the commitment and the sha256.
2. Run the notebook (about 3 GPU hours on Kaggle).
3. Report G1 (15–85%), per-family solve rates and hard-episode count on #123.
4. Stop at G1.
