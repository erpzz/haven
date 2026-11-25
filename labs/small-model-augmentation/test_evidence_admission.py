import copy, hashlib, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
import evidence_admission as e

def artifact_bytes(value=True):
    return json.dumps({"flag":value,"nested":{"n":1}}, separators=(",",":")).encode()

def valid_bundle():
    raw=artifact_bytes(True); sha=hashlib.sha256(raw).hexdigest()
    return {"schema":e.SCHEMA,
      "artifacts":[{"sha256":sha,"path":"art.json","media_type":"application/json","source_tool":"fixture","collected_at":"2026-11-25T00:00:00Z"}],
      "observations":[{"id":"obs-1","artifact":sha,"pointer":"/flag","value":True,"note":""}],
      "findings":[{"id":"F-1","title":"x","domain":"entra","service":"ca","source_tool":"fixture","source_check_id":"X",
        "resource_id":"r","environment":"synthetic:test","observation_point":"fixture","status":"fail","description":"x",
        "severity":"high","confidence":0.9,"collected_at":"2026-11-25T00:00:00Z","observations":["obs-1"],"artifacts":[sha],
        "controls":[],"remediation":"fix","references":[],"limitations":[],"next_validation_step":"","verification":"reported",
        "verification_notes":[],"inferred":True}]}

