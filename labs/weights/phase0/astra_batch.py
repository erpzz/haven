#!/usr/bin/env python3
"""Astra 6.2 teacher batches: export without gold, replay answers through the real harness.

  astra_batch.py export --episodes TRAIN.jsonl --label b1 --private-dir DIR --out b1.jsonl [--ids HARD.txt] [--n 50]
  astra_batch.py replay --private-dir DIR --label b1 --answers b1.answers.jsonl --out-dir R [--teacher astra-6.2]
  astra_batch.py reveal --private-dir DIR --label b1 --out b1.gold.json   # only after replay
  astra_batch.py verify --gold b1.gold.json --commitment HEX

Export (PLAN.md, "Exchange format"). Each record holds what the 4B is given (the system prompt,
the user turn with the claims instruction, the tool catalogue) plus an evidence bundle: the
output of every tool call the episode can answer successfully, computed by the real dispatcher,
and the deterministic rule for every other call. No record holds gold, a family name, a seed,
an oracle plan or the source episode id; ids are salted and the order is shuffled. The gold
payload (episodes with contracts and oracles, the id map, the generator seed commitment) stays
in the private directory. Its salted SHA-256 is printed for posting on #123 with the batch.

Replay. Each answer's tool calls are issued one per round through enforce.run_episode_x with
the advisory checks, the gateway and the verifier on (correction off: a fixed answer cannot
revise). The adjudicator then scores the executed trace and the final answer against gold. A
trace is kept only if it passes with zero blocked or duplicate calls, the same rule as every
other teacher's. Kept traces become SFT rows tagged with the teacher, in the 4B's own message
format (annotations included).
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import random
import secrets
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import dedupe  # noqa: E402
import sft  # noqa: E402
from common import agent, contract, generator  # noqa: E402

SCHEMA = "haven-weights-astra-batch-1"
MAX_BATCH = 50
PLACEHOLDER = "{proposal_id}"
VERDICTS = ("answered", "insufficient evidence", "no action needed", "refused")
ANSWER_SCHEMA = {
    "format": "one JSON object per line (JSONL), one line per batch record",
    "fields": {
        "id": "the batch record id, copied exactly",
        "tool_calls": "ordered list of {\"name\": <tool name>, \"arguments\": {...}} you would make; [] if none. "
                      "At most 5. Each is executed once, in order, by the real harness.",
        "conclusion": "your plain-language answer to the user",
        "claims": "the claims list defined in the user turn (value, evidence_id, status). Cite only ids that "
                  "a call in tool_calls returns. Write a proposal id as {proposal_id}; the replayer fills it "
                  "from the proposal your call creates.",
        "verdict": "optional, for the audit only: one of " + ", ".join(VERDICTS),
    },
    "rules": ["Plain answers only: no commentary about the plan, reserves or other episodes.",
              "Do not look up gold, seeds or generator code before answering.",
              "Use 'unavailable' / 'unknown' (and verdict 'insufficient evidence') when the evidence does not "
              "settle the question; say so rather than guess.",
              "Calls the bundle does not list follow its default rules."],
}


# ------------------------------------------------------------------ evidence bundle
def _dispatch(e, name, args):
    return json.loads(contract.dispatch(e["world"], e["principal"], name, args))


def evidence_bundle(e: dict) -> dict:
    """Every successful tool output the episode can return, plus the rule for everything else.
    Notes the principal cannot read are never listed (the dispatcher never discloses them)."""
    p, world = e["principal"], e["world"]
    readable = [n for n in world["notes"] if n["current"] and p in n["audience"]]
    results = [{"call": {"name": "haven_list_resources", "arguments": {"kind": "devices"}},
                "result": _dispatch(e, "haven_list_resources", {"kind": "devices"})}]
    for owner in sorted({p, "shared"} | {n["owner"] for n in readable}):
        args = {"kind": "notes", "owner": owner}
        results.append({"call": {"name": "haven_list_resources", "arguments": args},
                        "result": _dispatch(e, "haven_list_resources", args)})
    for topic, owner in sorted({(n["topic"], n["owner"]) for n in readable}):
        args = {"topic": topic, "owner": owner}
        results.append({"call": {"name": "haven_read_note", "arguments": args},
                        "result": _dispatch(e, "haven_read_note", dict(args, principal=p))})
    for d in world["devices"]:
        args = {"device_id": d["device_id"]}
        results.append({"call": {"name": "haven_device_state", "arguments": args},
                        "result": _dispatch(e, "haven_device_state", args)})
    return {
        "authenticated_principal": p,
        "results": results,
        "defaults": {
            "haven_read_note": "any (topic, owner) not listed returns {\"ok\": false, \"error\": "
                               "\"NOT_FOUND_OR_NOT_AUTHORIZED\", \"topic\": <topic>, \"owner\": <owner>}. "
                               f"Omitting owner means owner = {p}.",
            "haven_list_resources": "kind=notes for an owner not listed returns that owner with \"topics\": []; "
                                    "any other kind returns {\"ok\": false, \"error\": \"UNKNOWN_KIND\"}.",
            "haven_device_state": "any device_id not listed returns {\"ok\": false, \"error\": \"UNKNOWN_DEVICE\", "
                                  "\"device_id\": <id>}.",
            "haven_propose_action": "records an inert proposal and returns {\"ok\": true, \"proposal_id\": ..., "
                                    "\"action\": ..., \"target\": ..., \"executed\": false, \"authority\": "
                                    "\"PROPOSAL_ONLY\"}; refer to its id as {proposal_id}. Nothing is executed.",
        },
    }


def bundle_lookup(bundle: dict, name: str, args: dict, principal: str):
    """What the bundle says a call returns (used by the completeness test)."""
    a = {k: v for k, v in args.items() if k != "principal"}
    if name == "haven_read_note" and "owner" not in a:
        a["owner"] = principal
    if name == "haven_list_resources" and a.get("kind") == "notes" and "owner" not in a:
        a["owner"] = principal
    for r in bundle["results"]:
        if r["call"]["name"] == name and r["call"]["arguments"] == a:
            return r["result"]
    if name == "haven_read_note":
        return {"ok": False, "error": "NOT_FOUND_OR_NOT_AUTHORIZED", "topic": str(a.get("topic", "")),
                "owner": str(a.get("owner"))}
    if name == "haven_device_state":
        return {"ok": False, "error": "UNKNOWN_DEVICE", "device_id": str(a.get("device_id", ""))}
    if name == "haven_list_resources" and a.get("kind") == "notes":
        return {"ok": True, "kind": "notes", "owner": str(a.get("owner")), "topics": []}
    return None


# ------------------------------------------------------------------ export
def _paths(priv, label):
    return {k: priv / f"{label}.{k}.json" for k in ("gold", "salt", "public")}


def select(episodes, n, rng, ids=None):
    if ids is not None:
        chosen = [e for e in episodes if e["id"] in ids]
        missing = set(ids) - {e["id"] for e in chosen}
        if missing:
            raise SystemExit(f"{len(missing)} requested ids are not in the episode file")
        if len(chosen) > n:
            raise SystemExit(f"{len(chosen)} ids requested; a batch holds at most {n}")
        return chosen
    by = collections.defaultdict(list)
    for e in episodes:
        by[e["family"]].append(e)
    for v in by.values():
        rng.shuffle(v)
    chosen, fams = [], sorted(by)
    while len(chosen) < n and any(by.values()):      # stratified round-robin over families
        for f in fams:
            if by[f] and len(chosen) < n:
                chosen.append(by[f].pop())
    return chosen


def export_batch(episodes, label, n=MAX_BATCH, ids=None, seed_commitment=None):
    """(public_records, gold_payload, salt, commitment)."""
    if n > MAX_BATCH:
        raise SystemExit(f"batches hold at most {MAX_BATCH} episodes")
    if any(not e["id"].startswith("train-") for e in episodes):
        raise SystemExit("only training-pool episodes can go to a teacher")
    rep = dedupe.check_items([dedupe.hare_item(e) for e in episodes], dedupe.load_fingerprint())
    if rep["rejected"]:
        raise SystemExit(f"dedupe rejected {len(rep['rejected'])} episodes; refusing to export")
    rng = random.Random(secrets.token_bytes(32))
    chosen = select(episodes, n, rng, ids)
    rng.shuffle(chosen)
    salt = common.new_salt()
    records, idmap = [], {}
    for e in chosen:
        rid = "a-" + common.sha256_bytes(bytes.fromhex(salt) + e["id"].encode())[:12]
        idmap[rid] = e["id"]
        records.append({"id": rid, "batch": label, "system": agent.SYSTEM,
                        "user": agent.user_message(e["principal"], generator.task_text(e)),
                        "tools": contract.TOOL_SCHEMAS, "evidence_bundle": evidence_bundle(e),
                        "answer_schema": ANSWER_SCHEMA})
    gold = {"schema": SCHEMA + "-gold", "batch": label, "generator_seed_commitment": seed_commitment,
            "records": [{"id": rid, "episode": next(e for e in chosen if e["id"] == idmap[rid])}
                        for rid in idmap]}
    return records, gold, salt, common.commit(salt, gold)


def cmd_export(args):
    priv = common.private_dir(args.private_dir)
    paths = _paths(priv, args.label)
    common.refuse_overwrite(args.out, *paths.values())
    ids = set(pathlib.Path(args.ids).read_text().split()) if args.ids else None
    seed_commitment = None
    for f in priv.glob("*.seed.json"):
        seed_commitment = json.loads(f.read_text())["commitment"]
    records, gold, salt, digest = export_batch(common.read_jsonl(args.episodes), args.label, args.n, ids,
                                               seed_commitment)
    common.write_jsonl(args.out, records)
    paths["gold"].write_text(json.dumps(gold, sort_keys=True) + "\n")
    paths["salt"].write_text(json.dumps({"salt": salt, "commitment": digest}) + "\n")
    public = {"schema": SCHEMA, "batch": args.label, "episodes": len(records),
              "batch_sha256": common.sha256_file(args.out), "gold_commitment": digest,
              "commitment_rule": "sha256(bytes.fromhex(salt) + canonical_json(gold)); canonical = sort_keys, "
                                 "separators (',', ':'), UTF-8",
              "code_sha256": common.code_hashes(["astra_batch.py", "common.py", "dedupe.py"])}
    paths["public"].write_text(json.dumps(public, indent=2) + "\n")
    print(json.dumps(public, indent=2))


# ------------------------------------------------------------------ replay
class AnswerBackend:
    """Replays one teacher answer: one tool call per round, then the conclusion and claims."""

    def __init__(self, answer: dict):
        self.calls = [dict(c) for c in answer["tool_calls"]]
        self.conclusion, self.claims = answer["conclusion"], answer["claims"]

    def step(self, messages, tools):
        if self.calls:
            c = self.calls.pop(0)
            return {"content": "", "tool_calls": [{"name": c["name"], "arguments": dict(c["arguments"])}]}
        pid = None
        for m in common.strip_annotations(messages):
            if m["role"] == "tool" and m["name"] == "haven_propose_action":
                try:
                    out = json.loads(m["content"])
                except ValueError:
                    continue
                if out.get("ok") and out.get("proposal_id"):
                    pid = out["proposal_id"]
        text = self.conclusion.strip() + "\n" + json.dumps({"claims": self.claims})
        if pid:
            text = text.replace(PLACEHOLDER, pid)
        return {"content": text, "tool_calls": []}


def validate(answer) -> str | None:
    if not isinstance(answer, dict):
        return "not an object"
    if not isinstance(answer.get("id"), str):
        return "id missing"
    calls = answer.get("tool_calls")
    if not isinstance(calls, list) or len(calls) > agent.MAX_ROUNDS - 1:
        return f"tool_calls must be a list of at most {agent.MAX_ROUNDS - 1}"
    for c in calls:
        if not (isinstance(c, dict) and c.get("name") in contract.TOOL_NAMES and isinstance(c.get("arguments"), dict)):
            return "tool call with an unknown tool or non-object arguments"
    if not isinstance(answer.get("conclusion"), str):
        return "conclusion missing"
    claims = answer.get("claims")
    if not isinstance(claims, list) or not claims or not all(isinstance(c, dict) for c in claims):
        return "claims must be a non-empty list of objects"
    if answer.get("verdict") not in (None, *VERDICTS):
        return "unknown verdict"
    return None


def replay(gold: dict, answers: list, teacher: str) -> dict:
    episodes = {r["id"]: r["episode"] for r in gold["records"]}
    seen, rows, results = collections.Counter(a.get("id") for a in answers if isinstance(a, dict)), [], []
    attempted = set()
    for a in answers:
        problem = validate(a)
        rid = a.get("id") if isinstance(a, dict) else None
        if rid in episodes:
            attempted.add(rid)
        if problem is None and rid not in episodes:
            problem = "unknown id"
        if problem is None and seen[rid] > 1:
            problem = "duplicate id"
        if problem:
            results.append({"id": rid, "status": "schema_invalid", "problem": problem, "keep": False})
            continue
        e = episodes[rid]
        rec = common.run_harness(AnswerBackend(a), e, common.REPLAY)
        m = common.judge(rec, e)
        results.append({"id": rid, "episode": e["id"], "family": e["family"], "status": "replayed",
                        "keep": m["keep"], "pass": m["pass"], "blocked": m["blocked_any"],
                        "blocked_policies": sorted({x["policy"] for x in rec["attempts"] if not x["executed"]}),
                        "violations": m["violations"], "verifier": rec.get("raw_problems"),
                        "verdict": a.get("verdict")})
        if m["keep"]:
            rows += sft.rows_from_record(rec, source="teacher", arm="B", teacher=teacher, episode_id=e["id"])
    for rid in sorted(set(episodes) - attempted):
        results.append({"id": rid, "episode": episodes[rid]["id"], "family": episodes[rid]["family"],
                        "status": "no_answer", "keep": False})
    kept = sum(r["keep"] for r in results)
    fam = collections.defaultdict(lambda: [0, 0])
    for r in results:
        if r.get("family"):
            fam[r["family"]][0] += r["keep"]
            fam[r["family"]][1] += 1
    return {"rows": rows, "results": results,
            "summary": {"batch": gold["batch"], "teacher": teacher, "episodes": len(episodes),
                        "answers": len(answers), "kept": kept,
                        "keep_rate": round(kept / len(episodes), 3) if episodes else 0.0,
                        "schema_invalid": sum(r["status"] == "schema_invalid" for r in results),
                        "no_answer": sum(r["status"] == "no_answer" for r in results),
                        "blocked_episodes": sum(bool(r.get("blocked")) for r in results),
                        "by_family": {f: f"{k}/{n}" for f, (k, n) in sorted(fam.items())},
                        "rows": len(rows)}}


def cmd_replay(args):
    priv = pathlib.Path(args.private_dir)
    gold = json.loads(_paths(priv, args.label)["gold"].read_text())
    out = pathlib.Path(args.out_dir)
    paths = {k: out / f"{args.label}.{k}" for k in ("kept-rows.jsonl", "results.jsonl", "summary.json")}
    common.refuse_overwrite(*paths.values())
    res = replay(gold, common.read_jsonl(args.answers), args.teacher)
    common.write_jsonl(paths["kept-rows.jsonl"], res["rows"])
    common.write_jsonl(paths["results.jsonl"], res["results"])
    res["summary"].update({"answers_sha256": common.sha256_file(args.answers),
                           "kept_rows_sha256": common.sha256_file(paths["kept-rows.jsonl"])})
    paths["summary.json"].write_text(json.dumps(res["summary"], indent=2) + "\n")
    print(json.dumps(res["summary"], indent=2))


def cmd_reveal(args):
    paths = _paths(pathlib.Path(args.private_dir), args.label)
    gold, salt = json.loads(paths["gold"].read_text()), json.loads(paths["salt"].read_text())
    if not common.check_commitment(salt["salt"], gold, salt["commitment"]):
        raise SystemExit("stored gold does not match its commitment")
    common.refuse_overwrite(args.out)
    pathlib.Path(args.out).write_text(json.dumps({"salt": salt["salt"], "commitment": salt["commitment"],
                                                  "gold": gold}, sort_keys=True, indent=1) + "\n")
    print(f"{args.out}: commitment {salt['commitment']} verifies")


def cmd_verify(args):
    obj = json.loads(pathlib.Path(args.gold).read_text())
    ok = common.check_commitment(obj["salt"], obj["gold"], args.commitment)
    print(json.dumps({"commitment": args.commitment, "verifies": ok}))
    if not ok:
        raise SystemExit(1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--episodes", required=True)
    e.add_argument("--label", required=True)
    e.add_argument("--private-dir", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--ids")
    e.add_argument("--n", type=int, default=MAX_BATCH)
    r = sub.add_parser("replay")
    r.add_argument("--private-dir", required=True)
    r.add_argument("--label", required=True)
    r.add_argument("--answers", required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--teacher", default="astra-6.2")
    v = sub.add_parser("reveal")
    v.add_argument("--private-dir", required=True)
    v.add_argument("--label", required=True)
    v.add_argument("--out", required=True)
    c = sub.add_parser("verify")
    c.add_argument("--gold", required=True)
    c.add_argument("--commitment", required=True)
    args = ap.parse_args(argv)
    {"export": cmd_export, "replay": cmd_replay, "reveal": cmd_reveal, "verify": cmd_verify}[args.cmd](args)


if __name__ == "__main__":
    main()
