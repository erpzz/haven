"""Independent evidence verifier.

Three layers, each recorded in `Finding.verification_notes`:

1. Completeness: required fields, valid enums, a failing finding has observations, artifacts and remediation.
2. Consistency: every observation's artifact is in the bundle, its bytes still hash to the recorded sha256, and the
   JSON pointer still resolves to the recorded value (catches tampering, stale artifacts and fabricated pointers).
3. Re-derivation: when a raw Graph snapshot is available, the claim is re-checked with this module's own
   predicates, written separately from the assessor in tools/entra_ca.py so a bug in one does not silently
   confirm itself. Agreement -> `corroborated`; disagreement -> `refuted`. Imported Maester/Prowler verdicts are
   re-checked the same way through the crosswalk of equivalent checks.

The verifier never sets `confirmed`; that needs a human or a controlled lab test.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .evidence import SEVERITIES, STATUSES, VERIFICATION, EvidenceBundle, Finding, json_pointer_get, sha256_bytes

GA = "62e90394-69f5-4237-9190-012177145e10"
PHISH = "00000000-0000-0000-0000-000000000004"

# Upstream check -> (Haven rule the verifier can re-derive, criterion level). Kept here (not imported) on purpose.
# "exists": the upstream check asks whether at least one qualifying enabled policy exists.
# "covered": it asks whether every in-scope principal is actually covered (exclusions resolved). Haven's own HCA rules
# are judged at "covered". Comparing an upstream verdict at the wrong level would call a criterion difference a lie.
EQUIVALENT = {
    "entra_legacy_authentication_blocked": ("HCA-001", "exists"), "MT.1006": ("HCA-002", "exists"),
    "entra_admin_users_mfa_enabled": ("HCA-002", "exists"), "MT.1007": ("HCA-003", "exists"),
    "entra_admin_users_phishing_resistant_mfa_enabled": ("HCA-004", "exists"), "MT.1005": ("HCA-005", "covered"),
    "entra_emergency_access_exclusion": ("HCA-005", "covered"),
    "entra_conditional_access_policy_device_code_flow_blocked": ("HCA-007", "exists"),
}


@dataclass
class Report:
    checked: int = 0
    by_status: dict = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)

    def ok(self) -> bool:
        return not self.problems


# ---- independent predicates over a Graph snapshot ----------------------------------------------------------------

def _members(snap, gid):
    return next((set(g.get("members", [])) for g in snap.get("groups", []) if g["id"] == gid), set())


def _excluded(pol, snap):
    u = pol["conditions"]["users"]
    out = set(u.get("excludeUsers") or [])
    for g in u.get("excludeGroups") or []:
        out |= _members(snap, g)
    return out


def _roles(snap, uid):
    return {a["roleTemplateId"] for a in snap.get("roleAssignments", []) if a["principalId"] == uid}


def _applies(pol, uid, snap):
    u = pol["conditions"]["users"]
    if uid in _excluded(pol, snap) or _roles(snap, uid) & set(u.get("excludeRoles") or []):
        return False
    if "GuestsOrExternalUsers" in (u.get("excludeUsers") or []) and any(x["id"] == uid and x.get("userType") == "Guest" for x in snap.get("users", [])):
        return False
    return ("All" in (u.get("includeUsers") or []) or uid in (u.get("includeUsers") or [])
            or any(uid in _members(snap, g) for g in u.get("includeGroups") or [])
            or bool(_roles(snap, uid) & set(u.get("includeRoles") or [])))


def _on(pol):
    return pol.get("state") == "enabled"


def _all_apps(pol):
    return "All" in ((pol["conditions"].get("applications") or {}).get("includeApplications") or [])


def _ctrls(pol):
    g = pol.get("grantControls") or {}
    return set(g.get("builtInControls") or []), (g.get("operator") or "OR").upper(), ((g.get("authenticationStrength") or {}).get("id"))


def _forces_mfa(pol):
    c, op, strength = _ctrls(pol)
    if op == "AND":
        return "mfa" in c or bool(strength)
    return (c == {"mfa"} or (not c and bool(strength)) or (c == {"mfa"} and bool(strength)))


def _all_clients(pol):
    return "all" in (pol["conditions"].get("clientAppTypes") or ["all"])


def recheck(rule: str, snap: dict) -> tuple[bool, bool] | None:
    """Re-derive a rule from the raw snapshot: (a qualifying enabled policy exists, every in-scope principal is covered).
    None when this rule cannot be re-derived."""
    pols = [p for p in snap.get("conditionalAccessPolicies", []) if _on(p)]
    em = set(snap.get("emergencyAccessAccounts", []))
    members = [u["id"] for u in snap.get("users", []) if u.get("userType") != "Guest" and u["id"] not in em]
    if rule == "HCA-001":
        q = [p for p in pols if "block" in _ctrls(p)[0] and {"exchangeActiveSync", "other"} <= set(p["conditions"].get("clientAppTypes") or [])
             and _all_apps(p) and "All" in (p["conditions"]["users"].get("includeUsers") or [])]
        return bool(q), all(any(_applies(p, x, snap) for p in q) for x in members)
    if rule in ("HCA-002", "HCA-004"):
        good = (lambda p: _ctrls(p)[2] == PHISH) if rule == "HCA-004" else _forces_mfa
        q = [p for p in pols if _all_apps(p) and _all_clients(p) and good(p)
             and (GA in (p["conditions"]["users"].get("includeRoles") or []) or "All" in (p["conditions"]["users"].get("includeUsers") or []))]
        admins = [a["principalId"] for a in snap.get("roleAssignments", []) if a["roleTemplateId"] == GA and a["principalId"] not in em]
        return bool(q), all(any(_applies(p, a, snap) for p in q) for a in admins)
    if rule == "HCA-003":
        q = [p for p in pols if _all_apps(p) and _all_clients(p) and _forces_mfa(p) and "All" in (p["conditions"]["users"].get("includeUsers") or [])]
        return bool(q), all(any(_applies(p, x, snap) for p in q) for x in members)
    if rule == "HCA-005":
        ok = bool(em) and not any(_applies(p, x, snap) for p in pols for x in em)
        return ok, ok
    if rule == "HCA-007":
        q = [p for p in pols if "block" in _ctrls(p)[0] and "deviceCodeFlow" in str((p["conditions"].get("authenticationFlows") or {}).get("transferMethods"))]
        return bool(q), all(any(_applies(p, x, snap) for p in q) for x in members)
    return None


# ---- verification ---------------------------------------------------------------------------------------------------

def load_artifact(sha: str, bundle: EvidenceBundle, root: Path, inline: dict | None = None):
    if inline and sha in inline:
        return inline[sha], None
    ref = next((a for a in bundle.artifacts if a.sha256 == sha), None)
    if ref is None:
        return None, "artifact not declared in bundle"
    p = Path(ref.path) if Path(ref.path).is_absolute() else root / ref.path
    if not p.exists():
        return None, f"artifact file missing: {ref.path}"
    data = p.read_bytes()
    if sha256_bytes(data) != sha:
        return None, f"artifact hash mismatch: {ref.path} changed since collection"
    return json.loads(data.decode("utf-8-sig")), None


def verify(bundle: EvidenceBundle, root: Path, snapshot: dict | None = None, inline: dict | None = None) -> Report:
    rep = Report()
    obs = {o.id: o for o in bundle.observations}
    cache: dict[str, object] = {}
    for f in bundle.findings:
        rep.checked += 1
        notes: list[str] = []
        problems = _completeness(f)
        for oid in f.observations:
            o = obs.get(oid)
            if o is None:
                problems.append(f"observation {oid} not in bundle")
                continue
            if o.artifact not in cache:
                cache[o.artifact], err = load_artifact(o.artifact, bundle, root, inline)
                if err:
                    problems.append(err)
            doc = cache.get(o.artifact)
            if doc is None:
                continue
            try:
                actual = json_pointer_get(doc, o.pointer)
            except KeyError:
                problems.append(f"{oid}: pointer {o.pointer} does not resolve")
                continue
            if actual != o.value:
                problems.append(f"{oid}: value at {o.pointer} differs from recorded observation")
        if problems:
            f.verification = "insufficient_evidence"
            notes += problems
            rep.problems += [f"{f.id}: {p}" for p in problems]
        else:
            notes.append("complete; all observations re-read from their artifacts")
            rule, level = (f.source_check_id, "covered") if f.source_check_id.startswith("HCA-") else EQUIVALENT.get(f.source_check_id, (None, None))
            derived = recheck(rule, snapshot) if (rule and snapshot is not None and f.status in ("pass", "fail")) else None
            if derived is None:
                f.verification = "reported"
                if rule and snapshot is None:
                    notes.append(f"re-derivation possible via {rule} but no raw snapshot supplied")
                elif not rule:
                    notes.append("no independent re-derivation available for this check")
            else:
                exists, covered = derived
                verdict = exists if level == "exists" else covered
                if verdict == (f.status == "pass"):
                    f.verification = "corroborated"
                    notes.append(f"independently re-derived via {rule} ({level}): control {'present' if verdict else 'absent'}")
                else:
                    f.verification = "refuted"
                    notes.append(f"independent re-derivation via {rule} ({level}) disagrees: control {'present' if verdict else 'absent'} in snapshot")
                if level == "exists" and exists and not covered:
                    notes.append(f"criterion gap: a qualifying policy exists but not every in-scope principal is covered (see {rule}); "
                                 "a pass at this level can hide an exclusion gap")
        f.verification_notes = notes
        rep.by_status[f.verification] = rep.by_status.get(f.verification, 0) + 1
    return rep


def _completeness(f: Finding) -> list[str]:
    errs = []
    for name in ("id", "title", "domain", "source_tool", "source_check_id", "resource_id", "environment", "status",
                 "description", "severity", "collected_at"):
        if not getattr(f, name):
            errs.append(f"missing {name}")
    if f.severity and f.severity not in SEVERITIES:
        errs.append(f"severity {f.severity!r} invalid")
    if f.status and f.status not in STATUSES:
        errs.append(f"status {f.status!r} invalid")
    if f.verification not in VERIFICATION:
        errs.append(f"verification {f.verification!r} invalid")
    if not 0 <= f.confidence <= 1:
        errs.append("confidence outside 0..1")
    if f.verification == "confirmed":
        errs.append("tools may not self-certify 'confirmed'")
    if f.status == "fail":
        if not f.observations:
            errs.append("failing finding has no observations")
        if not f.artifacts:
            errs.append("failing finding has no raw artifact")
        if not f.remediation:
            errs.append("failing finding has no remediation")
    return errs
