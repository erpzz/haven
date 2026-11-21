"""Read the local CE official Entra sample and correlate four generated export shapes."""

import hashlib
import json
import os

from apm.offline.demo import FIXTURES, fixture
from apm.offline.formats import PARSERS
from apm.offline.vault import bounded, correlate, ingest, report
from apm.path_history import record_paths
from apm.paths import digest, registry, sample_scan
from apm.samples import ROOT


def check():
    history = ROOT / "history.sqlite3"
    if not os.environ.get("APM_STATE") or history.exists():
        raise SystemExit(
            "Set APM_STATE to a separate sample workspace with no graph history"
        )
    snapshot = sample_scan(registry()["resource-admins"])
    assert snapshot["origin"] == "ce-sample" and len(snapshot["paths"]) == 1
    run = record_paths(snapshot)
    fp = digest(snapshot["paths"][0])
    before = hashlib.sha256(history.read_bytes()).hexdigest()
    for fmt in PARSERS:
        aid, state = ingest(
            bounded(FIXTURES / (fmt + ".json")), fixture(fmt + ".receipt")
        )
        assert state == "accepted"
        correlate(run, fp, aid)
    view = report(run, fp, "2026-11-21T20:00:00Z")
    after = hashlib.sha256(history.read_bytes()).hexdigest()
    assert before == after
    assert (
        len(view["identity_tier_evidence"]) == 4 and len(view["posture_evidence"]) == 2
    )
    assert all(
        r["join"] == "exact"
        for r in view["posture_evidence"] + view["identity_tier_evidence"]
    )
    assert fp == digest(fixture("sample-path")["paths"][0])
    print(
        json.dumps(
            dict(
                graph_source=snapshot["origin"],
                graph_observed=snapshot["observed"],
                membership_fingerprint=fp,
                source="four generated fixtures",
                privilege_rows=4,
                posture_rows=2,
                history_sha256_before=before,
                history_sha256_after=after,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    check()
