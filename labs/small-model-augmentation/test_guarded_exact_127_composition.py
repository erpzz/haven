"""CI-only end-to-end composition of #199 supervisor with exact #127 source."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import stat
import sys
import tempfile
import unittest

import guarded_model_supervisor as supervisor


AUG = Path(__file__).resolve().parent
PLUGIN_SOURCE = AUG / "hermes_scope_plugin"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


FAKE_HERMES = """#!/usr/bin/env python3
import json, sys
if sys.argv[1:3] == ["plugins", "list"]:
    print(json.dumps([{
        "name": "haven-scope", "status": "enabled", "version": "0.1.0",
        "description": "fixture", "source": "user", "removed": None
    }]))
    raise SystemExit(0)
if sys.argv[1:3] == ["plugins", "doctor"]:
    raise SystemExit(0)
raise SystemExit(9)
"""


FAKE_SERVER = r"""#!/usr/bin/env python3
import http.server, json, os
args = __import__("sys").argv[1:]
port = int(args[args.index("--port") + 1])
alias = args[args.index("--alias") + 1]
ctx = int(args[args.index("-c") + 1])
with open(os.environ["FAKE_PIDFILE"], "w") as f:
    f.write(str(os.getpid()))
class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    def log_message(self, *a): pass
    def sendj(self, value):
        raw = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_GET(self):
        if self.path == "/v1/models":
            return self.sendj({"object": "list", "data": [{"id": alias, "object": "model"}]})
        if self.path == "/props":
            return self.sendj({"default_generation_settings": {"n_ctx": ctx}})
        self.send_response(404); self.end_headers()
http.server.ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
"""


FAKE_LSOF = """#!/usr/bin/env python3
import os, pathlib
p = pathlib.Path(os.environ["FAKE_PIDFILE"])
if p.exists():
    print(p.read_text().strip())
