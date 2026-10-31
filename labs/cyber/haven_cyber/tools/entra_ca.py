"""Read-only Entra Conditional Access assessment over a Microsoft Graph-shaped tenant snapshot.

Input is the JSON a read-only collector produces (see graph.py and fixtures/tenants/*.json): Graph v1.0
`conditionalAccessPolicy` objects plus the users, groups, role templates and authentication strengths they
reference, and the operator's list of emergency-access accounts (a Haven input, not a Graph object).

Each rule emits a Finding whose observations are JSON pointers into the snapshot, so the independent verifier
can re-read exactly what the rule relied on. Rule ids are Haven's (HCA-nnn); CROSSWALK maps the equivalent
Maester and Prowler checks so their results can be corroborated or refuted against the same snapshot.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..evidence import ArtifactRef, EvidenceBundle, Finding, Observation, sha256_bytes, utcnow

GLOBAL_ADMIN = "62e90394-69f5-4237-9190-012177145e10"
# Role templates in Microsoft's "Require MFA for administrators" policy template.
ADMIN_ROLES = {
    GLOBAL_ADMIN: "Global Administrator",
    "e8611ab8-c189-46e8-94e1-60213ab1f814": "Privileged Role Administrator",
    "194ae4cb-b126-40b2-bd5b-6091b380977d": "Security Administrator",
    "29232cdf-9323-42fd-ade2-1d097af3e4de": "Exchange Administrator",
    "f28a1f50-f6e7-4571-818b-6a12f2af6b6c": "SharePoint Administrator",
    "fe930be7-5e62-47db-91af-98c3a49a38b1": "User Administrator",
    "b1be1c3e-b65d-4f19-8427-f6fa0d97feb9": "Conditional Access Administrator",
    "9b895d92-2cd3-44c7-9d02-a6ac2d5ea5c3": "Application Administrator",
    "158c047a-c907-4556-b7ef-446551a6b5f7": "Cloud Application Administrator",
    "729827e3-9c14-49f7-bb1b-9608f156bbb8": "Helpdesk Administrator",
    "b0f54661-2d74-4c50-afa3-1ec803f12efe": "Billing Administrator",
    "c4e39bd9-1100-46d3-8c65-fb160da0071f": "Authentication Administrator",
    "7be44c8a-adaf-4e2a-84d6-ab2649e08a13": "Privileged Authentication Administrator",
}
STRENGTH_MFA = "00000000-0000-0000-0000-000000000002"
STRENGTH_PASSWORDLESS = "00000000-0000-0000-0000-000000000003"
STRENGTH_PHISHING_RESISTANT = "00000000-0000-0000-0000-000000000004"
PHISHING_RESISTANT_METHODS = {"fido2", "windowsHelloForBusiness", "x509CertificateMultiFactor"}
LEGACY_CLIENTS = {"exchangeActiveSync", "other"}

CROSSWALK = {  # Haven rule -> equivalent upstream checks (identifiers preserved verbatim)
    "HCA-001": ["prowler:entra_legacy_authentication_blocked"],
    "HCA-002": ["maester:MT.1006", "prowler:entra_admin_users_mfa_enabled"],
    "HCA-003": ["maester:MT.1007"],
    "HCA-004": ["prowler:entra_admin_users_phishing_resistant_mfa_enabled"],
    "HCA-005": ["maester:MT.1005", "prowler:entra_emergency_access_exclusion"],
    "HCA-007": ["prowler:entra_conditional_access_policy_device_code_flow_blocked"],
    "HCA-008": ["prowler:entra_conditional_access_policy_block_high_medium_sign_in_risk"],
    "HCA-010": ["prowler:entra_conditional_access_policy_no_deleted_object_references"],
}
LEARN = "https://learn.microsoft.com/entra/identity/conditional-access/"


@dataclass
class Snapshot:
    data: dict
    artifact: ArtifactRef

    @classmethod
    def load(cls, path: Path, rel_to: Path | None = None) -> "Snapshot":
        raw = Path(path).read_bytes()
        data = json.loads(raw)
        ref = ArtifactRef(sha256=sha256_bytes(raw),
                          path=str(Path(path).resolve().relative_to(rel_to.resolve())) if rel_to else str(path),
                          source_tool=data.get("collector", "graph-snapshot"), collected_at=data.get("collected_at", ""))
        return cls(data, ref)

    @classmethod
    def from_dict(cls, data: dict, label: str = "inline") -> "Snapshot":
        raw = json.dumps(data, sort_keys=True).encode()
        return cls(data, ArtifactRef(sha256=sha256_bytes(raw), path=label, source_tool=data.get("collector", "graph-snapshot"),
                                     collected_at=data.get("collected_at", "")))

    @property
    def policies(self) -> list[dict]:
        return self.data.get("conditionalAccessPolicies", [])

    @property
    def emergency(self) -> set[str]:
        return set(self.data.get("emergencyAccessAccounts", []))

    def group_members(self, gid: str) -> set[str]:
        for g in self.data.get("groups", []):
            if g["id"] == gid:
                return set(g.get("members", []))
        return set()

    def roles_of(self, uid: str) -> set[str]:
        return {a["roleTemplateId"] for a in self.data.get("roleAssignments", []) if a.get("principalId") == uid}

    def is_guest(self, uid: str) -> bool:
        return any(u["id"] == uid and u.get("userType") == "Guest" for u in self.data.get("users", []))

    def known_ids(self) -> set[str]:
        ids = {u["id"] for u in self.data.get("users", [])} | {g["id"] for g in self.data.get("groups", [])}
        return ids | {r["id"] for r in self.data.get("directoryRoleTemplates", [])} | set(ADMIN_ROLES)

    def strength(self, sid: str) -> dict | None:
        for s in self.data.get("authenticationStrengthPolicies", []):
            if s["id"] == sid:
                return s
        return None

    def name(self, oid: str) -> str:
        for u in self.data.get("users", []):
            if u["id"] == oid:
                return u.get("userPrincipalName", oid)
        for g in self.data.get("groups", []):
            if g["id"] == oid:
                return g.get("displayName", oid)
        return ADMIN_ROLES.get(oid, oid)


# ---- policy predicates -------------------------------------------------------------------------------------------

def users(p: dict) -> dict:
    return p.get("conditions", {}).get("users", {}) or {}


def grants(p: dict) -> dict:
    return p.get("grantControls") or {}


def all_users(p: dict) -> bool:
    return "All" in (users(p).get("includeUsers") or [])


def all_apps(p: dict) -> bool:
    return "All" in ((p.get("conditions", {}).get("applications") or {}).get("includeApplications") or [])


def client_types(p: dict) -> set[str]:
    return set(p.get("conditions", {}).get("clientAppTypes") or ["all"])


def covers_all_clients(p: dict) -> bool:
    return "all" in client_types(p)


def blocks(p: dict) -> bool:
    return "block" in (grants(p).get("builtInControls") or [])


def requires_mfa(p: dict, snap: Snapshot) -> bool:
    """True when every way of satisfying the grant includes an MFA-class control."""
    g = grants(p)
    ctrls = set(g.get("builtInControls") or [])
    has_strength = bool((g.get("authenticationStrength") or {}).get("id"))
    if not ctrls and not has_strength:
        return False
    if (g.get("operator") or "OR").upper() == "AND":
        return "mfa" in ctrls or has_strength
    # OR: each alternative must itself be MFA-class; compliantDevice etc. would let a user skip MFA.
    return ctrls <= {"mfa"} and ("mfa" in ctrls or has_strength)


def phishing_resistant(p: dict, snap: Snapshot) -> bool:
    sid = (grants(p).get("authenticationStrength") or {}).get("id")
    if not sid:
        return False
    if sid == STRENGTH_PHISHING_RESISTANT:
        return True
    s = snap.strength(sid)
    combos = set((s or {}).get("allowedCombinations") or [])
    return bool(combos) and all(any(c.startswith(m) for m in PHISHING_RESISTANT_METHODS) for c in combos)


def excluded_principals(p: dict, snap: Snapshot) -> set[str]:
    """Users effectively excluded (direct users plus members of excluded groups)."""
    u = users(p)
    out = set(u.get("excludeUsers") or [])
    for gid in u.get("excludeGroups") or []:
        out |= snap.group_members(gid)
    return out


def in_scope(p: dict, uid: str, snap: Snapshot) -> bool:
    """Would policy p apply to user uid (ignoring non-user conditions)?"""
    u = users(p)
    inc = set(u.get("includeUsers") or [])
    hit = "All" in inc or uid in inc or ("GuestsOrExternalUsers" in inc and snap.is_guest(uid))
    hit = hit or any(uid in snap.group_members(g) for g in u.get("includeGroups") or [])
    hit = hit or bool(snap.roles_of(uid) & set(u.get("includeRoles") or []))
    excluded = uid in excluded_principals(p, snap) or bool(snap.roles_of(uid) & set(u.get("excludeRoles") or []))
    excluded = excluded or ("GuestsOrExternalUsers" in (u.get("excludeUsers") or []) and snap.is_guest(uid))
    return hit and not excluded


def non_emergency_exclusions(p: dict, snap: Snapshot) -> list[str]:
    u = users(p)
    bad = [x for x in (u.get("excludeUsers") or []) if x not in snap.emergency]
    for gid in u.get("excludeGroups") or []:
        members = snap.group_members(gid)
        if not members or not members <= snap.emergency:
            bad.append(gid)
    bad += list(u.get("excludeRoles") or [])
    return bad


def covers_admin_roles(p: dict) -> set[str]:
    u = users(p)
    if all_users(p):
        return set(ADMIN_ROLES) - set(u.get("excludeRoles") or [])
    return set(u.get("includeRoles") or []) & set(ADMIN_ROLES)


# ---- assessment --------------------------------------------------------------------------------------------------

class Assessor:
    def __init__(self, snap: Snapshot, environment: str | None = None):
        self.snap = snap
        self.env = environment or f"{snap.data.get('source', 'synthetic')}:{snap.data.get('tenant', {}).get('displayName', 'unknown')}"
        self.bundle = EvidenceBundle(artifacts=[snap.artifact])
        self._obs = 0

    def obs(self, pointer: str, value, note: str = "") -> str:
        self._obs += 1
        oid = f"obs-{self._obs:03d}"
        self.bundle.observations.append(Observation(oid, self.snap.artifact.sha256, pointer, value, note))
        return oid

    def policy_obs(self, i: int, p: dict, fields=("state",)) -> list[str]:
        out = []
        for f in fields:
            if f == "state":
                out.append(self.obs(f"/conditionalAccessPolicies/{i}/state", p.get("state"), p.get("displayName", "")))
            elif f == "grant":
                out.append(self.obs(f"/conditionalAccessPolicies/{i}/grantControls", p.get("grantControls"), p.get("displayName", "")))
            elif f == "users":
                out.append(self.obs(f"/conditionalAccessPolicies/{i}/conditions/users", users(p), p.get("displayName", "")))
            elif f == "clients":
                out.append(self.obs(f"/conditionalAccessPolicies/{i}/conditions/clientAppTypes",
                                    p.get("conditions", {}).get("clientAppTypes"), p.get("displayName", "")))
        return out

    def add(self, rule: str, title: str, status: str, severity: str, description: str, obs: list[str],
            remediation: str, ref: str, resource: str = "conditionalAccess", confidence: float = 0.9,
            limitations: list[str] | None = None, next_step: str = "", controls: list[str] | None = None):
        self.bundle.findings.append(Finding(
            id=f"{rule}:{resource}", title=title, domain="entra", service="conditional-access",
            source_tool="haven.entra_ca", source_check_id=rule, resource_id=resource, environment=self.env,
            observation_point="microsoft-graph:v1.0 snapshot", status=status, description=description,
            severity=severity if status == "fail" else "informational", confidence=confidence,
            collected_at=self.snap.artifact.collected_at or utcnow(), observations=obs,
            artifacts=[self.snap.artifact.sha256], controls=(controls or []) + CROSSWALK.get(rule, []),
            remediation=remediation, references=[LEARN + ref] if ref else [], limitations=limitations or [],
            next_validation_step=next_step))

    def enabled_grants_obs(self) -> list[str]:
        """For absence claims: record the grant controls of every enabled policy that was scanned."""
        return [self.obs(f"/conditionalAccessPolicies/{i}/grantControls", p.get("grantControls"), p.get("displayName", ""))
                for i, p in self.enabled()]

    def enabled(self):
        return [(i, p) for i, p in enumerate(self.snap.policies) if p.get("state") == "enabled"]

    def run(self) -> EvidenceBundle:
        for rule in (self.hca001, self.hca002, self.hca003, self.hca004, self.hca005, self.hca006, self.hca007,
                     self.hca008, self.hca009, self.hca010):
            rule()
        return self.bundle

    def hca001(self):
        hits = [(i, p) for i, p in self.enabled() if blocks(p) and all_users(p) and all_apps(p)
                and LEGACY_CLIENTS <= client_types(p)]
        near = [(i, p) for i, p in enumerate(self.snap.policies)
                if blocks(p) and LEGACY_CLIENTS & client_types(p) and (i, p) not in hits]
        if hits:
            i, p = hits[0]
            gaps = non_emergency_exclusions(p, self.snap)
            obs = self.policy_obs(i, p, ("state", "users", "clients", "grant"))
            if gaps:
                self.add("HCA-001", "Legacy authentication block has non-emergency exclusions", "fail", "medium",
                         f"Policy '{p.get('displayName')}' ({p['id']}) blocks legacy clients but excludes "
                         f"{', '.join(self.snap.name(g) for g in gaps)}, which are not emergency-access accounts.",
                         obs, "Remove the exclusions or migrate the excluded accounts off legacy protocols.",
                         "policy-block-legacy-authentication", resource=p["id"], confidence=0.85)
            else:
                self.add("HCA-001", "Legacy authentication is blocked for all users", "pass", "critical",
                         f"Enabled policy '{p.get('displayName')}' ({p['id']}) blocks exchangeActiveSync and other clients for all users and apps.",
                         obs, "", "policy-block-legacy-authentication", resource=p["id"])
            return
        obs = []
        desc = "No enabled Conditional Access policy blocks both legacy client types (exchangeActiveSync, other) for all users and all apps."
        for i, p in near:
            obs += self.policy_obs(i, p, ("state", "clients", "users"))
        if near:
            desc += " Candidate policies that do not qualify: " + "; ".join(
                f"'{p.get('displayName')}' ({p['id']}, state={p.get('state')}, clients={sorted(client_types(p))})" for _, p in near)
        self.add("HCA-001", "Legacy authentication is not blocked", "fail", "critical", desc, obs,
                 "Create or enable a policy: all users (exclude emergency accounts), all apps, client apps "
                 "exchangeActiveSync + other, grant Block. Validate in report-only first using sign-in logs.",
                 "policy-block-legacy-authentication",
                 limitations=["Exchange Online authentication policies can also disable basic auth per protocol; they are not in a Graph CA snapshot."],
                 next_step="Query sign-in logs for clientAppUsed in legacy protocols over the last 30 days.")

    def _mfa_rule(self, rule: str, title_ok: str, title_bad: str, scope_fn, ref: str, sev: str, strength_fn=None):
        req = strength_fn or requires_mfa
        cand = [(i, p) for i, p in self.enabled() if scope_fn(p) and all_apps(p) and covers_all_clients(p) and req(p, self.snap)]
        if cand:
            clean = [(i, p) for i, p in cand if not non_emergency_exclusions(p, self.snap)]
            i, p = (clean or cand)[0]
            obs = self.policy_obs(i, p, ("state", "users", "grant"))
            if clean:
                self.add(rule, title_ok, "pass", sev, f"Enabled policy '{p.get('displayName')}' ({p['id']}) satisfies the requirement.",
                         obs, "", ref, resource=p["id"])
            else:
                gaps = non_emergency_exclusions(p, self.snap)
                self.add(rule, title_bad + " (exclusion gap)", "fail", sev,
                         f"Policy '{p.get('displayName')}' ({p['id']}) would satisfy the requirement, but it excludes "
                         f"{', '.join(self.snap.name(g) for g in gaps)}; those principals are not covered.",
                         obs, "Remove non-emergency exclusions, or cover the excluded principals with an equivalent policy.",
                         ref, resource=p["id"], confidence=0.85,
                         next_step="List members of each excluded group and check whether any hold the targeted roles.")
            return
        near = [(i, p) for i, p in enumerate(self.snap.policies) if scope_fn(p) and (requires_mfa(p, self.snap) or grants(p).get("authenticationStrength"))]
        obs = []
        for i, p in near:
            obs += self.policy_obs(i, p, ("state", "grant"))
        reasons = []
        for _, p in near:
            why = []
            if p.get("state") != "enabled":
                why.append(f"state={p.get('state')}")
            if not all_apps(p):
                why.append("not all apps")
            if not covers_all_clients(p):
                why.append(f"clientAppTypes={sorted(client_types(p))}")
            if not req(p, self.snap):
                why.append("grant does not require a phishing-resistant authentication strength" if strength_fn
                           else "grant can be satisfied without MFA (OR with a non-MFA control, or no MFA control)")
            reasons.append(f"'{p.get('displayName')}' ({p['id']}): {', '.join(why)}")
        self.add(rule, title_bad, "fail", sev,
                 "No enabled policy meets the requirement." + (" Near misses: " + "; ".join(reasons) if reasons else ""),
                 obs, "Create or enable a policy that targets the scope for all cloud apps and all client app types with the required grant.",
                 ref, confidence=0.9)

    def hca002(self):
        self._mfa_rule("HCA-002", "MFA is required for administrator roles", "MFA is not enforced for administrator roles",
                       lambda p: GLOBAL_ADMIN in covers_admin_roles(p), "policy-old-require-mfa-admin", "high")

    def hca003(self):
        self._mfa_rule("HCA-003", "MFA is required for all users", "MFA is not enforced for all users",
                       all_users, "policy-all-users-mfa-strength", "high")

    def hca004(self):
        self._mfa_rule("HCA-004", "Phishing-resistant MFA is required for administrators",
                       "Phishing-resistant MFA is not required for administrators",
                       lambda p: GLOBAL_ADMIN in covers_admin_roles(p), "policy-admin-phish-resistant-mfa", "high",
                       strength_fn=phishing_resistant)

    def hca005(self):
        em = self.snap.emergency
        if not em:
            self.add("HCA-005", "No emergency-access accounts are declared", "manual", "high",
                     "The snapshot lists no emergency-access accounts, so lockout protection cannot be assessed.",
                     [self.obs("/emergencyAccessAccounts", [], "absent or empty")],
                     "Declare the tenant's emergency-access accounts (two cloud-only accounts) in the collector configuration.",
                     "../role-based-access-control/security-emergency-access", confidence=0.5)
            return
        missing = []
        obs = []
        for i, p in self.enabled():
            lacking = {x for x in em if in_scope(p, x, self.snap)}
            if lacking:
                missing.append((p, lacking))
                obs += self.policy_obs(i, p, ("users", "grant"))
        if missing:
            self.add("HCA-005", "Emergency-access accounts are not excluded from all enforcing policies", "fail", "high",
                     "; ".join(f"'{p.get('displayName')}' ({p['id']}) applies to {', '.join(sorted(self.snap.name(x) for x in lack))}"
                               f"{' and BLOCKS' if blocks(p) else ''}" for p, lack in missing),
                     obs, "Exclude the emergency-access accounts (or a group containing only them) from every Conditional Access policy; monitor their sign-ins.",
                     "../role-based-access-control/security-emergency-access",
                     next_step="Confirm the accounts are cloud-only, use FIDO2 or certificate credentials and have sign-in alerts.")
        else:
            self.add("HCA-005", "Emergency-access accounts are excluded from every enabled policy", "pass", "high",
                     f"{len(em)} emergency-access account(s) are excluded from all {len(self.enabled())} enabled policies.",
                     [self.obs("/emergencyAccessAccounts", sorted(em))], "", "../role-based-access-control/security-emergency-access")

    def hca006(self):
        ro = [(i, p) for i, p in enumerate(self.snap.policies) if p.get("state") == "enabledForReportingButNotEnforced"]
        if ro:
            self.add("HCA-006", "Report-only policies enforce nothing", "manual", "low",
                     "Report-only policies: " + "; ".join(f"'{p.get('displayName')}' ({p['id']})" for _, p in ro)
                     + ". They log what they would do but never block or challenge.",
                     [o for i, p in ro for o in self.policy_obs(i, p)], "Review report-only impact in sign-in logs, then enable or delete.",
                     "concept-conditional-access-report-only", confidence=1.0)

    def hca007(self):
        hits = [(i, p) for i, p in self.enabled() if blocks(p) and all_users(p) and "deviceCodeFlow" in
                (((p.get("conditions") or {}).get("authenticationFlows") or {}).get("transferMethods") or "")]
        if hits:
            i, p = hits[0]
            self.add("HCA-007", "Device code flow is blocked", "pass", "high", f"'{p.get('displayName')}' ({p['id']}) blocks device code flow.",
                     self.policy_obs(i, p, ("state", "grant")), "", "policy-block-authentication-flows", resource=p["id"])
        else:
            self.add("HCA-007", "Device code flow is not restricted", "fail", "medium",
                     "No enabled policy blocks the deviceCodeFlow authentication flow for all users. Device-code phishing remains possible.",
                     self.enabled_grants_obs(),
                     "Block device code flow for all users except a documented exception group for devices that need it.",
                     "policy-block-authentication-flows", confidence=0.8)

    def hca008(self):
        hits = [(i, p) for i, p in self.enabled() if "high" in (p.get("conditions", {}).get("signInRiskLevels") or [])
                and (blocks(p) or requires_mfa(p, self.snap))]
        if hits:
            i, p = hits[0]
            self.add("HCA-008", "High sign-in risk is challenged or blocked", "pass", "medium",
                     f"'{p.get('displayName')}' ({p['id']}) acts on high sign-in risk.", self.policy_obs(i, p, ("state", "grant")),
                     "", "policy-risk-based-sign-in", resource=p["id"])
        else:
            self.add("HCA-008", "No sign-in risk policy", "fail", "medium",
                     "No enabled policy requires MFA or blocks on high sign-in risk.",
                     self.enabled_grants_obs(),
                     "Create a sign-in risk policy (requires Entra ID P2).", "policy-risk-based-sign-in", confidence=0.8,
                     limitations=["Requires Entra ID P2; the snapshot does not record licensing."])

    def hca009(self):
        for i, p in self.enabled():
            u = users(p)
            for gid in u.get("excludeGroups") or []:
                members = self.snap.group_members(gid)
                if len(members) > 5 and not members <= self.snap.emergency:
                    self.add("HCA-009", "Broad group excluded from an enforcing policy", "fail", "medium",
                             f"'{p.get('displayName')}' ({p['id']}) excludes group {self.snap.name(gid)} with {len(members)} members.",
                             [self.obs(f"/conditionalAccessPolicies/{i}/conditions/users/excludeGroups", u.get("excludeGroups"))],
                             "Replace broad exclusions with narrowly scoped, time-bound exception groups under access review.",
                             "plan-conditional-access", resource=p["id"], confidence=0.7)

    def hca010(self):
        known = self.snap.known_ids()
        special = {"All", "None", "GuestsOrExternalUsers"}
        for i, p in enumerate(self.snap.policies):
            u = users(p)
            dangling = [x for k in ("includeUsers", "excludeUsers", "includeGroups", "excludeGroups", "includeRoles", "excludeRoles")
                        for x in (u.get(k) or []) if x not in known and x not in special]
            if dangling:
                self.add("HCA-010", "Policy references objects that do not exist", "fail", "low",
                         f"'{p.get('displayName')}' ({p['id']}) references unknown object ids {dangling}.",
                         self.policy_obs(i, p, ("users",)), "Remove deleted objects from the policy and re-check its intended scope.",
                         "troubleshoot-conditional-access", resource=p["id"], confidence=0.6,
                         limitations=["The snapshot may be partial; an id absent here may still exist in the tenant."])


def assess(path: Path, rel_to: Path | None = None) -> EvidenceBundle:
    return Assessor(Snapshot.load(path, rel_to)).run()


def assess_dict(data: dict, label: str = "inline") -> EvidenceBundle:
    return Assessor(Snapshot.from_dict(data, label)).run()
