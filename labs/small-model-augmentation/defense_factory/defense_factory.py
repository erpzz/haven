#!/usr/bin/env python3
"""Local, deterministic defense-factory primitives for Haven.

This module intentionally does not execute scanners, patches, or tests. It normalizes
scanner evidence, constrains model-authored unified diffs, and records a tamper-evident
finding lifecycle so execution can remain in a separate host-owned runner.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import PurePosixPath
from typing import Any, Callable, Iterable, Mapping

SCHEMA = "haven-local-defense-factory-v1"
MAX_PATCH_BYTES = 64 * 1024
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")

_SEVERITY = {
    "error": "high",
    "warning": "medium",
    "note": "low",
    "none": "info",
}
_ALLOWED_SEVERITIES = {"critical", "high", "medium", "low", "info"}

def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def canonical_rel_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("path must be a non-empty string without NUL")
    if "\\" in value:
        raise ValueError("backslashes are not accepted in repository paths")
    if "://" in value:
        raise ValueError("URI schemes are not accepted in repository paths")
    p = PurePosixPath(value)
    if p.is_absolute():
        raise ValueError("absolute paths are not allowed")
    parts = [part for part in p.parts if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        raise ValueError("path traversal is not allowed")
    return "/".join(parts)

@dataclass(frozen=True)
class EvidenceRef:
    path: str
    line_start: int
    line_end: int
    file_sha256: str
    excerpt_sha256: str

    @classmethod
    def from_bytes(cls, path: str, content: bytes, line_start: int, line_end: int) -> "EvidenceRef":
        path = canonical_rel_path(path)
        if isinstance(line_start, bool) or isinstance(line_end, bool):
            raise ValueError("line numbers must be integers")
        if not isinstance(line_start, int) or not isinstance(line_end, int):
            raise ValueError("line numbers must be integers")
        if line_start < 1 or line_end < line_start:
            raise ValueError("invalid line range")
        lines = content.splitlines(keepends=True)
        if line_start > len(lines) or line_end > len(lines):
            raise ValueError("line range exceeds file")
        excerpt = b"".join(lines[line_start - 1:line_end])
        return cls(
            path=path,
            line_start=line_start,
            line_end=line_end,
            file_sha256=_sha256(content),
            excerpt_sha256=_sha256(excerpt),
        )

@dataclass(frozen=True)
class Finding:
    finding_id: str
    rule_id: str
    severity: str
    title: str
    evidence: EvidenceRef
    source: str = "sarif"

    @classmethod
    def build(cls, *, rule_id: str, severity: str, title: str, evidence: EvidenceRef, source: str = "sarif") -> "Finding":
        if not isinstance(rule_id, str) or not rule_id.strip():
            raise ValueError("rule_id required")
        if severity not in _ALLOWED_SEVERITIES:
            raise ValueError("unsupported severity")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title required")
        if not isinstance(source, str) or not source.strip():
            raise ValueError("source required")
        identity = {
            "schema": SCHEMA,
            "source": source,
            "rule_id": rule_id.strip(),
            "severity": severity,
            "path": evidence.path,
            "line_start": evidence.line_start,
            "line_end": evidence.line_end,
            "file_sha256": evidence.file_sha256,
            "excerpt_sha256": evidence.excerpt_sha256,
        }
        return cls(
            finding_id="hdf_" + _sha256(_canonical_json(identity))[:32],
            rule_id=rule_id.strip(),
            severity=severity,
            title=title.strip(),
            evidence=evidence,
            source=source.strip(),
        )

def findings_from_sarif(doc: Mapping[str, Any], read_file: Callable[[str], bytes]) -> list[Finding]:
    """Normalize SARIF 2.x results while binding each result to current source bytes."""
    if not isinstance(doc, Mapping):
        raise ValueError("SARIF document must be an object")
    runs = doc.get("runs")
    if not isinstance(runs, list):
        raise ValueError("SARIF runs must be an array")
    findings: list[Finding] = []
    for run in runs:
        if not isinstance(run, Mapping):
            raise ValueError("SARIF run must be an object")
        results = run.get("results", [])
        if not isinstance(results, list):
            raise ValueError("SARIF results must be an array")
        for result in results:
            if not isinstance(result, Mapping):
                raise ValueError("SARIF result must be an object")
            rule_id = result.get("ruleId")
            if not isinstance(rule_id, str) or not rule_id.strip():
                raise ValueError("SARIF result missing ruleId")
            level = result.get("level", "warning")
            if not isinstance(level, str):
                raise ValueError("SARIF level must be a string")
            severity = _SEVERITY.get(level.lower(), "medium")
            msg = result.get("message", {})
            title = msg.get("text") if isinstance(msg, Mapping) else None
            if not isinstance(title, str) or not title.strip():
                title = rule_id
            locations = result.get("locations")
            if not isinstance(locations, list) or len(locations) != 1:
                raise ValueError("each SARIF result must have exactly one physical location")
            loc = locations[0]
            if not isinstance(loc, Mapping):
                raise ValueError("SARIF location must be an object")
            physical = loc.get("physicalLocation")
            if not isinstance(physical, Mapping):
                raise ValueError("physicalLocation required")
            artifact = physical.get("artifactLocation")
            region = physical.get("region")
            if not isinstance(artifact, Mapping) or not isinstance(region, Mapping):
                raise ValueError("artifactLocation and region required")
            path = canonical_rel_path(artifact.get("uri"))
            start = region.get("startLine")
            end = region.get("endLine", start)
            content = read_file(path)
            if not isinstance(content, (bytes, bytearray)):
                raise ValueError("read_file must return bytes")
            evidence = EvidenceRef.from_bytes(path, bytes(content), start, end)
            findings.append(Finding.build(
                rule_id=rule_id,
                severity=severity,
                title=title,
                evidence=evidence,
                source="sarif",
            ))
    return findings

def validate_unified_diff(patch: str, allowed_paths: Iterable[str], max_bytes: int = MAX_PATCH_BYTES) -> tuple[str, ...]:
    """Return modified paths after enforcing a narrow, existing-file unified-diff shape.

    The validator does not apply the patch. It rejects creates/deletes, renames/copies,
    binary patches, traversal, absolute paths, and files outside the host allowlist.
    """
    if not isinstance(patch, str) or not patch.strip():
        raise ValueError("patch must be non-empty text")
    raw = patch.encode("utf-8")
    if len(raw) > max_bytes:
        raise ValueError("patch exceeds byte budget")
    allowed = {canonical_rel_path(p) for p in allowed_paths}
    if not allowed:
        raise ValueError("allowed_paths must not be empty")
    forbidden_markers = (
        "GIT binary patch", "Binary files ", "rename from ", "rename to ",
        "copy from ", "copy to ", "new file mode ", "deleted file mode ",
        "old mode ", "new mode ",
    )
    for marker in forbidden_markers:
        if marker in patch:
            raise ValueError(f"unsupported diff construct: {marker.strip()}")
    lines = patch.splitlines()
    touched: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("diff --git "):
            parts = line.split(" ")
            if len(parts) != 4 or not parts[2].startswith("a/") or not parts[3].startswith("b/"):
                raise ValueError("malformed diff --git header")
            a_path = canonical_rel_path(parts[2][2:])
            b_path = canonical_rel_path(parts[3][2:])
            if a_path != b_path:
                raise ValueError("renames are not allowed")
            if a_path not in allowed:
                raise ValueError(f"path outside allowlist: {a_path}")
            if i + 2 >= len(lines) or lines[i + 1] != f"--- a/{a_path}" or lines[i + 2] != f"+++ b/{b_path}":
                raise ValueError("diff headers must bind the same existing file")
            touched.append(a_path)
            i += 3
            continue
        if line.startswith("--- ") or line.startswith("+++ "):
            raise ValueError("orphaned unified diff header")
        i += 1
    if not touched:
        raise ValueError("no file diff headers found")
    if len(set(touched)) != len(touched):
        raise ValueError("duplicate file sections are not allowed")
    return tuple(touched)

_ALLOWED_EVENTS = {
    "detected", "triaged", "fix_proposed", "fix_applied", "retested", "closed", "suppressed"
}

class FindingLedger:
    """Append-only hash-chained finding lifecycle ledger."""

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []
        self._states: dict[str, str] = {}

    @property
    def head_hash(self) -> str:
        return self.entries[-1]["event_hash"] if self.entries else "0" * 64

    def state(self, finding_id: str) -> str | None:
        return self._states.get(finding_id)

    def append(self, *, finding_id: str, event: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(finding_id, str) or not finding_id.startswith("hdf_"):
            raise ValueError("invalid finding_id")
        if event not in _ALLOWED_EVENTS:
            raise ValueError("unsupported event")
        payload = {} if payload is None else dict(payload)
        current = self._states.get(finding_id)
        new_state = self._transition(current, event, payload)
        body = {
            "schema": SCHEMA,
            "seq": len(self.entries),
            "prev_hash": self.head_hash,
            "finding_id": finding_id,
            "event": event,
            "payload": payload,
        }
        entry = dict(body)
        entry["event_hash"] = _sha256(_canonical_json(body))
        self.entries.append(entry)
        self._states[finding_id] = new_state
        return dict(entry)

    @staticmethod
    def _transition(current: str | None, event: str, payload: Mapping[str, Any]) -> str:
        if current is None:
            if event != "detected":
                raise ValueError("first event must be detected")
            return "open"
        if current == "open":
            if event == "triaged":
                return "triaged"
            if event == "suppressed":
                if not isinstance(payload.get("reason"), str) or not payload["reason"].strip():
                    raise ValueError("suppression reason required")
                return "suppressed"
        elif current == "triaged":
            if event == "fix_proposed":
                patch_sha = payload.get("patch_sha256")
                if not isinstance(patch_sha, str) or not _HASH_RE.fullmatch(patch_sha):
                    raise ValueError("fix proposal must bind lowercase sha256")
                return "fix_proposed"
            if event == "suppressed":
                if not isinstance(payload.get("reason"), str) or not payload["reason"].strip():
                    raise ValueError("suppression reason required")
                return "suppressed"
        elif current == "fix_proposed":
            if event == "fix_applied":
                applied = payload.get("applied_patch_sha256")
                if not isinstance(applied, str) or not _HASH_RE.fullmatch(applied):
                    raise ValueError("fix application must bind lowercase sha256")
                return "fix_applied"
        elif current == "fix_applied":
            if event == "retested":
                passed = payload.get("passed")
                if not isinstance(passed, bool):
                    raise ValueError("retest passed must be boolean")
                receipt = payload.get("receipt_sha256")
                if not isinstance(receipt, str) or not _HASH_RE.fullmatch(receipt):
                    raise ValueError("retest must bind lowercase sha256")
                return "verified" if passed else "fix_applied"
        elif current == "verified":
            if event == "closed":
                return "closed"
        raise ValueError(f"invalid transition: {current} -> {event}")

    def to_jsonl(self) -> str:
        return "".join(json.dumps(e, sort_keys=True, separators=(",", ":")) + "\n" for e in self.entries)

    @classmethod
    def from_jsonl(cls, text: str) -> "FindingLedger":
        ledger = cls()
        expected_seq = 0
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError("malformed ledger JSON") from exc
            if not isinstance(entry, dict):
                raise ValueError("ledger entry must be an object")
            if entry.get("seq") != expected_seq:
                raise ValueError("non-contiguous ledger sequence")
            if entry.get("prev_hash") != ledger.head_hash:
                raise ValueError("broken ledger hash chain")
            event_hash = entry.get("event_hash")
            body = {k: v for k, v in entry.items() if k != "event_hash"}
            if event_hash != _sha256(_canonical_json(body)):
                raise ValueError("ledger event hash mismatch")
            recreated = ledger.append(
                finding_id=entry.get("finding_id"),
                event=entry.get("event"),
                payload=entry.get("payload"),
            )
            if recreated != entry:
                raise ValueError("ledger entry is non-canonical")
            expected_seq += 1
        return ledger

def finding_to_dict(finding: Finding) -> dict[str, Any]:
    out = asdict(finding)
    out["schema"] = SCHEMA
    return out

def build_fix_packet(finding: Finding, allowed_paths: Iterable[str]) -> dict[str, Any]:
    """Build the host-owned contract given to a fix-proposing model."""
    allowed = tuple(sorted({canonical_rel_path(p) for p in allowed_paths}))
    if not allowed:
        raise ValueError("allowed_paths must not be empty")
    if finding.evidence.path not in allowed:
        raise ValueError("finding evidence path must be explicitly authorized")
    return {
        "schema": SCHEMA,
        "task": "propose_fix",
        "finding": finding_to_dict(finding),
        "allowed_paths": list(allowed),
        "max_patch_bytes": MAX_PATCH_BYTES,
        "response_contract": {
            "exact_keys": ["finding_id", "summary", "patch"],
            "patch_format": "unified_diff_existing_files_only",
        },
    }

def validate_fix_response(response: Mapping[str, Any], packet: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a model fix proposal without applying it or trusting its success claim."""
    if not isinstance(response, Mapping):
        raise ValueError("fix response must be an object")
    if set(response) != {"finding_id", "summary", "patch"}:
        raise ValueError("fix response keys do not match contract")
    finding = packet.get("finding") if isinstance(packet, Mapping) else None
    if not isinstance(finding, Mapping) or response.get("finding_id") != finding.get("finding_id"):
        raise ValueError("finding_id does not match fix packet")
    summary = response.get("summary")
    patch = response.get("patch")
    if not isinstance(summary, str) or not summary.strip() or len(summary.encode("utf-8")) > 4096:
        raise ValueError("summary must be non-empty and bounded")
    if not isinstance(patch, str):
        raise ValueError("patch must be text")
    allowed = packet.get("allowed_paths")
    max_bytes = packet.get("max_patch_bytes")
    if not isinstance(allowed, list) or isinstance(max_bytes, bool) or not isinstance(max_bytes, int):
        raise ValueError("malformed fix packet")
    touched = validate_unified_diff(patch, allowed, max_bytes=max_bytes)
    return {
        "finding_id": response["finding_id"],
        "summary": summary.strip(),
        "patch": patch,
        "patch_sha256": _sha256(patch.encode("utf-8")),
        "touched_paths": list(touched),
    }
