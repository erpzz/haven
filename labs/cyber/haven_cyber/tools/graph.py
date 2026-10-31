"""Read-only Microsoft Graph collector that produces the snapshot format consumed by entra_ca.

Security properties:
- GET only, and only to the allowlisted v1.0 paths below. No write, no beta, no arbitrary URL.
- The bearer token comes from the environment (HAVEN_GRAPH_TOKEN, e.g. from `az account get-access-token
  --resource https://graph.microsoft.com`) and is never logged, returned or written to the snapshot.
- Live collection is off unless HAVEN_CYBER_ALLOW_LIVE=1, and the operator supplies emergency-access account ids.
- Paging follows @odata.nextLink only when it stays on graph.microsoft.com/v1.0; 429/503 honour Retry-After.

Required delegated or application permissions (least privilege): Policy.Read.All, User.Read.All (or
User.ReadBasic.All), GroupMember.Read.All, RoleManagement.Read.Directory.

Status: exercised against recorded mock responses only (tests/test_graph.py). Not yet run against a live tenant.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Callable

BASE = "https://graph.microsoft.com/v1.0"
ALLOWED = {
    "conditionalAccessPolicies": "/identity/conditionalAccess/policies",
    "namedLocations": "/identity/conditionalAccess/namedLocations",
    "authenticationStrengthPolicies": "/policies/authenticationStrengthPolicies",
    "users": "/users?$select=id,userPrincipalName,userType,accountEnabled",
    "groups": "/groups?$select=id,displayName",
    "roleAssignments": "/roleManagement/directory/roleAssignments?$select=roleDefinitionId,principalId,directoryScopeId",
    "directoryRoleTemplates": "/directoryRoleTemplates?$select=id,displayName",
}


class GraphError(Exception):
    def __init__(self, code: str, message: str, status: int | None = None):
        super().__init__(f"{code}: {message}")
        self.code, self.status = code, status


def _check_url(url: str) -> None:
    if not url.startswith(BASE + "/"):
        raise GraphError("url_not_allowed", "refusing to follow a link outside graph.microsoft.com/v1.0")


class GraphReader:
    def __init__(self, token: str, opener: Callable | None = None, max_pages: int = 50, sleep=time.sleep):
        self._token = token
        self._open = opener or urllib.request.urlopen
        self.max_pages, self._sleep = max_pages, sleep
        self.calls: list[str] = []  # paths only, for the audit trail

    def get_all(self, url: str) -> list[dict]:
        items, pages = [], 0
        while url:
            _check_url(url)
            pages += 1
            if pages > self.max_pages:
                raise GraphError("too_many_pages", f"stopped after {self.max_pages} pages")
            body = self._get(url)
            items += body.get("value", [])
            url = body.get("@odata.nextLink")
        return items

    def _get(self, url: str, attempt: int = 0) -> dict:
        req = urllib.request.Request(url, method="GET", headers={"Authorization": f"Bearer {self._token}",
                                                                 "Accept": "application/json", "ConsistencyLevel": "eventual"})
        self.calls.append(url[len(BASE):])
        try:
            with self._open(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 4:
                self._sleep(min(60, int(e.headers.get("Retry-After", 2 ** attempt))))
                return self._get(url, attempt + 1)
            try:
                err = json.loads(e.read()).get("error", {})
            except Exception:
                err = {}
            raise GraphError(err.get("code", f"http_{e.code}"), err.get("message", str(e)), e.code) from None


def collect(token: str, emergency_accounts: list[str], opener: Callable | None = None) -> dict:
    g = GraphReader(token, opener)
    snap = {"schema": "haven-graph-snapshot-v1", "collector": "haven.graph", "source": "tenant",
            "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "graph_endpoints": []}
    for key, path in ALLOWED.items():
        snap[key] = g.get_all(BASE + path)
    for grp in snap["groups"]:
        grp["members"] = [m["id"] for m in g.get_all(f"{BASE}/groups/{grp['id']}/transitiveMembers?$select=id")]
    # Graph returns roleDefinitionId; for built-in roles it equals the role template id that CA policies reference.
    snap["roleAssignments"] = [{"roleTemplateId": a["roleDefinitionId"], "principalId": a["principalId"],
                                "directoryScopeId": a.get("directoryScopeId", "/")} for a in snap["roleAssignments"]]
    org = g.get_all(BASE + "/organization?$select=id,displayName")
    snap["tenant"] = {"id": org[0]["id"], "displayName": org[0].get("displayName", "")} if org else {}
    snap["emergencyAccessAccounts"] = list(emergency_accounts)
    snap["graph_endpoints"] = sorted({"GET /v1.0" + c.split("?")[0] for c in g.calls})
    return snap


def live_allowed() -> tuple[bool, str]:
    if os.environ.get("HAVEN_CYBER_ALLOW_LIVE") != "1":
        return False, "live tenant access is disabled (set HAVEN_CYBER_ALLOW_LIVE=1 for an authorized tenant)"
    if not os.environ.get("HAVEN_GRAPH_TOKEN"):
        return False, "HAVEN_GRAPH_TOKEN is not set"
    return True, "ok"
