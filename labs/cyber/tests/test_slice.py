"""Regression tests for the end-to-end vertical slice: offline, and live against a stub OpenAI-compatible server."""
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from haven_cyber.slice import run


class Stub(BaseHTTPRequestHandler):
    replies: list = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Stub.seen.append(body)
        text = Stub.replies.pop(0)
        out = json.dumps({"choices": [{"message": {"role": "assistant", "content": text}}], "usage": {}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


class SliceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_offline_slice(self):
        rec = run("Are Global Administrators forced to use MFA, and could Conditional Access lock out emergency accounts?",
                  "fixtures/tenants/contoso-weak.json",
                  ["maester:fixtures/tool_outputs/maester-weak.json", "prowler-ocsf:fixtures/tool_outputs/prowler-weak.ocsf.json"],
                  None, "none", True, out_root=self.out)
        self.assertEqual(rec["outcome"], "ok")
        st = rec["steps"]
        self.assertEqual(st["plan"]["tool_id"], "entra.ca.assess")
        self.assertEqual(st["verify"]["problems"], [])
        self.assertGreaterEqual(st["verify"]["by_status"]["corroborated"], 10)
        self.assertIn("HCA-002", st["answer"])
        self.assertIn("HCA-005", st["answer"])
        self.assertTrue(all(r["source"].startswith("https://") for r in st["retrieve"]))
        self.assertTrue((self.out / "records.jsonl").exists())

    def test_live_path_with_stub_model_and_grounding_check(self):
        Stub.seen = []
        Stub.replies = [
            '{"tool_id": "entra.ca.assess", "arguments": {"snapshot_path": "fixtures/tenants/contoso-weak.json"}, "why": "CA question"}',
            "HCA-002 fails [R1]: ops.admin is excluded (policy e3c40a96-b703-593d-a81d-3f4de3b9cd93). HCA-005 fails. "
            "Also HCA-099 and policy 11111111-2222-3333-4444-555555555555 [R9].",
        ]
        srv = HTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            rec = run("Is MFA enforced for Global Administrators under conditional access?", "fixtures/tenants/contoso-weak.json", [],
                      f"http://127.0.0.1:{srv.server_port}/v1", "stub", False, out_root=self.out)
        finally:
            srv.shutdown()
        g = rec["steps"]["grounding"]
        self.assertEqual(rec["outcome"], "grounding_failed")  # the stub invented a rule, an id and a reference
        self.assertEqual(g["unknown_rules"], ["HCA-099"])
        self.assertEqual(g["unknown_ids"], ["11111111-2222-3333-4444-555555555555"])
        self.assertEqual(g["bad_refs"], [9])
        self.assertIn("VERIFIED EVIDENCE", Stub.seen[1]["messages"][1]["content"])

    def test_bad_tool_choice_is_contained(self):
        Stub.seen = []
        Stub.replies = ['{"tool_id": "entra.ca.assess", "arguments": {"snapshot_path": "/etc/passwd"}}']
        srv = HTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            rec = run("conditional access mfa", "fixtures/tenants/contoso-weak.json", [], f"http://127.0.0.1:{srv.server_port}/v1",
                      "stub", False, out_root=self.out)
        finally:
            srv.shutdown()
        self.assertEqual(rec["outcome"], "tool_selection_or_execution_failed")
        self.assertEqual(rec["steps"]["tool"]["error"]["code"], "path_out_of_scope")


if __name__ == "__main__":
    unittest.main()
