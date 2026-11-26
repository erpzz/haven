import copy
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

LABS = Path(__file__).resolve().parents[2]
AUG = LABS / "small-model-augmentation"
sys.path.insert(0, str(AUG))

import bounded_claims as bounded  # noqa: E402
from apm import bounded_claim_adapter as adapter  # noqa: E402
from apm import review, store, tier_zero as tz  # noqa: E402
from apm.path_history import record_paths  # noqa: E402
from test_tier_zero import FakeCE  # noqa: E402


def candidate(bundle, ids):
    return json.dumps({"bundle_sha256": bounded.bundle_sha256(bundle), "claims": ids})


def claims_of(bundle, kind=None, metric=None):
    out = bundle["claims"]
    if kind is not None:
        out = [c for c in out if c["payload"].get("claim_type") == kind]
    if metric is not None:
        out = [c for c in out if c["payload"].get("metric") == metric]
    return out


class PurpleBoundedClaimsIntegration(unittest.TestCase):
    def setUp(self):
        tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for module in (store, tz, review):
            self.enterContext(patch.object(module, "ROOT", tmp))
        self.enterContext(patch.object(tz, "verify_reader", lambda: None))
        self.enterContext(patch.object(tz, "ingest_issues", lambda: ([], {"id": 1, "end_time": "t"})))
        self.ce = FakeCE()
        record_paths(tz.evidence("ad", self.ce.run))

    def result(self, name, args):
        return json.loads(review.call(name, args))

    def bundle(self, name, args):
        result = self.result(name, args)
        bundle = adapter.build_bundle(name, result)
        self.assertEqual(bounded.validate_bundle(bundle), [])
        return result, bundle

    def release(self, bundle, ids, required=()):
        return bounded.release(
            bundle, candidate(bundle, ids),
            allowed_ids=[c["id"] for c in bundle["claims"]],
            required_ids=list(required),
        )

    def test_overview_count_claims_release_and_render_exactly(self):
        result, bundle = self.bundle("purple_tier_zero_overview", {"platform": "ad"})
        principals = claims_of(bundle, "count", "principals_with_direct_control")
        self.assertEqual(len(principals), 1)
        self.assertEqual(principals[0]["payload"]["value"], 3)
        self.assertEqual(bundle["scope"]["snapshot"], result["snapshot"])
        released = self.release(bundle, [principals[0]["id"]])
        self.assertTrue(released["released"], released)
        text = adapter.render_release(released)
        self.assertIn("3 non-Tier Zero principals hold direct Tier Zero control [T0-1].", text)
        self.assertIn("snapshot 1", text)
        self.assertIn("do not establish compromise", text)

    def test_principal_edges_are_exact_host_relationships(self):
        _, bundle = self.bundle(
            "purple_tier_zero_principal",
            {"platform": "ad", "principal": "G1@SAMPLE"},
        )
        edges = claims_of(bundle, "edge")
        self.assertEqual(len(edges), 1)
        payload = edges[0]["payload"]
        self.assertEqual(
            (payload["subject"], payload["relationship"], payload["object"], payload["state"]),
            ("G1@SAMPLE", "GenericAll", "T0B@SAMPLE", "new"),
        )
        released = self.release(bundle, [edges[0]["id"]], required=[edges[0]["id"]])
        text = adapter.render_release(released)
        self.assertIn("G1@SAMPLE -[GenericAll]-> T0B@SAMPLE; state=new", text)
        self.assertNotIn("compromised", text.lower())

    def test_missing_change_forces_limitation_and_neutral_state(self):
        self.ce.edges.remove(("C1", "HasSession", "T0A"))
        record_paths(tz.evidence("ad", self.ce.run))
        _, bundle = self.bundle("purple_tier_zero_changes", {"platform": "ad"})
        missing = [c for c in claims_of(bundle, "edge") if c["payload"]["state"] == "missing"]
        self.assertEqual(len(missing), 1)
        self.assertIn(adapter.MISSING_LIMITATION, bundle["global_limitations"])
        released = self.release(bundle, [missing[0]["id"]], required=[missing[0]["id"]])
        text = adapter.render_release(released)
        self.assertIn("state=missing", text)
        self.assertIn(adapter.MISSING_LIMITATION, text)
        self.assertNotIn("removed", text.lower().split("limitations:", 1)[0])

    def test_compact_search_never_reconstructs_hidden_edges(self):
        with patch.object(review, "COMPACT", 1):
            _, bundle = self.bundle(
                "purple_tier_zero_search",
                {"platform": "ad", "relationship": "genericall"},
            )
        self.assertEqual(claims_of(bundle, "edge"), [])
        holders = claims_of(bundle, "holder_summary")
        self.assertEqual([c["payload"]["holder"] for c in holders], ["G1@SAMPLE", "Z@SAMPLE"])
        released = self.release(bundle, [holders[0]["id"]])
        text = adapter.render_release(released)
        self.assertIn("relationships: GenericAll=1", text)
        self.assertNotIn("T0B@SAMPLE", text)  # compact result did not expose per-edge target detail

    def test_current_prose_verifier_semantic_gap_is_documented(self):
        result = self.result(
            "purple_tier_zero_principal",
            {"platform": "ad", "principal": "G1@SAMPLE"},
        )
        turn = review.Turn("What control does G1 hold?")
        turn.results.append(("purple_tier_zero_principal", json.dumps(result, sort_keys=True)))
        citation = result["edges"][0]["citation"]

        # All names and citations are real. The current prose verifier is intentionally
        # lexical, so it does not bind arbitrary predicates/relationships/timestamps.
        false_semantics = [
            f"G1@SAMPLE has DCSync over T0B@SAMPLE [{citation}].",
            f"G1@SAMPLE compromised T0B@SAMPLE [{citation}].",
            f"Observed 2099-01-01T00:00:00Z: G1@SAMPLE controls T0B@SAMPLE [{citation}].",
        ]
        for text in false_semantics:
            with self.subTest(text=text):
                self.assertEqual(review.Verifier().problems(turn, text), [])

        bundle = adapter.build_bundle("purple_tier_zero_principal", result)
        edge = claims_of(bundle, "edge")[0]
        released = self.release(bundle, [edge["id"]])
        rendered = adapter.render_release(released)
        self.assertIn("-[GenericAll]->", rendered)
        self.assertNotIn("DCSync", rendered)
        self.assertNotIn("compromised", rendered.lower())
        self.assertNotIn("2099-01-01", rendered)

    def test_model_candidate_has_no_narrative_or_predicate_channel(self):
        _, bundle = self.bundle("purple_tier_zero_overview", {"platform": "ad"})
        cid = bundle["claims"][0]["id"]
        raw = json.dumps({
            "bundle_sha256": bounded.bundle_sha256(bundle),
            "claims": [cid],
            "narrative": "Everything is compromised.",
            "predicate": "compromised",
        })
        released = bounded.release(bundle, raw, allowed_ids=[cid])
        self.assertFalse(released["released"])
        self.assertIn("INVALID_CANDIDATE_SHAPE", released["errors"])

    def test_required_conflict_or_limitation_claim_cannot_be_omitted(self):
        self.ce.edges.remove(("C1", "HasSession", "T0A"))
        record_paths(tz.evidence("ad", self.ce.run))
        _, bundle = self.bundle("purple_tier_zero_changes", {"platform": "ad"})
        missing = next(c for c in claims_of(bundle, "edge") if c["payload"]["state"] == "missing")
        total = next(c for c in claims_of(bundle, "count", "change_total_missing"))
        released = bounded.release(
            bundle,
            candidate(bundle, [total["id"]]),
            allowed_ids=[total["id"], missing["id"]],
            required_ids=[missing["id"]],
        )
        self.assertFalse(released["released"])
        self.assertIn("REQUIRED_CLAIM_MISSING", released["errors"])

    def covered_release(self, bundle, ids, policy=None):
        policy = policy or adapter.coverage_policy(bundle)
        return adapter.release_with_coverage(
            bundle, candidate(bundle, ids), policy, bounded.release
        )

    def test_overview_coverage_requires_all_host_summary_counts(self):
        _, bundle = self.bundle("purple_tier_zero_overview", {"platform": "ad"})
        policy = adapter.coverage_policy(bundle)
        required_metrics = {
            c["payload"]["metric"]
            for c in bundle["claims"]
            if c["id"] in policy["required_ids"]
        }
        self.assertEqual(
            required_metrics,
            {
                "principals_with_direct_control",
                "control_edges",
                "identities_able_to_reach_tier_zero",
            },
        )
        one = policy["required_ids"][0]
        released, coverage = self.covered_release(bundle, [one], policy)
        self.assertFalse(released["released"])
        self.assertIn("REQUIRED_CLAIM_MISSING", released["errors"])
        self.assertEqual(coverage["status"], "block")

        released, coverage = self.covered_release(
            bundle, policy["required_ids"], policy
        )
        self.assertTrue(released["released"], released)
        self.assertEqual(coverage["status"], "pass")
        self.assertEqual(
            set(coverage["selected_ids"]), set(policy["required_ids"])
        )

    def test_principal_coverage_requires_all_subject_summary_counts(self):
        _, bundle = self.bundle(
            "purple_tier_zero_principal",
            {"platform": "ad", "principal": "G1@SAMPLE"},
        )
        policy = adapter.coverage_policy(bundle)
        required_metrics = {
            c["payload"]["metric"]
            for c in bundle["claims"]
            if c["id"] in policy["required_ids"]
        }
        self.assertEqual(
            required_metrics,
            {
                "tier_zero_controls_held",
                "identities_able_to_gain_control",
                "reachable_from_users",
                "reachable_from_computers",
                "reachable_from_workloads",
                "reachable_from_groups",
            },
        )
        optional_edge = claims_of(bundle, "edge")[0]
        released, coverage = self.covered_release(
            bundle, [optional_edge["id"]], policy
        )
        self.assertFalse(released["released"])
        self.assertIn("REQUIRED_CLAIM_MISSING", released["errors"])
        self.assertEqual(coverage["selected_ids"], [])

        selected = policy["required_ids"] + [optional_edge["id"]]
        released, coverage = self.covered_release(bundle, selected, policy)
        self.assertTrue(released["released"], released)
        self.assertEqual(set(coverage["selected_ids"]), set(selected))

    def test_changes_coverage_always_requires_missing_total_even_when_zero(self):
        _, zero_bundle = self.bundle(
            "purple_tier_zero_changes", {"platform": "ad"}
        )
        zero_policy = adapter.coverage_policy(zero_bundle)
        zero_missing = next(
            c for c in claims_of(zero_bundle, "count", "change_total_missing")
        )
        self.assertEqual(zero_missing["payload"]["value"], 0)
        self.assertIn(zero_missing["id"], zero_policy["required_ids"])

        self.ce.edges.remove(("C1", "HasSession", "T0A"))
        record_paths(tz.evidence("ad", self.ce.run))
        _, changed_bundle = self.bundle(
            "purple_tier_zero_changes", {"platform": "ad"}
        )
        changed_policy = adapter.coverage_policy(changed_bundle)
        changed_missing = next(
            c for c in claims_of(
                changed_bundle, "count", "change_total_missing"
            )
        )
        self.assertGreater(changed_missing["payload"]["value"], 0)
        self.assertIn(changed_missing["id"], changed_policy["required_ids"])

        other_required = [
            cid for cid in changed_policy["required_ids"]
            if cid != changed_missing["id"]
        ]
        released, coverage = self.covered_release(
            changed_bundle, other_required, changed_policy
        )
        self.assertFalse(released["released"])
        self.assertIn("REQUIRED_CLAIM_MISSING", released["errors"])
        self.assertEqual(coverage["status"], "block")

    def test_search_coverage_requires_totals_but_details_remain_optional(self):
        _, bundle = self.bundle(
            "purple_tier_zero_search",
            {"platform": "ad", "relationship": "genericall"},
        )
        policy = adapter.coverage_policy(bundle)
        required_metrics = {
            c["payload"]["metric"]
            for c in bundle["claims"]
            if c["id"] in policy["required_ids"]
        }
        self.assertEqual(
            required_metrics,
            {"matches_total", "holders_total", "tier_zero_targets_total"},
        )
        detail_ids = [
            c["id"] for c in bundle["claims"]
            if c["id"] not in policy["required_ids"]
        ]
        self.assertTrue(detail_ids)
        released, coverage = self.covered_release(
            bundle, policy["required_ids"], policy
        )
        self.assertTrue(released["released"], released)
        self.assertEqual(coverage["status"], "pass")
        self.assertFalse(set(detail_ids) & set(coverage["selected_ids"]))

    def test_coverage_policy_tamper_and_bundle_mismatch_block(self):
        _, bundle = self.bundle(
            "purple_tier_zero_overview", {"platform": "ad"}
        )
        policy = adapter.coverage_policy(bundle)

        tampered = copy.deepcopy(policy)
        tampered["required_ids"] = tampered["required_ids"][:-1]
        released, coverage = self.covered_release(
            bundle, policy["required_ids"], tampered
        )
        self.assertFalse(released["released"])
        self.assertIn("COVERAGE_REQUIRED_IDS_MISMATCH", released["errors"])
        self.assertEqual(coverage["status"], "block")

        changed = copy.deepcopy(bundle)
        changed["scope"]["snapshot"] += 1
        released, coverage = self.covered_release(
            changed, policy["required_ids"], policy
        )
        self.assertFalse(released["released"])
        self.assertIn("COVERAGE_BUNDLE_MISMATCH", released["errors"])
        self.assertEqual(coverage["status"], "block")

    def test_coverage_receipt_binds_policy_candidate_and_release(self):
        _, bundle = self.bundle(
            "purple_tier_zero_overview", {"platform": "ad"}
        )
        policy = adapter.coverage_policy(bundle)
        raw = candidate(bundle, policy["required_ids"])
        released, coverage = adapter.release_with_coverage(
            bundle, raw, policy, bounded.release
        )
        self.assertTrue(released["released"])
        expected = copy.deepcopy(coverage)
        digest = expected.pop("receipt_sha256")
        self.assertEqual(
            digest,
            __import__("hashlib").sha256(
                json.dumps(
                    expected, sort_keys=True, separators=(",", ":"),
                    ensure_ascii=False, allow_nan=False,
                ).encode()
            ).hexdigest(),
        )
        changed_raw = candidate(bundle, policy["required_ids"][::-1])
        _, changed_coverage = adapter.release_with_coverage(
            bundle, changed_raw, policy, bounded.release
        )
        self.assertNotEqual(
            coverage["candidate_sha256"], changed_coverage["candidate_sha256"]
        )
        self.assertNotEqual(
            coverage["receipt_sha256"], changed_coverage["receipt_sha256"]
        )

    def test_final_head_malformed_candidate_fuzz_is_fail_closed(self):
        _, bundle = self.bundle(
            "purple_tier_zero_overview", {"platform": "ad"}
        )
        policy = adapter.coverage_policy(bundle)
        rng = random.Random(0x132C0DE)
        alphabet = '{}[]":,0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-/ \n\t'
        host_by_id = {claim["id"]: claim for claim in bundle["claims"]}

        corpus = [
            "",
            "null",
            "[]",
            "{}",
            '{"bundle_sha256":"x","claims":[]}',
            '{"bundle_sha256":"' + policy["bundle_sha256"] + '","claims":[]}',
            '{"bundle_sha256":"' + policy["bundle_sha256"] + '","claims":[],"claims":[]}',
            '{"bundle_sha256":"' + policy["bundle_sha256"] + '","claims":[null]}',
            '{"bundle_sha256":"' + policy["bundle_sha256"] + '","claims":["../x"]}',
            '{"bundle_sha256":"' + policy["bundle_sha256"] + '","claims":["' +
                policy["required_ids"][0] + '","' + policy["required_ids"][0] + '"]}',
        ]
        for _ in range(4096):
            n = rng.randrange(0, 257)
            corpus.append("".join(rng.choice(alphabet) for _ in range(n)))

        for raw in corpus:
            released, coverage = adapter.release_with_coverage(
                bundle, raw, policy, bounded.release
            )
            self.assertIs(type(released), dict)
            self.assertEqual(released.get("schema"), bounded.RECEIPT_SCHEMA)
            self.assertIs(type(released.get("released")), bool)
            self.assertIs(type(released.get("errors")), list)
            self.assertIs(type(coverage), dict)
            self.assertIn(coverage["status"], {"pass", "block"})
            self.assertEqual(
                coverage["status"],
                "pass" if released["released"] else "block",
            )
            if released["released"]:
                ids = {claim["id"] for claim in released["claims"]}
                self.assertTrue(set(policy["required_ids"]) <= ids)
                for claim in released["claims"]:
                    self.assertEqual(claim, host_by_id[claim["id"]])

    def test_claim_checkpoint_binding_changes_with_bundle_policy_renderer_or_run(self):
        _, bundle = self.bundle(
            "purple_tier_zero_overview", {"platform": "ad"}
        )
        policy = adapter.coverage_policy(bundle)
        base = adapter.claim_checkpoint_binding(
            bundle,
            policy,
            renderer_sha256="1" * 64,
            run_manifest_sha256="2" * 64,
        )
        self.assertEqual(base["bundle_sha256"], policy["bundle_sha256"])
        self.assertEqual(
            base["coverage_policy_sha256"], policy["policy_sha256"]
        )
        self.assertEqual(len(base["binding_sha256"]), 64)

        renderer_changed = adapter.claim_checkpoint_binding(
            bundle,
            policy,
            renderer_sha256="3" * 64,
            run_manifest_sha256="2" * 64,
        )
        run_changed = adapter.claim_checkpoint_binding(
            bundle,
            policy,
            renderer_sha256="1" * 64,
            run_manifest_sha256="4" * 64,
        )
        self.assertNotEqual(
            base["binding_sha256"], renderer_changed["binding_sha256"]
        )
        self.assertNotEqual(
            base["binding_sha256"], run_changed["binding_sha256"]
        )

        self.ce.edges.add(("U2", "GenericAll", "T0B"))
        changed_result = tz.overview("ad", self.ce.run)
        changed_bundle = adapter.build_bundle_from_result(
            "purple_tier_zero_overview",
            {"platform": "ad"},
            changed_result,
        )
        changed_policy = adapter.coverage_policy(changed_bundle)
        bundle_changed = adapter.claim_checkpoint_binding(
            changed_bundle,
            changed_policy,
            renderer_sha256="1" * 64,
            run_manifest_sha256="2" * 64,
        )
        self.assertNotEqual(
            base["binding_sha256"], bundle_changed["binding_sha256"]
        )
        self.assertNotEqual(
            base["coverage_policy_sha256"],
            bundle_changed["coverage_policy_sha256"],
        )

    def test_claim_checkpoint_binding_rejects_policy_tamper_and_zero_hashes(self):
        _, bundle = self.bundle(
            "purple_tier_zero_search",
            {"platform": "ad", "relationship": "genericall"},
        )
        policy = adapter.coverage_policy(bundle)
        tampered = copy.deepcopy(policy)
        tampered["required_ids"] = tampered["required_ids"][:-1]
        with self.assertRaises(adapter.ClaimAdapterError):
            adapter.claim_checkpoint_binding(
                bundle,
                tampered,
                renderer_sha256="1" * 64,
                run_manifest_sha256="2" * 64,
            )
        with self.assertRaises(adapter.ClaimAdapterError):
            adapter.claim_checkpoint_binding(
                bundle,
                policy,
                renderer_sha256="0" * 64,
                run_manifest_sha256="2" * 64,
            )

    def test_selector_view_exposes_only_opaque_ids_kinds_and_required_bits(self):
        _, bundle = self.bundle(
            "purple_tier_zero_overview", {"platform": "ad"}
        )
        policy = adapter.coverage_policy(bundle)
        view = adapter.selector_view(bundle, policy)
        self.assertEqual(
            set(view),
            {
                "schema", "bundle_sha256", "coverage_policy_sha256",
                "tool", "max_claims", "claims", "selector_sha256",
            },
        )
        self.assertEqual(
            [claim["id"] for claim in view["claims"]],
            policy["allowed_ids"],
        )
        for claim in view["claims"]:
            self.assertEqual(set(claim), {"id", "kind", "required"})
            self.assertEqual(
                claim["required"], claim["id"] in policy["required_ids"]
            )
        encoded = json.dumps(view, sort_keys=True)
        self.assertNotIn("payload", encoded)
        self.assertNotIn("citations", encoded)
        self.assertNotIn("limitations", encoded)
        self.assertNotIn('"platform"', encoded)
        self.assertNotIn('"snapshot"', encoded)

    def test_hidden_claim_and_provenance_sentinels_cannot_leak_to_selector_or_log(self):
        _, bundle = self.bundle(
            "purple_tier_zero_overview", {"platform": "ad"}
        )
        bundle = copy.deepcopy(bundle)
        bundle["claims"][0]["payload"]["private_note"] = "PAYLOAD-SENTINEL-7731"
        bundle["claims"][0]["citations"][0]["private_note"] = "CITATION-SENTINEL-8842"
        bundle["limitations"].append("LIMITATION-SENTINEL-9953")
        policy = adapter.coverage_policy(bundle)
        view = adapter.selector_view(bundle, policy)
        selector_json = json.dumps(view, sort_keys=True)
        for secret in (
            "PAYLOAD-SENTINEL-7731",
            "CITATION-SENTINEL-8842",
            "LIMITATION-SENTINEL-9953",
        ):
            self.assertNotIn(secret, selector_json)

        released, coverage = self.covered_release(
            bundle, policy["required_ids"], policy
        )
        self.assertTrue(released["released"], released)
        coverage_json = json.dumps(coverage, sort_keys=True)
        for secret in (
            "PAYLOAD-SENTINEL-7731",
            "CITATION-SENTINEL-8842",
            "LIMITATION-SENTINEL-9953",
        ):
            self.assertNotIn(secret, coverage_json)

    def test_malformed_candidate_text_cannot_leak_through_error_receipt(self):
        _, bundle = self.bundle(
            "purple_tier_zero_overview", {"platform": "ad"}
        )
        policy = adapter.coverage_policy(bundle)
        raw = "MALFORMED-PRIVATE-SENTINEL-2291"
        released, coverage = adapter.release_with_coverage(
            bundle, raw, policy, bounded.release
        )
        self.assertFalse(released["released"])
        self.assertNotIn(raw, json.dumps(released, sort_keys=True))
        self.assertNotIn(raw, json.dumps(coverage, sort_keys=True))
        self.assertEqual(
            coverage["candidate_sha256"],
            __import__("hashlib").sha256(raw.encode()).hexdigest(),
        )

    def test_disclosure_policy_is_hash_bound_and_declares_hidden_surfaces(self):
        policy = adapter.disclosure_policy()
        body = copy.deepcopy(policy)
        digest = body.pop("policy_sha256")
        self.assertEqual(
            digest,
            __import__("hashlib").sha256(
                json.dumps(
                    body, sort_keys=True, separators=(",", ":"),
                    ensure_ascii=False, allow_nan=False,
                ).encode()
            ).hexdigest(),
        )
        self.assertIn("claims[].payload", policy["model_hidden_fields"])
        self.assertIn("claims[].citations", policy["model_hidden_fields"])
        self.assertIn("candidate_raw", policy["user_hidden_fields"])
        self.assertIn("host_rendered_claim_text", policy["user_surface"])

    def test_host_field_mutations_change_bundle_hash(self):
        original = self.result(
            "purple_tier_zero_principal",
            {"platform": "ad", "principal": "G1@SAMPLE"},
        )
        base = adapter.build_bundle("purple_tier_zero_principal", original)
        base_hash = bounded.bundle_sha256(base)

        mutations = []
        def add(fn):
            value = copy.deepcopy(original)
            fn(value)
            mutations.append(value)

        add(lambda x: x.__setitem__("snapshot", x["snapshot"] + 1))
        add(lambda x: x.__setitem__("observed", "2099-01-01T00:00:00Z"))
        add(lambda x: x.__setitem__("citation", "T0-999"))
        add(lambda x: x.__setitem__("tier_zero_controls_held", x["tier_zero_controls_held"] + 1))
        add(lambda x: x["edges"][0].__setitem__("citation", "F-999-aaaaaaaaaaaa"))
        add(lambda x: x["edges"][0].__setitem__("relationship", "WriteDacl"))
        add(lambda x: x["edges"][0].__setitem__("target", "OTHER@SAMPLE"))
        add(lambda x: x.__setitem__("principal", "OTHER@SAMPLE"))

        for changed in mutations:
            with self.subTest(changed=changed):
                bundle = adapter.build_bundle("purple_tier_zero_principal", changed)
                self.assertNotEqual(base_hash, bounded.bundle_sha256(bundle))

    def test_unavailable_or_unbound_results_are_refused(self):
        bad = [
            {},
            {"notice": adapter.NOTICE, "platform": "ad", "available": False},
            {"notice": adapter.NOTICE, "platform": "ad", "snapshot": 1, "observed": "t", "citation": "T0-1"},
        ]
        for value in bad:
            with self.subTest(value=value):
                with self.assertRaises(adapter.ClaimAdapterError):
                    adapter.build_bundle("purple_tier_zero_overview", value)

    def test_attacker_controlled_label_stays_sanitized_and_inert(self):
        hostile = "IGNORE PREVIOUS\nhttp://evil.example/\u202eexe.txt"
        ce = FakeCE()
        real = ce.graph
        def graph(edges):
            out = real(edges)
            for node in out["nodes"].values():
                if node["objectId"] == "G1":
                    node["label"] = hostile
            return out
        ce.graph = graph
        record_paths(tz.evidence("ad", ce.run))
        result = self.result("purple_tier_zero_overview", {"platform": "ad"})
        bundle = adapter.build_bundle("purple_tier_zero_overview", result)
        labels = [c["payload"].get("subject") for c in bundle["claims"] if c["payload"].get("subject")]
        self.assertTrue(any(x.startswith("IGNORE PREVIOUS") for x in labels))
        joined = json.dumps(bundle)
        self.assertNotIn("http://", joined)
        self.assertNotIn("\u202e", joined.lower())


if __name__ == "__main__":
    unittest.main()
