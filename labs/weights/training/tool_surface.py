"""Hash-bound model-visible tool-surface receipts for Haven training rows.

Collection/inference may supply tools out-of-band from the chat messages. Training must
therefore bind the exact model-visible tool array to each row before tokenization instead
of silently rendering with tools=None.

The binding supports:
- fixed surfaces (for the currently preregistered HARE collection path);
- routed surfaces (for a future #131-adopted collection path);
- exact empty surfaces.

Tool array order is intentionally part of the hash because chat templates may render
tools in order.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections import defaultdict
from typing import Any, Mapping, Sequence

SCHEMA = "haven-weights-tool-surface-v1"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
NAME = re.compile(r"[A-Za-z0-9_.:-]{1,256}\Z", re.ASCII)
MODES = {"fixed", "routed"}
MAX_TOOLS = 256
MAX_JSON_DEPTH = 32
MAX_ITEMS = 1024


class SurfaceError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise SurfaceError("value is not canonical JSON") from exc


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _json_ok(value: Any, depth: int = 0) -> bool:
    if depth > MAX_JSON_DEPTH:
        return False
    if value is None or type(value) is bool:
        return True
    if type(value) is int:
        return -(2**63) <= value <= 2**63 - 1
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is str:
        return len(value) <= 32768 and "\x00" not in value
    if type(value) is list:
        return len(value) <= MAX_ITEMS and all(_json_ok(v, depth + 1) for v in value)
    if type(value) is dict:
        return (
            len(value) <= MAX_ITEMS
            and all(
                isinstance(k, str)
                and len(k) <= 256
                and "\x00" not in k
                and _json_ok(v, depth + 1)
                for k, v in value.items()
            )
        )
    return False


def validate_tools(tools: Sequence[dict]) -> list[str]:
    errors: list[str] = []
    if not isinstance(tools, list) or len(tools) > MAX_TOOLS:
        return ["INVALID_TOOL_ARRAY"]
    names: list[str] = []
    for tool in tools:
        if not isinstance(tool, dict) or set(tool) != {"type", "function"}:
            errors.append("INVALID_TOOL")
            continue
        if tool.get("type") != "function":
            errors.append("INVALID_TOOL_TYPE")
        fn = tool.get("function")
        if not isinstance(fn, dict):
            errors.append("INVALID_FUNCTION")
            continue
        if set(fn) - {"name", "description", "parameters"}:
            errors.append("UNEXPECTED_FUNCTION_FIELD")
        name = fn.get("name")
        if not isinstance(name, str) or NAME.fullmatch(name) is None:
            errors.append("INVALID_TOOL_NAME")
        else:
            names.append(name)
        description = fn.get("description")
        if description is not None and (
            not isinstance(description, str) or len(description) > 65536 or "\x00" in description
        ):
            errors.append("INVALID_TOOL_DESCRIPTION")
        params = fn.get("parameters")
        if not isinstance(params, dict) or not _json_ok(params):
            errors.append("INVALID_TOOL_PARAMETERS")
    if len(names) != len(set(names)):
        errors.append("DUPLICATE_TOOL_NAME")
    return sorted(set(errors))


def tool_surface_sha256(tools: list[dict]) -> str:
    errors = validate_tools(tools)
    if errors:
        raise SurfaceError(",".join(errors))
    return sha256(tools)


def make_binding(
    tools: list[dict],
    *,
    mode: str,
    collector_sha256: str,
    catalog_sha256: str | None = None,
    route_receipt_sha256: str | None = None,
) -> dict:
    """Create one immutable tool-surface binding receipt.

    collector_sha256 binds the collection/run identity or collector contract the caller
    used to establish what the model actually saw. For fixed mode, the surface itself is
    the catalogue. For routed mode, catalog_sha256 names the full host catalogue and a
    route receipt is required for the selected surface.
    """
    errors = validate_tools(tools)
    if errors:
        raise SurfaceError(",".join(errors))
    if mode not in MODES:
        raise SurfaceError("invalid surface mode")
    if not isinstance(collector_sha256, str) or HEX64.fullmatch(collector_sha256) is None:
        raise SurfaceError("invalid collector hash")

    surface_hash = tool_surface_sha256(tools)
    if mode == "fixed":
        if catalog_sha256 not in (None, surface_hash):
            raise SurfaceError("fixed surface catalog hash must equal surface hash")
        if route_receipt_sha256 is not None:
            raise SurfaceError("fixed surface must not carry a route receipt")
        catalog_sha256 = surface_hash
    else:
        if not isinstance(catalog_sha256, str) or HEX64.fullmatch(catalog_sha256) is None:
            raise SurfaceError("routed surface requires catalog hash")
        if not isinstance(route_receipt_sha256, str) or HEX64.fullmatch(route_receipt_sha256) is None:
            raise SurfaceError("routed surface requires route receipt hash")

    body = {
        "schema": SCHEMA,
        "mode": mode,
        "collector_sha256": collector_sha256,
        "catalog_sha256": catalog_sha256,
        "route_receipt_sha256": route_receipt_sha256,
        "tool_surface_sha256": surface_hash,
        "tool_names": [tool["function"]["name"] for tool in tools],
        "tools": copy.deepcopy(tools),
    }
    body["receipt_sha256"] = sha256(body)
    return body


def validate_binding(binding: Mapping[str, Any]) -> list[str]:
    if not isinstance(binding, Mapping):
        return ["INVALID_BINDING"]
    expected = {
        "schema", "mode", "collector_sha256", "catalog_sha256",
        "route_receipt_sha256", "tool_surface_sha256", "tool_names",
        "tools", "receipt_sha256",
    }
    if set(binding) != expected:
        return ["INVALID_BINDING_SHAPE"]
    errors: list[str] = []
    if binding.get("schema") != SCHEMA:
        errors.append("INVALID_SCHEMA")
    mode = binding.get("mode")
    if mode not in MODES:
        errors.append("INVALID_MODE")
    for key in ("collector_sha256", "catalog_sha256", "tool_surface_sha256", "receipt_sha256"):
        value = binding.get(key)
        if not isinstance(value, str) or HEX64.fullmatch(value) is None:
            errors.append("INVALID_HASH")
    route = binding.get("route_receipt_sha256")
    if mode == "fixed":
        if route is not None:
            errors.append("FIXED_ROUTE_RECEIPT_PRESENT")
    elif not isinstance(route, str) or HEX64.fullmatch(route) is None:
        errors.append("INVALID_ROUTE_RECEIPT")

    tools = binding.get("tools")
    tool_errors = validate_tools(tools) if isinstance(tools, list) else ["INVALID_TOOL_ARRAY"]
    errors.extend(tool_errors)
    if not tool_errors:
        surface_hash = tool_surface_sha256(tools)
        if binding.get("tool_surface_sha256") != surface_hash:
            errors.append("SURFACE_HASH_MISMATCH")
        names = [tool["function"]["name"] for tool in tools]
        if binding.get("tool_names") != names:
            errors.append("TOOL_NAMES_MISMATCH")
        if mode == "fixed" and binding.get("catalog_sha256") != surface_hash:
            errors.append("FIXED_CATALOG_MISMATCH")

    body = dict(binding)
    claimed = body.pop("receipt_sha256", None)
    try:
        actual = sha256(body)
    except SurfaceError:
        errors.append("INVALID_BINDING_JSON")
    else:
        if claimed != actual:
            errors.append("RECEIPT_HASH_MISMATCH")
    return sorted(set(errors))


def bind_rows(rows: Sequence[dict], binding: Mapping[str, Any]) -> list[dict]:
    """Attach one exact surface binding to a group of collection rows."""
    errors = validate_binding(binding)
    if errors:
        raise SurfaceError(",".join(errors))
    if not isinstance(rows, Sequence) or not rows:
        raise SurfaceError("rows must be non-empty")
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            raise SurfaceError("row must be an object")
        if any(k in row for k in ("tools", "tool_surface", "tool_surface_sha256")):
            raise SurfaceError("row already contains tool-surface fields")
        if not isinstance(row.get("episode"), str) or not row["episode"]:
            raise SurfaceError("row missing episode")
        if not isinstance(row.get("trace"), str) or not row["trace"]:
            raise SurfaceError("row missing trace")
        copy_row = copy.deepcopy(row)
        copy_row["tools"] = copy.deepcopy(binding["tools"])
        copy_row["tool_surface_sha256"] = binding["tool_surface_sha256"]
        copy_row["tool_surface"] = {
            key: copy.deepcopy(binding[key])
            for key in (
                "schema", "mode", "collector_sha256", "catalog_sha256",
                "route_receipt_sha256", "tool_surface_sha256", "tool_names",
                "receipt_sha256",
            )
        }
        out.append(copy_row)
    return out


def validate_bound_rows(rows: Sequence[dict]) -> list[str]:
    """Validate row bindings and reject routed/fixed mixing inside one training arm."""
    errors: list[str] = []
    if not isinstance(rows, Sequence) or not rows:
        return ["INVALID_ROWS"]

    modes = set()
    catalog_hashes = set()
    collectors = set()
    per_trace: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    for row in rows:
        if not isinstance(row, dict):
            errors.append("INVALID_ROW")
            continue
        tools = row.get("tools")
        meta = row.get("tool_surface")
        if not isinstance(tools, list) or not isinstance(meta, dict):
            errors.append("MISSING_TOOL_SURFACE")
            continue
        tool_errors = validate_tools(tools)
        errors.extend(tool_errors)
        if tool_errors:
            continue
        surface_hash = tool_surface_sha256(tools)
        if row.get("tool_surface_sha256") != surface_hash:
            errors.append("ROW_SURFACE_HASH_MISMATCH")
        if meta.get("tool_surface_sha256") != surface_hash:
            errors.append("META_SURFACE_HASH_MISMATCH")

        # Reconstruct the binding with the row's tools and metadata and require the
        # same receipt hash. This catches source/catalog/route mutation as well.
        reconstructed = {
            **copy.deepcopy(meta),
            "tools": copy.deepcopy(tools),
        }
        if validate_binding(reconstructed):
            errors.append("INVALID_ROW_BINDING")
            continue

        mode = meta["mode"]
        modes.add(mode)
        catalog_hashes.add(meta["catalog_sha256"])
        collectors.add(meta["collector_sha256"])
        episode = row.get("episode")
        trace = row.get("trace")
        if not isinstance(episode, str) or not episode or not isinstance(trace, str) or not trace:
            errors.append("INVALID_ROW_IDENTITY")
            continue
        per_trace[(episode, trace)].add((surface_hash, meta["receipt_sha256"]))

    if len(modes) != 1:
        errors.append("MIXED_SURFACE_MODES")
    if len(catalog_hashes) != 1:
        errors.append("MIXED_CATALOGS")
    if len(collectors) != 1:
        errors.append("MIXED_COLLECTORS")
    if any(len(values) != 1 for values in per_trace.values()):
        errors.append("TRACE_SURFACE_CHANGED")
    return sorted(set(errors))
