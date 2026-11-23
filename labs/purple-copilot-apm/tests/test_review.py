import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apm import review, store, tier_zero as tz
from apm.path_history import record_paths
from test_tier_zero import FakeCE


class Review(unittest.TestCase):
    def setUp(self):
        tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for module in (store, tz, review):
            self.enterContext(patch.object(module, "ROOT", tmp))
        self.enterContext(patch.object(tz, "verify_reader", lambda: None))
        self.enterContext(patch.object(tz, "ingest_issues", lambda: ([], {"id": 1, "end_time": "t"})))
        self.ce = FakeCE()
        record_paths(tz.evidence("ad", self.ce.run))

    def evidence(self, *calls):
        turn = review.Turn("question")
        for name, args in calls:
            turn.results.append((name, review.call(name, args)))
        return turn

    def test_tools_return_cited_evidence(self):
        o = json.loads(review.call("purple_tier_zero_overview", {"platform": "ad"}))
        self.assertEqual((o["citation"], o["principals_with_direct_control"], o["control_edges"]), ("T0-1", 3, 3))
        self.assertEqual([p["principal"] for p in o["top_principals"]], ["C1@SAMPLE", "G1@SAMPLE", "Z@SAMPLE"])
        p = json.loads(review.call("purple_tier_zero_principal", {"platform": "ad", "principal": "g1@sample"}))
        self.assertEqual((p["tier_zero_controls_held"], p["edges"][0]["relationship"], p["reachable_from"]["users"]), (1, "GenericAll", 2))
        self.assertEqual(p["edges"][0]["meaning"], "G1@SAMPLE has full control of T0B@SAMPLE")
        self.assertTrue(p["edges"][0]["citation"].startswith("F-1-"))
        self.assertFalse(json.loads(review.call("purple_tier_zero_overview", {"platform": "entra"}))["available"])
        self.ce.edges.remove(("C1", "HasSession", "T0A"))
        record_paths(tz.evidence("ad", self.ce.run))
        c = json.loads(review.call("purple_tier_zero_changes", {"platform": "ad"}))
        self.assertEqual((c["previous_snapshot"], c["counts"]), (1, {"missing": 1, "persistent": 2}))
        self.assertTrue(c["summary"].startswith("At snapshot 2, 0 Tier Zero control edges are new, 0 changed route and 1 are missing"))
        self.assertEqual(c["missing"][0]["principal"], "C1@SAMPLE")

    def test_gate(self):
        strict, turn = review.Gate(strict=True), review.Turn()
        self.assertIn("only the read-only", strict.check(turn, "terminal", {"command": "id"}))
        self.assertIsNone(review.Gate(strict=False).check(turn, "terminal", {"command": "id"}))
        self.assertIn("exactly", strict.check(turn, "purple_tier_zero_overview", {"platform": "ad", "x": 1}))
        self.assertIn("platform", strict.check(turn, "purple_tier_zero_overview", {"platform": "gcp"}))
        self.assertIn("no recorded", strict.check(turn, "purple_tier_zero_principal",
                                                  {"platform": "ad", "principal": "T0A@SAMPLE"}))
        self.assertIsNone(strict.check(turn, "purple_tier_zero_overview", {"platform": "ad"}))
        self.assertIn("already retrieved", strict.check(turn, "purple_tier_zero_overview", {"platform": "ad"}))
        self.assertIsNone(strict.check(turn, "purple_tier_zero_principal", {"platform": "ad", "principal": "C1@SAMPLE"}))
        with patch.object(review, "MAX_CALLS", 2):
            self.assertIn("budget", strict.check(turn, "purple_tier_zero_changes", {"platform": "ad"}))

    def test_verifier(self):
        v = review.Verifier()
        turn = self.evidence(("purple_tier_zero_overview", {"platform": "ad"}))
        o = json.loads(turn.results[0][1])
        c1 = o["top_principals"][0]["citation"]
        good = (f"In AD, 3 principals hold direct control of Tier Zero [T0-1].\n"
                f"1. C1@SAMPLE: 3 identities can gain its HasSession control [{c1}].")
        self.assertEqual(v.problems(turn, good), [])
        self.assertIn("numbers absent from evidence: 40", v.problems(turn, good.replace("3 identities", "40 identities"))[0])
        self.assertIn("unknown citations", v.problems(turn, good + " [F-1-0123456789ab]")[0])
        self.assertIn("unknown citations", v.problems(turn, good + " [F-1-ADCSESC3]")[0])
        self.assertEqual(v.problems(turn, "Three principals control Tier Zero."), ["no evidence citation"])
        self.assertIn("principals absent", v.problems(turn, good + " MALLORY@SAMPLE is exposed.")[0])
        self.assertEqual(v.problems(turn, good + " Review C1@SAMPLE."), [])
        self.assertEqual(v.problems(review.Turn(), "Nothing retrieved, 12 claims."), [])
        # A number that exists in the evidence, but for another principal or only as a headline, is misattributed.
        bound = review.Turn()
        bound.results.append(("purple_tier_zero_overview", json.dumps({
            "platform": "ad", "citation": "T0-9", "identities_able_to_reach_tier_zero": 99,
            "top_principals": [{"principal": "C1@SAMPLE", "citation": "P-9-aaaaaaaaaaaa", "users": 7},
                               {"principal": "Q@SAMPLE", "citation": "P-9-bbbbbbbbbbbb", "users": 77}]})))
        self.assertEqual(v.problems(bound, "C1@SAMPLE is reachable from 7 users [P-9-aaaaaaaaaaaa]. "
                                           "Q@SAMPLE from 77 [P-9-bbbbbbbbbbbb]. 99 identities overall [T0-9]."), [])
        for claim in ("C1@SAMPLE is reachable from 77 users [P-9-aaaaaaaaaaaa].",
                      "C1@SAMPLE is reachable from 99 identities [T0-9]."):
            self.assertIn("wrong principal", " ".join(v.problems(bound, claim)))
        self.assertIn("numbers absent", v.problems(turn, good + " Twenty-three more exist.")[0])
        self.assertEqual(v.problems(turn, good.replace("3 principals", "three principals")), [])
        dated = good + " Observed 2026-11-22T21:31:38.091201+00:00, about 21:31 UTC [citation: T0-1]."
        self.assertEqual(v.problems(turn, dated), [])
        # Digits inside identifiers do not ground a fabricated count.
        turn.results.append(("purple_tier_zero_overview", json.dumps({"platform": "ad", "label": "S-1-5-21-9999"})))
        self.assertTrue(v.problems(turn, good.replace("3 identities", "9999 identities")))

    def test_rendered_sentences_only_use_returned_numbers(self):
        turn = self.evidence(("purple_tier_zero_overview", {"platform": "ad"}),
                             ("purple_tier_zero_principal", {"platform": "ad", "principal": "C1@SAMPLE"}),
                             ("purple_tier_zero_changes", {"platform": "ad"}))
        sentences = []
        def walk(value, key=""):
            if isinstance(value, dict):
                for k, v in value.items():
                    walk(v, k)
            elif isinstance(value, list):
                for v in value:
                    walk(v, key)
            elif isinstance(value, str) and key in ("summary", "meaning", "reach"):
                sentences.append(value)
        for _, data in turn.results:
            walk(json.loads(data))
        self.assertTrue(sentences)
        quoted = " ".join(sentences) + " [T0-1]"
        self.assertEqual(review.Verifier().problems(turn, quoted), [])

    def test_fallback_passes_its_own_verifier(self):
        turn = self.evidence(("purple_tier_zero_overview", {"platform": "ad"}),
                             ("purple_tier_zero_principal", {"platform": "ad", "principal": "C1@SAMPLE"}),
                             ("purple_tier_zero_changes", {"platform": "ad"}))
        text = review.fallback(turn, ["no evidence citation", "numbers absent from evidence: 412",
                                      "principals absent from evidence: mallory@sample"])
        self.assertIn("[T0-1]", text)
        self.assertNotIn("412", text)
        self.assertNotIn("mallory", text.lower())
        self.assertEqual(review.Verifier().problems(turn, text.split("Retrieved evidence:", 1)[1]), [])


if __name__ == "__main__":
    unittest.main()
