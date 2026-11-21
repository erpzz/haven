import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from apm import store
from apm.offline import vault
from apm.offline.demo import FIXTURES, fixture, seed
from apm.offline.formats import PARSERS, parse
from apm.offline.vault import bounded, confidence, correlate, ingest, report


class OfflineEvidence(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(store, "ROOT", root))
        self.enterContext(patch.object(vault, "ROOT", root))
        self.run_id, self.fp = seed()
        self.history = root / "history.sqlite3"
        self.original = self.history.read_bytes()

    def tearDown(self):
        self.assertEqual(self.history.read_bytes(), self.original)

    def submit(self, fmt, doc=None, **receipt):
        raw = (
            bounded(FIXTURES / (fmt + ".json"))
            if doc is None
            else json.dumps(doc).encode()
        )
        m = dict(fixture(fmt + ".receipt"), **receipt)
        m["sha256"] = hashlib.sha256(raw).hexdigest()
        aid, status = ingest(raw, m)
        correlate(self.run_id, self.fp, aid)
        return aid, status

    def view(self):
        return report(self.run_id, self.fp, "2026-11-21T20:00:00Z")

    def test_formats_and_immutable_replay(self):
        for fmt in PARSERS:
            aid, status = self.submit(fmt)
            self.assertEqual(status, "accepted")
            self.assertEqual(
                self.submit(fmt, received_utc="2026-11-21T19:05:00Z"), (aid, "replayed")
            )
        view = self.view()
        self.assertEqual(len(view["collection_quality"]), 4)
        self.assertEqual(
            {
                x["assignment_mode"]
                for x in view["identity_tier_evidence"]
                if "assignment_mode" in x
            },
            {"eligible"},
        )
        self.assertEqual({x["result"] for x in view["posture_evidence"]}, {"Failed"})
        self.assertEqual(view["path_context"]["assessment"], "historical_only")

    def test_conflict_and_relabel(self):
        fmt = "entraops_eam"
        self.submit(fmt)
        with self.assertRaises(ValueError):
            self.submit(fmt, run="other")
        doc = fixture(fmt)
        doc[0]["ObjectAdminTierLevel"] = 2
        with self.assertRaises(ValueError):
            self.submit(fmt, doc)
        with closing(vault.connect(True)) as db:
            self.assertEqual(
                db.execute("select count(*) from artifacts").fetchone()[0], 1
            )
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("delete from artifacts")

    def test_wrong_dataset_and_tenant(self):
        self.submit("maester_2x", dataset="other")
        self.assertFalse(self.view()["posture_evidence"])
        with closing(vault.connect(True)) as db:
            self.assertEqual(
                {r[0] for r in db.execute("select outcome from links")},
                {"cross_dataset_rejected"},
            )
        for fmt in ("maester_3_preview", "entraops_opengraph"):
            with self.assertRaises(ValueError):
                self.submit(fmt, tenant="00000000-0000-4000-8000-000000000099")

    def test_bad_pim_and_missing_identifier(self):
        for value in ("unknown-enum", "Active"):
            doc = fixture("entraops_opengraph")
            doc["graph"]["edges"][0]["properties"]["pimassignmenttype"] = value
            with self.assertRaises(ValueError):
                self.submit("entraops_opengraph", doc)
        doc = fixture("entraops_eam")
        doc[0]["ObjectId"] = ""
        with self.assertRaises(ValueError):
            self.submit("entraops_eam", doc)

    def test_ambiguous_or_derived_refs(self):
        doc = fixture("maester_2x")
        obj = doc["AffectedObjects"][0]
        doc["AffectedObjects"].append(dict(obj, UniqueId="different-derived-key"))
        with self.assertRaises(ValueError):
            self.submit("maester_2x", doc)
        doc["AffectedObjects"] = [dict(obj, UniqueId=obj["Id"], Id=None)]
        self.submit("maester_2x", doc)
        self.assertFalse(self.view()["posture_evidence"])

    def test_stale_partial_warning(self):
        fmt = "maester_2x"
        self.submit(fmt, partitions=[])
        self.assertEqual(self.view()["posture_evidence"][0]["confidence"], "limited")
        self.assertEqual(
            confidence(
                True,
                ["tests"],
                ["tests"],
                [],
                "2026-01-01T00:00:00Z",
                "2026-03-01T00:00:00Z",
            ),
            "limited",
        )

    def test_invalid_files_and_rollback(self):
        fmt = "maester_3_preview"
        doc = fixture(fmt)
        for field, value in [
            ("SchemaVersion", "9"),
            ("ExecutedAt", "yesterday"),
            ("Tests", [{}, {}]),
        ]:
            with self.assertRaises((ValueError, KeyError)):
                self.submit(fmt, dict(doc, **{field: value}))
        for raw in (b"{", b'{"a":1,"a":2}', b'{"n":NaN}'):
            with self.assertRaises(ValueError):
                parse(raw)
        self.assertFalse((store.ROOT / "enrichment-v1.sqlite3").exists())

    def test_redacted_ids_and_kind_mismatch(self):
        self.submit("maester_2x", identity_basis="redacted")
        self.assertFalse(self.view()["posture_evidence"])
        doc = fixture("maester_3_preview")
        doc["AffectedObjects"][0]["Type"] = "User"
        self.submit("maester_3_preview", doc)
        self.assertIn("incompatible_kind", {r["outcome"] for r in self.view()["joins"]})

    def test_positive_active_and_preview_inapplicability(self):
        doc = fixture("entraops_eam")
        doc[0]["RoleAssignments"][0]["PIMAssignmentType"] = "Active"
        self.submit("entraops_eam", doc)
        claims = self.view()["identity_tier_evidence"]
        self.assertTrue(
            any(
                r.get("assignment_mode") == "active" and r["scope"] == "/"
                for r in claims
            )
        )
        doc = fixture("maester_3_preview")
        doc["Tests"][0].update(Result="Skipped", ReasonCode="NotApplicable")
        self.submit("maester_3_preview", doc)
        self.assertEqual(
            self.view()["posture_evidence"][0]["applicability"], "not_applicable"
        )

    def test_empty_export_keeps_receipt_and_unknown_coverage(self):
        self.submit("entraops_eam", [])
        view = self.view()
        self.assertEqual(view["source_coverage"]["identity_tier_evidence"], "unknown")
        self.assertEqual(len(view["collection_quality"]), 1)

    def test_dangling_and_incompatible_role_endpoints(self):
        doc = fixture("entraops_opengraph")
        edge = doc["graph"]["edges"][0]
        edge["end"]["value"] = edge["start"]["value"]
        with self.assertRaisesRegex(ValueError, "endpoint kind"):
            self.submit("entraops_opengraph", doc)
        edge["end"]["value"] = "unresolved-target"
        self.submit("entraops_opengraph", doc)
        self.assertFalse(
            any("assignment_mode" in r for r in self.view()["identity_tier_evidence"])
        )

    def test_mixed_aggregate_requires_test_local_attribution(self):
        doc = fixture("maester_2x")
        obj = doc["AffectedObjects"][0]
        obj["Sources"].append("Markdown")
        self.submit("maester_2x", doc)
        self.assertFalse(self.view()["posture_evidence"])
        ref = {k: obj[k] for k in ("System", "Type", "Id", "AnchorKind")}
        doc["Tests"][0]["ResultDetail"]["RelatedObjects"] = [
            dict(ref, Source="GraphObjects")
        ]
        self.submit("maester_2x", doc, run="with-related")
        self.assertEqual(len(self.view()["posture_evidence"]), 1)
        del doc["AffectedObjects"]
        self.submit("maester_2x", doc, run="only-related")
        self.assertEqual(
            {r["reference"] for r in self.view()["posture_evidence"]},
            {"RelatedObjects", "AffectedObjects"},
        )

    def test_review_before_first_import_is_read_only(self):
        view = self.view()
        self.assertEqual(set(view["source_coverage"].values()), {"unknown"})
        self.assertFalse(view["collection_quality"])
        self.assertFalse((store.ROOT / "enrichment-v1.sqlite3").exists())
