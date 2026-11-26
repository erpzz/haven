import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import row_encoding as enc
import tool_surface as surface


READ = {
    "type": "function",
    "function": {
        "name": "read_fixture",
        "description": "read synthetic fixture",
        "parameters": {
            "type": "object",
            "properties": {"object": {"type": "string"}},
            "required": ["object"],
            "additionalProperties": False,
        },
    },
}
WRITE = {
    "type": "function",
    "function": {
        "name": "write_canary",
        "description": "synthetic canary",
        "parameters": {
            "type": "object",
            "properties": {"object": {"type": "string"}},
            "required": ["object"],
            "additionalProperties": False,
        },
    },
}


def training_row(episode="ep", trace="trace", target="answer"):
    return {
        "episode": episode,
        "trace": trace,
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "request"},
            {"role": "assistant", "content": target},
        ],
    }


class FakeTokenizer:
    def __init__(self):
        self.template_calls = []

    def apply_chat_template(
        self, messages, *, tools, tokenize, enable_thinking, add_generation_prompt=False
    ):
        self.template_calls.append({
            "messages": copy.deepcopy(messages),
            "tools": copy.deepcopy(tools),
            "tokenize": tokenize,
            "enable_thinking": enable_thinking,
            "add_generation_prompt": add_generation_prompt,
        })
        prefix_messages = messages if add_generation_prompt else messages[:-1]
        base = "TOOLS=" + json.dumps(tools, sort_keys=True) + "|MESSAGES=" + json.dumps(
            prefix_messages, sort_keys=True
        ) + "|ASSIST="
        if add_generation_prompt:
            return base
        return base + json.dumps(messages[-1], sort_keys=True)

    def __call__(self, text, add_special_tokens=False):
        self.last_add_special_tokens = add_special_tokens
        return {"input_ids": [ord(ch) % 251 for ch in text]}


class FallbackTokenizer(FakeTokenizer):
    def apply_chat_template(
        self, messages, *, tools, tokenize, enable_thinking, add_generation_prompt=False
    ):
        self.template_calls.append({
            "messages": copy.deepcopy(messages),
            "tools": copy.deepcopy(tools),
            "tokenize": tokenize,
            "enable_thinking": enable_thinking,
            "add_generation_prompt": add_generation_prompt,
        })
        base = "BASE:" + json.dumps(tools, sort_keys=True)
        if add_generation_prompt:
            return base + "\nHEAD\nGEN"
        if messages and messages[-1].get("role") == "assistant":
            return base + "\nHEAD\nTARGET:" + json.dumps(messages[-1], sort_keys=True)
        return base


