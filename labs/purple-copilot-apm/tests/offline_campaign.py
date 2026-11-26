"""Project the frozen *inputs* through the importer and emit only independent actuals."""

import hashlib
import json
import re
import tempfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from apm import store
from apm.offline import vault
from apm.offline.demo import fixture, seed
from apm.offline.formats import mode, opengraph, parse, unique, utc, variant
from apm.offline.vault import confidence, correlate, identity_join, ingest, report

ASOF = "2026-11-21T20:00:00Z"


def submit(fmt, doc=None, **receipt):
    raw = json.dumps(fixture(fmt) if doc is None else doc).encode()
    m = dict(
        fixture(fmt + ".receipt"), **receipt, sha256=hashlib.sha256(raw).hexdigest()
    )
    return ingest(raw, m)


def decision(op, d):
    if op == "receipt_identity":
        decisions = []
        for r in d["runs"]:
            doc = fixture("entraops_eam")
            doc[0]["Description"] = r["bytes"]
            try:
                _, state = submit(
                    "entraops_eam", doc, dataset=r["dataset_id"], run=r["run_id"]
                )
            except ValueError as err:
                if "Conflicting source run" not in str(err):
                    raise
                state = "conflict_rejected"
            decisions.append(state)
        with closing(vault.connect(True)) as db:
            return dict(
                decisions=decisions,
                distinct_artifacts=db.execute(
                    "SELECT count(*) FROM artifacts"
                ).fetchone()[0],
            )
    if op == "identity_join":
        left, right = d["left"], d["right"]

        def key(r):
            return (r["dataset_id"], r["provider"], r["native_kind"], r["native_id"])

        return {"join": identity_join(*key(left), [key(right)])}
    if op == "missing_reference":
        doc = fixture("entraops_opengraph")
        doc["graph"]["edges"][0]["start"]["value"] = d["name"]
        rows = opengraph(doc, fixture("entraops_opengraph.receipt"))
        stub = rows[-1]
        return dict(
            join=identity_join("D", "T", stub["kind"], stub["native_id"], []),
            retained_stub=stub["native_id"].casefold() == d["name"].casefold(),
        )
    if op == "assignment_mode":
        observed = sorted({mode(v.title(), None) for v in d["modes"]})
        return dict(observed=observed, active_privilege_proven="active" in observed)
    if op == "tiers":
        tiers = sorted({(a["rbac_system"], a["tier"]) for a in d["assignments"]})
        return dict(
            scoped_tiers=list(map(list, tiers)),
            collapsed=len(tiers) < len(d["assignments"]),
        )
    if op == "edge_semantics":
        doc = fixture("entraops_opengraph")
        doc["graph"]["edges"][0]["kind"] = d["edge_kind"]
        return dict(
            traversable=opengraph(doc, fixture("entraops_opengraph.receipt"))[-1][
                "data"
            ]["traversable"]
        )
    if op == "maester_shapes":
        return dict(variants=[variant(x) for x in d["exports"]])
    if op == "freshness":
        return dict(
            confidence=confidence(
                d["complete"],
                d["partitions"],
                d["required"],
                d["warnings"],
                d["collected_utc"],
                d["observed_utc"],
            )
        )
    if op == "format_validation":
        errors = []
        if d["byte_count"] > d["max_bytes"]:
            errors.append("oversized")
        for name, fn, arg in [
            ("malformed_json", parse, d["json_text"].encode()),
            ("duplicate_ids", unique, d["ids"]),
            ("bad_timestamp", utc, d["collected_utc"]),
        ]:
            try:
                fn(arg)
            except ValueError:
                errors.append(name)
        return dict(invalid=errors, accepted=not errors)
    if op == "public_redaction":
        public_text = re.sub(r"[^\s:@]+@[^\s;]+", "[REDACTED_EMAIL]", d["text"])
        return dict(public_text=public_text, raw_export_public=d["text"] in public_text)
    run, fp = seed()
    pathfile = store.ROOT / "history.sqlite3"
    before = pathfile.read_bytes()
    doc = fixture("maester_3_preview")
    t = doc["Tests"][0]
    if op == "test_lifecycle":
        for i, outcome in enumerate(d["states"]):
            t["Result"] = outcome
            aid, _ = submit("maester_3_preview", doc, run=str(i))
            correlate(run, fp, aid)
        return dict(
            resolution="unresolved"
            if before == pathfile.read_bytes()
            and outcome in {"NotRun", "Skipped", "Error", "Investigate"}
            else "requires_validation"
        )
    if op == "posture_link":
        t["ResourceType"] = d["scope"].title()
        doc["AffectedObjects"] = []
    if op == "affected_uniqueid":
        doc["AffectedObjects"][0].update(UniqueId=d["unique_id"], Id=None)
    if op == "tool_injection":
        t["Title"] = d["description"]
    if op == "missing_enrichment":
        t["Result"] = d["maester_status"]
    with (
        patch(
            "socket.socket.connect",
            side_effect=AssertionError("Unexpected network request"),
        ) as network,
        patch(
            "subprocess.Popen", side_effect=AssertionError("Unexpected tool process")
        ) as process,
    ):
        aid, state = submit("maester_3_preview", doc)
        correlate(run, fp, aid)
        view = report(run, fp, ASOF)
    external_calls = [
        name
        for name, mock in (("network", network), ("process", process))
        if mock.called
    ]
    if op == "posture_link":
        return dict(link=view["posture_evidence"][0]["join"])
    if op == "affected_uniqueid":
        return dict(
            match="verified_explicit" if view["posture_evidence"] else "unknown"
        )
    if op == "immutable_facts":
        return dict(
            finding_state_unchanged=before == pathfile.read_bytes()
            and d["before"] == d["after"]
        )
    if op == "tool_injection":
        return dict(
            exposed_tools=[k for k in view if k in vault.SECTIONS],
            executed_tools=external_calls,
            text_is_data=d["description"] not in json.dumps(view),
        )
    if op == "model_unavailable":
        return dict(
            deterministic_import="unaffected" if state == "accepted" else state,
            model_claim="unavailable"
            if d["model_status"] == "offline" and not external_calls
            else "unverified",
        )
    if op == "missing_enrichment":
        return dict(
            privilege="unknown" if not view["identity_tier_evidence"] else "observed",
            maester_status=view["posture_evidence"][0]["result"],
        )
    if op == "graph_temporality":
        return dict(
            assessment=view["path_context"]["assessment"]
            if d["observed_path"] != d["current_path"]
            else "same_sequence"
        )
    raise ValueError(op)


def main():
    cases = json.loads(Path("phase3_contract/cases.json").read_bytes())
    for case in cases:
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(store, "ROOT", Path(tmp)),
            patch.object(vault, "ROOT", Path(tmp)),
        ):
            print(
                json.dumps(
                    dict(
                        id=case["id"], actual=decision(case["operation"], case["input"])
                    ),
                    sort_keys=True,
                )
            )


if __name__ == "__main__":
    main()
