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
        self.assertEqual(run.extract_answer('ok {"answer": ["b", "a"]}', "set"), ["a", "b"])
        self.assertIs(run.extract_answer('{"answer": false}', "bool"), False)
        self.assertEqual(run.extract_answer('{"answer": "7"}', "int"), 7)
        self.assertEqual(run.extract_cypher("```cypher\nMATCH (n) RETURN n;\n```"), "MATCH (n) RETURN n")

    def test_gold_is_not_trivially_empty(self):
        qs = [q for i in T.make_suite(run.SUITE_SEED, 12) for q in i["questions"]]
        nontrivial = sum(q["answer"] not in ([], False, 0) for q in qs)
        self.assertGreater(nontrivial / len(qs), 0.6)


if __name__ == "__main__":
    unittest.main()
