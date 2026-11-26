"""Live oracle checks of Tier Zero findings against BloodHound CE and the SpecterOps query library.

Requires the seeded sample lab (README) and APM_STATE. Two independent checks:
1. Containment: every non-Tier Zero to Tier Zero edge returned by the pinned SpecterOps library
   queries below must be a recorded boundary finding.
2. Exposure: every object counted as able to reach a boundary source must reach it under CE's own
   shortest-path search (soundness), and anything CE finds that is not counted must route through
   Tier Zero, which places it in the exposed population of another finding (completeness).
Run: PYTHONPATH=. APM_STATE=... python3 tests/live_tier_zero.py [--entra-sample N]
"""
import argparse
import json
import random
import sys
from collections import defaultdict

from apm import tier_zero as tz

# SpecterOps/BloodHoundQueryLibrary at ca4924e007ed8094850f980239a1f2ba2bf23b95 (2026-11-04):
# file name, guid, revision, verbatim query.
LIBRARY = [
    ("Shortest paths to Domain Admins", "f40cb34b-5ec7-44bc-9aa8-a200a4a41f22", 2,
     "MATCH p=shortestPath((t:Group)<-[:AD_ATTACK_PATHS*1..]-(s:Base))\nWHERE t.objectid ENDS WITH '-512' AND s<>t\nRETURN p\nLIMIT 1000"),
    ("Non-Tier Zero owners of Tier Zero Entra groups", "f02f57b9-ac94-4954-a698-4584457962eb", 2,
     "MATCH p=(n:AZBase)-[:AZOwns]->(g:AZGroup)\nWHERE NOT (n:Tag_Tier_Zero)\nAND (g:Tag_Tier_Zero)\nRETURN p"),
    ("Shortest paths from Domain Users to Tier Zero High Value targets", "469dc0f3-71b8-41b0-a03b-b4af7874665d", 4,
     "MATCH p=shortestPath((s:Group)-[:AD_ATTACK_PATHS*1..]->(t:Tag_Tier_Zero))\nWHERE s.objectid ENDS WITH '-513' AND s<>t\nRETURN p\nLIMIT 1000"),
    ("Shortest paths to Domain Admins from Kerberoastable users", "bd163361-1e05-47c7-908b-962aef251535", 2,
     "MATCH p=shortestPath((s:User)-[:AD_ATTACK_PATHS*1..]->(t:Group))\nWHERE s.hasspn=true\nAND s.enabled = true\nAND NOT s.objectid ENDS WITH '-502'\nAND NOT COALESCE(s.gmsa, false) = true\nAND NOT COALESCE(s.msa, false) = true\nAND t.objectid ENDS WITH '-512'\nRETURN p\nLIMIT 1000"),
    ("Shortest paths to privileged roles", "3dc73dd8-4873-4aeb-a88f-56a58c77f512", 4,
     "MATCH p=shortestPath((s:AZBase)-[:AZ_ATTACK_PATHS*1..]->(t:AZRole))\nWHERE t.name =~ '(?i)^(Global Administrator|User Administrator|Cloud Application Administrator|Authentication Policy Administrator|Exchange Administrator|Helpdesk Administrator|Privileged Authentication Administrator|Privileged Role Administrator).*$' AND s<>t\nRETURN p\nLIMIT 1000"),
    ("Accounts with local Administrator access to Tier Zero computers", "52490ad1-42b8-416b-ac38-4a45cbe4d73c", 1,
     "MATCH p=()-[:MemberOf*0..]->()-[:AdminTo]->(n:Computer)\nWHERE (n:Tag_Tier_Zero)\nRETURN p\nLIMIT 1000"),
    ("Non-Tier Zero principals with GPO link control over Tier Zero containers", "41a9df23-99ab-40dd-a965-2ea89db96823", 2,
     "MATCH p = (n:Base)-[r:WriteGPLink|GenericAll|GenericWrite|WriteDacl|WriteOwner|Owns]->(t:Base)\nWHERE (t:Domain OR t:OU)\nAND (t:Tag_Tier_Zero)\nAND NOT (n:Tag_Tier_Zero)\nRETURN p\nLIMIT 1000"),
    ("Non-Tier Zero principals with access to enabled gMSA passwords", "10d0ee8e-17ec-4f6c-9b94-8dffe548f9d4", 3,
     "MATCH p1=(s1:Base)-[r:ReadGMSAPassword|GenericAll|GenericWrite|WriteOwner|WriteDacl]->(d1:Base)\nWHERE s1<>d1\nAND d1.gmsa = true\nAND d1.enabled = true\n// Exclude Tier Zero principals\nAND NOT (s1:Tag_Tier_Zero)\nMATCH p2 = (s2:Base)-[:MemberOf*1..]->()-[:ReadGMSAPassword|GenericAll|GenericWrite|WriteOwner|WriteDacl]->(d2:Base)\nWHERE s2<>d2\nAND d2.gmsa = true\nAND d2.enabled = true\n// Exclude Tier Zero principals\nAND NOT (s2:Tag_Tier_Zero)\nRETURN p1,p2"),
    ("Shortest paths from non-Tier Zero computers to Tier Zero", "004374c9-4a81-4884-9837-c75dad71fa83", 2,
     "// MANY TO MANY SHORTEST PATH QUERIES USE EXCESSIVE SYSTEM RESOURCES AND TYPICALLY WILL NOT COMPLETE\nMATCH p=shortestPath((s:Computer)-[:AD_ATTACK_PATHS*1..]->(t:Base))\nWHERE s<>t\nAND NOT (s:Tag_Tier_Zero)\nAND (t:Tag_Tier_Zero)\nRETURN p\nLIMIT 1000"),
    ("Shortest paths from non-Tier Zero user accounts to Tier Zero", "8b61bf34-5256-47e5-a5a8-370e8ddc3f90", 2,
     "// MANY TO MANY SHORTEST PATH QUERIES USE EXCESSIVE SYSTEM RESOURCES AND TYPICALLY WILL NOT COMPLETE\nMATCH p=shortestPath((s:User)-[:AD_ATTACK_PATHS*1..]->(t:Base))\nWHERE s<>t\nAND NOT (s:Tag_Tier_Zero)\nAND (t:Tag_Tier_Zero)\nRETURN p\nLIMIT 1000"),
    ("Shortest paths from non-Tier Zero groups to Tier Zero", "0ac20b7a-31df-4f3a-b2bd-3eecd541fcaa", 2,
     "// MANY TO MANY SHORTEST PATH QUERIES USE EXCESSIVE SYSTEM RESOURCES AND TYPICALLY WILL NOT COMPLETE\nMATCH p=shortestPath((s:Group)-[:AD_ATTACK_PATHS*1..]->(t:Base))\nWHERE s<>t\nAND NOT (s:Tag_Tier_Zero)\nAND (t:Tag_Tier_Zero)\nRETURN p\nLIMIT 1000"),
    ("Non-Tier Zero principals with BadSuccessor rights (no prerequisites check)", "2b9fb71e-73ad-4061-a2df-40c7132b044d", 2,
     "// Find OU control\nMATCH p = (ou:OU)<-[:WriteDacl|Owns|GenericAll|WriteOwner]-(n:Base)\n// Exclude Tier Zero\nWHERE NOT (n:Tag_Tier_Zero)\nRETURN p LIMIT 1000"),
    ("Non-Tier Zero accounts with WriteDACL on Tier Zero group", "d9e80a24-93a8-4847-b354-762b7ac7510d", 1,
     "MATCH p=(n:Base)-[:WriteDacl]->(g:Group)\nWHERE NOT (n:Tag_Tier_Zero)\nAND (g:Tag_Tier_Zero)\nRETURN p"),
    ("Principals that can write Shadow Credentials on Tier Zero principals", "96e86fb9-4cd6-4df3-81a6-e36fd7a34614", 2,
     "MATCH p=(n:Base)-[:AddKeyCredentialLink]->(m:Base)\nWHERE (n:User or n:Computer)\nAND (m:Tag_Tier_Zero)\nRETURN p\nLIMIT 1000"),
    ("Non-Tier Zero principals with control of AdminSDHolder", "4c1e0137-5b7f-48d8-bd09-9db7674bca61", 3,
     "MATCH p=(n:Group)-[r:AD_ATTACK_PATHS]->(m:Container)\nWHERE NOT (n:Tag_Tier_Zero)\nAND m.name STARTS WITH \"ADMINSDHOLDER@\"\nRETURN p"),
    ("Non-Tier Zero accounts with SID History of Tier Zero accounts", "59744dfe-9411-4daf-b342-1203dc62acd4", 2,
     "MATCH p=(n:Base)-[:HasSIDHistory]->(m:Base)\nWHERE (m:Tag_Tier_Zero)\nAND NOT (n:Tag_Tier_Zero)\nRETURN p"),
    ("Foreign principals in Tier Zero groups", "bf8701bb-964f-484e-98e9-6a5dc9a0b35f", 1,
     "MATCH p=(s:Base)-[:MemberOf]->(t:Group)\nWHERE s.domainsid <> t.domainsid\nAND (t:Tag_Tier_Zero)\nRETURN p\nLIMIT 1000"),
    ("Non-Tier Zero Principals with ExecuteDCOM privileges on Domain Controllers", "2aeefd57-cbe7-4f0e-907f-86a97d7b723c", 3,
     "MATCH p1=(n:Base)-[:ExecuteDCOM]->(c:Computer)\nWHERE NOT (n:Tag_Tier_Zero)\nAND c.isdc\nMATCH p2=(n)-[:MemberOf]->(g:Group)\nWHERE g.objectid ENDS WITH \"S-1-5-32-562\" // Distributed COM Users \nOR g.objectid ENDS WITH \"S-1-5-32-559\" // Performance Log Users\nRETURN p1,p2\nLIMIT 1000"),
]


