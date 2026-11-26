import json
import unittest

from defense_factory import (
    EvidenceRef, FindingLedger, canonical_rel_path, findings_from_sarif,
    validate_unified_diff, finding_to_dict, build_fix_packet, validate_fix_response,
)

class DefenseFactoryTests(unittest.TestCase):
    def setUp(self):
        self.files = {"src/app.py": b"one\ntwo\nthree\n"}

    def sarif(self, **overrides):
        result = {
            "ruleId": "R1",
            "level": "error",
            "message": {"text": "unsafe thing"},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": "src/app.py"},
                    "region": {"startLine": 2, "endLine": 2},
                }
            }],
        }
        result.update(overrides)
        return {"version": "2.1.0", "runs": [{"results": [result]}]}

    def test_evidence_binds_file_and_excerpt(self):
        ref = EvidenceRef.from_bytes("src/app.py", self.files["src/app.py"], 2, 2)
        self.assertEqual(ref.path, "src/app.py")
        self.assertNotEqual(ref.file_sha256, ref.excerpt_sha256)

    def test_sarif_normalizes_stable_finding(self):
        a = findings_from_sarif(self.sarif(), self.files.__getitem__)[0]
        b = findings_from_sarif(self.sarif(), self.files.__getitem__)[0]
        self.assertEqual(a.finding_id, b.finding_id)
        self.assertEqual(a.severity, "high")
        self.assertEqual(finding_to_dict(a)["schema"], "haven-local-defense-factory-v1")

    def test_changed_source_changes_finding_identity(self):
        a = findings_from_sarif(self.sarif(), self.files.__getitem__)[0]
        changed = {"src/app.py": b"one\nTWO\nthree\n"}
        b = findings_from_sarif(self.sarif(), changed.__getitem__)[0]
        self.assertNotEqual(a.finding_id, b.finding_id)

    def test_rejects_multilocation_result(self):
        doc = self.sarif()
        doc["runs"][0]["results"][0]["locations"].append(doc["runs"][0]["results"][0]["locations"][0])
        with self.assertRaises(ValueError):
            findings_from_sarif(doc, self.files.__getitem__)

    def test_path_rejects_traversal_absolute_backslash(self):
        for value in ("../x", "/tmp/x", r"a\b"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    canonical_rel_path(value)

    def test_patch_gate_accepts_one_allowed_existing_file(self):
        patch = "\n".join([
            "diff --git a/src/app.py b/src/app.py",
            "--- a/src/app.py",
            "+++ b/src/app.py",
            "@@ -1,2 +1,2 @@",
            "-one",
            "+ONE",
            " two",
        ])
        self.assertEqual(validate_unified_diff(patch, ["src/app.py"]), ("src/app.py",))

    def test_patch_gate_rejects_extra_path(self):
        patch = "\n".join([
            "diff --git a/src/other.py b/src/other.py",
            "--- a/src/other.py",
            "+++ b/src/other.py",
            "@@ -1 +1 @@",
            "-x",
            "+y",
        ])
        with self.assertRaises(ValueError):
            validate_unified_diff(patch, ["src/app.py"])

    def test_patch_gate_rejects_create_delete_rename_binary_and_oversize(self):
        cases = [
            "diff --git a/x b/x\nnew file mode 100644\n--- /dev/null\n+++ b/x\n",
            "diff --git a/x b/y\nrename from x\nrename to y\n",
            "diff --git a/x b/x\nGIT binary patch\n",
        ]
        for patch in cases:
            with self.subTest(patch=patch[:30]):
                with self.assertRaises(ValueError):
                    validate_unified_diff(patch, ["x"])
        valid = "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n"
        with self.assertRaises(ValueError):
            validate_unified_diff(valid, ["x"], max_bytes=10)

    def test_ledger_requires_retest_pass_before_close(self):
        fid = "hdf_" + "a" * 32
        ledger = FindingLedger()
        ledger.append(finding_id=fid, event="detected")
        ledger.append(finding_id=fid, event="triaged")
        ledger.append(finding_id=fid, event="fix_proposed", payload={"patch_sha256": "b" * 64})
        ledger.append(finding_id=fid, event="fix_applied", payload={"applied_patch_sha256": "b" * 64})
        ledger.append(finding_id=fid, event="retested", payload={"passed": False, "receipt_sha256": "c" * 64})
        self.assertEqual(ledger.state(fid), "fix_applied")
        with self.assertRaises(ValueError):
            ledger.append(finding_id=fid, event="closed")
        ledger.append(finding_id=fid, event="retested", payload={"passed": True, "receipt_sha256": "d" * 64})
        ledger.append(finding_id=fid, event="closed")
        self.assertEqual(ledger.state(fid), "closed")

    def test_ledger_round_trip_and_tamper_detection(self):
        fid = "hdf_" + "1" * 32
        ledger = FindingLedger()
        ledger.append(finding_id=fid, event="detected")
        ledger.append(finding_id=fid, event="triaged")
        text = ledger.to_jsonl()
        restored = FindingLedger.from_jsonl(text)
        self.assertEqual(restored.head_hash, ledger.head_hash)
        rows = text.splitlines()
        obj = json.loads(rows[1])
        obj["payload"]["x"] = 1
        rows[1] = json.dumps(obj, sort_keys=True, separators=(",", ":"))
        with self.assertRaises(ValueError):
            FindingLedger.from_jsonl("\n".join(rows) + "\n")

    def test_fix_packet_and_response_bind_finding_and_paths(self):
        finding = findings_from_sarif(self.sarif(), self.files.__getitem__)[0]
        packet = build_fix_packet(finding, ["src/app.py"])
        patch = "\n".join([
            "diff --git a/src/app.py b/src/app.py",
            "--- a/src/app.py",
            "+++ b/src/app.py",
            "@@ -1 +1 @@",
            "-one",
            "+ONE",
        ])
        result = validate_fix_response({
            "finding_id": finding.finding_id, "summary": "tight fix", "patch": patch
        }, packet)
        self.assertEqual(result["touched_paths"], ["src/app.py"])
        self.assertEqual(len(result["patch_sha256"]), 64)

    def test_fix_response_rejects_extra_keys_wrong_id_and_extra_file(self):
        finding = findings_from_sarif(self.sarif(), self.files.__getitem__)[0]
        packet = build_fix_packet(finding, ["src/app.py"])
        patch = "diff --git a/src/app.py b/src/app.py\n--- a/src/app.py\n+++ b/src/app.py\n@@ -1 +1 @@\n-one\n+ONE\n"
        with self.assertRaises(ValueError):
            validate_fix_response({"finding_id": finding.finding_id, "summary": "x", "patch": patch, "pass": True}, packet)
        with self.assertRaises(ValueError):
            validate_fix_response({"finding_id": "hdf_" + "0" * 32, "summary": "x", "patch": patch}, packet)
        evil = patch.replace("src/app.py", "src/other.py")
        with self.assertRaises(ValueError):
            validate_fix_response({"finding_id": finding.finding_id, "summary": "x", "patch": evil}, packet)

    def test_ledger_rejects_nonhex_hash_claims(self):
        fid = "hdf_" + "3" * 32
        ledger = FindingLedger()
        ledger.append(finding_id=fid, event="detected")
        ledger.append(finding_id=fid, event="triaged")
        with self.assertRaises(ValueError):
            ledger.append(finding_id=fid, event="fix_proposed", payload={"patch_sha256": "z" * 64})

    def test_suppression_needs_reason(self):
        fid = "hdf_" + "2" * 32
        ledger = FindingLedger()
        ledger.append(finding_id=fid, event="detected")
        with self.assertRaises(ValueError):
            ledger.append(finding_id=fid, event="suppressed", payload={})
        ledger.append(finding_id=fid, event="suppressed", payload={"reason": "false positive"})
        self.assertEqual(ledger.state(fid), "suppressed")

if __name__ == "__main__":
    unittest.main()
