import json
import shutil
import tempfile
import unittest
from pathlib import Path

from haven_cyber import FIXTURES, ROOT
from haven_cyber.evidence import EvidenceBundle, finding_json_schema, json_pointer_get
from haven_cyber.normalize import maester, prowler_ocsf
from haven_cyber.tools.entra_ca import assess
from haven_cyber.verifier import verify

WEAK = json.loads((FIXTURES / "tenants" / "contoso-weak.json").read_text())
HARD = json.loads((FIXTURES / "tenants" / "contoso-hardened.json").read_text())


class NormalizerTests(unittest.TestCase):
    def test_maester_preserves_ids_and_maps_status(self):
        b = maester.normalize(FIXTURES / "tool_outputs" / "maester-weak.json", ROOT)
        by = {f.source_check_id: f for f in b.findings}
        self.assertEqual(set(by), {"MT.1005", "MT.1006", "MT.1007", "EIDSCA.AP01"})
        self.assertEqual(by["MT.1005"].status, "fail")
        self.assertEqual(by["MT.1005"].severity, "high")
        self.assertEqual(by["EIDSCA.AP01"].status, "skipped")
        self.assertTrue(any("Skipped is not a pass" in x for x in by["EIDSCA.AP01"].limitations))
        self.assertIn("https://maester.dev/docs/tests/maester/MT.1005", by["MT.1005"].references)

    def test_maester_v3_schema_2_1(self):
        b = maester.normalize(FIXTURES / "tool_outputs" / "maester-weak-v3.json", ROOT)
        by = {f.source_check_id: f for f in b.findings}
        self.assertEqual(by["MT.1005"].domain, "entra")  # from Product, not tags (3.0 rows carry no product tags)
        self.assertEqual(by["MT.1005"].service, "conditional-access")
        self.assertIn("attack:T1078.004", by["MT.1006"].controls)
        self.assertIn("example:REQ-7", by["MT.1007"].controls)  # synthetic control id, not a real framework mapping
        self.assertNotIn("attack:None", by["EIDSCA.AP01"].controls)
        self.assertIn("schema 2.1", by["MT.1005"].source_tool)
        verify(b, ROOT, WEAK)  # cross-tool corroboration works the same for 3.0 results
        self.assertEqual(by["MT.1005"].verification, "corroborated")

    def test_prowler_ocsf(self):
        b = prowler_ocsf.normalize(FIXTURES / "tool_outputs" / "prowler-weak.ocsf.json", ROOT)
        by = {f.source_check_id: f for f in b.findings}
        self.assertEqual(by["entra_legacy_authentication_blocked"].status, "pass")
        self.assertEqual(by["entra_conditional_access_policy_device_code_flow_blocked"].severity, "high")
        self.assertIn("CIS-4.0_M365:5.2.2.3", by["entra_legacy_authentication_blocked"].controls)
        self.assertEqual(by["entra_legacy_authentication_blocked"].domain, "entra")

    def test_bundle_roundtrip_and_schema(self):
        b = assess(FIXTURES / "tenants" / "contoso-weak.json", ROOT)
        again = EvidenceBundle.from_dict(json.loads(b.to_json()))
        self.assertEqual(len(again.findings), len(b.findings))
        schema = finding_json_schema()
        self.assertIn("verification", schema["required"] + list(schema["properties"]))
        self.assertEqual(schema["properties"]["severity"]["enum"][0], "critical")

    def test_json_pointer(self):
        self.assertEqual(json_pointer_get({"a/b": [1, {"~": 2}]}, "/a~1b/1/~0"), 2)
        with self.assertRaises(KeyError):
            json_pointer_get({"a": []}, "/a/3")


class VerifierTests(unittest.TestCase):
    def test_haven_findings_corroborated(self):
        b = assess(FIXTURES / "tenants" / "contoso-weak.json", ROOT)
        rep = verify(b, ROOT, WEAK)
        self.assertTrue(rep.ok(), rep.problems)
        st = {f.source_check_id: f.verification for f in b.findings}
        for rule in ("HCA-001", "HCA-002", "HCA-003", "HCA-004", "HCA-005", "HCA-007"):
            self.assertEqual(st[rule], "corroborated", rule)

    def test_wrong_tool_verdict_is_refuted(self):
        b = prowler_ocsf.normalize(FIXTURES / "tool_outputs" / "prowler-hardened-fp.ocsf.json", ROOT)
        verify(b, ROOT, HARD)
        self.assertEqual(b.findings[0].verification, "refuted")

    def test_existence_pass_flags_coverage_gap(self):
        b = maester.normalize(FIXTURES / "tool_outputs" / "maester-weak.json", ROOT)
        verify(b, ROOT, WEAK)
        f = next(x for x in b.findings if x.source_check_id == "MT.1006")
        self.assertEqual(f.verification, "corroborated")
        self.assertTrue(any("criterion gap" in n for n in f.verification_notes))

    def test_without_snapshot_stays_reported(self):
        b = maester.normalize(FIXTURES / "tool_outputs" / "maester-weak.json", ROOT)
        verify(b, ROOT, None)
        self.assertEqual({f.verification for f in b.findings}, {"reported"})

    def test_tampered_artifact_detected(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "snap.json"
            shutil.copy(FIXTURES / "tenants" / "contoso-weak.json", src)
            b = assess(src)
            data = json.loads(src.read_text())
            data["conditionalAccessPolicies"][0]["state"] = "disabled"
            src.write_text(json.dumps(data))
            rep = verify(b, Path(d), WEAK)
            self.assertFalse(rep.ok())
            self.assertTrue(any("hash mismatch" in p for p in rep.problems))

    def test_fabricated_pointer_detected(self):
        b = assess(FIXTURES / "tenants" / "contoso-weak.json", ROOT)
        b.observations[0].value = "enabled-but-fabricated"
        rep = verify(b, ROOT, WEAK)
        self.assertTrue(any("differs from recorded observation" in p for p in rep.problems))

    def test_failing_finding_without_evidence_is_insufficient(self):
        b = assess(FIXTURES / "tenants" / "contoso-weak.json", ROOT)
        f = next(x for x in b.findings if x.status == "fail")
        f.observations, f.artifacts = [], []
        verify(b, ROOT, WEAK)
        self.assertEqual(f.verification, "insufficient_evidence")

    def test_tool_cannot_self_confirm(self):
        b = assess(FIXTURES / "tenants" / "contoso-weak.json", ROOT)
        b.findings[0].verification = "confirmed"
        rep = verify(b, ROOT, WEAK)
        self.assertTrue(any("self-certify" in p for p in rep.problems))


if __name__ == "__main__":
    unittest.main()
