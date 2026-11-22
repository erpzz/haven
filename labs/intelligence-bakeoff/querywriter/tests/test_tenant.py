"""python3 -m unittest discover -s querywriter/tests -v   (needs: pip install kuzu)"""
import os
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import run  # noqa: E402
import tenant as T  # noqa: E402


class Suite(unittest.TestCase):
    def test_oracle_cypher_matches_python_gold(self):
        for item in T.make_suite(run.SUITE_SEED, 12):
            _, conn = T.load_kuzu(item["tenant"], os.path.join(tempfile.mkdtemp(), "g"))
            for q in item["questions"]:
                got = T.run_query(conn, T.ORACLE_CYPHER[q["family"]].format(**q["params"]), q["kind"])
                self.assertEqual(got, q["answer"], q["id"])

    def test_deterministic(self):
        a, b = T.make_suite(run.SUITE_SEED, 3), T.make_suite(run.SUITE_SEED, 3)
        self.assertEqual([q["answer"] for i in a for q in i["questions"]],
                         [q["answer"] for i in b for q in i["questions"]])

    def test_acyclic_nesting(self):
        for item in T.make_suite(run.SUITE_SEED, 12):
            t = item["tenant"]
            for g in t["groups"]:
                self.assertNotIn(g, T._containers(t, g), f"cycle through {g}")

    def test_write_queries_refused(self):
        item = T.make_suite(run.SUITE_SEED, 1)[0]
        _, conn = T.load_kuzu(item["tenant"], os.path.join(tempfile.mkdtemp(), "g"))
        for bad in ("CREATE (:User {id: 'x', enabled: true})", "MATCH (u:User) DELETE u",
                    "MATCH (u:User) SET u.enabled = false"):
            with self.assertRaises(ValueError):
                T.run_query(conn, bad, "set")

    def test_answer_extraction(self):
        self.assertEqual(run.extract_answer('ok {"answer": ["b", "a"]}'), ("set", ["a", "b"]))
        self.assertEqual(run.extract_answer('{"answer": false}'), ("bool", False))
        self.assertEqual(run.extract_answer('{"answer": 7}'), ("int", 7))
        self.assertEqual(run.extract_answer('{"answer": "7"}'), (None, None))  # a string is not a declared count
        self.assertEqual(run.extract_cypher("TYPE: set\n```cypher\nMATCH (n) RETURN n;\n```"), "MATCH (n) RETURN n")
        self.assertEqual(run.declared_type("TYPE: bool\n```cypher\nRETURN true\n```"), "bool")
        self.assertIsNone(run.declared_type("```cypher\nRETURN 1\n```"))

    def test_type_inference_from_result_shape(self):
        self.assertEqual(T.infer_type([[True]]), "bool")
        self.assertEqual(T.infer_type([[3]]), "int")
        self.assertEqual(T.infer_type([["a"], ["b"]]), "set")
        self.assertEqual(T.infer_type([]), "set")

    def test_arms_never_read_gold_inside_the_timed_block(self):
        src = (HERE / "run.py").read_text()
        block = src[src.index("t0 = time.monotonic()  # one end-to-end timer"):src.index("secs = time.monotonic() - t0")]
        for leak in ('q["kind"]', 'q["answer"]', 'rec["gold', "gold_kind"):
            self.assertNotIn(leak, block)

    def test_type_mismatch_scores_zero(self):
        q = {"kind": "int", "answer": 2}
        self.assertFalse(run.score(q, "set", ["a", "b"])["exact"])
        self.assertTrue(run.score(q, "int", 2)["exact"])

    def test_code_alone_parser(self):
        item = T.make_suite(run.SUITE_SEED, 1)[0]
        for q in item["questions"]:
            fam, params = run.parse_question(q["question"], item["tenant"])
            self.assertEqual(fam, q["family"], q["question"])
            self.assertEqual({k: v for k, v in q["params"].items()}, {k: params[k] for k in q["params"]})
        self.assertIsNone(run.parse_question("Who can reset the CFO's password?", item["tenant"]))

    def test_gold_is_not_trivially_empty(self):
        qs = [q for i in T.make_suite(run.SUITE_SEED, 12) for q in i["questions"]]
        nontrivial = sum(q["answer"] not in ([], False, 0) for q in qs)
        self.assertGreater(nontrivial / len(qs), 0.6)


if __name__ == "__main__":
    unittest.main()
