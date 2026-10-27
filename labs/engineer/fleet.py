#!/usr/bin/env python3
"""Fleet inventory: enrolled nodes, live observations, discovered candidates.

Enrollment is an owner act. A node is enrolled only through an SSH alias the
owner already trusts (strict host-key checking, key auth, BatchMode), or as
the local host. Enrollment records the host-key fingerprint; a later mismatch
marks the node UNTRUSTED and it receives no work. Devices seen passively on
the owner's configured subnets (ARP cache, no scanning) appear as candidates
only: network proximity is not proof of ownership.

There is no node-count limit. Each observation is a real measurement with its
capture time and round-trip; missing values are null, never zero.

  fleet.py observe                 # JSON for every enrolled node + candidates
  fleet.py enroll NAME --ssh ALIAS [--roles inference,tools,build]
  fleet.py remove NAME
  fleet.py bind NAME --tsz-node ID  # owner binds a node to its TSZ identity (trust.py)
"""
from __future__ import annotations

import argparse
import concurrent.futures
import ipaddress
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import time

import trust

CONFIG = pathlib.Path(os.environ.get("HAVEN_ENGINEER_CONFIG", pathlib.Path.home() / ".config/haven-engineer"))
STATE = pathlib.Path(os.environ.get("HAVEN_ENGINEER_STATE", pathlib.Path.home() / ".local/state/haven-engineer"))
FLEET = CONFIG / "fleet.json"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=6"]

# One read-only probe, the same shape on Linux and macOS. Prints KEY=VALUE lines.
REMOTE_PROBE = r'''
set +e
echo "HOST=$(hostname)"; echo "OS=$(uname -sr)"; echo "ARCH=$(uname -m)"
echo "CORES=$(getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu)"
echo "LOAD=$(cut -d' ' -f1-3 /proc/loadavg 2>/dev/null || sysctl -n vm.loadavg | tr -d '{}')"
if [ -r /proc/meminfo ]; then
  echo "MEM_TOTAL=$(awk '/MemTotal/{print $2*1024}' /proc/meminfo)"
  echo "MEM_AVAIL=$(awk '/MemAvailable/{print $2*1024}' /proc/meminfo)"
fi
echo "CPU=$(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2- | sed 's/^ //')"
echo "DISK=$(df -Pk / | awk 'NR==2{print $2*1024, $4*1024}')"
echo "UPTIME=$(cut -d' ' -f1 /proc/uptime 2>/dev/null)"
if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader,nounits | sed 's/^/GPU=/'
  nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits | sed 's/^/GPU_APP=/'
fi
systemctl --user list-units --type=service --state=running --no-legend --plain 2>/dev/null | awk '/haven|strata|llama/{print "UNIT="$1}'
ps -eo pid,etimes,args 2>/dev/null | grep -E '[l]lama-server|[m]lx_lm' | awk '{a=$0; m=""; p=""; al="";
  if (match(a, /--model [^ ]+|-m [^ ]+/)) m=substr(a, RSTART, RLENGTH);
  if (match(a, /--port [0-9]+/)) p=substr(a, RSTART+7, RLENGTH-7);
  if (match(a, /--alias [^ ]+/)) al=substr(a, RSTART+8, RLENGTH-8);
  n=split(m, parts, "/"); print "MODEL=" $1 "|" $2 "|" parts[n] "|" p "|" al}'
for f in "$HOME"/.local/state/haven-model-lab/gpu-lease*.json; do [ -r "$f" ] && echo "LEASE=$(tr -d '\n' < "$f" | cut -c1-300)"; done
'''


def load():
    if FLEET.exists():
        return json.loads(FLEET.read_text())
    return {"nodes": [{"name": "local", "kind": "local", "roles": ["tools", "inference", "supervisor"],
                       "enrolled": time.time(), "trust": "LOCAL_HOST"}], "discovery_scopes": []}


def save(cfg):
    CONFIG.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = FLEET.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2))
    os.chmod(tmp, 0o600)
    os.replace(tmp, FLEET)


def host_fingerprint(alias):
    """Fingerprint of the key the owner's known_hosts already pins for this alias."""
    r = subprocess.run(["ssh", "-G", alias], capture_output=True, text=True, timeout=5)
    host = re.search(r"^hostname (\S+)", r.stdout, re.M)
    port = re.search(r"^port (\S+)", r.stdout, re.M)
    if not host:
        return None
    target = host[1] if not port or port[1] == "22" else f"[{host[1]}]:{port[1]}"
    k = subprocess.run(["ssh-keygen", "-F", target], capture_output=True, text=True)
    lines = [ln for ln in k.stdout.splitlines() if ln and not ln.startswith("#")]
    if not lines:
        return None
    fp = subprocess.run(["ssh-keygen", "-lf", "-"], input=lines[0] + "\n", capture_output=True, text=True)
    m = re.search(r"(SHA256:\S+)", fp.stdout)
    return {"address": host[1], "fingerprint": m[1] if m else None}


