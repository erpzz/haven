"""Read-only Tier Zero review tools with an evidence gateway and answer verifier.

The functions here are independent of any agent runtime. The Hermes Agent plugin in
``.hermes/plugins/purple-copilot`` registers the three tools and wires ``Gate`` to
``pre_tool_call`` and ``Verifier`` to ``transform_llm_output``. Every tool result carries
citation tokens. A final answer may use only citations, numbers and principal names that this
turn's tool results returned. Otherwise the answer is replaced with a deterministic summary of
the retrieved evidence. Nothing here writes to CE, the history database or the directory.
"""
import hashlib
import json
import re
from collections import Counter
from contextlib import closing
from pathlib import Path

from .samples import ROOT
from .store import database

PLATFORMS = ("ad", "entra")
LIVE = ("new", "persistent", "changed")
TOOLS = {
    "purple_tier_zero_overview": ("platform",),
    "purple_tier_zero_principal": ("platform", "principal"),
    "purple_tier_zero_changes": ("platform",),
}
MAX_CALLS = 6
CITATION = re.compile(r"\[((?:T0|P|F)-\d+(?:-[0-9a-f]{12})?)\]")
NUMBER = re.compile(r"(?<![\w.-])\d{1,3}(?:,\d{3})+(?![\w-])|(?<![\w.-])\d+(?![\w-])")
PRINCIPAL = re.compile(r"[A-Za-z0-9_.$-]+@[A-Za-z0-9_.-]+")


def state(f):
    return f.get("observation") or f["state"]


def latest(platform, before=None):
    if platform not in PLATFORMS:
        raise ValueError("platform must be ad or entra")
    clause = "AND id < ?" if before else ""
    with closing(database(True)) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='path_runs'").fetchone():
            return None
        row = db.execute(f"""SELECT * FROM path_runs WHERE json_extract(evidence,'$.asset.key')=? {clause}
            ORDER BY id DESC LIMIT 1""", (f"tier-zero-{platform}", *([before] if before else []))).fetchone()
    return (row["id"], row["observed"], json.loads(row["evidence"]), json.loads(row["findings"])) if row else None


def by_principal(findings):
    groups = {}
    for key, f in findings.items():
        groups.setdefault(f["path"][0][0], []).append((key, f))
    return groups


def short(run, oid):
    return f"P-{run}-" + hashlib.sha256(oid.encode()).hexdigest()[:12]


def overview(platform, limit=10):
    """Headline exposure and the highest-priority principals in the latest snapshot."""
    snap = latest(platform)
    if not snap:
        return {"platform": platform, "available": False, "reason": "No Tier Zero snapshot recorded"}
    run, observed, e, findings = snap
    base = {"citation": f"T0-{run}", "platform": platform, "snapshot": run, "observed": observed,
            "confidence": "limited", "issues": e["issues"], "notes": e.get("notes", [])}
    if e.get("unavailable"):
        return dict(base, available=False, reason="Latest observation unavailable; prior findings carried")
    nodes, groups = e["nodes"], by_principal(findings)
    live = {s: [(k, f) for k, f in items if state(f) in LIVE] for s, items in groups.items()}
    ranked = sorted((s for s in live if live[s]), key=lambda s: (-groups[s][0][1]["priority"]["score"], s))
    pop = e.get("population", {})
    top = []
    for s in ranked[:limit]:
        factors = groups[s][0][1]["priority"]["factors"]
        top.append({"citation": short(run, s), "principal": nodes[s]["label"], "kind": nodes[s]["kind"],
                    "identities_able_to_gain_control": groups[s][0][1]["priority"]["score"],
                    "users": factors["users"], "computers": factors["computers"], "workloads": factors["workloads"],
                    "control_edges": dict(Counter(f["path"][0][1] for _, f in live[s]).most_common())})
    return dict(base, available=True,
                principals_with_direct_control=len(ranked),
                control_edges=sum(len(v) for v in live.values()),
                identities_able_to_reach_tier_zero=sum(pop.get(k, 0) for k in ("users", "computers", "workloads")),
                exposed_users=pop.get("users", 0), exposed_computers=pop.get("computers", 0),
                exposed_workloads=pop.get("workloads", 0), top_principals=top, shown=len(top))


def resolve(platform, name):
    snap = latest(platform)
    if not snap or snap[2].get("unavailable"):
        return None, snap
    want = name.strip().casefold()
    for oid, n in snap[2]["nodes"].items():
        if oid.casefold() == want or (n.get("label") or "").casefold() == want:
            if oid in by_principal(snap[3]):
                return oid, snap
    return None, snap


