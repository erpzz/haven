"""Local model and CE acceptance check on the official synthetic fixtures."""
import json
import re
from contextlib import closing

from apm.analyst import analyze
from apm.graph import snapshot
from apm.store import database, record


def check():
    for name, size, words in [("ad", 12, "twelve"), ("entra", 1, "one|single")]:
        e = snapshot(name)
        assert len(e["edges"]) == size
        assert set(m[0] for m in e["edges"]) == set(e["expected_members"])
        if name == "ad":
            assert e["issues"] == ["Collector declared 113 records, archive contains 115"]
        else:
            assert not e["issues"]
        n = record(e)
        answer = analyze(n, gateway=False)
        with closing(database(True)) as db:
            receipt = db.execute("SELECT * FROM conclusions WHERE run=? ORDER BY id DESC LIMIT 1", (n,)).fetchone()
            assert receipt["classification"] == "hypothesis"
            assert json.loads(receipt["response"])["choices"][0]["message"]["content"] == answer
        print(name, n, answer, flush=True)
        assert re.search(rf"\b({size}|{words})\b", answer, re.I), "Review omitted the observed count"


if __name__ == "__main__":
    check()
