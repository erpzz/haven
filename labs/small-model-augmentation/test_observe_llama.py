import contextlib
import http.server
import json
import socket
import subprocess
import sys
import threading
import unittest
from pathlib import Path

import observe_llama


class State:
    model_ids = ["fixture-model-9b"]
    context = 65536
    models_count = 0
    mode = "normal"


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/v1/models":
            State.models_count += 1
            if State.mode == "redirect":
                self.send_response(302)
                self.send_header("Location", "http://example.invalid/")
                self.end_headers()
                return
            if State.mode == "oversize":
                body = b"{" + b" " * (observe_llama.MAX_RESPONSE_BYTES + 1) + b"}"
            elif State.mode == "duplicate":
                body = b'{"data":[],"data":[]}'
            elif State.mode == "bad_models_schema":
                body = b'{"data":[{"id":null}]}'
            else:
                ids = State.model_ids
                if State.mode == "swap" and State.models_count > 1:
                    ids = ["fixture-model-4b"]
                body = json.dumps({"object": "list", "data": [{"id": x, "object": "model"} for x in ids]}).encode()
        elif self.path == "/props":
            if State.mode == "bad_props_schema":
                body = b'{"default_generation_settings":{"n_ctx":true}}'
            else:
                body = json.dumps({"default_generation_settings": {"n_ctx": State.context},
                                   "model_path": "/private/should/not/appear"}).encode()
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        if State.mode != "no_length":
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@contextlib.contextmanager
def server():
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


class ObserverTests(unittest.TestCase):
    def setUp(self):
        State.model_ids = ["fixture-model-9b"]
        State.context = 65536
        State.models_count = 0
        State.mode = "normal"

    def test_valid_live_observation(self):
        with server() as base:
            result = observe_llama.check_runtime("fixture-model-9b", "fixture-model-9b", base)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["live_endpoint_verified"])
        self.assertFalse(result["weight_identity_verified"])

    def test_wrong_model_and_low_context(self):
        with server() as base:
            State.model_ids = ["fixture-model-4b"]
            State.context = 8192
            result = observe_llama.check_runtime("fixture-model-9b", "fixture-model-9b", base)
        self.assertEqual(result["status"], "block")
        self.assertEqual(set(result["errors"]), {"OBSERVED_MODEL_MISMATCH", "CONTEXT_UNVERIFIED_OR_TOO_SMALL"})
        self.assertFalse(result["live_endpoint_verified"])

    def test_requested_model_mismatch(self):
        with server() as base:
            result = observe_llama.check_runtime("fixture-model-9b", "fixture-model-4b", base)
        self.assertIn("REQUESTED_MODEL_MISMATCH", result["errors"])

    def test_rejects_non_loopback_and_url_tricks_without_network(self):
        bad = ["http://localhost:1", "http://127.0.0.2:1", "https://127.0.0.1:1",
               "http://user@127.0.0.1:1", "http://127.0.0.1:1/v1",
               "http://127.0.0.1:1?x=1", "http://127.0.0.1:1#x",
               "http://127.0.0.1", "http://127.0.0.1:0", "http://127.0.0.1:65536",
               "http://2130706433:1", "http://0x7f000001:1", "file:///etc/passwd", ""]
        for value in bad:
            with self.subTest(value=value):
                self.assertEqual(observe_llama.check_runtime("fixture-model-9b", "fixture-model-9b", value)["errors"], ["INVALID_BASE_URL"])

    def test_redirect_not_followed(self):
        State.mode = "redirect"
        with server() as base:
            result = observe_llama.check_runtime("fixture-model-9b", "fixture-model-9b", base)
        self.assertEqual(result["errors"], ["MODELS_OBSERVATION_FAILED"])

    def test_bounded_and_strict_json(self):
        for mode, code in (("oversize", "MODELS_OBSERVATION_FAILED"),
                           ("duplicate", "MODELS_OBSERVATION_FAILED"),
                           ("bad_models_schema", "MODELS_SCHEMA_INVALID"),
                           ("bad_props_schema", "PROPS_SCHEMA_INVALID")):
            State.mode = mode
            State.models_count = 0
            with server() as base:
                result = observe_llama.check_runtime("fixture-model-9b", "fixture-model-9b", base)
            self.assertEqual(result["errors"], [code])

    def test_server_change_during_check(self):
        State.mode = "swap"
        with server() as base:
            result = observe_llama.check_runtime("fixture-model-9b", "fixture-model-9b", base)
        self.assertEqual(result["errors"], ["SERVER_CHANGED_DURING_CHECK"])

    def test_dead_port_fails_closed(self):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        result = observe_llama.check_runtime("fixture-model-9b", "fixture-model-9b", f"http://127.0.0.1:{port}")
        self.assertEqual(result["errors"], ["MODELS_OBSERVATION_FAILED"])

    def test_invalid_expected_or_requested_skips_network(self):
        self.assertEqual(observe_llama.check_runtime("TODO", "fixture-model-9b", "http://127.0.0.1:1")["errors"], ["INVALID_EXPECTED_MODEL"])
        self.assertEqual(observe_llama.check_runtime("fixture-model-9b", "TODO", "http://127.0.0.1:1")["errors"], ["INVALID_REQUESTED_MODEL"])

    def test_cli_redacts_server_private_fields(self):
        with server() as base:
            run = subprocess.run([sys.executable, str(Path(observe_llama.__file__)),
                                  "--expected-model", "fixture-model-9b",
                                  "--requested-model", "fixture-model-9b", "--base-url", base],
                                 text=True, capture_output=True)
        self.assertEqual(run.returncode, 0)
        self.assertEqual(json.loads(run.stdout)["status"], "pass")
        self.assertNotIn("/private/should/not/appear", run.stdout + run.stderr)
        self.assertEqual(run.stderr, "")

    def test_no_content_length_still_bounded(self):
        State.mode = "no_length"
        with server() as base:
            result = observe_llama.check_runtime("fixture-model-9b", "fixture-model-9b", base)
        self.assertEqual(result["status"], "pass")

    def test_multiple_and_duplicate_model_ids_block(self):
        for ids, code in ((["fixture-model-9b", "other-model"], "OBSERVED_MODEL_MISMATCH"),
                          (["fixture-model-9b", "fixture-model-9b"], "DUPLICATE_OBSERVED_MODELS")):
            State.model_ids = ids
            State.models_count = 0
            with server() as base:
                result = observe_llama.check_runtime("fixture-model-9b", "fixture-model-9b", base)
            self.assertIn(code, result["errors"])

    def test_context_boundary_from_live_props(self):
        for context, status in ((63999, "block"), (64000, "pass"), (65536, "pass")):
            State.context = context
            State.models_count = 0
            with server() as base:
                result = observe_llama.check_runtime("fixture-model-9b", "fixture-model-9b", base)
            self.assertEqual(result["status"], status)


if __name__ == "__main__":
    unittest.main()
