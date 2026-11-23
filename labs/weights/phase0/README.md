# Weights Phase 0: CPU-only preparation for W1 and W2

**Status: BUILT AND TESTED ON CPU against [`PLAN.md`](../PLAN.md) (`667bd3a`, sha256 `119930a9…6720`) as amended by [`AMENDMENT_1.md`](../AMENDMENT_1.md) (`63bcd6e`, sha256 `cb7954a2…1a1b`).** No GPU time, no model inference, no teacher batch, no training. Workspace: [issue #123](https://github.com/erpzz/haven/issues/123); plan PR #124.

Nothing here may spend GPU time or send a teacher batch until all three of these are on record:
1. Astra 6.2's **DECISION:** sign-off on #123 of PLAN.md as amended.
2. An accepted M4 reserve commitment on #119. As of 2026-11-23 03:31 UTC, v1 and v2 are retired after review rejections, and v3 (`f2c817f1…9318`) is posted with no ACCEPT.
3. An independent human review of that reserve (#117), recorded on #119.

## What is here

| Piece | File | What it guarantees (tested) |
|---|---|---|
| Pinned harness | `deps.json`, `fetch_deps.py`, `common.py` | PR #115's checks, gateway, verifier and run-1 metrics, PR #118's tenant code, and every dev set, fetched by commit and sha256. A changed file is refused. The pinned full arm reproduces #115's guarantee: oracle 180/180, 179/179 and 179/179 kept. Every episode gets **three score views** (model-clean, corrected-model, final-system); weights claims use model-clean only. |
| HARE training generator | `gen_hare.py` | All 15 families, same contract as dev. Vocabulary disjoint from the dev generators. 2–5 new templates per family, each recorded as a **template id**. **Scenario groups** come first, with optional paired variants (same world, different wording) that always share a split. The secret seed and a **private pool manifest** are posted only as framed salted commitments. The **no-action share** is matched to the frozen public-dev rate. Every kept episode passes the oracle gate and dedupe, and groups are dropped whole. |
| Query-task generator | `gen_query.py` | Fresh Entra-style tenants whose user, group and SP ids are disjoint from the 84-question suite. Gold comes from #118's traversal. Three new phrasings per family. Kùzu runs every reference query, and each must match the Python gold. |
| Pools and splits | `pools.py`, `pools/dev_manifest.jsonl` | Frozen manifest of all 938 dev items across 8 pools: id, pool, family, template lineage, structure, scenario and entity group, paired variants, disposition, split. The frozen 180, the fresh 179s and the Purple suites stay identifiable. **No-action rate frozen at 0.1673** (90 of 538 public HARE dev episodes). |
| Dedupe | `dedupe.py` | Rejects a training item that shares, with any of 13 dev sources (1,584 items), any 8-token run, any entity id, the same **prompt lineage or whole-item structure**, or a **WL-equivalent tenant graph**. `check-general` checks the general-data mix against the pinned regression slice. `export-fingerprint` produces hashed fingerprints, so Astra can check reserve collisions privately and report only pass or fail. |
| Rule 8 pairs | `flip_pairs.py`, `rule8/evidence_flip_pairs.jsonl` | 66 evidence-flip pairs and 66 control pairs across 9 families, from a public dev seed, frozen. On flip pairs the request is byte-identical and one authoritative observation changes. Validated: the old answer fails on every flip and still passes on every control. |
| Arm O | `oracle_export.py`, `sft.py` | Scripted solver through the full harness. `--match` builds O_B and O_C on exactly B's or C's episode ids. **Per-episode weight cap**: each episode's kept traces share a total weight of 1.0. |
| Astra exchange | `astra_batch.py` | Stepwise, as Amendment 1 §5 requires (described below). |
| Regression config | `regression/` | IFEval (541), BFCL non-live AST plus irrelevance (1,240), MMLU-Pro (1,400 by id). Revisions and file hashes pinned. Rule 4 reads "2 absolute points per benchmark vs a paired stock baseline". Config only. |
| W1 Phase 1 notebook | `kaggle/` | Built, not run. 8 attempts per episode at T=0.7 in the full harness; keeps at most 2 per episode, weight-capped; lists hard episodes; reports G1 over all rollouts. Publishes throughput, peak VRAM, accelerator count, wall-hours, device-hours and per-episode coverage. Dry-run end to end on CPU against a fake server. |
| Manifest | `manifest.py`, `PHASE0_MANIFEST.json` | Hashes of everything above, tied to both preregistration commits. Also records the registered training seeds 1101, 2202 and 3303. |

## The stepwise teacher exchange (Amendment 1 §5)

- **Round 0**, one record per opaque id. It holds the system prompt and user turn exactly as the 4B sees them in the full harness, the tool catalogue, and the initially visible observations (none for HARE). No tool output and no gold is included. A framed, separately salted commitment to the gold manifest is posted along with the round-0 sha256 and the schema and tool versions.
- **Each round**, the teacher sends one line per open id: either one call, or its final record. `step` runs each call through the real gateway, dispatcher and advisory checks on the frozen fixture, and returns only that call's result, in the 4B's message format.
- **Final record**: the ordered calls (they must equal the session's), a disposition (`answer`, `insufficient_evidence`, `no_action_needed` or `refusal`; `clarification` is not allowed for HARE), a conclusion, and claims whose citations must be records the session actually returned.
- **Seal, then reveal.** After `seal`, no step is accepted, and gold can be revealed only after a seal exists. Replay recomputes every observation from the fixtures. A trace is kept only if it passes gold with zero blocked or duplicate calls, has no unreturned or future citation, its disposition agrees with its claims, and it matches its session. Correction is off, so a fallback rescue is never kept.
- **Audit**: `audit-sample` draws up to 50 kept traces without replacement, using an RNG keyed to the fixed kept-rows bytes.

## Run

```sh
cd labs/weights/phase0
python3 fetch_deps.py --regression        # pinned code, dev sets and regression files into _deps/ (gitignored)
pip install kuzu pyarrow                  # optional: Cypher oracle check; regression-text loader
python3 -m unittest discover -s tests -v  # 52 tests, CPU, about 7 s
python3 manifest.py --check && python3 pools.py --check && python3 flip_pairs.py check
```

Phase 1, after all gates. The private directory is owner-held and never inside Git:

```sh
python3 gen_hare.py generate --per-family 14 --private-dir ~/haven-private/w1 --label w1-pilot  # post the receipt on #123
# attach w1-pilot.episodes.jsonl as a private Kaggle dataset, set EPISODES_SHA256, run kaggle/w1_phase1_kaggle.ipynb
```

## Handback

- **Thread / task:** W1/W2 weight training, Phase 0, [#123](https://github.com/erpzz/haven/issues/123). Claude lead; the owner merges.
- **Base:** stacked on `claude/weights-plan-20261122` @ `63bcd6e` (PR #124: PLAN.md `667bd3a` and AMENDMENT_1.md `63bcd6e`), which is based on `main` @ `53387e7`.
- **Read inputs:** PLAN.md and AMENDMENT_1.md (sha256 verified); PR #115 @ `7f5af0d`; PR #118 @ `5276673`; PR #122 @ `cd15d57` (Purple dev files, read only); PR #95 @ `d87236d` (read, for the Phase 3 path); PR #45. File hashes are in `deps.json`.
- **Output paths:** `labs/weights/phase0/` only. New files; no existing file changed; no Codex file touched.
- **Requirements retained:** PLAN.md rules as amended by Amendment 1. This handback proposes no further amendment.
- **Publication:** public-safe. Synthetic data only. Seeds, salts, gold and training manifests before reveal are refused inside the repository (`common.private_dir`).
- **Review requested:** Astra 6.2 on #123; merge by the owner. No self-approval.

### Decisions

- **Dedupe parameters:** n = 8 tokens; entity ids as listed in `dedupe.py`; dates are values, not ids. Structure and lineage use typed placeholders, and graphs use 4-round WL. Fixed before any training data. Negative finding kept: the first template draft was rejected for 56 of 600 items, and six templates were reworded.
- **Dispositions come from the contract** (`pools.py`), so the no-action stratum and the opportunity sets for Rule 3 are fixed in advance.
- **W1 corrected attempts:** a verifier-rejected first answer is never a training target. Rows carry `corrected`, so an arm can drop them, and Astra may amend this. Teacher traces must also be model-clean.
- **Seeds are not drawn in Phase 0.** This session has no durable private store. The pilot seed is drawn at Phase 1 start, and its commitment is posted before sampling.
- **`bench_x.py` is pinned at the PR #115 head**, which carries the disclosed post-run false-refusal correction. `checks.py`, `enforce.py` and `bench_s0.py` match their registration.

### Acceptance (CPU, Python 3.13, this sandbox; reproduced from a fresh clone)

| Test | Expected | Actual |
|---|---|---|
| Pins; full-arm oracle on the dev sets | hashes match; 180/180, 179/179, 179/179 kept | PASS |
| HARE generator: 4 seeds × 60 per family, plus one seed with 3 variants | oracle kept, dedupe clean, vocabulary overlap ∅, variants share a world | PASS: 3,600/3,600 and 2,370/2,370 |
| Query generator (40 tenants) | Kùzu = Python gold; dedupe clean; ≤ 40% trivial | PASS: 280/280, 280/280, 23.6% |
| Dedupe controls | each source catches itself; dev prompt, id, principal and tenant user rejected; renamed dev episode caught by structure; relabelled dev tenant caught by the graph hash; 7-token overlap accepted, 8 rejected; regression items caught in the general mix | PASS |
| No-action rate | frozen from 538 public dev episodes; training matched | PASS: 0.1673; matched within 0.001 |
| Rule 8 pairs | 66 flip and 66 control; old answer fails on each flip and passes on each control; flip requests identical | PASS |
| Arm O | all exported, annotated, accepted raw; weights sum to 1.0 per episode | PASS |
| Stepwise exchange: oracle sessions (120, raw and `{proposal_id}` forms) | all kept | PASS: 120/120 twice |
| Stepwise exchange: corrupted sessions across 11 kinds, including **future citation with a correct conclusion** and **future identifier** | none kept | PASS: 0 of 1,092 kept |
| Stepwise exchange: protocol | round 0 shows no tool output or gold; each step shows only the call just made; violations close the session; seal before reveal; altered sealed session refused; framed commitment; audit sample deterministic without replacement | PASS |
| Notebook and runner | built, current, no outputs; CPU dry run: keep rule, weights, three views, G1, coverage, telemetry, resume | PASS |
| GPU, model, teacher, training | not run | NOT_EXECUTED |

### Risks and open questions

1. **Rule 4 noise.** IFEval has 541 prompts. If about 10% of prompts flip between models, the standard deviation of the difference is about 1.4 points, so a 2-point drop can occur by chance. Uncertainty will be published beside each delta, as amended. Astra may want a decision on whether the margin is applied to point estimates alone.
2. **The stepwise exchange takes up to 6 round trips per batch** on #123, all batched per round. This is slower than a single bundle, but it is what §5 requires.
3. **Query-task training may add little.** Code alone scores 84/84 on the templated dev suite. The reserve decides.
4. **Owner decision needed: where the private directory lives** (seeds, salts, gold and training manifests before reveal).

### Next package

Phase 1 only, after all three gates, including an accepted M4 v3 or later:
1. Generate the pilot episodes from a fresh secret seed and post the receipt.
2. Run the notebook (about 3 device-hours).
3. Post G1 over all rollouts, coverage, the three views and the measured telemetry on #123.
4. Re-cost the remainder inside the 50 device-hour cap.
5. Stop at G1.
