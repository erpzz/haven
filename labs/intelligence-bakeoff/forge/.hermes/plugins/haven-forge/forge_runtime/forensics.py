"""Local-only trajectory extraction and explicit, fail-closed dataset admission."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .evidence import observe, digest


def _trace_references(path: Path) -> tuple[str, dict]:
    raw = path.read_bytes()
    references = {}
    for number, line in enumerate(raw.splitlines(), 1):
        row = json.loads(line)
        content = row.get("message", {}).get("content", [])
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            call_id = block.get("id") if kind == "tool_use" else block.get("tool_use_id")
            if kind in {"tool_use", "tool_result"} and call_id:
                slot = references.setdefault(call_id, {})
                if kind in slot:
                    raise ValueError("Duplicate tool identity in trace")
                slot[kind] = {"line": number, "uuid": row.get("uuid")}
    return hashlib.sha256(raw).hexdigest(), references


def extract(path: Path, trace: Path | None = None) -> list[dict]:
    """Read Hermes session JSONL, correlate tool calls by ID, preserve unknowns.

    Private event records contain original arguments/results for local review.
    Nothing is sent to a model or external service. Duplicate call IDs are
    rejected instead of silently attributing a result to the wrong invocation.
    """
    raw = path.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    trace_hash, trace_refs = _trace_references(trace) if trace else (None, {})
    events = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        session = json.loads(line)
        messages = session.get("messages")
        if not isinstance(messages, list):
            raise ValueError("Expected Hermes sessions export JSONL (one session per line)")
        calls = {}
        objective = ""
        for index, message in enumerate(messages):
            if message.get("role") == "user":
                objective = message.get("content")
            for call in message.get("tool_calls") or []:
                call_id = call.get("id") or call.get("call_id")
                if not call_id or call_id in calls:
                    raise ValueError("Missing or duplicate tool call ID")
                fn = call.get("function", {})
                arguments = fn.get("arguments", {})
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except ValueError:
                        arguments = {"unparsed_arguments": arguments}
                calls[call_id] = {"tool": fn.get("name"), "arguments": arguments,
                                  "call_index": index, "call_timestamp": message.get("timestamp"),
                                  "objective": objective, "result": None, "result_index": None}
            if message.get("role") == "tool":
                call_id = message.get("tool_call_id")
                if call_id not in calls:
                    raise ValueError("Orphan tool result; cannot establish provenance")
                event = calls[call_id]
                if event["result_index"] is not None:
                    raise ValueError("Duplicate result for one tool call")
                event.update(result=message.get("content"), result_index=index,
                             result_timestamp=message.get("timestamp"),
                             result_message_id=message.get("message_uid") or message.get("id"))
        for call_id, event in calls.items():
            reference = {"session_sha256": source_hash, "export_line": line_number,
                         "session_id": session["id"], "tool_call_id": call_id,
                         "call_message_index": event["call_index"],
                         "result_message_index": event["result_index"]}
            if trace:
                if call_id not in trace_refs:
                    raise ValueError("Session call has no matching trace reference")
                reference.update(trace_sha256=trace_hash, trace=trace_refs[call_id])
            observation = observe(event["tool"], event["arguments"], event["result"], call_id=call_id)
            if event["result_index"] is None:
                observation.update(execution="unknown", diagnostics=["missing_tool_result"])
            interpretation = None
            if event["result_index"] is not None:
                # Only the immediate next model message is associated. This is
                # context for human review, not an automatic claim attribution.
                for message in messages[event["result_index"] + 1:]:
                    if message.get("role") == "assistant":
                        interpretation = message.get("content")
                        break
                    if message.get("role") == "user":
                        break
            events.append({"event_id": observation["event_id"], "reference": reference,
                           **event, "observation": observation,
                           "following_model_text_unverified": interpretation,
                           "primary_cause": "UNREVIEWED", "training_admitted": False})
    return events


def write_private_jsonl(path: Path, rows: list[dict]) -> None:
    """Create once, owner-only, no overwrite/symlink following or public repo output."""
    parent = path.parent.resolve()
    for candidate in (parent, *parent.parents):
        if (candidate / ".git").exists():
            raise ValueError("Private trajectories must stay outside Git checkouts")
    if not parent.is_dir() or parent.stat().st_mode & 0o077:
        raise ValueError("Create an owner-only output directory (mode 0700) first")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def admission(candidate: dict, *, evaluation_groups: set[str]) -> list[str]:
    """List rejection reasons. An annotation alone cannot assert verification.

    Only reviewed, original synthetic examples can enter the initial dataset.
    Real private sessions supply failure provenance, never verbatim training
    targets. Verification receipts bind the admitted input/output by SHA256.
    """
    reasons = []
    if candidate.get("synthetic") is not True or candidate.get("license") != "CC0-1.0":
        reasons.append("synthetic_original_license_required")
    if candidate.get("privacy_review") != "passed" or candidate.get("reviewer") != "operator-authorized-local-review":
        reasons.append("privacy_review_required")
    if candidate.get("group") in evaluation_groups:
        reasons.append("evaluation_group_overlap")
    for field in ("id", "group", "input", "target", "provenance", "verification"):
        if not candidate.get(field):
            reasons.append("missing_" + field)
    receipt = candidate.get("verification", {})
    if (not isinstance(receipt, dict) or receipt.get("passed") is not True
            or receipt.get("input_sha256") != digest(candidate.get("input"))
            or receipt.get("target_sha256") != digest(candidate.get("target"))
            or receipt.get("method") != "deterministic_reproduction"):
        reasons.append("verified_reproduction_required")
    return reasons
