"""Synthetic, per-policy MFA requirement analysis. No tenant/network access."""
from __future__ import annotations

import json
from pathlib import Path

from .evidence import digest
from .knowledge import load_cards, search


FIXTURES = Path(__file__).with_name("fixtures")
STATES = {"enabled", "disabled", "enabledForReportingButNotEnforced"}
_CONTROLS = {"mfa", "compliantDevice", "domainJoinedDevice", "approvedApplication",
             "compliantApplication", "passwordChange", "block", "unknownFutureValue", "riskRemediation"}

SCOPE = "Per-policy requirement only; does not establish sign-in or tenant MFA coverage."
REMEDIATIONS = {
    "not_enforced_by_policy": "Review report-only results and exclusions; obtain approval before enabling a tested policy.",
    "mfa_not_required_by_policy": "Review grant alternatives. Requiring MFA needs a supported AND control or a separate applicable policy.",
    "mfa_required_by_policy": "Verify assignments, exclusions and actual sign-in results independently.",
    "access_blocked_by_policy": "This policy blocks access; it does not demonstrate MFA enrollment or successful MFA.",
    "indeterminate": "Unsupported control combination: inspect official semantics and sign-in evidence before concluding.",
}
REFERENCE_FIELDS = ("id", "version", "source_url", "sha256", "trust")


def fixture(name: str = "entra-demo") -> dict:
    # No model-selected file path, shell command or URL is accepted.
    if name not in {"entra-demo", "entra-heldout"}:
        raise ValueError("Unknown synthetic fixture")
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def validate(snapshot: dict) -> list[dict]:
    if not isinstance(snapshot, dict) or snapshot.get("synthetic") is not True or snapshot.get("schema_version") != 1:
        raise ValueError("Expected a version-1 synthetic snapshot")
    policies = snapshot.get("policies")
    if not isinstance(policies, list) or len(policies) > 200:
        raise ValueError("Expected at most 200 policies")
    seen = set()
    for policy in policies:
        if not isinstance(policy, dict) or not isinstance(policy.get("id"), str) or not policy["id"]:
            raise ValueError("Every policy needs a nonempty id")
        if policy["id"] in seen:
            raise ValueError("Duplicate policy id")
        seen.add(policy["id"])
        if policy.get("state") not in STATES:
            raise ValueError("Unknown policy state")
        grant = policy.get("grantControls")
        if not isinstance(grant, dict):
            raise ValueError("Missing grant controls")
        controls = grant.get("builtInControls")
        if not isinstance(controls, list) or not all(isinstance(x, str) and x in _CONTROLS for x in controls):
            raise ValueError("Unknown built-in grant control")
        if grant.get("operator") not in {"AND", "OR"}:
            raise ValueError("Unknown grant operator")
        for key in ("termsOfUse", "customAuthenticationFactors"):
            if key in grant and not isinstance(grant[key], list):
                raise ValueError("Malformed supplemental grant controls")
    return policies


def select_policy(snapshot: dict, policy_id: str | None) -> dict:
    """Narrow a shipped synthetic fixture to one existing policy, when requested."""
    policies = validate(snapshot)
    if policy_id is None:
        return snapshot
    if not isinstance(policy_id, str) or len(policy_id) > 128:
        raise ValueError("Invalid synthetic policy id")
    selected = [policy for policy in policies if policy["id"] == policy_id]
    if not selected:
        raise ValueError("Unknown synthetic policy id")
    return {**snapshot, "policies": selected}


def policy_verdict(policy: dict) -> str:
    grant = policy["grantControls"]
    controls = set(grant["builtInControls"])
    if policy["state"] != "enabled":
        return "not_enforced_by_policy"
    if (grant.get("authenticationStrength") or grant.get("customAuthenticationFactors")
            or grant.get("termsOfUse") or controls & {"unknownFutureValue", "riskRemediation", "passwordChange"}):
        return "indeterminate"
    if "block" in controls:
        return "access_blocked_by_policy" if controls == {"block"} else "indeterminate"
    if "mfa" not in controls:
        return "mfa_not_required_by_policy" if controls else "indeterminate"
    if grant["operator"] == "OR" and controls != {"mfa"}:
        return "mfa_not_required_by_policy"
    return "mfa_required_by_policy"


def route(question: str) -> str:
    if not isinstance(question, str):
        raise ValueError("Question must be text")
    q = question.casefold()
    if len(q) > 4000:
        raise ValueError("Question too long")
    if ("conditional access" in q or "entra" in q) and any(w in q for w in ("mfa", "multifactor", "multi-factor")):
        return "deterministic_entra_mfa"
    return "retrieve_only"


