"""Acquire a consistent membership inventory and independent change journal from a synthetic directory."""
import sqlite3
from contextlib import closing
from uuid import uuid4

from .local import now
from .paths import enumerate_paths

ASSET = dict(key="lab-council", platform="ad", target="COUNCIL", sensitivity="critical", privileged=True)
STATEMENTS = {
    "groups": "SELECT id FROM groups ORDER BY id",
    "members": "SELECT src,kind,dst FROM memberships ORDER BY src,kind,dst",
    "audit": "SELECT event_id,src,kind,dst,occurred FROM deletion_journal ORDER BY occurred,event_id",
}


def acquire(path, dataset):
    started, run = now(), str(uuid4())
    e = dict(asset=ASSET, origin="synthetic-directory", observed=None, paths=[], inventory_edges=[],
             enumerated_groups=[], query=STATEMENTS, issues=[], removals=[])
    receipt = dict(collector="synthetic-directory/v1", run=run, started=started, completed=None,
                   dataset=dataset, partitions=[], complete=False)
    e["receipt"] = receipt
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            db.execute("BEGIN")
            identity = db.execute("SELECT dataset_id FROM synthetic_directory").fetchone()[0]
            if not dataset or identity != dataset:
                raise ValueError("Synthetic directory identity mismatch")
            for partition, statement in STATEMENTS.items():
                rows = db.execute(statement).fetchall()
                if partition == "groups":
                    e["enumerated_groups"] = [row[0] for row in rows]
                elif partition == "members":
                    e["inventory_edges"] = rows
                else:
                    e["removals"] = [dict(event_id=event, edge=[s, k, t], time=when, run=run)
                                     for event, s, k, t, when in rows]
                receipt["partitions"].append(partition)
            if ASSET["target"] not in e["enumerated_groups"]:
                raise ValueError("Missing target group")
            e["paths"] = enumerate_paths(ASSET, e["inventory_edges"])
            receipt["complete"] = True
    except (sqlite3.Error, ValueError, TypeError) as exc:
        e["issues"].append(str(exc))
        e["unavailable"] = True
    receipt["completed"] = now()
    e["observed"] = now()
    return e


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    from .path_history import record_paths
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("dataset")
    args = parser.parse_args()
    evidence = acquire(args.file, args.dataset)
    print(record_paths(evidence), evidence["issues"])
    raise SystemExit(2 if evidence["issues"] else 0)
