#!/usr/bin/env python3
"""Training-pool generator for the Purple Copilot query tasks (PR #118 schema): fresh tenants,
new names, new question wording, gold from plain Python traversal.

  gen_query.py generate --tenants 30 --private-dir ~/haven-private/q-pilot --label q-pilot

Everything that defines correctness is reused from querywriter/tenant.py at its pinned hash:
the schema, the role table, the traversal helpers that compute gold, and the reference Cypher.
What is new: the user-name and team pools (so every user, group and service-principal id is
disjoint from the 84-question development suite), tenant sizes, and three analyst-style
phrasings per family that share no 8-token run with the development wording. When kuzu is
installed, every reference query is executed and must reproduce the Python gold.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import os
import pathlib
import random
import secrets
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402

T, QRUN = common.load_querywriter()
SCHEMA = "haven-weights-train-query-1"
FIRST = ["abel", "bea", "cyrus", "dara", "emre", "fleur", "gideon", "hedda", "ilya", "joss", "kiri", "lior",
         "maeve", "noor", "otto", "pax", "reza", "saskia", "teo", "una", "vesna", "wade", "xin", "yoav",
         "zora", "beni"]
TEAMS = ["procurement", "research", "marketing", "facilities", "payroll", "devops", "audit", "training",
         "logistics", "risk"]

TEMPLATES = {
    "direct_holders": [
        "List every user, group or service principal that is directly assigned '{role}' with mode active, "
        "at whatever scope.",
        "Who holds '{role}' through a direct, active role assignment (any scope, any principal type)? "
        "Give the ids.",
        "Give me the ids of principals with an active '{role}' assignment made directly to them, "
        "regardless of scope.",
    ],
    "transitive_member": [
        "Does '{user}' belong to '{group}', counting membership inherited through nested groups? "
        "Reply true or false.",
        "True or false: '{user}' is inside group '{group}' either directly or via a chain of groups.",
        "Through direct or nested membership, is '{user}' part of '{group}'? true/false.",
    ],
    "effective_holders": [
        "List the users who effectively have '{role}' as an active assignment at scope '/', whether it is "
        "assigned to them or to a group they sit in (nesting counts).",
        "Which people end up with active tenant-wide '{role}', counting assignments to any group they "
        "belong to, nested or not? User ids only.",
        "Give user ids for everyone holding '{role}' active at tenant scope by any path: direct "
        "assignment or a nested group.",
    ],
    "eligible_only": [
        "Which users could activate '{role}' tenant-wide (eligible directly or through groups, nesting "
        "included) yet have no active tenant-wide '{role}' by any route? User ids.",
        "Find users eligible for '{role}' at scope '/' by some path who do not already hold it actively at "
        "scope '/' by any path.",
        "User ids of people whose tenant-wide '{role}' is eligible-only: eligible via some path, active "
        "via none.",
    ],
    "stale_privileged": [
        "Which accounts are disabled but still carry an active tenant-wide tier-0 role, assigned directly "
        "or via nested groups? User ids.",
        "Find disabled users who keep any tier-0 role active at scope '/' through any membership path.",
        "List user ids for disabled accounts that still have tier-0 privileges (active, tenant-wide, any "
        "path).",
    ],
    "owner_escalation": [
        "Which users are owners of a service principal that has an active tenant-wide tier-0 role? "
        "User ids.",
        "Who could act as a tier-0 service principal because they own it (its role is active at scope "
        "'/')? Give user ids.",
        "List users owning any service principal with an active, tenant-wide, tier-0 assignment.",
    ],
    "transitive_count": [
        "Count the distinct users in '{group}', including those who are members only through nested "
        "groups. Return the number.",
        "How many unique users does '{group}' contain once nested group membership is expanded? A number, "
        "please.",
        "What is the number of distinct users that belong to '{group}' directly or through any nesting?",
    ],
}
assert set(TEMPLATES) == set(T.ORACLE_CYPHER)


def make_tenant(seed: str) -> dict:
    """Same construction as tenant.make_tenant, with new pools and varied sizes."""
    r = random.Random(seed)
    n_users, n_groups, n_sps = r.randint(20, 36), r.randint(9, 15), r.randint(4, 7)
    users = [{"id": f"{n}.{r.choice(TEAMS)}{i}", "enabled": r.random() > 0.15}
             for i, n in enumerate(r.sample(FIRST * 2, n_users))]
    groups = [f"grp-{t}-{i}" for i, t in enumerate(r.choices(TEAMS, k=n_groups))]
    sps = [f"sp-{t}-app{i}" for i, t in enumerate(r.choices(TEAMS, k=n_sps))]
    member = set()
    for u in users:
        for g in r.sample(groups, r.choice([0, 1, 1, 2])):
            member.add((u["id"], g))
    order = groups[:]
    r.shuffle(order)
    for i, g in enumerate(order[1:], 1):  # nesting only toward earlier groups: acyclic
        if r.random() < 0.55:
            member.add((g, r.choice(order[:i])))
    has_role = set()
    for g in r.sample(groups, 5):
        has_role.add((g, r.choice(T.ROLES)[0], r.choice(["active", "active", "eligible"]), "/"))
    for u in r.sample(users, 6):
        has_role.add((u["id"], r.choice(T.ROLES)[0], r.choice(["active", "eligible"]),
                      r.choice(["/", "/", "/subscriptions/payroll"])))
    for sp in r.sample(sps, 3):
        has_role.add((sp, r.choice(T.ROLES[:5])[0], "active", "/"))
    owns = {(r.choice(users)["id"], sp) for sp in sps if r.random() < 0.8}
    return {"seed": seed, "users": users, "groups": groups, "sps": sps, "member": sorted(member),
            "has_role": sorted(has_role), "owns": sorted(owns)}


def questions(t: dict, rng: random.Random, tag: str) -> list[dict]:
    """Gold logic identical to tenant.questions(); only the wording differs."""
    uid = [u["id"] for u in t["users"]]
    enabled = {u["id"]: u["enabled"] for u in t["users"]}
    role_names = sorted({h[1] for h in t["has_role"]}) or [T.ROLES[0][0]]
    qs = []

    def add(family, answer, kind, **params):
        text = rng.choice(TEMPLATES[family]).format(**params)
        qs.append({"id": f"train-{tag}-{family}-{len(qs)}", "family": family, "question": text,
                   "answer": answer, "kind": kind, "params": params})

    def pick_role(fn):
        live = [ro for ro in role_names if fn(ro)]
        return rng.choice(live) if live and rng.random() < 0.8 else rng.choice(role_names)

    role = pick_role(lambda ro: any(h[1] == ro and h[2] == "active" for h in t["has_role"]))
    add("direct_holders", sorted({p for p, ro, m, s in t["has_role"] if ro == role and m == "active"}), "set", role=role)
    if rng.random() < 0.5 and any(T._containers(t, x) for x in uid):
        u = rng.choice([x for x in uid if T._containers(t, x)])
        g = rng.choice(sorted(T._containers(t, u)))
    else:
        u = rng.choice(uid)
        g = rng.choice([x for x in t["groups"] if x not in T._containers(t, u)] or t["groups"])
    add("transitive_member", g in T._containers(t, u), "bool", user=u, group=g)
    role = pick_role(lambda ro: any(ro in T._roles_of(t, x, "active") for x in uid))
    add("effective_holders", sorted(x for x in uid if role in T._roles_of(t, x, "active")), "set", role=role)
    role = pick_role(lambda ro: any(ro in T._roles_of(t, x, "eligible") and ro not in T._roles_of(t, x, "active")
                                    for x in uid))
    add("eligible_only", sorted(x for x in uid if role in T._roles_of(t, x, "eligible")
                                and role not in T._roles_of(t, x, "active")), "set", role=role)
    add("stale_privileged", sorted(x for x in uid if not enabled[x]
                                   and any(T.tier(ro) == 0 for ro in T._roles_of(t, x, "active"))), "set")
    sp_t0 = {p for p, ro, m, s in t["has_role"] if p in t["sps"] and m == "active" and s == "/" and T.tier(ro) == 0}
    add("owner_escalation", sorted({o for o, sp in t["owns"] if sp in sp_t0}), "set")
    g = rng.choice(t["groups"])
    add("transitive_count", sum(1 for x in uid if g in T._containers(t, x)), "int", group=g)
    return qs


def make_rows(seed: str, n_tenants: int, salt: str | None = None):
    salt = salt or common.new_salt()
    digest = common.commit(salt, {"seed": seed, "tenants": n_tenants})
    tag, rng, rows = digest[:8], random.Random(f"{seed}|questions"), []
    for i in range(n_tenants):
        t = make_tenant(f"{seed}|t{i}")
        rows += [{"question": q, "tenant": t, "source": SCHEMA} for q in questions(t, rng, f"{tag}t{i}")]
    return rows, salt, digest


def oracle_cypher(q: dict) -> str:
    return T.ORACLE_CYPHER[q["family"]].format(**q["params"])


def oracle_reply(q: dict) -> str:
    """The cypher arm's exact reply format: a TYPE line, then the query in a cypher block."""
    return f"TYPE: {q['kind']}\n```cypher\n{oracle_cypher(q)}\n```"