def assess(snapshot: dict, question: str) -> dict:
    selected = route(question)
    cards = search(question)
    report = {
        "schema_version": 1, "synthetic": True, "route": selected,
        "snapshot_sha256": digest(snapshot), "coverage_evaluated": False,
        "scope": SCOPE,
        "knowledge": [{k: card[k] for k in REFERENCE_FIELDS} for card in cards],
        "findings": [], "model_invocations": 0, "network_requests": 0,
    }
    if selected == "retrieve_only":
        report["status"] = "OUTSIDE_IMPLEMENTED_CAPABILITY"
        return report
    for index, policy in enumerate(validate(snapshot)):
        evidence = {
            "policy_id": policy["id"], "snapshot_sha256": report["snapshot_sha256"],
            "json_pointer": f"/policies/{index}", "state": policy["state"],
            "grantControls": policy["grantControls"],
        }
        verdict = policy_verdict(policy)
        remediation = REMEDIATIONS[verdict]
        report["findings"].append({
            "policy_id": policy["id"], "verdict": verdict, "evidence": evidence,
            "evidence_id": "entra-" + digest(evidence)[:24], "remediation": remediation,
        })
    report["verification"] = verify(snapshot, report)
    report["status"] = "VERIFIED_SYNTHETIC" if report["verification"]["passed"] else "VERIFICATION_FAILED"
    return report


def verify(snapshot: dict, report: dict) -> dict:
    """Reconcile every finding with source facts using a separate truth-table check.

    This catches tampering, omissions and verdict drift; it shares the input
    schema, so it is not an independent Microsoft policy implementation.
    """
    policies = validate(snapshot)
    failures = []
    if (report.get("schema_version") != 1 or report.get("synthetic") is not True
            or report.get("route") != "deterministic_entra_mfa"
            or report.get("coverage_evaluated") is not False or report.get("scope") != SCOPE):
        failures.append("scope_or_schema_mismatch")
    references = report.get("knowledge")
    known = {card["id"]: {**{k: card[k] for k in REFERENCE_FIELDS if k != "trust"},
                           "trust": "REFERENCE_DATA_ONLY"} for card in load_cards()}
    if (not isinstance(references, list) or any(not isinstance(ref, dict)
            or ref.get("id") not in known or ref != known[ref["id"]] for ref in references)
            or len({ref["id"] for ref in references if isinstance(ref, dict) and "id" in ref}) != len(references)):
        failures.append("knowledge_reference_mismatch")
    if report.get("snapshot_sha256") != digest(snapshot):
        failures.append("snapshot_hash_mismatch")
    findings = report.get("findings", [])
    if len(findings) != len(policies):
        failures.append("finding_count_mismatch")
    for index, (policy, finding) in enumerate(zip(policies, findings)):
        grant = policy["grantControls"]
        controls = frozenset(grant["builtInControls"])
        unsupported = bool(grant.get("authenticationStrength") or grant.get("termsOfUse")
                           or grant.get("customAuthenticationFactors")
                           or controls.intersection({"unknownFutureValue", "riskRemediation", "passwordChange"}))
        if policy["state"] in {"disabled", "enabledForReportingButNotEnforced"}:
            expected = "not_enforced_by_policy"
        elif unsupported or not controls or ("block" in controls and len(controls) > 1):
            expected = "indeterminate"
        elif controls == frozenset({"block"}):
            expected = "access_blocked_by_policy"
        else:
            must_mfa = "mfa" in controls and (grant["operator"] == "AND" or len(controls) == 1)
            expected = "mfa_required_by_policy" if must_mfa else "mfa_not_required_by_policy"
        expected_evidence = {
            "policy_id": policy["id"], "snapshot_sha256": digest(snapshot),
            "json_pointer": f"/policies/{index}", "state": policy["state"], "grantControls": grant,
        }
        if (finding.get("policy_id") != policy["id"] or finding.get("verdict") != expected
                or finding.get("evidence") != expected_evidence
                or finding.get("evidence_id") != "entra-" + digest(expected_evidence)[:24]
                or finding.get("remediation") != REMEDIATIONS[expected]):
            failures.append(f"policy_{index}_evidence_or_verdict_mismatch")
    return {"passed": not failures, "checked_policies": len(policies), "failures": failures,
            "method": "source_hash_json_pointer_and_separate_truth_table"}
