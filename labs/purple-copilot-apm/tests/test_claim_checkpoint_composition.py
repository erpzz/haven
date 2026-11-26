import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve()
LABS = HERE.parents[2]
SMALL = LABS / "small-model-augmentation"
if str(SMALL) not in sys.path:
    sys.path.insert(0, str(SMALL))

import checkpoint_journal as checkpoint
from apm import bounded_claim_adapter as adapter


def bundle(value=3):
    claims = []
    for metric, suffix in (
        ("principals_with_direct_control", "direct"),
        ("control_edges", "edges"),
        ("identities_able_to_reach_tier_zero", "reach"),
    ):
        claims.append({
            "id": f"c_{suffix}",
            "kind": "count",
            "payload": {
                "claim_type": "count",
                "metric": metric,
                "value": value,
            },
            "citations": [{"source": "host", "path": f"$.{metric}"}],
        })
    return {
        "schema": adapter.BUNDLE_SCHEMA,
        "scope": {
            "tool": "purple_tier_zero_overview",
            "platform": "ad",
            "snapshot": 1,
        },
        "claims": claims,
        "limitations": [],
    }


class ClaimCheckpointCompositionTests(unittest.TestCase):
    def make_binding(self, *, value=3, renderer="1", run="2"):
        b = bundle(value)
        policy = adapter.coverage_policy(b)
        return adapter.claim_checkpoint_binding(
            b,
            policy,
            renderer_sha256=renderer * 64,
            run_manifest_sha256=run * 64,
        )

    def open_run(self, path, binding):
        j = checkpoint.Journal(
            path,
            "claim-run",
            binding["binding_sha256"],
            fsync=True,
        )
        j.open()
        return j

    def test_same_claim_identity_can_resume(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "journal.jsonl"
            binding = self.make_binding()
            self.open_run(path, binding)
            resumed = checkpoint.Journal(
                path, "claim-run", binding["binding_sha256"], fsync=True
            )
            resumed.open(resume=True)
            scan = checkpoint.scan(path)
            self.assertTrue(scan.ok, scan.errors)
            self.assertEqual(scan.events[-1]["event"], "run_resumed")

    def test_changed_bundle_and_coverage_policy_refuse_resume(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "journal.jsonl"
            original = self.make_binding(value=3)
            changed = self.make_binding(value=4)
            self.assertNotEqual(
                original["bundle_sha256"], changed["bundle_sha256"]
            )
            self.assertNotEqual(
                original["coverage_policy_sha256"],
                changed["coverage_policy_sha256"],
            )
            self.open_run(path, original)
            with self.assertRaisesRegex(ValueError, "run identity mismatch"):
                checkpoint.Journal(
                    path,
                    "claim-run",
                    changed["binding_sha256"],
                    fsync=True,
                ).open(resume=True)

    def test_changed_renderer_refuses_resume(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "journal.jsonl"
            original = self.make_binding(renderer="1")
            changed = self.make_binding(renderer="3")
            self.assertNotEqual(
                original["binding_sha256"], changed["binding_sha256"]
            )
            self.open_run(path, original)
            with self.assertRaisesRegex(ValueError, "run identity mismatch"):
                checkpoint.Journal(
                    path,
                    "claim-run",
                    changed["binding_sha256"],
                    fsync=True,
                ).open(resume=True)

    def test_changed_underlying_run_manifest_refuses_resume(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "journal.jsonl"
            original = self.make_binding(run="2")
            changed = self.make_binding(run="4")
            self.assertNotEqual(
                original["binding_sha256"], changed["binding_sha256"]
            )
            self.open_run(path, original)
            with self.assertRaisesRegex(ValueError, "run identity mismatch"):
                checkpoint.Journal(
                    path,
                    "claim-run",
                    changed["binding_sha256"],
                    fsync=True,
                ).open(resume=True)

    def test_policy_tamper_cannot_create_checkpoint_binding(self):
        b = bundle()
        policy = adapter.coverage_policy(b)
        policy["required_ids"] = policy["required_ids"][:-1]
        with self.assertRaises(adapter.ClaimAdapterError):
            adapter.claim_checkpoint_binding(
                b,
                policy,
                renderer_sha256="1" * 64,
                run_manifest_sha256="2" * 64,
            )


if __name__ == "__main__":
    unittest.main()
