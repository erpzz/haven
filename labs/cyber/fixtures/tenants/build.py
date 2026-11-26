"""Generate the synthetic Graph-shaped tenant snapshots used by tests, the vertical slice and the evaluation.

All identities are fictional (contoso.example, RFC 2606). Object ids are deterministic UUIDv5 values so fixtures
are reproducible. Run: python3 fixtures/tenants/build.py  (writes the *.json files next to this script).
"""
from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path

NS = uuid.UUID("6f1b2c1e-1d1a-4c55-9e0e-6d6176656e01")
GA = "62e90394-69f5-4237-9190-012177145e10"
PRA = "e8611ab8-c189-46e8-94e1-60213ab1f814"
SECADM = "194ae4cb-b126-40b2-bd5b-6091b380977d"
PHISH = "00000000-0000-0000-0000-000000000004"


def oid(name: str) -> str:
    return str(uuid.uuid5(NS, name))


def user(name, guest=False):
    return {"id": oid("user:" + name), "userPrincipalName": f"{name}@contoso.example" if not guest else f"{name}_fabrikam.example#EXT#@contoso.example",
            "userType": "Guest" if guest else "Member", "accountEnabled": True}


def policy(name, state="enabled", include_users=None, exclude_users=None, include_groups=None, exclude_groups=None,
           include_roles=None, exclude_roles=None, apps=("All",), clients=("all",), controls=(), operator="OR",
           strength=None, sign_in_risk=None, flows=None):
    p = {"id": oid("policy:" + name), "displayName": name, "state": state,
         "createdDateTime": "2026-03-02T10:00:00Z", "modifiedDateTime": "2026-09-14T16:20:00Z",
         "conditions": {"users": {"includeUsers": list(include_users or []), "excludeUsers": list(exclude_users or []),
                                  "includeGroups": list(include_groups or []), "excludeGroups": list(exclude_groups or []),
                                  "includeRoles": list(include_roles or []), "excludeRoles": list(exclude_roles or [])},
                        "applications": {"includeApplications": list(apps), "excludeApplications": []},
                        "clientAppTypes": list(clients), "signInRiskLevels": list(sign_in_risk or []), "userRiskLevels": []},
         "grantControls": {"operator": operator, "builtInControls": list(controls), "authenticationStrength": None},
         "sessionControls": None}
    if strength:
        p["grantControls"]["authenticationStrength"] = {"id": strength, "displayName": "Phishing-resistant MFA" if strength == PHISH else "custom"}
    if flows:
        p["conditions"]["authenticationFlows"] = {"transferMethods": flows}
    return p


def base_directory():
    users = {n: user(n) for n in ["alice.admin", "ops.admin", "bg-01", "bg-02", "svc-mailscan", "dana", "eli", "fay",
                                  "gus", "hana", "ivan", "jo"]}
    users["guest.kim"] = user("kim", guest=True)
    groups = {
        "emergency": {"id": oid("group:CA-Exclude-EmergencyAccess"), "displayName": "CA-Exclude-EmergencyAccess",
                      "members": [users["bg-01"]["id"], users["bg-02"]["id"]]},
        "legacy": {"id": oid("group:Legacy-Mail-Clients"), "displayName": "Legacy-Mail-Clients", "members": [users["svc-mailscan"]["id"]]},
        "contractors": {"id": oid("group:Contractors"), "displayName": "Contractors",
                        "members": [users[n]["id"] for n in ["dana", "eli", "fay", "gus", "hana", "ivan", "jo"]]},
    }
    roles = [{"roleTemplateId": GA, "principalId": users[n]["id"]} for n in ["alice.admin", "ops.admin", "bg-01", "bg-02"]]
    return users, groups, roles


