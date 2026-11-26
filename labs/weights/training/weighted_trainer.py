"""Transformers adapter for Haven's episode-normalized W1/W2 loss contract.

This module deliberately does not import torch or transformers at import time. Phase-3
code passes its installed Trainer class to make_episode_weighted_trainer_class().

Training unit:
  one dataset item == one episode
  one item contains all kept per-turn rows for all kept traces of that episode

The collator expands that single episode to a row batch. compute_loss obtains a mean
cross-entropy for each row, then calls episode_weighting.reduce_weighted_row_losses().
Therefore optimizer-facing episode loss is independent of trace row count and target
token count while still training every assistant target from the original per-turn rows.
"""
from __future__ import annotations

import collections
from typing import Sequence

import episode_weighting as weighting


def _target_count(encoded: dict) -> int:
    if not isinstance(encoded, dict):
        raise weighting.WeightingError("encoded row must be an object")
    labels = encoded.get("labels")
    input_ids = encoded.get("input_ids")
    if not isinstance(labels, list) or not isinstance(input_ids, list) or len(labels) != len(input_ids):
        raise weighting.WeightingError("encoded row needs aligned input_ids and labels")
    count = sum(label != -100 for label in labels)
    if count <= 0:
        raise weighting.WeightingError("encoded row has no supervised target tokens")
    return count


def build_episode_items(rows: Sequence[dict], encoded_rows: Sequence[dict]) -> list[dict]:
    """Group tokenized per-turn rows into one deterministic dataset item per episode."""
    if not rows or len(rows) != len(encoded_rows):
        raise weighting.WeightingError("rows and encoded rows must be non-empty and aligned")

    grouped: dict[str, list[tuple[dict, dict]]] = collections.defaultdict(list)
    for row, encoded in zip(rows, encoded_rows):
        episode, _ = weighting._row_identity(row)
        _target_count(encoded)
        grouped[episode].append((row, encoded))

    items = []
    for episode in sorted(grouped):
        pairs = grouped[episode]
        source_rows = [row for row, _ in pairs]
        counts = [_target_count(encoded) for _, encoded in pairs]
        weights = weighting.row_loss_weights(source_rows, counts)
        packed = []
        for (row, encoded), count, loss_weight in zip(pairs, counts, weights):
            attention = encoded.get("attention_mask")
            if attention is None:
                attention = [1] * len(encoded["input_ids"])
            if not isinstance(attention, list) or len(attention) != len(encoded["input_ids"]):
                raise weighting.WeightingError("invalid attention_mask")
            packed.append({
                "input_ids": list(encoded["input_ids"]),
                "attention_mask": list(attention),
                "labels": list(encoded["labels"]),
                "target_tokens": count,
                "loss_weight": loss_weight,
                "trace": row["trace"],
            })
        items.append({"episode": episode, "rows": packed})
    return items


def make_episode_collator(pad_token_id: int):
    """Return a collator for per-device train batch size exactly one episode."""
    if isinstance(pad_token_id, bool) or not isinstance(pad_token_id, int) or pad_token_id < 0:
        raise weighting.WeightingError("invalid pad token id")

    def collate(batch):
        if not isinstance(batch, list) or len(batch) != 1:
            raise weighting.WeightingError(
                "episode-weighted training requires per-device batch size 1"
            )
        item = batch[0]
        if not isinstance(item, dict) or not isinstance(item.get("rows"), list) or not item["rows"]:
            raise weighting.WeightingError("invalid episode item")
        import torch

        rows = item["rows"]
        width = max(len(row["input_ids"]) for row in rows)
        inputs, attention, labels, weights, counts = [], [], [], [], []
        for row in rows:
            n = len(row["input_ids"])
            if n <= 0 or len(row["labels"]) != n or len(row["attention_mask"]) != n:
                raise weighting.WeightingError("malformed encoded row")
            inputs.append(row["input_ids"] + [pad_token_id] * (width - n))
            attention.append(row["attention_mask"] + [0] * (width - n))
            labels.append(row["labels"] + [-100] * (width - n))
            weights.append(float(row["loss_weight"]))
            counts.append(int(row["target_tokens"]))
        return {
            "input_ids": torch.tensor(inputs, dtype=torch.long),
            "attention_mask": torch.tensor(attention, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
            "loss_weights": torch.tensor(weights, dtype=torch.float32),
            "expected_target_counts": torch.tensor(counts, dtype=torch.long),
        }

    return collate


def make_episode_weighted_trainer_class(Trainer):
    """Build a Trainer subclass whose scalar loss is exactly one episode objective."""
    if not isinstance(Trainer, type):
        raise weighting.WeightingError("Trainer must be a class")

    class EpisodeWeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
            import torch

            loss_weights = inputs.pop("loss_weights")
            expected_counts = inputs.pop("expected_target_counts")
            labels = inputs["labels"]
            outputs = model(**inputs)
            logits = outputs.logits.float()

            if logits.ndim != 3 or labels.ndim != 2 or logits.shape[:2] != labels.shape:
                raise weighting.WeightingError("unexpected causal-LM logits/labels shape")
            shifted_logits = logits[:, :-1, :].contiguous()
            shifted_labels = labels[:, 1:].contiguous()
            mask = shifted_labels.ne(-100)
            actual_counts = mask.sum(dim=1)
            if not torch.equal(actual_counts.cpu(), expected_counts.cpu()):
                raise weighting.WeightingError("target-token count changed after collation")

            flat = torch.nn.functional.cross_entropy(
                shifted_logits.view(-1, shifted_logits.size(-1)),
                shifted_labels.view(-1),
                reduction="none",
                ignore_index=-100,
            ).view_as(shifted_labels)
            token_loss_sums = (flat * mask).sum(dim=1)

            counts = [int(x) for x in expected_counts.detach().cpu().tolist()]
            weights = [float(x) for x in loss_weights.detach().cpu().tolist()]
            sums = [token_loss_sums[i] for i in range(token_loss_sums.shape[0])]
            loss = weighting.reduce_weighted_row_losses(sums, counts, weights)
            return (loss, outputs) if return_outputs else loss

    EpisodeWeightedTrainer.__name__ = "EpisodeWeightedTrainer"
    return EpisodeWeightedTrainer
