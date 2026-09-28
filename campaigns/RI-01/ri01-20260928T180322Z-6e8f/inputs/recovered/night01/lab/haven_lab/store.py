"""Separate synthetic ledger. No M0 tables, database path or migrations."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from .types import Denied, Unavailable, USERS, PURPOSE, canonical, digest, parse_time

SCHEMA_VERSION = 1
APPLICATION_ID = 1213090865
LAB_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = LAB_ROOT / "runtime"

SCHEMA = """
BEGIN IMMEDIATE;
CREATE TABLE records(evidence_id TEXT PRIMARY KEY, owner TEXT NOT NULL,
                     topic TEXT NOT NULL, document TEXT NOT NULL);
CREATE TABLE grants(evidence_id TEXT NOT NULL REFERENCES records(evidence_id),
    recipient TEXT NOT NULL, purpose TEXT NOT NULL, active INTEGER NOT NULL CHECK(active IN (0,1)),
    revision INTEGER NOT NULL CHECK(revision>0), expires_at TEXT NOT NULL,
    PRIMARY KEY(evidence_id,recipient,purpose));
CREATE TABLE requests(actor TEXT NOT NULL, request_id TEXT NOT NULL, payload_hash TEXT NOT NULL,
    request_json TEXT NOT NULL, context_json TEXT NOT NULL, created_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('RUNNING','ANSWER_READY','PROPOSAL_READY','REJECTED','UNAVAILABLE')),
    reason TEXT NOT NULL, result_json TEXT, completed_at TEXT,
    PRIMARY KEY(actor,request_id));
CREATE TABLE attempts(actor TEXT NOT NULL, request_id TEXT NOT NULL,
    attempt INTEGER NOT NULL CHECK(attempt BETWEEN 1 AND 2), started_at TEXT NOT NULL,
    ended_at TEXT, state TEXT NOT NULL, output_json TEXT,
    PRIMARY KEY(actor,request_id,attempt),
    FOREIGN KEY(actor,request_id) REFERENCES requests(actor,request_id));
CREATE TABLE grant_events(sequence INTEGER PRIMARY KEY, evidence_id TEXT NOT NULL,
    recipient TEXT NOT NULL, revision INTEGER NOT NULL, active INTEGER NOT NULL, at TEXT NOT NULL);
