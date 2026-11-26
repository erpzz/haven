import copy
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from apm import store
from apm.local import now
from apm.path_history import confidence, get_run, record_paths, utc
from apm.paths import digest, enumerate_paths, query, registry
from apm.synthetic_collector import ASSET, acquire
from path_scenario import init


class Paths(unittest.TestCase):
    def setUp(self):
        tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.object(store, "ROOT", Path(tmp)))
        self.file = Path(tmp) / "directory.db"
        self.db = self.enterContext(closing(sqlite3.connect(self.file)))
        self.dataset = init(self.db)

    def read(self):
        return acquire(self.file, self.dataset)

    def test_lengths_semantics_cycles_and_endpoints(self):
        e = self.read()
        self.assertEqual(sorted(map(len, e["paths"])), [1, 2, 3, 4])
        longest = max(e["paths"], key=len)
        self.assertEqual([s for s, _, _ in longest], ["USER", "A", "B", "C"])
        self.assertEqual(longest[-1][-1], "COUNCIL")
        for label, kind in (("ad", "MemberOf"), ("entra", "AZMemberOf")):
            edges = [("U", kind, "G"), ("G", kind, "T"), ("T", kind, "G"),
                     ("DECOY", "Owns", "G"), ("T", kind, "BACK")]
            paths = enumerate_paths(dict(target="T", platform=label), edges)
            self.assertEqual(sorted(map(len, paths)), [1, 2])

    def test_path_budget_fails_closed(self):
        with self.assertRaises(ValueError):
            enumerate_paths(ASSET, [(str(i), "MemberOf", "COUNCIL") for i in range(129)])

    def test_replacement_and_corroborated_removal(self):
        first = record_paths(self.read())
        _, original = get_run(first)
        self.assertEqual({r["state"] for r in original.values()}, {"new"})
        old = digest(max((r["path"] for r in original.values()), key=len))
        repeat = record_paths(self.read())
        self.assertEqual(get_run(repeat)[1][old]["state"], "persistent")
        self.db.execute("DELETE FROM memberships WHERE src='A'")
        self.db.execute("INSERT INTO memberships VALUES ('A','MemberOf','C')")
        self.db.commit()
        seen = now()
        changed = get_run(record_paths(self.read()))[1]
        self.assertEqual(changed[old]["state"], "missing")
        self.assertTrue(any(old in r["replaces"] for r in changed.values()))
        self.db.execute("INSERT INTO deletion_journal VALUES ('change-1','A','MemberOf','B',?)", (seen,))
        self.db.commit()
        result = get_run(record_paths(self.read()))[1]
        self.assertEqual(result[old]["state"], "removed")
        self.assertEqual(result[old]["removal"]["event_id"], "change-1")

    def test_failed_partial_and_wrong_source(self):
        baseline = record_paths(self.read())
        self.db.execute("DROP TABLE deletion_journal")
        gap = self.read()
        self.assertTrue(gap["unavailable"])
        self.assertEqual(confidence(gap), "limited")
        result = get_run(record_paths(gap))[1]
        self.assertEqual(set(result), set(get_run(baseline)[1]))
        self.assertTrue(all(r["observation"] == "unavailable" for r in result.values()))
        self.assertFalse(acquire(self.file, "different")["receipt"]["complete"])

    def test_stale_source_or_absent_journal_never_closes(self):
        old = self.read()
        first = record_paths(old)
        self.db.execute("DELETE FROM memberships")
        self.db.execute("INSERT INTO deletion_journal VALUES ('x','A','MemberOf','B',?)", (now(),))
        self.db.commit()
        e = self.read()
        e["observed"] = (utc(e["observed"]) + timedelta(days=2)).isoformat()
        rows = get_run(record_paths(e))[1]
        self.assertEqual({r["state"] for r in rows.values()}, {"missing"})
        self.assertGreater(next(iter(get_run(first)[1].values()))["priority"]["score"],
                           next(iter(rows.values()))["priority"]["score"])

    def test_idempotence_conflict_and_old_source_replay(self):
        e = self.read()
        self.assertEqual(record_paths(e), record_paths(e))
        conflict = copy.deepcopy(e)
        conflict["observed"] = now()
        conflict["paths"] = []
        with self.assertRaises(ValueError):
            record_paths(conflict)
        record_paths(self.read())
        with self.assertRaises(ValueError):
            record_paths(dict(e, observed=now()))

    def test_template_and_config_reject_injection(self):
        with self.assertRaises(ValueError):
            query(dict(ASSET, target="' RETURN n //"))
        file = self.file.with_suffix(".json")
        file.write_text(json.dumps([dict(ASSET, platform="custom")]))
        with patch.dict(os.environ, APM_ASSETS=str(file)), self.assertRaises(ValueError):
            registry()
