"""Deterministic tests for guarded Hermes plugin preflight."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import hermes_plugin_preflight as preflight


AUG = Path(__file__).resolve().parent
SOURCE_PLUGIN = AUG / "hermes_scope_plugin"


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


FAKE_HERMES = """#!/usr/bin/env python3
import json, os, pathlib, sys

args = sys.argv[1:]
if args[:2] == ["plugins", "list"]:
    row = {
        "name": "haven-scope",
        "status": os.environ.get("FAKE_STATUS", "enabled"),
        "version": os.environ.get("FAKE_VERSION", "0.1.0"),
        "description": "fixture",
        "source": os.environ.get("FAKE_SOURCE", "user"),
        "removed": None if os.environ.get("FAKE_REMOVED", "0") == "0" else "removed",
    }
    rows = [row]
    if os.environ.get("FAKE_EXTRA", "0") == "1":
        rows.append({
            "name": "surprise-plugin", "status": "enabled", "version": "1",
            "description": "x", "source": "user", "removed": None,
        })
    if os.environ.get("FAKE_DUP", "0") == "1":
        rows.append(dict(row))
    sys.stdout.write(json.dumps(rows))
    raise SystemExit(int(os.environ.get("FAKE_LIST_EXIT", "0")))

if args[:2] == ["plugins", "doctor"]:
    if os.environ.get("FAKE_MUTATE", "0") == "1":
        home = pathlib.Path(os.environ["HERMES_HOME"])
        p = home / "plugins" / "haven-scope" / "__init__.py"
        p.write_text(p.read_text() + "\\n# mutated by fixture\\n")
    raise SystemExit(int(os.environ.get("FAKE_DOCTOR_EXIT", "0")))