PRAGMA user_version=1;
PRAGMA application_id=1213090865;
COMMIT;
"""

def access_revision(c, actor, evidence_id, timestamp):
    row = c.execute("SELECT owner FROM records WHERE evidence_id=?",(evidence_id,)).fetchone()
    if not row:
        return None
    if row[0] == actor:
        return 0
    grant = c.execute("SELECT active,revision,expires_at FROM grants WHERE evidence_id=? AND recipient=? AND purpose=?",
                      (evidence_id,actor,PURPOSE)).fetchone()
    if grant and grant[0] == 1 and parse_time(grant[2]) > parse_time(timestamp):
        return grant[1]
    return None

def permitted(c, actor, evidence_id, timestamp):
    return access_revision(c, actor, evidence_id, timestamp) is not None

def context_still_permitted(c, context, timestamp):
    for record in context["records"]:
        eid = record["evidence_id"]
        revision = access_revision(c, context["principal_id"], eid, timestamp)
        if revision is None or revision != context["access_revisions"][eid]:
            return False
        row = c.execute("SELECT document FROM records WHERE evidence_id=?",(eid,)).fetchone()
        if not row or digest(json.loads(row[0])) != digest(record):
            return False
    return True

def validate_fixture(fixture):
    import re
    from . import LABEL
    categories={"CURRENT_STATE":"OBSERVED_FACT", "HISTORICAL_FACT":"OBSERVED_FACT",
                "USER_STATEMENT":"USER_STATEMENT", "MODEL_INTERPRETATION":"MODEL_INFERENCE"}
    if type(fixture) is not dict or set(fixture) != {"fixture_version","label","records","grants"}:
        raise Denied("FIXTURE_FIELDS")
    if type(fixture["fixture_version"]) is not int or fixture["fixture_version"] != 1:
        raise Denied("FIXTURE_VERSION")
    if fixture["label"] != LABEL or type(fixture["records"]) is not list or not 1 <= len(fixture["records"]) <= 64:
        raise Denied("FIXTURE_LABEL_OR_SIZE")
    if type(fixture["grants"]) is not list or len(fixture["grants"]) > 64:
        raise Denied("FIXTURE_GRANTS")
    ids = set()
    owners = {}
    fields = {"schema_version","topic","origin","synthetic","version","captured_at","received_at",
              "qualified_for_physical_action","evidence_id","owner","category","claim_class","text"}
    for record in fixture["records"]:
        if type(record) is not dict or set(record) != fields:
            raise Denied("FIXTURE_FIELDS")
        if type(record["owner"]) is not str or record["owner"] not in USERS:
            raise Denied("FIXTURE_OWNER")
        if type(record["schema_version"]) is not int or record["schema_version"] != 1:
            raise Denied("FIXTURE_RECORD_VERSION")
        if type(record["version"]) is not int or not 1 <= record["version"] <= 1000:
            raise Denied("FIXTURE_REVISION")
        if type(record["category"]) is not str or record["category"] not in categories or record["claim_class"] != categories[record["category"]]:
            raise Denied("FIXTURE_CLAIM_CLASS")
        for key in ("evidence_id","topic"):
            if type(record[key]) is not str or re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,63}",record[key]) is None:
                raise Denied("FIXTURE_IDENTIFIER")
        if record["synthetic"] is not True or record["origin"] != "SIMULATED" or record["qualified_for_physical_action"] is not False:
            raise Denied("FIXTURE_NOT_SYNTHETIC")
        if type(record["text"]) is not str or not 1 <= len(record["text"]) <= 2000:
            raise Denied("FIXTURE_TEXT")
        if record["evidence_id"] in ids:
            raise Denied("DUPLICATE_EVIDENCE")
        ids.add(record["evidence_id"])
        owners[record["evidence_id"]]=record["owner"]
        try:
            if parse_time(record["captured_at"]) > parse_time(record["received_at"]):
                raise ValueError()
        except (ValueError,TypeError):
            raise Denied("FIXTURE_TIME") from None
    grant_ids=set()
    for grant in fixture["grants"]:
        if type(grant) is not dict or set(grant) != {"evidence_id","recipient","purpose","active","revision","expires_at"}:
            raise Denied("GRANT_FIELDS")
        if type(grant["evidence_id"]) is not str or grant["evidence_id"] not in ids or type(grant["recipient"]) is not str or grant["recipient"] not in USERS or grant["purpose"] != PURPOSE:
            raise Denied("GRANT_SCOPE")
        key=(grant["evidence_id"],grant["recipient"],grant["purpose"])
        if key in grant_ids or owners[grant["evidence_id"]]==grant["recipient"]:
            raise Denied("DUPLICATE_OR_SELF_GRANT")
        grant_ids.add(key)
        if type(grant["active"]) is not bool or type(grant["revision"]) is not int or grant["revision"] < 1:
            raise Denied("GRANT_STATE")
        try:
            parse_time(grant["expires_at"])
        except (ValueError,TypeError):
            raise Denied("GRANT_TIME") from None

class Ledger:
    def __init__(self, run_dir):
        p = Path(run_dir)
        root = RUNTIME_ROOT.resolve()
        if RUNTIME_ROOT.is_symlink() or p.is_symlink() or p.resolve().parent != root:
            raise Denied("LAB_RUN_PATH_ONLY")
        self.run_dir = p.resolve()
        self.path = self.run_dir / "ledger.sqlite3"
        marker = self.run_dir / "RUN.json"
        if marker.is_symlink() or self.path.is_symlink() or not marker.is_file() or not self.path.is_file():
            raise Denied("LAB_MARKER_REQUIRED")
        try:
            meta = json.loads(marker.read_text())
        except (ValueError, OSError):
            raise Denied("LAB_MARKER_INVALID") from None
        if meta != {"run_id":self.run_dir.name,"application":"HAVEN_NIGHT01_SYNTHETIC","schema_version":1}:
            raise Denied("LAB_MARKER_INVALID")

    @classmethod
    def create(cls, fixture=None):
        fixture = fixture if fixture is not None else json.loads((LAB_ROOT/"fixtures/context.json").read_text())
        validate_fixture(fixture)
        if RUNTIME_ROOT.is_symlink():
            raise Denied("LAB_RUN_PATH_ONLY")
        RUNTIME_ROOT.mkdir(exist_ok=True, mode=0o700)
        run_dir = RUNTIME_ROOT / ("run-"+str(uuid4()))
        run_dir.mkdir(mode=0o700)
        c = sqlite3.connect(run_dir/"ledger.sqlite3", isolation_level=None)
        try:
            c.execute("PRAGMA journal_mode=DELETE")
            c.execute("PRAGMA synchronous=FULL")
            c.execute("PRAGMA foreign_keys=ON")
            c.execute("PRAGMA busy_timeout=500")
            expected={"journal_mode":"delete", "synchronous":2, "foreign_keys":1, "busy_timeout":500}
            if c.in_transaction or any(c.execute("PRAGMA "+key).fetchone()[0]!=value for key,value in expected.items()):
                raise Unavailable("INITIAL_LEDGER_SETTINGS")
            c.executescript(SCHEMA)
            c.execute("BEGIN IMMEDIATE")
            for row in fixture["records"]:
                c.execute("INSERT INTO records VALUES(?,?,?,?)",(row["evidence_id"],row["owner"],row["topic"],canonical(row)))
            for row in fixture["grants"]:
                c.execute("INSERT INTO grants VALUES(?,?,?,?,?,?)",tuple(row[k] for k in
                    ("evidence_id","recipient","purpose","active","revision","expires_at")))
            c.commit()
        finally:
            c.close()
        (run_dir/"RUN.json").write_text(canonical({"run_id":run_dir.name,"application":"HAVEN_NIGHT01_SYNTHETIC","schema_version":1}))
        return cls(run_dir)

    @contextmanager
    def connect(self, write=False):
        # Validate path/marker again before each open; missing DB cannot create an empty ledger.
        Ledger(self.run_dir)
        c = None
        try:
            c = sqlite3.connect(self.path.as_uri()+("?mode=rw" if write else "?mode=ro"),uri=True,isolation_level=None,timeout=0.5)
            c.row_factory = sqlite3.Row
            if c.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID or c.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
                raise Unavailable("UNSUPPORTED_LEDGER_VERSION")
            c.execute("PRAGMA busy_timeout=500")
            c.execute("PRAGMA foreign_keys=ON")
            if write:
                c.execute("PRAGMA journal_mode=DELETE")
                c.execute("PRAGMA synchronous=FULL")
            else:
                c.execute("PRAGMA synchronous=FULL")
                c.execute("PRAGMA query_only=ON")
            if c.execute("PRAGMA journal_mode").fetchone()[0] != "delete" or c.execute("PRAGMA synchronous").fetchone()[0] != 2 or c.execute("PRAGMA foreign_keys").fetchone()[0] != 1 or c.execute("PRAGMA busy_timeout").fetchone()[0] != 500 or c.in_transaction:
                raise Unavailable("LEDGER_SETTINGS")
            if write:
                c.execute("BEGIN IMMEDIATE")
            else:
                c.execute("BEGIN")
            yield c
            if write:
                c.commit()
            else:
                c.rollback()
        except sqlite3.Error:
            if c is not None:
                c.rollback()
            raise Unavailable("LEDGER_ERROR") from None
        finally:
            if c is not None:
                c.close()

    def revoke(self, owner, evidence_id, recipient):
        from .types import now
        owner.check()
        with self.connect(write=True) as c:
            row = c.execute("SELECT owner FROM records WHERE evidence_id=?",(evidence_id,)).fetchone()
            if row is None or row[0] != owner.actor:
                raise Denied("ONLY_FIXTURE_OWNER_CAN_REVOKE")
            old = c.execute("SELECT revision FROM grants WHERE evidence_id=? AND recipient=? AND purpose=?",
                            (evidence_id,recipient,PURPOSE)).fetchone()
            if old is None:
                raise Denied("GRANT_NOT_FOUND")
            c.execute("UPDATE grants SET active=0,revision=revision+1 WHERE evidence_id=? AND recipient=? AND purpose=?",
                      (evidence_id,recipient,PURPOSE))
            c.execute("INSERT INTO grant_events(evidence_id,recipient,revision,active,at) VALUES(?,?,?,?,?)",
                      (evidence_id,recipient,old[0]+1,0,now()))
