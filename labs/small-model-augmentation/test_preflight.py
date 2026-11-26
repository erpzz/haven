import json
from pathlib import Path
import subprocess
import sys
import unittest

import preflight


def manifest(**overrides):
    return {"expected_model": "fixture-model-9b", "requested_model": "fixture-model-9b",
            "observed_model_ids": ["fixture-model-9b"], "observed_context_tokens": 65536,
            **overrides}


class PreflightTests(unittest.TestCase):
    def test_valid(self):
        result = preflight.check(manifest())
        self.assertEqual(result["status"], "pass")
        self.assertFalse(result["weight_identity_verified"])
        self.assertFalse(result["live_endpoint_verified"])

    def test_requested_mismatch(self):
        self.assertIn("REQUESTED_MODEL_MISMATCH", preflight.check(manifest(requested_model="fixture-model-4b"))["errors"])

    def test_wrong_server(self):
        self.assertIn("OBSERVED_MODEL_MISMATCH", preflight.check(manifest(observed_model_ids=["fixture-model-4b"]))["errors"])

    def test_ambiguous_inventory(self):
        self.assertEqual(preflight.check(manifest(observed_model_ids=["fixture-model-9b", "other-model"]))["status"], "block")

    def test_duplicate_inventory(self):
        self.assertIn("DUPLICATE_OBSERVED_MODELS", preflight.check(manifest(observed_model_ids=["fixture-model-9b"] * 2))["errors"])

    def test_missing_or_extra_fields(self):
        for field in manifest():
            doc = manifest()
            del doc[field]
            self.assertEqual(preflight.check(doc)["status"], "block")
        self.assertEqual(preflight.check(manifest(extra="anything"))["status"], "block")

    def test_bad_ids(self):
        for value in (None, "", "<MODEL_ID>", "${MODEL}", "model-id", "TODO", " model", True, 42):
            for field in ("expected_model", "requested_model"):
                with self.subTest(field=field, value=value):
                    self.assertEqual(preflight.check(manifest(**{field: value}))["status"], "block")
        for value in ([], None, "fixture-model-9b", [None], ["<MODEL>"]):
            self.assertEqual(preflight.check(manifest(observed_model_ids=value))["status"], "block")

    def test_context(self):
        for value in (8192, 63999, None, True, "65536", 65536.0):
            self.assertEqual(preflight.check(manifest(observed_context_tokens=value))["status"], "block")
        self.assertEqual(preflight.check(manifest(observed_context_tokens=64000))["status"], "pass")

    def test_exact_case(self):
        self.assertEqual(preflight.check(manifest(requested_model="Fixture-model-9b"))["status"], "block")

    def test_parse_failures(self):
        for value in (b"{", b"\xff", b'{"a":1,"a":2}', b"[]", b"[" * 2000 + b"]" * 2000, b" " * 65537):
            self.assertEqual(preflight.parse(value)["status"], "block")

    def test_cli(self):
        for doc, status in ((manifest(), 0), (manifest(expected_model="private-fixture-value"), 2)):
            run = subprocess.run([sys.executable, str(Path(preflight.__file__))], input=json.dumps(doc), text=True, capture_output=True)
            self.assertEqual(run.returncode, status)
            self.assertEqual(json.loads(run.stdout)["status"], "pass" if status == 0 else "block")
            self.assertNotIn("private-fixture-value", run.stdout + run.stderr)
            self.assertEqual(run.stderr, "")


if __name__ == "__main__":
    unittest.main()
