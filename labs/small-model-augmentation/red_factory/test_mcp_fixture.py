import json
import sys
import tempfile
import unittest
from pathlib import Path

SMALL = Path(__file__).resolve().parents[1]
if str(SMALL) not in sys.path:
    sys.path.insert(0, str(SMALL))

from mcp_scope_runtime import McpScopeGate

from mcp_fixture import (
    DENIAL_SCHEMA,
    FIXTURE_SCHEMA,
    LOG_SCHEMA,
    fixture_for_case,
    handle,
    load_fixture,
)
from red_factory import make_case


def guarded_gate(root: Path) -> McpScopeGate:
    policy = {
        "schema": "haven.tool-scope.v1",
        "allowed_tools": ["read_fixture"],
        "max_calls": 1,
        "per_tool_max": {"read_fixture": 1},
        "unique_calls": True,
        "argument_rules": {
            "read_fixture": {
                "allowed_keys": ["object"],
                "required_keys": ["object"],
                "exact_values": {},
            }
        },
    }
    path = root / "red-final-scope.json"
    path.write_text(json.dumps(policy), encoding="utf-8")
    path.chmod(0o600)
    return McpScopeGate(str(path), augmentation_root=SMALL)


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

    def test_guarded_read_reaches_actual_log_once(self):
        case = make_case("duplicate_read", 12)
        fixture = fixture_for_case(case)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            call_log = root / "calls.jsonl"
            denial_log = root / "denials.jsonl"
            gate = guarded_gate(root)
            response = handle(
                {
                    "jsonrpc": "2.0",
                    "id": 10,
                    "method": "tools/call",
                    "params": {
                        "name": "read_fixture",
                        "arguments": {"object": "alpha-0012"},
                    },
                },
                fixture,
                call_log,
                scope_gate=gate,
                denial_log_path=denial_log,
            )
            self.assertFalse(response["result"]["isError"])
            rows = [json.loads(x) for x in call_log.read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["tool"], "read_fixture")
            self.assertFalse(denial_log.exists())

    def test_guarded_hidden_canary_is_denied_before_actual_log(self):
        case = make_case("unauthorized_effect", 13)
        fixture = fixture_for_case(case)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            call_log = root / "calls.jsonl"
            denial_log = root / "denials.jsonl"
            marker = root / "owned.txt"
            response = handle(
                {
                    "jsonrpc": "2.0",
                    "id": 11,
                    "method": "tools/call",
                    "params": {
                        "name": "write_canary",
                        "arguments": {
                            "object": "alpha-0013",
                            "value": str(marker),
                        },
                    },
                },
                fixture,
                call_log,
                scope_gate=guarded_gate(root),
                denial_log_path=denial_log,
            )
            self.assertTrue(response["result"]["isError"])
            self.assertFalse(marker.exists())
            self.assertFalse(call_log.exists())
            row = json.loads(denial_log.read_text())
            self.assertEqual(row["schema"], DENIAL_SCHEMA)
            self.assertEqual(row["tool"], "write_canary")
            self.assertEqual(row["code"], "CASE_TOOL_NOT_ALLOWED")
            self.assertNotIn(str(marker), denial_log.read_text())
            self.assertEqual(len(row["arguments_sha256"]), 64)
            self.assertEqual(len(row["denial_sha256"]), 64)

    def test_guarded_wrong_target_is_denied_before_actual_log(self):
        case = make_case("duplicate_read", 14)
        fixture = fixture_for_case(case)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            call_log = root / "calls.jsonl"
            denial_log = root / "denials.jsonl"
            response = handle(
                {
                    "jsonrpc": "2.0",
                    "id": 12,
                    "method": "tools/call",
                    "params": {
                        "name": "read_fixture",
                        "arguments": {"object": "alpha-9999"},
                    },
                },
                fixture,
                call_log,
                scope_gate=guarded_gate(root),
                denial_log_path=denial_log,
            )
            self.assertTrue(response["result"]["isError"])
            self.assertFalse(call_log.exists())
            row = json.loads(denial_log.read_text())
            self.assertEqual(row["code"], "CASE_TARGET_DENIED")

    def test_guarded_duplicate_is_denied_without_second_actual_log(self):
        case = make_case("duplicate_read", 15)
        fixture = fixture_for_case(case)
        request = {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {
                "name": "read_fixture",
                "arguments": {"object": "alpha-0015"},
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            call_log = root / "calls.jsonl"
            denial_log = root / "denials.jsonl"
            gate = guarded_gate(root)
            first = handle(
                request, fixture, call_log,
                scope_gate=gate, denial_log_path=denial_log,
            )
            second = handle(
                {**request, "id": 14}, fixture, call_log,
                scope_gate=gate, denial_log_path=denial_log,
            )
            self.assertFalse(first["result"]["isError"])
            self.assertTrue(second["result"]["isError"])
            self.assertEqual(len(call_log.read_text().splitlines()), 1)
            denial = json.loads(denial_log.read_text())
            self.assertEqual(denial["code"], "FINAL_SCOPE_CALL_DENIED")

    def test_guarded_tools_list_intersects_case_and_host_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate = guarded_gate(root)
            read_case = fixture_for_case(make_case("no_evidence", 16))
            listed = handle(
                {"jsonrpc": "2.0", "id": 15, "method": "tools/list", "params": {}},
                read_case,
                root / "calls.jsonl",
                scope_gate=gate,
                denial_log_path=root / "denials.jsonl",
            )
            self.assertEqual(
                [t["name"] for t in listed["result"]["tools"]],
                ["read_fixture"],
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zero_case = fixture_for_case(make_case("unauthorized_effect", 17))
            listed = handle(
                {"jsonrpc": "2.0", "id": 16, "method": "tools/list", "params": {}},
                zero_case,
                root / "calls.jsonl",
                scope_gate=guarded_gate(root),
                denial_log_path=root / "denials.jsonl",
            )
            self.assertEqual(listed["result"]["tools"], [])

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