def principal(platform, principal, limit=60):
    """Every control edge one non-Tier Zero principal holds, with its exposure."""
    oid, snap = resolve(platform, principal)
    if not oid:
        return {"platform": platform, "found": False, "reason": "No such principal holds a Tier Zero control edge"}
    run, observed, e, findings = snap
    items = sorted(by_principal(findings)[oid], key=lambda kf: (kf[1]["path"][0][1], kf[1]["path"][0][2]))
    nodes, prio = e["nodes"], items[0][1]["priority"]
    edges = [{"citation": f"F-{run}-{k[:12]}", "relationship": f["path"][0][1],
              "target": nodes.get(f["path"][0][2], {}).get("label") or f["path"][0][2],
              "target_kind": nodes.get(f["path"][0][2], {}).get("kind"), "state": state(f)} for k, f in items]
    return {"citation": short(run, oid), "platform": platform, "snapshot": run, "observed": observed, "found": True,
            "principal": nodes[oid]["label"], "kind": nodes[oid]["kind"], "object_id": oid,
            "identities_able_to_gain_control": prio["score"], "users": prio["factors"]["users"],
            "computers": prio["factors"]["computers"], "workloads": prio["factors"]["workloads"],
            "groups": prio["factors"]["groups"], "edges_total": len(edges), "edges": edges[:limit],
            "confidence": "limited"}


def changes(platform, limit=40):
    """Findings that appeared, changed route or went missing at the latest snapshot."""
    snap = latest(platform)
    if not snap:
        return {"platform": platform, "available": False, "reason": "No Tier Zero snapshot recorded"}
    run, observed, e, findings = snap
    previous = latest(platform, before=run)
    nodes = dict(e.get("nodes", {}))
    wanted = {x for f in findings.values() for x in (f["path"][0][0], f["path"][0][2])} - set(nodes)
    earlier = previous
    for _ in range(50):  # Missing findings keep the labels from when they were last observed.
        if not wanted or not earlier:
            break
        for oid in wanted & set(earlier[2].get("nodes", {})):
            nodes[oid] = earlier[2]["nodes"][oid]
        wanted -= set(nodes)
        earlier = latest(platform, before=earlier[0])
    out = {"citation": f"T0-{run}", "platform": platform, "snapshot": run, "observed": observed,
           "previous_snapshot": previous[0] if previous else None,
           "counts": dict(Counter(state(f) for f in findings.values())), "confidence": "limited",
           "note": "Missing means not observed; removal needs independent corroboration"}
    for kind in ("new", "changed", "missing"):
        rows = [(k, f) for k, f in sorted(findings.items()) if state(f) == kind]
        out[kind] = [{"citation": f"F-{run}-{k[:12]}", "principal": nodes.get(f["path"][0][0], {}).get("label") or f["path"][0][0],
                      "relationship": f["path"][0][1],
                      "target": nodes.get(f["path"][0][2], {}).get("label") or f["path"][0][2]} for k, f in rows[:limit]]
    return out


IMPLEMENTATIONS = {"purple_tier_zero_overview": overview, "purple_tier_zero_principal": principal,
                   "purple_tier_zero_changes": changes}
SCHEMAS = {
    "purple_tier_zero_overview": "Headline Tier Zero exposure and the highest-priority non-Tier Zero principals "
                                 "for one platform. Start here.",
    "purple_tier_zero_principal": "All Tier Zero control edges held by one principal named exactly as an earlier "
                                  "result showed it, with the identities able to gain that control.",
    "purple_tier_zero_changes": "Tier Zero control edges that are new, changed or missing at the latest snapshot.",
}


def schema(name):
    props = {"platform": {"type": "string", "enum": list(PLATFORMS), "description": "ad or entra"}}
    if name == "purple_tier_zero_principal":
        props["principal"] = {"type": "string", "description": "Exact principal label or object ID from an earlier result"}
    return {"name": name, "description": SCHEMAS[name] + " Cite results with their [citation] tokens.",
            "parameters": {"type": "object", "properties": props, "required": list(TOOLS[name]),
                           "additionalProperties": False}}


def call(name, args):
    return json.dumps(IMPLEMENTATIONS[name](**{k: args[k] for k in TOOLS[name]}), sort_keys=True)


class Turn:
    """Evidence retrieved and calls attempted during one user turn of one session."""

    def __init__(self, question=""):
        self.question, self.calls, self.blocked, self.results = question, [], [], []

    def citations(self):
        out = set()
        for _, data in self.results:
            for token in re.findall(r'"citation": "([^"]+)"', data):
                out.add(token)
        return out

    def numbers(self):
        """Integer values the tools returned. Digits inside IDs, hashes and names do not count."""
        out = set()

        def walk(value):
            if isinstance(value, bool):
                return
            if isinstance(value, int):
                out.add(str(value))
            elif isinstance(value, dict):
                for v in value.values():
                    walk(v)
            elif isinstance(value, list):
                for v in value:
                    walk(v)
        for _, data in self.results:
            walk(json.loads(data))
        return out

    def principals(self):
        return {m.casefold() for _, data in self.results for m in PRINCIPAL.findall(data)}