def enroll(name, alias, roles):
    cfg = load()
    if any(n["name"] == name for n in cfg["nodes"]):
        raise SystemExit(f"{name} is already enrolled")
    pin = host_fingerprint(alias)
    if not pin or not pin["fingerprint"]:
        raise SystemExit(f"{alias}: no pinned host key in known_hosts; verify the host and connect once yourself")
    r = subprocess.run(SSH + [alias, "true"], capture_output=True, text=True, timeout=15)
    if r.returncode:
        raise SystemExit(f"{alias}: key-based SSH failed: {r.stderr.strip()[:200]}")
    node = {"name": name, "kind": "ssh", "ssh": alias, "roles": roles, "enrolled": time.time(),
            "trust": "OWNER_SSH", "host_fingerprint": pin["fingerprint"], "address": pin["address"]}
    cfg["nodes"].append(node)
    save(cfg)
    return node


def remove(name):
    cfg = load()
    before = len(cfg["nodes"])
    cfg["nodes"] = [n for n in cfg["nodes"] if n["name"] != name or n["kind"] == "local"]
    save(cfg)
    return before != len(cfg["nodes"])


def bind(name, tsz_node_id):
    """Owner act: tie a Haven node to the identity the external trust model approves."""
    cfg = load()
    node = next((n for n in cfg["nodes"] if n["name"] == name), None)
    if node is None:
        raise SystemExit(f"{name} is not enrolled")
    if tsz_node_id and any(n.get("tsz_node_id") == tsz_node_id and n is not node for n in cfg["nodes"]):
        raise SystemExit(f"{tsz_node_id} is already bound to another node")
    if tsz_node_id:
        node["tsz_node_id"] = tsz_node_id
    else:
        node.pop("tsz_node_id", None)
    save(cfg)
    return node


def _parse(text):
    obs = {"gpus": [], "gpu_apps": [], "units": [], "models": [], "leases": []}
    for line in text.splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if k == "GPU":
            p = [x.strip() for x in v.split(",")]
            obs["gpus"].append({"name": p[0], "mem_used_mb": _num(p[1]), "mem_total_mb": _num(p[2]),
                                "util_pct": _num(p[3]), "temp_c": _num(p[4]),
                                "power_w": _num(p[5]) if len(p) > 5 else None})
        elif k == "GPU_APP":
            p = [x.strip() for x in v.split(",")]
            obs["gpu_apps"].append({"pid": _num(p[0]), "mem_mb": _num(p[1])})
        elif k == "UNIT":
            obs["units"].append(v)
        elif k == "MODEL":
            pid, age, model, port, alias = (v.split("|") + ["", "", "", "", ""])[:5]
            obs["models"].append({"pid": _num(pid), "uptime_s": _num(age), "file": model, "port": _num(port),
                                  "alias": alias or None})
        elif k == "LEASE":
            obs["leases"].append(v)
        elif k == "DISK":
            parts = v.split()
            obs["disk_total"], obs["disk_free"] = (_num(parts[0]), _num(parts[1])) if len(parts) == 2 else (None, None)
        else:
            obs[k.lower()] = v
    for k in ("cores", "mem_total", "mem_avail"):
        if k in obs:
            obs[k] = _num(obs[k])
    if "load" in obs:
        obs["load"] = [_num(x) for x in obs["load"].split()[:3]]
    return obs


def _num(v):
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return None


def observe_local():
    t0 = time.monotonic()
    r = subprocess.run(["/bin/bash", "-c", REMOTE_PROBE], capture_output=True, text=True, timeout=20)
    obs = _parse(r.stdout)
    if platform.system() == "Darwin":
        obs["cpu"] = _sh(["sysctl", "-n", "machdep.cpu.brand_string"])
        obs["mem_total"] = _num(_sh(["sysctl", "-n", "hw.memsize"]))
        vm = _sh(["vm_stat"])
        page = 16384
        pages = {m[0]: int(m[1]) for m in re.findall(r"Pages (\w[\w ]*?):\s+(\d+)", vm)}
        avail = sum(pages.get(k, 0) for k in ("free", "inactive", "speculative", "purgeable"))
        obs["mem_avail"] = avail * page
        obs["mem_compressed"] = pages.get("occupied by compressor", 0) * page
        obs["gpus"] = [{"name": f"{obs['cpu']} GPU (Metal, unified memory)", "mem_used_mb": None,
                        "mem_total_mb": None, "util_pct": None}]
        obs["uptime"] = None
    obs["rtt_ms"] = round((time.monotonic() - t0) * 1000, 1)
    return obs


def _sh(argv):
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def observe_ssh(node):
    pin = host_fingerprint(node["ssh"])
    if not pin or pin["fingerprint"] != node.get("host_fingerprint"):
        return {"status": "UNTRUSTED", "error": "host key no longer matches the enrolled fingerprint"}
    t0 = time.monotonic()
    try:
        r = subprocess.run(SSH + [node["ssh"], "bash -s"], input=REMOTE_PROBE, capture_output=True, text=True,
                           timeout=20)
    except subprocess.TimeoutExpired:
        return {"status": "OFFLINE", "error": "probe timed out"}
    if r.returncode not in (0, 1) or "HOST=" not in r.stdout:
        return {"status": "OFFLINE", "error": (r.stderr.strip() or f"exit {r.returncode}")[:200]}
    obs = _parse(r.stdout)
    obs["rtt_ms"] = round((time.monotonic() - t0) * 1000, 1)
    return obs


