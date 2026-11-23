"""Private enrichment database. Graph reads go through Phase 2's read-only connection."""

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import timedelta
from pathlib import Path

from .timeline import observation_groups
from ..path_history import get_run, confidence as graph_confidence
from ..paths import digest
from ..samples import FILES, ROOT
from .formats import LIMIT, PARSERS, array, guid, parse, require, text, utc, KINDS

SAMPLE_DATASET = "specterops-entra-sample"
SAMPLE_TENANT = "6c12b0b0-b2cc-4a73-8252-0b94bfca2145"
SECTIONS = (
    "path_context",
    "identity_tier_evidence",
    "posture_evidence",
    "collection_quality",
)
DDL = """
CREATE TABLE IF NOT EXISTS artifacts(
 id TEXT PRIMARY KEY, source TEXT NOT NULL, dataset TEXT NOT NULL, tenant TEXT NOT NULL,
 run TEXT NOT NULL, sha TEXT NOT NULL, manifest TEXT NOT NULL, raw BLOB NOT NULL,
 UNIQUE(source,dataset,run), UNIQUE(source,dataset,sha));
CREATE TABLE IF NOT EXISTS records(
 artifact TEXT REFERENCES artifacts, seq INTEGER, category TEXT NOT NULL, kind TEXT, native TEXT, data TEXT NOT NULL,
 PRIMARY KEY(artifact,seq));
CREATE TABLE IF NOT EXISTS correlated_artifacts(
 path_run INTEGER NOT NULL, snapshot TEXT NOT NULL, finding TEXT NOT NULL, artifact TEXT REFERENCES artifacts,
 PRIMARY KEY(path_run,snapshot,finding,artifact));
CREATE TABLE IF NOT EXISTS links(
 path_run INTEGER NOT NULL, snapshot TEXT, finding TEXT, artifact TEXT, seq INTEGER, outcome TEXT NOT NULL,
 PRIMARY KEY(path_run,snapshot,finding,artifact,seq), FOREIGN KEY(artifact,seq) REFERENCES records);
"""


def bounded(file):
    with Path(file).open("rb") as f:
        data = f.read(LIMIT + 1)
    require(len(data) <= LIMIT, "Oversized artifact")
    return data


def connect(readonly=False):
    path = ROOT / "enrichment-v1.sqlite3"
    require(
        not path.is_symlink() and (not path.exists() or path.stat().st_nlink == 1),
        "Expected independent enrichment file",
    )
    if not readonly:
        ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.touch(mode=0o600, exist_ok=True)
    if readonly and not path.exists():
        # A first review can show unknown enrichment without creating state on disk.
        db = sqlite3.connect(":memory:")
        db.executescript(DDL)
        db.execute("PRAGMA query_only=ON")
    else:
        db = sqlite3.connect(
            path.as_uri() + ("?mode=ro" if readonly else "?mode=rw"),
            uri=True,
            timeout=10,
        )
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    if not readonly:
        db.executescript(DDL)
    return db


def confidence(complete, partitions, required, warnings, collected, observed):
    age = utc(observed) - utc(collected)
    ok = (
        complete is True
        and set(required) <= set(partitions)
        and not warnings
        and timedelta(0) <= age <= timedelta(days=1)
    )
    return "verified" if ok else "limited"


