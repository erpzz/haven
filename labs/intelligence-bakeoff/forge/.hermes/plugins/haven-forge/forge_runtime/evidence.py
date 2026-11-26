"""Advisory observations, never authorization or proof of a user's objective."""
from __future__ import annotations

import hashlib
import json
import re


RULES = (
    ("command_not_found", r"(?m)^(?:/bin/)?(?:ba|z|a|da)?sh:.*(?:command not found|not found)$"),
    ("missing_dependency", r"(?m)^(?:ModuleNotFoundError|ImportError): No module named"),
    ("invalid_option", r"(?mi)^(?:\S+: )?(?:unrecognized|unknown|illegal|invalid) (?:option|argument)"),
    ("invalid_api_query", r"(?mi)^(?:[\w.]+(?:Error|Exception): )?Invalid (?:search )?query"),
    ("authentication_failure", r"(?mi)^(?:sudo: .*password is required|su: Sorry|.*HTTP(?:Error)?[ :]+401\b|.*Authentication failed\b)"),
    ("permission_denied", r"(?mi)^(?:\S+: )?.*Permission denied(?:[ :].*)?$"),
    ("missing_file", r"(?mi)^(?:\S+: )?.*No such file or directory$"),
    ("rate_limited", r"(?mi)^(?:.*HTTP(?:Error)?[ :]+429\b|.*API rate limit exceeded\b)"),
    ("network_failure", r"(?mi)^(?:curl: \([567]\)|.*Connection refused|.*Failed to resolve |Error resolving )"),
    ("timeout", r"(?mi)^(?:Command timed out|.*Operation timed out|.*TimeoutError:)"),
    ("malformed_output", r"(?m)^(?:[\w.]*JSONDecodeError:|SyntaxError:)"),
)
_PATTERNS = tuple((name, re.compile(pattern)) for name, pattern in RULES)
_RUNNING = {"running", "background", "yielded_to_background", "still_running"}
_CANCELLED = {"cancelled", "canceled", "interrupted", "killed"}


def digest(value) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def observe(tool: str, arguments: dict, result, *, call_id: str = "") -> dict:
    """Normalize the envelope without changing its exit code or parsing shell text.

    Diagnostic matches describe text present in output; content printed by a
    command can contain a diagnostic from another process. They are advisory.
    Missing/boolean/string exit codes never imply successful execution.
    """
    try:
        body = json.loads(result) if isinstance(result, str) else result
    except (ValueError, TypeError):
        body = None
    raw_hash = digest(result)
    event_id = "forge-" + digest([tool, arguments, call_id, raw_hash])[:24]
    record = {
        "schema_version": 1, "event_id": event_id, "tool": tool,
        "result_sha256": raw_hash, "execution": "unknown", "exit_code": None,
        "diagnostics": [], "objective_verified": False,
        "authority": "OBSERVATION_ONLY", "next_action": "inspect_result",
    }
    if not isinstance(body, dict):
        record.update(execution="malformed", diagnostics=["malformed_result_envelope"])
        return record
    status = body.get("status")
    status = status if isinstance(status, str) else ""
    code = body.get("exit_code")
    code = code if type(code) is int else None
    record["exit_code"] = code
    text = "\n".join(str(body.get(k) or "") for k in ("error", "output"))[:16000]
    diagnostics = [name for name, rx in _PATTERNS if rx.search(text)]
    if status in _RUNNING:
        execution, next_action = "running", "await_existing_process"
    elif status in _CANCELLED or (code == 130 and "[Command interrupted]" in text):
        execution, next_action = "cancelled", "inspect_cancellation"
    elif code is not None and code != 0:
        execution, next_action = "failed", "inspect_before_retry"
    elif body.get("error"):
        execution, next_action = "failed", "inspect_before_retry"
    elif code == 0:
        execution = "succeeded_with_diagnostics" if diagnostics else "succeeded"
        next_action = "verify_objective_independently"
    else:
        execution, next_action = "unknown", "inspect_result"
    record.update(execution=execution, diagnostics=diagnostics, next_action=next_action)
    return record


def annotate(tool_name: str, args: dict, result, tool_call_id: str = "", **_kwargs):
    """Hermes transform hook: preserve result fields and add an inert evidence block.

    No command execution, disk writes, retry loop, credential access or claim
    verification. Hermes' own approval and process lifecycle stay authoritative.
    """
    if tool_name not in {"terminal", "process"} or not isinstance(result, str):
        return None
    try:
        body = json.loads(result)
    except ValueError:
        return None
    if not isinstance(body, dict):
        return None
    body["forge_evidence"] = observe(tool_name, args, result, call_id=tool_call_id)
    return json.dumps(body, ensure_ascii=False)
