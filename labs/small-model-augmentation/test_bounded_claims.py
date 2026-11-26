import copy
import json
import unittest

import bounded_claims as b


def bundle():
    return {
        "schema": b.BUNDLE_SCHEMA,
        "scope": {
            "tenant": "tenant-a",
            "dataset": "dataset-a",
            "snapshot": "snapshot-7",
            "as_of": "2026-11-25T00:00:00Z",
        },
        "claims": [
            {
                "id": "c-control",
                "citation": "F-1",
                "payload": {
                    "subject": "A",
                    "predicate": "controls",
                    "object": "B",
                    "observed_at": "2026-11-25T00:00:00Z",
                },
            },
            {
                "id": "c-reach",
                "citation": "P-2",
                "payload": {
                    "subject": "A",
                    "predicate": "reachable_users",
                    "value": 7,
                    "observed_at": "2026-11-25T00:00:00Z",
                },
            },
            {
                "id": "c-membership",
                "citation": "F-3",
                "payload": {
                    "subject": "Q",
                    "predicate": "membership",
                    "value": "reported",
                    "observed_at": "2026-11-24T00:00:00Z",
                },
            },
        ],
        "global_limitations": [
            "membership is not compromise",
            "missing is not removal",
        ],
    }


def candidate(bundle_value, ids):
    return json.dumps({
        "bundle_sha256": b.bundle_sha256(bundle_value),
        "claims": ids,
    })


