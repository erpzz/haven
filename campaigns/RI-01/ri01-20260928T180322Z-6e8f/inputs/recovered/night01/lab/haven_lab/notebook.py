"""N2 inert engineering notebook. No CAD, printer, radio or robot interfaces."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import sys
from uuid import uuid4
from . import LABEL
from .types import Denied, canonical, digest, now
from .store import LAB_ROOT
from .synthetic_score import score, METRIC_VERSION, FORMULA
from .design_check import evaluate, CHECK_VERSION

OUTPUTS = LAB_ROOT.parent/"outputs"

N1_SOURCE_PATHS = frozenset({
    "haven_lab/__init__.py", "haven_lab/__main__.py", "haven_lab/backend.py", "haven_lab/cli.py",
    "haven_lab/context.py", "haven_lab/coordinator.py", "haven_lab/render.py", "haven_lab/store.py",
    "haven_lab/types.py", "haven_lab/validation.py", "fixtures/context.json", "tests/test_n1.py"})

def check_gate_evidence(gate,log):
    import ast
    if type(gate) is not dict or gate.get("status")!="EXECUTED_PASS" or gate.get("scope")!="N1_SYNTHETIC_ONLY":
        raise Denied("N1_GATE_NOT_PASSED")
    if type(gate.get("source_hashes")) is not dict or set(gate["source_hashes"]) != N1_SOURCE_PATHS:
        raise Denied("N1_GATE_SOURCE_SET")
    for field in ("exit_code","failures","errors","skips"):
        if type(log.get(field)) is not int or log[field] != 0:
            raise Denied("N1_TESTS_NOT_PASSING")
    if log.get("suite") != "n1" or log.get("label") != LABEL or log.get("scope") != "SYNTHETIC_LAB_ONLY":
        raise Denied("N1_TEST_SCOPE")
    tree=ast.parse((LAB_ROOT/"tests/test_n1.py").read_text())
    expected={"test_n1.N1Tests."+node.name for cls in tree.body if isinstance(cls,ast.ClassDef) and cls.name=="N1Tests"
              for node in cls.body if isinstance(node,ast.FunctionDef) and node.name.startswith("test_")}
    rows=log.get("tests")
    if type(rows) is not list or len(expected)<32 or type(log.get("tests_run")) is not int or log["tests_run"]!=len(expected) or gate.get("tests")!=len(expected) or len(rows)!=len(expected):
        raise Denied("N1_TEST_COVERAGE")
    if any(type(row) is not dict or row.get("status")!="EXECUTED_PASS" for row in rows) or {row.get("id") for row in rows}!=expected:
        raise Denied("N1_TEST_COVERAGE")
    run_sources=log.get("source_sha256",{})
    if any(run_sources.get(name)!=sha for name,sha in gate["source_hashes"].items()):
        raise Denied("N1_TEST_SOURCE_MISMATCH")

def verify_n1_gate():
    gate_path=OUTPUTS/"N1_GATE.json"
    gate=json.loads(gate_path.read_text())
    log_relative=gate.get("test_log")
    if type(log_relative) is not str or not log_relative.startswith("outputs/logs/") or ".." in Path(log_relative).parts:
        raise Denied("N1_GATE_LOG_PATH")
    test_log=LAB_ROOT.parent/log_relative
    if test_log.is_symlink() or not test_log.resolve().is_relative_to((OUTPUTS/"logs").resolve()):
        raise Denied("N1_GATE_LOG_PATH")
    raw=test_log.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=gate["test_log_sha256"]:
        raise Denied("N1_TEST_EVIDENCE_CHANGED")
    check_gate_evidence(gate,json.loads(raw))
    for relative,expected in gate["source_hashes"].items():
        path=LAB_ROOT/relative
        if not path.resolve().is_relative_to(LAB_ROOT.resolve()) or path.is_symlink():
            raise Denied("N1_GATE_PATH")
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise Denied("N1_CHANGED_REQUALIFICATION_REQUIRED")
    return hashlib.sha256(gate_path.read_bytes()).hexdigest()

def check_design(design):
    fields={"artifact_id","revision","parent_artifact_ids","units","dimensions","qualification_state",
            "fabrication_enabled","synthetic","artifact_kind"}
    if type(design) is not dict or set(design)!=fields:
        raise Denied("DESIGN_FIELDS")
    if design["units"]!="mm" or design["qualification_state"]!="UNQUALIFIED" or design["fabrication_enabled"] is not False or design["synthetic"] is not True or design["artifact_kind"]!="INERT_JSON_DIMENSIONS":
        raise Denied("DESIGN_AUTHORITY_OR_LABEL")
    if type(design["artifact_id"]) is not str or re.fullmatch(r"[A-Z][A-Z0-9_]{0,39}",design["artifact_id"]) is None:
        raise Denied("DESIGN_ID")
    if type(design["parent_artifact_ids"]) is not list or len(design["parent_artifact_ids"]) > 1 or any(type(x) is not str for x in design["parent_artifact_ids"]):
        raise Denied("DESIGN_PARENTS")
    if type(design["revision"]) is not int or not 1<=design["revision"]<=6:
        raise Denied("DESIGN_REVISION")
    d=design["dimensions"]
    if type(d) is not dict or set(d)!={"base_mm","depth_mm","height_mm","thickness_mm","slot_mm"}:
        raise Denied("DIMENSION_FIELDS")
    for v in d.values():
        if type(v) not in (int,float) or not math.isfinite(v) or not 1<=v<=100:
            raise Denied("DIMENSION_BOUNDS")

def promote(design,evaluation,target):
    """No physical ACCEPTED or fabrication transition exists in NIGHT-01."""
    check_design(design)
    if not evaluation or evaluation.get("status")!="PASS" or evaluation.get("design_sha256")!=digest(design):
        raise Denied("MISSING_REJECTED_OR_MISMATCHED_EVALUATION")
    raise Denied("PHYSICAL_PROMOTION_AND_FABRICATION_NOT_AUTHORIZED")

def campaign(inputs):
    if type(inputs) is not dict or set(inputs)!={"schema_version","label","hypothesis","baseline","candidates","max_iterations","metric_version"}:
        raise Denied("CAMPAIGN_FIELDS")
    if type(inputs["schema_version"]) is not int or inputs["schema_version"]!=1 or inputs["label"]!=LABEL or inputs["metric_version"]!=METRIC_VERSION:
        raise Denied("CAMPAIGN_VERSION")
    if type(inputs["max_iterations"]) is not int or not 1<=inputs["max_iterations"]<=5:
        raise Denied("ITERATION_LIMIT")
    if type(inputs["hypothesis"]) is not str or not 1 <= len(inputs["hypothesis"]) <= 1000:
        raise Denied("HYPOTHESIS_REQUIRED")
    candidates=inputs["candidates"]
    if type(candidates) is not list or not 1<=len(candidates)<=inputs["max_iterations"]:
        raise Denied("ITERATION_LIMIT")
    baseline=inputs["baseline"];check_design(baseline)
    if baseline["parent_artifact_ids"] != []:
        raise Denied("BASELINE_PROVENANCE")
    known={baseline["artifact_id"]}
    for design in candidates:
        check_design(design)
        if design["artifact_id"] in known or design["parent_artifact_ids"]!=[baseline["artifact_id"]]:
            raise Denied("DESIGN_PROVENANCE")
        known.add(design["artifact_id"])
    bscore=score(baseline["dimensions"])
    baseline_result={"design":baseline,"design_sha256":digest(baseline),"score":bscore,"evaluation":evaluate(baseline)}
    results=[]
    for design in candidates:
        value=score(design["dimensions"]);check=evaluate(design)
        results.append({"design":design,"design_sha256":digest(design),"score":value,
                        "delta_from_baseline":round(value-bscore,6),"evaluation":check,
                        "outcome":"SYNTHETIC_IMPROVEMENT" if value<bscore and check["status"]=="PASS" else
                            "CHECK_REJECTED" if check["status"]!="PASS" else "NO_IMPROVEMENT",
                        "qualification_state":"UNQUALIFIED","fabrication_enabled":False})
    eligible=[x for x in results if x["outcome"]=="SYNTHETIC_IMPROVEMENT"]
    best=min(eligible,key=lambda x:(x["score"],x["design"]["artifact_id"])) if eligible else None
    return {"schema_version":1,"label":LABEL,"synthetic_objective_only":True,
            "hypothesis":inputs["hypothesis"],"original_inputs":inputs,"input_sha256":digest(inputs),
            "metric":{"version":METRIC_VERSION,"formula":FORMULA,"direction":"MINIMIZE"},
            "checker":CHECK_VERSION,"baseline":baseline_result,"results":results,
            "iterations":len(results),"max_iterations":inputs["max_iterations"],
            "decision":"PROPOSE_NEXT_FOR_REVIEW" if best else "STOP_NO_ELIGIBLE_IMPROVEMENT",
            "next_candidate":best["design"]["artifact_id"] if best else None,
            "physical_measurements":0,"physical_permission":"NOT_GRANTED","fabrication_enabled":False,
            "qualification_state":"UNQUALIFIED",
            "limits":"Arithmetic fixture objective; not structural validation, physical performance, AI-discovered invention or autonomous engineering qualification."}

def main(argv=None):
    parser=argparse.ArgumentParser(description=LABEL+" — N2 synthetic experiment")
    parser.parse_args(argv)
    if sys.version_info[:2]!=(3,12):
        parser.error("Python 3.12 required")
    try:
        gate=verify_n1_gate()
        input_path=LAB_ROOT/"fixtures/engineering.json"
        inputs=json.loads(input_path.read_text())
        result=campaign(inputs)
        result["run_id"]="n2-"+str(uuid4());result["executed_at"]=now();result["n1_gate_sha256"]=gate
        result["source_sha256"]={name:hashlib.sha256((LAB_ROOT/"haven_lab"/name).read_bytes()).hexdigest()
                                 for name in ("notebook.py","synthetic_score.py","design_check.py")}
        directory=OUTPUTS/result["run_id"];directory.mkdir(mode=0o700)
        (directory/"original_inputs.json").write_bytes(input_path.read_bytes())
        (directory/"results.json").write_text(json.dumps(result,indent=2)+"\n")
        for record in [result["baseline"],*result["results"]]:
            design=record["design"]
            (directory/(design["artifact_id"]+".json")).write_text(canonical(design)+"\n")
        text=["# N2 synthetic engineering notebook", "", LABEL,
              "",result["limits"],"", "Hypothesis: "+result["hypothesis"],
              "Metric (fixed before execution): "+FORMULA,"", "| Design | Score | Check | Outcome |",
              "| --- | ---: | --- | --- |",f"| BASELINE | {result['baseline']['score']} | {result['baseline']['evaluation']['status']} | BASELINE |"]
        text.extend(f"| {x['design']['artifact_id']} | {x['score']} | {x['evaluation']['status']} | {x['outcome']} |" for x in result["results"])
        text += ["", "Decision: "+result["decision"]+"; next candidate: "+str(result["next_candidate"]),
                 "All candidates UNQUALIFIED. Fabrication disabled. Original inputs, rejected candidates and negative results retained.",
                 "The separate checker is deterministic software authored by the same writer; it is not independent physical validation."]
        (directory/"REPORT.md").write_text("\n".join(text)+"\n")
        print(json.dumps({"label":LABEL,"status":"SYNTHETIC_COMPLETED","output":str(directory),"iterations":result["iterations"],"decision":result["decision"],"next_candidate":result["next_candidate"]}))
        return 0
    except (Denied,ValueError,OSError) as exc:
        print(json.dumps({"label":LABEL,"status":"BLOCKED","reason":str(exc)}),file=sys.stderr)
        return 2

if __name__=="__main__":raise SystemExit(main())
