import math
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import episode_weighting as w
import weighted_trainer as t


def row(episode, trace, turn):
    return {"episode": episode, "trace": trace, "turn": turn}


def encoded(target_tokens, prefix_tokens=3):
    # Non-empty masked prefix mirrors the causal-LM training contract.
    return {
        "input_ids": list(range(prefix_tokens + target_tokens)),
        "attention_mask": [1] * (prefix_tokens + target_tokens),
        "labels": [-100] * prefix_tokens + list(range(target_tokens)),
    }


class EpisodeWeightingInvariantTests(unittest.TestCase):
    def test_required_one_short_one_long_fixture_is_half_plus_half(self):
        rows = [
            row("ep", "short", 0),
            row("ep", "long", 0),
            row("ep", "long", 1),
            row("ep", "long", 2),
            row("ep", "long", 3),
        ]
        counts = [2, 1, 3, 5, 11]
        weights = w.row_loss_weights(rows, counts)
        by_trace = w.trace_weight_totals(rows, weights)

        self.assertTrue(math.isclose(by_trace["short"], 0.5, abs_tol=1e-12))
        self.assertTrue(math.isclose(by_trace["long"], 0.5, abs_tol=1e-12))
        self.assertTrue(math.isclose(sum(weights), 1.0, abs_tol=1e-12))

        # Every supervised token has identical loss 7. The one-row/two-token trace
        # and the four-row/twenty-token trace must each contribute 0.5 of the
        # optimization weight and therefore 3.5 of this scalar loss.
        token_loss_sums = [count * 7.0 for count in counts]
        contributions = [
            loss_sum * weight / count
            for loss_sum, weight, count in zip(token_loss_sums, weights, counts)
        ]
        self.assertTrue(math.isclose(contributions[0], 3.5, abs_tol=1e-12))
        self.assertTrue(math.isclose(sum(contributions[1:]), 3.5, abs_tol=1e-12))
        self.assertTrue(math.isclose(
            w.reduce_weighted_row_losses(token_loss_sums, counts, weights),
            7.0,
            abs_tol=1e-12,
        ))

    def test_token_length_changes_do_not_change_trace_or_episode_weight(self):
        rows = [
            row("ep", "a", 0),
            row("ep", "b", 0),
            row("ep", "b", 1),
            row("ep", "b", 2),
            row("ep", "b", 3),
        ]
        for counts in ([1, 1, 1, 1, 1], [1, 10, 100, 1000, 10000], [999, 7, 2, 3, 5]):
            with self.subTest(counts=counts):
                weights = w.row_loss_weights(rows, counts)
                totals = w.trace_weight_totals(rows, weights)
                self.assertAlmostEqual(totals["a"], 0.5)
                self.assertAlmostEqual(totals["b"], 0.5)
                self.assertAlmostEqual(sum(weights), 1.0)

    def test_trace_mean_not_mean_of_turn_means(self):
        rows = [row("ep", "a", 0), row("ep", "a", 1)]
        counts = [1, 9]
        weights = w.row_loss_weights(rows, counts)
        # First token loss=10, next nine token losses=0. Correct trace token mean=1.
        result = w.reduce_weighted_row_losses([10.0, 0.0], counts, weights)
        self.assertAlmostEqual(result, 1.0)
        # An equal mean of the two row means would incorrectly be 5.
        self.assertNotAlmostEqual(result, 5.0)

    def test_three_traces_each_receive_one_third(self):
        rows = [
            row("ep", "a", 0),
            row("ep", "b", 0), row("ep", "b", 1),
            row("ep", "c", 0), row("ep", "c", 1), row("ep", "c", 2),
        ]
        counts = [2, 2, 8, 1, 2, 7]
        totals = w.trace_weight_totals(rows, w.row_loss_weights(rows, counts))
        self.assertEqual(set(totals), {"a", "b", "c"})
        for value in totals.values():
            self.assertAlmostEqual(value, 1.0 / 3.0)

    def test_different_trace_losses_are_equal_weighted(self):
        rows = [row("ep", "a", 0), row("ep", "b", 0), row("ep", "b", 1)]
        counts = [2, 1, 9]
        weights = w.row_loss_weights(rows, counts)
        # Trace a has mean token loss 2; trace b has mean 6.
        sums = [4.0, 6.0, 54.0]
        self.assertAlmostEqual(w.reduce_weighted_row_losses(sums, counts, weights), 4.0)

    def test_mixed_episodes_are_refused(self):
        with self.assertRaises(w.WeightingError):
            w.row_loss_weights([row("a", "t", 0), row("b", "t", 0)], [1, 1])

    def test_zero_or_boolean_token_counts_are_refused(self):
        for bad in (0, -1, True):
            with self.subTest(bad=bad), self.assertRaises(w.WeightingError):
                w.row_loss_weights([row("a", "t", 0)], [bad])

    def test_loss_inputs_must_align(self):
        with self.assertRaises(w.WeightingError):
            w.reduce_weighted_row_losses([1.0], [1, 2], [1.0])

    def test_build_episode_items_derives_weights_after_tokenization(self):
        rows = [
            row("ep2", "only", 0),
            row("ep1", "short", 0),
            row("ep1", "long", 0),
            row("ep1", "long", 1),
            row("ep1", "long", 2),
            row("ep1", "long", 3),
        ]
        enc = [encoded(4), encoded(2), encoded(1), encoded(3), encoded(5), encoded(11)]
        items = t.build_episode_items(rows, enc)
        self.assertEqual([item["episode"] for item in items], ["ep1", "ep2"])

        ep1 = items[0]["rows"]
        self.assertAlmostEqual(sum(r["loss_weight"] for r in ep1), 1.0)
        by_trace = {}
        for r in ep1:
            by_trace[r["trace"]] = by_trace.get(r["trace"], 0.0) + r["loss_weight"]
        self.assertAlmostEqual(by_trace["short"], 0.5)
        self.assertAlmostEqual(by_trace["long"], 0.5)
        self.assertEqual([r["target_tokens"] for r in ep1], [2, 1, 3, 5, 11])

        self.assertAlmostEqual(items[1]["rows"][0]["loss_weight"], 1.0)

    def test_encoded_row_without_target_is_refused(self):
        with self.assertRaises(w.WeightingError):
            t.build_episode_items(
                [row("ep", "a", 0)],
                [{"input_ids": [1, 2], "labels": [-100, -100]}],
            )

    def test_encoded_row_requires_masked_causal_prefix(self):
        with self.assertRaises(w.WeightingError):
            t.build_episode_items(
                [row("ep", "a", 0)],
                [{"input_ids": [1, 2], "labels": [1, 2]}],
            )

    def test_episode_batching_contract_is_explicit(self):
        class Args:
            per_device_train_batch_size = 1
            remove_unused_columns = False

        class DummyTrainer:
            def __init__(self, args=None):
                self.args = args or Args()
                self.model_accepts_loss_kwargs = True

        Weighted = t.make_episode_weighted_trainer_class(DummyTrainer)
        self.assertTrue(issubclass(Weighted, DummyTrainer))
        self.assertEqual(Weighted.__name__, "EpisodeWeightedTrainer")
        instance = Weighted()
        self.assertFalse(instance.model_accepts_loss_kwargs)

        collator = t.make_episode_collator(0)
        with self.assertRaises(w.WeightingError):
            collator([])

        bad_batch = Args()
        bad_batch.per_device_train_batch_size = 2
        with self.assertRaisesRegex(w.WeightingError, "batch_size=1"):
            Weighted(args=bad_batch)

        bad_columns = Args()
        bad_columns.remove_unused_columns = True
        with self.assertRaisesRegex(w.WeightingError, "remove_unused_columns=False"):
            Weighted(args=bad_columns)


if __name__ == "__main__":
    unittest.main()
