"""Pure-stdlib reference policy oracle for synthetic Purple Copilot APM Phase 3.

This is NOT an EntraOps/Maester import adapter. It deliberately consumes a tiny,
contract-level synthetic format, so a future importer can be measured against
independently defined policy decisions without network or model dependencies.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

RESULTS = {"Passed", "Failed", "Investigate", "Skipped", "NotRun", "Error"}
ALLOWED_TOOLS = ("path_context", "identity_tier_evidence", "posture_evidence", "collection_quality")
SAFE_TRAVERSALS = {"MemberOf", "AZMemberOf"}
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")


class InvalidEvidence(ValueError):
    pass


def utc(s: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError) as exc:
        raise InvalidEvidence("invalid_timestamp") from exc
    if parsed.utcoffset() != timedelta(0):
        raise InvalidEvidence("non_utc_timestamp")
    return parsed


def key(x: dict):
    fields = ("dataset_id", "provider", "native_kind", "native_id")
    if not all(isinstance(x.get(f), str) and x[f].strip() for f in fields):
        return None
    return tuple(x[f] for f in fields)


def join(a: dict, b: dict) -> str:
    if a.get("dataset_id") != b.get("dataset_id"):
        return "cross_dataset_rejected"
    if key(a) is None or key(b) is None:
        return "unmatched"
    if a["provider"] != b["provider"] or a["native_kind"] != b["native_kind"]:
        return "incompatible_kind"
    return "exact" if a["native_id"] == b["native_id"] else "unmatched"


def confidence(d: dict) -> str:
    if not d.get("complete") or d.get("warnings") or not set(d.get("partitions", [])) >= set(d.get("required", [])):
        return "limited"
    try:
        collected, observed = utc(d["collected_utc"]), utc(d["observed_utc"])
    except (InvalidEvidence, KeyError):
        return "limited"
    return "verified" if timedelta(0) <= observed - collected <= timedelta(days=1) else "limited"


def variant(d: dict) -> str:
    if not isinstance(d.get("Tests"), list) or not d.get("ExecutedAt") or not isinstance(d.get("Result"), str):
        return "unsupported"
    schema = d.get("SchemaVersion")
    if schema is None:
        return "maester_2x"
    if schema == "2.1" and isinstance(d.get("CatalogVersion"), str):
        return "maester_3_preview"
    return "unsupported"


def posture_status(d: dict) -> str:
    if not d.get("coverage") or not d.get("provenance"):
        return "unresolved"
    states = d.get("states", [])
    if not states or any(x not in RESULTS for x in states):
        return "unresolved"
    if states[-1] in ("NotRun", "Skipped", "Error", "Investigate"):
        return "unresolved"
    if states[0] == "Failed" and states[-1] == "Passed":
        return "needs_independent_validation"
    return "observed_failure" if states[-1] == "Failed" else "passed_check_only"


def evaluate(case: dict) -> dict:
    """Evaluate one declarative, synthetic oracle test; never execute a tool or network call."""
    d = case["input"]
    op = case["operation"]
    if op == "receipt_identity":
        existing = {}
        decisions = []
        for item in d["runs"]:
            run = (item["source"], item["dataset_id"], item["run_id"])
            dig = hashlib.sha256(item["bytes"].encode("utf-8")).hexdigest()
            if run not in existing:
                existing[run] = dig
                decisions.append("accepted")
            elif existing[run] == dig:
                decisions.append("replayed")
            else:
                decisions.append("conflict_rejected")
        return {"decisions": decisions, "distinct_artifacts": len(existing)}
    if op == "identity_join":
        return {"join": join(d["left"], d["right"])}
    if op == "missing_reference":
        return {"join": "unmatched", "retained_stub": bool(d.get("stub"))}
    if op == "assignment_mode":
        modes = set(d.get("modes", []))
        return {"observed": sorted(modes), "active_privilege_proven": "active" in modes}
    if op == "tiers":
        attrs = {(x["rbac_system"], x["tier"]) for x in d["assignments"]}
        return {"scoped_tiers": sorted([list(x) for x in attrs]), "collapsed": False}
    if op == "edge_semantics":
        return {"traversable": d.get("edge_kind") in SAFE_TRAVERSALS}
    if op == "maester_shapes":
        return {"variants": [variant(o) for o in d["exports"]]}
    if op == "test_lifecycle":
        return {"resolution": posture_status(d)}
    if op == "posture_link":
        reference = d.get("affected", {})
        native = reference.get("NativeObjectId")
        if d.get("scope") == "tenant" or not native:
            return {"link": "tenant_context" if d.get("scope") == "tenant" else "unknown"}
        return {"link": "exact_object" if reference.get("VerifiedNativeId") is True and native == d.get("target_id") else "unknown"}
    if op == "affected_uniqueid":
        return {"match": "unknown" if not d.get("native_id_verified") else "verified_explicit"}
    if op == "freshness":
        return {"confidence": confidence(d)}
    if op == "immutable_facts":
        return {"finding_state_unchanged": d["before"] == d["after"]}
    if op == "tool_injection":
        # A text field is deliberately not interpreted as a tool instruction.
        return {"exposed_tools": list(ALLOWED_TOOLS), "executed_tools": [], "text_is_data": True}
    if op == "format_validation":
        invalid = []
        if d.get("byte_count", 0) > d.get("max_bytes", 1024 * 1024):
            invalid.append("oversized")
        try:
            json.loads(d.get("json_text", ""))
        except json.JSONDecodeError:
            invalid.append("malformed_json")
        if len(d.get("ids", [])) != len(set(d.get("ids", []))):
            invalid.append("duplicate_ids")
        try:
            utc(d.get("collected_utc"))
        except InvalidEvidence:
            invalid.append("bad_timestamp")
        return {"invalid": invalid, "accepted": not invalid}
    if op == "public_redaction":
        text = EMAIL.sub("[REDACTED_EMAIL]", d["text"])
        return {"public_text": text, "raw_export_public": False}
    if op == "model_unavailable":
        return {"deterministic_import": "unaffected", "model_claim": "unavailable"}
    if op == "missing_enrichment":
        return {"privilege": "unknown", "maester_status": d["maester_status"]}
    if op == "graph_temporality":
        return {"assessment": "present_in_current_graph" if d["observed_path"] == d["current_path"] else "historical_only"}
    raise InvalidEvidence("unknown_operation")


def run_suite(path: Path):
    cases = json.loads(path.read_text())
    if not isinstance(cases, list):
        raise InvalidEvidence("test_suite_must_be_list")
    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise InvalidEvidence("duplicate_case_ids")
    if ids != [f"P3-{i:02d}" for i in range(1, 21)]:
        raise InvalidEvidence("expected_P3-01_through_P3-20")
    out = []
    for case in cases:
        actual = evaluate(case)
        out.append({"id": case["id"], "pass": actual == case["expected"], "actual": actual})
    return out


def compare_adapter_results(reference, result_file: Path):
    """Check a future Codex adapter's JSONL output against the *frozen* expected results."""
    rows = [json.loads(line) for line in result_file.read_text().splitlines() if line.strip()]
    target = {c["id"]: c["expected"] for c in reference}
    seen, failures = set(), []
    for row in rows:
        ident = row.get("id")
        if ident in seen or ident not in target:
            failures.append(f"duplicate/unknown id: {ident}")
            continue
        seen.add(ident)
        if row.get("actual") != target[ident]:
            failures.append(f"mismatch: {ident}")
    for missing in target.keys() - seen:
        failures.append(f"missing: {missing}")
    return sorted(failures)


def main():
    parser = argparse.ArgumentParser(description="Synthetic APM Phase 3 contract oracle, no network/model use")
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("cases.json"))
    parser.add_argument("--adapter-results", type=Path, help="JSONL lines: {'id':'P3-xx', 'actual': {...}}")
    parser.add_argument("--write-oracle", type=Path, help="Write reference JSONL for harness validation only")
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text())
    results = run_suite(args.cases)
    failures = [r["id"] for r in results if not r["pass"]]
    if args.write_oracle:
        args.write_oracle.write_text("".join(json.dumps({"id": c["id"], "actual": c["expected"]}, sort_keys=True) + "\n" for c in cases))
    if args.adapter_results:
        failures += compare_adapter_results(cases, args.adapter_results)
    print(json.dumps({"cases": len(results), "oracle_passed": sum(r["pass"] for r in results), "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
