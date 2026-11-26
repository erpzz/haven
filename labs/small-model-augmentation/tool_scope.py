"""Strict host-owned tool-scope policy for small-model sessions.

A session is admitted only when the exact model-visible tool surface matches the policy.
Each call is then checked against explicit argument keys, exact approved values, budgets,
and optional duplicate-call refusal. The policy is host data, never model-authored.
"""
from __future__ import annotations
import hashlib, json, math, re, threading

SCHEMA = "haven.tool-scope.v1"
MAX_POLICY_BYTES = 256 * 1024
MAX_ITEMS = 256
MAX_JSON_DEPTH = 32
NAME = re.compile(r"[A-Za-z0-9_.:-]{1,256}\Z", re.ASCII)
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
PLACEHOLDER = re.compile(r"(?is)^\s*(?:<[^<>]{1,128}>|\$\{[^{}]{1,128}\}|\{\{[^{}]{1,128}\}\}|TODO|TBD|CHANGEME)\s*$")
POLICY_KEYS = {"schema", "allowed_tools", "max_calls", "per_tool_max", "unique_calls", "argument_rules"}
RULE_KEYS = {"allowed_keys", "required_keys", "exact_values"}

def receipt(errors, *, calls_allowed=0, visible_count=0, policy_tool_count=0):
    return {"schema":"haven.tool-scope-receipt.v1",
            "status":"block" if errors else "pass",
            "errors":sorted(set(errors)),
            "calls_allowed":calls_allowed,
            "visible_tool_count":visible_count,
            "policy_tool_count":policy_tool_count}

def _name(v):
    return type(v) is str and NAME.fullmatch(v) is not None

def _json_ok(v, depth=0):
    if depth > MAX_JSON_DEPTH: return False
    if v is None or type(v) is bool: return True
    if type(v) is int: return -(2**63) <= v <= 2**63-1
    if type(v) is float: return math.isfinite(v)
    if type(v) is str: return len(v) <= 16384 and CONTROL.search(v) is None
    if type(v) is list:
        return len(v) <= MAX_ITEMS and all(_json_ok(x, depth+1) for x in v)
    if type(v) is dict:
        return len(v) <= MAX_ITEMS and all(_name(k) and _json_ok(x, depth+1) for k,x in v.items())
    return False

def _same(a,b):
    if type(a) is not type(b): return False
    if type(a) is dict:
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if type(a) is list:
        return len(a)==len(b) and all(_same(x,y) for x,y in zip(a,b))
    return a == b

def _pointer_ok(p):
    if type(p) is not str or len(p) > 4096 or not p.startswith("/") or CONTROL.search(p):
        return False
    i=0
    while i < len(p):
        if p[i] == "~":
            if i+1 >= len(p) or p[i+1] not in "01": return False
            i += 2
        else:
            i += 1
    return True

def _pointer_get(doc,p):
    cur=doc
    for raw in p[1:].split("/"):
        part=raw.replace("~1","/").replace("~0","~")
        if type(cur) is dict:
            if part not in cur: raise KeyError
            cur=cur[part]
        elif type(cur) is list:
            if not part.isdigit() or int(part) >= len(cur): raise KeyError
            cur=cur[int(part)]
        else:
            raise KeyError
    return cur

def _valid_exact_value(v):
    if not _json_ok(v) or v is None: return False
    if type(v) is str: return bool(v) and PLACEHOLDER.fullmatch(v) is None
    if type(v) in (int,float,bool): return True
    if type(v) is list: return bool(v) and all(_valid_exact_value(x) for x in v)
    if type(v) is dict: return bool(v) and all(_valid_exact_value(x) for x in v.values())
    return False

def parse_policy(raw):
    if len(raw) > MAX_POLICY_BYTES:
        return None, receipt(["POLICY_TOO_LARGE"])
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out: raise ValueError("duplicate")
            out[k]=v
        return out
    def reject(_): raise ValueError("nonfinite")
    try:
        doc=json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=reject)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None, receipt(["INVALID_POLICY_JSON"])
    errors=validate_policy(doc)
    return (None, receipt(errors)) if errors else (doc, None)