def ingest(raw, m):
    sha = hashlib.sha256(raw).hexdigest()
    require(
        len(raw) <= LIMIT and sha == m["sha256"], "Digest mismatch or oversized input"
    )
    fmt = m["format"]
    require(fmt in PARSERS, "Unsupported adapter format")
    source, pin, parser = PARSERS[fmt]
    require(
        m["producer_revision"] == pin and m["contract"] == "purple-apm-evidence/v1",
        "Unrecognized receipt version",
    )
    require(
        m["origin"] in ("offline-fixture", "offline-export")
        and m["identity_basis"] in ("native", "redacted", "unknown"),
        "Missing origin or identity assurance",
    )
    dataset, tenant, run = text(m["dataset"]), guid(m["tenant"]), text(m["run"])
    utc(m["collected_utc"])
    require(
        utc(m["received_utc"]) >= utc(m["collected_utc"]), "Receipt predates collection"
    )
    require(type(m["complete"]) is bool, "Invalid completeness")
    for key in ("partitions", "warnings"):
        for entry in array(m[key]):
            text(entry)
    if dataset == SAMPLE_DATASET:
        require(tenant == SAMPLE_TENANT, "Dataset and tenant binding disagree")
    try:
        rows = parser(parse(raw), m)
    except (KeyError, AttributeError, TypeError) as exc:
        raise ValueError(f"Malformed {fmt} export") from exc
    aid = digest([source, dataset, tenant, run, sha])
    with closing(connect()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT * FROM artifacts WHERE source=? AND dataset=? AND run=?",
            (source, dataset, run),
        ).fetchone()
        if existing:
            old = json.loads(existing["manifest"])
            require(
                existing["sha"] == sha
                and dict(old, received_utc=m["received_utc"]) == m,
                "Conflicting source run",
            )
            return existing["id"], "replayed"
        require(
            not db.execute(
                "SELECT 1 FROM artifacts WHERE source=? AND dataset=? AND sha=?",
                (source, dataset, sha),
            ).fetchone(),
            "Duplicate content relabeled as another run",
        )
        db.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
            (aid, source, dataset, tenant, run, sha, json.dumps(m), raw),
        )
        db.executemany(
            "INSERT INTO records VALUES (?,?,?,?,?,?)",
            [
                (
                    aid,
                    i,
                    r["category"],
                    r["kind"],
                    r["native_id"],
                    json.dumps(r["data"]),
                )
                for i, r in enumerate(rows)
            ],
        )
    return aid, "accepted"


def identity_join(dataset, tenant, kind, native, candidates):
    if not native:
        return "unmatched"
    same_id = [r for r in candidates if r[3].casefold() == native.casefold()]
    local = [r for r in same_id if r[:2] == (dataset, tenant)]
    if same_id and not local:
        return "cross_dataset_rejected"
    exact = [r for r in local if r[2] == kind and kind]
    if len(exact) > 1:
        return "ambiguous"
    if exact:
        return "exact"
    return "incompatible_kind" if local else "unmatched"


def historical(run, fingerprint):
    e, findings = get_run(run)
    require(
        e["origin"] == "ce-sample"
        and e.get("archive") == FILES["entra_sampledata.zip"]
        and e["asset"]["platform"] == "entra",
        "Unknown graph namespace",
    )
    path = findings[fingerprint]["path"]
    require(
        digest(path) == fingerprint and path in e["paths"] and not e.get("unavailable"),
        "No observed path",
    )
    ids = {value for s, _, t in path for value in (s, t)}
    candidates = [
        (SAMPLE_DATASET, SAMPLE_TENANT, KINDS.get(n["kind"]), n["objectId"])
        for n in e["graph"]["nodes"].values()
        if n["objectId"] in ids
    ]
    return e, path, candidates


def correlate(run, fingerprint, artifact):
    e, _, candidates = historical(run, fingerprint)
    snapshot = digest(e)
    with closing(connect()) as db, db:
        a = db.execute("SELECT * FROM artifacts WHERE id=?", (artifact,)).fetchone()
        require(a, "Unknown artifact")
        db.execute(
            "INSERT OR IGNORE INTO correlated_artifacts VALUES (?,?,?,?)",
            (run, snapshot, fingerprint, artifact),
        )
        manifest = json.loads(a["manifest"])
        for r in db.execute("SELECT * FROM records WHERE artifact=?", (artifact,)):
            data = json.loads(r["data"])
            outcome = identity_join(
                a["dataset"], a["tenant"], r["kind"], r["native"], candidates
            )
            if (a["dataset"], a["tenant"]) != (SAMPLE_DATASET, SAMPLE_TENANT):
                outcome = "cross_dataset_rejected"
            elif manifest["identity_basis"] != "native" and r["native"]:
                outcome = "unmatched"
            elif r["category"] == "check" and data["scope"] == "tenant":
                outcome = "tenant_context"
            db.execute(
                "INSERT OR IGNORE INTO links VALUES (?,?,?,?,?,?)",
                (run, snapshot, fingerprint, artifact, r["seq"], outcome),
            )


