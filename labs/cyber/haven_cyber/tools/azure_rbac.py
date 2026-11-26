"""Read-only Azure RBAC effective-permission evaluator over an exported assignment set.

Implements the documented semantics: an operation is allowed if at least one role assignment at the target
scope or any parent scope grants it through `Actions`/`DataActions` and that same role does not remove it through
`NotActions`/`NotDataActions`; `NotActions` never subtract across roles; deny assignments at or above the scope
override everything for the principals they cover (minus their excluded principals). Wildcards follow ARM rules
(`*` matches any run of characters, case-insensitive).

Input (fixtures/azure/*.json or a Resource Graph export): {"roleDefinitions": [...], "roleAssignments": [...],
"denyAssignments": [...], "groups": {"<groupId>": ["<memberId>", ...]}}.
"""
from __future__ import annotations

import re
from functools import lru_cache


@lru_cache(maxsize=4096)
def _pattern(p: str) -> re.Pattern:
    return re.compile("^" + re.escape(p).replace(r"\*", ".*") + "$", re.IGNORECASE)


def matches(pattern: str, op: str) -> bool:
    return bool(_pattern(pattern).match(op))


def scope_applies(assignment_scope: str, target: str, hierarchy: dict | None = None) -> bool:
    """True if an assignment at assignment_scope is inherited by target. Management groups are not path prefixes of
    their subscriptions, so `hierarchy` maps a management-group scope to the subscription scopes beneath it."""
    a, t = assignment_scope.rstrip("/").lower(), target.rstrip("/").lower()
    if a == "" or t == a or t.startswith(a + "/"):
        return True
    for mg, subs in (hierarchy or {}).items():
        if mg.rstrip("/").lower() == a and any(scope_applies(s, target) for s in subs):
            return True
    return False


def principals_of(principal: str, data: dict) -> set[str]:
    out = {principal}
    for gid, members in (data.get("groups") or {}).items():
        if principal in members:
            out.add(gid)
    return out


def check(data: dict, principal: str, operation: str, scope: str, data_action: bool = False) -> dict:
    ids = principals_of(principal, data)
    roles = {r["id"]: r for r in data.get("roleDefinitions", [])}
    grants = []
    for a in data.get("roleAssignments", []):
        if a["principalId"] not in ids or not scope_applies(a["scope"], scope, data.get("hierarchy")):
            continue
        r = roles.get(a["roleDefinitionId"])
        if not r:
            continue
        allow, deny = ("dataActions", "notDataActions") if data_action else ("actions", "notActions")
        if any(matches(p, operation) for p in r.get(allow, [])) and not any(matches(p, operation) for p in r.get(deny, [])):
            grants.append({"role": r.get("roleName", r["id"]), "scope": a["scope"], "assignment": a.get("id", "")})
    denied_by = []
    for d in data.get("denyAssignments", []):
        if not scope_applies(d["scope"], scope, data.get("hierarchy")):
            continue
        covered = any(p in ids or p == "everyone" for p in d.get("principals", []))
        if covered and not (set(d.get("excludePrincipals", [])) & ids):
            ops = d.get("dataActions" if data_action else "actions", [])
            if any(matches(p, operation) for p in ops) and not any(matches(p, operation) for p in d.get("notDataActions" if data_action else "notActions", [])):
                denied_by.append(d.get("name", d.get("id", "deny")))
    return {"allowed": bool(grants) and not denied_by, "granted_by": grants, "denied_by": denied_by,
            "principal_and_groups": sorted(ids), "operation": operation, "scope": scope, "data_action": data_action}