class BoundedClaimsTests(unittest.TestCase):
    def test_valid_selection_returns_exact_host_payloads(self):
        x = bundle()
        r = b.release(x, candidate(x, ["c-reach", "c-control"]),
                      allowed_ids=["c-control", "c-reach"])
        self.assertTrue(r["released"])
        self.assertEqual([c["id"] for c in r["claims"]], ["c-control", "c-reach"])
        self.assertEqual(r["claims"][0]["payload"]["predicate"], "controls")
        self.assertEqual(r["claims"][1]["payload"]["value"], 7)

    def test_candidate_order_cannot_control_presentation_order(self):
        x = bundle()
        r = b.release(x, candidate(x, ["c-reach", "c-control"]),
                      allowed_ids=["c-control", "c-reach"])
        self.assertEqual([c["id"] for c in r["claims"]], ["c-control", "c-reach"])

    def test_candidate_has_no_prose_channel(self):
        x = bundle()
        raw = json.dumps({
            "bundle_sha256": b.bundle_sha256(x),
            "claims": ["c-control"],
            "narrative": "A compromised B",
        })
        self.assertIn("INVALID_CANDIDATE_SHAPE",
                      b.release(x, raw, allowed_ids=["c-control"])["errors"])

    def test_candidate_cannot_modify_predicate_or_value(self):
        x = bundle()
        raw = json.dumps({
            "bundle_sha256": b.bundle_sha256(x),
            "claims": [{"id": "c-control", "predicate": "compromised"}],
        })
        self.assertIn("INVALID_CANDIDATE_CLAIMS",
                      b.release(x, raw, allowed_ids=["c-control"])["errors"])

    def test_candidate_cannot_splice_fields_from_two_claims(self):
        x = bundle()
        raw = json.dumps({
            "bundle_sha256": b.bundle_sha256(x),
            "claims": ["c-control"],
            "subject": "A",
            "value": 7,
        })
        self.assertIn("INVALID_CANDIDATE_SHAPE",
                      b.release(x, raw, allowed_ids=["c-control", "c-reach"])["errors"])

    def test_disallowed_claim_is_blocked(self):
        x = bundle()
        r = b.release(x, candidate(x, ["c-membership"]), allowed_ids=["c-control"])
        self.assertIn("CLAIM_NOT_ALLOWED", r["errors"])

    def test_unknown_allowed_id_is_host_configuration_error(self):
        x = bundle()
        r = b.release(x, candidate(x, []), allowed_ids=["ghost"])
        self.assertIn("ALLOWED_ID_NOT_IN_BUNDLE", r["errors"])

    def test_required_claim_must_be_allowed(self):
        x = bundle()
        r = b.release(x, candidate(x, []),
                      allowed_ids=["c-control"], required_ids=["c-reach"])
        self.assertIn("REQUIRED_ID_NOT_ALLOWED", r["errors"])

    def test_required_claim_cannot_be_omitted_by_model(self):
        x = bundle()
        r = b.release(x, candidate(x, ["c-control"]),
                      allowed_ids=["c-control", "c-reach"],
                      required_ids=["c-reach"])
        self.assertIn("REQUIRED_CLAIM_MISSING", r["errors"])

    def test_conflicting_or_limiting_claim_can_be_required(self):
        x = bundle()
        r = b.release(x, candidate(x, ["c-membership"]),
                      allowed_ids=["c-membership"],
                      required_ids=["c-membership"])
        self.assertTrue(r["released"])
        self.assertEqual(r["claims"][0]["payload"]["value"], "reported")

    def test_global_limitations_cannot_be_omitted(self):
        x = bundle()
        r = b.release(x, candidate(x, ["c-control"]), allowed_ids=["c-control"])
        self.assertEqual(r["global_limitations"], x["global_limitations"])

    def test_scope_cannot_be_changed_by_candidate(self):
        x = bundle()
        r = b.release(x, candidate(x, ["c-control"]), allowed_ids=["c-control"])
        self.assertEqual(r["scope"]["snapshot"], "snapshot-7")
        self.assertEqual(r["scope"]["tenant"], "tenant-a")

    def test_stale_candidate_hash_blocks_after_scope_change(self):
        x = bundle()
        raw = candidate(x, ["c-control"])
        x["scope"]["snapshot"] = "snapshot-8"
        r = b.release(x, raw, allowed_ids=["c-control"])
        self.assertIn("CANDIDATE_BUNDLE_MISMATCH", r["errors"])

    def test_bundle_hash_binds_predicate(self):
        x = bundle()
        before = b.bundle_sha256(x)
        x["claims"][0]["payload"]["predicate"] = "member_of"
        self.assertNotEqual(before, b.bundle_sha256(x))

    def test_bundle_hash_binds_timestamp(self):
        x = bundle()
        before = b.bundle_sha256(x)
        x["claims"][0]["payload"]["observed_at"] = "1999-01-01T00:00:00Z"
        self.assertNotEqual(before, b.bundle_sha256(x))

    def test_bundle_hash_is_claim_order_independent(self):
        x = bundle()
        y = copy.deepcopy(x)
        y["claims"].reverse()
        self.assertEqual(b.bundle_sha256(x), b.bundle_sha256(y))

    def test_expected_bundle_hash_detects_host_bundle_change(self):
        x = bundle()
        expected = b.bundle_sha256(x)
        x["claims"][0]["payload"]["object"] = "C"
        r = b.release(x, candidate(x, ["c-control"]),
                      allowed_ids=["c-control"],
                      expected_bundle_sha256=expected)
        self.assertIn("BUNDLE_CHANGED", r["errors"])

    def test_invalid_expected_bundle_hash_is_distinct(self):
        x = bundle()
        r = b.release(x, candidate(x, ["c-control"]),
                      allowed_ids=["c-control"],
                      expected_bundle_sha256="not-a-hash")
        self.assertIn("INVALID_EXPECTED_BUNDLE_HASH", r["errors"])

    def test_duplicate_bundle_claim_id_blocks(self):
        x = bundle()
        x["claims"].append(copy.deepcopy(x["claims"][0]))
        self.assertIn("DUPLICATE_CLAIM_ID", b.validate_bundle(x))

    def test_duplicate_candidate_claim_blocks(self):
        x = bundle()
        raw = json.dumps({
            "bundle_sha256": b.bundle_sha256(x),
            "claims": ["c-control", "c-control"],
        })
        self.assertIn("DUPLICATE_CANDIDATE_CLAIM",
                      b.release(x, raw, allowed_ids=["c-control"])["errors"])

    def test_duplicate_candidate_json_key_blocks(self):
        raw = ('{"bundle_sha256":"' + "0" * 64
               + '","bundle_sha256":"' + "0" * 64 + '","claims":[]}')
        _, errors = b.parse_candidate(raw)
        self.assertIn("INVALID_CANDIDATE_JSON", errors)

    def test_candidate_budget_is_enforced(self):
        x = bundle()
        r = b.release(x, candidate(x, ["c-control"]),
                      allowed_ids=["c-control"], max_claims=0)
        self.assertIn("CLAIM_BUDGET_EXCEEDED", r["errors"])

    def test_release_returns_copies_not_host_objects(self):
        x = bundle()
        r = b.release(x, candidate(x, ["c-control"]), allowed_ids=["c-control"])
        r["claims"][0]["payload"]["object"] = "mutated"
        r["scope"]["tenant"] = "mutated"
        self.assertEqual(x["claims"][0]["payload"]["object"], "B")
        self.assertEqual(x["scope"]["tenant"], "tenant-a")

    def test_empty_selection_is_allowed_when_host_requires_nothing(self):
        x = bundle()
        r = b.release(x, candidate(x, []), allowed_ids=["c-control"])
        self.assertTrue(r["released"])
        self.assertEqual(r["claims"], [])

    def test_empty_scope_is_rejected(self):
        x = bundle()
        x["scope"] = {}
        self.assertIn("INVALID_SCOPE", b.validate_bundle(x))

    def test_malformed_bundle_payload_fails_closed(self):
        x = bundle()
        x["claims"][0]["payload"]["value"] = float("nan")
        self.assertIn("INVALID_PAYLOAD", b.validate_bundle(x))

    def test_invalid_candidate_nonfinite_json_blocks(self):
        x = bundle()
        raw = ('{"bundle_sha256":"' + b.bundle_sha256(x)
               + '","claims":[],"x":NaN}')
        _, errors = b.parse_candidate(raw)
        self.assertIn("INVALID_CANDIDATE_JSON", errors)


if __name__ == "__main__":
    unittest.main()