def reach(incoming, source):
    seen, stack = set(), [source]
    while stack:
        for parent in incoming[stack.pop()]:
            if parent != source and parent not in seen:
                seen.add(parent)
                stack.append(parent)
    return seen


def containment(boundary):
    failures, crossing_total = [], 0
    for name, guid, revision, query in LIBRARY:
        try:
            edges, nodes = tz.triples(tz.cypher(query))
        except RuntimeError as exc:
            print(json.dumps({"query": name, "guid": guid, "error": str(exc)}))
            failures.append(name)
            continue
        crossing = {(s, k, t) for s, k, t in edges if not nodes[s].get("isTierZero") and nodes[t].get("isTierZero")}
        missing = sorted(crossing - boundary)
        crossing_total += len(crossing)
        print(json.dumps({"query": name, "guid": guid, "revision": revision, "edges": len(edges),
                          "crossing": len(crossing), "missing": missing[:5]}))
        if missing:
            failures.append(name)
    return failures, crossing_total


def exposure_check(platform, o, sample):
    incoming = defaultdict(set)
    for s, _, t in o["upstream"]:
        incoming[t].add(s)
    sources = sorted({s for s, _, _ in o["boundary"]})
    local = {s: reach(incoming, s) for s in sources}
    population = set(sources).union(*local.values()) if local else set()
    base, kinds = tz.PLATFORMS[platform]
    picked = sources if sample is None else random.Random(1).sample(sources, min(sample, len(sources)))
    failures = []
    for source in picked:
        query = (f"MATCH p=shortestPath((x:{base})-[:{kinds}*1..]->(y:{base} {{objectid:'{source}'}})) "
                 f"WHERE NOT (x:Tag_Tier_Zero) AND x<>y RETURN p LIMIT 100000")
        _, nodes = tz.triples(tz.cypher(query))
        found = {oid for oid, n in nodes.items() if oid != source}
        unsound = local[source] - found
        unexplained = {x for x in found - local[source] if x not in population and not nodes[x].get("isTierZero")}
        if unsound or unexplained:
            failures.append(source)
            print(json.dumps({"platform": platform, "source": source, "unsound": len(unsound),
                              "unexplained": len(unexplained)}))
    print(json.dumps({"platform": platform, "sources": len(sources), "checked": len(picked),
                      "failures": len(failures)}))
    return failures


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--entra-sample", type=int, default=8)
    args = p.parse_args()
    tz.verify_reader()
    observed = {platform: tz.observe(platform) for platform in tz.PLATFORMS}
    boundary = set().union(*(set(o["boundary"]) for o in observed.values()))
    failed, crossing = containment(boundary)
    assert crossing > 0, "Library queries returned no crossing edges; the oracle is vacuous"
    for platform, o in observed.items():
        failed += exposure_check(platform, o, None if platform == "ad" else args.entra_sample)
    print(json.dumps({"passed": not failed, "library_crossing_edges": crossing, "failures": failed}))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
