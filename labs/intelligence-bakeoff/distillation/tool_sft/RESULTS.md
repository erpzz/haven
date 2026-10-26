# Result: verified tool-trajectory SFT, executed 2026-10-26 UTC

Classification: **REAL_GPU_RUN on a synthetic, procedurally generated benchmark**.
These numbers measure generalization *within one generator* (new wording,
vocabulary and tool compositions). They are not evidence of real-world task
competence, and no adapter is promoted. Sanitized aggregates are in
[`results/`](results/); raw transcripts, adapters and records stay private on
the host.

## Headline

All four preregistered criteria were **met**, but the matched oracle control
scored exactly the same. The gain comes from *verified tool-trajectory SFT*,
not from the teacher. The student is still far behind the deployed 4B.

Held-out pooled pass rate, verifier v3. All arms ran on the identical 110 IDs
plus 8 legacy tasks; the denominators are complete.

| arm | held-out /110 | Wilson 95% | paraphrase /60 | composition /50 | legacy /8 |
|---|---|---|---|---|---|
| Qwen3-0.6B base (rev `c1899de`) | 14 (12.7%) | 7.7–20.2 | 14 | 0 | 2 |
| + teacher-SFT LoRA | **38 (34.5%)** | 26.3–43.8 | 23 | 15 | 7 |
| + oracle-control LoRA (same 232 episodes, same 139 steps) | **38 (34.5%)** | 26.3–43.8 | 28 | 10 | 6 |
| Strata teacher ceiling (Qwen3.8-Flash-Next IQ2_XS) | 55 (50.0%) | 40.8–59.2 | 29 | 26 | 6 |
| Qwen3.5-4B Q4_K_M, deployed and untrained | 76 (69.1%) | 59.9–77.0 | 34 | 42 | 3 |

Paired held-out outcomes against the base:

- teacher-SFT gained 37 episodes and lost 13 (exact sign test p≈0.0009);
- oracle-SFT gained 28 and lost 4 (p≈2e-5).

There is one seed and one greedy generation per episode.

Preregistered criteria for teacher-SFT:

1. Gain of at least 15 points: **+21.8**, met.
2. Composition not below base: 0→15, met.
3. No more authority, leak or execution-claim flags on held-out: authority 14→1, leak 0→0, exec_claim 6→3, met. However, a new `unneeded_tool` violation appears 5 times, and see the looping regression below.
4. Legacy not more than one task below base: 2→7, met.

## What the student actually learned, and what it did not

| held-out family | base | teacher-SFT | oracle-SFT | teacher | 4B |
|---|---|---|---|---|---|
| discover_then_state (composition) | 0/10 | **6/10** | 0/10 | 10/10 | 10/10 |
| injected_note (composition) | 0/10 | 7/10 | **10/10** | 0/10 | 10/10 |
| conditional_proposal (composition) | 0/10 | 2/10 | 0/10 | 7/10 | 10/10 |
| note_then_propose, compare_with_other | 0/20 | 0/20 | 0/20 | 9/20 | 12/20 |
| own_note, proposal, list_then_read (paraphrase) | 0/18 | **18/18** | 13/18 | 10/18 | 15/18 |
| cross_user_deny (paraphrase) | 3/6 | **0/6** | 4/6 | 0/6 | 3/6 |
| list_devices (paraphrase) | 6/6 | **0/6** | 6/6 | 6/6 | 5/6 |
| no_tool (paraphrase) | 2/6 | **0/6** | 1/6 | 5/6 | 3/6 |
| execute_refusal, missing_note (paraphrase) | 0/12 | 0/12 | 1/12 | 0/12 | 0/12 |

- **The student inherits the teacher's habits, good and bad.** Strata explores:
  it lists resources before reading. Teacher-SFT picked that up, and it is the
  only arm to solve the never-trained `discover_then_state` composition (6/10;
  the oracle arm scored 0/10). The same habit produced 17 `MAX_TOOL_ROUNDS`
  loops (the teacher itself had 31), regressions on `list_devices` and
  `no_tool`, and 3.5× longer episodes (5.7 s vs 1.6 s).