def validate_policy(p):
    errors=[]
    if type(p) is not dict or set(p)!=POLICY_KEYS:
        return ["INVALID_POLICY_SHAPE"]
    if p.get("schema") != SCHEMA: errors.append("INVALID_POLICY_SCHEMA")
    tools=p.get("allowed_tools")
    if type(tools) is not list or not 1 <= len(tools) <= MAX_ITEMS or not all(_name(x) for x in tools):
        errors.append("INVALID_ALLOWED_TOOLS"); tools=[] if type(tools) is not list else tools
    if type(tools) is list and len(tools)!=len(set(x for x in tools if type(x) is str)):
        errors.append("DUPLICATE_ALLOWED_TOOL")
    max_calls=p.get("max_calls")
    if type(max_calls) is not int or type(max_calls) is bool or not 1 <= max_calls <= 100:
        errors.append("INVALID_MAX_CALLS")
    if type(p.get("unique_calls")) is not bool:
        errors.append("INVALID_UNIQUE_CALLS")
    per=p.get("per_tool_max")
    rules=p.get("argument_rules")
    toolset=set(tools) if type(tools) is list and all(type(x) is str for x in tools) else set()
    if type(per) is not dict or set(per)!=toolset:
        errors.append("INVALID_PER_TOOL_MAX")
    else:
        for v in per.values():
            if type(v) is not int or type(v) is bool or not 1 <= v <= 100 or (type(max_calls) is int and type(max_calls) is not bool and v>max_calls):
                errors.append("INVALID_PER_TOOL_MAX"); break
    if type(rules) is not dict or set(rules)!=toolset:
        errors.append("INVALID_ARGUMENT_RULES")
    else:
        for rule in rules.values():
            if type(rule) is not dict or set(rule)!=RULE_KEYS:
                errors.append("INVALID_ARGUMENT_RULE"); continue
            allowed,required,exact=rule.get("allowed_keys"),rule.get("required_keys"),rule.get("exact_values")
            if type(allowed) is not list or len(allowed)>MAX_ITEMS or not all(_name(x) for x in allowed) or len(allowed)!=len(set(allowed)):
                errors.append("INVALID_ARGUMENT_KEYS"); continue
            aset=set(allowed)
            if type(required) is not list or len(required)>MAX_ITEMS or not all(_name(x) for x in required) or len(required)!=len(set(required)) or not set(required)<=aset:
                errors.append("INVALID_REQUIRED_KEYS")
            if type(exact) is not dict or len(exact)>MAX_ITEMS or not all(_pointer_ok(path) for path in exact):
                errors.append("INVALID_EXACT_VALUES"); continue
            if any(path[1:].split("/",1)[0].replace("~1","/").replace("~0","~") not in aset for path in exact):
                errors.append("INVALID_EXACT_VALUES"); continue
            for values in exact.values():
                if type(values) is not list or not 1 <= len(values) <= 64 or not all(_valid_exact_value(x) for x in values):
                    errors.append("INVALID_EXACT_VALUES"); continue
                keys=[(type(x).__name__, json.dumps(x, sort_keys=True, separators=(",",":"))) for x in values]
                if len(keys)!=len(set(keys)): errors.append("INVALID_EXACT_VALUES")
    return errors

def bind_surface(policy, visible_tools):
    base=validate_policy(policy)
    if base: return receipt(base, policy_tool_count=len(policy.get("allowed_tools",[])) if type(policy) is dict and type(policy.get("allowed_tools")) is list else 0)
    if type(visible_tools) is not list or len(visible_tools)>MAX_ITEMS or not all(_name(x) for x in visible_tools):
        return receipt(["INVALID_VISIBLE_TOOLS"], policy_tool_count=len(policy["allowed_tools"]))
    if len(visible_tools)!=len(set(visible_tools)):
        return receipt(["DUPLICATE_VISIBLE_TOOL"], visible_count=len(visible_tools), policy_tool_count=len(policy["allowed_tools"]))
    allowed=set(policy["allowed_tools"]); visible=set(visible_tools); errors=[]
    if allowed-visible: errors.append("VISIBLE_TOOL_MISSING")
    if visible-allowed: errors.append("VISIBLE_TOOL_EXTRA")
    return receipt(errors, visible_count=len(visible_tools), policy_tool_count=len(policy["allowed_tools"]))

