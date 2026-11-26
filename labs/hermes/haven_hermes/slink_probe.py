"""Read-only Slink probe, sent over ssh stdin (`ssh haven python3 - <command>`) so nothing is deployed there.

Prints one JSON object. It reads the Model Lab API with the same private loopback launch file labctl uses
(the token never leaves Slink), nvidia-smi, systemd unit state and the latest Sentinel report. It never
starts, stops or changes anything.

  status   lab + gpu + units + sentinel summary
  gpu      who holds the GPU (each compute process mapped to its systemd unit)
  models   catalog with download and admission state
  sentinel latest Sentinel report, summarized
"""
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HOME = Path.home()
LAUNCH = HOME / ".local/state/haven-model-lab/launch-url"
SENTINEL = HOME / ".local/state/haven-sentinel/reports/latest.json"
LAB_UNIT, STRATA_UNIT = "haven-model-lab.service", "haven-strata.service"
PEER_UNITS = ("haven-toolsft-base.service", "haven-toolsft-teacher.service", "haven-toolsft-arms.service",
              "haven-e5.service", "haven-paradigms-round2.service")


def lab_get(path, timeout=10):
    parsed = urllib.parse.urlsplit(LAUNCH.read_text().strip())
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1":
        raise ValueError("launch file does not name a loopback service")
    token = urllib.parse.parse_qs(parsed.fragment).get("token", [""])[0]
    req = urllib.request.Request(f"http://{parsed.netloc}{path}", headers={"X-Lab-Token": token})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as r:
        return json.load(r)


def guarded(fn):
    try:
        return fn()
    except Exception as e:  # each part reports unknown on its own; one failure must not hide the rest
        return {"unknown": True, "error": f"{type(e).__name__}: {str(e)[:200]}"}


def sh(argv, timeout=8):
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)


def unit_of(pid):
    try:
        text = Path(f"/proc/{pid}/cgroup").read_text()
    except OSError:
        return None
    m = re.findall(r"/([A-Za-z0-9@._-]+\.service)", text)
    return m[-1] if m else None


def unit_state(unit):
    return sh(["systemctl", "--user", "show", unit, "--property=ActiveState", "--value"]).stdout.strip() or "unknown"


def gpu():
    r = sh(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"])
    if r.returncode:
        raise RuntimeError("nvidia-smi failed")
    apps = []
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        pid, mib = [x.strip() for x in line.split(",")[:2]]
        unit = unit_of(int(pid))
        owner = "lab" if unit == LAB_UNIT else "strata" if unit == STRATA_UNIT else "peer"
        apps.append({"pid": int(pid), "mib": int(mib), "unit": unit, "owner": owner})
    mem = sh(["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader,nounits"])
    name, used, total = ([x.strip() for x in mem.stdout.split(",")] + ["", "", ""])[:3]
    peers = [u for u in PEER_UNITS if unit_state(u) in ("active", "activating", "reloading")]
    return {"name": name, "mem_used_mib": int(used or 0), "mem_total_mib": int(total or 0), "compute_apps": apps,
            "peer_units_busy": peers, "strata_unit": unit_state(STRATA_UNIT),
            "free_for_lab": not peers and all(a["owner"] == "lab" for a in apps)}


def lab():
    s = lab_get("/api/state")
    loaded = s.get("engine", {})
    return {"engine": loaded, "connection": s.get("connection") or {}, "idle_unloaded": s.get("idle_unloaded"),
            "providers": [{k: p.get(k) for k in ("id", "kind", "locality")} | {"state": (p.get("observed") or {}).get("state")}
                          for p in s.get("providers", [])],
            "running_jobs": [j for j in (s.get("jobs") or []) if isinstance(j, dict) and j.get("state") == "RUNNING"][:5]}


def units():
    r = sh(["systemctl", "--user", "list-units", "--type=service", "--state=running", "--no-legend", "--plain", "haven*"])
    return [line.split()[0] for line in r.stdout.splitlines() if line.strip()]


def sentinel():
    d = json.loads(SENTINEL.read_text())
    bad = [f for f in d.get("findings", []) if f.get("status") != "pass"]
    return {"generated_utc": d.get("generated_utc"), "counts": d.get("counts"),
            "not_passing": [{k: f.get(k) for k in ("check", "severity", "status", "title")} for f in bad][:20]}


def models():
    s = lab_get("/api/state")
    adm = guarded(lambda: lab_get("/api/model-admission"))
    stages = {}
    for e in (adm.get("models") or adm.get("entries") or []) if isinstance(adm, dict) else []:
        if isinstance(e, dict) and e.get("id"):
            stages[e["id"]] = {k: e.get(k) for k in ("stage", "blocking", "role") if k in e}
    return {"loaded": (s.get("engine") or {}).get("label"),
            "models": [{"id": m.get("id"), "name": m.get("name"), "downloaded": m.get("downloaded"),
                        "size_gb": m.get("download_gb"), "tag": m.get("tag"), **({"admission": stages[m["id"]]}
                                                                                    if m.get("id") in stages else {})}
                       for m in s.get("models", [])],
            "admission_error": adm.get("error") if isinstance(adm, dict) and adm.get("unknown") else None}


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        out = {"host": os.uname().nodename, "lab": guarded(lab), "gpu": guarded(gpu), "units": guarded(units),
               "sentinel": guarded(sentinel)}
    elif cmd == "gpu":
        out = guarded(gpu)
    elif cmd == "models":
        out = guarded(models)
    elif cmd == "sentinel":
        out = guarded(sentinel)
    else:
        out = {"unknown": True, "error": f"unknown probe command {cmd}"}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