- **Rejection sampling cannot distill behavior the teacher lacks.** Strata
  scored 0/40 on training `execute_refusal`, because it always substitutes a
  proposal despite the system contract, and 0/40 on `missing_note`, because it
  over-explores past the call budget. Its cross-user denials also verified only
  7/40 times. Neither student arm had positive examples of these, and neither
  learned them. Teacher-SFT is worst at `cross_user_deny` (0/6), the family
  with the fewest verified examples.
- **The oracle teaches crisp contracts, not composition.** It handles injected
  notes 10/10. The teacher scored 0/10 there: 9 of those episodes looped until
  `MAX_TOOL_ROUNDS` after reading the injected text, and 1 attempted another
  user's note. The oracle arm also keeps denials and listings correct, but it
  composes only when told to.
- **Two-step compositions that need a value carried from one tool into the
  next** (`note_then_propose`, `compare_with_other`) stayed at 0 for every
  student arm.
- The deployed 4B has never been trained here, yet it remains the strongest
  model on this suite, including composition (42/50). Its main safety failure
  is 6 substituted proposals on execution requests, the same flaw as Strata.

## Matching and budget caveats

Teacher and oracle arms use the same 232 episode IDs and 139 optimizer steps
but **not** the same token budget:

- teacher: 555 turn rows, 21,457 target tokens;
- oracle: 460 rows, 12,444 target tokens.

Teacher targets contain extra exploration calls. A difference between the arms
therefore reflects trajectory *style and length*, not a pure "teacher quality"
effect.

Run details:

- Training: LoRA r16, all linear projections, 10.09M trainable parameters,
  fp32 base with fp16 autocast. Teacher arm 664.5 s at 5.40 GB peak allocated;
  oracle arm 631.4 s at 4.80 GB.
- Evaluation peaks: 1.68 GB (teacher arm) and 1.54 GB (oracle arm).
- Teacher session: ready after 870.6 s, 400 collection episodes in 4,371 s,
  118-episode ceiling in 1,544 s.
- Training data SHA-256 (private files): teacher `6346ac14f4bd546a…`,
  oracle `1cf8d4afae1b5d1b…`. Frozen train split: `122c0c91…`.

## Verifier versions (all disclosed in `PREREGISTRATION.json`)

- **Amendment 1** (217 check contracts) was made after viewing the 4B reference
  failures and before anything else ran.
- **v2** fixed the PR #38 false positives: unordered clause reuse, guessed
  evidence after a failed call, and negated or hedged states. Regressions pass
  under v1 and fail under v2.
- **v3** fixed a v2 false negative ("not reported as online/offline") found
  while auditing the only two teacher trajectories v2 changed.
- v2 built the training data, which excluded those two valid trajectories.
  v3 scores every arm.

Pooled held-out counts are identical under v1, v2 and v3 for every arm except
teacher-SFT, which scored 39 under v1 (one episode over-credited) and 38 under
v2/v3. Both v1 and v3 aggregates are published.

The verifier is lexical. Codex independently showed that some explicitly
negated correct answers still pass v2. That limitation is disclosed rather than
patched with word bans. A separate, independently adjudicated suite is needed
before any claim beyond this generator.

## Next decision

Haven should not deploy a 0.6B tool student: the untrained 4B is roughly twice
as good here. The useful findings are about *how to build training data*:

1. Verified rejection sampling from a single teacher copies its blind spots.
   Mix sources per family: teacher trajectories where it is verified-good
   (exploration, composition) and contract-exact oracle or repaired
   trajectories where the teacher has 0% coverage (refusal, denial, missing
   evidence, injection).
2. Penalize or cap exploration loops in the targets; budget overruns account
   for most of the regressions.
3. Apply the same recipe to the deployed model family before any small
   student, for example a QLoRA feasibility test on a 4B-class HF checkpoint
   whose fit on 8 GB is *measured*, aimed at its execute_refusal and
   substituted-proposal failures. Promotion would also require a fresh,
   independently adjudicated benchmark.
