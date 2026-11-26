import json
import tempfile
import unittest
from pathlib import Path

from mcp_fixture import (
    FIXTURE_SCHEMA,
    LOG_SCHEMA,
    fixture_for_case,
    handle,
    load_fixture,
)
from red_factory import make_case
from mcp_scope_runtime import McpScopeGate


def guarded_policy(case, fixture):
    allowed = list(case.tool_policy.allowed_tools)
    rules = {}
    for name in allowed:
        rules[name] = {
            "allowed_keys": ["object"],
            "required_keys": ["object"],
            "exact_values": {"/object": [fixture["object"]]},
        }
    return {
        "schema": "haven.tool-scope.v1",
        "allowed_tools": allowed,
        "max_calls": case.tool_policy.max_total_calls,
        "per_tool_max": {name: case.tool_policy.max_per_tool for name in allowed},
        "unique_calls": not case.tool_policy.allow_duplicate_calls,
        "argument_rules": rules,
    }


def make_gate(tmp, case, fixture):
    path = Path(tmp) / "scope.json"
    path.write_text(json.dumps(guarded_policy(case, fixture)))
    path.chmod(0o600)
    return McpScopeGate(str(path), augmentation_root=Path(__file__).resolve().parents[1])


class McpFixtureTests(unittest.TestCase):
    def test_fixture_binds_case_and_trusted_evidence(self):
        case = make_case("stale_premise", 7)
        fixture = fixture_for_case(case)
        self.assertEqual(fixture["schema"], FIXTURE_SCHEMA)
        self.assertEqual(fixture["case_id"], case.case_id)
        self.assertEqual(fixture["object"], "alpha-0007")
        self.assertEqual(fixture["allowed_tools"], ["read_fixture"])
        self.assertIn("current_owner=beta-0007", fixture["read_result"])
        self.assertNotIn("old_owner=gamma-0007", fixture["read_result"])
        self.assertEqual(len(fixture["fixture_sha256"]), 64)

    def test_tools_list_is_exact_case_authorized_surface(self):
        case = make_case("no_evidence", 1)
        fixture = fixture_for_case(case)
        with tempfile.TemporaryDirectory() as tmp:
            result = handle(
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                fixture,
                Path(tmp) / "calls.jsonl",
            )
        names = [tool["name"] for tool in result["result"]["tools"]]
        self.assertEqual(names, ["read_fixture"])

        zero = fixture_for_case(make_case("unauthorized_effect", 2))
        with tempfile.TemporaryDirectory() as tmp:
            result = handle(
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                zero,
                Path(tmp) / "calls.jsonl",
            )
        self.assertEqual(result["result"]["tools"], [])

    def test_read_fixture_returns_trusted_record_and_logs_call(self):
        case = make_case("duplicate_read", 5)
        fixture = fixture_for_case(case)
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.jsonl"
            response = handle(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "read_fixture", "arguments": {"object": "alpha-0005"}},
                },
                fixture,
                log,
            )
            self.assertFalse(response["result"]["isError"])
            self.assertIn("state=beta-0005", response["result"]["content"][0]["text"])
            row = json.loads(log.read_text())
            self.assertEqual(row["schema"], LOG_SCHEMA)
            self.assertEqual(row["tool"], "read_fixture")
            self.assertEqual(row["arguments"], {"object": "alpha-0005"})
            self.assertEqual(len(row["call_sha256"]), 64)

    def test_wrong_read_target_is_not_found(self):
        case = make_case("duplicate_read", 5)
        fixture = fixture_for_case(case)
        with tempfile.TemporaryDirectory() as tmp:
            response = handle(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "read_fixture", "arguments": {"object": "beta-0005"}},
                },
                fixture,
                Path(tmp) / "calls.jsonl",
            )
        self.assertEqual(response["result"]["content"][0]["text"], "lookup_result=not_found")

    def test_canary_has_no_side_effect_but_is_logged(self):
        case = make_case("unauthorized_effect", 2)
        fixture = fixture_for_case(case)
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "owned.txt"
            log = Path(tmp) / "calls.jsonl"
            response = handle(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "write_canary",
                        "arguments": {"object": "alpha-0002", "value": str(marker)},
                    },
                },
                fixture,
                log,
            )
            self.assertTrue(response["result"]["isError"])
            self.assertFalse(marker.exists())
            row = json.loads(log.read_text())
            self.assertEqual(row["tool"], "write_canary")

    def test_final_scope_denies_hidden_canary_before_dispatch_log(self):
        case = make_case("unauthorized_effect", 22)
        fixture = fixture_for_case(case)
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.jsonl"
            deny = Path(tmp) / "denials.jsonl"
            gate = make_gate(tmp, case, fixture)
            response = handle(
                {
                    "jsonrpc": "2.0", "id": 40, "method": "tools/call",
                    "params": {
                        "name": "write_canary",
                        "arguments": {"object": "alpha-0022", "value": "synthetic"},
                    },
                },
                fixture,
                log,
                gate,
                deny,
            )
            self.assertEqual(response["error"]["code"], -32602)
            self.assertIn("host scope", response["error"]["message"])
            self.assertFalse(log.exists())
            row = json.loads(deny.read_text())
            self.assertEqual(row["tool"], "write_canary")
            self.assertEqual(row["reason"], "host_scope_denied")
            self.assertEqual(len(row["denial_sha256"]), 64)

    def test_final_scope_denies_wrong_target_before_dispatch_log(self):
        case = make_case("duplicate_read", 23)
        fixture = fixture_for_case(case)
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.jsonl"
            deny = Path(tmp) / "denials.jsonl"
            gate = make_gate(tmp, case, fixture)
            response = handle(
                {
                    "jsonrpc": "2.0", "id": 41, "method": "tools/call",
                    "params": {
                        "name": "read_fixture",
                        "arguments": {"object": "beta-0023"},
                    },
                },
                fixture,
                log,
                gate,
                deny,
            )
            self.assertEqual(response["error"]["code"], -32602)
            self.assertFalse(log.exists())
            row = json.loads(deny.read_text())
            self.assertEqual(row["arguments"], {"object": "beta-0023"})
            self.assertEqual(row["reason"], "host_scope_denied")

    def test_final_scope_allows_one_exact_read_then_blocks_duplicate(self):
        case = make_case("duplicate_read", 24)
        fixture = fixture_for_case(case)
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.jsonl"
            deny = Path(tmp) / "denials.jsonl"
            gate = make_gate(tmp, case, fixture)
            request = {
                "jsonrpc": "2.0", "id": 42, "method": "tools/call",
                "params": {
                    "name": "read_fixture",
                    "arguments": {"object": "alpha-0024"},
                },
            }
            first = handle(request, fixture, log, gate, deny)
            second = handle({**request, "id": 43}, fixture, log, gate, deny)
            self.assertFalse(first["result"]["isError"])
            self.assertEqual(second["error"]["code"], -32602)
            rows = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["tool"], "read_fixture")
            denied = [json.loads(line) for line in deny.read_text().splitlines()]
            self.assertEqual(len(denied), 1)
            self.assertEqual(denied[0]["tool"], "read_fixture")
            self.assertEqual(denied[0]["reason"], "host_scope_denied")

    def test_final_scope_tools_list_cannot_widen_case_surface(self):
        case = make_case("unauthorized_effect", 25)
        fixture = fixture_for_case(case)
        with tempfile.TemporaryDirectory() as tmp:
            gate = make_gate(tmp, case, fixture)
            result = handle(
                {"jsonrpc": "2.0", "id": 44, "method": "tools/list", "params": {}},
                fixture,
                Path(tmp) / "calls.jsonl",
                gate,
            )
            self.assertEqual(result["result"]["tools"], [])

    def test_fixture_file_hash_tamper_rejected(self):
        case = make_case("no_evidence", 3)
        fixture = fixture_for_case(case)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.json"
            fixture["read_result"] = "tampered"
            path.write_text(json.dumps(fixture))
            with self.assertRaises(ValueError):
                load_fixture(path)


if __name__ == "__main__":
    unittest.main()
