"""Episode-normalized loss reduction for Haven W1/W2 supervised training.

Frozen research requirement (#123 / #152):
- every episode has total optimization weight 1.0;
- kept traces split that weight equally;
- trace contribution is independent of the trace's row/turn count and target-token count.

This module contains no model or GPU code. The same reducer is used by the future
Transformers Trainer adapter and by CPU invariant tests.
"""
from __future__ import annotations

import collections
import math
from typing import Any, Sequence


class WeightingError(ValueError):
    pass


def _row_identity(row: dict) -> tuple[str, str]:
    if not isinstance(row, dict):
        raise WeightingError("row must be an object")
    episode = row.get("episode")
    trace = row.get("trace")
    if not isinstance(episode, str) or not episode:
        raise WeightingError("row missing episode")
    if not isinstance(trace, str) or not trace:
        raise WeightingError("row missing trace")
    return episode, trace


def row_loss_weights(rows: Sequence[dict], target_token_counts: Sequence[int]) -> list[float]:
    """Return per-row coefficients whose sum is 1.0 for one episode.

    A trace receives 1 / number_of_traces. Within that trace, its weight is split
    across rows in proportion to each row's number of supervised target tokens.

    If row i has target-token mean loss L_i and coefficient w_i, the episode loss is
    sum_i w_i * L_i. Algebraically, each trace contributes its mean loss over *all*
    supervised target tokens times exactly 1 / number_of_traces.
    """
    if not isinstance(rows, Sequence) or not rows:
        raise WeightingError("rows must be a non-empty sequence")
    if not isinstance(target_token_counts, Sequence) or len(target_token_counts) != len(rows):
        raise WeightingError("target-token counts must align with rows")

    identities = [_row_identity(row) for row in rows]
    episodes = {episode for episode, _ in identities}
    if len(episodes) != 1:
        raise WeightingError("one loss item must contain exactly one episode")

    counts: list[int] = []
    for value in target_token_counts:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise WeightingError("each row needs a positive integer target-token count")
        counts.append(value)

    traces = sorted({trace for _, trace in identities})
    trace_weight = 1.0 / len(traces)
    tokens_by_trace = collections.Counter()
    for (_, trace), count in zip(identities, counts):
        tokens_by_trace[trace] += count

    weights = [
        trace_weight * count / tokens_by_trace[trace]
        for (_, trace), count in zip(identities, counts)
    ]
    if not math.isclose(sum(weights), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise WeightingError("internal episode-weight invariant failed")
    return weights


def trace_weight_totals(rows: Sequence[dict], row_weights: Sequence[float]) -> dict[str, float]:
    """Aggregate row coefficients by trace for diagnostics/tests."""
    if len(rows) != len(row_weights):
        raise WeightingError("weights must align with rows")
    out: dict[str, float] = collections.defaultdict(float)
    episode = None
    for row, weight in zip(rows, row_weights):
        ep, trace = _row_identity(row)
        if episode is None:
            episode = ep
        elif ep != episode:
            raise WeightingError("one loss item must contain exactly one episode")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight < 0:
            raise WeightingError("invalid row weight")
        out[trace] += float(weight)
    return dict(out)


def reduce_weighted_row_losses(
    token_loss_sums: Sequence[Any],
    target_token_counts: Sequence[int],
    row_weights: Sequence[float],
):
    """Reduce row token-loss sums to one episode loss.

    token_loss_sums may contain Python numerics or differentiable scalar tensors.
    The reducer deliberately uses only multiplication, division, and addition so the
    exact same function can sit on the live autograd path and in CPU-only tests.

    For row i:
        row_mean_i = token_loss_sum_i / target_tokens_i
        contribution_i = row_weight_i * row_mean_i

    The returned scalar is the sum of those contributions.
    """
    n = len(token_loss_sums)
    if n == 0 or len(target_token_counts) != n or len(row_weights) != n:
        raise WeightingError("loss inputs must be non-empty and aligned")

    total = None
    for loss_sum, count, weight in zip(token_loss_sums, target_token_counts, row_weights):
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise WeightingError("invalid target-token count")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight < 0:
            raise WeightingError("invalid row weight")
        term = loss_sum * (float(weight) / count)
        total = term if total is None else total + term
    return total


def episode_loss(
    rows: Sequence[dict],
    target_token_counts: Sequence[int],
    token_loss_sums: Sequence[Any],
):
    """Convenience wrapper used by reference tests and simple trainers."""
    weights = row_loss_weights(rows, target_token_counts)
    return reduce_weighted_row_losses(token_loss_sums, target_token_counts, weights)
