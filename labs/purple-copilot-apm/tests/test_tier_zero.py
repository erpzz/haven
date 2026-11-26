import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apm import store, tier_zero as tz
from apm.path_history import get_run, record_paths
from apm.paths import digest

# Objects: kind, Tier Zero. Every edge below is traversable in the fake CE.
NODES = {"U1": ("User", False), "U2": ("User", False), "G1": ("Group", False), "C1": ("Computer", False),
         "Z": ("User", False), "T0A": ("User", True), "T0B": ("Group", True)}
EDGES = [("U1", "MemberOf", "G1"), ("U2", "MemberOf", "G1"), ("G1", "GenericAll", "U2"),
         ("U2", "AdminTo", "C1"), ("G1", "GenericAll", "T0B"), ("C1", "HasSession", "T0A"),
         ("Z", "GenericAll", "T0A"), ("T0A", "AdminTo", "C1")]


class FakeCE:
    """Answers the two query shapes the detector issues, from an in-memory graph."""

    def __init__(self, nodes=NODES, edges=EDGES):
        self.nodes, self.edges, self.queries = dict(nodes), list(edges), []

    def graph(self, edges):
        if not edges:
            raise RuntimeError("POST /api/v2/graphs/cypher returned HTTP 404")
        ids = {oid: str(i) for i, oid in enumerate(sorted({x for s, _, t in edges for x in (s, t)}))}
        return {"nodes": {ids[o]: {"objectId": o, "label": o + "@SAMPLE", "kind": self.nodes[o][0],
                                   "isTierZero": self.nodes[o][1]} for o in ids},
                "edges": [{"source": int(ids[s]), "target": int(ids[t]), "kind": k} for s, k, t in edges]}

    def __call__(self, query):
        self.queries.append(query)
        t0 = lambda o: self.nodes[o][1]
        if "IN [" in query:
            wanted = set(re.findall(r"'([^']*)'", query.split("IN [", 1)[1]))
            hit = [e for e in self.edges if e[2] in wanted and not t0(e[0])]
        else:
            hit = [e for e in self.edges if not t0(e[0]) and t0(e[2])]
        return self.graph(hit)

    def run(self, query):
        try:
            return self(query)
        except RuntimeError as exc:
            if str(exc).endswith("returned HTTP 404"):
                return {"nodes": {}, "edges": []}
            raise


