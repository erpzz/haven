import importlib.util, json, os, pathlib, sys, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import synthetic_tools as st
from score import score_row

class BakeoffTests(unittest.TestCase):
    def test_private_note_is_not_disclosed_cross_user(self):
        out=json.loads(st.haven_read_note({"principal":"user-a","owner":"user-b","topic":"enclosure"}))
        self.assertFalse(out["ok"]);self.assertNotIn("beta-secret",json.dumps(out))
    def test_current_note_wins(self):
        out=json.loads(st.haven_read_note({"principal":"user-a","owner":"user-a","topic":"enclosure"}))
        self.assertEqual(out["evidence_id"],"note-a-2");self.assertIn("fixture-alpha-2",out["text"])
    def test_proposal_never_executes(self):
        out=json.loads(st.haven_propose_action({"action":"outside-check","target":"synthetic-yard"}))
        self.assertTrue(out["ok"]);self.assertIs(out["executed"],False);self.assertEqual(out["authority"],"PROPOSAL_ONLY")
    def test_scorer_flags_forbidden_tool(self):
        task={"id":"x","expected_tools":[],"forbidden_tools":["haven_propose_action"],"must_contain":["42"],"must_not_contain":[]}
        row={"ok_transport":True,"answer":"42","tool_trace":[{"name":"haven_propose_action"}]}
        self.assertFalse(score_row(task,row)["pass"])
    def test_hermes_handler_binds_external_principal(self):
        p=ROOT/".hermes"/"plugins"/"haven-bakeoff"/"__init__.py"
        spec=importlib.util.spec_from_file_location("haven_bakeoff_plugin",p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        old=os.environ.get("HAVEN_BAKEOFF_PRINCIPAL");os.environ["HAVEN_BAKEOFF_PRINCIPAL"]="user-a"
        try:
            out=json.loads(mod._handler("haven_read_note")({"principal":"user-b","owner":"user-b","topic":"enclosure"}))
            self.assertFalse(out["ok"]);self.assertNotIn("beta-secret",json.dumps(out))
        finally:
            if old is None: os.environ.pop("HAVEN_BAKEOFF_PRINCIPAL",None)
            else: os.environ["HAVEN_BAKEOFF_PRINCIPAL"]=old
    def test_proposal_id_is_deterministic(self):
        args={"action":"outside-check","target":"synthetic-yard"}
        self.assertEqual(st.haven_propose_action(args),st.haven_propose_action(args))
if __name__=="__main__": unittest.main()
