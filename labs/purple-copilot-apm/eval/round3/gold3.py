"""Answer key for the round 3 held-out questions, computed only from the exported BloodHound CSV files.

Independent of apm/: plain Python over the CE export, following each SpecterOps BloodHoundQueryLibrary
query (commit ca4924e) named in questions.json. The reworded questions reuse eval/gold.json.
Run: python3 eval/round3/gold3.py EXPORT_DIR > eval/round3/gold3.json
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


def load(root, platform):
    nodes = {r["objectid"]: r for r in csv.DictReader(open(root / f"{platform}_nodes.csv"))}
    edges = [(r["source"], r["relationship"], r["target"]) for r in csv.DictReader(open(root / f"{platform}_edges.csv"))]
    return nodes, edges


def t0(nodes, oid):
    return nodes.get(oid, {}).get("tier_zero") == "True"


def kind(nodes, oid):
    return nodes.get(oid, {}).get("kind")


def name(nodes, oid):
    return nodes.get(oid, {}).get("name") or oid


def main(root):
    root = Path(root)
    ad, ad_edges = load(root, "ad")
    az, az_edges = load(root, "entra")
    member_of = defaultdict(set)
    for s, k, t in ad_edges:
        if k == "MemberOf":
            member_of[s].add(t)

    def groups(oid):  # the object itself plus every group it belongs to, transitively (MemberOf*0..)
        seen, stack = {oid}, [oid]
        while stack:
            for g in member_of[stack.pop()]:
                if g not in seen:
                    seen.add(g)
                    stack.append(g)
        return seen

    # Accounts with local Administrator access to Tier Zero computers: ()-[:MemberOf*0..]->()-[:AdminTo]->(t0 Computer)
    admins = {s for s, k, t in ad_edges if k == "AdminTo" and kind(ad, t) == "Computer" and t0(ad, t)}
    local_admin = sorted(name(ad, o) for o in ad if not t0(ad, o) and groups(o) & admins)
    local_admin_kinds = {name(ad, o): kind(ad, o) for o in ad if not t0(ad, o) and groups(o) & admins}

    # Non-Tier Zero owners of Tier Zero Entra groups: (n)-[:AZOwns]->(t0 AZGroup), n not Tier Zero
    owners = sorted({name(az, s) for s, k, t in az_edges
                     if k == "AZOwns" and kind(az, t) == "AZGroup" and t0(az, t) and not t0(az, s)})

    # Non-Tier Zero principals with control of AdminSDHolder: (non-T0 Group)-[AD_ATTACK_PATHS]->(ADMINSDHOLDER@ container)
    sdholder = {o for o in ad if kind(ad, o) == "Container" and name(ad, o).startswith("ADMINSDHOLDER@")}
    sd_control = sorted({name(ad, s) for s, k, t in ad_edges if t in sdholder and kind(ad, s) == "Group" and not t0(ad, s)})

    # Tier Zero users not member of Protected Users (objectid ending -525), membership transitive
    protected = {o for o in ad if o.endswith("-525")}
    t0_users = [o for o in ad if kind(ad, o) == "User" and t0(ad, o)]
    unprotected = sorted(name(ad, o) for o in t0_users if not (groups(o) - {o}) & protected)

    # Tier Zero external Entra ID users: AZUser, Tier Zero, name contains #EXT#@
    guests = sorted(name(az, o) for o in az if kind(az, o) == "AZUser" and t0(az, o) and "#EXT#@" in name(az, o))

    key = {
        "ho-local-admin": {"principals": local_admin, "kinds": local_admin_kinds},
        "ho-entra-group-owners": {"principals": owners},
        "ho-adminsdholder": {"principals": sd_control, "adminsdholder": sorted(name(ad, o) for o in sdholder)},
        "ho-protected-users": {"count": len(unprotected), "tier_zero_users": len(t0_users), "principals": unprotected},
        "ho-entra-guests": {"principals": guests},
    }
    json.dump(key, sys.stdout, indent=1, sort_keys=True)
    print()


if __name__ == "__main__":
    main(sys.argv[1])
