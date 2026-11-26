"""Verify directed live paths against the independent, pinned group inventories."""
import json
from collections import Counter
from time import perf_counter

from apm.path_history import confidence, record_paths
from apm.paths import registry, sample_scan

EXPECTED = {"phantom-admins": {1: 8, 2: 12, 3: 1}, "resource-admins": {1: 1},
            "consent-review": {1: 4, 2: 1}}


def check():
    cache = {}
    for name, asset in registry().items():
        start = perf_counter()
        e = sample_scan(asset, cache)
        histogram = Counter(map(len, e["paths"]))
        assert histogram == EXPECTED[name]
        issues = e["issues"]
        assert (len(issues) == 1 and issues[0].startswith("Archive record count mismatch")
                if name == "phantom-admins" else not issues)
        assert confidence(e) == "limited" and e["receipt"]["run"] is None
        run = record_paths(e)
        print(json.dumps(dict(asset=name, run=run, hops=histogram, seconds=round(perf_counter()-start, 3))))


if __name__ == "__main__":
    check()