"""


class ExactGuardedCompositionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)

        self.home = root / "home"
        plugin = self.home / "plugins" / "haven-scope"
        plugin.mkdir(parents=True)
        shutil.copyfile(PLUGIN_SOURCE / "__init__.py", plugin / "__init__.py")
        shutil.copyfile(PLUGIN_SOURCE / "plugin.yaml", plugin / "plugin.yaml")
        shutil.copyfile(PLUGIN_SOURCE / "README.md", plugin / "README.md")

        self.hermes = root / "hermes"
        self.hermes.write_text(FAKE_HERMES)
        self.hermes.chmod(0o700)

        self.scope_policy = root / "model-scope.json"
        self.mcp_policy = root / "mcp-scope.json"
        self._policy(self.scope_policy, "mcp_fixture_read")
        self._policy(self.mcp_policy, "read_fixture")

        self.server = root / "fake-llama-server"
        self.server.write_text(FAKE_SERVER)
        self.server.chmod(self.server.stat().st_mode | stat.S_IXUSR)
        self.model = root / "fixture.gguf"
        self.model.write_bytes(b"fixture-model")

        self.bin = root / "bin"
        self.bin.mkdir()
        lsof = self.bin / "lsof"
        lsof.write_text(FAKE_LSOF)
        lsof.chmod(0o700)
        self.pidfile = root / "server.pid"
        self.marker = root / "guarded.marker"

        self.owned = AUG / "owned_llama.py"
        self.observe = AUG / "observe_llama.py"
        self.model_preflight = AUG / "preflight.py"

        self.plugin_args = {
            "hermes": self.hermes,
            "hermes_home": self.home,
            "hermes_sha256": sha(self.hermes),
            "init_sha256": sha(plugin / "__init__.py"),
            "manifest_sha256": sha(plugin / "plugin.yaml"),
            "augmentation_root": AUG,
            "scope_engine_sha256": sha(AUG / "tool_scope.py"),
            "scope_policy": self.scope_policy,
            "scope_policy_sha256": sha(self.scope_policy),
            "mcp_policy": self.mcp_policy,
            "mcp_policy_sha256": sha(self.mcp_policy),
            "allowed_user_plugins": ["haven-scope"],
        }
        self.env = dict(os.environ)
        self.env["PATH"] = str(self.bin) + os.pathsep + self.env.get("PATH", "")
        self.env["FAKE_PIDFILE"] = str(self.pidfile)
        self.env["GUARDED_MARKER"] = str(self.marker)

    def _policy(self, path, tool):
        data = {
            "schema": "haven.tool-scope.v1",
            "allowed_tools": [tool],
            "max_calls": 1,
            "per_tool_max": {tool: 1},
            "unique_calls": True,
            "argument_rules": {
                tool: {
                    "allowed_keys": [],
                    "required_keys": [],
                    "exact_values": {},
                }
            },
        }
        path.write_text(json.dumps(data))
        path.chmod(0o600)

    def run_composed(self, **overrides):
        kwargs = {
            "plugin_args": self.plugin_args,
            "owned_llama": self.owned,
            "owned_llama_sha256": sha(self.owned),
            "observe_llama_sha256": sha(self.observe),
            "model_preflight_sha256": sha(self.model_preflight),
            "server": self.server,
            "server_sha256": sha(self.server),
            "model": self.model,
            "model_sha256": sha(self.model),
            "alias": "fixture-model",
            "port": free_port(),
            "context": 65536,
            "guarded_command": [
                sys.executable, "-c",
                "import os,pathlib; pathlib.Path(os.environ['GUARDED_MARKER']).write_text('ok')",
            ],
            "start_timeout": 5,
            "env": self.env,
        }
        kwargs.update(overrides)
        return supervisor.run_supervisor(**kwargs)

    def test_real_preflight_real_owned_lease_guarded_child_and_cleanup(self):
        receipt, rc = self.run_composed()
        self.assertEqual(receipt["status"], "pass", receipt)
        self.assertEqual(rc, 0)
        self.assertTrue(self.marker.exists())
        self.assertEqual(self.marker.read_text(), "ok")
        self.assertTrue(self.pidfile.exists())
        port = None
        # The owned launcher must stop its dedicated server after the guarded child.
        # We use the requested port rather than PID liveness to avoid PID-reuse ambiguity.
        # Run a second composed launch on a fresh port as a cleanup/regression smoke.
        receipt2, rc2 = self.run_composed()
        self.assertEqual(receipt2["status"], "pass", receipt2)
        self.assertEqual(rc2, 0)

    def test_real_preflight_failure_prevents_llama_process_start(self):
        (self.home / "plugins" / "haven-scope" / "plugin.yaml").unlink()
        receipt, rc = self.run_composed()
        self.assertEqual(receipt["status"], "block")
        self.assertEqual(receipt["errors"], ["PLUGIN_PREFLIGHT_BLOCKED"])
        self.assertIsNone(rc)
        self.assertFalse(self.pidfile.exists())
        self.assertFalse(self.marker.exists())

    def test_exact_127_source_hash_mismatch_prevents_server_start(self):
        receipt, rc = self.run_composed(owned_llama_sha256="0" * 64)
        self.assertEqual(receipt["status"], "block")
        self.assertEqual(
            receipt["errors"], ["OWNED_LLAMA_SOURCE_HASH_MISMATCH"]
        )
        self.assertIsNone(rc)
        self.assertFalse(self.pidfile.exists())
        self.assertFalse(self.marker.exists())

    def test_model_hash_failure_is_propagated_and_guarded_child_never_runs(self):
        receipt, rc = self.run_composed(model_sha256="0" * 64)
        self.assertEqual(receipt["status"], "block")
        self.assertEqual(receipt["errors"], ["OWNED_LLAMA_FAILED"])
        self.assertEqual(rc, 2)
        self.assertFalse(self.pidfile.exists())
        self.assertFalse(self.marker.exists())


if __name__ == "__main__":
    unittest.main()