def oracle_check(rows) -> dict:
    """Execute every reference query in Kùzu and compare with the Python gold."""
    try:
        import kuzu  # noqa: F401
    except ImportError:
        return {"executed": False, "reason": "kuzu not installed", "mismatches": []}
    by_tenant, bad = collections.defaultdict(list), []
    for r in rows:
        by_tenant[r["tenant"]["seed"]].append(r)
    for rs in by_tenant.values():
        _, conn = T.load_kuzu(rs[0]["tenant"], os.path.join(tempfile.mkdtemp(), "g"))
        for r in rs:
            q = r["question"]
            if T.run_query(conn, oracle_cypher(q), q["kind"]) != q["answer"]:
                bad.append(q["id"])
    return {"executed": True, "questions": len(rows), "mismatches": bad}


def cmd_generate(args):
    import dedupe
    priv = common.private_dir(args.private_dir)
    out, seed_path = priv / f"{args.label}.questions.jsonl", priv / f"{args.label}.seed.json"
    common.refuse_overwrite(out, seed_path)
    seed = args.seed or secrets.token_hex(16)
    rows, salt, digest = make_rows(seed, args.tenants)
    check = oracle_check(rows)
    report = dedupe.check_items([dedupe.query_item(r["question"], r["tenant"]) for r in rows], dedupe.load_fingerprint())
    drop = {x["id"] for x in report["rejected"]} | set(check["mismatches"])
    kept = [r for r in rows if r["question"]["id"] not in drop]
    seed_path.write_text(json.dumps({"seed": seed, "salt": salt, "commitment": digest,
                                     "payload": {"seed": seed, "tenants": args.tenants}}, indent=2) + "\n")
    common.write_jsonl(out, kept)
    print(json.dumps({"schema": SCHEMA + "-manifest", "label": args.label, "seed_commitment": digest,
                      "questions": len(rows), "kept": len(kept), "dropped": len(drop),
                      "per_family": dict(collections.Counter(r["question"]["family"] for r in kept)),
                      "oracle_cypher_check": {k: v for k, v in check.items() if k != "mismatches"},
                      "questions_sha256": common.sha256_file(out),
                      "dedupe_fingerprint": report["fingerprint_sha256"],
                      "written_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
                     indent=2))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--tenants", type=int, required=True)
    g.add_argument("--private-dir", required=True)
    g.add_argument("--label", required=True)
    g.add_argument("--seed", help="Tests only. Omit for a fresh secret seed.")
    args = ap.parse_args(argv)
    cmd_generate(args)


if __name__ == "__main__":
    main()
