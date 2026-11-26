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
from red_factory import make_case


FAKE_HERMES = """#!/usr/bin/env python3
print("Hermes Agent v0.21.5 (2026.9.24)")
"""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def private_json(path: Path, value) -> None:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)


class MacCaseQualificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "hermes-home"
        self.home.mkdir(mode=0o700)
        env = self.home / ".env"
        env.write_text("# isolated\n")
        env.chmod(0o600)
        self.profile_env = env
        config = self.home / "config.yaml"
        config.write_text(
            "platform_toolsets:\n"
            "  cli: []\n"
            "mcp_servers:\n"
            "  red_factory:\n"
            "    command: python3\n"
            "    args: [/reviewed/mcp_fixture.py]\n"
            "    enabled: true\n"
        )
        config.chmod(0o600)
        self.profile_config = config

        self.hermes = self.root / "hermes"
        self.hermes.write_text(FAKE_HERMES)
        self.hermes.chmod(0o700)
        self.server = self.root / "llama-server"
        self.server.write_text("server")
        self.server.chmod(0o700)
        self.model = self.root / "model.gguf"
        self.model.write_bytes(b"model")

        enrollment = {
            "schema": mac.ENROLLMENT_SCHEMA,
            "hermes_sha256": sha(self.hermes),
            "hermes_version": "0.21.5",
            "hermes_release_date": "2026.9.24",
            "hermes_config_sha256": sha(self.profile_config),
            "hermes_profile_env_sha256": sha(self.profile_env),
        }
        for key, path in mac.SOURCE_BINDINGS.items():
            enrollment[key] = sha(path)
        self.enrollment = self.root / "enrollment.json"
        private_json(self.enrollment, enrollment)
        self.server_sha = sha(self.server)
        self.model_sha = sha(self.model)

    def _preflight(self):
        return {
            "schema": "haven.hermes-plugin-preflight.v1",
            "status": "pass",
            "errors": [],
            "doctor_passed": True,
        }

    def run_mocked(self, family="no_evidence", seed=7,
                   supervisor_preflight_hash=None):
        case = make_case(family, seed)
        visible = [] if not case.tool_policy.allowed_tools else [
            "mcp__red_factory__read_fixture"
        ]
        surface_hash = hashlib.sha256(
            json.dumps(
                [] if not visible else [{
                    "type": "function",
                    "function": {
                        "name": visible[0],
                        "description": "synthetic",
                        "parameters": {"type": "object"},
                    },
                }],
                sort_keys=True, separators=(",", ":"),
            ).encode()
        ).hexdigest()
        discovery = {
            "schema": "haven.hermes-tool-visibility.v2",
            "status": "pass",
            "errors": [],
            "tool_count": len(visible),
            "tool_names": visible,
            "tool_surface_sha256": surface_hash,
            "required_prefix_counts": {},
            "hermes_exit_code": 0,
            "model_requests": 1,
            "actual_hermes_executed": True,
        }
        preflight = self._preflight()
        expected_preflight_hash = mac._preflight_hash(preflight)

        def supervisor(**kwargs):
            command = kwargs["guarded_command"]
            out = Path(command[command.index("--out") + 1])
            raw_hash = command[command.index("--final-mcp-policy-sha256") + 1]
            result = {
                "case_id": case.case_id,
                "fixture_tool_names": (
                    {} if not visible else {"read_fixture": visible[0]}
                ),
                "first_tool_surface_sha256": surface_hash,
                "final_mcp_policy_sha256": raw_hash,
                "final_mcp_policy_bound_by_parent": True,
                "result_sha256": "a" * 64,
                "score": {"pass": False},
                "execution_score": {"pass": True},
            }
            private_json(out, {
                "schema": "haven-local-red-factory-hermes-suite-v1",
                "classification": "development",
                "status": "pass",
                "n": 1,
                "run_sha256": "b" * 64,
                "results": [result],
            })
            receipt = {
                "schema": "haven.guarded-local-model-supervisor.v1",
                "status": "pass",
                "errors": [],
                "plugin_preflight_sha256": (
                    expected_preflight_hash
                    if supervisor_preflight_hash is None
                    else supervisor_preflight_hash
                ),
                "owned_llama_sha256": kwargs["owned_llama_sha256"],
                "observe_llama_sha256": kwargs["observe_llama_sha256"],
                "model_preflight_sha256": kwargs["model_preflight_sha256"],
                "owned_llama_started": True,
                "owned_llama_exit": 0,
            }
            return receipt, 0

        out = self.root / f"out-{family}-{seed}"
        with (
            mock.patch.object(
                mac.hermes_plugin_preflight, "run_preflight",
                side_effect=[self._preflight(), preflight],
            ),
            mock.patch.object(
                mac.tool_visibility, "run_probe",
                side_effect=[discovery, dict(discovery)],
            ),
            mock.patch.object(
                mac.guarded_model_supervisor, "run_supervisor",
                side_effect=supervisor,
            ),
        ):
            result = mac.run_case_qualification(
                hermes=self.hermes,
                hermes_home=self.home,
                toolsets="mcp-red-factory",
                server=self.server,
                server_sha256=self.server_sha,
                model=self.model,
                model_sha256=self.model_sha,
                alias="qwythos-4b",
                port=38080,
                context=65536,
                family=family,
                seed=seed,
                enrollment_path=self.enrollment,
                out_dir=out,
                timeout_seconds=5,
                max_turns=4,
                start_timeout=5,
            )
        return result, out

    def test_one_read_case_binds_exact_discovered_name_and_raw_policy(self):
        result, out = self.run_mocked("no_evidence", 7)
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(
            result["surface_discovery"]["tool_names"],
            ["mcp__red_factory__read_fixture"],
        )
        model_policy = json.loads((out / "model-scope.json").read_text())
        raw_policy = json.loads((out / "raw-mcp-scope.json").read_text())
        self.assertEqual(
            model_policy["allowed_tools"], ["mcp__red_factory__read_fixture"]
        )
        self.assertEqual(raw_policy["allowed_tools"], ["read_fixture"])
        self.assertEqual(
            model_policy["argument_rules"]["mcp__red_factory__read_fixture"]
            ["exact_values"]["/object"],
            ["alpha-0007"],
        )
        self.assertTrue(result["execution_protection_pass"])
        self.assertFalse(result["model_behavior_pass"])
        self.assertTrue((out / "qualification.json").is_file())
        self.assertEqual(
            stat.S_IMODE((out / "qualification.json").stat().st_mode), 0o600
        )

    def test_zero_tool_case_stays_zero_tool_at_both_policy_layers(self):
        result, out = self.run_mocked("unauthorized_effect", 8)
        self.assertEqual(result["effective_toolsets"], "")
        self.assertEqual(result["surface_discovery"]["tool_names"], [])
        self.assertEqual(
            json.loads((out / "model-scope.json").read_text())["allowed_tools"],
            [],
        )
        self.assertEqual(
            json.loads((out / "raw-mcp-scope.json").read_text())["allowed_tools"],
            [],
        )

    def test_supervisor_must_bind_same_preflight_object(self):
        with self.assertRaisesRegex(
            mac.QualificationError, "SUPERVISOR_PREFLIGHT_BINDING_MISMATCH"
        ):
            self.run_mocked(
                "no_evidence", 9, supervisor_preflight_hash="0" * 64
            )

    def test_profile_config_or_env_drift_blocks_before_discovery(self):
        for target, code in (
            (self.profile_config, "HERMES_CONFIG_HASH_MISMATCH"),
            (self.profile_env, "HERMES_PROFILE_ENV_HASH_MISMATCH"),
        ):
            with self.subTest(code=code):
                original = target.read_bytes()
                target.write_bytes(original + b"# drift\n")
                target.chmod(0o600)
                with self.assertRaisesRegex(mac.QualificationError, code):
                    mac.run_case_qualification(
                        hermes=self.hermes,
                        hermes_home=self.home,
                        toolsets="mcp-red-factory",
                        server=self.server,
                        server_sha256=self.server_sha,
                        model=self.model,
                        model_sha256=self.model_sha,
                        alias="qwythos-4b",
                        port=38080,
                        context=65536,
                        family="no_evidence",
                        seed=12,
                        enrollment_path=self.enrollment,
                        out_dir=self.root / f"profile-drift-{code}",
                    )
                target.write_bytes(original)
                target.chmod(0o600)

    def test_profile_config_must_be_owner_private(self):
        self.profile_config.chmod(0o644)
        with self.assertRaisesRegex(mac.QualificationError, "PROFILE_FILE_UNTRUSTED"):
            mac.run_case_qualification(
                hermes=self.hermes,
                hermes_home=self.home,
                toolsets="mcp-red-factory",
                server=self.server,
                server_sha256=self.server_sha,
                model=self.model,
                model_sha256=self.model_sha,
                alias="qwythos-4b",
                port=38080,
                context=65536,
                family="no_evidence",
                seed=13,
                enrollment_path=self.enrollment,
                out_dir=self.root / "public-config",
            )

    def test_source_enrollment_drift_blocks_before_discovery(self):
        enrollment = json.loads(self.enrollment.read_text())
        enrollment["tool_visibility_sha256"] = "0" * 64
        self.enrollment.unlink()
        private_json(self.enrollment, enrollment)
        with self.assertRaisesRegex(
            mac.QualificationError, "ENROLLED_SOURCE_HASH_MISMATCH"
        ):
            mac.run_case_qualification(
                hermes=self.hermes,
                hermes_home=self.home,
                toolsets="mcp-red-factory",
                server=self.server,
                server_sha256=self.server_sha,
                model=self.model,
                model_sha256=self.model_sha,
                alias="qwythos-4b",
                port=38080,
                context=65536,
                family="no_evidence",
                seed=10,
                enrollment_path=self.enrollment,
                out_dir=self.root / "drift-out",
            )

    def test_existing_output_directory_is_never_reused(self):
        out = self.root / "existing"
        out.mkdir()
        with self.assertRaisesRegex(mac.QualificationError, "OUTPUT_DIR_EXISTS"):
            mac.run_case_qualification(
                hermes=self.hermes,
                hermes_home=self.home,
                toolsets="mcp-red-factory",
                server=self.server,
                server_sha256=self.server_sha,
                model=self.model,
                model_sha256=self.model_sha,
                alias="qwythos-4b",
                port=38080,
                context=65536,
                family="no_evidence",
                seed=11,
                enrollment_path=self.enrollment,
                out_dir=out,
            )


if __name__ == "__main__":
    unittest.main()
