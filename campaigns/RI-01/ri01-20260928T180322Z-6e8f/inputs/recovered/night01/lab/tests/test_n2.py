import copy
import json
import unittest
from haven_lab.store import LAB_ROOT
from haven_lab.notebook import campaign, promote, verify_n1_gate, check_gate_evidence
from haven_lab.types import Denied, digest

class N2Tests(unittest.TestCase):
    def setUp(self):self.inputs=json.loads((LAB_ROOT/"fixtures/engineering.json").read_text())
    def test_fixed_objective_expected_values_and_selection(self):
        out=campaign(self.inputs)
        self.assertEqual(out["baseline"]["score"],10.3456)
        self.assertEqual([x["score"] for x in out["results"]],[5.3072,0.1536,0.2496,0.288,15.384])
        self.assertEqual(out["next_candidate"],"CANDIDATE_4")
        self.assertEqual(out["decision"],"PROPOSE_NEXT_FOR_REVIEW")
        self.assertEqual(out["qualification_state"],"UNQUALIFIED")
    def test_negatives_rejections_and_original_inputs_retained(self):
        original=copy.deepcopy(self.inputs);out=campaign(self.inputs)
        self.assertEqual(self.inputs,original);self.assertEqual(out["original_inputs"],original)
        self.assertEqual([x["outcome"] for x in out["results"]],
            ["SYNTHETIC_IMPROVEMENT","CHECK_REJECTED","CHECK_REJECTED","SYNTHETIC_IMPROVEMENT","NO_IMPROVEMENT"])
        self.assertEqual(out["input_sha256"],digest(original));self.assertEqual(out["iterations"],5)
        for r in out["results"]:self.assertEqual(r["evaluation"]["design_sha256"],digest(r["design"]))
    def test_missing_rejected_and_mismatched_evaluation_never_accepted(self):
        design=self.inputs["candidates"][0]
        for ev in (None,{"status":"REJECTED","design_sha256":digest(design)},
                   {"status":"PASS","design_sha256":"0"*64}):
            for target in ("ACCEPTED","FABRICATION"):
                with self.subTest(ev=ev,target=target),self.assertRaises(Denied):promote(design,ev,target)
    def test_even_passing_synthetic_check_cannot_fabricate_or_accept(self):
        record=campaign(self.inputs)["results"][0]
        with self.assertRaisesRegex(Denied,"NOT_AUTHORIZED"):promote(record["design"],record["evaluation"],"ACCEPTED")
        self.assertFalse(campaign(self.inputs)["fabrication_enabled"])
    def test_max_five_and_metric_cannot_change(self):
        for key,value in [("max_iterations",6),("max_iterations",True),("metric_version","new-easy-score")]:
            data=copy.deepcopy(self.inputs);data[key]=value
            with self.subTest(key=key),self.assertRaises(Denied):campaign(data)
        self.inputs["candidates"].append(copy.deepcopy(self.inputs["candidates"][0]))
        with self.assertRaises(Denied):campaign(self.inputs)
    def test_no_improvement_stops(self):
        self.inputs["candidates"]=[self.inputs["candidates"][-1]]
        out=campaign(self.inputs);self.assertEqual(out["decision"],"STOP_NO_ELIGIBLE_IMPROVEMENT")
        self.assertIsNone(out["next_candidate"])
    def test_bad_dimensions_and_execution_fields_denied(self):
        for value in (float("nan"),float("inf"),True,-1,101):
            data=copy.deepcopy(self.inputs);data["baseline"]["dimensions"]["height_mm"]=value
            with self.subTest(value=value),self.assertRaises(Denied):campaign(data)
        self.inputs["candidates"][0]["fabrication_enabled"]=True
        with self.assertRaises(Denied):campaign(self.inputs)
    def test_provenance_and_metadata(self):
        self.inputs["candidates"][0]["parent_artifact_ids"]=["UNKNOWN"]
        with self.assertRaises(Denied):campaign(self.inputs)
    def test_n1_executed_gate_matches_source(self):
        self.assertEqual(len(verify_n1_gate()),64)

    def test_n1_gate_rejects_failed_or_incomplete_evidence(self):
        gate=json.loads((LAB_ROOT.parent/"outputs/N1_GATE.json").read_text())
        log=json.loads((LAB_ROOT.parent/gate["test_log"]).read_text())
        for changes in ({"exit_code":1},{"failures":1},{"errors":1},{"skips":1},
                        {"tests_run":0},{"tests":[]},{"suite":"n2"},{"source_sha256":{}}):
            bad=copy.deepcopy(log);bad.update(changes)
            with self.subTest(changes=changes),self.assertRaises(Denied):check_gate_evidence(gate,bad)
        bad=copy.deepcopy(log);bad["tests"][0]["status"]="EXECUTED_FAIL"
        with self.assertRaises(Denied):check_gate_evidence(gate,bad)
        bad=copy.deepcopy(log);bad["tests"][0]=bad["tests"][1]
        with self.assertRaises(Denied):check_gate_evidence(gate,bad)
        for changes in ({"source_hashes":{}},{"status":"EXECUTED_FAIL"},{"tests":0}):
            bad=copy.deepcopy(gate);bad.update(changes)
            with self.subTest(changes=changes),self.assertRaises(Denied):check_gate_evidence(bad,log)

    def test_design_identifiers_cannot_escape_artifact_directory(self):
        for bad in ("../escape","/absolute",123,""):
            data=copy.deepcopy(self.inputs);data["candidates"][0]["artifact_id"]=bad
            with self.subTest(bad=bad),self.assertRaises(Denied):campaign(data)

if __name__=="__main__":unittest.main()
