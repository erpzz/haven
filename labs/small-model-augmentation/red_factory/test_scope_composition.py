import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
AUG = HERE.parents[1]
sys.path.insert(0, str(AUG))

import tool_context as routing  # noqa: E402
import tool_scope as scope  # noqa: E402
from mcp_fixture import fixture_for_case, handle  # noqa: E402
from red_factory import FAMILIES, make_case  # noqa: E402


def scope_policy(case):
    case.validate()
    allowed = list(case.tool_policy.allowed_tools)
    rules = {}
    for name in allowed:
        if name != "read_fixture":
            raise AssertionError(f"unexpected HRF tool {name}")
        rules[name] = {
            "allowed_keys": ["object"],
            "required_keys": ["object"],
            "exact_values": {"/object": [f"alpha-{case.seed:04d}"]},
        }
    return {
        "schema": scope.SCHEMA,
        "allowed_tools": allowed,
        "max_calls": case.tool_policy.max_total_calls,
        "per_tool_max": {name: case.tool_policy.max_per_tool for name in allowed},
        "unique_calls": not case.tool_policy.allow_duplicate_calls,
        "argument_rules": rules,
    }


def route_cards():
    return [
        {
            "name": "read_fixture",
            "effect": "read",
            "route_terms": ["read", "record", "owner", "state", "lookup", "resolve"],
            "definition": {
                "name": "read_fixture",
                "description": "synthetic fixture read",
                "inputSchema": {
                    "type": "object",
                    "properties": {"object": {"type": "string"}},
                    "required": ["object"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "name": "write_canary",
            "effect": "change",
            "route_terms": ["write", "change", "owner"],
            "definition": {
                "name": "write_canary",
                "description": "hidden synthetic canary",
                "inputSchema": {
                    "type": "object",
                    "properties": {"object": {"type": "string"}},
                    "required": ["object"],
                    "additionalProperties": False,
                },
            },
        },
    ]


def gated_dispatch(policy, state, tool, arguments, implementation):
    gate = scope.check_call(policy, state, tool, arguments)
    if gate["status"] != "pass":
        return gate, None
    return gate, implementation()


class RedFactoryScopeRoutingComposition(unittest.TestCase):
    def test_every_family_maps_to_valid_exact_scope_policy(self):
        for family in FAMILIES:
            with self.subTest(family=family):
                case = make_case(family, 11)
                policy = scope_policy(case)
                self.assertEqual(scope.validate_policy(policy), [])
                expected = list(case.tool_policy.allowed_tools)
                self.assertEqual(scope.bind_surface(policy, expected)["status"], "pass")
                extra = scope.bind_surface(policy, expected + ["write_canary"])
                self.assertEqual(extra["status"], "block")
                self.assertIn("VISIBLE_TOOL_EXTRA", extra["errors"])

    def test_context_routing_never_widens_scope_authorization(self):
        cards = route_cards()
        for family in FAMILIES:
            with self.subTest(family=family):
                case = make_case(family, 12)
                allowed = list(case.tool_policy.allowed_tools)
                result = routing.route(
                    cards,
                    case.prompt,
                    authorized=allowed,
                    required=allowed,
                    allowed_effects=["read", "change", "create"],
                    max_tools=2,
                )
                self.assertEqual(result["status"], "pass", result)
                self.assertEqual(result["selected"], allowed)
                self.assertNotIn("write_canary", result["selected"])
                self.assertEqual(
                    scope.bind_surface(scope_policy(case), result["selected"])["status"],
                    "pass",
                )

    def test_unauthorized_effect_is_true_zero_tool_session(self):
        case = make_case("unauthorized_effect", 13)
        policy = scope_policy(case)
        self.assertEqual(policy["allowed_tools"], [])
        self.assertEqual(policy["max_calls"], 0)
        self.assertEqual(scope.bind_surface(policy, [])["status"], "pass")
        routed = routing.route(
            route_cards(),
            "change owner immediately",
            authorized=[],
            allowed_effects=["read", "change", "create"],
            max_tools=2,
        )
        self.assertEqual(routed["status"], "pass")
        self.assertEqual(routed["selected"], [])
        self.assertEqual(routed["definitions"], [])

    def test_hidden_canary_blocks_before_implementation(self):
        case = make_case("unauthorized_effect", 14)
        marker = {"executed": False}

        def implementation():
            marker["executed"] = True
            return {"ok": True}

        gate, result = gated_dispatch(
            scope_policy(case),
            scope.State(),
            "write_canary",
            {"object": "alpha-0014"},
            implementation,
        )
        self.assertEqual(gate["status"], "block")
        self.assertIn("TOOL_NOT_ALLOWED", gate["errors"])
        self.assertIsNone(result)
        self.assertFalse(marker["executed"])

    def test_wrong_target_blocks_before_implementation(self):
        case = make_case("duplicate_read", 15)
        marker = {"executed": False}

        def implementation():
            marker["executed"] = True
            return {"ok": True}

        gate, result = gated_dispatch(
            scope_policy(case),
            scope.State(),
            "read_fixture",
            {"object": "alpha-9999"},
            implementation,
        )
        self.assertEqual(gate["status"], "block")
        self.assertIn("ARGUMENT_VALUE_OUT_OF_SCOPE", gate["errors"])
        self.assertIsNone(result)
        self.assertFalse(marker["executed"])

    def test_duplicate_budget_blocks_second_implementation(self):
        case = make_case("duplicate_read", 16)
        state = scope.State()
        calls = {"n": 0}

        def implementation():
            calls["n"] += 1
            return {"ok": True}

        args = {"object": "alpha-0016"}
        first, result = gated_dispatch(scope_policy(case), state, "read_fixture", args, implementation)
        self.assertEqual(first["status"], "pass")
        self.assertEqual(result, {"ok": True})
        second, result = gated_dispatch(scope_policy(case), state, "read_fixture", args, implementation)
        self.assertEqual(second["status"], "block")
        self.assertTrue(
            {"CALL_BUDGET_EXCEEDED", "TOOL_BUDGET_EXCEEDED", "DUPLICATE_CALL"}
            & set(second["errors"])
        )
        self.assertIsNone(result)
        self.assertEqual(calls["n"], 1)

    def test_mcp_tools_list_matches_scope_surface_exactly(self):
        for family in FAMILIES:
            with self.subTest(family=family), tempfile.TemporaryDirectory() as tmp:
                case = make_case(family, 17)
                fixture = fixture_for_case(case)
                response = handle(
                    {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                    fixture,
                    Path(tmp) / "calls.jsonl",
                )
                listed = [row["name"] for row in response["result"]["tools"]]
                self.assertEqual(listed, list(case.tool_policy.allowed_tools))
                self.assertEqual(scope.bind_surface(scope_policy(case), listed)["status"], "pass")


if __name__ == "__main__":
    unittest.main()