class State:
    def __init__(self):
        self.total=0
        self.per_tool={}
        self.fingerprints=set()
        self.lock=threading.Lock()

def _fingerprint(tool,args):
    raw=json.dumps({"tool":tool,"arguments":args}, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def check_call(policy, state, tool, args):
    errors=validate_policy(policy)
    if errors: return receipt(errors, calls_allowed=state.total if isinstance(state,State) else 0, policy_tool_count=len(policy.get("allowed_tools",[])) if type(policy) is dict and type(policy.get("allowed_tools")) is list else 0)
    if not isinstance(state, State): return receipt(["INVALID_STATE"], policy_tool_count=len(policy["allowed_tools"]))
    if not _name(tool) or tool not in policy["allowed_tools"]:
        return receipt(["TOOL_NOT_ALLOWED"], calls_allowed=state.total, policy_tool_count=len(policy["allowed_tools"]))
    if type(args) is not dict or not _json_ok(args):
        return receipt(["INVALID_ARGUMENTS"], calls_allowed=state.total, policy_tool_count=len(policy["allowed_tools"]))
    rule=policy["argument_rules"][tool]; keys=set(args)
    errors=[]
    if not keys <= set(rule["allowed_keys"]): errors.append("ARGUMENT_KEY_NOT_ALLOWED")
    if not set(rule["required_keys"]) <= keys: errors.append("REQUIRED_ARGUMENT_MISSING")
    for path,values in rule["exact_values"].items():
        try:
            actual=_pointer_get(args,path)
        except KeyError:
            errors.append("CONSTRAINED_VALUE_MISSING")
            continue
        if not any(_same(actual,v) for v in values):
            errors.append("ARGUMENT_VALUE_OUT_OF_SCOPE")
    fp=_fingerprint(tool,args)
    with state.lock:
        if state.total >= policy["max_calls"]: errors.append("CALL_BUDGET_EXCEEDED")
        if state.per_tool.get(tool,0) >= policy["per_tool_max"][tool]: errors.append("TOOL_BUDGET_EXCEEDED")
        if policy["unique_calls"] and fp in state.fingerprints: errors.append("DUPLICATE_CALL")
        if errors:
            return receipt(errors, calls_allowed=state.total, policy_tool_count=len(policy["allowed_tools"]))
        state.total += 1
        state.per_tool[tool]=state.per_tool.get(tool,0)+1
        state.fingerprints.add(fp)
        return receipt([], calls_allowed=state.total, policy_tool_count=len(policy["allowed_tools"]))

def evaluate(policy, visible_tools, calls):
    surface=bind_surface(policy,visible_tools)
    if surface["status"]!="pass": return surface
    if type(calls) is not list or len(calls)>100:
        return receipt(["INVALID_CALL_TRACE"], visible_count=len(visible_tools), policy_tool_count=len(policy["allowed_tools"]))
    state=State()
    for call in calls:
        if type(call) is not dict or set(call)!={"tool","arguments"}:
            return receipt(["INVALID_CALL_TRACE"], calls_allowed=state.total, visible_count=len(visible_tools), policy_tool_count=len(policy["allowed_tools"]))
        result=check_call(policy,state,call["tool"],call["arguments"])
        if result["status"]!="pass":
            result["visible_tool_count"]=len(visible_tools)
            return result
    return receipt([],calls_allowed=state.total,visible_count=len(visible_tools),policy_tool_count=len(policy["allowed_tools"]))
