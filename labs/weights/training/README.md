# Episode-normalized trainer loss contract

This package closes the pre-training weighting gate recorded on Haven issue #123 and the Phase 0 candidate #152.

It does **not** train a model, load a model, spend GPU time, or alter the already-approved W1 Phase-1 collection notebook.

## Frozen requirement

For every supervised episode:

- total optimization weight = **1.0**;
- if the episode has N kept traces, each trace receives **1/N**;
- a trace's contribution must not increase because it has more assistant turns/rows;
- a trace's contribution must not increase because its targets contain more tokens.

The explicit closure fixture required by review is one short one-row trace plus one long four-row trace from the same episode. They must contribute **0.5 + 0.5**, even when the long trace contains many more supervised tokens.

The Phase-0 trace_weight metadata by itself is not sufficient. Duplicating a 0.5 trace weight onto four rows would make the emitted row weights sum to 2.5. Vanilla causal-LM loss reduction can also bias toward target length.

## Objective

For one episode e, trace t, and row r:

    trace_weight(t) = 1 / number_of_traces(e)

    row_weight(r) =
        trace_weight(t) *
        target_tokens(r) / total_target_tokens(t)

If token_loss_sum(r) is the sum of token cross-entropies for row r, the optimizer-facing episode scalar is:

    episode_loss(e) =
        sum over rows r [
            row_weight(r) *
            token_loss_sum(r) / target_tokens(r)
        ]

The target-token term cancels within a trace, so each trace contributes its equal trace weight times the mean loss over every supervised token in that trace.

The row coefficients sum to 1.0 per episode. With two traces they sum to 0.5 for each trace independent of row count and token count.

## Runtime shape

episode_weighting.py contains the model-independent reference reducer. It accepts Python scalars in CPU tests and differentiable scalar tensors on the live autograd path.

weighted_trainer.py supplies a Transformers adapter:

1. tokenize the existing per-turn SFT rows;
2. group all kept rows for one episode into one dataset item;
3. derive row coefficients **after tokenization** from actual supervised-token counts;
4. use per_device_train_batch_size=1 episode;
5. the collator expands that episode into its row batch;
6. EpisodeWeightedTrainer.compute_loss() computes each row's token-loss sum and calls the shared reducer;
7. Hugging Face receives one already-normalized scalar episode loss.

The trainer class refuses any configuration where:

- per_device_train_batch_size is not 1;
- remove_unused_columns is not False.

It also disables Trainer's inferred item/token denominator because the returned scalar is already the frozen episode objective.

Gradient accumulation is therefore accumulation over equal-weight **episodes**, not over arbitrary rows.

The adapter also refuses schedules that would make epoch accounting ambiguous: max_steps truncation, fractional epochs, or an episode count not divisible by world_size × gradient_accumulation_steps. With complete groups, DistributedSampler does not need padding and every accumulation group contains the same number of episode scalars. DDP/accumulation therefore apply only a common batch-average factor to every episode.

## Why not patch row weights onto the legacy trainers?

The referenced historical tool_sft/train.py uses vanilla Trainer and does not consume trace_weight.

The newer secpatch AnswerOnlyTrainer computes a mean token loss for one sequence and lets Trainer average sequences/accumulation steps. That avoids within-row token-length bias, but it still does not consume Phase-0 trace weights and multi-turn traces appear as multiple sequence rows.

This contract deliberately groups at the episode boundary instead.

## CPU closure tests

test_episode_weighting.py verifies, without torch, transformers, or model loading:

- the required one-short/one-long 0.5 + 0.5 fixture;
- token-count changes cannot change trace weight;
- four-row vs one-row traces remain equally weighted;
- the reducer uses the mean over all target tokens in a trace, not an equal mean of row means;
- three traces get exactly one third each;
- different trace losses reduce as the equal-weight trace objective;
- mixed episodes, zero target counts and malformed causal rows fail closed;
- row weights are derived after tokenization;
- the Trainer adapter requires one episode per device batch and preserves its own loss normalization;
- uneven DDP/gradient-accumulation schedules, max-steps truncation, and fractional epochs fail closed.

## Gate semantics

A green CPU suite proves the actual loss-reduction code required for Phase 3. It does **not** authorize training by itself.

Before any GPU trainer run:

- this code, or a reviewed byte-equivalent descendant, must be the reduction used by the Phase-3 trainer;
- the trainer configuration must retain the enforced episode batching contract;
- Phase-3 arms and all other #123 preregistration gates remain unchanged;
- no M4/reserve content enters this lane.

No threshold, dataset, arm, or promotion rule is changed by this implementation.
