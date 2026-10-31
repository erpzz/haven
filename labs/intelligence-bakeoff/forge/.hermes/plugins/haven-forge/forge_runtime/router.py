"""Narrow, fail-closed pre-model routing for shipped synthetic fixtures only."""
from __future__ import annotations

import json
import re
from typing import Callable

from .entra import fixture, route, select_policy, verify


_POLICY_SCOPE = re.compile(r"\b(?:this|the)\s+(?:entra\s+)?(?:conditional\s+access\s+)?policy\b", re.I)
_MUTATION = re.compile(r"\b(?:disable|enable|delete|remove|create|change|modify|update|turn|configure|add|set|apply|edit|alter|reset|toggle|switch|revoke|grant)\b", re.I)


def route_synthetic(question: str, fixture_name: str, policy_id: str, execute: Callable[[dict], str]) -> dict:
    """Decide whether to dispatch, then verify the result; never auto-fallback.

    The caller supplies an executor such as Hermes' own tool dispatcher. This
    helper cannot access arbitrary files, tenants, credentials or model APIs.
    Unknown questions, requested changes and non-fixture inputs are returned
    as NOT_HANDLED so the caller can choose the next authorized action.
    """
    if (not isinstance(question, str) or len(question) > 4000
            or not _POLICY_SCOPE.search(question) or _MUTATION.search(question)):
        return {"route_status": "NOT_HANDLED", "reason": "outside_read_only_synthetic_policy_scope"}
    if route(question) != "deterministic_entra_mfa":
        return {"route_status": "NOT_HANDLED", "reason": "unsupported_question"}
    try:
        snapshot = select_policy(fixture(fixture_name), policy_id)
    except (TypeError, ValueError):
        return {"route_status": "NOT_HANDLED", "reason": "unknown_synthetic_fixture_or_policy"}
    if not isinstance(policy_id, str):
        return {"route_status": "NOT_HANDLED", "reason": "one_synthetic_policy_is_required"}
    try:
        raw = execute({"question": question, "fixture": fixture_name, "policy_id": policy_id})
        report = json.loads(raw) if isinstance(raw, str) else raw
        if (not isinstance(report, dict) or report.get("status") != "VERIFIED_SYNTHETIC"
                or report.get("synthetic") is not True or not verify(snapshot, report)["passed"]):
            return {"route_status": "ERROR", "reason": "assessment_evidence_not_verified"}
    except Exception:  # No exception text or credentials are returned to the caller.
        return {"route_status": "ERROR", "reason": "assessment_failed"}
    return {"route_status": "HANDLED", "report": report}
