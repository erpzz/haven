import json
import os
import stat
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from local_runner import main, normalize_loopback_base_url, run_case, run_suite
from red_factory import TRANSCRIPT_SCHEMA, build_suite, make_case


class ScriptedHandler(BaseHTTPRequestHandler):
    responses = []
    requests = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        type(self).requests.append({
            "path": self.path,
            "body": json.loads(body),
            "authorization": self.headers.get("Authorization"),
        })
        content = type(self).responses.pop(0)
        payload = {"choices": [{"message": {"role": "assistant", "content": content}}]}
        encoded = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt, *args):
        pass


class LocalRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), ScriptedHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}/v1"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        ScriptedHandler.responses = []
        ScriptedHandler.requests = []

    def response_for(self, case, *, decision=None, claim_ids=None, tool_calls=None):
        return json.dumps({
            "schema": TRANSCRIPT_SCHEMA,
            "case_id": case.case_id,
            "decision": case.expected_decision if decision is None else decision,
            "claim_ids": list(case.expected_claim_ids) if claim_ids is None else claim_ids,
            "tool_calls": [] if tool_calls is None else tool_calls,
        })

    def test_endpoint_is_strictly_loopback(self):
        self.assertEqual(normalize_loopback_base_url(self.base_url), self.base_url)
        bad = (
            "https://127.0.0.1:8080/v1",
            "http://example.com:8080/v1",
            "http://127.0.0.1/v1",
            "http://127.0.0.1:8080/other",
            "http://user:pass@127.0.0.1:8080/v1",
            "http://127.0.0.1:8080/v1?x=1",
        )
        for url in bad:
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalize_loopback_base_url(url)

    def test_valid_case_is_scored_and_expected_answer_is_not_leaked(self):
        case = make_case("stale_premise", 1)
        ScriptedHandler.responses.append(self.response_for(case))
        result = run_case(base_url=self.base_url, model="local-4b", case=case)
        self.assertTrue(result["score"]["pass"], result)
        self.assertNotIn("raw_output", result)
        request = ScriptedHandler.requests[0]
        self.assertEqual(request["path"], "/v1/chat/completions")
        encoded = json.dumps(request["body"], sort_keys=True)
        self.assertNotIn("expected_claim_ids", encoded)
        self.assertNotIn("expected_decision", encoded)

    def test_think_block_is_removed_but_trailing_prose_is_rejected(self):
        case = make_case("no_evidence", 2)
        good = "<think>private scratch</think>\n" + self.response_for(case)
        ScriptedHandler.responses.append(good)
        result = run_case(base_url=self.base_url, model="local-4b", case=case)
        self.assertTrue(result["score"]["pass"])

        ScriptedHandler.responses.append(self.response_for(case) + "\nextra prose")
        bad = run_case(base_url=self.base_url, model="local-4b", case=case)
        self.assertFalse(bad["score"]["pass"])
        self.assertIn("invalid_model_result", bad["score"]["violations"])

        ScriptedHandler.responses.append("prefix prose\n" + self.response_for(case))
        leading = run_case(base_url=self.base_url, model="local-4b", case=case)
        self.assertFalse(leading["score"]["pass"])

        ScriptedHandler.responses.append("<think>unfinished reasoning " + self.response_for(case))
        unclosed = run_case(base_url=self.base_url, model="local-4b", case=case)
        self.assertFalse(unclosed["score"]["pass"])

    def test_canary_proposal_is_scored_but_never_executed(self):
        case = make_case("tool_output_injection", 3)
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "should-not-exist"
            ScriptedHandler.responses.append(self.response_for(
                case,
                tool_calls=[{
                    "tool": "write_canary",
                    "arguments": {"path": str(marker), "value": "owned"},
                }],
            ))
            result = run_case(base_url=self.base_url, model="local-4b", case=case)
            self.assertFalse(result["score"]["pass"])
            self.assertIn("canary_tool_attempt", result["score"]["violations"])
            self.assertFalse(marker.exists())

    def test_wrong_target_is_scored_fail(self):
        case = make_case("stale_premise", 4)
        ScriptedHandler.responses.append(self.response_for(
            case,
            tool_calls=[{
                "tool": "read_fixture",
                "arguments": {"object": "beta-0004"},
            }],
        ))
        result = run_case(base_url=self.base_url, model="local-4b", case=case)
        self.assertFalse(result["score"]["pass"])
        self.assertIn("unauthorized_target", result["score"]["violations"])

    def test_duplicate_read_family_requires_one_exact_read(self):
        case = make_case("duplicate_read", 5)
        ScriptedHandler.responses.append(self.response_for(
            case,
            tool_calls=[{
                "tool": "read_fixture",
                "arguments": {"object": "alpha-0005"},
            }],
        ))
        result = run_case(base_url=self.base_url, model="local-4b", case=case)
        self.assertTrue(result["score"]["pass"], result)

    def test_malformed_model_output_becomes_failed_receipt(self):
        case = make_case("no_evidence", 6)
        ScriptedHandler.responses.append("not json")
        result = run_case(base_url=self.base_url, model="local-4b", case=case)
        self.assertFalse(result["score"]["pass"])
        self.assertIsNotNone(result["error"])
        self.assertEqual(len(result["output_sha256"]), 64)
        self.assertEqual(len(result["result_sha256"]), 64)

    def test_oversized_loopback_response_becomes_failed_receipt(self):
        case = make_case("no_evidence", 10)
        ScriptedHandler.responses.append("x" * (1024 * 1024 + 100))
        result = run_case(base_url=self.base_url, model="local-4b", case=case)
        self.assertFalse(result["score"]["pass"])
        self.assertIn("invalid_model_result", result["score"]["violations"])
        self.assertIn("byte budget", result["error"])

    def test_optional_api_key_is_sent_but_not_persisted_in_result(self):
        case = make_case("no_evidence", 7)
        ScriptedHandler.responses.append(self.response_for(case))
        result = run_case(
            base_url=self.base_url,
            model="local-4b",
            case=case,
            api_key="local-secret",
        )
        self.assertEqual(ScriptedHandler.requests[0]["authorization"], "Bearer local-secret")
        self.assertNotIn("api_key", result)
        self.assertNotIn("local-secret", json.dumps(result))

    def test_complete_suite_run_is_bound_and_summarized(self):
        suite = build_suite(
            seeds=[1],
            families=["stale_premise", "unauthorized_effect", "duplicate_read"],
        )
        for case in suite["cases"]:
            calls = []
            if case.family == "duplicate_read":
                calls = [{"tool": "read_fixture", "arguments": {"object": "alpha-0001"}}]
            ScriptedHandler.responses.append(self.response_for(case, tool_calls=calls))
        run = run_suite(
            base_url=self.base_url,
            model="local-4b",
            suite=suite,
        )
        self.assertEqual(run["summary"]["passes"], 3)
        self.assertEqual(run["summary"]["rate"], 1.0)
        self.assertEqual(len(run["results"]), 3)
        self.assertEqual(len(run["run_sha256"]), 64)

    def test_tampered_suite_is_rejected_before_first_request(self):
        suite = build_suite(seeds=[1], families=["stale_premise"])
        tampered = dict(suite)
        tampered["suite_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            run_suite(base_url=self.base_url, model="local-4b", suite=tampered)
        self.assertEqual(ScriptedHandler.requests, [])

    def test_cli_writes_private_receipt_and_reads_key_from_environment(self):
        case = make_case("no_evidence", 11)
        ScriptedHandler.responses.append(self.response_for(case))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "red-run.json"
            os.environ["HRF_TEST_LOCAL_KEY"] = "cli-secret"
            try:
                rc = main([
                    "--base-url", self.base_url,
                    "--model", "local-4b",
                    "--seeds", "11",
                    "--families", "no_evidence",
                    "--api-key-env", "HRF_TEST_LOCAL_KEY",
                    "--out", str(out),
                ])
            finally:
                os.environ.pop("HRF_TEST_LOCAL_KEY", None)
            self.assertEqual(rc, 0)
            self.assertTrue(out.is_file())
            self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o600)
            data = json.loads(out.read_text())
            self.assertEqual(data["summary"]["passes"], 1)
            self.assertNotIn("cli-secret", out.read_text())
            self.assertEqual(ScriptedHandler.requests[0]["authorization"], "Bearer cli-secret")

    def test_cli_existing_output_refuses_before_model_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "exists.json"
            out.write_text("{}")
            with self.assertRaises(ValueError):
                main([
                    "--base-url", self.base_url,
                    "--model", "local-4b",
                    "--seeds", "1",
                    "--families", "no_evidence",
                    "--out", str(out),
                ])
            self.assertEqual(ScriptedHandler.requests, [])

    def test_retain_raw_is_explicit(self):
        case = make_case("no_evidence", 9)
        ScriptedHandler.responses.append(self.response_for(case))
        result = run_case(
            base_url=self.base_url,
            model="local-4b",
            case=case,
            retain_raw=True,
        )
        self.assertIn("raw_output", result)
        self.assertIn("parsed_transcript", result)


if __name__ == "__main__":
    unittest.main()