class Gate:
    """Pre-execution checks. A returned message blocks the call and is shown to the model."""

    def __init__(self, strict=True):
        self.strict = strict

    def check(self, turn, tool_name, args):
        if tool_name not in TOOLS:
            if self.strict:
                return ("Blocked: this Purple Copilot review permits only the read-only purple_tier_zero_* "
                        "evidence tools.")
            return None
        if not isinstance(args, dict) or set(args) != set(TOOLS[tool_name]):
            return f"Blocked: {tool_name} takes exactly {', '.join(TOOLS[tool_name])}."
        if args["platform"] not in PLATFORMS:
            return "Blocked: platform must be ad or entra."
        if tool_name == "purple_tier_zero_principal":
            name = args["principal"]
            if not isinstance(name, str) or not 0 < len(name) <= 400:
                return "Blocked: principal must be a non-empty name of at most 400 characters."
            if not resolve(args["platform"], name)[0]:
                return ("Blocked: that principal holds no recorded Tier Zero control edge on this platform. "
                        "Use a name exactly as purple_tier_zero_overview returned it.")
        key = (tool_name, json.dumps(args, sort_keys=True))
        if key in turn.calls:
            return "Blocked: this evidence was already retrieved in this turn. Use the earlier result."
        if len(turn.calls) >= MAX_CALLS:
            return f"Blocked: the review budget of {MAX_CALLS} evidence reads per turn is spent."
        turn.calls.append(key)
        return None


class Verifier:
    """Checks a final answer against the evidence retrieved in the same turn."""

    def problems(self, turn, answer):
        if not turn.results:
            return []
        found = []
        cited = CITATION.findall(answer)
        known = turn.citations()
        if not cited:
            found.append("no evidence citation")
        unknown = sorted(set(cited) - known)
        if unknown:
            found.append("unknown citations: " + ", ".join(unknown[:5]))
        text = CITATION.sub(" ", answer)
        text = re.sub(r"(?m)^\s*(?:\d+[.)]|[-*])\s+", " ", text)
        numbers = {n.replace(",", "") for n in NUMBER.findall(text)}
        unsupported = sorted(numbers - turn.numbers(), key=lambda n: (len(n), n))
        if unsupported:
            found.append("numbers absent from evidence: " + ", ".join(unsupported[:5]))
        names = {m.casefold() for m in PRINCIPAL.findall(text)} - turn.principals()
        if names:
            found.append("principals absent from evidence: " + ", ".join(sorted(names)[:5]))
        return found


def fallback(turn, problems):
    """A deterministic answer assembled only from this turn's evidence."""
    # Name the failure categories only; the rejected values stay in the private receipt, never in front of the user.
    categories = sorted({p.split(":", 1)[0] for p in problems})
    lines = ["The model's answer was withheld because it failed evidence verification ("
             + "; ".join(categories) + "). Retrieved evidence:"]
    for name, data in turn.results:
        r = json.loads(data)
        if name == "purple_tier_zero_overview" and r.get("available"):
            lines.append(f"- {r['platform'].upper()} snapshot {r['snapshot']}: {r['principals_with_direct_control']} "
                         f"principals hold {r['control_edges']} direct control edges into Tier Zero; "
                         f"{r['identities_able_to_reach_tier_zero']} identities can reach Tier Zero "
                         f"({r['exposed_users']} users, {r['exposed_computers']} computers, "
                         f"{r['exposed_workloads']} workloads). Confidence {r['confidence']}. [{r['citation']}]")
            for p in r["top_principals"][:5]:
                edges = ", ".join(p["control_edges"])
                lines.append(f"  - {p['principal']} ({p['kind']}): {p['identities_able_to_gain_control']} identities "
                             f"can gain this control via {edges}. [{p['citation']}]")
        elif name == "purple_tier_zero_principal" and r.get("found"):
            lines.append(f"- {r['principal']} ({r['kind']}) holds {r['edges_total']} Tier Zero control edges; "
                         f"{r['identities_able_to_gain_control']} identities can gain them. [{r['citation']}]")
            for edge in r["edges"][:8]:
                lines.append(f"  - {edge['relationship']} → {edge['target']} ({edge['state']}) [{edge['citation']}]")
        elif name == "purple_tier_zero_changes" and r.get("snapshot"):
            counts = ", ".join(f"{v} {k}" for k, v in sorted(r["counts"].items()))
            lines.append(f"- {r['platform'].upper()} snapshot {r['snapshot']} versus "
                         f"{r['previous_snapshot'] or 'no earlier snapshot'}: {counts}. {r['note']}. [{r['citation']}]")
        else:
            lines.append(f"- {name}: {r.get('reason', 'no result')}")
    return "\n".join(lines)


def receipt(record):
    """Append-only private review receipts under the lab state directory."""
    path = Path(ROOT) / "agent-reviews.jsonl"
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


__all__ = ["Gate", "Turn", "Verifier", "call", "fallback", "receipt", "schema", "TOOLS"]
