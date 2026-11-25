"""Exact host-owned claim bundle selection for bounded small-model answers.

The model candidate is not a prose channel. It may select claim ids only. Scope,
payloads, citations and limitations are projected from the host-owned bundle after
selection, so fields from different claims cannot be spliced into a new conclusion.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

BUNDLE_SCHEMA = "haven.claim-bundle.v1"
RECEIPT_SCHEMA = "haven.claim-release.v1"
MAX_BUNDLE_BYTES = 8 * 1024 * 1024
MAX_CANDIDATE_CHARS = 131_072
MAX_CLAIMS = 2048
TOKEN = re.compile(r"[A-Za-z0-9_.:@/-]{1,256}\Z", re.ASCII)
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _json_ok(value, depth=0):
    if depth > 32:
        return False
    if value is None or type(value) is bool:
        return True
    if type(value) is int:
        return -(2**63) <= value <= 2**63 - 1
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is str:
        return len(value) <= 32_768 and "\x00" not in value
    if type(value) is list:
        return len(value) <= 4096 and all(_json_ok(x, depth + 1) for x in value)
    if type(value) is dict:
        return (len(value) <= 4096
                and all(type(k) is str and len(k) <= 256 and _json_ok(v, depth + 1)
                        for k, v in value.items()))
    return False


def _token(value):
    return type(value) is str and TOKEN.fullmatch(value) is not None


def validate_bundle(bundle):
    errors = []
    if type(bundle) is not dict or set(bundle) != {
            "schema", "scope", "claims", "global_limitations"}:
        return ["INVALID_BUNDLE_SHAPE"]
    if bundle.get("schema") != BUNDLE_SCHEMA:
        errors.append("INVALID_BUNDLE_SCHEMA")
    if type(bundle.get("scope")) is not dict or not _json_ok(bundle["scope"]):
        errors.append("INVALID_SCOPE")

    claims = bundle.get("claims")
    if type(claims) is not list or len(claims) > MAX_CLAIMS:
        return sorted(set(errors + ["INVALID_CLAIMS"]))
    seen = set()
    for claim in claims:
        if type(claim) is not dict or set(claim) != {"id", "citation", "payload"}:
            errors.append("INVALID_CLAIM")
            continue
        cid = claim["id"]
        if not _token(cid):
            errors.append("INVALID_CLAIM_ID")
        elif cid in seen:
            errors.append("DUPLICATE_CLAIM_ID")
        else:
            seen.add(cid)
        if not _token(claim["citation"]):
            errors.append("INVALID_CITATION")
        if type(claim["payload"]) is not dict or not _json_ok(claim["payload"]):
            errors.append("INVALID_PAYLOAD")

    limitations = bundle.get("global_limitations")
    if (type(limitations) is not list or len(limitations) > 256
            or not all(type(x) is str and 0 < len(x) <= 2048 and "\x00" not in x
                       for x in limitations)):
        errors.append("INVALID_GLOBAL_LIMITATIONS")

    try:
        size = len(_canon(bundle))
    except (TypeError, ValueError, RecursionError):
        errors.append("INVALID_BUNDLE_JSON")
    else:
        if size > MAX_BUNDLE_BYTES:
            errors.append("BUNDLE_TOO_LARGE")
    return sorted(set(errors))


def bundle_sha256(bundle):
    errors = validate_bundle(bundle)
    if errors:
        raise ValueError(",".join(errors))
    normalized = {**bundle, "claims": sorted(bundle["claims"], key=lambda c: c["id"])}
    return hashlib.sha256(_canon(normalized)).hexdigest()


def parse_candidate(raw):
    if type(raw) is not str or len(raw) > MAX_CANDIDATE_CHARS:
        return None, ["INVALID_CANDIDATE"]

    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("duplicate key")
            out[key] = value
        return out

    def reject_constant(_):
        raise ValueError("non-finite")

    try:
        value = json.loads(raw, object_pairs_hook=unique, parse_constant=reject_constant)
    except (ValueError, RecursionError):
        return None, ["INVALID_CANDIDATE_JSON"]
    if type(value) is not dict or set(value) != {"bundle_sha256", "claims"}:
        return None, ["INVALID_CANDIDATE_SHAPE"]
    if (type(value["bundle_sha256"]) is not str
            or HEX64.fullmatch(value["bundle_sha256"]) is None):
        return None, ["INVALID_CANDIDATE_HASH"]
    chosen = value["claims"]
    if (type(chosen) is not list or len(chosen) > MAX_CLAIMS
            or not all(_token(x) for x in chosen)):
        return None, ["INVALID_CANDIDATE_CLAIMS"]
    if len(chosen) != len(set(chosen)):
        return None, ["DUPLICATE_CANDIDATE_CLAIM"]
    return value, []


def _release_error(code, bundle_hash=None):
    out = {"schema": RECEIPT_SCHEMA, "released": False, "errors": [code]}
    if bundle_hash is not None:
        out["bundle_sha256"] = bundle_hash
    return out


def release(bundle, candidate_raw, *, allowed_ids, required_ids=(),
            max_claims=32, expected_bundle_sha256=None):
    """Release only exact, host-owned claims selected by id.

    allowed_ids is the host question/scope relevance boundary. required_ids
    prevents the model from omitting host-required claims or conflicting evidence.
    """
    errors = validate_bundle(bundle)
    if errors:
        return {"schema": RECEIPT_SCHEMA, "released": False, "errors": errors}

    ids = {claim["id"] for claim in bundle["claims"]}
    if (type(allowed_ids) not in (list, tuple, set)
            or not all(_token(x) for x in allowed_ids)
            or len(allowed_ids) != len(set(allowed_ids))):
        return _release_error("INVALID_ALLOWED_IDS")
    if (type(required_ids) not in (list, tuple, set)
            or not all(_token(x) for x in required_ids)
            or len(required_ids) != len(set(required_ids))):
        return _release_error("INVALID_REQUIRED_IDS")
    allowed = set(allowed_ids)
    required = set(required_ids)
    if not allowed <= ids:
        return _release_error("ALLOWED_ID_NOT_IN_BUNDLE")
    if not required <= allowed:
        return _release_error("REQUIRED_ID_NOT_ALLOWED")
    if type(max_claims) is not int or type(max_claims) is bool or not 0 <= max_claims <= 256:
        return _release_error("INVALID_MAX_CLAIMS")

    bundle_hash = bundle_sha256(bundle)
    if expected_bundle_sha256 is not None:
        if (type(expected_bundle_sha256) is not str
                or HEX64.fullmatch(expected_bundle_sha256) is None):
            return _release_error("INVALID_EXPECTED_BUNDLE_HASH", bundle_hash)
        if expected_bundle_sha256 != bundle_hash:
            return _release_error("BUNDLE_CHANGED", bundle_hash)

    candidate, parse_errors = parse_candidate(candidate_raw)
    if parse_errors:
        return {"schema": RECEIPT_SCHEMA, "released": False, "errors": parse_errors,
                "bundle_sha256": bundle_hash}
    if candidate["bundle_sha256"] != bundle_hash:
        return _release_error("CANDIDATE_BUNDLE_MISMATCH", bundle_hash)

    chosen = candidate["claims"]
    if len(chosen) > max_claims:
        return _release_error("CLAIM_BUDGET_EXCEEDED", bundle_hash)
    chosen_set = set(chosen)
    if not chosen_set <= allowed:
        return _release_error("CLAIM_NOT_ALLOWED", bundle_hash)
    if not required <= chosen_set:
        return _release_error("REQUIRED_CLAIM_MISSING", bundle_hash)

    selected = sorted(
        (claim for claim in bundle["claims"] if claim["id"] in chosen_set),
        key=lambda claim: claim["id"],
    )
    projected = json.loads(json.dumps(selected, ensure_ascii=False))
    scope = json.loads(json.dumps(bundle["scope"], ensure_ascii=False))
    return {
        "schema": RECEIPT_SCHEMA,
        "released": True,
        "errors": [],
        "bundle_sha256": bundle_hash,
        "allowed_count": len(allowed),
        "required_count": len(required),
        "selected_count": len(projected),
        "scope": scope,
        "claims": projected,
        "global_limitations": list(bundle["global_limitations"]),
    }
