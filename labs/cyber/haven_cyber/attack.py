"""MITRE ATT&CK technique table and Sigma rule index, used to validate ids and map findings to detections.

    python -m haven_cyber.attack build-attack <enterprise-attack-X.Y.json>    # STIX 2.1 bundle -> compact table
    python -m haven_cyber.attack build-sigma                                   # SigmaHQ cloud rules -> metadata index
    python -m haven_cyber.attack map HCA-001                                   # techniques + Sigma rules for a finding

ATT&CK content: © The MITRE Corporation, used under the ATT&CK Terms of Use (reproduction permitted with this
notice). Only ids, names, tactics, platforms and status are kept. Sigma: SigmaHQ rules are under the Detection Rule
License 1.1; the index stores only rule metadata (title, id, tags, logsource, level, status) and a link back to the
rule. No detection logic is copied, so attribution travels with every link.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

from . import ROOT

KNOW = ROOT / "knowledge"
ATTACK_TABLE = KNOW / "attack" / "enterprise-techniques.json"
SIGMA_INDEX = KNOW / "sigma" / "cloud-rules-index.json"
TECH_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b")

# Haven findings -> ATT&CK techniques an attacker would use against the gap. Reviewed by hand; validated by tests.
FINDING_TECHNIQUES = {
    "HCA-001": ["T1110.003", "T1078.004"],   # legacy protocols: password spray, valid cloud accounts
    "HCA-002": ["T1078.004", "T1110"],       # admin without MFA
    "HCA-003": ["T1078.004", "T1110.003"],
    "HCA-004": ["T1557", "T1539"],           # phishable MFA: adversary-in-the-middle, session cookie theft
    "HCA-007": ["T1528", "T1566.002"],       # device-code phishing: token theft via a link
    "HCA-008": ["T1078.004"],
    "HCA-009": ["T1078.004"],
    "entra_legacy_authentication_blocked": ["T1110.003", "T1078.004"],
    "MT.1006": ["T1078.004", "T1110"], "MT.1007": ["T1078.004", "T1110.003"],
}


def build_attack(bundle: Path, out: Path = ATTACK_TABLE) -> dict:
    raw = bundle.read_bytes()
    data = json.loads(raw)
    version = next((o.get("x_mitre_version") for o in data["objects"] if o.get("type") == "x-mitre-collection"), None)
    tactics = {}
    techniques = {}
    for o in data["objects"]:
        ref = next((r for r in o.get("external_references", []) if r.get("source_name") == "mitre-attack"), None)
        if not ref:
            continue
        if o.get("type") == "x-mitre-tactic":
            tactics[o["x_mitre_shortname"]] = ref["external_id"]
        elif o.get("type") == "attack-pattern":
            techniques[ref["external_id"]] = {
                "name": o["name"], "tactics": sorted({p["phase_name"] for p in o.get("kill_chain_phases", [])
                                                      if p.get("kill_chain_name") == "mitre-attack"}),
                "platforms": o.get("x_mitre_platforms", []), "subtechnique": bool(o.get("x_mitre_is_subtechnique")),
                "deprecated": bool(o.get("x_mitre_deprecated")), "revoked": bool(o.get("revoked")),
                "url": ref.get("url"), "modified": o.get("modified")}
    table = {"source": "mitre-attack/attack-stix-data enterprise-attack", "attack_version": version,
             "bundle_file": bundle.name, "bundle_sha256": hashlib.sha256(raw).hexdigest(),
             "notice": "© The MITRE Corporation. Reproduced under the ATT&CK Terms of Use: https://attack.mitre.org/resources/legal-and-branding/terms-of-use/",
             "tactics": tactics, "techniques": dict(sorted(techniques.items()))}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(table, indent=0, sort_keys=False) + "\n")
    return {"version": version, "techniques": len(techniques), "out": str(out)}


def load_attack(path: Path = ATTACK_TABLE) -> dict:
    return json.loads(path.read_text())


def validate(ids, table: dict | None = None) -> dict:
    """Classify technique ids as current, deprecated/revoked or unknown."""
    t = (table or load_attack())["techniques"]
    out = {"current": [], "deprecated_or_revoked": [], "unknown": []}
    for i in sorted(set(ids)):
        if i not in t:
            out["unknown"].append(i)
        elif t[i]["deprecated"] or t[i]["revoked"]:
            out["deprecated_or_revoked"].append(i)
        else:
            out["current"].append(i)
    return out


SIGMA_DIRS = ["rules/cloud/azure", "rules/cloud/m365"]


def _gh_json(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "haven-cyber"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _sigma_meta(text: str) -> dict:
    """Read only the top-level metadata keys of a Sigma rule; the detection block is ignored on purpose."""
    meta, tags, cur = {}, [], None
    for line in text.splitlines():
        if re.match(r"^[a-z_]+:", line):
            key, _, val = line.partition(":")
            cur = key
            if key in ("title", "id", "status", "level"):
                meta[key] = val.strip().strip("'\"")
        elif cur == "tags" and line.strip().startswith("- "):
            tags.append(line.strip()[2:].strip())
        elif cur == "logsource" and ":" in line:
            k, _, v = line.strip().partition(":")
            meta.setdefault("logsource", {})[k.strip()] = v.strip()
    meta["tags"] = tags
    meta["techniques"] = sorted({t.split(".", 1)[1].upper() for t in tags if re.match(r"attack\.t\d{4}", t)})
    return meta


def build_sigma(out: Path = SIGMA_INDEX, ref: str = "master") -> dict:
    rules, tree = [], _gh_json(f"https://api.github.com/repos/SigmaHQ/sigma/git/trees/{ref}?recursive=1")
    commit = _gh_json(f"https://api.github.com/repos/SigmaHQ/sigma/commits/{ref}")["sha"]
    paths = [e["path"] for e in tree["tree"] if e["type"] == "blob" and e["path"].endswith(".yml")
             and any(e["path"].startswith(d + "/") for d in SIGMA_DIRS)]
    for p in sorted(paths):
        with urllib.request.urlopen(f"https://raw.githubusercontent.com/SigmaHQ/sigma/{commit}/{p}", timeout=60) as r:
            m = _sigma_meta(r.read().decode("utf-8", "replace"))
        m["path"] = p
        m["url"] = f"https://github.com/SigmaHQ/sigma/blob/{commit}/{p}"
        rules.append(m)
    idx = {"source": "SigmaHQ/sigma", "commit": commit, "dirs": SIGMA_DIRS,
           "license": "Detection Rule License (DRL) 1.1, https://github.com/SigmaHQ/Detection-Rule-License; metadata only, follow url for the rule",
           "rules": rules}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(idx, indent=0) + "\n")
    return {"commit": commit, "rules": len(rules), "out": str(out)}


# Where activity exploiting each gap would be logged (Sigma logsource.service values).
FINDING_LOGSOURCES = {"HCA-001": {"signinlogs", "riskdetection"}, "HCA-002": {"signinlogs", "riskdetection"},
                      "HCA-003": {"signinlogs", "riskdetection"}, "HCA-004": {"signinlogs", "riskdetection"},
                      "HCA-007": {"signinlogs", "auditlogs", "riskdetection"}, "HCA-008": {"riskdetection", "signinlogs"},
                      "HCA-009": {"signinlogs"}}
GENERIC = {"T1078", "T1078.004"}  # too broad to select rules on their own


def map_finding(check_id: str, table: dict | None = None, sigma: dict | None = None, limit: int = 8) -> dict:
    """Techniques for a finding and the most specific SigmaHQ rules for them, restricted to the log source where the
    exploiting activity would appear. Exact technique match scores 2, parent-technique match 1; generic techniques
    (valid cloud accounts) never select a rule by themselves. An empty list is reported as a detection gap."""
    techs = FINDING_TECHNIQUES.get(check_id, [])
    t = (table or load_attack())["techniques"]
    sig = sigma if sigma is not None else (json.loads(SIGMA_INDEX.read_text()) if SIGMA_INDEX.exists() else {"rules": []})
    specific = [x for x in techs if x not in GENERIC]
    services = FINDING_LOGSOURCES.get(check_id)
    scored = []
    for r in sig["rules"]:
        if r.get("status") in ("deprecated", "unsupported"):
            continue
        if services and (r.get("logsource") or {}).get("service") not in services:
            continue
        rt = set(r["techniques"])
        score = sum(2 for x in specific if x in rt) + sum(1 for x in specific if x.split(".")[0] in rt and x not in rt)
        if score:
            scored.append((score, r))
    scored.sort(key=lambda sr: (-sr[0], sr[1].get("title", "")))
    rules = [{"title": r.get("title"), "id": r.get("id"), "level": r.get("level"), "status": r.get("status"),
              "logsource": (r.get("logsource") or {}).get("service"), "techniques": r["techniques"], "match": "exact" if s >= 2 else "parent",
              "url": r["url"]} for s, r in scored[:limit]]
    return {"check": check_id, "techniques": [{"id": x, "name": t.get(x, {}).get("name"), "tactics": t.get(x, {}).get("tactics")} for x in techs],
            "sigma_rules": rules, "detection_gap": not rules and bool(techs), "sigma_commit": sig.get("commit")}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build-attack")
    b.add_argument("bundle", type=Path)
    sub.add_parser("build-sigma")
    m = sub.add_parser("map")
    m.add_argument("check_id")
    a = ap.parse_args(argv)
    if a.cmd == "build-attack":
        print(json.dumps(build_attack(a.bundle)))
    elif a.cmd == "build-sigma":
        print(json.dumps(build_sigma()))
    else:
        print(json.dumps(map_finding(a.check_id), indent=1))


if __name__ == "__main__":
    main()
