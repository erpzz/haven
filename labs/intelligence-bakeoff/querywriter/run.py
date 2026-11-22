#!/usr/bin/env python3
"""Query-writing vs reasoning-in-text, matched questions, one OpenAI-compatible endpoint.

  run.py check                                   # oracle Cypher == Python gold on the whole suite
  run.py eval --arm cypher|prose --base-url http://127.0.0.1:PORT/v1 --label L --out R.jsonl [--tenants 12]

code:   no model. A rules-only parser (family keywords + verbatim entity match) fills the
        reference query templates. This is the code-alone baseline the model must beat.
cypher: the model sees the schema and the question and writes one read-only query. The
        Kùzu engine executes it. If execution fails, the model gets one retry with the
        error text (recorded separately).
prose:  the model sees the whole tenant as text plus the question and answers in JSON.
Both: temperature 0, thinking off. Scored by exact match (set, bool, int) against the
Python gold, with Jaccard similarity for sets as a secondary metric.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import re
import sys
import tempfile
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tenant as T  # noqa: E402

SUITE_SEED = "dev-20261121"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
CYPHER_SYSTEM = ("You translate identity-security questions into ONE read-only Kùzu Cypher query over the schema "
                 "below. Reply with exactly two parts: a first line 'TYPE: set' (a list of ids or names), "
                 "'TYPE: bool' (yes/no) or 'TYPE: int' (a count), then the query inside a ```cypher code block.\n"
                 + T.SCHEMA + "\n"
                 "Rules: return ids (or names) in the FIRST column; for yes/no questions return one boolean; for "
                 "counts return one number. Variable-length paths are written like [:MEMBER_OF*1..10]; use "
                 "*0..10 to include the zero-hop case. Never write data.")
PROSE_SYSTEM = ("Answer the identity-security question using only the tenant data given. Think silently, then "
                "reply with one line of JSON: {\"answer\": <list of ids | true/false | number>}.")


# ------------------------------------------------------------------ code-alone arm (rules only, no model)
FAMILY_RULES = [  # first match wins; written for this suite's wording, frozen by hash before any reserve
    ("transitive_member", r"\bis user\b.*\bmember of group\b"),
    ("transitive_count", r"\bhow many\b.*\bmembers of group\b"),
    ("owner_escalation", r"\bown\b.*\bservice principal\b"),
    ("stale_privileged", r"\bdisabled\b.*\btier-0\b"),
    ("eligible_only", r"\beligible\b.*\bnot\b.*\bactive\b"),
    ("effective_holders", r"\busers\b.*\bactive tenant-wide\b"),
    ("direct_holders", r"\bdirect active assignment\b"),
]


FAMILY_TYPE = {"transitive_member": "bool", "transitive_count": "int"}  # every other family answers a set


def parse_question(question, tenant):
    """(family, params) or None. Entities must appear verbatim and be unique in the tenant."""
    fam = next((f for f, pat in FAMILY_RULES if re.search(pat, question, re.I)), None)
    if fam is None:
        return None
    quoted = re.findall(r"'([^']+)'", question)
    users = {u["id"] for u in tenant["users"]}
    groups, roles = set(tenant["groups"]), {r for r, _ in T.ROLES}
    pick = lambda pool: next((q for q in quoted if q in pool), None)  # noqa: E731
    params = {"role": pick(roles), "user": pick(users), "group": pick(groups)}
    need = {"direct_holders": ["role"], "effective_holders": ["role"], "eligible_only": ["role"],
            "transitive_member": ["user", "group"], "transitive_count": ["group"]}.get(fam, [])
    if any(params[k] is None for k in need):
        return None
    return fam, {k: v for k, v in params.items() if v is not None}


def chat(base_url, model, system, user, max_tokens):
    body = {"model": model, "temperature": 0, "max_tokens": max_tokens, "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.monotonic()
    with OPENER.open(req, timeout=600) as r:
        obj = json.load(r)
    msg = obj["choices"][0]["message"]
    return (msg.get("content") or ""), obj.get("usage") or {}, time.monotonic() - t0


def extract_cypher(text):
    m = re.search(r"```(?:cypher)?\s*(.*?)```", text, re.S | re.I)
    return (m.group(1) if m else text).strip().rstrip(";")


def declared_type(text):
    m = re.search(r"^\s*TYPE:\s*(set|bool|int)\b", text, re.I | re.M)
    return m.group(1).lower() if m else None


def extract_answer(text):
    """(type, value) from the prose arm's own JSON; the JSON value's type is its declaration."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None, None
    try:
        v = json.loads(m.group(0)).get("answer")
    except ValueError:
        return None, None
    if isinstance(v, bool):
        return "bool", v
    if isinstance(v, int):
        return "int", v
    if isinstance(v, list):
        return "set", sorted({str(x) for x in v})
    return None, None


def jaccard(a, b):
    a, b = set(a or []), set(b or [])
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def score(q, got_type, got):
    """Exact only if the arm's own declared type AND value match the gold."""
    exact = got_type == q["kind"] and got == q["answer"]
    both_sets = got_type == "set" and q["kind"] == "set" and isinstance(got, list)
    return {"exact": exact, "type_match": got_type == q["kind"],
            "jaccard": jaccard(got, q["answer"]) if both_sets else float(exact)}


