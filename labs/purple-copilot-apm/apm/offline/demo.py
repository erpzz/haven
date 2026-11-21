"""Exercise supplied fixtures in a new private APM_STATE."""

import json
import os
from pathlib import Path

from ..path_history import record_paths
from ..paths import digest
from ..samples import ROOT
from .formats import PARSERS, parse
from .vault import bounded, correlate, ingest, report

FIXTURES = Path(__file__).resolve().parents[2] / "tests/offline_fixtures"


def fixture(name):
    return parse(bounded(FIXTURES / (name + ".json")))


def seed():
    e = fixture("sample-path")
    return record_paths(e), digest(e["paths"][0])


if __name__ == "__main__":
    if not os.getenv("APM_STATE") or (ROOT.exists() and any(ROOT.iterdir())):
        raise SystemExit(
            "Set APM_STATE to an empty private directory for the demonstration"
        )
    run, path = seed()
    for fmt in PARSERS:
        aid, _ = ingest(bounded(FIXTURES / (fmt + ".json")), fixture(fmt + ".receipt"))
        correlate(run, path, aid)
    print(json.dumps(report(run, path, "2026-11-21T20:00:00Z"), indent=2))
