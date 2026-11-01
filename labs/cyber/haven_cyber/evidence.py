"""Common evidence model: raw observations are kept apart from inferred findings.

An Observation is something a tool saw, with a pointer into the raw artifact it came from. A Finding is a
conclusion drawn from one or more observations. A tool reporting a problem gives `verification == "reported"`;
only the independent verifier (haven_cyber.verifier) can move it to `corroborated` or `refuted`, and only a
human or a controlled lab test can set `confirmed`. See docs/research/SECURITY_EVIDENCE_SCHEMA.md.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "haven-cyber-evidence-v1"
SEVERITIES = ("critical", "high", "medium", "low", "informational")
VERIFICATION = ("reported", "corroborated", "refuted", "insufficient_evidence", "confirmed")
STATUSES = ("fail", "pass", "manual", "error", "skipped", "not_applicable")


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class ArtifactRef:
    """A raw artifact (tool output, API snapshot) identified by content hash."""
    sha256: str
    path: str  # where the artifact can be re-read; relative to labs/cyber when it is a fixture
    media_type: str = "application/json"
    source_tool: str = ""
    collected_at: str = ""

    @classmethod
    def from_file(cls, path: Path, source_tool: str, collected_at: str | None = None, rel_to: Path | None = None):
        data = Path(path).read_bytes()
        shown = str(Path(path).resolve().relative_to(rel_to.resolve())) if rel_to else str(path)
        return cls(sha256=sha256_bytes(data), path=shown, source_tool=source_tool,
                   collected_at=collected_at or utcnow())


@dataclass
class Observation:
    """What a tool actually saw. `pointer` is an RFC 6901 JSON pointer into the artifact; `value` is what was there."""
    id: str
    artifact: str  # ArtifactRef.sha256
    pointer: str
    value: Any
    note: str = ""


@dataclass
class Finding:
    id: str
    title: str
    domain: str  # entra | azure | m365 | windows-ad | linux | macos | network | detection
    service: str
    source_tool: str
    source_check_id: str  # the tool's own identifier, preserved verbatim (e.g. MT.1005, prowler CheckID)
    resource_id: str
    environment: str  # e.g. "synthetic:contoso-fixture", "tenant:<guid>", "lab:<name>"
    observation_point: str  # where the data was collected from (API, host, sensor)
    status: str  # one of STATUSES, as the tool reported it
    description: str
    severity: str
    confidence: float  # 0..1: how strongly the observations support the conclusion
    collected_at: str
    observations: list[str] = field(default_factory=list)  # Observation ids
    artifacts: list[str] = field(default_factory=list)  # ArtifactRef sha256s
    controls: list[str] = field(default_factory=list)  # e.g. "MITRE:T1110.003", "CIS-M365:5.2.2.3", "MT.1005"
    remediation: str = ""
    references: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    next_validation_step: str = ""
    verification: str = "reported"
    verification_notes: list[str] = field(default_factory=list)
    inferred: bool = True  # findings are conclusions; set False only for direct restatements of an observation


@dataclass
class EvidenceBundle:
    schema: str = SCHEMA_VERSION
    artifacts: list[ArtifactRef] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def to_json(self, **kw) -> str:
        return json.dumps(self.to_dict(), indent=kw.pop("indent", 2), default=str, **kw)

    @classmethod
    def from_dict(cls, d: dict) -> "EvidenceBundle":
        return cls(schema=d.get("schema", SCHEMA_VERSION),
                   artifacts=[ArtifactRef(**a) for a in d.get("artifacts", [])],
                   observations=[Observation(**o) for o in d.get("observations", [])],
                   findings=[Finding(**f) for f in d.get("findings", [])])

    def merge(self, other: "EvidenceBundle") -> "EvidenceBundle":
        seen = {a.sha256 for a in self.artifacts}
        self.artifacts += [a for a in other.artifacts if a.sha256 not in seen]
        self.observations += other.observations
        self.findings += other.findings
        return self


def json_pointer_get(doc: Any, pointer: str) -> Any:
    """Resolve an RFC 6901 pointer; raises KeyError when it does not resolve."""
    if pointer in ("", "/"):
        return doc
    if not pointer.startswith("/"):
        raise KeyError(f"pointer must start with '/': {pointer!r}")
    cur = doc
    for raw in pointer[1:].split("/"):
        part = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, list):
            if not part.isdigit() or int(part) >= len(cur):
                raise KeyError(pointer)
            cur = cur[int(part)]
        elif isinstance(cur, dict):
            if part not in cur:
                raise KeyError(pointer)
            cur = cur[part]
        else:
            raise KeyError(pointer)
    return cur


def finding_json_schema() -> dict:
    """JSON Schema (draft 2020-12) for one Finding, generated from the dataclass so the two cannot drift."""
    props: dict[str, Any] = {}
    for f in dataclasses.fields(Finding):
        t = f.type if isinstance(f.type, str) else getattr(f.type, "__name__", "string")
        if t.startswith("list"):
            props[f.name] = {"type": "array", "items": {"type": "string"}}
        elif t == "float":
            props[f.name] = {"type": "number", "minimum": 0, "maximum": 1}
        elif t == "bool":
            props[f.name] = {"type": "boolean"}
        else:
            props[f.name] = {"type": "string"}
    props["severity"]["enum"] = list(SEVERITIES)
    props["verification"]["enum"] = list(VERIFICATION)
    props["status"]["enum"] = list(STATUSES)
    required = [f.name for f in dataclasses.fields(Finding)
                if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING]
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": SCHEMA_VERSION + "/finding",
            "type": "object", "properties": props, "required": required, "additionalProperties": False}
