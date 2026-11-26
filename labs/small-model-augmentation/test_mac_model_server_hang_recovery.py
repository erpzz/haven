from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

AUG = Path(__file__).resolve().parent
RED = AUG / "red_factory"
if str(AUG) not in sys.path:
    sys.path.insert(0, str(AUG))
if str(RED) not in sys.path:
    sys.path.insert(0, str(RED))

import mac_case_qualification as mac
import mac_model_server_hang_recovery as hang


FAKE_LLAMA = r'''#!/usr/bin/env python3
import http.server, json, sys
args = sys.argv[1:]
port = int(args[args.index("--port") + 1])
alias = args[args.index("--alias") + 1]
ctx = int(args[args.index("-c") + 1])

class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    def log_message(self, *a):
        pass
    def sendj(self, value):
        raw = json.dumps(value, separators=(",", ":")).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_GET(self):
        if self.path == "/v1/models":
            return self.sendj({
                "object": "list",
                "data": [{"id": alias, "object": "model"}],
            })
        if self.path == "/props":
            return self.sendj({
                "default_generation_settings": {"n_ctx": ctx},
            })
        self.send_response(404)
        self.end_headers()
    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        size = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(size)
        self.sendj({
            "id": "fixture",
            "object": "chat.completion",
            "model": alias,
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
        })

http.server.ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
'''


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def private_json(path: Path, value) -> None:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode() + b"\n"
    fd = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)


class OwnerProbe:
    def __call__(self, port, pid):
        return {pid}


@unittest.skipUnless(os.name == "posix", "requires SIGSTOP/SIGKILL and POSIX flock")
class ServerHangRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

        self.server = self.root / "fake-llama-server"
        self.server.write_text(FAKE_LLAMA)
        self.server.chmod(self.server.stat().st_mode | stat.S_IXUSR)
        self.model = self.root / "model.gguf"
        self.model.write_bytes(b"fixture-model")

        enrollment = {
            "schema": mac.ENROLLMENT_SCHEMA,
            "hermes_sha256": "1" * 64,
            "hermes_version": "0.21.5",
            "hermes_release_date": "2026.9.24",
            "hermes_python_sha256": "2" * 64,
            "hermes_runtime_source_sha256": "3" * 64,
            "hermes_config_sha256": "4" * 64,
            "hermes_profile_env_sha256": "5" * 64,
        }
        for key, path in mac.SOURCE_BINDINGS.items():
            enrollment[key] = sha(path)
        self.assertEqual(set(enrollment), mac.ENROLLMENT_KEYS)
        self.enrollment = self.root / "enrollment.json"
        private_json(self.enrollment, enrollment)

    def test_owned_server_is_stopped_request_blocks_then_resume_completes(self):
        out = self.root / "out"
        result = hang.run_server_hang_recovery_qualification(
            enrollment_path=self.enrollment,
            server=self.server,
            server_sha256=sha(self.server),
            model=self.model,
            model_sha256=sha(self.model),
            alias="fixture-model",
            out_dir=out,
            port=0,
            context=65536,
            start_timeout=5,
            request_timeout=5,
            hang_observation_seconds=0.2,
            interrupt_max_tokens=8,
            resume_max_tokens=8,
            require_apfs=False,
            owner_probe=OwnerProbe(),
        )

        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["hang_injection"], "SIGSTOP")
        self.assertTrue(result["server_side_hang_proven"])
        self.assertFalse(result["natural_server_hang_proven"])
        self.assertTrue(result["connection_established_before_stop"])
        self.assertTrue(result["request_sent_while_server_stopped"])
        self.assertTrue(result["response_absent_during_stop_observation"])
        self.assertTrue(result["competing_owner_blocked"])
        self.assertTrue(result["lease_reacquired_after_hang"])
        self.assertTrue(result["final_state"]["run_completed"])
        self.assertEqual(result["final_state"]["completed_units"], ["model-request"])
        self.assertEqual(result["interrupted_state"]["retryable_units"], [{
            "unit": "model-request",
            "next_attempt": 2,
            "pending_model_requests": 1,
            "uncertain_replay_safe_tools": 0,
        }])
        self.assertRegex(result["request_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(result["response_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(result["receipt_sha256"], r"^[0-9a-f]{64}$")
        receipt_path = out / "server-hang-recovery.json"
        self.assertTrue(receipt_path.is_file())
        self.assertEqual(stat.S_IMODE(receipt_path.stat().st_mode), 0o600)

    def test_receipt_contract_cannot_call_injected_hang_natural(self):
        source = (RED / "mac_model_server_hang_recovery.py").read_text()
        self.assertIn('"hang_injection": "SIGSTOP"', source)
        self.assertIn('"server_side_hang_proven": True', source)
        self.assertIn('"natural_server_hang_proven": False', source)


if __name__ == "__main__":
    unittest.main()
