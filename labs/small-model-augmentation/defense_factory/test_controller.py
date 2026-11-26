import hashlib
import json
import unittest

from controller import (
    DefenseWorkflowController,
    build_workflow_contract,
    verify_run_receipt,
)
from defense_factory import FindingLedger
from runner import Recipe


def canonical_hash(body):
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.finding_id = "hdf_" + "a" * 32
        self.fix = {
            "finding_id": self.finding_id,
            "packet_sha256": "b" * 64,
            "patch_sha256": "c" * 64,
            "touched_paths": ["src/app.py"],
        }
        self.base = "d" * 40
        self.recipes = (
            Recipe("unit", ("python", "-m", "unittest"), 30.0, "."),
            Recipe("scan", ("bandit", "-q", "src/app.py"), 30.0, "."),
        )
        self.contract = build_workflow_contract(
            validated_fix=self.fix, base_commit=self.base, recipes=self.recipes
        )
        self.ledger = FindingLedger()
        self.ledger.append(finding_id=self.finding_id, event="detected")
        self.ledger.append(finding_id=self.finding_id, event="triaged")
        self.controller = DefenseWorkflowController(self.ledger)

    def command(self, recipe_id, exit_code=0, timed_out=False):
        return {
            "recipe_id": recipe_id,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "duration_ms": 12,
            "stdout_sha256": "e" * 64,
            "stderr_sha256": "f" * 64,
            "stdout_bytes": 4,
            "stderr_bytes": 0,
        }

    def receipt(self, rows=None, passed=True, **overrides):
        body = {
            "schema": "haven-local-defense-factory-run-v1",
            "finding_id": self.contract["finding_id"],
            "fix_packet_sha256": self.contract["fix_packet_sha256"],
            "base_commit": self.contract["base_commit"],
            "patch_sha256": self.contract["patch_sha256"],
            "recipe_policy_sha256": self.contract["recipe_policy_sha256"],
            "touched_paths": list(self.contract["touched_paths"]),
            "recipes": rows if rows is not None else [
                self.command("unit"),
                self.command("scan"),
            ],
            "passed": passed,
        }
        body.update(overrides)
        body["receipt_sha256"] = canonical_hash(body)
        return body

    def test_successful_bound_run_closes_finding(self):
        self.controller.record_proposal(self.contract)
        result = self.controller.record_run(contract=self.contract, receipt=self.receipt())
        self.assertEqual(result["state"], "closed")
        self.assertTrue(result["passed"])
        self.assertEqual(
            [x["event"] for x in self.ledger.entries],
            ["detected", "triaged", "fix_proposed", "fix_applied", "retested", "closed"],
        )

    def test_failed_retest_remains_revisable(self):
        self.controller.record_proposal(self.contract)
        failed = self.receipt(rows=[self.command("unit", exit_code=7)], passed=False)
        result = self.controller.record_run(contract=self.contract, receipt=failed)
        self.assertEqual(result["state"], "fix_applied")
        revised = dict(self.fix, patch_sha256="1" * 64)
        revised_contract = build_workflow_contract(
            validated_fix=revised, base_commit=self.base, recipes=self.recipes
        )
        self.controller.record_proposal(revised_contract)
        self.assertEqual(self.ledger.state(self.finding_id), "fix_proposed")

    def test_receipt_hash_tamper_rejected(self):
        receipt = self.receipt()
        receipt["passed"] = False
        with self.assertRaises(ValueError):
            verify_run_receipt(receipt, self.contract)

    def test_cross_finding_receipt_rejected(self):
        receipt = self.receipt(finding_id="hdf_" + "9" * 32)
        with self.assertRaises(ValueError):
            verify_run_receipt(receipt, self.contract)

    def test_cross_base_patch_packet_and_policy_receipts_rejected(self):
        mutations = {
            "base_commit": "1" * 40,
            "patch_sha256": "2" * 64,
            "fix_packet_sha256": "3" * 64,
            "recipe_policy_sha256": "4" * 64,
        }
        for key, value in mutations.items():
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    verify_run_receipt(self.receipt(**{key: value}), self.contract)

    def test_pass_flag_recomputed_from_command_receipts(self):
        bad = self.receipt(
            rows=[self.command("unit"), self.command("scan", exit_code=5)],
            passed=True,
        )
        with self.assertRaises(ValueError):
            verify_run_receipt(bad, self.contract)

    def test_incomplete_receipt_must_end_in_failure(self):
        truncated_success = self.receipt(rows=[self.command("unit")], passed=False)
        with self.assertRaises(ValueError):
            verify_run_receipt(truncated_success, self.contract)
        legitimate_stop = self.receipt(rows=[self.command("unit", timed_out=True, exit_code=-9)], passed=False)
        verified = verify_run_receipt(legitimate_stop, self.contract)
        self.assertFalse(verified["passed"])

    def test_empty_or_extra_recipe_receipts_rejected(self):
        with self.assertRaises(ValueError):
            verify_run_receipt(self.receipt(rows=[], passed=False), self.contract)
        extra = self.receipt(rows=[
            self.command("unit"), self.command("scan"), self.command("extra")
        ], passed=False)
        with self.assertRaises(ValueError):
            verify_run_receipt(extra, self.contract)

    def test_recipe_order_rejected(self):
        receipt = self.receipt(rows=[self.command("scan", exit_code=1)], passed=False)
        with self.assertRaises(ValueError):
            verify_run_receipt(receipt, self.contract)

    def test_duplicate_receipt_cannot_be_consumed_again(self):
        self.controller.record_proposal(self.contract)
        failed = self.receipt(rows=[self.command("unit", exit_code=1)], passed=False)
        self.controller.record_run(contract=self.contract, receipt=failed)
        self.controller.record_proposal(self.contract)
        with self.assertRaises(ValueError):
            self.controller.record_run(contract=self.contract, receipt=failed)

    def test_pending_proposal_must_match_contract(self):
        self.controller.record_proposal(self.contract)
        other = dict(self.fix, patch_sha256="1" * 64)
        other_contract = build_workflow_contract(
            validated_fix=other, base_commit=self.base, recipes=self.recipes
        )
        with self.assertRaises(ValueError):
            self.controller.record_run(contract=other_contract, receipt=self.receipt())

    def test_contract_hash_tamper_rejected(self):
        contract = dict(self.contract)
        contract["base_commit"] = "1" * 40
        with self.assertRaises(ValueError):
            self.controller.record_proposal(contract)

    def test_command_receipt_type_confusion_rejected(self):
        row = self.command("unit")
        row["duration_ms"] = True
        receipt = self.receipt(rows=[row], passed=False)
        with self.assertRaises(ValueError):
            verify_run_receipt(receipt, self.contract)

    def test_close_can_be_deferred_after_verified_retest(self):
        self.controller.record_proposal(self.contract)
        result = self.controller.record_run(
            contract=self.contract, receipt=self.receipt(), close_on_pass=False
        )
        self.assertEqual(result["state"], "verified")


if __name__ == "__main__":
    unittest.main()
