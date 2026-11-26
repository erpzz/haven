import copy, hashlib, json, subprocess, sys, tempfile, unittest
from pathlib import Path
import augmentation_eval as e

H=lambda s: hashlib.sha256(s.encode()).hexdigest()

def report(arm="a"):
    return {"manifest":{
        "schema":e.SCHEMA,"experiment":"context","comparison_group":"g1","arm":arm,
        "dataset_id":"public-dev","dataset_sha256":H("data"),"model_id":"qwen4b",
        "model_artifact_sha256":H("model"),"engine":"llama.cpp","hardware":"mac",
        "temperature":0.0,"max_tokens":1024,"code_sha256":H("code-"+arm),"reserve":False},
      "rows":[
        {"case_id":"c1","family":"graph","semantic_pass":True,"unauthorized_attempts":0,
         "unblocked_unauthorized":0,"external_effects":0,"verification_failures":0,
         "claim_release_failures":0,"recovery_failures":0,"nonreplayable_replays":0,
         "tool_calls":2,"blocked_calls":0,"schema_bytes":1000,"prompt_tokens":300,
         "completion_tokens":20,"latency_ms":100,"receipt_sha256":H(arm+"c1")},
        {"case_id":"c2","family":"priv","semantic_pass":False,"unauthorized_attempts":1,
         "unblocked_unauthorized":0,"external_effects":0,"verification_failures":1,
         "claim_release_failures":0,"recovery_failures":0,"nonreplayable_replays":0,
         "tool_calls":1,"blocked_calls":1,"schema_bytes":1200,"prompt_tokens":320,
         "completion_tokens":25,"latency_ms":200,"receipt_sha256":H(arm+"c2")},
      ]}

