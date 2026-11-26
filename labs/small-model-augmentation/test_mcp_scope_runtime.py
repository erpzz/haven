"""Final-dispatch scope tests for Haven operator and Haven Cyber."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

AUG = Path(__file__).resolve().parent
LABS = AUG.parent
sys.path.insert(0, str(AUG))
sys.path.insert(0, str(LABS / "hermes"))
sys.path.insert(0, str(LABS / "cyber"))

import mcp_scope_runtime as runtime  # noqa: E402
import tool_scope as scope  # noqa: E402
from haven_hermes.mcp_stdio import RpcError, Server  # noqa: E402
from haven_cyber import mcp_server as cyber_mcp  # noqa: E402


class FakeTool:
    def __init__(self, name):
        self.name = name
        self.description = name

    def schema(self):
        return {"type": "object", "properties": {}, "additionalProperties": False}

    def annotations(self):
        return {"readOnlyHint": True}


class FakeRegistry:
    def __init__(self, names):
        self._tools = [FakeTool(name) for name in names]
        self.listeners = []
        self.calls = []

    def refresh(self):
        return None

    def visible(self):
        return list(self._tools)

    def invoke(self, name, args, **kwargs):
        self.calls.append((name, args, kwargs))
        return {"ok": True, "result": {"name": name, "args": args}}


def raw_policy(name="haven_status", *, max_calls=1):
    return {
        "schema": scope.SCHEMA,
        "allowed_tools": [name],
        "max_calls": max_calls,
        "per_tool_max": {name: max_calls},
        "unique_calls": True,
        "argument_rules": {
            name: {
                "allowed_keys": [],
                "required_keys": [],
                "exact_values": {},
            }
        },
    }


def cyber_policy(max_calls=1):
    target = "fixtures/tenants/contoso-weak.json"
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
                    "/arguments": [{"snapshot_path": target}],
                    "/arguments/snapshot_path": [target],
                },
            }
        },
    }


class FinalDispatcherScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.policy_path = Path(self.tmp.name) / "policy.json"

    def write_policy(self, data):
        self.policy_path.write_text(json.dumps(data), encoding="utf-8")
        self.policy_path.chmod(0o600)

    def gate(self, data):
        self.write_policy(data)
        return runtime.McpScopeGate(str(self.policy_path), augmentation_root=AUG)

    def test_operator_tools_list_is_narrowed_at_server(self):
        reg = FakeRegistry(["haven_status", "haven_gpu", "haven_models"])
        srv = Server(reg, name="haven", version="test", instructions="i",
                     scope_gate=self.gate(raw_policy()))
        listed = srv.dispatch("tools/list", {})["tools"]
        self.assertEqual([t["name"] for t in listed], ["haven_status"])

    def test_operator_hidden_tool_cannot_reach_registry(self):
        reg = FakeRegistry(["haven_status", "haven_gpu"])
        srv = Server(reg, name="haven", version="test", instructions="i",
                     scope_gate=self.gate(raw_policy()))
        with self.assertRaisesRegex(RpcError, "host scope"):
            srv.dispatch("tools/call", {"name": "haven_gpu", "arguments": {}})
        self.assertEqual(reg.calls, [])

    def test_operator_final_args_are_rechecked_and_budgeted(self):
        reg = FakeRegistry(["haven_status"])
        gate = self.gate(raw_policy())
        srv = Server(reg, name="haven", version="test", instructions="i", scope_gate=gate)
        result = srv.dispatch("tools/call", {"name": "haven_status", "arguments": {}})
        self.assertFalse(result["isError"])
        self.assertEqual(len(reg.calls), 1)
        # A duplicate/budget bypass that appears only after an upstream rewrite still
        # hits this same final boundary and never executes twice.
        with self.assertRaisesRegex(RpcError, "host scope"):
            srv.dispatch("tools/call", {"name": "haven_status", "arguments": {}})
        self.assertEqual(len(reg.calls), 1)

    def test_operator_policy_mutation_blocks_list_and_call(self):
        reg = FakeRegistry(["haven_status"])
        gate = self.gate(raw_policy())
        srv = Server(reg, name="haven", version="test", instructions="i", scope_gate=gate)
        self.write_policy(raw_policy(max_calls=2))
        with self.assertRaisesRegex(RpcError, "policy unavailable"):
            srv.dispatch("tools/list", {})
        with self.assertRaisesRegex(RpcError, "host scope"):
            srv.dispatch("tools/call", {"name": "haven_status", "arguments": {}})
        self.assertEqual(reg.calls, [])

    def test_zero_tool_operator_surface_is_real(self):
        p = {
            "schema": scope.SCHEMA, "allowed_tools": [], "max_calls": 0,
            "per_tool_max": {}, "unique_calls": True, "argument_rules": {},
        }
        reg = FakeRegistry(["haven_status"])
        srv = Server(reg, name="haven", version="test", instructions="i",
                     scope_gate=self.gate(p))
        self.assertEqual(srv.dispatch("tools/list", {})["tools"], [])
        with self.assertRaisesRegex(RpcError, "host scope"):
            srv.dispatch("tools/call", {"name": "haven_status", "arguments": {}})
        self.assertEqual(reg.calls, [])

    def test_cyber_final_nested_target_rechecked_before_registry(self):
        reg = FakeRegistry([])
        gate = self.gate(cyber_policy())
        wrong = {"snapshot_path": "/etc/hosts"}
        with self.assertRaises(cyber_mcp.ToolError) as caught:
            cyber_mcp._dispatch_cyber_call(reg, gate, "entra.ca.assess", wrong)
        self.assertEqual(caught.exception.code, "scope_denied")
        self.assertEqual(reg.calls, [])

        good = {"snapshot_path": "fixtures/tenants/contoso-weak.json"}
        out = cyber_mcp._dispatch_cyber_call(reg, gate, "entra.ca.assess", good)
        self.assertTrue(out["ok"])
        self.assertEqual(len(reg.calls), 1)
        self.assertEqual(reg.calls[0][0], "entra.ca.assess")

    def test_cyber_inner_tool_rewrite_never_dispatches(self):
        reg = FakeRegistry([])
        gate = self.gate(cyber_policy())
        good = {"snapshot_path": "fixtures/tenants/contoso-weak.json"}
        with self.assertRaises(cyber_mcp.ToolError) as caught:
            cyber_mcp._dispatch_cyber_call(reg, gate, "findings.lookup", good)
        self.assertEqual(caught.exception.code, "scope_denied")
        self.assertEqual(reg.calls, [])

    def test_cyber_duplicate_final_dispatch_blocks(self):
        reg = FakeRegistry([])
        gate = self.gate(cyber_policy())
        good = {"snapshot_path": "fixtures/tenants/contoso-weak.json"}
        cyber_mcp._dispatch_cyber_call(reg, gate, "entra.ca.assess", good)
        with self.assertRaises(cyber_mcp.ToolError) as caught:
            cyber_mcp._dispatch_cyber_call(reg, gate, "entra.ca.assess", good)
        self.assertEqual(caught.exception.code, "scope_denied")
        self.assertEqual(len(reg.calls), 1)

    def test_required_guarded_mode_refuses_missing_policy(self):
        with self.assertRaisesRegex(runtime.ScopeDenied, "POLICY_REQUIRED"):
            runtime.from_env({
                runtime.REQUIRED_ENV: "1",
                runtime.ROOT_ENV: str(AUG),
            })

    def test_policy_file_must_be_private_regular_file(self):
        self.write_policy(raw_policy())
        self.policy_path.chmod(0o644)
        with self.assertRaisesRegex(runtime.ScopeDenied, "INSECURE_POLICY_FILE"):
            runtime.McpScopeGate(str(self.policy_path), augmentation_root=AUG)


if __name__ == "__main__":
    unittest.main()
