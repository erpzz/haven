from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

import mac_case_qualification as mac
import mac_enrollment_candidate as candidate
from local_runner import _write_private_json


class EnrollmentCandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir(mode=0o700)
        self.config = self.home / "config.yaml"
        self.config.write_text("platform_toolsets:\n  cli: []\n")
        self.config.chmod(0o600)
        self.env = self.home / ".env"
        self.env.write_text("# isolated\n")
        self.env.chmod(0o600)
        self.interpreter = Path("/bin/sh").resolve()
        self.hermes = self.root / "hermes"
        self.hermes.write_text(
            "#!" + str(self.interpreter) + chr(10)
            + 'echo "Hermes Agent v0.21.5 (2026.9.24)"' + chr(10)
        )
        self.hermes.chmod(0o700)
        self.runtime = {
            "version": "0.21.5",
            "release_date": "2026.9.24",
            "source_sha256": "c" * 64,
            "python_sha256": mac._sha_provenance_executable(self.interpreter),
        }

    def build(self):
        with mock.patch.object(
            mac, "_runtime_package_snapshot", return_value=dict(self.runtime)
        ):
            return candidate.build_candidate(
                hermes=self.hermes, hermes_home=self.home, env={}
            )

    def test_wrapper_is_unreviewed_and_inner_shape_is_exact(self):
        value = self.build()
        self.assertEqual(value["schema"], candidate.CANDIDATE_SCHEMA)
        self.assertEqual(value["review_status"], "unreviewed")
        self.assertFalse(value["qualification_runner_accepts_this_wrapper"])
        self.assertEqual(set(value["candidate"]), mac.ENROLLMENT_KEYS)
        self.assertEqual(
            value["candidate"]["hermes_runtime_source_sha256"], "c" * 64
        )
        expected = hashlib.sha256(
            json.dumps(
                value["candidate"], sort_keys=True, separators=(",", ":"),
                ensure_ascii=True, allow_nan=False,
            ).encode()
        ).hexdigest()
        self.assertEqual(value["candidate_sha256"], expected)
        self.assertEqual(len(value["wrapper_sha256"]), 64)

    def test_candidate_wrapper_is_deliberately_rejected_as_enrollment(self):
        value = self.build()
        path = self.root / "candidate.json"
        _write_private_json(path, value)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        with self.assertRaisesRegex(
            mac.QualificationError, "PRIVATE_JSON_SCHEMA_MISMATCH"
        ):
            mac._read_private_json(path, mac.ENROLLMENT_SCHEMA)

    def test_profile_files_must_already_be_private(self):
        self.config.chmod(0o644)
        with mock.patch.object(
            mac, "_runtime_package_snapshot", return_value=dict(self.runtime)
        ):
            with self.assertRaisesRegex(
                mac.QualificationError, "PROFILE_FILE_UNTRUSTED"
            ):
                candidate.build_candidate(
                    hermes=self.hermes, hermes_home=self.home, env={}
                )

    def test_source_binding_values_are_measurements_not_placeholders(self):
        value = self.build()
        inner = value["candidate"]
        for key, path in mac.SOURCE_BINDINGS.items():
            self.assertEqual(inner[key], hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