raise SystemExit(9)
"""


class HermesPluginPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.home = root / "home"
        self.home.mkdir()
        self.plugin = self.home / "plugins" / preflight.PLUGIN_NAME
        self.plugin.mkdir(parents=True)
        shutil.copyfile(SOURCE_PLUGIN / "__init__.py", self.plugin / "__init__.py")
        shutil.copyfile(SOURCE_PLUGIN / "plugin.yaml", self.plugin / "plugin.yaml")
        (self.plugin / "README.md").write_text("fixture\n")
        self.hermes = root / "hermes"
        self.hermes.write_text(FAKE_HERMES)
        self.hermes.chmod(0o700)
        self.hermes_sha = sha(self.hermes)
        self.init_sha = sha(self.plugin / "__init__.py")
        self.manifest_sha = sha(self.plugin / "plugin.yaml")

    def run(self, **env):
        child = dict(os.environ)
        child.update({k: str(v) for k, v in env.items()})
        return preflight.run_preflight(
            hermes=self.hermes,
            hermes_home=self.home,
            hermes_sha256=self.hermes_sha,
            init_sha256=self.init_sha,
            manifest_sha256=self.manifest_sha,
            allowed_user_plugins=[preflight.PLUGIN_NAME],
            timeout=10,
            env=child,
        )

    def test_exact_profile_passes_and_receipt_binds_bytes(self):
        result = self.run()
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["hermes_sha256"], self.hermes_sha)
        self.assertEqual(result["plugin_init_sha256"], self.init_sha)
        self.assertEqual(result["plugin_manifest_sha256"], self.manifest_sha)
        self.assertEqual(result["enabled_user_plugin_count"], 1)
        self.assertTrue(result["doctor_passed"])

    def test_unexpected_enabled_user_plugin_blocks(self):
        result = self.run(FAKE_EXTRA=1)
        self.assertEqual(result["status"], "block")
        self.assertEqual(result["errors"], ["UNEXPECTED_ENABLED_USER_PLUGIN"])

    def test_duplicate_plugin_row_blocks_malformed_listing(self):
        result = self.run(FAKE_DUP=1)
        self.assertEqual(result["errors"], ["INVALID_PLUGIN_LIST"])

    def test_scope_plugin_status_version_source_and_removed_are_bound(self):
        cases = [
            ({"FAKE_STATUS": "not enabled"}, "SCOPE_PLUGIN_NOT_ENABLED"),
            ({"FAKE_VERSION": "9.9"}, "SCOPE_PLUGIN_VERSION_MISMATCH"),
            ({"FAKE_SOURCE": "project"}, "SCOPE_PLUGIN_SOURCE_MISMATCH"),
            ({"FAKE_REMOVED": "1"}, "SCOPE_PLUGIN_REMOVED"),
        ]
        for env, code in cases:
            with self.subTest(code=code):
                self.assertEqual(self.run(**env)["errors"], [code])

    def test_list_or_doctor_failure_blocks(self):
        self.assertEqual(self.run(FAKE_LIST_EXIT=3)["errors"], ["PLUGIN_LIST_FAILED"])
        self.assertEqual(self.run(FAKE_DOCTOR_EXIT=3)["errors"], ["PLUGIN_DOCTOR_FAILED"])

    def test_plugin_code_and_manifest_hash_mismatch_block(self):
        self.assertEqual(
            preflight.run_preflight(
                hermes=self.hermes, hermes_home=self.home,
                hermes_sha256=self.hermes_sha, init_sha256="1" * 64,
                manifest_sha256=self.manifest_sha,
                allowed_user_plugins=[preflight.PLUGIN_NAME], env=os.environ,
            )["errors"],
            ["PLUGIN_CODE_HASH_MISMATCH"],
        )
        self.assertEqual(
            preflight.run_preflight(
                hermes=self.hermes, hermes_home=self.home,
                hermes_sha256=self.hermes_sha, init_sha256=self.init_sha,
                manifest_sha256="2" * 64,
                allowed_user_plugins=[preflight.PLUGIN_NAME], env=os.environ,
            )["errors"],
            ["PLUGIN_MANIFEST_HASH_MISMATCH"],
        )

    def test_unexpected_plugin_source_file_blocks(self):
        (self.plugin / "backdoor.py").write_text("raise SystemExit\n")
        self.assertEqual(self.run()["errors"], ["UNEXPECTED_PLUGIN_FILE"])

    def test_symlinked_plugin_code_blocks(self):
        target = Path(self.tmp.name) / "elsewhere.py"
        target.write_text((self.plugin / "__init__.py").read_text())
        (self.plugin / "__init__.py").unlink()
        (self.plugin / "__init__.py").symlink_to(target)
        self.assertEqual(self.run()["errors"], ["ENROLLED_FILE_UNAVAILABLE"])

    def test_hermes_hash_and_executable_are_enrolled(self):
        bad = preflight.run_preflight(
            hermes=self.hermes, hermes_home=self.home,
            hermes_sha256="3" * 64, init_sha256=self.init_sha,
            manifest_sha256=self.manifest_sha,
            allowed_user_plugins=[preflight.PLUGIN_NAME],
        )
        self.assertEqual(bad["errors"], ["HERMES_HASH_MISMATCH"])
        self.hermes.chmod(0o600)
        not_exec = preflight.run_preflight(
            hermes=self.hermes, hermes_home=self.home,
            hermes_sha256=self.hermes_sha, init_sha256=self.init_sha,
            manifest_sha256=self.manifest_sha,
            allowed_user_plugins=[preflight.PLUGIN_NAME],
        )
        self.assertEqual(not_exec["errors"], ["HERMES_NOT_EXECUTABLE"])

    def test_doctor_time_mutation_is_detected(self):
        result = self.run(FAKE_MUTATE=1)
        self.assertEqual(result["errors"], ["PLUGIN_CODE_HASH_MISMATCH"])

    def test_invalid_allowlist_or_hash_fails_without_exec(self):
        bad_set = preflight.run_preflight(
            hermes=self.hermes, hermes_home=self.home,
            hermes_sha256=self.hermes_sha, init_sha256=self.init_sha,
            manifest_sha256=self.manifest_sha,
            allowed_user_plugins=["other"],
        )
        self.assertEqual(bad_set["errors"], ["INVALID_ALLOWED_PLUGIN_SET"])
        bad_hash = preflight.run_preflight(
            hermes=self.hermes, hermes_home=self.home,
            hermes_sha256="nope", init_sha256=self.init_sha,
            manifest_sha256=self.manifest_sha,
            allowed_user_plugins=[preflight.PLUGIN_NAME],
        )
        self.assertEqual(bad_hash["errors"], ["INVALID_ENROLLED_HASH"])

    def test_receipt_does_not_echo_cli_output_or_home(self):
        result = self.run(FAKE_DOCTOR_EXIT=3)
        encoded = json.dumps(result)
        self.assertNotIn(str(self.home), encoded)
        self.assertNotIn("fixture", encoded)


if __name__ == "__main__":
    unittest.main()
