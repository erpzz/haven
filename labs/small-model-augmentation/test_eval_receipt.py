import copy
import hashlib
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

import augmentation_eval as sidecar
import eval_receipt as receipt


def H(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def manifest(arm="a"):
    return {
        "schema": sidecar.SCHEMA,
        "experiment": "context",
        "comparison_group": "g1",
        "arm": arm,
        "dataset_id": "public-dev",
        "dataset_sha256": H("data"),
        "model_id": "qwen4b",
        "model_artifact_sha256": H("model"),
        "engine": "llama.cpp",
        "hardware": "mac",
        "temperature": 0.0,
        "max_tokens": 1024,
        "code_sha256": H("code-" + arm),
        "grader_sha256": H("grader"),
        "reserve": False,
    }


def controls(tag="x"):
    return {
        "admission_receipt_sha256": H(tag + "-admission"),
        "tool_policy_sha256": H(tag + "-policy"),
        "catalog_sha256": H(tag + "-catalog"),
        "selection_receipt_sha256": H(tag + "-selection"),
        "claim_bundle_sha256": H(tag + "-claims"),
        "claim_policy_sha256": H(tag + "-claim-policy"),
        "renderer_sha256": H(tag + "-renderer"),
        "run_manifest_sha256": H(tag + "-run"),
        "tool_implementation_sha256": H(tag + "-tools"),
    }


def sources(tag="x", *, semantic_pass=True):
    return {
        "grader": {
            "receipt_sha256": H(tag + "-grader-source"),
            "semantic_pass": semantic_pass,
        },
        "dispatcher": {
            "receipt_sha256": H(tag + "-dispatcher-source"),
            "unauthorized_attempts": 1,
            "unblocked_unauthorized": 0,
            "tool_calls": 2,
            "blocked_calls": 1,
        },
        "observer": {
            "receipt_sha256": H(tag + "-observer-source"),
            "external_effects": 0,
        },
        "verifier": {
            "receipt_sha256": H(tag + "-verifier-source"),
            "verification_failures": 0,
            "claim_release_failures": 0,
        },
        "recovery": {
            "receipt_sha256": H(tag + "-recovery-source"),
            "recovery_failures": 0,
            "nonreplayable_replays": 0,
        },
        "backend": {
            "receipt_sha256": H(tag + "-backend-source"),
            "schema_bytes": 1200,
            "prompt_tokens": 320,
            "completion_tokens": 25,
            "latency_ms": 200,
        },
    }


def private(arm="a", case_id="c1", tag=None):
    tag = tag or f"{arm}-{case_id}"
    return receipt.make_receipt(
        manifest=manifest(arm),
        case_id=case_id,
        family="graph",
        controls=controls(tag),
        sources=sources(tag),
    )


class PrivateEvalReceiptTests(unittest.TestCase):
    def test_receipt_derives_public_row_exactly(self):
        r = private()
        self.assertEqual(receipt.validate_receipt(r), [])
        row = receipt.row_from_receipt(r)
        self.assertEqual(row["case_id"], "c1")
        self.assertTrue(row["semantic_pass"])
        self.assertEqual(row["unauthorized_attempts"], 1)
        self.assertEqual(row["blocked_calls"], 1)
        self.assertEqual(row["tool_calls"], 2)
        self.assertEqual(row["receipt_sha256"], r["receipt_sha256"])

    def test_report_is_derived_from_receipts_and_sidecar_valid(self):
        r1 = private("a", "c1")
        r2 = receipt.make_receipt(
            manifest=manifest("a"),
            case_id="c2",
            family="priv",
            controls=controls("a-c2"),
            sources=sources("a-c2", semantic_pass=False),
        )
        report = receipt.report_from_receipts(manifest("a"), [r1, r2])
        self.assertEqual(sidecar.validate(report), [])
        self.assertEqual({x["case_id"] for x in report["rows"]}, {"c1", "c2"})
        self.assertEqual(
            {x["receipt_sha256"] for x in report["rows"]},
            {r1["receipt_sha256"], r2["receipt_sha256"]},
        )

    def test_control_binding_mutation_breaks_receipt_hash(self):
        r = private()
        r["controls"]["tool_policy_sha256"] = H("changed-policy")
        errors = receipt.validate_receipt(r)
        self.assertIn("RECEIPT_HASH_MISMATCH", errors)

    def test_source_metric_mutation_breaks_receipt_hash(self):
        r = private()
        r["sources"]["dispatcher"]["blocked_calls"] = 0
        self.assertIn("RECEIPT_HASH_MISMATCH", receipt.validate_receipt(r))

    def test_source_receipt_hashes_must_be_distinct(self):
        s = sources("dup")
        s["backend"]["receipt_sha256"] = s["grader"]["receipt_sha256"]
        with self.assertRaisesRegex(receipt.ReceiptError, "distinct"):
            receipt.make_receipt(
                manifest=manifest(),
                case_id="c1",
                family="graph",
                controls=controls(),
                sources=s,
            )

    def test_reserve_manifest_refused_before_receipt(self):
        m = manifest()
        m["reserve"] = True
        with self.assertRaises(receipt.ReceiptError):
            receipt.make_receipt(
                manifest=m,
                case_id="c1",
                family="graph",
                controls=controls(),
                sources=sources(),
            )

    def test_zero_control_hash_refused(self):
        c = controls()
        c["admission_receipt_sha256"] = "0" * 64
        with self.assertRaisesRegex(receipt.ReceiptError, "control hash"):
            receipt.make_receipt(
                manifest=manifest(),
                case_id="c1",
                family="graph",
                controls=c,
                sources=sources(),
            )

    def test_report_manifest_mismatch_refused(self):
        r = private("a")
        changed = manifest("a")
        changed["code_sha256"] = H("different-code")
        with self.assertRaisesRegex(receipt.ReceiptError, "manifest"):
            receipt.report_from_receipts(changed, [r])

    def test_duplicate_case_receipts_refused(self):
        a = private("a", "c1", "one")
        b = private("a", "c1", "two")
        with self.assertRaisesRegex(receipt.ReceiptError, "duplicate case"):
            receipt.report_from_receipts(manifest("a"), [a, b])

    def test_arm_identity_makes_receipts_disjoint(self):
        a = private("a", "c1", "same-controls")
        b = private("b", "c1", "same-controls")
        self.assertNotEqual(a["receipt_sha256"], b["receipt_sha256"])
        ra = receipt.report_from_receipts(manifest("a"), [a])
        rb = receipt.report_from_receipts(manifest("b"), [b])
        self.assertEqual(sidecar.compare(ra, rb)["status"], "pass")

    def test_public_row_tamper_is_detectable_against_private_receipt(self):
        r = private()
        report = receipt.report_from_receipts(manifest(), [r])
        report["rows"][0]["semantic_pass"] = False
        self.assertNotEqual(report["rows"][0], receipt.row_from_receipt(r))

    def test_write_and_load_private_receipt_are_0600(self):
        r = private()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "receipt.json"
            receipt.write_private_receipt(path, r)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            loaded = receipt.load_private_receipt(path)
            self.assertEqual(loaded, r)
            with self.assertRaises(receipt.ReceiptError):
                receipt.write_private_receipt(path, r)

    def test_loader_refuses_broad_permissions(self):
        r = private()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "receipt.json"
            path.write_text(json.dumps(r))
            path.chmod(0o644)
            with self.assertRaisesRegex(receipt.ReceiptError, "permissions"):
                receipt.load_private_receipt(path)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support required")
    def test_loader_refuses_symlink(self):
        r = private()
        with tempfile.TemporaryDirectory() as d:
            real = Path(d) / "real.json"
            real.write_text(json.dumps(r))
            real.chmod(0o600)
            link = Path(d) / "link.json"
            link.symlink_to(real)
            with self.assertRaisesRegex(receipt.ReceiptError, "non-symlink"):
                receipt.load_private_receipt(link)

    def test_sidecar_cross_arm_reuse_still_hard_blocks(self):
        a = private("a", "c1", "a")
        b = private("b", "c1", "b")
        ra = receipt.report_from_receipts(manifest("a"), [a])
        rb = receipt.report_from_receipts(manifest("b"), [b])
        rb["rows"][0]["receipt_sha256"] = ra["rows"][0]["receipt_sha256"]
        result = sidecar.compare(ra, rb)
        self.assertEqual(result["status"], "block")
        self.assertIn("CROSS_ARM_RECEIPT_REUSE", result["errors"])


if __name__ == "__main__":
    unittest.main()
