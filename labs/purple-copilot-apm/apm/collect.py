"""External scheduler entry point. Failures are evidence and yield nonzero exit."""
import fcntl
import sys

from .graph import now, snapshot
from .policy import REVIEWS
from .samples import FILES, ROOT
from .store import record


def collect():
    ROOT.mkdir(parents=True, mode=0o700, exist_ok=True)
    healthy = True
    with (ROOT / "collection.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for scope, review in REVIEWS.items():
            try:
                evidence = snapshot(scope)
            except (KeyError, IndexError, ValueError, RuntimeError, OSError, TypeError) as exc:
                evidence = dict(scope=scope, query=review.query, observed=now(), collected=None,
                                edges=[], source=FILES[review.source], unavailable=True, issues=[str(exc)])
            run = record(evidence)
            count = "unavailable" if evidence.get("unavailable") else len(evidence["edges"])
            print(scope, "snapshot", run, "observed edges", count, evidence["issues"])
            healthy &= not evidence["issues"]
    return healthy


if __name__ == "__main__":
    sys.exit(0 if collect() else 2)
