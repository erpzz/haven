"""Supervisor composition tests: preflight must gate #127 before launch."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import guarded_model_supervisor as supervisor


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


FAKE_OWNED = """#!/usr/bin/env python3
import os, pathlib, sys
required = [
    "HERMES_HOME", "HAVEN_AUGMENTATION_ROOT", "HAVEN_SCOPE_POLICY_FILE",
    "HAVEN_MCP_SCOPE_POLICY_FILE", "HAVEN_MCP_SCOPE_REQUIRED",
]
if any(not os.environ.get(key) for key in required):
    raise SystemExit(21)
args = sys.argv[1:]
if "--server" not in args or "--model" not in args or "--alias" not in args:
    raise SystemExit(22)
if "--" not in args:
    raise SystemExit(23)
marker = os.environ.get("SUPERVISOR_MARKER")
if marker:
    pathlib.Path(marker).write_text("launched")
raise SystemExit(int(os.environ.get("FAKE_OWNED_EXIT", "0")))
"""


class GuardedModelSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.runtime = root / "runtime"
        self.runtime.mkdir()
        self.owned = self.runtime / "owned_llama.py"
        self.observe = self.runtime / "observe_llama.py"
        self.model_preflight = self.runtime / "preflight.py"
        self.owned.write_text(FAKE_OWNED)
        self.observe.write_text("# observe fixture\n")
        self.model_preflight.write_text("# preflight fixture\n")

        self.home = root / "home"
        self.home.mkdir()
        self.aug = root / "aug"
        self.aug.mkdir()
        self.scope = root / "scope.json"
        self.mcp = root / "mcp.json"
        self.server = root / "server"
        self.model = root / "model.gguf"
        self.server.write_text("server")
        self.model.write_text("model")
        self.marker = root / "launched"

        self.plugin_args = {
            "hermes": root / "hermes",
            "hermes_home": self.home,
            "hermes_sha256": "a" * 64,
            "init_sha256": "b" * 64,
            "manifest_sha256": "c" * 64,
            "augmentation_root": self.aug,
            "scope_engine_sha256": "d" * 64,
            "scope_policy": self.scope,
            "scope_policy_sha256": "e" * 64,
            "mcp_policy": self.mcp,
            "mcp_policy_sha256": "f" * 64,
            "allowed_user_plugins": ["haven-scope"],
        }
        self.preflight_receipt = {
            "schema": "haven.hermes-plugin-preflight.v1",
            "status": "pass",
            "errors": [],
            "doctor_passed": True,
        }

    def call(self, *, preflight=None, owned_sha=None, observe_sha=None,
             model_preflight_sha=None, command=None, context=65536, env=None):
        child_env = dict(os.environ)
        child_env["SUPERVISOR_MARKER"] = str(self.marker)
        if env:
            child_env.update(env)
        with mock.patch.object(
            supervisor.plugin_preflight, "run_preflight",
            return_value=self.preflight_receipt if preflight is None else preflight,
        ):
            return supervisor.run_supervisor(
                plugin_args=self.plugin_args,
                owned_llama=self.owned,
                owned_llama_sha256=owned_sha or sha(self.owned),
                observe_llama_sha256=observe_sha or sha(self.observe),
                model_preflight_sha256=model_preflight_sha or sha(self.model_preflight),
                server=self.server,
                server_sha256="1" * 64,
                model=self.model,
                model_sha256="2" * 64,
                alias="qwythos-4b",
                port=38080,
                context=context,
                guarded_command=["fake-hermes-runner"] if command is None else command,
                env=child_env,
            )

    def test_passed_preflight_launches_enrolled_owned_llama(self):
        receipt, rc = self.call()
        self.assertEqual(receipt["status"], "pass", receipt)
        self.assertEqual(rc, 0)
        self.assertTrue(receipt["owned_llama_started"])
        self.assertEqual(receipt["owned_llama_exit"], 0)
        self.assertTrue(self.marker.exists())
        self.assertEqual(receipt["owned_llama_sha256"], sha(self.owned))
        self.assertRegex(receipt["plugin_preflight_sha256"], r"^[0-9a-f]{64}$")

    def test_blocked_preflight_never_launches_owned_llama(self):
        blocked = dict(self.preflight_receipt, status="block", errors=["X"])
        receipt, rc = self.call(preflight=blocked)
        self.assertEqual(receipt["errors"], ["PLUGIN_PREFLIGHT_BLOCKED"])
        self.assertIsNone(rc)
        self.assertFalse(self.marker.exists())
        self.assertFalse(receipt["owned_llama_started"])

    def test_owned_launcher_or_dependency_hash_mismatch_never_launches(self):
        cases = [
            {"owned_sha": "3" * 64},
            {"observe_sha": "4" * 64},
            {"model_preflight_sha": "5" * 64},
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                self.marker.unlink(missing_ok=True)
                receipt, rc = self.call(**kwargs)
                self.assertEqual(
                    receipt["errors"], ["OWNED_LLAMA_SOURCE_HASH_MISMATCH"]
                )
                self.assertIsNone(rc)
                self.assertFalse(self.marker.exists())

    def test_invalid_guarded_command_or_context_never_launches(self):
        for kwargs, code in [
            ({"command": []}, "INVALID_GUARDED_COMMAND"),
            ({"context": 8192}, "INVALID_CONTEXT"),
        ]:
            with self.subTest(code=code):
                self.marker.unlink(missing_ok=True)
                receipt, rc = self.call(**kwargs)
                self.assertEqual(receipt["errors"], [code])
                self.assertIsNone(rc)
                self.assertFalse(self.marker.exists())

    def test_owned_llama_failure_is_not_reported_as_pass(self):
        receipt, rc = self.call(env={"FAKE_OWNED_EXIT": "7"})
        self.assertEqual(rc, 7)
        self.assertEqual(receipt["status"], "block")
        self.assertEqual(receipt["errors"], ["OWNED_LLAMA_FAILED"])
        self.assertTrue(receipt["owned_llama_started"])
        self.assertTrue(self.marker.exists())

    def test_required_guard_environment_is_forced_into_child(self):
        env = {
            "HERMES_HOME": "/wrong",
            "HAVEN_AUGMENTATION_ROOT": "/wrong",
            "HAVEN_SCOPE_POLICY_FILE": "/wrong",
            "HAVEN_MCP_SCOPE_POLICY_FILE": "/wrong",
            "HAVEN_MCP_SCOPE_REQUIRED": "0",
        }
        receipt, rc = self.call(env=env)
        self.assertEqual(receipt["status"], "pass", receipt)
        self.assertEqual(rc, 0)
        self.assertTrue(self.marker.exists())

    def test_receipt_does_not_echo_paths_or_guarded_command(self):
        receipt, _ = self.call()
        encoded = json.dumps(receipt)
        self.assertNotIn(str(self.tmp.name), encoded)
        self.assertNotIn("fake-hermes-runner", encoded)


if __name__ == "__main__":
    unittest.main()
