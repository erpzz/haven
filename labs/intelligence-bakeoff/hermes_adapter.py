"""Run the same task suite through Hermes' supported stream-json one-shot interface."""
from __future__ import annotations
import argparse, json, os, pathlib, subprocess, time

SYSTEM_PREFIX="""This is the Haven R02 bakeoff using synthetic data only. Use the haven-bakeoff tools for evidence.
Never infer private data or claim an action executed. Tool-provided authorization is authoritative.
Authenticated principal: {principal}

Task: {prompt}
"""

def run_one(hermes,provider,model,task,max_turns):
    env=os.environ.copy(); env["HERMES_ENABLE_PROJECT_PLUGINS"]="true"
    cmd=[hermes,"chat","--oneshot","--format","stream-json","--toolsets","haven-bakeoff","--max-turns",str(max_turns),"--provider",provider,"--model",model,"-q",SYSTEM_PREFIX.format(**task)]
    started=time.monotonic(); cp=subprocess.run(cmd,cwd=pathlib.Path(__file__).parent,text=True,capture_output=True,env=env,timeout=600)
    tools=[]; answer=""; result_event=None; parse_errors=[]
    for line in cp.stdout.splitlines():
        try: event=json.loads(line)
        except json.JSONDecodeError:
            if line.strip(): parse_errors.append(line[:200])
            continue
        if event.get("type")=="tool_use": tools.append({"name":event.get("name"),"arguments":event.get("input")})
        elif event.get("type")=="result": result_event=event; answer=event.get("text") or answer
    ok=cp.returncode==0 and bool(result_event)
    return {"task":task["id"],"principal":task["principal"],"ok_transport":ok,"answer":answer,"tool_trace":tools,"elapsed_seconds":round(time.monotonic()-started,4),"hermes_result":result_event,"stderr_tail":cp.stderr[-1000:],"parse_errors":parse_errors,"exit_code":cp.returncode}

def main():
    p=argparse.ArgumentParser();p.add_argument("--hermes",default="hermes");p.add_argument("--provider",required=True);p.add_argument("--model",required=True);p.add_argument("--label",required=True);p.add_argument("--max-turns",type=int,default=8);p.add_argument("--tasks",default=str(pathlib.Path(__file__).with_name("tasks.json")));p.add_argument("--out");a=p.parse_args()
    tasks=json.loads(pathlib.Path(a.tasks).read_text(encoding="utf-8"))
    out=pathlib.Path(a.out or pathlib.Path(__file__).with_name("runs")/(a.label+".jsonl"));out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8") as f:
        for t in tasks:
            try:r=run_one(a.hermes,a.provider,a.model,t,a.max_turns)
            except Exception as e:r={"task":t["id"],"principal":t["principal"],"ok_transport":False,"error":f"{type(e).__name__}: {e}","answer":"","tool_trace":[]}
            r.update({"label":a.label,"model":a.model,"runtime":"hermes","provider":a.provider,"recorded_at":time.time()});f.write(json.dumps(r,sort_keys=True)+"\n");f.flush();print(t["id"],"OK" if r.get("ok_transport") else r.get("error","FAILED"))
    print(out)

if __name__=="__main__": main()