# The neighbor-cache read TSZ (ops/tsz/fleet.py observe) uses on each platform; parsing is TSZ's.
NEIGHBOR_CACHE = {"Linux": ["ip", "-j", "neigh", "show"], "Darwin": ["arp", "-an"]}


def _cache_interfaces(tsz, system, text):
    """Every interface named in the cache output (used when the owner configured none)."""
    if system == "Linux":
        raw = json.loads(text)
        return {e["dev"] for e in raw if isinstance(e, dict) and isinstance(e.get("dev"), str)} \
            if isinstance(raw, list) else set()
    return {m[3] for m in tsz.ARP.finditer(text)}


def neighbors(system, text, scopes, interfaces=None):
    """Pure: candidates in `scopes` from one neighbor-cache dump, parsed by TSZ."""
    tsz = trust._tsz()
    nets = [ipaddress.ip_network(s, strict=False) for s in scopes]
    if not nets or system not in NEIGHBOR_CACHE:
        return []
    try:
        ifaces = set(interfaces or ()) or _cache_interfaces(tsz, system, text)
        ifaces = {i for i in ifaces if tsz.INTERFACE.fullmatch(i)}
        seen = (tsz.parse_linux if system == "Linux" else tsz.parse_macos)(text, ifaces) if ifaces else []
    except ValueError:  # malformed cache output (json.JSONDecodeError and FleetError are ValueErrors)
        return []
    return [{"address": o["address"], "mac_prefix": ":".join(o["mac"].split(":")[:3]),
             "candidate_id": o["candidate_id"], "status": "DISCOVERED_NOT_ENROLLED"}
            for o in seen if any(ipaddress.ip_address(o["address"]) in n for n in nets)]


def discover(scopes):
    """Passive: devices in the OS neighbor cache inside owner-configured subnets. No probing."""
    system = platform.system()
    cmd = NEIGHBOR_CACHE.get(system)
    if not scopes or not cmd or not shutil.which(cmd[0]):
        return []
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if r.returncode:
        return []
    return neighbors(system, r.stdout, scopes, load().get("discovery_interfaces"))


def observe(cache_s=10):
    cache = STATE / "fleet-observation.json"
    if cache.exists() and time.time() - cache.stat().st_mtime < cache_s:
        return json.loads(cache.read_text())
    cfg = load()

    def one(node):
        started = time.time()
        try:
            obs = observe_local() if node["kind"] == "local" else observe_ssh(node)
        except Exception as e:  # noqa: BLE001 - surfaced as an observation error
            obs = {"status": "ERROR", "error": f"{type(e).__name__}: {e}"[:200]}
        obs.setdefault("status", "ONLINE")
        obs["observed_at"] = started
        return {**{k: v for k, v in node.items() if k != "host_fingerprint"},
                "fingerprint_pinned": bool(node.get("host_fingerprint")), "observation": obs}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(32, len(cfg["nodes"])))) as pool:
        nodes = list(pool.map(one, cfg["nodes"]))
    enrolled = {n.get("address") for n in cfg["nodes"]}
    candidates = [c for c in discover(cfg.get("discovery_scopes", [])) if c["address"] not in enrolled]
    result = {"observed_at": time.time(), "nodes": nodes, "candidates": candidates}
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    cache.write_text(json.dumps(result))
    os.chmod(cache, 0o600)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("observe")
    e = sub.add_parser("enroll")
    e.add_argument("name")
    e.add_argument("--ssh", required=True)
    e.add_argument("--roles", default="inference,tools")
    r = sub.add_parser("remove")
    r.add_argument("name")
    b = sub.add_parser("bind")
    b.add_argument("name")
    b.add_argument("--tsz-node", default="", help="empty string removes the binding")
    s = sub.add_parser("scope")
    s.add_argument("cidr")
    args = ap.parse_args(argv)
    if args.cmd == "observe":
        print(json.dumps(observe(cache_s=0), indent=2))
    elif args.cmd == "enroll":
        print(json.dumps(enroll(args.name, args.ssh, args.roles.split(",")), indent=2))
    elif args.cmd == "remove":
        print("removed" if remove(args.name) else "not found")
    elif args.cmd == "bind":
        print(json.dumps({k: v for k, v in bind(args.name, args.tsz_node).items() if k != "host_fingerprint"},
                         indent=2))
    elif args.cmd == "scope":
        cfg = load()
        ipaddress.ip_network(args.cidr, strict=False)
        cfg.setdefault("discovery_scopes", []).append(args.cidr)
        save(cfg)
        print(cfg["discovery_scopes"])


if __name__ == "__main__":
    main()