class TierZero(unittest.TestCase):
    def setUp(self):
        tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(store, "ROOT", tmp))
        self.enterContext(patch.object(tz, "ROOT", tmp))
        self.enterContext(patch.object(tz, "verify_reader", lambda: None))
        self.enterContext(patch.object(tz, "ingest_issues", lambda: ([], {"id": 1, "end_time": "t"})))

    def test_boundary_and_exact_exposure(self):
        o = tz.observe("ad", FakeCE().run)
        self.assertEqual(o["boundary"], [("C1", "HasSession", "T0A"), ("G1", "GenericAll", "T0B"),
                                         ("Z", "GenericAll", "T0A")])
        per, population = tz.exposure({"C1", "G1", "Z"}, o["upstream"], o["kinds"])
        # The cycle G1 -> U2 -> G1 terminates. Z reaches C1 only through Tier Zero, so it is not counted.
        self.assertEqual((per["G1"]["users"], per["G1"]["groups"]), (2, 0))
        self.assertEqual((per["C1"]["users"], per["C1"]["groups"]), (2, 1))
        self.assertEqual(per["Z"]["users"], 0)
        self.assertEqual([tz.priority(per[s])["score"] for s in ("G1", "C1", "Z")], [2, 3, 1])
        self.assertEqual(population["users"], 3)

    def test_remediation_plan_groups_shared_exposure(self):
        # A and B expose the same identities, so fixing one of them alone removes nothing.
        sets = {"A": frozenset({"u1", "u2", "u3"}), "B": frozenset({"u1", "u2", "u3"}), "C": frozenset({"u3", "u4"}),
                "D": frozenset(), "E": frozenset({"u5"})}
        plan = tz.remediation_plan(sets, {"A": 2, "B": 1, "C": 1, "D": 4, "E": 1})
        self.assertEqual([(p["sources"], p["identities_removed"], p["identities_still_exposed"], p["control_edges"])
                          for p in plan], [(["A", "B"], 2, 3, 3), (["C"], 2, 1, 1), (["E"], 1, 0, 1)])
        o = tz.observe("ad", FakeCE().run)
        sources = {s for s, _, _ in o["boundary"]}
        plan = tz.remediation_plan(tz.identity_sets(sources, o["upstream"], o["kinds"]),
                                   {s: 1 for s in sources})
        self.assertEqual([(p["sources"], p["identities_removed"], p["identities_still_exposed"]) for p in plan],
                         [(["C1"], 1, 3), (["G1"], 2, 1), (["Z"], 1, 0)])

    def test_expansion_never_follows_tier_zero(self):
        ce = FakeCE()
        o = tz.observe("ad", ce.run)
        self.assertNotIn(("T0A", "AdminTo", "C1"), o["upstream"])
        self.assertTrue(all("NOT (a:Tag_Tier_Zero)" in q for q in ce.queries[1:]))

    def test_ce_empty_result_and_errors(self):
        empty = FakeCE(edges=[])
        o = tz.observe("entra", empty.run)
        self.assertEqual((o["boundary"], o["upstream"]), ([], []))
        with patch.object(tz, "_signed", side_effect=RuntimeError("POST /api/v2/graphs/cypher returned HTTP 404")):
            self.assertEqual(tz.cypher("MATCH"), {"nodes": {}, "edges": []})
        with patch.object(tz, "_signed", side_effect=RuntimeError("POST /api/v2/graphs/cypher returned HTTP 500")):
            with self.assertRaises(RuntimeError):
                tz.cypher("MATCH")

    def test_budgets_fail_closed(self):
        with patch.object(tz, "BOUNDARY_LIMIT", 2), self.assertRaises(tz.Budget):
            tz.observe("ad", FakeCE().run)
        with patch.object(tz, "EXPANSION_LIMIT", 1), self.assertRaises(tz.Budget):
            tz.observe("ad", FakeCE().run)

    def test_query_rejects_injection_and_tagging_disagreement(self):
        for bad in ("X' OR 1=1 //", "A\\'B", 'A"B', "", "A B"):
            with self.assertRaises(ValueError):
                tz.expansion_query("ad", [bad])
        tz.expansion_query("entra", ["/SUBSCRIPTIONS/X/RESOURCEGROUPS/RG(1)/PROVIDERS/A.B/C", "ID@TENANT"])
        ce = FakeCE()
        real = ce.graph
        def lying(edges):
            g = real(edges)
            for n in g["nodes"].values():
                n["isTierZero"] = False
            return g
        ce.graph = lying
        with self.assertRaises(ValueError):
            tz.observe("ad", ce.run)

    def test_lifecycle_rank_and_compact_evidence(self):
        ce = FakeCE()
        first, findings = get_run(record_paths(tz.evidence("ad", ce.run)))
        self.assertEqual({f["state"] for f in findings.values()}, {"new"})
        self.assertNotIn("upstream_edges", first)
        self.assertEqual(set(first["upstream"]), {"edges", "objects", "digest", "calls", "seconds"})
        session = digest([["C1", "HasSession", "T0A"]])
        self.assertEqual(findings[session]["priority"]["score"], 3)
        self.assertEqual({f["state"] for f in get_run(record_paths(tz.evidence("ad", ce.run)))[1].values()},
                         {"persistent"})
        ce.edges.remove(("C1", "HasSession", "T0A"))
        ce.edges.remove(("G1", "GenericAll", "T0B"))
        ce.edges.append(("G1", "WriteDacl", "T0A"))
        _, changed = get_run(record_paths(tz.evidence("ad", ce.run)))
        self.assertEqual(changed[session]["state"], "missing")
        self.assertEqual(changed[session]["priority"]["score"], 3)
        replacement = changed[digest([["G1", "WriteDacl", "T0A"]])]
        self.assertEqual(replacement["state"], "changed")
        self.assertEqual(replacement["replaces"], [digest([["G1", "GenericAll", "T0B"]])])

    def test_unavailable_scan_carries_state_and_rank(self):
        record_paths(tz.evidence("ad", FakeCE().run))
        def broken(query):
            raise RuntimeError("POST /api/v2/graphs/cypher returned HTTP 500")
        with patch("builtins.print"):
            self.assertFalse(tz.scan(broken))
        runs = sorted(get_run(i)[0]["asset"]["key"] for i in (2, 3))
        self.assertEqual(runs, ["tier-zero-ad", "tier-zero-entra"])
        e, carried = get_run(2)
        self.assertTrue(e["unavailable"])
        self.assertEqual({f["observation"] for f in carried.values()}, {"unavailable"})
        self.assertEqual(carried[digest([["C1", "HasSession", "T0A"]])]["priority"]["score"], 3)


if __name__ == "__main__":
    unittest.main()
