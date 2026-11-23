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
# Anything shaped like a citation must be one the tools returned, so malformed or invented tokens are caught.
CITATION = re.compile(r"\[(?:citation:\s*)?((?:T0|P|F)-[^\]\s,;]+)\]")
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?"
                       r"|\b\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:\s?UTC)?")
NUMBER = re.compile(r"(?<![\w.-])\d{1,3}(?:,\d{3})+(?![\w-])|(?<![\w.-])\d+(?![\w-])")
PRINCIPAL = re.compile(r"[A-Za-z0-9_.$-]+@[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*")  # Never ends with a full stop.


# What each BloodHound attack edge lets whoever controls the source do, phrased with its direction.
MEANING = {
    "HasSession": "{target} has a logon session on {source}; whoever controls {source} can harvest {target}'s credentials",
    "AdminTo": "{source} is a local administrator on {target}",
    "MemberOf": "{source} is a member of {target} and inherits its rights",
    "Contains": "{source} contains {target}; control of {source} can be inherited by {target}",
    "GenericAll": "{source} has full control of {target}",
    "GenericWrite": "{source} can write the attributes of {target}",
    "WriteDacl": "{source} can change the permissions on {target} and grant itself full control",
    "WriteOwner": "{source} can make itself the owner of {target} and then take full control",
    "Owns": "{source} owns {target} and can grant itself full control",
    "AllExtendedRights": "{source} holds all extended rights on {target}, such as forcing a password reset",
    "AddMember": "{source} can add members to {target}",
    "AddSelf": "{source} can add itself to {target}",
    "ForceChangePassword": "{source} can reset the password of {target}",
    "DCSync": "{source} can replicate secrets from {target}, including every password hash (DCSync)",
    "ReadGMSAPassword": "{source} can read the managed account password of {target}",
    "ReadLAPSPassword": "{source} can read the local administrator password of {target}",
    "AllowedToDelegate": "{source} is trusted for constrained delegation to {target} and can impersonate users to it",
    "AllowedToAct": "{source} can impersonate users to {target} through resource-based constrained delegation",
    "CoerceToTGT": "{source} has unconstrained delegation; coercing {target} to authenticate to it yields {target}'s Kerberos tickets",
    "WriteAccountRestrictions": "{source} can write delegation settings on {target} and abuse resource-based constrained delegation",
    "AddKeyCredentialLink": "{source} can add shadow credentials to {target} and authenticate as it",
    "ManageCA": "{source} can manage the certificate authority {target}",
    "ManageCertificates": "{source} can approve certificate requests on {target}",
    "GoldenCert": "{source} holds a CA key that can forge certificates for principals in {target}",
    "HasSIDHistory": "{source} carries the SID of {target} in its SID history and receives its rights",
    "GPLink": "{source} is linked to {target}; control of {source} applies to objects in {target}",
    "AZAddOwner": "{source} can add owners to {target}",
    "AZAddSecret": "{source} can add a credential to {target} and authenticate as it",
    "AZMGAddOwner": "{source} holds a Microsoft Graph permission that lets it add an owner to {target}",
    "AZMGAddSecret": "{source} holds a Microsoft Graph permission that lets it add a credential to {target} and authenticate as it",
    "AZMGAddMember": "{source} holds a Microsoft Graph permission that lets it add members to {target}",
    "AZMGGrantRole": "{source} holds a Microsoft Graph permission that lets it assign the directory role {target}",
    "AZMGGrantAppRoles": "{source} holds a Microsoft Graph permission that lets it grant application permissions, reaching {target}",
    "AZManagedIdentity": "{source} runs as the managed identity {target}; control of {source} yields {target}'s permissions",
    "AZOwns": "{source} owns {target}",
    "AZResetPassword": "{source} can reset the password of {target}",
    "AZAddMembers": "{source} can add members to {target}",
    "AZHasRole": "{source} holds the directory role {target}",
    "AZMemberOf": "{source} is a member of {target} and inherits its rights",
    "AZRunsAs": "{source} runs as {target}",
    "AZContains": "{source} contains {target}",
    "AZContributor": "{source} has Contributor access to {target}",
    "AZOwner": "{source} has Owner access to {target}",
    "AZUserAccessAdministrator": "{source} can grant access to {target}",
    "AZGlobalAdmin": "{source} has Global Administrator control over {target}",
    "AZPrivilegedRoleAdmin": "{source} has Privileged Role Administrator control over {target}",
    "AZExecuteCommand": "{source} can run commands on {target}",
}


def meaning(kind, source, target):
    if kind.startswith("ADCSESC"):
        return f"{source} can obtain a certificate that authenticates as privileged principals of {target} ({kind[4:]} certificate abuse)"
    return MEANING.get(kind, "{source} has the BloodHound attack edge " + kind + " to {target}").format(source=source, target=target)


def plural(n, one, many=None):
    return f"{n} {one if n == 1 else (many or one + 's')}"


