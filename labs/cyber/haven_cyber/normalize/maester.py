"""Normalize Maester `TestResults.json` (Invoke-Maester -OutputJsonFile) into the Haven evidence model.

Field names follow maester365/maester powershell/internal/report/ConvertTo-MtMaesterResult.ps1 (main, read
2026-10-31): top level Result/FailedCount/.../ExecutedAt/TenantId/CurrentVersion and Tests[] with Id, Title, Name,
HelpUrl, Severity, Tag, Result (Passed|Failed|Error|Investigate|Skipped|NotRun), Block and ResultDetail
(TestDescription, TestResult, TestSkipped, SkippedReason, Severity, Service). Test identifiers, severity,
documentation links and remediation text are preserved verbatim; the test suite itself is not reimplemented.

Maester 3.0 results (`SchemaVersion` "2.1", website/docs/result-schema.md on main, read 2026-10-31) keep every 2.x
field but no longer put suite/product tags in `Tag`; rows carry typed `Product`, `Feature`, `Mitre`, `Control` and
`Lifecycle` instead. Both shapes are accepted: typed fields win, tags are the 2.x fallback.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..evidence import ArtifactRef, EvidenceBundle, Finding, Observation, sha256_bytes

STATUS = {"Passed": "pass", "Failed": "fail", "Error": "error", "Investigate": "manual", "Skipped": "skipped",
          "NotRun": "skipped"}
SEVERITY = {"critical": "critical", "high": "high", "medium": "medium", "low": "low", "info": "informational",
            "informational": "informational", "": "medium"}
DOMAIN_BY_PRODUCT = {"entra": "entra", "azure": "azure", "exchange": "m365", "teams": "m365", "sharepoint": "m365",
                     "onedrive": "m365", "defender": "m365", "purview": "m365", "intune": "m365", "ad": "windows-ad",
                     "active-directory": "windows-ad"}
DOMAIN_BY_TAG = {"Entra": "entra", "EIDSCA": "entra", "CA": "entra", "Azure": "azure", "Exchange": "m365",
                 "Teams": "m365", "SharePoint": "m365", "Defender": "m365", "AD": "windows-ad"}


def normalize(path: Path, rel_to: Path | None = None) -> EvidenceBundle:
    raw = Path(path).read_bytes()
    doc = json.loads(raw.decode("utf-8-sig"))
    if "Tests" not in doc:
        raise ValueError("not a Maester TestResults document (no Tests array)")
    art = ArtifactRef(sha256=sha256_bytes(raw), path=str(Path(path).resolve().relative_to(rel_to.resolve())) if rel_to else str(path),
                      source_tool=f"maester {doc.get('CurrentVersion', '')}".strip(), collected_at=str(doc.get("ExecutedAt", "")))
    b = EvidenceBundle(artifacts=[art])
    env = f"tenant:{doc.get('TenantId')}" if doc.get("TenantId") else "unknown"
    for i, t in enumerate(doc["Tests"]):
        detail = t.get("ResultDetail") or {}
        tags = t.get("Tag") or []
        result = t.get("Result", "")
        oid = f"maester-{i:04d}"
        b.observations.append(Observation(oid, art.sha256, f"/Tests/{i}/Result", result, t.get("Id", "")))
        obs = [oid]
        if detail.get("TestResult"):
            b.observations.append(Observation(oid + "-detail", art.sha256, f"/Tests/{i}/ResultDetail/TestResult",
                                              detail["TestResult"]))
            obs.append(oid + "-detail")
        sev = SEVERITY.get(str(detail.get("Severity") or t.get("Severity") or "").lower(), "medium")
        status = STATUS.get(result, "error")
        limitations = []
        if status == "skipped":
            limitations.append("Skipped is not a pass: " + str(detail.get("SkippedReason") or detail.get("TestSkipped") or "no reason recorded"))
        product = str(t.get("Product") or "").lower()
        domain = DOMAIN_BY_PRODUCT.get(product) or next((DOMAIN_BY_TAG[x] for x in tags if x in DOMAIN_BY_TAG), "entra")
        mitre = [m for m in (t.get("Mitre") or []) if m and m != "None"]
        typed_controls = [f"attack:{m}" for m in mitre] + [str(c) for c in (t.get("Control") or [])]
        if t.get("Lifecycle") == "Deprecated":
            limitations.append(f"Test is deprecated upstream; replaced by {t.get('ReplacedBy') or 'unknown'}")
        b.findings.append(Finding(
            id=f"maester:{t.get('Id')}:{i}", title=t.get("Title") or t.get("Name", ""),
            domain=domain,
            service=str(t.get("Feature") or detail.get("Service") or t.get("Block") or ""),
            source_tool=f"maester {doc.get('CurrentVersion', '')} schema {doc.get('SchemaVersion', '2.0')}".strip(),
            source_check_id=str(t.get("Id", "")), resource_id=env, environment=env,
            observation_point="microsoft-graph via Maester/Pester", status=status,
            description=str(detail.get("TestResult") or detail.get("TestDescription") or t.get("Name", "")),
            severity=sev if status == "fail" else "informational", confidence=0.7 if status == "fail" else 0.5,
            collected_at=art.collected_at, observations=obs, artifacts=[art.sha256],
            controls=[f"maester:{t.get('Id')}"] + typed_controls + [f"tag:{x}" for x in tags],
            remediation=str(detail.get("TestDescription") or ""), references=[t["HelpUrl"]] if t.get("HelpUrl") else [],
            limitations=limitations + ["Imported tool result: the raw Graph objects Maester evaluated are not in this artifact."],
            next_validation_step="Re-check against a Graph snapshot with haven.verify (cross-tool corroboration)."))
    return b
