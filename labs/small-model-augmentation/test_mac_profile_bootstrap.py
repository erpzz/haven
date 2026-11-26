from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

AUG = Path(__file__).resolve().parent

import mac_profile_bootstrap as bootstrap


class MacProfileBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_creates_minimal_private_profile_from_reviewed_bytes(self):
        home = Path(self.tmp.name) / "isolated"
        result = bootstrap.create_profile(
            home=home,
            augmentation_root=AUG,
        )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["enabled_user_plugins"], ["haven-scope"])
        self.assertEqual(result["mcp_servers"], ["red-factory"])
        self.assertFalse(result["project_plugins_enabled"])

        self.assertEqual(stat.S_IMODE(home.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((home / ".env").stat().st_mode), 0o600)
        self.assertEqual(
            stat.S_IMODE((home / "config.yaml").stat().st_mode), 0o600
        )
        self.assertNotIn(
            "HERMES_ENABLE_PROJECT_PLUGINS",
            (home / ".env").read_text(),
        )

        config = json.loads((home / "config.yaml").read_text())
        self.assertEqual(config["plugins"]["enabled"], ["haven-scope"])
        self.assertEqual(config["plugins"]["disabled"], [])
        self.assertEqual(set(config["mcp_servers"]), {"red-factory"})
        self.assertEqual(
            Path(config["mcp_servers"]["red-factory"]["args"][0]),
            AUG / "red_factory" / "mcp_fixture.py",
        )

        installed = home / "plugins" / "haven-scope"
        self.assertEqual(
            (installed / "__init__.py").read_bytes(),
            (AUG / "hermes_scope_plugin" / "__init__.py").read_bytes(),
        )
        self.assertEqual(
            (installed / "plugin.yaml").read_bytes(),
            (AUG / "hermes_scope_plugin" / "plugin.yaml").read_bytes(),
        )
        receipt = json.loads((home / "bootstrap-receipt.json").read_text())
        self.assertEqual(receipt["receipt_sha256"], result["receipt_sha256"])

    def test_existing_profile_is_never_modified(self):
        home = Path(self.tmp.name) / "existing"
        home.mkdir()
        marker = home / "do-not-touch"
        marker.write_text("keep")
        with self.assertRaisesRegex(bootstrap.BootstrapError, "PROFILE_ALREADY_EXISTS"):
            bootstrap.create_profile(home=home, augmentation_root=AUG)
        self.assertEqual(marker.read_text(), "keep")

    def test_relative_profile_is_refused(self):
        with self.assertRaisesRegex(bootstrap.BootstrapError, "PROFILE_PATH_NOT_ABSOLUTE"):
            bootstrap.create_profile(
                home=Path("relative-profile"),
                augmentation_root=AUG,
            )


if __name__ == "__main__":
    unittest.main()