def reach_statement(name, factors):
    return (f"{factors['users']} users, {factors['computers']} computers, {factors['workloads']} workloads and "
            f"{factors['groups']} groups can reach {name} through attack paths without passing through Tier Zero; "
            f"compromising any of them leads to the Tier Zero control {name} holds")


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
        kinds = dict(Counter(f["path"][0][1] for _, f in live[s]).most_common())
        label = nodes[s]["label"]
        top.append({"citation": short(run, s), "principal": label, "kind": nodes[s]["kind"],
                    "identities_able_to_gain_control": groups[s][0][1]["priority"]["score"],
                    "reachable_from": {k: factors[k] for k in ("users", "computers", "workloads", "groups")},
                    "tier_zero_controls_held": len(live[s]), "control_edges": kinds,
                    "summary": f"{label} ({nodes[s]['kind']}) holds {len(live[s])} Tier Zero control edges "
                               f"({', '.join(kinds)}); {reach_statement(label, factors)}."})
    fix_first = []
    for i, step in enumerate(e.get("remediation") or [], 1):
        names = [nodes[x]["label"] for x in step["sources"]]
        shown, more = names[:5], max(0, len(names) - 5)
        who = ", ".join(shown) + (f" and {more} more" if more else "")
        fix_first.append({
            "step": i, "principals": shown, "principals_count": len(names), "more_principals": more,
            "control_edges": step["control_edges"], "identities_removed": step["identities_removed"],
            "identities_still_exposed": step["identities_still_exposed"],
            "citations": [short(run, x) for x in step["sources"][:5]],
            "summary": (f"Step {i}: remove every direct Tier Zero control edge held by {who} "
                        f"({plural(step['control_edges'], 'edge')}"
                        + (f" across {len(names)} principals that must be fixed together" if len(names) > 1 else "")
                        + f"). {plural(step['identities_removed'], 'identity', 'identities')} then lose every route "
                          f"to Tier Zero and {step['identities_still_exposed']} remain exposed.")})
    return dict(base, available=True, fix_first=fix_first,
                principals_with_direct_control=len(ranked),
                control_edges=sum(len(v) for v in live.values()),
                identities_able_to_reach_tier_zero=sum(pop.get(k, 0) for k in ("users", "computers", "workloads")),
                exposed_users=pop.get("users", 0), exposed_computers=pop.get("computers", 0),
                exposed_workloads=pop.get("workloads", 0), top_principals=top, shown=len(top),
                not_shown=len(ranked) - len(top))


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
    label = nodes[oid]["label"]
    edges = []
    for k, f in items:
        target = nodes.get(f["path"][0][2], {}).get("label") or f["path"][0][2]
        edges.append({"citation": f"F-{run}-{k[:12]}", "relationship": f["path"][0][1], "target": target,
                      "target_kind": nodes.get(f["path"][0][2], {}).get("kind"), "state": state(f),
                      "meaning": meaning(f["path"][0][1], label, target)})
    factors = prio["factors"]
    return {"citation": short(run, oid), "platform": platform, "snapshot": run, "observed": observed, "found": True,
            "principal": label, "kind": nodes[oid]["kind"], "object_id": oid, "is_tier_zero": False,
            "tier_zero_controls_held": len(edges), "identities_able_to_gain_control": prio["score"],
            "reachable_from": {k: factors[k] for k in ("users", "computers", "workloads", "groups")},
            "reach": reach_statement(label, factors) + ".", "edges": edges[:limit], "confidence": "limited"}


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
    totals = {k: out["counts"].get(k, 0) for k in ("new", "changed", "missing")}
    out["totals"] = totals
    out["summary"] = (f"At snapshot {run}, {totals['new']} Tier Zero control edges are new, {totals['changed']} changed route "
                      f"and {totals['missing']} are missing compared with "
                      + (f"snapshot {previous[0]}" if previous else "no earlier snapshot")
                      + ". The lists below are examples, not totals.")
    for kind in ("new", "changed", "missing"):
        rows = [(k, f) for k, f in sorted(findings.items()) if state(f) == kind]
        out[kind] = []
        for k, f in rows[:limit]:
            source = nodes.get(f["path"][0][0], {}).get("label") or f["path"][0][0]
            target = nodes.get(f["path"][0][2], {}).get("label") or f["path"][0][2]
            out[kind].append({"citation": f"F-{run}-{k[:12]}", "principal": source, "relationship": f["path"][0][1],
                              "target": target, "meaning": meaning(f["path"][0][1], source, target)})
    return out


IMPLEMENTATIONS = {"purple_tier_zero_overview": overview, "purple_tier_zero_principal": principal,
                   "purple_tier_zero_changes": changes}
