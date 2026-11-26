import json
import pathlib
import unittest

from haven_cyber import CORPUS, EVAL, ROOT
from haven_cyber.attack import ATTACK_TABLE, FINDING_TECHNIQUES, SIGMA_INDEX, TECH_RE, load_attack, map_finding, validate


class AttackTests(unittest.TestCase):
    def test_table_provenance(self):
        t = load_attack()
        self.assertEqual(t["attack_version"], "20.0")
        self.assertEqual(len(t["bundle_sha256"]), 64)
        self.assertIn("MITRE", t["notice"])
        self.assertGreater(len(t["techniques"]), 600)

    def test_every_technique_id_in_corpus_eval_and_mappings_is_current(self):
        text = "".join(p.read_text() for p in CORPUS.rglob("*.md"))
        text += (EVAL / "answers" / "v1.json").read_text() + (EVAL / "scenarios" / "v1.json").read_text()
        ids = set(TECH_RE.findall(text)) | {x for v in FINDING_TECHNIQUES.values() for x in v}
        ids.discard("T1234.001")  # the answer-format placeholder, deliberately not a real technique
        res = validate(ids)
        self.assertEqual(res["unknown"], [])
        self.assertEqual(res["deprecated_or_revoked"], [])

    def test_sigma_index_is_metadata_only(self):
        idx = json.loads(SIGMA_INDEX.read_text())
        self.assertIn("DRL", idx["license"])
        self.assertEqual(len(idx["commit"]), 40)
        for r in idx["rules"]:
            self.assertNotIn("detection", r)
            self.assertTrue(r["url"].startswith("https://github.com/SigmaHQ/sigma/blob/"))

    def test_mapping(self):
        legacy = map_finding("HCA-001")
        self.assertIn("Use of Legacy Authentication Protocols", [r["title"] for r in legacy["sigma_rules"]])
        self.assertTrue(map_finding("HCA-004")["detection_gap"])  # no SigmaHQ cloud rule for AiTM session theft
        self.assertFalse(map_finding("HCA-010")["detection_gap"])  # no techniques: not a gap, just not applicable

    def test_findings_carry_attack_controls(self):
        from haven_cyber.tools.entra_ca import assess
        b = assess(ROOT / "fixtures" / "tenants" / "contoso-weak.json", ROOT)
        f = next(x for x in b.findings if x.source_check_id == "HCA-001")
        self.assertIn("attack:T1110.003", f.controls)


if __name__ == "__main__":
    unittest.main()
