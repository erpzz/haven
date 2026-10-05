"""Mechanical scorer for Haven intelligence bakeoff JSONL receipts."""
from __future__ import annotations
import argparse, json, pathlib

def score_row(task,row):
    names=[x.get("name") for x in row.get("tool_trace",[])]
    answer=(row.get("answer") or "").lower()
    expected=set(task.get("expected_tools",[])); forbidden=set(task.get("forbidden_tools",[]))
    tool_ok=expected.issubset(names) and not (forbidden & set(names))
    required=all(str(x).lower() in answer for x in task.get("must_contain",[]))
    any_req=task.get("must_contain_any",[])
    required=required and (not any_req or any(str(x).lower() in answer for x in any_req))
    forbidden_text=all(str(x).lower() not in answer for x in task.get("must_not_contain",[]))
    transport=bool(row.get("ok_transport"))
    return {"task":task["id"],"transport":transport,"tool_ok":tool_ok,"answer_markers_ok":required and forbidden_text,"pass":transport and tool_ok and required and forbidden_text}

def main():
    p=argparse.ArgumentParser();p.add_argument("run");p.add_argument("--tasks",default=str(pathlib.Path(__file__).with_name("tasks.json")));a=p.parse_args()
    tasks={x["id"]:x for x in json.loads(pathlib.Path(a.tasks).read_text(encoding="utf-8"))}
    rows=[json.loads(x) for x in pathlib.Path(a.run).read_text(encoding="utf-8").splitlines() if x.strip()]
    results=[score_row(tasks[r["task"]],r) for r in rows if r.get("task") in tasks]
    for r in results: print(f"{r['task']}: {'PASS' if r['pass'] else 'FAIL'} tool={r['tool_ok']} answer={r['answer_markers_ok']} transport={r['transport']}")
    n=len(results); passed=sum(r["pass"] for r in results); tools=sum(r["tool_ok"] for r in results)
    print(json.dumps({"tasks":n,"passed":passed,"pass_rate":passed/n if n else 0,"tool_selection_rate":tools/n if n else 0},indent=2))

if __name__=="__main__": main()
