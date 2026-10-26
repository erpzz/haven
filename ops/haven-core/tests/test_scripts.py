"""Dependency-free offline sanity checks; not host or GPU qualification."""
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bootstrap.sh"
PREFLIGHT = ROOT / "scripts" / "preflight.sh"


class BootstrapScriptTests(unittest.TestCase):
    def test_bash_syntax(self):
        for script in (SCRIPT, PREFLIGHT):
            with self.subTest(script=script.name):
                subprocess.run(["bash", "-n", str(script)], check=True, capture_output=True)

    def test_plan_is_nonmutating(self):
        result = subprocess.run(["bash", str(SCRIPT), "--plan"], check=True, text=True, capture_output=True)
        self.assertIn("PLAN ONLY", result.stdout)
        self.assertIn("openssh-server", result.stdout)

    def test_default_is_plan(self):
        result = subprocess.run(["bash", str(SCRIPT)], check=True, text=True, capture_output=True)
        self.assertIn("PLAN ONLY", result.stdout)

    def test_invalid_argument_rejected(self):
        result = subprocess.run(["bash", str(SCRIPT), "--force"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)

    def test_bootstrap_does_not_include_destructive_storage_commands(self):
        source = SCRIPT.read_text()
        for forbidden in ("mkfs.", "wipefs", "fdisk", "parted", "dd if=", "rm -rf", "curl -fsSL"):
            self.assertNotIn(forbidden, source)

    def test_preflight_does_not_request_sudo(self):
        self.assertNotIn("sudo ", PREFLIGHT.read_text())


if __name__ == "__main__":
    unittest.main()
