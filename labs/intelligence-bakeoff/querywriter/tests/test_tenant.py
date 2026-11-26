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
        for bad in (
            "CREATE (:User {id: 'x', enabled: true})",
            "CREATE\n(:User {id: 'x', enabled: true})",
            "MATCH (u:User) DELETE u",
            "MATCH (u:User) /* split */\nDELETE u",
            "MATCH (u:User) SET\nu.enabled = false",
            "MATCH (u:User) REMOVE u.enabled",
            "CALL current_setting('x')",
            "MATCH (u) RETURN u; DROP TABLE User",
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    T.run_query(conn, bad, "set")

    def test_read_only_guard_ignores_literals_comments_and_quoted_identifiers(self):
        for good in (
            "RETURN 'create delete set merge'",
            'RETURN "drop install attach"',
            "MATCH (n) // create delete set\nRETURN n.id",
            "MATCH (n) /* create delete set */ RETURN n.id",
            "MATCH (n {`set`: 'create'}) RETURN n.id",
        ):
            with self.subTest(good=good):
                T.assert_read_only(good)

    def test_read_only_guard_rejects_malformed_lexical_state(self):
        for bad in ("RETURN 'unterminated", "MATCH (n) /* unterminated", "RETURN `unterminated"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    T.assert_read_only(bad)

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

    def test_count_requires_one_row_one_column_genuine_int(self):
        q = {"kind": "int", "answer": 1}
        for rows in ([[True]], [[1.9]], [[1], [4]], [[1, 4]], [], [[None]]):
            self.assertIsNone(T.normalize(rows, "int"), rows)
            self.assertFalse(run.score(q, "int", T.normalize(rows, "int"))["exact"], rows)
        self.assertEqual(T.normalize([[1]], "int"), 1)

    def test_nearest_rank_p95(self):
        self.assertEqual(run.nearest_rank(list(range(1, 21)), 95), 19)
        self.assertEqual(run.nearest_rank(list(range(1, 22)), 95), 20)
        self.assertEqual(run.nearest_rank([5.0], 95), 5.0)

    def test_model_call_failure_scores_zero_and_run_continues(self):
        import argparse, json as _json, tempfile as _tf
        calls = {"n": 0}
        def failing_chat(*a):
            calls["n"] += 1
            raise TimeoutError("timed out")
        orig, run.chat = run.chat, failing_chat
        try:
            out = pathlib.Path(_tf.mkdtemp()) / "f.jsonl"
            for arm in ("cypher", "prose"):
                path = out.with_name(f"{arm}.jsonl")
                run.cmd_eval(argparse.Namespace(arm=arm, base_url="http://127.0.0.1:1/v1", model="x", label=arm,
                                                out=str(path), tenants=1, per_tenant=3))
                rows = [_json.loads(l) for l in pathlib.Path(path).read_text().splitlines()]
                self.assertEqual(len(rows), 3)
                self.assertTrue(all(not r["exact"] and "model call failed" in r["error"] for r in rows))
                self.assertTrue(all(r["id"] for r in rows))
                self.assertFalse(any(r.get("retried") for r in rows))
        finally:
            run.chat = orig

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