class EvidenceAdmissionTests(unittest.TestCase):
    def test_valid_structure_and_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            b=valid_bundle(); Path(d,"art.json").write_bytes(artifact_bytes(True))
            self.assertEqual(e.check_bundle(b)["status"],"pass")
            r=e.verify_artifact_root(b,d); self.assertEqual(r["status"],"pass"); self.assertEqual(r["artifacts_checked"],1)

    def test_duplicate_ids_and_hash(self):
        for kind in ("artifact","observation","finding"):
            b=valid_bundle()
            if kind=="artifact": b["artifacts"].append(copy.deepcopy(b["artifacts"][0])); code="DUPLICATE_ARTIFACT_HASH"
            elif kind=="observation": b["observations"].append(copy.deepcopy(b["observations"][0])); code="DUPLICATE_OBSERVATION_ID"
            else: b["findings"].append(copy.deepcopy(b["findings"][0])); code="DUPLICATE_FINDING_ID"
            self.assertIn(code,e.check_bundle(b)["errors"])

    def test_lineage_mismatch(self):
        b=valid_bundle(); b["findings"][0]["artifacts"]=[]
        self.assertIn("FINDING_LINEAGE_MISMATCH",e.check_bundle(b)["errors"])

    def test_preverified_rejected(self):
        for state in ("corroborated","confirmed","refuted","insufficient_evidence"):
            b=valid_bundle(); b["findings"][0]["verification"]=state
            self.assertIn("PREVERIFIED_FINDING",e.check_bundle(b)["errors"])
        b=valid_bundle(); b["findings"][0]["verification_notes"]=["already checked"]
        self.assertIn("PREVERIFIED_FINDING",e.check_bundle(b)["errors"])

    def test_decisive_requires_evidence(self):
        for status in ("pass","fail"):
            b=valid_bundle(); b["findings"][0]["status"]=status
            b["observations"]=[]; b["findings"][0]["observations"]=[]; b["findings"][0]["artifacts"]=[]
            self.assertIn("DECISIVE_FINDING_WITHOUT_EVIDENCE",e.check_bundle(b)["errors"])

    def test_paths(self):
        for p in ("../secret.json","x/../../secret.json","/etc/passwd","C:\\secret.json","\\server\\share\\x"):
            b=valid_bundle(); b["artifacts"][0]["path"]=p
            self.assertIn("UNSAFE_ARTIFACT_PATH",e.check_bundle(b)["errors"])

    def test_pointer_validation(self):
        for p in ("no-slash","/~2","/~","/\x00"):
            b=valid_bundle(); b["observations"][0]["pointer"]=p
            self.assertIn("INVALID_JSON_POINTER",e.check_bundle(b)["errors"])

    def test_strict_bool_int_difference(self):
        with tempfile.TemporaryDirectory() as d:
            b=valid_bundle(); Path(d,"art.json").write_bytes(artifact_bytes(True))
            b["observations"][0]["value"]=1
            self.assertIn("OBSERVATION_VALUE_MISMATCH",e.verify_artifact_root(b,d)["errors"])

    def test_tamper_and_invalid_json_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            b=valid_bundle(); Path(d,"art.json").write_bytes(b'{"flag":false}')
            self.assertIn("ARTIFACT_HASH_MISMATCH",e.verify_artifact_root(b,d)["errors"])
            raw=b'{"flag":true,"flag":false}'; sha=hashlib.sha256(raw).hexdigest()
            b["artifacts"][0]["sha256"]=sha; b["observations"][0]["artifact"]=sha; b["findings"][0]["artifacts"]=[sha]
            Path(d,"art.json").write_bytes(raw)
            self.assertIn("ARTIFACT_JSON_INVALID",e.verify_artifact_root(b,d)["errors"])

    def test_symlink_escape(self):
        if not hasattr(os,"symlink"): self.skipTest("no symlink")
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as out:
            b=valid_bundle(); Path(out,"art.json").write_bytes(artifact_bytes(True)); os.symlink(Path(out,"art.json"),Path(d,"art.json"))
            self.assertIn("ARTIFACT_ESCAPES_ROOT",e.verify_artifact_root(b,d)["errors"])

    def test_unknown_refs(self):
        b=valid_bundle(); b["findings"][0]["observations"]=["nope"]
        self.assertIn("UNKNOWN_FINDING_OBSERVATION",e.check_bundle(b)["errors"])
        b=valid_bundle(); b["observations"][0]["artifact"]="0"*64
        self.assertIn("UNDECLARED_OBSERVATION_ARTIFACT",e.check_bundle(b)["errors"])

    def test_schema_and_shape(self):
        b=valid_bundle(); b["schema"]="future"; self.assertIn("INVALID_SCHEMA",e.check_bundle(b)["errors"])
        b=valid_bundle(); b["extra"]=1; self.assertEqual(e.check_bundle(b)["errors"],["INVALID_TOP_LEVEL"])

    def test_confidence_types(self):
        for v in (True,-.1,1.1,float("nan"),"0.9"):
            b=valid_bundle(); b["findings"][0]["confidence"]=v
            self.assertIn("INVALID_CONFIDENCE",e.check_bundle(b)["errors"])

    def test_malformed_reference_lists_fail_closed_not_crash(self):
        for key,value in (("observations",[{"bad":1}]),("artifacts",[{"bad":1}]),("controls",[{"bad":1}])):
            b=valid_bundle(); b["findings"][0][key]=value
            r=e.check_bundle(b)
            self.assertEqual(r["status"],"block")
            self.assertIn("INVALID_FINDING_LIST",r["errors"])

    def test_observation_value_must_be_finite_json(self):
        for value in (float("nan"),float("inf"),{1:"bad"},object()):
            b=valid_bundle(); b["observations"][0]["value"]=value
            self.assertIn("INVALID_OBSERVATION_VALUE",e.check_bundle(b)["errors"])

    def test_cli_redacts_paths_and_values(self):
        with tempfile.TemporaryDirectory() as d:
            b=valid_bundle(); b["artifacts"][0]["path"]="../PRIVATE_MARKER.json"
            p=Path(d,"bundle.json"); p.write_text(json.dumps(b))
            cp=subprocess.run([sys.executable,str(Path(e.__file__)),str(p)],text=True,capture_output=True)
            self.assertEqual(cp.returncode,2); self.assertNotIn("PRIVATE_MARKER",cp.stdout+cp.stderr)
            self.assertEqual(json.loads(cp.stdout)["status"],"block")

    def test_bundle_duplicate_json_key(self):
        doc,err=e.parse_bundle(b'{"schema":"x","schema":"y","artifacts":[],"observations":[],"findings":[]}')
        self.assertIsNone(doc); self.assertEqual(err["errors"],["INVALID_BUNDLE_JSON"])
        doc,err=e.parse_bundle(b'{"schema":"haven-cyber-evidence-v1","artifacts":[],"observations":[{"id":1e999}],"findings":[]}')
        self.assertIsNone(doc); self.assertEqual(err["errors"],["INVALID_BUNDLE_JSON"])

    def test_root_pointer_and_nested(self):
        raw=json.dumps({"a/b":{"~":[1,{"x":"y"}]}},separators=(",",":")).encode(); sha=hashlib.sha256(raw).hexdigest()
        b=valid_bundle(); b["artifacts"][0]["sha256"]=sha; b["observations"][0].update(artifact=sha,pointer="/a~1b/~/1/x",value="y"); b["findings"][0]["artifacts"]=[sha]
        self.assertIn("INVALID_JSON_POINTER",e.check_bundle(b)["errors"])
        b["observations"][0]["pointer"]="/a~1b/~0/1/x"
        with tempfile.TemporaryDirectory() as d:
            Path(d,"art.json").write_bytes(raw); self.assertEqual(e.verify_artifact_root(b,d)["status"],"pass")

if __name__=="__main__": unittest.main()