class ToolSurfaceBindingTests(unittest.TestCase):
    def test_current_hare_surface_matches_phase0_pinned_source(self):
        repo = HERE.parents[2]
        world_path = repo / "labs" / "intelligence-bakeoff" / "distillation" / "tool_sft" / "world.py"
        digest = hashlib.sha256(world_path.read_bytes()).hexdigest()
        self.assertEqual(
            digest,
            "8d902631f10294339fa8bce242f1ccda58e269b1c675a8fe53a3ce0b226d02f7",
        )
        spec = importlib.util.spec_from_file_location("weights_surface_world", world_path)
        world = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(world)
        binding = surface.make_binding(
            world.TOOL_SCHEMAS, mode="fixed", collector_sha256=digest
        )
        self.assertEqual(surface.validate_binding(binding), [])
        self.assertEqual(binding["tool_names"], world.TOOL_NAMES)
        self.assertEqual(len(binding["tools"]), 4)

    def test_fixed_binding_hashes_exact_ordered_surface(self):
        binding = surface.make_binding(
            [READ, WRITE], mode="fixed", collector_sha256="a" * 64
        )
        self.assertEqual(surface.validate_binding(binding), [])
        self.assertEqual(binding["tool_names"], ["read_fixture", "write_canary"])
        self.assertEqual(binding["catalog_sha256"], binding["tool_surface_sha256"])

        reversed_binding = surface.make_binding(
            [WRITE, READ], mode="fixed", collector_sha256="a" * 64
        )
        self.assertNotEqual(
            binding["tool_surface_sha256"], reversed_binding["tool_surface_sha256"]
        )

    def test_empty_fixed_surface_is_first_class(self):
        binding = surface.make_binding(
            [], mode="fixed", collector_sha256="a" * 64
        )
        self.assertEqual(binding["tools"], [])
        self.assertEqual(binding["tool_names"], [])
        self.assertEqual(surface.validate_binding(binding), [])

    def test_binding_mutation_is_detected(self):
        binding = surface.make_binding(
            [READ], mode="fixed", collector_sha256="a" * 64
        )
        tampered = copy.deepcopy(binding)
        tampered["tools"][0]["function"]["description"] = "changed"
        errors = surface.validate_binding(tampered)
        self.assertTrue(
            {"SURFACE_HASH_MISMATCH", "RECEIPT_HASH_MISMATCH"} & set(errors),
            errors,
        )

    def test_bind_rows_refuses_preexisting_surface_fields(self):
        binding = surface.make_binding(
            [READ], mode="fixed", collector_sha256="a" * 64
        )
        row = training_row()
        row["tools"] = []
        with self.assertRaises(surface.SurfaceError):
            surface.bind_rows([row], binding)

    def test_routed_rows_may_vary_surface_but_not_catalog_or_collector(self):
        full = [READ, WRITE]
        catalog = surface.tool_surface_sha256(full)
        read_binding = surface.make_binding(
            [READ],
            mode="routed",
            collector_sha256="a" * 64,
            catalog_sha256=catalog,
            route_receipt_sha256="b" * 64,
        )
        empty_binding = surface.make_binding(
            [],
            mode="routed",
            collector_sha256="a" * 64,
            catalog_sha256=catalog,
            route_receipt_sha256="c" * 64,
        )
        rows = (
            surface.bind_rows([training_row("ep1", "t1")], read_binding)
            + surface.bind_rows([training_row("ep2", "t2")], empty_binding)
        )
        self.assertEqual(surface.validate_bound_rows(rows), [])

        wrong_catalog = surface.make_binding(
            [READ],
            mode="routed",
            collector_sha256="a" * 64,
            catalog_sha256="d" * 64,
            route_receipt_sha256="e" * 64,
        )
        mixed = rows + surface.bind_rows([training_row("ep3", "t3")], wrong_catalog)
        self.assertIn("MIXED_CATALOGS", surface.validate_bound_rows(mixed))

    def test_fixed_and_routed_rows_cannot_mix_inside_one_arm(self):
        fixed = surface.make_binding([READ], mode="fixed", collector_sha256="a" * 64)
        routed = surface.make_binding(
            [READ],
            mode="routed",
            collector_sha256="a" * 64,
            catalog_sha256=surface.tool_surface_sha256([READ, WRITE]),
            route_receipt_sha256="b" * 64,
        )
        rows = (
            surface.bind_rows([training_row("ep1", "t1")], fixed)
            + surface.bind_rows([training_row("ep2", "t2")], routed)
        )
        self.assertIn("MIXED_SURFACE_MODES", surface.validate_bound_rows(rows))

    def test_surface_cannot_change_mid_trace(self):
        catalog = surface.tool_surface_sha256([READ, WRITE])
        a = surface.make_binding(
            [READ], mode="routed", collector_sha256="a" * 64,
            catalog_sha256=catalog, route_receipt_sha256="b" * 64
        )
        b = surface.make_binding(
            [], mode="routed", collector_sha256="a" * 64,
            catalog_sha256=catalog, route_receipt_sha256="c" * 64
        )
        rows = (
            surface.bind_rows([training_row("ep", "same", "one")], a)
            + surface.bind_rows([training_row("ep", "same", "two")], b)
        )
        self.assertIn("TRACE_SURFACE_CHANGED", surface.validate_bound_rows(rows))

    def test_encoder_passes_exact_tools_to_every_template_call(self):
        binding = surface.make_binding(
            [READ, WRITE], mode="fixed", collector_sha256="a" * 64
        )
        row = surface.bind_rows([training_row()], binding)[0]
        tokenizer = FakeTokenizer()
        encoded = enc.encode_bound_row(tokenizer, row, max_length=10000)

        self.assertGreater(encoded["target_tokens"], 0)
        self.assertEqual(encoded["tool_surface_sha256"], binding["tool_surface_sha256"])
        self.assertEqual(
            encoded["tool_surface_receipt_sha256"], binding["receipt_sha256"]
        )
        self.assertGreaterEqual(len(tokenizer.template_calls), 2)
        for call in tokenizer.template_calls:
            self.assertEqual(call["tools"], [READ, WRITE])
            self.assertIs(call["tokenize"], False)
            self.assertIs(call["enable_thinking"], False)

    def test_encoder_preserves_true_empty_surface_not_tools_none(self):
        binding = surface.make_binding(
            [], mode="fixed", collector_sha256="a" * 64
        )
        row = surface.bind_rows([training_row()], binding)[0]
        tokenizer = FakeTokenizer()
        enc.encode_bound_row(tokenizer, row, max_length=10000)
        self.assertTrue(tokenizer.template_calls)
        self.assertTrue(all(call["tools"] == [] for call in tokenizer.template_calls))

    def test_qwythos_prefix_fallback_keeps_bound_tools(self):
        binding = surface.make_binding(
            [READ], mode="fixed", collector_sha256="a" * 64
        )
        row = surface.bind_rows([training_row()], binding)[0]
        tokenizer = FallbackTokenizer()
        encoded = enc.encode_bound_row(tokenizer, row, max_length=10000)
        self.assertGreater(encoded["target_tokens"], 0)
        self.assertTrue(all(call["tools"] == [READ] for call in tokenizer.template_calls))

    def test_oversized_bound_row_fails_instead_of_dropping_one_turn(self):
        binding = surface.make_binding(
            [READ], mode="fixed", collector_sha256="a" * 64
        )
        row = surface.bind_rows([training_row(target="a very long answer")], binding)[0]
        with self.assertRaisesRegex(enc.EncodingError, "max_length"):
            enc.encode_bound_row(FakeTokenizer(), row, max_length=2)

    def test_dataset_is_validated_before_any_tokenizer_call(self):
        binding = surface.make_binding(
            [READ], mode="fixed", collector_sha256="a" * 64
        )
        rows = surface.bind_rows(
            [training_row("ep1", "t1"), training_row("ep2", "t2")],
            binding,
        )
        rows[1]["tools"][0]["function"]["name"] = "mutated"
        tokenizer = FakeTokenizer()
        with self.assertRaises(enc.EncodingError):
            enc.encode_bound_rows(tokenizer, rows, max_length=10000)
        self.assertEqual(tokenizer.template_calls, [])


if __name__ == "__main__":
    unittest.main()
