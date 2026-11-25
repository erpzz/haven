"""Strict admission for haven-cyber-evidence-v1 bundles before independent verification.

This is a structural/lineage gate for untrusted or model-adjacent evidence. It does not
replace domain re-derivation. Receipts contain fixed codes and counts only.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, sys
from pathlib import Path

SCHEMA = "haven-cyber-evidence-v1"
MAX_BUNDLE_BYTES = 8 * 1024 * 1024
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
MAX_ITEMS = 10_000
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
ARTIFACT_KEYS = {"sha256","path","media_type","source_tool","collected_at"}
OBS_KEYS = {"id","artifact","pointer","value","note"}
FINDING_KEYS = {"id","title","domain","service","source_tool","source_check_id","resource_id","environment",
                "observation_point","status","description","severity","confidence","collected_at","observations",
                "artifacts","controls","remediation","references","limitations","next_validation_step",
                "verification","verification_notes","inferred"}
SEVERITIES = {"critical","high","medium","low","informational"}
STATUSES = {"fail","pass","manual","error","skipped","not_applicable"}

def receipt(errors, *, artifacts=0, observations=0, findings=0, artifacts_checked=0):
    return {"schema":"haven.evidence-admission.v1","status":"block" if errors else "pass",
            "errors":sorted(set(errors)),"artifacts":artifacts,"observations":observations,
            "findings":findings,"artifacts_checked":artifacts_checked}

def _plain(v): return type(v) is dict
def _text(v, limit=4096): return type(v) is str and 0 < len(v) <= limit and CONTROL.search(v) is None
def _str_list(v, limit=MAX_ITEMS):
    return type(v) is list and len(v) <= limit and all(type(x) is str and len(x) <= 4096 and CONTROL.search(x) is None for x in v)
def _safe_rel_path(value):
    if not _text(value, 4096): return False
    if value.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[\\/]", value): return False
    parts=[p for p in re.split(r"[\\/]+", value) if p not in ("",".")]
    return bool(parts) and ".." not in parts

def _pointer_ok(p):
    if type(p) is not str or len(p)>4096 or CONTROL.search(p): return False
    if p=="": return True
    if not p.startswith("/"): return False
    i=0
    while i<len(p):
        if p[i]=="~":
            if i+1>=len(p) or p[i+1] not in "01": return False
            i+=2
        else: i+=1
    return True

def _json_pointer(doc,p):
    if p=="": return doc
    cur=doc
    for raw in p[1:].split("/"):
        part=raw.replace("~1","/").replace("~0","~")
        if type(cur) is list:
            if not part.isdigit(): raise KeyError
            idx=int(part)
            if idx>=len(cur): raise KeyError
            cur=cur[idx]
        elif type(cur) is dict:
            if part not in cur: raise KeyError
            cur=cur[part]
        else: raise KeyError
    return cur

def _strict_equal(a,b):
    if type(a) is not type(b): return False
    if type(a) is dict:
        return a.keys()==b.keys() and all(_strict_equal(a[k],b[k]) for k in a)
    if type(a) is list:
        return len(a)==len(b) and all(_strict_equal(x,y) for x,y in zip(a,b))
    return a==b

def _load_json_bytes(raw):
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out: raise ValueError("duplicate")
            out[k]=v
        return out
    def reject_constant(_): raise ValueError("nonfinite")
    return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique, parse_constant=reject_constant)

def check_bundle(doc):
    errors=[]
    if not _plain(doc) or set(doc)!={"schema","artifacts","observations","findings"}:
        return receipt(["INVALID_TOP_LEVEL"])
    if doc.get("schema")!=SCHEMA: errors.append("INVALID_SCHEMA")
    arts,obs,finds=doc.get("artifacts"),doc.get("observations"),doc.get("findings")
    if type(arts) is not list or type(obs) is not list or type(finds) is not list:
        return receipt(errors+["INVALID_COLLECTIONS"])
    if any(len(x)>MAX_ITEMS for x in (arts,obs,finds)): errors.append("TOO_MANY_ITEMS")
    amap={}; oids=set(); fmap=set(); omap={}
    for a in arts[:MAX_ITEMS+1]:
        if not _plain(a) or set(a)!=ARTIFACT_KEYS: errors.append("INVALID_ARTIFACT"); continue
        sha=a.get("sha256")
        if type(sha) is not str or HEX64.fullmatch(sha) is None: errors.append("INVALID_ARTIFACT_HASH")
        elif sha in amap: errors.append("DUPLICATE_ARTIFACT_HASH")
        else: amap[sha]=a
        if not _safe_rel_path(a.get("path")): errors.append("UNSAFE_ARTIFACT_PATH")
        for k in ("media_type","source_tool","collected_at"):
            if not _text(a.get(k),4096): errors.append("INVALID_ARTIFACT_METADATA")
    for o in obs[:MAX_ITEMS+1]:
        if not _plain(o) or set(o)!=OBS_KEYS: errors.append("INVALID_OBSERVATION"); continue
        oid=o.get("id")
        if not _text(oid,256): errors.append("INVALID_OBSERVATION_ID")
        elif oid in oids: errors.append("DUPLICATE_OBSERVATION_ID")
        else: oids.add(oid); omap[oid]=o
        if type(o.get("artifact")) is not str or o.get("artifact") not in amap: errors.append("UNDECLARED_OBSERVATION_ARTIFACT")
        if not _pointer_ok(o.get("pointer")): errors.append("INVALID_JSON_POINTER")
        if type(o.get("note")) is not str or len(o.get("note"))>4096 or CONTROL.search(o.get("note")): errors.append("INVALID_OBSERVATION_NOTE")
    for f in finds[:MAX_ITEMS+1]:
        if not _plain(f) or set(f)!=FINDING_KEYS: errors.append("INVALID_FINDING"); continue
        fid=f.get("id")
        if not _text(fid,512): errors.append("INVALID_FINDING_ID")
        elif fid in fmap: errors.append("DUPLICATE_FINDING_ID")
        else: fmap.add(fid)
        for k in ("title","domain","service","source_tool","source_check_id","resource_id","environment","observation_point",
                  "description","collected_at"):
            if not _text(f.get(k),4096): errors.append("INVALID_FINDING_TEXT")
        if f.get("severity") not in SEVERITIES: errors.append("INVALID_SEVERITY")
        if f.get("status") not in STATUSES: errors.append("INVALID_STATUS")
        c=f.get("confidence")
        if type(c) not in (int,float) or type(c) is bool or not math.isfinite(c) or not 0<=c<=1: errors.append("INVALID_CONFIDENCE")
        if type(f.get("inferred")) is not bool: errors.append("INVALID_INFERRED")
        for k in ("observations","artifacts","controls","references","limitations","verification_notes"):
            if not _str_list(f.get(k)): errors.append("INVALID_FINDING_LIST")
        if type(f.get("remediation")) is not str or len(f.get("remediation"))>8192 or CONTROL.search(f.get("remediation")): errors.append("INVALID_REMEDIATION")
        if type(f.get("next_validation_step")) is not str or len(f.get("next_validation_step"))>8192 or CONTROL.search(f.get("next_validation_step")): errors.append("INVALID_NEXT_VALIDATION")
        if f.get("verification")!="reported" or f.get("verification_notes")!=[]: errors.append("PREVERIFIED_FINDING")
        fo=f.get("observations") if type(f.get("observations")) is list else []
        fa=f.get("artifacts") if type(f.get("artifacts")) is list else []
        if len(fo)!=len(set(fo)) or len(fa)!=len(set(fa)): errors.append("DUPLICATE_FINDING_REFERENCE")
        if any(x not in omap for x in fo): errors.append("UNKNOWN_FINDING_OBSERVATION")
        if any(x not in amap for x in fa): errors.append("UNKNOWN_FINDING_ARTIFACT")
        linked={omap[x]["artifact"] for x in fo if x in omap and type(omap[x]) is dict and omap[x].get("artifact") in amap}
        if set(fa)!=linked: errors.append("FINDING_LINEAGE_MISMATCH")
        if f.get("status") in ("pass","fail") and (not fo or not fa): errors.append("DECISIVE_FINDING_WITHOUT_EVIDENCE")
        if f.get("status")=="fail" and not f.get("remediation"): errors.append("FAILING_FINDING_WITHOUT_REMEDIATION")
    return receipt(errors,artifacts=len(arts),observations=len(obs),findings=len(finds))

def verify_artifact_root(doc, root):
    base=check_bundle(doc)
    if base["status"]!="pass": return base
    errors=[]; checked=0
    root=Path(root).resolve()
    amap={a["sha256"]:a for a in doc["artifacts"]}
    needed={o["artifact"] for o in doc["observations"]}
    cache={}
    for sha in needed:
        ref=amap[sha]
        try:
            p=(root/ref["path"]).resolve()
            p.relative_to(root)
        except (OSError, ValueError):
            errors.append("ARTIFACT_ESCAPES_ROOT"); continue
        try:
            if not p.is_file(): errors.append("ARTIFACT_MISSING"); continue
            with p.open("rb") as fh:
                raw=fh.read(MAX_ARTIFACT_BYTES+1)
        except OSError:
            errors.append("ARTIFACT_READ_FAILED"); continue
        if len(raw)>MAX_ARTIFACT_BYTES: errors.append("ARTIFACT_TOO_LARGE"); continue
        if hashlib.sha256(raw).hexdigest()!=sha: errors.append("ARTIFACT_HASH_MISMATCH"); continue
        try: cache[sha]=_load_json_bytes(raw)
        except (UnicodeDecodeError,ValueError,RecursionError):
            errors.append("ARTIFACT_JSON_INVALID"); continue
        checked+=1
    for o in doc["observations"]:
        if o["artifact"] not in cache: continue
        try: actual=_json_pointer(cache[o["artifact"]],o["pointer"])
        except KeyError:
            errors.append("OBSERVATION_POINTER_UNRESOLVED"); continue
        if not _strict_equal(actual,o["value"]): errors.append("OBSERVATION_VALUE_MISMATCH")
    return receipt(errors,artifacts=len(doc["artifacts"]),observations=len(doc["observations"]),
                   findings=len(doc["findings"]),artifacts_checked=checked)

def parse_bundle(raw):
    if len(raw)>MAX_BUNDLE_BYTES: return None, receipt(["BUNDLE_TOO_LARGE"])
    try: doc=_load_json_bytes(raw)
    except (UnicodeDecodeError,ValueError,RecursionError): return None, receipt(["INVALID_BUNDLE_JSON"])
    return doc,None

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("bundle")
    p.add_argument("--artifact-root")
    args=p.parse_args(argv)
    try:
        raw=Path(args.bundle).read_bytes()
    except OSError:
        result=receipt(["BUNDLE_READ_FAILED"])
    else:
        doc,err=parse_bundle(raw)
        result=err or (verify_artifact_root(doc,args.artifact_root) if args.artifact_root else check_bundle(doc))
    print(json.dumps(result,sort_keys=True))
    return 0 if result["status"]=="pass" else 2
if __name__=="__main__": raise SystemExit(main())