def report(run, fingerprint, as_of):
    utc(as_of)
    e, path, _ = historical(run, fingerprint)
    require(
        utc(e["observed"]) <= utc(as_of),
        "Graph observation unavailable at report clock",
    )
    snapshot = digest(e)
    result = {s: [] for s in SECTIONS}
    result["path_context"] = dict(
        snapshot=snapshot,
        run=run,
        fingerprint=fingerprint,
        path=path,
        observed=e["observed"],
        assessment="historical_only",
        issues=e["issues"],
        impact_tier=e["asset"]["sensitivity"],
        confidence=graph_confidence(e),
        receipt=e["receipt"],
    )
    result["joins"] = []
    with closing(connect(True)) as db:
        db.execute("BEGIN")
        confidence_by_id = {}
        for r in db.execute(
            """SELECT a.* FROM correlated_artifacts c JOIN artifacts a ON a.id=c.artifact
            WHERE c.path_run=? AND c.snapshot=? AND c.finding=? ORDER BY a.id""",
            (run, snapshot, fingerprint),
        ):
            m = json.loads(r["manifest"])
            if utc(m["received_utc"]) > utc(as_of):
                continue
            required = "tests" if r["source"] == "maester" else "role-assignments"
            c = confidence(
                m["complete"],
                m["partitions"],
                [required],
                m["warnings"],
                m["collected_utc"],
                as_of,
            )
            receipt = dict(
                artifact=r["id"],
                source=r["source"],
                dataset=r["dataset"],
                tenant=r["tenant"],
                identity_basis=m["identity_basis"],
                run=r["run"],
                collected=m["collected_utc"],
                confidence="limited" if c == "limited" else "qualified_by_receipt",
                integrity="sha256_matched_at_import",
                coverage="complete"
                if m["complete"] and required in m["partitions"] and not m["warnings"]
                else "incomplete",
                freshness="fresh"
                if utc(as_of) - utc(m["collected_utc"]) <= timedelta(days=1)
                else "stale",
                producer_authentication="unverified",
                sha256=r["sha"],
                format=m["format"],
                producer_revision=m["producer_revision"],
                origin=m["origin"],
                parser="purple-apm-offline/v1",
                received=m["received_utc"],
                complete=m["complete"],
                partitions=m["partitions"],
                warnings=m["warnings"],
            )
            result["collection_quality"].append(receipt)
            confidence_by_id[r["id"]] = receipt["confidence"]
        for r in db.execute(
            """SELECT a.*, r.seq,r.data,r.category,r.kind,r.native,l.outcome FROM links l
            JOIN artifacts a ON a.id=l.artifact JOIN records r ON r.artifact=l.artifact AND r.seq=l.seq
            WHERE l.path_run=? AND l.snapshot=? AND l.finding=?
            ORDER BY a.id,r.seq""",
            (run, snapshot, fingerprint),
        ):
            if r["id"] not in confidence_by_id:
                continue
            result["joins"].append(
                dict(
                    artifact=r["id"],
                    record=r["seq"],
                    outcome=r["outcome"],
                    category=r["category"],
                    native_id=r["native"],
                    native_kind=r["kind"],
                    referenced_target=json.loads(r["data"]).get("target"),
                )
            )
            if r["outcome"] not in ("exact", "tenant_context"):
                continue
            c = confidence_by_id[r["id"]]
            if r["category"] in ("affected", "check", "principal", "privilege"):
                section = (
                    "posture_evidence"
                    if r["source"] == "maester"
                    else "identity_tier_evidence"
                )
                result[section].append(
                    dict(
                        artifact=r["id"],
                        record=r["seq"],
                        native_id=r["native"],
                        native_kind=r["kind"],
                        dataset=r["dataset"],
                        tenant=r["tenant"],
                        provider="entra",
                        join=r["outcome"],
                        confidence=c,
                        **json.loads(r["data"]),
                    )
                )
    result["confidence_as_of"] = as_of
    result["source_coverage"] = {
        section: "linked" if result[section] else "unknown"
        for section in ("identity_tier_evidence", "posture_evidence")
    }
    receipts = {r["artifact"]: r for r in result["collection_quality"]}
    entitlements = observation_groups(
        result["identity_tier_evidence"], receipts, posture=False
    )
    checks = observation_groups(result["posture_evidence"], receipts, posture=True)
    result["latest_observations_as_of"] = dict(
        entitlements=entitlements, posture=checks
    )
    if any(g["conflict"] for g in entitlements + checks):
        action = "Reconcile contradictory observations with their source owners."
    elif any("eligible" in g["values"] for g in entitlements):
        action = "Review the eligible assignment's scope and check for separately recorded activation."
    elif entitlements:
        action = "Verify the latest reported assignment and its scope with the identity owner."
    else:
        action = "Obtain a scoped privilege export and verify the assignment identity."
    result["recommendation"] = (
        action + " Verify current membership before acting on this historical path."
    )
    return result
