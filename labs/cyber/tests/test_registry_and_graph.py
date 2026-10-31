import io
import json
import os
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from haven_cyber.tools import graph
from haven_cyber.tools.azure_rbac import check, scope_applies
from haven_cyber.tools.registry import Registry, ToolSpec, default_registry


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.audit = Path(self.tmp.name) / "audit.jsonl"
        self.reg = default_registry(self.audit)

    def tearDown(self):
        self.tmp.cleanup()

    def test_capabilities_are_compact_and_describe_is_lazy(self):
        caps = self.reg.capabilities()
        self.assertTrue(all(set(c) == {"id", "capability", "domain", "read_only", "scope", "available"} for c in caps))
        d = self.reg.describe("entra.graph.collect")
        self.assertEqual(d["scope"], "tenant-read")
        self.assertIn("Policy.Read.All", d["permissions"])
        self.assertFalse(d["available"])

    def test_validation_scope_and_audit(self):
        self.assertEqual(self.reg.invoke("entra.ca.assess", {})["error"]["code"], "invalid_input")
        self.assertEqual(self.reg.invoke("entra.ca.assess", {"snapshot_path": "x", "extra": 1})["error"]["code"], "invalid_input")
        self.assertEqual(self.reg.invoke("entra.ca.assess", {"snapshot_path": "../../../../etc/hosts"})["error"]["code"], "path_out_of_scope")
        self.assertEqual(self.reg.invoke("nope", {})["error"]["code"], "unknown_tool")
        ok = self.reg.invoke("entra.ca.assess", {"snapshot_path": "fixtures/tenants/contoso-weak.json"})
        self.assertTrue(ok["ok"])
        lines = [json.loads(x) for x in self.audit.read_text().splitlines()]
        self.assertEqual(len(lines), 5)
        self.assertTrue(all("input_sha256" in x and "snapshot_path" not in json.dumps(x) for x in lines))

    def test_live_tool_gated(self):
        with mock.patch.dict(os.environ, {"HAVEN_CYBER_ALLOW_LIVE": "", "HAVEN_GRAPH_TOKEN": ""}):
            self.assertEqual(self.reg.invoke("entra.graph.collect", {"emergency_account_ids": []})["error"]["code"], "prerequisite_failed")

    def test_write_tools_refused_timeout_and_rate_limit(self):
        r = Registry(None)
        r.register(ToolSpec("x.write", "w", {"type": "object", "properties": {}}, {}, lambda: 1, read_only=False))
        r.register(ToolSpec("x.slow", "s", {"type": "object", "properties": {}}, {}, lambda: time.sleep(2), timeout_s=0.2))
        r.register(ToolSpec("x.fast", "f", {"type": "object", "properties": {}}, {}, lambda: 1, rate_per_min=2))
        self.assertEqual(r.invoke("x.write")["error"]["code"], "write_not_authorized")
        self.assertEqual(r.invoke("x.slow")["error"]["code"], "timeout")
        codes = [r.invoke("x.fast").get("error", {}).get("code") for _ in range(3)]
        self.assertEqual(codes, [None, None, "rate_limited"])


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_graph(pages):
    calls = []

    def opener(req, timeout=30):
        calls.append((req.get_method(), req.full_url, req.headers.get("Authorization")))
        url = req.full_url
        if url in pages:
            v = pages[url]
            if isinstance(v, Exception):
                raise v
            return FakeResp(json.dumps(v).encode())
        return FakeResp(json.dumps({"value": []}).encode())
    return opener, calls


class GraphTests(unittest.TestCase):
    def test_collect_pages_and_shapes_snapshot(self):
        B = graph.BASE
        pages = {
            B + graph.ALLOWED["conditionalAccessPolicies"]: {"value": [{"id": "p1"}], "@odata.nextLink": B + "/identity/conditionalAccess/policies?$skiptoken=2"},
            B + "/identity/conditionalAccess/policies?$skiptoken=2": {"value": [{"id": "p2"}]},
            B + graph.ALLOWED["groups"]: {"value": [{"id": "g1", "displayName": "G"}]},
            B + "/groups/g1/transitiveMembers?$select=id": {"value": [{"id": "u1"}]},
            B + graph.ALLOWED["roleAssignments"]: {"value": [{"roleDefinitionId": "r1", "principalId": "u1"}]},
            B + "/organization?$select=id,displayName": {"value": [{"id": "t1", "displayName": "T"}]},
        }
        opener, calls = fake_graph(pages)
        snap = graph.collect("secret-token", ["u9"], opener=opener)
        self.assertEqual([p["id"] for p in snap["conditionalAccessPolicies"]], ["p1", "p2"])
        self.assertEqual(snap["groups"][0]["members"], ["u1"])
        self.assertEqual(snap["roleAssignments"][0]["roleTemplateId"], "r1")
        self.assertEqual(snap["emergencyAccessAccounts"], ["u9"])
        self.assertTrue(all(m == "GET" for m, _, _ in calls))
        self.assertNotIn("secret-token", json.dumps(snap))

    def test_refuses_foreign_next_link(self):
        B = graph.BASE
        opener, _ = fake_graph({B + graph.ALLOWED["users"]: {"value": [], "@odata.nextLink": "https://evil.example/steal"}})
        with self.assertRaises(graph.GraphError) as cm:
            graph.GraphReader("t", opener).get_all(B + graph.ALLOWED["users"])
        self.assertEqual(cm.exception.code, "url_not_allowed")

    def test_throttle_retry_then_error_mapping(self):
        B = graph.BASE
        url = B + graph.ALLOWED["users"]
        state = {"n": 0}

        def opener(req, timeout=30):
            state["n"] += 1
            if state["n"] == 1:
                raise urllib.error.HTTPError(url, 429, "throttled", {"Retry-After": "3"}, io.BytesIO(b"{}"))
            raise urllib.error.HTTPError(url, 403, "forbidden", {}, io.BytesIO(
                json.dumps({"error": {"code": "Authorization_RequestDenied", "message": "Insufficient privileges"}}).encode()))
        slept = []
        with self.assertRaises(graph.GraphError) as cm:
            graph.GraphReader("t", opener, sleep=slept.append).get_all(url)
        self.assertEqual(slept, [3])
        self.assertEqual(cm.exception.code, "Authorization_RequestDenied")


class RBACTests(unittest.TestCase):
    def test_semantics(self):
        sub = "/subscriptions/s1"
        data = {"roleDefinitions": [{"id": "r", "roleName": "R", "actions": ["Microsoft.Compute/*"], "notActions": ["Microsoft.Compute/virtualMachines/delete"]}],
                "roleAssignments": [{"principalId": "p", "roleDefinitionId": "r", "scope": sub}], "denyAssignments": [], "groups": {}}
        self.assertTrue(check(data, "p", "Microsoft.Compute/virtualMachines/start/action", sub + "/resourceGroups/a")["allowed"])
        self.assertFalse(check(data, "p", "microsoft.compute/virtualmachines/DELETE", sub)["allowed"])
        self.assertFalse(check(data, "p", "Microsoft.Compute/virtualMachines/read", "/subscriptions/s2")["allowed"])
        self.assertFalse(scope_applies("/subscriptions/s1", "/subscriptions/s10"))
        self.assertTrue(scope_applies("/providers/Microsoft.Management/managementGroups/m", sub + "/x",
                                      {"/providers/Microsoft.Management/managementGroups/m": [sub]}))


if __name__ == "__main__":
    unittest.main()