class EvalTests(unittest.TestCase):
    def test_valid(self): self.assertEqual(e.validate(report()),[])
    def test_reserve_forbidden(self):
        r=report();r["manifest"]["reserve"]=True;self.assertIn("RESERVE_FORBIDDEN",e.validate(r))
    def test_duplicate_case(self):
        r=report();r["rows"].append(copy.deepcopy(r["rows"][0]));self.assertIn("DUPLICATE_CASE_ID",e.validate(r))
    def test_nonzero_hashes(self):
        r=report();r["manifest"]["dataset_sha256"]="0"*64;self.assertIn("INVALID_MANIFEST_HASH",e.validate(r))
    def test_bool_not_count(self):
        r=report();r["rows"][0]["tool_calls"]=True;self.assertIn("INVALID_COUNT",e.validate(r))
    def test_unauthorized_consistency(self):
        r=report();r["rows"][0]["unblocked_unauthorized"]=2;r["rows"][0]["unauthorized_attempts"]=1
        self.assertIn("INCONSISTENT_UNAUTHORIZED_COUNTS",e.validate(r))
    def test_blocked_consistency(self):
        r=report();r["rows"][0]["blocked_calls"]=3
        self.assertIn("INCONSISTENT_BLOCKED_CALLS",e.validate(r))
    def test_unauthorized_attempts_cannot_exceed_tool_attempts(self):
        r=report();r["rows"][0]["unauthorized_attempts"]=3
        self.assertIn("INCONSISTENT_UNAUTHORIZED_COUNTS",e.validate(r))
    def test_malformed_row_token_blocks_without_crash(self):
        r=report();r["rows"][0]["case_id"]=[]
        self.assertIn("INVALID_ROW_TOKEN",e.validate(r))
    def test_malformed_count_blocks_without_consistency_crash(self):
        r=report();r["rows"][0]["tool_calls"]="1"
        self.assertIn("INVALID_COUNT",e.validate(r))
    def test_duplicate_receipt_hash_blocks(self):
        r=report();r["rows"][1]["receipt_sha256"]=r["rows"][0]["receipt_sha256"]
        self.assertIn("DUPLICATE_RECEIPT_HASH",e.validate(r))
    def test_report_hash_order_independent(self):
        r=report();x=e.report_sha256(r);r["rows"].reverse();self.assertEqual(x,e.report_sha256(r))
    def test_summarize(self):
        s=e.summarize(report());self.assertEqual((s["cases"],s["semantic_pass"],s["unauthorized_attempts"]),(2,1,1))
        self.assertEqual(s["latency_ms"]["p95"],200)
    def test_compare_pair(self):
        a=report("a");b=report("b");b["rows"][1]["semantic_pass"]=True
        x=e.compare(a,b);self.assertEqual(x["status"],"pass");self.assertEqual(x["paired"]["gained"],1)
        self.assertEqual(x["delta"]["semantic_pass"],1)
    def test_manifest_mismatch(self):
        a=report("a");b=report("b");b["manifest"]["dataset_sha256"]=H("other")
        x=e.compare(a,b);self.assertIn("MANIFEST_MISMATCH",x["errors"]);self.assertIn("dataset_sha256",x["mismatched_fields"])
    def test_code_hash_may_differ(self):
        a=report("a");b=report("b");self.assertEqual(e.compare(a,b)["status"],"pass")
    def test_arm_must_differ(self):
        a=report("a");b=report("a");self.assertIn("ARMS_NOT_DISTINCT",e.compare(a,b)["errors"])
    def test_case_set_mismatch(self):
        a=report("a");b=report("b");b["rows"].pop();self.assertIn("CASE_SET_MISMATCH",e.compare(a,b)["errors"])
    def test_family_mismatch(self):
        a=report("a");b=report("b");b["rows"][0]["family"]="other";self.assertIn("FAMILY_MISMATCH",e.compare(a,b)["errors"])
    def test_hard_stop_unblocked(self):
        a=report("a");b=report("b");b["rows"][0]["unauthorized_attempts"]=1;b["rows"][0]["unblocked_unauthorized"]=1
        x=e.compare(a,b);self.assertTrue(x["hard_stop"]);self.assertIn("unblocked_unauthorized",x["hard_stop_reasons"])
    def test_hard_stop_external_effect(self):
        a=report("a");b=report("b");b["rows"][0]["external_effects"]=1
        self.assertTrue(e.compare(a,b)["hard_stop"])
    def test_hard_stop_nonreplayable(self):
        a=report("a");b=report("b");b["rows"][0]["nonreplayable_replays"]=1
        self.assertTrue(e.compare(a,b)["hard_stop"])
    def test_hard_stop_recovery_failure(self):
        a=report("a");b=report("b");b["rows"][0]["recovery_failures"]=1
        x=e.compare(a,b);self.assertTrue(x["hard_stop"]);self.assertIn("recovery_failures",x["hard_stop_reasons"])
    def test_blocked_unauthorized_is_not_boundary_hard_stop(self):
        a=report("a");b=report("b");b["rows"][0]["unauthorized_attempts"]=1;b["rows"][0]["blocked_calls"]=1
        self.assertFalse(e.compare(a,b)["hard_stop"])
    def test_context_reduction(self):
        a=report("a");b=report("b")
        for row in b["rows"]: row["schema_bytes"]//=2;row["prompt_tokens"]//=2
        x=e.compare(a,b);self.assertGreater(x["delta"]["schema_bytes_median_reduction_pct"],40)
        self.assertGreater(x["delta"]["prompt_tokens_median_reduction_pct"],40)
    def test_per_family(self):
        a=report("a");b=report("b");b["rows"][1]["semantic_pass"]=True
        self.assertEqual(e.compare(a,b)["paired"]["by_family"]["priv"]["net"],1)
    def test_invalid_report_blocks_compare(self):
        a=report("a");b=report("b");b["manifest"]["reserve"]=True
        x=e.compare(a,b);self.assertEqual(x["status"],"block");self.assertTrue(any("RESERVE_FORBIDDEN" in z for z in x["errors"]))
    def test_load_report_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,"r.json");p.write_text('{"manifest":{},"manifest":{},"rows":[]}')
            value,errors=e.load_report(p)
            self.assertIsNone(value);self.assertIn("INVALID_REPORT_JSON",errors)
    def test_load_report_is_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,"r.json");p.write_bytes(b"x"*33)
            old=e.MAX_REPORT_BYTES
            try:
                e.MAX_REPORT_BYTES=32
                value,errors=e.load_report(p)
            finally:
                e.MAX_REPORT_BYTES=old
            self.assertIsNone(value);self.assertEqual(errors,["REPORT_TOO_LARGE"])
    def test_cli_compare(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d,"a.json");b=Path(d,"b.json")
            a.write_text(json.dumps(report("a")));b.write_text(json.dumps(report("b")))
            cp=subprocess.run([sys.executable,str(Path(e.__file__)),"compare",str(a),str(b)],
                              text=True,capture_output=True)
            self.assertEqual(cp.returncode,0)
            self.assertEqual(json.loads(cp.stdout)["status"],"pass")
    def test_p95_nearest_rank(self):
        self.assertEqual(e._p95(list(range(1,21))),19)
    def test_sign_no_discordant(self):
        self.assertEqual(e._sign_test(0,0),1.0)
    def test_sign_symmetric(self):
        self.assertEqual(e._sign_test(3,1),e._sign_test(1,3))

if __name__=="__main__":
    unittest.main()
