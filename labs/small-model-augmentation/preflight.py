"""Offline admission check for an explicitly selected Hermes model.

Inputs must be supplied by a trusted launcher, not by the model under test.
A passing receipt is a consistency check, not proof of loaded weight identity.
"""
import json
import re
import sys

MIN_CONTEXT = 64_000
MAX_BYTES = 65_536
FIELDS = {"expected_model", "requested_model", "observed_model_ids", "observed_context_tokens"}
MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}\Z", re.ASCII)
PLACEHOLDERS = {"model", "model-id", "model_id", "modelid", "your-model", "your_model", "changeme", "todo", "tbd", "none", "null", "unknown", "placeholder"}


def valid_id(value):
    return (type(value) is str and MODEL_ID.fullmatch(value) is not None
            and value.casefold() not in PLACEHOLDERS)


def check(document):
    """Return only fixed diagnostic codes, never input values."""
    errors = []
    if type(document) is not dict or set(document) != FIELDS:
        return receipt(["INVALID_FIELDS"])
    expected = document["expected_model"]
    requested = document["requested_model"]
    observed = document["observed_model_ids"]
    context = document["observed_context_tokens"]
    if not valid_id(expected):
        errors.append("INVALID_EXPECTED_MODEL")
    if not valid_id(requested):
        errors.append("INVALID_REQUESTED_MODEL")
    if valid_id(expected) and valid_id(requested) and requested != expected:
        errors.append("REQUESTED_MODEL_MISMATCH")
    if (type(observed) is not list or not 1 <= len(observed) <= 256
            or not all(valid_id(item) for item in observed)):
        errors.append("INVALID_OBSERVED_MODELS")
    elif len(set(observed)) != len(observed):
        errors.append("DUPLICATE_OBSERVED_MODELS")
    elif valid_id(expected) and observed != [expected]:
        # Single-model local server contract: no ambiguous aliases or inventories.
        errors.append("OBSERVED_MODEL_MISMATCH")
    if type(context) is not int or context < MIN_CONTEXT:
        errors.append("CONTEXT_UNVERIFIED_OR_TOO_SMALL")
    return receipt(errors)


def receipt(errors):
    return {"schema": "haven.model-preflight.v1", "status": "block" if errors else "pass",
            "errors": errors, "minimum_context_tokens": MIN_CONTEXT,
            "weight_identity_verified": False, "live_endpoint_verified": False}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def parse(raw):
    if len(raw) > MAX_BYTES:
        return receipt(["INPUT_TOO_LARGE"])
    try:
        return check(json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object))
    except (ValueError, RecursionError):
        return receipt(["INVALID_JSON"])


def main():
    result = parse(sys.stdin.buffer.read(MAX_BYTES + 1))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
