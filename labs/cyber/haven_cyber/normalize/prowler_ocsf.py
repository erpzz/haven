"""Normalize Prowler OCSF output (`prowler <provider> -M json-ocsf`) into the Haven evidence model.

Prowler writes a JSON array of OCSF Detection Finding objects (prowler/lib/outputs/ocsf/ocsf.py, main, read
2026-10-31): message, status_code (PASS|FAIL|MANUAL), status_detail, severity, finding_info{uid,title,desc},
resources[{uid,name,type,region,group{name}}], metadata{event_code=CheckID, product{name,version}, tenant_uid},
remediation{desc,references}, risk_details, cloud{provider,account{uid}}, unmapped{related_url,compliance,...}.
Any OCSF Detection Finding (class_uid 2004) from another product is accepted the same way.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..evidence import ArtifactRef, EvidenceBundle, Finding, Observation, sha256_bytes

STATUS = {"PASS": "pass", "FAIL": "fail", "MANUAL": "manual", "MUTED": "skipped"}
SEVERITY = {"critical": "critical", "high": "high", "medium": "medium", "low": "low", "informational": "informational",
            "info": "informational", "unknown": "medium", "other": "medium"}
DOMAIN = {"m365": "m365", "azure": "azure", "aws": "aws", "gcp": "gcp", "kubernetes": "kubernetes", "github": "appsec"}


def normalize(path: Path, rel_to: Path | None = None) -> EvidenceBundle:
    raw = Path(path).read_bytes()
    items = json.loads(raw)
    if isinstance(items, dict):
        items = [items]
    art = ArtifactRef(sha256=sha256_bytes(raw), path=str(Path(path).resolve().relative_to(rel_to.resolve())) if rel_to else str(path),
                      source_tool="prowler", collected_at=str(items[0].get("time_dt", "")) if items else "")
    b = EvidenceBundle(artifacts=[art])
    for i, it in enumerate(items):
        if it.get("class_uid") not in (None, 2004):
            continue
        md = it.get("metadata") or {}
        fi = it.get("finding_info") or {}
        res = (it.get("resources") or [{}])[0]
        provider = (it.get("unmapped") or {}).get("provider") or (it.get("cloud") or {}).get("provider") or ""
        check = md.get("event_code", "")
        domain = "entra" if check.startswith("entra_") else DOMAIN.get(provider, provider or "unknown")
        oid = f"prowler-{i:04d}"
        b.observations += [Observation(oid, art.sha256, f"/{i}/status_code", it.get("status_code")),
                           Observation(oid + "-detail", art.sha256, f"/{i}/status_detail", it.get("status_detail"))]
        status = STATUS.get(str(it.get("status_code", "")).upper(), "error")
        sev = SEVERITY.get(str(it.get("severity", "")).lower(), "medium")
        rem = it.get("remediation") or {}
        unm = it.get("unmapped") or {}
        compliance = unm.get("compliance") or {}
        controls = [f"prowler:{check}"] + [f"{fw}:{c}" for fw, cs in compliance.items() for c in (cs or [])]
        version = (md.get("product") or {}).get("version", "")
        b.findings.append(Finding(
            id=f"prowler:{fi.get('uid', i)}", title=fi.get("title", ""), domain=domain,
            service=(res.get("group") or {}).get("name", ""), source_tool=f"prowler {version}".strip(),
            source_check_id=check, resource_id=res.get("uid") or res.get("name", ""),
            environment=f"{provider}:{((it.get('cloud') or {}).get('account') or {}).get('uid') or md.get('tenant_uid', '')}",
            observation_point=f"{provider} API via Prowler", status=status,
            description=it.get("status_detail") or it.get("message", ""), severity=sev if status == "fail" else "informational",
            confidence=0.7 if status == "fail" else 0.5, collected_at=str(it.get("time_dt", "")),
            observations=[oid, oid + "-detail"], artifacts=[art.sha256], controls=controls,
            remediation=rem.get("desc", ""), references=list(rem.get("references") or []) + ([unm["related_url"]] if unm.get("related_url") else []),
            limitations=["Imported tool result: Prowler's verdict, not the raw configuration it evaluated."],
            next_validation_step="Re-check against a Graph/ARM snapshot with haven.verify (cross-tool corroboration)."))
    return b