def snapshot(name, policies, users, groups, roles, emergency):
    return {"schema": "haven-graph-snapshot-v1", "collector": "synthetic-fixture", "source": "synthetic",
            "collected_at": "2026-10-31T12:00:00Z", "tenant": {"id": oid("tenant:" + name), "displayName": f"Contoso ({name}, synthetic)"},
            "graph_endpoints": ["GET /v1.0/identity/conditionalAccess/policies", "GET /v1.0/users", "GET /v1.0/groups",
                                "GET /v1.0/roleManagement/directory/roleAssignments",
                                "GET /v1.0/policies/authenticationStrengthPolicies"],
            "conditionalAccessPolicies": policies, "users": list(users.values()), "groups": list(groups.values()),
            "roleAssignments": roles,
            "directoryRoleTemplates": [{"id": GA, "displayName": "Global Administrator"},
                                       {"id": PRA, "displayName": "Privileged Role Administrator"},
                                       {"id": SECADM, "displayName": "Security Administrator"}],
            "authenticationStrengthPolicies": [
                {"id": "00000000-0000-0000-0000-000000000002", "displayName": "Multifactor authentication", "policyType": "builtIn"},
                {"id": PHISH, "displayName": "Phishing-resistant MFA", "policyType": "builtIn",
                 "allowedCombinations": ["windowsHelloForBusiness", "fido2", "x509CertificateMultiFactor"]}],
            "emergencyAccessAccounts": emergency}


def weak():
    """A plausible mid-maturity tenant with several real gaps and some traps."""
    u, g, r = base_directory()
    em = [u["bg-01"]["id"], u["bg-02"]["id"]]
    pols = [
        policy("CA001 Block legacy authentication", include_users=["All"], exclude_groups=[g["emergency"]["id"], g["legacy"]["id"]],
               clients=["exchangeActiveSync", "other"], controls=["block"]),
        policy("CA002 Require MFA for administrators", include_roles=[GA, PRA, SECADM], exclude_users=[u["ops.admin"]["id"]],
               controls=["mfa"]),
        policy("CA003 Require MFA for all users", state="enabledForReportingButNotEnforced", include_users=["All"],
               exclude_groups=[g["emergency"]["id"]], controls=["mfa"]),
        policy("CA004 Phishing-resistant MFA for admins", state="disabled", include_roles=[GA], exclude_groups=[g["emergency"]["id"]],
               strength=PHISH),
        policy("CA005 Block high sign-in risk", include_users=["All"], exclude_groups=[g["emergency"]["id"]], sign_in_risk=["high"],
               controls=["block"]),
        policy("CA007 Contractors: MFA or compliant device", include_groups=[g["contractors"]["id"]],
               exclude_users=[oid("user:deleted-former-contractor")], controls=["mfa", "compliantDevice"], operator="OR"),
    ]
    return snapshot("weak", pols, u, g, r, em)


def hardened():
    """Every Haven CA rule passes; used to measure false positives."""
    u, g, r = base_directory()
    em = [u["bg-01"]["id"], u["bg-02"]["id"]]
    ex = [g["emergency"]["id"]]
    pols = [
        policy("CA001 Block legacy authentication", include_users=["All"], exclude_groups=ex, clients=["exchangeActiveSync", "other"], controls=["block"]),
        policy("CA002 Require MFA for administrators", include_roles=[GA, PRA, SECADM], exclude_groups=ex, controls=["mfa"]),
        policy("CA003 Require MFA for all users", include_users=["All"], exclude_groups=ex, controls=["mfa"]),
        policy("CA004 Phishing-resistant MFA for admins", include_roles=[GA, PRA, SECADM], exclude_groups=ex, strength=PHISH),
        policy("CA005 Block high sign-in risk", include_users=["All"], exclude_groups=ex, sign_in_risk=["high"], controls=["block"]),
        policy("CA006 Block device code flow", include_users=["All"], exclude_groups=ex, controls=["block"], flows=["deviceCodeFlow"]),
        # Trap: a disabled duplicate of CA001. Tools that do not check state may call it a gap.
        policy("CA001-old Block legacy auth (superseded)", state="disabled", include_users=["All"], clients=["other"], controls=["block"]),
    ]
    return snapshot("hardened", pols, u, g, r, em)


def main():
    here = Path(__file__).parent
    for name, fn in (("contoso-weak", weak), ("contoso-hardened", hardened)):
        (here / f"{name}.json").write_text(json.dumps(fn(), indent=2) + "\n")
        print("wrote", name)


__all__ = ["oid", "user", "policy", "base_directory", "snapshot", "weak", "hardened", "GA", "PRA", "SECADM", "PHISH", "copy"]

if __name__ == "__main__":
    main()