SCHEMAS = {
    "purple_tier_zero_overview": "Headline Tier Zero exposure, the highest-priority non-Tier Zero principals and a "
                                 "computed fix_first remediation order for one platform. Start here; for 'what should "
                                 "I fix first' quote fix_first.",
    "purple_tier_zero_principal": "All Tier Zero control edges held by one principal named exactly as an earlier "
                                  "result showed it. Each edge has a 'meaning' sentence stating its direction; "
                                  "'reachable_from' counts who can reach this principal, not what it can access.",
    "purple_tier_zero_changes": "Tier Zero control edges that are new, changed or missing at the latest snapshot.",
}


def schema(name):
    props = {"platform": {"type": "string", "enum": list(PLATFORMS), "description": "ad or entra"}}
    if name == "purple_tier_zero_principal":
        props["principal"] = {"type": "string", "description": "Exact principal label or object ID from an earlier result"}
    return {"name": name, "description": SCHEMAS[name] + " Prefer the result's own summary and meaning sentences. "
                                                       "Cite each claim with its [citation] token.",
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

    def by_principal(self):
        """Integer values found in each object that describes one principal, keyed by its label."""
        index = {}

        def ints(value, out):
            if isinstance(value, bool):
                return
            if isinstance(value, int):
                out.add(str(value))
            elif isinstance(value, dict):
                for v in value.values():
                    ints(v, out)
            elif isinstance(value, list):
                for v in value:
                    ints(v, out)

        def walk(value):
            if isinstance(value, dict):
                names = [value["principal"]] if isinstance(value.get("principal"), str) else []
                names += [n for n in value.get("principals") or [] if isinstance(n, str)]
                for name in names:  # An object describing several principals is evidence for each of them.
                    ints(value, index.setdefault(name.casefold(), set()))
                for v in value.values():
                    walk(v)
            elif isinstance(value, list):
                for v in value:
                    walk(v)
        for _, data in self.results:
            walk(json.loads(data))
        return index


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


UNITS = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen " \
        "seventeen eighteen nineteen".split()
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
NUMBER_WORD = re.compile(r"\b(" + "|".join(TENS) + r")(?:[- ](" + "|".join(UNITS[1:10]) + r"))?\b|\b(" + "|".join(UNITS[2:]) + r")\b",
                         re.IGNORECASE)


def spelled(text):
    """Counts written as words above one, such as 'twenty-three', as digits."""
    out = []
    for tens, unit, small in NUMBER_WORD.findall(text):
        if small:
            out.append(str(UNITS.index(small.lower())))
        else:
            out.append(str(TENS[tens.lower()] + (UNITS.index(unit.lower()) if unit else 0)))
    return out


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
        text = TIMESTAMP.sub(" ", CITATION.sub(" ", answer))  # Dates and times are not counts.
        text = re.sub(r"(?m)^\s*(?:\d+[.)]|[-*])\s+", " ", text)
        numbers = {n.replace(",", "") for n in NUMBER.findall(text)} | set(spelled(text))
        unsupported = sorted(numbers - turn.numbers(), key=lambda n: (len(n), n))
        if unsupported:
            found.append("numbers absent from evidence: " + ", ".join(unsupported[:5]))
        names = {m.casefold() for m in PRINCIPAL.findall(text)} - turn.principals()
        if names:
            found.append("principals absent from evidence: " + ", ".join(sorted(names)[:5]))
        misbound = self.misattributed(turn, text)
        if misbound:
            found.append("numbers attributed to the wrong principal: " + ", ".join(misbound[:5]))
        return found

    def misattributed(self, turn, text):
        """In a sentence that names principals, each number must belong to one of those principals' evidence."""
        index = turn.by_principal()
        labels = sorted(index, key=len, reverse=True)
        out = []
        for segment in re.split(r"(?<=[.;!?])\s+|\n+|\s+\|\s+", text):
            lowered, named = segment.casefold(), []
            for label in labels:
                if label in lowered and not any(label in other for other in named):
                    named.append(label)
            if not named:
                continue
            allowed = set().union(*(index[n] for n in named))
            for n in NUMBER.findall(segment):
                if n.replace(",", "") not in allowed:
                    out.append(f"{n} with {named[0]}")
        return out


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
            for step in r.get("fix_first", [])[:3]:
                lines.append(f"  - {step['summary']} [{step['citations'][0]}]")
            for p in r["top_principals"][:5]:
                lines.append(f"  - {p['summary']} [{p['citation']}]")
        elif name == "purple_tier_zero_principal" and r.get("found"):
            lines.append(f"- {r['principal']} ({r['kind']}) holds {r['tier_zero_controls_held']} Tier Zero control edges. "
                         f"{r['reach']} [{r['citation']}]")
            for edge in r["edges"][:8]:
                lines.append(f"  - {edge['meaning']} ({edge['state']}). [{edge['citation']}]")
        elif name == "purple_tier_zero_changes" and r.get("snapshot"):
            lines.append(f"- {r['platform'].upper()}: {r['summary']} {r['note']}. [{r['citation']}]")
            for edge in (r["new"] + r["changed"] + r["missing"])[:5]:
                lines.append(f"  - {edge['meaning']}. [{edge['citation']}]")
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
