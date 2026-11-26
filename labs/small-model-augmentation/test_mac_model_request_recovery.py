from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest

AUG = Path(__file__).resolve().parent
RED = AUG / "red_factory"
if str(AUG) not in sys.path:
    sys.path.insert(0, str(AUG))
if str(RED) not in sys.path:
    sys.path.insert(0, str(RED))

import checkpoint_journal as checkpoint
import mac_model_request_recovery as recovery


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *args):
        pass

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(size)
        self.server.requests.append(raw)
        body = json.dumps({
            "id": "fixture",
            "object": "chat.completion",
            "model": "local-4b",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "OK"},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass


class ModelRequestRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.requests = []
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.journal = self.root / "checkpoint.jsonl"
        self.manifest = "a" * 64

    def _wait(self, path, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.exists():
                return
            time.sleep(0.02)
        self.fail(f"marker did not appear: {path}")

    @unittest.skipUnless(os.name == "posix", "requires POSIX flock and SIGKILL")
    def test_sent_request_sigkill_resume_and_complete(self):
        pid_marker = self.root / "pid.json"
        sent_marker = self.root / "sent.json"
        first = subprocess.Popen([
            sys.executable, str(RED / "mac_model_request_recovery.py"),
            "--child-phase", "interrupt",
            "--journal", str(self.journal),
            "--manifest-sha256", self.manifest,
            "--port", str(self.server.server_port),
            "--alias", "local-4b",
            "--pid-marker", str(pid_marker),
            "--sent-marker", str(sent_marker),
            "--max-tokens", "32",
        ])
        try:
            self._wait(sent_marker)
            pid = json.loads(pid_marker.read_text())["pid"]
            self.assertEqual(pid, first.pid)
            sent = json.loads(sent_marker.read_text())
            self.assertGreater(sent["bytes_sent"], 0)
            self.assertRegex(sent["request_sha256"], r"^[0-9a-f]{64}$")

            with self.assertRaisesRegex(RuntimeError, "live owner"):
                with checkpoint.RunLease(self.journal):
                    pass

            os.kill(pid, signal.SIGKILL)
            rc = first.wait(timeout=5)
            self.assertNotEqual(rc, 0)
        finally:
            if first.poll() is None:
                first.kill()
                first.wait()

        scan = checkpoint.scan(self.journal)
        self.assertTrue(scan.ok, scan.errors)
        state = checkpoint.resume_plan(scan.events)
        self.assertEqual(state["blocked_units"], [])
        self.assertEqual(state["retryable_units"], [{
            "unit": recovery.UNIT,
            "next_attempt": 2,
            "pending_model_requests": 1,
            "uncertain_replay_safe_tools": 0,
        }])

        with checkpoint.RunLease(self.journal):
            pass

        result = self.root / "resume.json"
        second = subprocess.run([
            sys.executable, str(RED / "mac_model_request_recovery.py"),
            "--child-phase", "resume",
            "--journal", str(self.journal),
            "--manifest-sha256", self.manifest,
            "--port", str(self.server.server_port),
            "--alias", "local-4b",
            "--result", str(result),
            "--max-tokens", "8",
        ], timeout=10)
        self.assertEqual(second.returncode, 0)
        child = json.loads(result.read_text())
        self.assertEqual(child["status"], "pass")
        self.assertRegex(child["response_sha256"], r"^[0-9a-f]{64}$")

        final_scan = checkpoint.scan(self.journal)
        self.assertTrue(final_scan.ok, final_scan.errors)
        final = checkpoint.resume_plan(final_scan.events)
        self.assertTrue(final["run_completed"])
        self.assertEqual(final["completed_units"], [recovery.UNIT])
        self.assertEqual(final["retryable_units"], [])
        self.assertEqual(final["blocked_units"], [])

        events = [row["event"] for row in final_scan.events]
        self.assertEqual(events.count("run_resumed"), 1)
        self.assertEqual(events.count("model_request_started"), 2)
        self.assertEqual(events.count("model_response_committed"), 1)

    def test_port_zero_selects_numeric_loopback_port(self):
        port = recovery._select_port(0)
        self.assertIsInstance(port, int)
        self.assertGreater(port, 0)
        self.assertLessEqual(port, 65535)

    def test_receipt_explicitly_distinguishes_server_hang_claim(self):
        # Static contract guard: this tool is intentionally not allowed to imply
        # server-side hanging from a killed client request.
        source = (RED / "mac_model_request_recovery.py").read_text()
        self.assertIn('"server_side_hang_proven": False', source)


if __name__ == "__main__":
    unittest.main()
