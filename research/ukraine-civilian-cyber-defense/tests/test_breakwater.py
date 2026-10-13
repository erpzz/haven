import importlib.util
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
S = HERE / "breakwater" / "breakwater.py"
spec = importlib.util.spec_from_file_location("breakwater", S)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NOW = datetime(2026, 10, 13, tzinfo=timezone.utc)


def sample():
    return json.loads((HERE / "breakwater" / "examples" / "clickfix-hypothetical.json").read_text())


class BreakwaterTests(unittest.TestCase):
    def test_candidate_only_never_qualifies_as_attested(self):
        report = module.plan(sample(), NOW)
        self.assertEqual(report["attested_covered_count"], 0)
        self.assertEqual(report["status"], "PROPOSED_ONLY")
        self.assertEqual(report["modeled_paths"], 3)

    def test_selects_less_disruptive_complete_plan(self):
        report = module.plan(sample(), NOW)
        self.assertEqual([x["id"] for x in report["recommended_controls"]], ["execution_control"])
        self.assertEqual(report["no_candidate_path_ids"], [])

    def test_attested_coverage_requires_evidence_and_recent_validation(self):
        model = sample()
        c = model["controls"][1]
        c.update(state="attested", evidence_reference="operator local change ticket #1",
                 validated_utc=NOW.isoformat())
        report = module.plan(model, NOW)
        self.assertEqual(report["status"], "ATTESTED_IN_MODEL")
        self.assertEqual(report["attested_covered_count"], 3)

    def test_stale_attestation_not_trusted(self):
        model = sample()
        c = model["controls"][1]
        c.update(state="attested", evidence_reference="local ticket",
                 validated_utc=(NOW - timedelta(days=45)).isoformat())
        report = module.plan(model, NOW)
        self.assertEqual(report["attested_covered_count"], 0)

    def test_missing_attestation_not_trusted(self):
        model = sample()
        model["controls"][1]["state"] = "attested"
        self.assertEqual(module.plan(model, NOW)["attested_covered_count"], 0)

    def test_reports_unprotectable_path(self):
        model = sample()
        model["attack_paths"].append({"id": "new_path", "steps": ["unmapped_step"]})
        report = module.plan(model, NOW)
        self.assertEqual(report["status"], "NO_SUPPORTED_PLAN")
        self.assertEqual(report["no_candidate_path_ids"], ["new_path"])

    def test_refuses_undefined_step(self):
        model = sample()
        model["controls"][0]["interrupts"].append("unknown_step")
        with self.assertRaises(module.InvalidModel):
            module.plan(model, NOW)

    def test_refuses_missing_scope_or_rollback(self):
        model = sample()
        model["controls"][0]["scope"] = ""
        with self.assertRaises(module.InvalidModel):
            module.plan(model, NOW)
        model = sample()
        model["controls"][0]["rollback"] = ""
        with self.assertRaises(module.InvalidModel):
            module.plan(model, NOW)

    def test_refuses_fake_source(self):
        model = sample()
        model["source_url"] = "http://localhost/exploit"
        with self.assertRaises(module.InvalidModel):
            module.plan(model, NOW)

    def test_refuses_duplicate_steps_and_controls(self):
        model = sample()
        model["attack_paths"][0]["steps"].append("harm")
        with self.assertRaises(module.InvalidModel):
            module.plan(model, NOW)
        model = sample()
        model["controls"].append(dict(model["controls"][0]))
        with self.assertRaises(module.InvalidModel):
            module.plan(model, NOW)

    def test_refuses_abusive_search_size(self):
        model = sample()
        model["controls"] = model["controls"] + [
            dict(model["controls"][0], id=f"extra_{i}") for i in range(20)
        ]
        with self.assertRaises(module.InvalidModel):
            module.plan(model, NOW)

    def test_emits_no_live_changes_or_external_calls(self):
        self.assertIn("Candidate coverage is a mathematical recommendation", " ".join(module.plan(sample(), NOW)["limitations"]))


if __name__ == "__main__":
    unittest.main()
