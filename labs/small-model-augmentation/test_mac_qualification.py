from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

AUG = Path(__file__).resolve().parent

import mac_qualification as qual


def provenance():
    manifest = {
        "schema": "haven.hermes-core-source-manifest.v1",
        "file_count": 1,
        "files": [{"path": "hermes_cli/__init__.py", "sha256": "a" * 64}],
    }
    manifest["manifest_sha256"] = qual._sha(manifest)
    p = {
        "schema": "haven.hermes-runtime-provenance.v1",
        "version": "0.21.5",
        "release_date": "2026.9.24",
        "git_commit": "f97608f178d1ffeca59860195ab7da295f7c8e5f",
        "source_root": "/fixture/hermes",
        "module_file": "/fixture/hermes/hermes_cli/__init__.py",
        "core_source_manifest_sha256": manifest["manifest_sha256"],
        "core_source_file_count": 1,
    }
    p["provenance_sha256"] = qual._sha(p)
    return p, manifest


class MacQualificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def campaign_result(self, p):
        return {
            "status": "pass",
            "campaign_sha256": "b" * 64,
            "tool_implementation_sha256": "c" * 64,
            "hermes_provenance": p,
            "runtime": {
                "model_artifact_sha256": "d" * 64,
                "llama_server_sha256": "e" * 64,
            },
            "n": 2,
            "harness_passes": 2,
            "model_passes": 1,
            "execution_passes": 2,
        }

    def test_controls_pass_before_qwythos_campaign_and_receipt_binds_all(self):
        p, manifest = provenance()
        events = []

        def control_side_effect(**kwargs):
            events.append("control:" + kwargs["mode"])
            return {
                "status": "pass",
                "control_sha256": (
                    "1" * 64 if kwargs["mode"] == "wrong-target" else "2" * 64
                ),
            }

        def campaign_side_effect(**kwargs):
            events.append("campaign")
            self.assertTrue(kwargs["hermes_home"].is_dir())
            return self.campaign_result(p)

        out = self.base / "qual"
        with mock.patch.object(
            qual.red_campaign, "_hermes_provenance",
            return_value=(p, manifest),
        ), mock.patch.object(
            qual.final_gate, "run_control", side_effect=control_side_effect
        ), mock.patch.object(
            qual.red_campaign, "run_campaign", side_effect=campaign_side_effect
        ):
            result = qual.run_qualification(
                hermes=self.base / "hermes",
                server=self.base / "llama-server",
                model=self.base / "model.gguf",
                alias="qwythos-4b",
                out_root=out,
                augmentation_root=AUG,
                seeds=[1],
                families=["duplicate_read", "unauthorized_effect"],
            )

        self.assertEqual(
            events,
            ["control:wrong-target", "control:duplicate", "campaign"],
        )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["tool_implementation_sha256"], "c" * 64)
        self.assertTrue((out / "qualification-receipt.json").is_file())
        written = json.loads((out / "qualification-receipt.json").read_text())
        self.assertEqual(
            written["final_gate_control_sha256"]["wrong-target"], "1" * 64
        )
        self.assertEqual(
            written["final_gate_control_sha256"]["duplicate"], "2" * 64
        )
        self.assertEqual(written["campaign_sha256"], "b" * 64)

    def test_failed_final_gate_control_prevents_qwythos_campaign(self):
        p, manifest = provenance()

        def control_side_effect(**kwargs):
            if kwargs["mode"] == "wrong-target":
                return {"status": "block", "control_sha256": "1" * 64}
            return {"status": "pass", "control_sha256": "2" * 64}

        campaign = mock.Mock()
        with mock.patch.object(
            qual.red_campaign, "_hermes_provenance",
            return_value=(p, manifest),
        ), mock.patch.object(
            qual.final_gate, "run_control", side_effect=control_side_effect
        ), mock.patch.object(
            qual.red_campaign, "run_campaign", campaign
        ):
            with self.assertRaisesRegex(
                qual.QualificationError, "FINAL_GATE_CONTROL_FAILED"
            ):
                qual.run_qualification(
                    hermes=self.base / "hermes",
                    server=self.base / "llama-server",
                    model=self.base / "model.gguf",
                    alias="qwythos-4b",
                    out_root=self.base / "blocked",
                    augmentation_root=AUG,
                    seeds=[1],
                    families=["duplicate_read"],
                )
        campaign.assert_not_called()

    def test_existing_output_root_is_refused(self):
        out = self.base / "existing"
        out.mkdir()
        marker = out / "keep"
        marker.write_text("unchanged")
        with self.assertRaisesRegex(
            qual.QualificationError, "OUTPUT_ROOT_ALREADY_EXISTS"
        ):
            qual.run_qualification(
                hermes=self.base / "hermes",
                server=self.base / "server",
                model=self.base / "model",
                alias="qwythos-4b",
                out_root=out,
                augmentation_root=AUG,
                seeds=[1],
                families=["duplicate_read"],
            )
        self.assertEqual(marker.read_text(), "unchanged")


if __name__ == "__main__":
    unittest.main()
