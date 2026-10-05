"""Hermes project plugin exposing the same synthetic Haven tools as the thin runner."""
from __future__ import annotations
import json, os, pathlib, sys, time
ROOT=pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from synthetic_tools import TOOL_SCHEMAS, dispatch

def _schema(name):
    for item in TOOL_SCHEMAS:
        fn=item["function"]
        if fn["name"]==name: return {"name":name,"description":fn["description"],"parameters":fn["parameters"]}
    raise KeyError(name)

def _handler(name):
    def call(params, **kwargs):
        return dispatch(name,dict(params or {}))
    return call

def _trace(tool_name, args, result, **kwargs):
    if not tool_name.startswith("haven_"): return
    path=os.environ.get("HAVEN_BAKEOFF_TRACE")
    if not path: return
    pathlib.Path(path).parent.mkdir(parents=True,exist_ok=True)
    with open(path,"a",encoding="utf-8") as f:
        f.write(json.dumps({"at":time.time(),"tool":tool_name,"arguments":args,"result":result},sort_keys=True)+"\n")

def register(ctx):
    for name in ("haven_read_note","haven_device_state","haven_propose_action"):
        ctx.register_tool(name=name,toolset="haven-bakeoff",schema=_schema(name),handler=_handler(name))
    ctx.register_hook("post_tool_call",_trace)