def cmd_check(args):
    suite, bad, n = T.make_suite(SUITE_SEED, args.tenants), [], 0
    for item in suite:
        _, conn = T.load_kuzu(item["tenant"], os.path.join(tempfile.mkdtemp(), "g"))
        for q in item["questions"]:
            n += 1
            got = T.run_query(conn, T.ORACLE_CYPHER[q["family"]].format(**q["params"]), q["kind"])
            if got != q["answer"]:
                bad.append(q["id"])
    print(json.dumps({"questions": n, "oracle_mismatches": bad}))
    if bad:
        raise SystemExit(1)


def cmd_eval(args):
    out = pathlib.Path(args.out)
    if out.exists():
        raise SystemExit("refusing to overwrite")
    suite = T.make_suite(SUITE_SEED, args.tenants)
    rows = []
    for item in suite:
        t = item["tenant"]
        _, conn = T.load_kuzu(t, os.path.join(tempfile.mkdtemp(), "g"))
        for q in item["questions"][: args.per_tenant or None]:
            rec = {"id": q["id"], "family": q["family"], "gold_kind": q["kind"], "arm": args.arm, "gold": q["answer"]}
            t0 = time.monotonic()  # one end-to-end timer: model calls, execution, retry, parsing
            usage = {}
            got_type, got = None, None
            if args.arm == "code":
                parsed = parse_question(q["question"], t)
                cy = None
                if parsed:
                    fam, params = parsed
                    got_type = FAMILY_TYPE.get(fam, "set")
                    cy = T.ORACLE_CYPHER[fam].format(**params)
                    got = T.normalize(T.execute(conn, cy), got_type)
                rec.update({"query": cy, "unsupported": parsed is None})
            elif args.arm == "cypher":
                text, usage, _ = chat(args.base_url, args.model, CYPHER_SYSTEM, q["question"], 512)
                cy, err, retried = extract_cypher(text), None, False
                got_type = declared_type(text)
                qrows = None
                try:
                    qrows = T.execute(conn, cy)
                except Exception as e:  # one bounded retry with the engine's error
                    err, retried = f"{type(e).__name__}: {str(e)[:300]}", True
                    text2, usage2, _ = chat(args.base_url, args.model, CYPHER_SYSTEM,
                                            f"{q['question']}\n\nYour previous query:\n{cy}\nfailed with:\n{err}\n"
                                            "Write a corrected query.", 512)
                    usage = {k: usage.get(k, 0) + usage2.get(k, 0) for k in set(usage) | set(usage2)
                             if isinstance(usage.get(k, 0), int) and isinstance(usage2.get(k, 0), int)}
                    cy, got_type = extract_cypher(text2), declared_type(text2) or got_type
                    try:
                        qrows, err = T.execute(conn, cy), None
                    except Exception as e2:
                        err = f"{type(e2).__name__}: {str(e2)[:300]}"
                type_declared = got_type is not None
                if qrows is not None:
                    got_type = got_type or T.infer_type(qrows)
                    got = T.normalize(qrows, got_type)
                rec.update({"query": cy, "error": err, "retried": retried, "type_declared": type_declared})
            else:
                text, usage, _ = chat(args.base_url, args.model, PROSE_SYSTEM,
                                      T.graph_as_text(t) + "\n\nQuestion: " + q["question"], 1024)
                got_type, got = extract_answer(text)
                rec.update({"raw": text[-400:]})
            secs = time.monotonic() - t0
            rec.update({"got_type": got_type, "got": got})
            rec.update(score(q, got_type, got), seconds=round(secs, 3), usage=usage)
            rows.append(rec)
            with open(out, "a") as f:
                f.write(json.dumps(rec) + "\n")
            print(q["id"], "OK" if rec["exact"] else "x", f"{secs:.1f}s", flush=True)
    by = collections.defaultdict(list)
    for r in rows:
        by[r["family"]].append(r)
    summary = {"arm": args.arm, "label": args.label, "model": args.model, "suite_seed": SUITE_SEED,
               "questions": len(rows), "exact": sum(r["exact"] for r in rows),
               "mean_jaccard": round(sum(r["jaccard"] for r in rows) / max(len(rows), 1), 3),
               "mean_seconds": round(sum(r["seconds"] for r in rows) / max(len(rows), 1), 2),
               "query_errors_after_retry": sum(1 for r in rows if r.get("error") and r.get("got") is None),
               "retries": sum(1 for r in rows if r.get("retried")),
               "unsupported": sum(1 for r in rows if r.get("unsupported")),
               "type_mismatches": sum(1 for r in rows if not r["type_match"]),
               "p95_seconds": round(sorted(r["seconds"] for r in rows)[max(0, int(0.95 * len(rows)) - 1)], 3) if rows else None,
               "by_family": {f: f"{sum(r['exact'] for r in v)}/{len(v)}" for f, v in sorted(by.items())}}
    out.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--tenants", type=int, default=12)
    c.set_defaults(func=cmd_check)
    e = sub.add_parser("eval")
    e.add_argument("--arm", choices=["code", "cypher", "prose"], required=True)
    e.add_argument("--base-url", default="")
    e.add_argument("--model", default="local")
    e.add_argument("--label", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--tenants", type=int, default=12)
    e.add_argument("--per-tenant", type=int, default=0, help="smoke tests only")
    e.set_defaults(func=cmd_eval)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
