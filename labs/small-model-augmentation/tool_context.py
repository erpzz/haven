"""Deterministic tool-context router for small-model sessions.

The router is not an authorization layer. It can only narrow a host-authorized
tool set. Routing uses host-curated route_terms, never free-form tool descriptions
or model output. The returned definitions are byte-budgeted exactly as serialized.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

SCHEMA = "haven.tool-context.v1"
RECEIPT = "haven.tool-context-receipt.v1"
MAX_CARDS = 512
MAX_CATALOG_BYTES = 8 * 1024 * 1024
MAX_DEFINITION_BYTES = 256 * 1024
MAX_QUERY = 16_000
EFFECTS = {"read", "change", "create"}
NAME = re.compile(r"[A-Za-z0-9_.:-]{1,256}\Z", re.ASCII)
TERM = re.compile(r"[a-z0-9][a-z0-9_.:-]{0,79}\Z", re.ASCII)
WORD = re.compile(r"[a-z0-9][a-z0-9_.:-]*", re.ASCII)


def _canon(value) -> bytes:
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
        return len(value) <= 1024 and all(_json_ok(x, depth + 1) for x in value)
    if type(value) is dict:
        return (len(value) <= 1024
                and all(type(k) is str and len(k) <= 256 and _json_ok(v, depth + 1)
                        for k, v in value.items()))
    return False


def _name(value):
    return type(value) is str and NAME.fullmatch(value) is not None


def _term(value):
    return type(value) is str and TERM.fullmatch(value) is not None


def validate_catalog(cards):
    errors = []
    if type(cards) is not list or not 1 <= len(cards) <= MAX_CARDS:
        return ["INVALID_CATALOG"]
    seen = set()
    total = 2
    for card in cards:
        if type(card) is not dict or set(card) != {"name", "effect", "route_terms", "definition"}:
            errors.append("INVALID_CARD")
            continue
        name = card["name"]
        if not _name(name):
            errors.append("INVALID_TOOL_NAME")
        elif name in seen:
            errors.append("DUPLICATE_TOOL_NAME")
        else:
            seen.add(name)
        if card["effect"] not in EFFECTS:
            errors.append("INVALID_EFFECT")
        terms = card["route_terms"]
        if (type(terms) is not list or not 1 <= len(terms) <= 64
                or not all(_term(x) for x in terms) or len(terms) != len(set(terms))):
            errors.append("INVALID_ROUTE_TERMS")
        definition = card["definition"]
        if not _json_ok(definition) or type(definition) is not dict:
            errors.append("INVALID_DEFINITION")
        elif definition.get("name") != name:
            errors.append("DEFINITION_NAME_MISMATCH")
        else:
            try:
                size = len(_canon(definition))
            except (TypeError, ValueError, RecursionError):
                errors.append("INVALID_DEFINITION")
            else:
                if size > MAX_DEFINITION_BYTES:
                    errors.append("DEFINITION_TOO_LARGE")
                total += size + 1
    if total > MAX_CATALOG_BYTES:
        errors.append("CATALOG_TOO_LARGE")
    return sorted(set(errors))


def catalog_sha256(cards):
    errors = validate_catalog(cards)
    if errors:
        raise ValueError(",".join(errors))
    normalized = sorted(cards, key=lambda c: c["name"])
    return hashlib.sha256(_canon(normalized)).hexdigest()


def _tokens(query):
    return set(WORD.findall(query.lower()))


def _score(query_tokens, route_terms):
    return sum(term in query_tokens for term in route_terms)


def _context_bytes(definitions):
    return len(_canon(definitions))


def _blocked(code, **fields):
    return {"schema": RECEIPT, "status": "block", "errors": [code], **fields}


def route(cards, query, *, authorized, required=(), allowed_effects=("read",),
          max_tools=8, max_schema_bytes=24_000, expected_catalog_sha256=None):
    """Return a deterministic subset of already-authorized tool definitions.

    definition must be the exact model-visible definition the integration will
    send. route_terms are separate host-curated routing metadata.
    """
    errors = validate_catalog(cards)
    if errors:
        return {"schema": RECEIPT, "status": "block", "errors": errors}
    if type(query) is not str or len(query) > MAX_QUERY or "\x00" in query:
        return _blocked("INVALID_QUERY")
    if (type(authorized) not in (list, tuple, set) or not authorized
            or not all(_name(x) for x in authorized)):
        return _blocked("INVALID_AUTHORIZED_SET")
    if len(authorized) != len(set(authorized)):
        return _blocked("DUPLICATE_AUTHORIZED_TOOL")
    if (type(required) not in (list, tuple, set) or not all(_name(x) for x in required)
            or len(required) != len(set(required))):
        return _blocked("INVALID_REQUIRED_SET")
    if (type(allowed_effects) not in (list, tuple, set) or not allowed_effects
            or not set(allowed_effects) <= EFFECTS):
        return _blocked("INVALID_ALLOWED_EFFECTS")
    if type(max_tools) is not int or type(max_tools) is bool or not 1 <= max_tools <= 64:
        return _blocked("INVALID_MAX_TOOLS")
    if (type(max_schema_bytes) is not int or type(max_schema_bytes) is bool
            or not 64 <= max_schema_bytes <= 1_048_576):
        return _blocked("INVALID_SCHEMA_BUDGET")

    by_name = {card["name"]: card for card in cards}
    authorized = set(authorized)
    required = set(required)
    if not authorized <= set(by_name):
        return _blocked("AUTHORIZED_TOOL_NOT_IN_CATALOG")
    if not required <= authorized:
        return _blocked("REQUIRED_TOOL_NOT_AUTHORIZED")

    catalog_hash = catalog_sha256(cards)
    common = {"catalog_sha256": catalog_hash, "catalog_count": len(cards)}
    if expected_catalog_sha256 is not None:
        if (type(expected_catalog_sha256) is not str
                or re.fullmatch(r"[0-9a-f]{64}", expected_catalog_sha256) is None):
            return _blocked("INVALID_EXPECTED_CATALOG_HASH", **common)
        if expected_catalog_sha256 != catalog_hash:
            return _blocked("CATALOG_CHANGED", **common)

    allowed_effects = set(allowed_effects)
    if any(by_name[name]["effect"] not in allowed_effects for name in required):
        return _blocked("REQUIRED_EFFECT_NOT_ALLOWED", **common)

    required_order = sorted(required)
    definitions = [by_name[name]["definition"] for name in required_order]
    if len(definitions) > max_tools:
        return _blocked("REQUIRED_TOOL_BUDGET_EXCEEDED", **common)
    used_bytes = _context_bytes(definitions)
    if used_bytes > max_schema_bytes:
        return _blocked("REQUIRED_SCHEMA_BUDGET_EXCEEDED",
                        schema_bytes=used_bytes, **common)

    query_tokens = _tokens(query)
    ranked = []
    for name in sorted(authorized - required):
        card = by_name[name]
        if card["effect"] not in allowed_effects:
            continue
        score = _score(query_tokens, card["route_terms"])
        if score:
            ranked.append((-score, name))
    ranked.sort()

    selected = list(required_order)
    relevant_count = len(ranked)
    budget_limited = False
    for _, name in ranked:
        if len(selected) >= max_tools:
            budget_limited = True
            break
        trial = definitions + [by_name[name]["definition"]]
        trial_bytes = _context_bytes(trial)
        if trial_bytes <= max_schema_bytes:
            selected.append(name)
            definitions = trial
            used_bytes = trial_bytes
        else:
            budget_limited = True

    optional_selected = len(selected) - len(required_order)
    return {
        "schema": RECEIPT,
        "status": "pass",
        "errors": [],
        **common,
        "authorized_count": len(authorized),
        "selected": selected,
        "selected_count": len(selected),
        "required_count": len(required_order),
        "relevant_count": relevant_count,
        "omitted_relevant_count": relevant_count - optional_selected,
        "budget_limited": budget_limited,
        "schema_bytes": used_bytes,
        "max_schema_bytes": max_schema_bytes,
        "max_tools": max_tools,
        "definitions": definitions,
    }
