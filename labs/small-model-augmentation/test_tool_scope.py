import json, unittest
import tool_scope as s

def policy():
    return {"schema":s.SCHEMA,
      "allowed_tools":["mcp_haven_status","mcp_haven_cyber_search"],
      "max_calls":3,
      "per_tool_max":{"mcp_haven_status":1,"mcp_haven_cyber_search":2},
      "unique_calls":True,
      "argument_rules":{
        "mcp_haven_status":{"allowed_keys":[],"required_keys":[],"exact_values":{}},
        "mcp_haven_cyber_search":{"allowed_keys":["query","domain"],"required_keys":["query","domain"],
          "exact_values":{"/domain":["network"]}}
      }}

class ScopeTests(unittest.TestCase):
    def test_surface_exact(self):
        p=policy()
        self.assertEqual(s.bind_surface(p,p["allowed_tools"])["status"],"pass")
        self.assertIn("VISIBLE_TOOL_EXTRA",s.bind_surface(p,p["allowed_tools"]+["terminal"])["errors"])
        self.assertIn("VISIBLE_TOOL_MISSING",s.bind_surface(p,["mcp_haven_status"])["errors"])

    def test_zero_tool_surface_is_valid_and_fail_closed(self):
        p={
          "schema":s.SCHEMA,
          "allowed_tools":[],
          "max_calls":0,
          "per_tool_max":{},
          "unique_calls":True,
          "argument_rules":{},
        }
        self.assertEqual(s.validate_policy(p), [])
        self.assertEqual(s.bind_surface(p,[]), {
          "schema":"haven.tool-scope-receipt.v1",
          "status":"pass",
          "errors":[],
          "calls_allowed":0,
          "visible_tool_count":0,
          "policy_tool_count":0,
        })
        extra=s.bind_surface(p,["write_canary"])
        self.assertEqual(extra["status"],"block")
        self.assertIn("VISIBLE_TOOL_EXTRA",extra["errors"])
        st=s.State()
        denied=s.check_call(p,st,"write_canary",{"object":"alpha-0001"})
        self.assertEqual(denied["status"],"block")
        self.assertIn("TOOL_NOT_ALLOWED",denied["errors"])
        self.assertEqual(st.total,0)
        self.assertEqual(s.evaluate(p,[],[])["status"],"pass")

    def test_zero_tool_surface_requires_zero_budget(self):
        p={
          "schema":s.SCHEMA,
          "allowed_tools":[],
          "max_calls":1,
          "per_tool_max":{},
          "unique_calls":True,
          "argument_rules":{},
        }
        self.assertIn("INVALID_MAX_CALLS",s.validate_policy(p))
        q=policy(); q["max_calls"]=0
        self.assertIn("INVALID_MAX_CALLS",s.validate_policy(q))

    def test_duplicate_visible(self):
        self.assertIn("DUPLICATE_VISIBLE_TOOL",s.bind_surface(policy(),["mcp_haven_status"]*2)["errors"])

    def test_scoped_call(self):
        st=s.State(); p=policy()
        self.assertEqual(s.check_call(p,st,"mcp_haven_cyber_search",{"query":"guest isolation","domain":"network"})["status"],"pass")
        self.assertEqual(st.total,1)

    def test_wrong_exact_target(self):
        st=s.State(); p=policy()
        r=s.check_call(p,st,"mcp_haven_cyber_search",{"query":"x","domain":"entra"})
        self.assertIn("ARGUMENT_VALUE_OUT_OF_SCOPE",r["errors"]); self.assertEqual(st.total,0)

    def test_missing_and_extra_args(self):
        st=s.State(); p=policy()
        self.assertIn("REQUIRED_ARGUMENT_MISSING",s.check_call(p,st,"mcp_haven_cyber_search",{"query":"x"})["errors"])
        self.assertIn("ARGUMENT_KEY_NOT_ALLOWED",s.check_call(p,st,"mcp_haven_status",{"target":"x"})["errors"])

    def test_unknown_tool_and_non_dict_args(self):
        st=s.State(); p=policy()
        self.assertIn("TOOL_NOT_ALLOWED",s.check_call(p,st,"terminal",{"command":"id"})["errors"])
        for v in ([], "", None, 0):
            self.assertIn("INVALID_ARGUMENTS",s.check_call(p,st,"mcp_haven_status",v)["errors"])

    def test_budget(self):
        st=s.State(); p=policy()
        self.assertEqual(s.check_call(p,st,"mcp_haven_status",{})["status"],"pass")
        self.assertIn("TOOL_BUDGET_EXCEEDED",s.check_call(p,st,"mcp_haven_status",{"x":1})["errors"])
        st=s.State()
        self.assertEqual(s.check_call(p,st,"mcp_haven_cyber_search",{"query":"a","domain":"network"})["status"],"pass")
        self.assertEqual(s.check_call(p,st,"mcp_haven_cyber_search",{"query":"b","domain":"network"})["status"],"pass")
        self.assertIn("TOOL_BUDGET_EXCEEDED",s.check_call(p,st,"mcp_haven_cyber_search",{"query":"c","domain":"network"})["errors"])

    def test_duplicate_call(self):
        st=s.State(); p=policy(); args={"query":"a","domain":"network"}
        self.assertEqual(s.check_call(p,st,"mcp_haven_cyber_search",args)["status"],"pass")
        self.assertIn("DUPLICATE_CALL",s.check_call(p,st,"mcp_haven_cyber_search",args)["errors"])
        self.assertEqual(st.total,1)

    def test_placeholder_policy_rejected(self):
        placeholders=["<TARGET>","${TARGET}","{{target}}","TODO","TBD","CHANGEME","",None]
        for v in placeholders:
            p=policy(); p["argument_rules"]["mcp_haven_cyber_search"]["exact_values"]["/domain"]=[v]
            self.assertIn("INVALID_EXACT_VALUES",s.validate_policy(p))

    def test_policy_requires_explicit_rules_and_budgets(self):
        p=policy(); del p["argument_rules"]["mcp_haven_status"]
        self.assertIn("INVALID_ARGUMENT_RULES",s.validate_policy(p))
        p=policy(); del p["per_tool_max"]["mcp_haven_status"]
        self.assertIn("INVALID_PER_TOOL_MAX",s.validate_policy(p))

    def test_exact_value_type_strict(self):
        p=policy(); p["argument_rules"]["mcp_haven_cyber_search"]["allowed_keys"].append("level")
        p["argument_rules"]["mcp_haven_cyber_search"]["exact_values"]["/level"]=[1]
        st=s.State()
        r=s.check_call(p,st,"mcp_haven_cyber_search",{"query":"x","domain":"network","level":True})
        self.assertIn("ARGUMENT_VALUE_OUT_OF_SCOPE",r["errors"])

    def test_concurrent_budget_is_atomic_and_state_keeps_only_hashes(self):
        import concurrent.futures
        p=policy(); p["max_calls"]=2; p["per_tool_max"]["mcp_haven_cyber_search"]=2
        st=s.State()
        def one(i):
            return s.check_call(p,st,"mcp_haven_cyber_search",{"query":f"q{i}","domain":"network"})
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            results=list(ex.map(one,range(20)))
        self.assertEqual(sum(r["status"]=="pass" for r in results),2)
        self.assertEqual(st.total,2)
        self.assertTrue(all(len(x)==64 and "q" not in x for x in st.fingerprints))

    def test_call_trace_stops_on_first_denial(self):
        p=policy()
        r=s.evaluate(p,p["allowed_tools"],[
          {"tool":"mcp_haven_status","arguments":{}},
          {"tool":"terminal","arguments":{"command":"curl x"}},
          {"tool":"mcp_haven_cyber_search","arguments":{"query":"x","domain":"network"}}])
        self.assertEqual(r["status"],"block"); self.assertEqual(r["calls_allowed"],1)
        self.assertIn("TOOL_NOT_ALLOWED",r["errors"])

    def test_nested_dispatcher_target_is_exact(self):
        p={"schema":s.SCHEMA,
           "allowed_tools":["mcp_haven_cyber_cyber_call"],"max_calls":2,
           "per_tool_max":{"mcp_haven_cyber_cyber_call":2},"unique_calls":True,
           "argument_rules":{"mcp_haven_cyber_cyber_call":{
             "allowed_keys":["tool_id","arguments"],"required_keys":["tool_id","arguments"],
             "exact_values":{
               "/tool_id":["entra.ca.assess"],
               "/arguments/snapshot_path":["fixtures/tenants/approved.json"]
             }}}}
        visible=["mcp_haven_cyber_cyber_call"]
        self.assertEqual(s.bind_surface(p,visible)["status"],"pass")
        st=s.State()
        ok=s.check_call(p,st,visible[0],{"tool_id":"entra.ca.assess","arguments":{"snapshot_path":"fixtures/tenants/approved.json"}})
        self.assertEqual(ok["status"],"pass")
        st=s.State()
        bad=s.check_call(p,st,visible[0],{"tool_id":"entra.ca.assess","arguments":{"snapshot_path":"../../etc/hosts"}})
        self.assertIn("ARGUMENT_VALUE_OUT_OF_SCOPE",bad["errors"])
        st=s.State()
        missing=s.check_call(p,st,visible[0],{"tool_id":"entra.ca.assess","arguments":{}})
        self.assertIn("CONSTRAINED_VALUE_MISSING",missing["errors"])

    def test_exact_structured_target_is_type_strict(self):
        p=policy()
        p["argument_rules"]["mcp_haven_cyber_search"]["allowed_keys"].append("targets")
        p["argument_rules"]["mcp_haven_cyber_search"]["required_keys"].append("targets")
        p["argument_rules"]["mcp_haven_cyber_search"]["exact_values"]["/targets"]=[["id-a","id-b"]]
        st=s.State()
        self.assertEqual(s.check_call(p,st,"mcp_haven_cyber_search",
            {"query":"x","domain":"network","targets":["id-a","id-b"]})["status"],"pass")
        st=s.State()
        self.assertIn("ARGUMENT_VALUE_OUT_OF_SCOPE",s.check_call(p,st,"mcp_haven_cyber_search",
            {"query":"x","domain":"network","targets":["id-b","id-a"]})["errors"])
        p["argument_rules"]["mcp_haven_cyber_search"]["exact_values"]["/targets"]=[["id-a","<TARGET>"]]
        self.assertIn("INVALID_EXACT_VALUES",s.validate_policy(p))

    def test_policy_json_duplicate_and_nonfinite(self):
        doc,err=s.parse_policy(b'{"schema":"x","schema":"y"}')
        self.assertIsNone(doc); self.assertIn("INVALID_POLICY_JSON",err["errors"])
        p=policy()
        raw=json.dumps(p).replace('"max_calls": 3','"max_calls": NaN').encode()
        doc,err=s.parse_policy(raw); self.assertIsNone(doc); self.assertIn("INVALID_POLICY_JSON",err["errors"])

    def test_receipts_do_not_echo_sensitive_values(self):
        p=policy(); st=s.State()
        marker="PRIVATE_TARGET_MARKER"
        r=s.check_call(p,st,"mcp_haven_cyber_search",{"query":marker,"domain":"entra"})
        self.assertNotIn(marker,json.dumps(r)); self.assertNotIn("entra",json.dumps(r))

if __name__=="__main__": unittest.main()
