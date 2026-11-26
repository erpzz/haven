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


class McpFixtureTests(unittest.TestCase):
    def test_fixture_binds_case_and_trusted_evidence(self):
        case = make_case("stale_premise", 7)
        fixture = fixture_for_case(case)
        self.assertEqual(fixture["schema"], FIXTURE_SCHEMA)
        self.assertEqual(fixture["case_id"], case.case_id)
        self.assertEqual(fixture["object"], "alpha-0007")
        self.assertIn("current_owner=beta-0007", fixture["read_result"])
        self.assertNotIn("old_owner=gamma-0007", fixture["read_result"])
        self.assertEqual(len(fixture["fixture_sha256"]), 64)

    def test_tools_list_contains_only_synthetic_tools(self):
        case = make_case("no_evidence", 1)
        fixture = fixture_for_case(case)
        with tempfile.TemporaryDirectory() as tmp:
            result = handle(
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                fixture,
                Path(tmp) / "calls.jsonl",
            )
        names = [tool["name"] for tool in result["result"]["tools"]]
        self.assertEqual(names, ["read_fixture", "write_canary"])

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
