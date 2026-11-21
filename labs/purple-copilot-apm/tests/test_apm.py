import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from apm import dashboard, graph, store
from apm.policy import authorize


class History(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.enterContext(patch.object(store, "ROOT", Path(temp.name)))
        self.edge = ("synthetic-member", "MemberOf", authorize("ad").target)
        self.tick = 0

    def ev(self, present=True, source=None, issues=None, **updates):
        self.tick += 1
        time = f"2026-01-01T00:{self.tick:02}:00+00:00"
        e = dict(scope="ad", observed=time, source=source or str(self.tick), collection_utc=time,
                 query=authorize("ad").query, issues=issues or [], edges=[self.edge] if present else [],
                 expected_members=[self.edge[0]] if present else [])
        return dict(e, **updates)

    def step(self, *args, **kwargs):
        n = store.record(self.ev(*args, **kwargs))
        with closing(store.database(True)) as db:
            return db.execute("SELECT state,investigation FROM changes WHERE run=?", (n,)).fetchone()[0]

    def test_lifecycle_and_reopened_membership(self):
        self.assertEqual(self.step(), "new")
        self.assertEqual(self.step(), "persistent")
        self.assertEqual(self.step(False), "missing")
        self.assertEqual(self.step(False), "confirmed-remediated")
        self.assertEqual(self.step(), "new")

    def test_incomplete_and_failed_reads_break_corroboration(self):
        self.step()
        self.step(False)
        self.assertEqual(self.step(False, issues=["partial"]), "missing")
        self.assertEqual(self.step(False), "missing")
        self.assertEqual(self.step(False, unavailable=True, issues=["timeout"]), "missing")
        self.assertEqual(self.step(False), "missing")

    def test_unavailable_does_not_change_observed_presence(self):
        self.step()
        self.assertEqual(self.step(False, unavailable=True, issues=["403"]), "new")

    def test_replaying_same_collection_and_old_collections(self):
        self.step()
        self.step(False, "same")
        self.assertEqual(self.step(False, "same"), "missing")
        self.assertEqual(self.step(False, collection_utc="2025-12-31T00:00:00+00:00"), "missing")
        self.assertEqual(self.step(False), "missing")

    def test_unknown_time_or_membership_mismatch(self):
        self.step()
        for kwargs in [{"collection_utc": None}, {"expected_members": [self.edge[0]]},
                       {"collection_utc": "2026-01-01T00:00:00"}]:
            self.assertEqual(self.step(False, **kwargs), "missing")
            self.assertEqual(self.step(False), "missing")

    def test_retry_order_and_atomicity(self):
        e = self.ev()
        n = store.record(e)
        self.assertEqual(store.record(e), n)
        with self.assertRaises(ValueError):
            store.record(dict(e, source="conflicting"))
        with self.assertRaises(ValueError):
            store.record(dict(e, observed="2024-01-01T00:00:00+00:00"))
        with closing(store.database(True)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM runs").fetchone()[0], 1)
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("DELETE FROM changes")

    def test_hypothesis_writer_cannot_change_facts_or_policy(self):
        n = store.record(self.ev())
        with closing(store.conclusion_writer()) as db, db:
            db.execute("INSERT INTO conclusions(run,classification) VALUES(?,'hypothesis')", (n,))
            for statement in ("DELETE FROM runs", "UPDATE changes SET state='confirmed-remediated'",
                              "DELETE FROM conclusions", "DROP TABLE runs", "PRAGMA foreign_keys=off"):
                with self.assertRaises(sqlite3.DatabaseError):
                    db.execute(statement)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO conclusions(run,classification) VALUES(?,'fact')", (n,))

    def test_observations_at_same_source_time_cannot_confirm(self):
        self.step()
        self.step(False)
        self.assertEqual(self.step(False, collection_utc="2026-01-01T00:02:00+00:00"), "missing")

    def test_scope_and_query_isolation(self):
        self.step()
        with self.assertRaises(ValueError):
            store.record(self.ev(query="arbitrary"))
        run = store.record(self.ev(scope="entra", query=authorize("entra").query, edges=[]))
        with closing(store.database(True)) as db:
            self.assertFalse(db.execute("SELECT * FROM changes WHERE run=?", (run,)).fetchall())

    def test_dashboard_escapes_local_evidence(self):
        n = store.record(self.ev(issues=["<script>synthetic</script>"]))
        page = dashboard.page(n)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>", page)


class Policy(unittest.TestCase):
    def test_unlisted_requests_denied_before_network(self):
        with patch.object(graph, "_signed") as client:
            for invalid in ("file_upload", "arbitrary Cypher", {}, None):
                with self.assertRaises(PermissionError):
                    graph.snapshot(invalid)
            client.assert_not_called()

    def test_wrong_role_or_identity_refused(self):
        for name, roles in [("admin", ["Administrator"]), ("purple-sample-reader", ["Read-Only", "User"]),
                            ("unknown", ["Read-Only"])]:
            with patch.object(graph, "_signed", return_value={"data": {
                    "principal_name": name, "roles": [{"name": r} for r in roles]}}):
                with self.assertRaises(PermissionError):
                    graph.verify_reader()
