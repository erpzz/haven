"""CPU-lane equivalence on a tiny random Qwen3: no download, skipped without torch/peft."""
import pathlib
import sys
import unittest

TOOL_SFT = pathlib.Path(__file__).resolve().parents[1] / "tool_sft"
sys.path.insert(0, str(TOOL_SFT))

try:
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import Qwen3Config, Qwen3ForCausalLM
except ImportError:  # the CI smoke job has no torch
    torch = None


@unittest.skipIf(torch is None, "torch, transformers and peft are not installed")
class SharedPrefixTests(unittest.TestCase):
    def setUp(self):
        import cpu_lane
        self.cpu_lane = cpu_lane
        torch.manual_seed(0)
        config = Qwen3Config(vocab_size=97, hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                             num_attention_heads=4, num_key_value_heads=2, head_dim=8,
                             max_position_embeddings=128)
        model = Qwen3ForCausalLM(config)
        self.model = get_peft_model(model, LoraConfig(r=4, lora_alpha=8, lora_dropout=0.0,
                                                      target_modules=cpu_lane.LORA_TARGETS))
        for name, param in self.model.named_parameters():
            if "lora_B" in name:
                param.data.normal_(0, 0.05)
        self.params = [p for p in self.model.parameters() if p.requires_grad]
        prefix = torch.randint(0, 97, (20,)).tolist()
        self.rows = []
        for length, target in ((9, 3), (14, 6), (11, 2)):
            suffix = torch.randint(0, 97, (length,)).tolist()
            ids = prefix + suffix
            self.rows.append({"input_ids": ids,
                              "labels": [-100] * (len(ids) - target) + ids[-target:]})

    def grads(self):
        out = [p.grad.detach().clone() for p in self.params]
        self.model.zero_grad(set_to_none=True)
        return out

    def test_matches_per_row_token_weighted_loss(self):
        tokens = sum(sum(x != -100 for x in r["labels"]) for r in self.rows)
        naive = 0.0
        for row in self.rows:
            logits = self.model(input_ids=torch.tensor([row["input_ids"]])).logits[0, :-1]
            loss = torch.nn.functional.cross_entropy(
                logits, torch.tensor(row["labels"][1:]), ignore_index=-100, reduction="sum") / tokens
            loss.backward()
            naive += float(loss)
        expected = self.grads()
        prefix = self.rows[0]["input_ids"][:self.cpu_lane.common_prefix([r["input_ids"] for r in self.rows])]
        self.assertEqual(len(prefix), 20)
        shared, counted = self.cpu_lane.step_loss(self.model, prefix, self.rows, autocast=False)
        actual = self.grads()
        self.assertEqual(counted, tokens)
        self.assertAlmostEqual(shared, naive, places=5)
        for a, b in zip(actual, expected):
            torch.testing.assert_close(a, b, rtol=1e-4, atol=1e-6)

    def test_refuses_a_target_inside_the_prefix(self):
        row = dict(self.rows[0])
        row["labels"] = list(row["input_ids"])
        with self.assertRaises(ValueError):
            self.cpu_lane.step_loss(self.model, row["input_ids"][:20], [row], autocast=False)


class CommonPrefixTests(unittest.TestCase):
    def test_common_prefix(self):
        sys.path.insert(0, str(TOOL_SFT))
        if torch is None:
            self.skipTest("cpu_lane imports run.py only; kept with the torch tests")
        import cpu_lane
        self.assertEqual(cpu_lane.common_prefix([[1, 2, 3, 4], [1, 2, 9], [1, 2, 3]]), 2)


if __name__ == "__main__":
    unittest.main()
