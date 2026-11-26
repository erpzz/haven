import copy
import json
import sys
import unittest
from pathlib import Path

CYBER = Path(__file__).resolve().parents[1]
AUG = CYBER.parent / "small-model-augmentation"
sys.path.insert(0, str(AUG))

import evidence_admission as admission  # noqa: E402
from haven_cyber.evidence import EvidenceBundle  # noqa: E402
from haven_cyber.normalize import maester, prowler_ocsf  # noqa: E402
from haven_cyber.tools.entra_ca import assess  # noqa: E402
from haven_cyber.verifier import verify  # noqa: E402


class StrictEvidenceAdmissionIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot_path = CYBER / "fixtures" / "tenants" / "contoso-weak.json"
        cls.snapshot = json.loads(cls.snapshot_path.read_text())

    def assert_admitted_then_verified(self, bundle):
        doc = bundle.to_dict()
        structural = admission.check_bundle(doc)
        self.assertEqual(structural["status"], "pass", structural)

        byte_lineage = admission.verify_artifact_root(doc, CYBER)
        self.assertEqual(byte_lineage["status"], "pass", byte_lineage)
        self.assertGreater(byte_lineage["artifacts_checked"], 0)

        verified = EvidenceBundle.from_dict(copy.deepcopy(doc))
        report = verify(verified, CYBER, self.snapshot)
        self.assertEqual(report.problems, [])

        # Strict admission is deliberately pre-verification: once the independent
        # verifier has changed verification state/notes, the object is not a fresh
        # producer bundle and must not be silently re-admitted as one.
        post = admission.check_bundle(verified.to_dict())
        self.assertEqual(post["status"], "block")
        self.assertIn("PREVERIFIED_FINDING", post["errors"])

    def test_ca_assessor_bundle_is_compatible(self):
        self.assert_admitted_then_verified(assess(self.snapshot_path, rel_to=CYBER))

    def test_maester_bundle_is_compatible(self):
        path = CYBER / "fixtures" / "tool_outputs" / "maester-weak.json"
        self.assert_admitted_then_verified(maester.normalize(path, rel_to=CYBER))

    def test_prowler_bundle_is_compatible(self):
        path = CYBER / "fixtures" / "tool_outputs" / "prowler-weak.ocsf.json"
        self.assert_admitted_then_verified(prowler_ocsf.normalize(path, rel_to=CYBER))

    def test_merged_real_producer_bundle_is_compatible(self):
        bundle = assess(self.snapshot_path, rel_to=CYBER)
        bundle.merge(maester.normalize(CYBER / "fixtures" / "tool_outputs" / "maester-weak.json", rel_to=CYBER))
        bundle.merge(prowler_ocsf.normalize(CYBER / "fixtures" / "tool_outputs" / "prowler-weak.ocsf.json", rel_to=CYBER))
        self.assert_admitted_then_verified(bundle)


if __name__ == "__main__":
    unittest.main()
