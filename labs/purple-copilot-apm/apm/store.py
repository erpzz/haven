"""Append-only evidence with one transaction per review. The model has no write API."""
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta

from .policy import authorize
from .samples import ROOT

DDL = """
CREATE TABLE IF NOT EXISTS runs (
 id INTEGER PRIMARY KEY, scope TEXT NOT NULL, observed TEXT NOT NULL, evidence TEXT NOT NULL,
 UNIQUE(scope, observed)
);
CREATE TABLE IF NOT EXISTS changes (
 run INTEGER REFERENCES runs, src TEXT, kind TEXT, dst TEXT, state TEXT NOT NULL,
 absent_source TEXT, investigation TEXT NOT NULL, PRIMARY KEY(run,src,kind,dst)
);
CREATE TABLE IF NOT EXISTS conclusions (
 id INTEGER PRIMARY KEY, run INTEGER REFERENCES runs, created TEXT, model TEXT,
 prompt TEXT, response TEXT, classification TEXT CHECK(classification='hypothesis')
);
"""


def database(readonly=False):
    ROOT.mkdir(parents=True, mode=0o700, exist_ok=True)
    path = ROOT / "history.sqlite3"
    conn = sqlite3.connect(path.as_uri() + "?mode=ro" if readonly else path, uri=readonly, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma foreign_keys=on")
    if not readonly:
        conn.executescript(DDL)
    return conn


def conclusion_writer():
    """The inference adapter may append a hypothesis to an existing observation."""
    conn = sqlite3.connect(ROOT / "history.sqlite3", timeout=15)
    conn.execute("pragma foreign_keys=on")

    def permit(action, table, column, schema, trigger):
        if action == sqlite3.SQLITE_INSERT and table == "conclusions":
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_TRANSACTION or (action == sqlite3.SQLITE_READ and table == "runs"):
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    conn.set_authorizer(permit)
    return conn


def transition(previous, present, issues, source):
    if present:
        state = "new" if not previous or previous["state"] in ("confirmed-remediated", "missing") else "persistent"
        return state, None, "open"
    if previous["state"] == "confirmed-remediated":
        return "confirmed-remediated", None, "closed"
    if issues:
        return "missing", None, "coverage required"
    prior = previous["absent_source"]
    if prior and prior != source:
        return "confirmed-remediated", None, "closed"
    return "missing", source, "awaiting corroboration"


def confirmation_issues(db, evidence):
    """A fresh, complete membership enumeration must contradict the old edge.

    Unknown time zones, replayed older inventories and stale source data cannot
    establish a removal. Same-source retries never constitute corroboration.
    """
    if evidence["issues"] or evidence.get("unavailable"):
        return True
    collected = evidence.get("collection_utc")
    if not collected or not evidence.get("source"):
        return True
    stamp = datetime.fromisoformat(collected)
    if stamp.utcoffset() != timedelta(0):
        return True
    age = datetime.fromisoformat(evidence["observed"]) - stamp
    if not timedelta(0) <= age <= timedelta(days=1):
        return True
    previous = db.execute("""
        SELECT 1 FROM runs WHERE scope=?
        AND (julianday(json_extract(evidence,'$.collection_utc')) > julianday(?)
            OR (julianday(json_extract(evidence,'$.collection_utc')) = julianday(?)
                AND json_extract(evidence,'$.source') != ?))
        LIMIT 1""", (evidence["scope"], collected, collected, evidence["source"])).fetchone()
    if previous:
        return True
    expected = evidence.get("expected_members")
    return expected is None or set(expected) != {e[0] for e in evidence["edges"]}


def record(evidence):
    scope, observed = evidence["scope"], evidence["observed"]
    review = authorize(scope)
    if evidence["query"] != review.query:
        raise ValueError("Query scope changed")
    with closing(database()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        latest = db.execute("SELECT * FROM runs WHERE scope=? ORDER BY id DESC LIMIT 1", (scope,)).fetchone()
        encoded = json.dumps(evidence, sort_keys=True)
        retry = db.execute("SELECT id,evidence FROM runs WHERE scope=? AND observed=?", (scope, observed)).fetchone()
        if retry:
            if retry["evidence"] != encoded:
                raise ValueError("Conflicting snapshot")
            return retry["id"]
        if latest and json.loads(latest["evidence"])["query"] != review.query:
            raise ValueError("Use a new catalog scope for a changed query")
        if latest and latest["observed"] >= observed:
            raise ValueError("Out-of-order observation")
        old = {}
        if latest:
            old = {(r["src"], r["kind"], r["dst"]): r for r in
                   db.execute("SELECT * FROM changes WHERE run=?", (latest["id"],))}
        blocked = confirmation_issues(db, evidence)
        run = db.execute("INSERT INTO runs(scope,observed,evidence) VALUES (?,?,?)",
                         (scope, observed, encoded)).lastrowid
        current = {tuple(edge) for edge in evidence["edges"]}
        for edge in sorted(set(old) | current):
            if evidence.get("unavailable"):
                # A failed request supplies no observation about presence or absence.
                row = old[edge]
                state = (row["state"], None, "collection unavailable")
            else:
                state = transition(old.get(edge), edge in current, blocked, evidence["source"])
            db.execute("INSERT INTO changes VALUES (?,?,?,?,?,?,?)", (run, *edge, *state))
        return run
