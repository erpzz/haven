"""Create a disposable synthetic source and acquire before/after evidence. No CE writes."""
import json
import sqlite3
import tempfile
from collections import Counter
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from apm.local import now
from apm.path_history import get_run, record_paths
from apm.synthetic_collector import acquire


def init(db):
    db.executescript("""
        CREATE TABLE synthetic_directory(dataset_id PRIMARY KEY);
        CREATE TABLE groups(id PRIMARY KEY);
        CREATE TABLE memberships(src,kind,dst,PRIMARY KEY(src,kind,dst));
        CREATE TABLE deletion_journal(event_id PRIMARY KEY,src,kind,dst,occurred);
        CREATE TABLE pending_audit AS SELECT * FROM deletion_journal WHERE 0;
        INSERT INTO groups VALUES ('A'),('B'),('C'),('COUNCIL');
        INSERT INTO memberships VALUES ('USER','MemberOf','A'),('A','MemberOf','B'),
          ('B','MemberOf','C'),('C','MemberOf','COUNCIL'),('DECOY','Owns','B'),
          ('COUNCIL','MemberOf','BACKWARDS');
        """)
    dataset = str(uuid4())
    db.execute("INSERT INTO synthetic_directory VALUES (?)", (dataset,))
    db.commit()
    return dataset


def demo():
    with tempfile.TemporaryDirectory() as tmp:
        file = Path(tmp) / "fixture.sqlite"
        with closing(sqlite3.connect(file)) as db:
            dataset = init(db)
            for step in ("baseline", "repeat", "replacement", "unavailable", "journal", "revoked"):
                if step == "replacement":
                    db.execute("DELETE FROM memberships WHERE src='A'")
                    db.execute("INSERT INTO memberships VALUES ('A','MemberOf','C')")
                    db.execute("INSERT INTO pending_audit VALUES ('audit-1','A','MemberOf','B',?)", (now(),))
                if step == "unavailable":
                    db.execute("ALTER TABLE deletion_journal RENAME TO delayed_journal")
                if step == "journal":
                    db.execute("ALTER TABLE delayed_journal RENAME TO deletion_journal")
                    db.execute("INSERT INTO deletion_journal SELECT * FROM pending_audit")
                if step == "revoked":
                    db.execute("DELETE FROM memberships WHERE src='C' AND dst='COUNCIL'")
                    db.execute("INSERT INTO deletion_journal VALUES ('audit-2','C','MemberOf','COUNCIL',?)", (now(),))
                db.commit()
                run = record_paths(acquire(file, dataset))
                _, rows = get_run(run)
                print(json.dumps(dict(step=step, run=run, states=Counter(r["state"] for r in rows.values()))))


if __name__ == "__main__":
    demo()
