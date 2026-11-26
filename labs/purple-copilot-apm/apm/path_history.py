"""Transactional path-level evidence history and deterministic priority."""
import argparse
import fcntl
import json
from contextlib import closing
from datetime import datetime, timedelta
from time import perf_counter

from .local import now
from .paths import digest, enumerate_paths, query, registry, sample_scan
from .samples import ROOT
from .store import database

SCHEMA = """CREATE TABLE IF NOT EXISTS path_runs(
 id INTEGER PRIMARY KEY, stream TEXT NOT NULL, observed TEXT NOT NULL,
 evidence TEXT NOT NULL, findings TEXT NOT NULL, UNIQUE(stream, observed));
CREATE INDEX IF NOT EXISTS path_run_stream ON path_runs(stream,id);"""


def utc(value):
    stamp = datetime.fromisoformat(value)
    if stamp.utcoffset() != timedelta(0):
        raise ValueError("Require UTC collector timestamps")
    return stamp


def confidence(e):
    r = e["receipt"]
    if (e["origin"] != "synthetic-directory" or r["collector"] != "synthetic-directory/v1"
            or not r.get("dataset") or e["issues"] or r["complete"] is not True or not r["collector"] or not r["run"]
            or not r["completed"] or not r.get("started") or r.get("partitions") != ["groups", "members", "audit"]
            or e["asset"]["target"] not in e.get("enumerated_groups", [])):
        return "limited"
    expected = enumerate_paths(e["asset"], e["inventory_edges"])
    if {digest(p) for p in expected} != {digest(p) for p in e["paths"]}:
        return "limited"
    end, observed = utc(r["completed"]), utc(e["observed"])
    if utc(r["started"]) > end or end - utc(r["started"]) > timedelta(days=1):
        return "limited"
    return "verified" if timedelta(0) <= observed - end <= timedelta(days=1) else "limited"


def priority(asset, verified):
    factors = {"sensitivity": 50 if asset["sensitivity"] == "critical" else 30,
               "privileged_group": 30 if asset["privileged"] else 0,
               "verified_collection": 20 if verified else 0}
    return {"score": sum(factors.values()), "factors": factors}


def compare(e, prior):
    # A detector may supply its own deterministic per-finding rank. A finding without a current
    # rank keeps the one from its last observation.
    ranks = e.get("rank")

    def rank(key, verified, old=None):
        if ranks is None:
            return priority(e["asset"], verified)
        return ranks.get(key) or (old or {}).get("priority") or {"score": 0, "factors": {}}

    if e.get("unavailable"):
        return {k: dict(v, observation="unavailable", priority=rank(k, False, v)) for k, v in prior.items()}
    paths = {digest(path): path for path in e["paths"]}
    verified = confidence(e) == "verified"
    findings = {}
    for key, path in paths.items():
        old = prior.get(key)
        alternatives = [k for k, item in prior.items()
                        if k not in paths and item["state"] != "removed"
                        and item["path"][0][0] == path[0][0]]
        if old and old["state"] not in ("removed", "missing"):
            state = "persistent"
        else:
            state = "changed" if alternatives else "new"
        findings[key] = dict(path=path, state=state, replaces=alternatives if state == "changed" else [],
                             last_seen=e["observed"], source_run=e["receipt"]["run"],
                             priority=rank(key, verified, old))
    for key in prior.keys() - paths.keys():
        old = prior[key]
        if old["state"] == "removed":
            findings[key] = old
            continue
        r = e["receipt"]
        proof = next((event for event in e["removals"]
                      if verified and old["source_run"] and old["source_run"] != r["run"]
                      and event["edge"] in old["path"] and event["event_id"]
                      and event["run"] == r["run"]
                      and utc(old["last_seen"]) < utc(event["time"]) <= utc(r["completed"])
                      and event["edge"] not in e["inventory_edges"]), None)
        findings[key] = dict(old, state="removed" if proof else "missing", removal=proof,
                             priority=rank(key, verified, old))
    return findings


def record_paths(e):
    # Canonicalize nested tuples and timestamps before comparison and persistence.
    e = json.loads(json.dumps(e))
    e["observed"] = utc(e["observed"]).isoformat(timespec="microseconds")
    for field in ("started", "completed"):
        if e["receipt"].get(field):
            e["receipt"][field] = utc(e["receipt"][field]).isoformat(timespec="microseconds")
    stream = digest([e["origin"], e["asset"]["platform"], e["asset"]["target"],
                     e["receipt"]["collector"], e["receipt"].get("dataset"), e["query"]])
    with closing(database()) as db, db:
        db.executescript(SCHEMA)
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("SELECT * FROM path_runs WHERE stream=? ORDER BY id DESC LIMIT 1", (stream,)).fetchone()
        encoded = json.dumps(e, sort_keys=True)
        same = db.execute("SELECT id,evidence FROM path_runs WHERE stream=? AND observed=?",
                          (stream, e["observed"])).fetchone()
        if same:
            if same["evidence"] != encoded:
                raise ValueError("Conflicting observation")
            return same["id"]
        if old and e["observed"] <= old["observed"]:
            raise ValueError("Out-of-order observation")
        r = e["receipt"]
        if r["run"]:
            previous = db.execute("""SELECT evidence FROM path_runs WHERE stream=?
                AND json_extract(evidence,'$.receipt.run')=? LIMIT 1""", (stream, r["run"])).fetchone()
            if previous:
                before = json.loads(previous[0])
                if any(before.get(k) != e.get(k) for k in ("receipt", "paths", "removals", "issues",
                                                          "inventory_edges", "enumerated_groups", "unavailable")):
                    raise ValueError("Collector run identity reused with different evidence")
            if r["completed"] and db.execute("""SELECT 1 FROM path_runs WHERE stream=?
                AND json_extract(evidence,'$.receipt.run') != ?
                AND json_extract(evidence,'$.receipt.completed') >= ? LIMIT 1""",
                                                (stream, r["run"], r["completed"])).fetchone():
                raise ValueError("Non-advancing source collection")
        findings = compare(e, json.loads(old["findings"]) if old else {})
        return db.execute("INSERT INTO path_runs(stream,observed,evidence,findings) VALUES (?,?,?,?)",
                          (stream, e["observed"], encoded, json.dumps(findings))).lastrowid


def get_run(run):
    with closing(database(True)) as db:
        row = db.execute("SELECT * FROM path_runs WHERE id=?", (run,)).fetchone()
    if not row:
        raise ValueError("Unknown path observation")
    return json.loads(row["evidence"]), json.loads(row["findings"])


def scan():
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (ROOT / "path-scan.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return scan_assets()


def scan_assets():
    healthy = True
    inventories = {}
    for asset in registry().values():
        start = perf_counter()
        try:
            e = sample_scan(asset, inventories)
        except (OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
            e = dict(asset=asset, origin="ce-sample", observed=now(), paths=[], query=query(asset), unavailable=True,
                     issues=[str(exc)], removals=[], receipt=dict(collector="official-archive",
                     run=None, completed=None, complete=False))
        run = record_paths(e)
        print(json.dumps(dict(run=run, asset=asset["key"], paths=len(e["paths"]), issues=e["issues"],
                              confidence=confidence(e), seconds=round(perf_counter()-start, 3))))
        healthy &= not e["issues"]
    return healthy


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--show", type=int, metavar="RUN")
    args = p.parse_args()
    if args.show:
        print(json.dumps(get_run(args.show), indent=2))
    else:
        raise SystemExit(0 if scan() else 2)
