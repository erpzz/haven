import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

CYBER = Path(__file__).resolve().parents[1]
AUG = CYBER.parent / "small-model-augmentation"
sys.path.insert(0, str(AUG))

import tool_scope as scope  # noqa: E402
from haven_cyber.tools.registry import ToolSpec, default_registry  # noqa: E402

SNAPSHOT = "fixtures/tenants/contoso-weak.json"


def policy(max_calls=2):
    arguments = {"snapshot_path": SNAPSHOT}
    return {
        "schema": scope.SCHEMA,
        "allowed_tools": ["cyber_call"],
        "max_calls": max_calls,
        "per_tool_max": {"cyber_call": max_calls},
        "unique_calls": True,
        "argument_rules": {
            "cyber_call": {
                "allowed_keys": ["tool_id", "arguments"],
                "required_keys": ["tool_id", "arguments"],
                "exact_values": {
                    "/tool_id": ["entra.ca.assess"],
                    "/arguments": [arguments],
                    "/arguments/snapshot_path": [SNAPSHOT],
                },
            }
        },
    }


def gated_dispatch(pol, state, registry, tool_id, arguments):
    outer = {"tool_id": tool_id, "arguments": arguments}
    gate = scope.check_call(pol, state, "cyber_call", outer)
    if gate["status"] != "pass":
        return gate, None
    return gate, registry.invoke(tool_id, arguments, caller="scope-integration")


class CyberDispatcherScopeIntegration(unittest.TestCase):
    def test_exact_model_visible_surface(self):
        p = policy()
        self.assertEqual(scope.bind_surface(p, ["cyber_call"])["status"], "pass")
        self.assertEqual(scope.bind_surface(p, ["cyber_call", "terminal"])["status"], "block")
        self.assertEqual(scope.bind_surface(p, ["cyber_call", "tool_search"])["status"], "block")

    def test_allowed_nested_dispatch_reaches_real_registry(self):
        reg = default_registry(None)
        gate, result = gated_dispatch(policy(), scope.State(), reg, "entra.ca.assess", {"snapshot_path": SNAPSHOT})
        self.assertEqual(gate["status"], "pass")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["result"]["schema"], "haven-cyber-evidence-v1")

    def test_wrong_inner_tool_or_target_blocks_before_registry(self):
        reg = default_registry(None)
        cases = [
            ("findings.lookup", {"path": "runs/guess.json"}),
            ("entra.ca.assess", {"snapshot_path": "/etc/passwd"}),
            ("entra.ca.assess", {"snapshot_path": "<snapshot>"}),
            ("entra.ca.assess", {}),
            ("entra.ca.assess", {"snapshot_path": SNAPSHOT, "extra": True}),
        ]
        for tool_id, arguments in cases:
            with self.subTest(tool_id=tool_id, arguments=arguments):
                state = scope.State()
                with mock.patch.object(reg, "invoke", wraps=reg.invoke) as invoke:
                    gate, result = gated_dispatch(policy(), state, reg, tool_id, arguments)
                    self.assertEqual(gate["status"], "block")
                    self.assertIsNone(result)
                    invoke.assert_not_called()

    def test_denied_side_effect_canary_never_executes(self):
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d) / "executed"
            reg = default_registry(None)
            reg.register(ToolSpec(
                "x.canary", "side effect canary",
                {"type": "object", "properties": {}, "additionalProperties": False},
                {}, lambda: marker.write_text("executed") or {"ok": True},
            ))
            gate, result = gated_dispatch(policy(), scope.State(), reg, "x.canary", {})
            self.assertEqual(gate["status"], "block")
            self.assertIsNone(result)
            self.assertFalse(marker.exists())

    def test_budget_blocks_second_dispatch_before_registry(self):
        reg = default_registry(None)
        state = scope.State()
        p = policy(max_calls=1)
        with mock.patch.object(reg, "invoke", wraps=reg.invoke) as invoke:
            first_gate, first = gated_dispatch(p, state, reg, "entra.ca.assess", {"snapshot_path": SNAPSHOT})
            self.assertEqual(first_gate["status"], "pass")
            self.assertTrue(first["ok"])
            self.assertEqual(invoke.call_count, 1)

            second_gate, second = gated_dispatch(p, state, reg, "entra.ca.assess", {"snapshot_path": SNAPSHOT})
            self.assertEqual(second_gate["status"], "block")
            self.assertIsNone(second)
            self.assertEqual(invoke.call_count, 1)
            self.assertTrue({"CALL_BUDGET_EXCEEDED", "TOOL_BUDGET_EXCEEDED", "DUPLICATE_CALL"} & set(second_gate["errors"]))


if __name__ == "__main__":
    unittest.main()
