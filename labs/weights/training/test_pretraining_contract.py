import hashlib
import importlib.util
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import episode_weighting as weighting
import row_encoding
import tool_surface
import weighted_trainer


class FakeTokenizer:
    def __init__(self):
        self.template_tools = []

    def apply_chat_template(
        self, messages, *, tools, tokenize, enable_thinking, add_generation_prompt=False
    ):
        self.template_tools.append(tools)
        base = "P:" + tool_surface.tool_surface_sha256(tools) + ":"
        if add_generation_prompt:
            return base
        if messages and messages[-1].get("role") == "assistant":
            return base + str(messages[-1].get("content") or "")
        return base

    def __call__(self, text, add_special_tokens=False):
        return {"input_ids": list(range(1, len(text) + 1))}


def row(trace, turn, target):
    return {
        "episode": "ep-required-fixture",
        "trace": trace,
        "turn": turn,
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "request"},
            {"role": "assistant", "content": target},
        ],
    }


class PretrainingContractCompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo = HERE.parents[2]
        world_path = (
            repo / "labs" / "intelligence-bakeoff" / "distillation" / "tool_sft" / "world.py"
        )
        cls.world_sha = hashlib.sha256(world_path.read_bytes()).hexdigest()
        spec = importlib.util.spec_from_file_location("pretraining_contract_world", world_path)
        cls.world = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.world)

    def test_exact_hare_surface_through_required_weighting_fixture(self):
        self.assertEqual(
            self.world_sha,
            "8d902631f10294339fa8bce242f1ccda58e269b1c675a8fe53a3ce0b226d02f7",
        )
        binding = tool_surface.make_binding(
            self.world.TOOL_SCHEMAS,
            mode="fixed",
            collector_sha256=self.world_sha,
        )

        source_rows = [
            row("short", 0, "aa"),          # 2 target tokens
            row("long", 0, "b"),            # 1
            row("long", 1, "ccc"),          # 3
            row("long", 2, "ddddd"),        # 5
            row("long", 3, "eeeeeeeeeee"),  # 11
        ]
        bound = tool_surface.bind_rows(source_rows, binding)
        tokenizer = FakeTokenizer()
        encoded = row_encoding.encode_bound_rows(tokenizer, bound, max_length=10000)

        self.assertEqual([r["target_tokens"] for r in encoded], [2, 1, 3, 5, 11])
        self.assertTrue(tokenizer.template_tools)
        self.assertTrue(
            all(tools == self.world.TOOL_SCHEMAS for tools in tokenizer.template_tools)
        )
        self.assertTrue(
            all(r["tool_surface_sha256"] == binding["tool_surface_sha256"] for r in encoded)
        )

        items = weighted_trainer.build_episode_items(bound, encoded)
        self.assertEqual(len(items), 1)
        packed = items[0]["rows"]
        self.assertEqual([r["target_tokens"] for r in packed], [2, 1, 3, 5, 11])

        trace_totals = {}
        for packed_row in packed:
            trace_totals[packed_row["trace"]] = (
                trace_totals.get(packed_row["trace"], 0.0) + packed_row["loss_weight"]
            )
        self.assertAlmostEqual(trace_totals["short"], 0.5)
        self.assertAlmostEqual(trace_totals["long"], 0.5)
        self.assertAlmostEqual(sum(r["loss_weight"] for r in packed), 1.0)

        counts = [r["target_tokens"] for r in packed]
        weights = [r["loss_weight"] for r in packed]
        token_loss_sums = [count * 7.0 for count in counts]
        self.assertAlmostEqual(
            weighting.reduce_weighted_row_losses(token_loss_sums, counts, weights),
            7.0,
        )

    def test_true_empty_surface_survives_binding_encoding_and_weighting(self):
        binding = tool_surface.make_binding([], mode="fixed", collector_sha256="a" * 64)
        bound = tool_surface.bind_rows([row("direct", 0, "ok")], binding)
        tokenizer = FakeTokenizer()
        encoded = row_encoding.encode_bound_rows(tokenizer, bound, max_length=10000)
        self.assertTrue(all(tools == [] for tools in tokenizer.template_tools))

        item = weighted_trainer.build_episode_items(bound, encoded)[0]
        self.assertAlmostEqual(item["rows"][0]["loss_weight"], 1.0)
        self.assertEqual(item["rows"][0]["target_tokens"], 2)

    def test_encoded_surface_swap_blocks_before_loss_plan(self):
        binding = tool_surface.make_binding(
            self.world.TOOL_SCHEMAS, mode="fixed", collector_sha256=self.world_sha
        )
        bound = tool_surface.bind_rows([row("a", 0, "ok")], binding)
        encoded = row_encoding.encode_bound_rows(FakeTokenizer(), bound, max_length=10000)
        encoded[0]["tool_surface_sha256"] = "0" * 64
        with self.assertRaisesRegex(weighting.WeightingError, "tool-surface hash mismatch"):
            weighted_trainer.build_episode_items(bound, encoded)

    def test_encoded_receipt_swap_blocks_before_loss_plan(self):
        binding = tool_surface.make_binding(
            self.world.TOOL_SCHEMAS, mode="fixed", collector_sha256=self.world_sha
        )
        bound = tool_surface.bind_rows([row("a", 0, "ok")], binding)
        encoded = row_encoding.encode_bound_rows(FakeTokenizer(), bound, max_length=10000)
        encoded[0]["tool_surface_receipt_sha256"] = "0" * 64
        with self.assertRaisesRegex(weighting.WeightingError, "receipt mismatch"):
            weighted_trainer.build_episode_items(bound, encoded)

    def test_encoded_target_count_tamper_blocks_before_loss_plan(self):
        binding = tool_surface.make_binding(
            self.world.TOOL_SCHEMAS, mode="fixed", collector_sha256=self.world_sha
        )
        bound = tool_surface.bind_rows([row("a", 0, "okay")], binding)
        encoded = row_encoding.encode_bound_rows(FakeTokenizer(), bound, max_length=10000)
        encoded[0]["target_tokens"] += 1
        with self.assertRaisesRegex(weighting.WeightingError, "target-token count mismatch"):
            weighted_trainer.build_episode_items(bound, encoded)

    def test_surface_tamper_blocks_before_episode_weighting(self):
        binding = tool_surface.make_binding(
            self.world.TOOL_SCHEMAS, mode="fixed", collector_sha256=self.world_sha
        )
        bound = tool_surface.bind_rows([row("a", 0, "ok")], binding)
        bound[0]["tools"][0]["function"]["description"] += " tampered"
        tokenizer = FakeTokenizer()
        with self.assertRaises(row_encoding.EncodingError):
            row_encoding.encode_bound_rows(tokenizer, bound, max_length=10000)
        self.assertEqual(tokenizer.template_tools, [])


if __name__ == "__main__":
    unittest.main()
