#!/usr/bin/env python3
"""Astra 6.2 teacher batches, stepwise (Amendment 1, section 5). Nothing is sent before both gates.

  astra_batch.py export --episodes TRAIN.jsonl --label b1 --private-dir DIR --out b1.round0.jsonl [--ids HARD.txt]
  astra_batch.py step   --private-dir DIR --label b1 --reply b1.reply1.jsonl --out b1.obs1.jsonl   # repeat per round
  astra_batch.py seal   --private-dir DIR --label b1                                              # post the seal
  astra_batch.py replay --private-dir DIR --label b1 --out-dir R [--teacher astra-6.2]
  astra_batch.py reveal --private-dir DIR --label b1 --out b1.gold.json                           # only after seal
  astra_batch.py audit-sample --kept R/b1.kept-rows.jsonl [--n 50]
  astra_batch.py verify --gold b1.gold.json --commitment HEX

Input (round 0): per opaque id, the system prompt and the user turn exactly as the 4B sees them in
the full harness, the authorized tool catalogue, and the initially visible observations (none for
HARE). No tool output is sent up front.

Each round the teacher returns one line per open id: either one tool call, or its final record.
`step` runs every call through the real harness on the frozen fixture: the gateway, the
dispatcher and the advisory checks. The observation file carries only the result of the call just
made, in the 4B's message format. A later result can never be seen before an earlier call.

Final record: schema, batch and id; the ordered tool calls (must equal the session's); a terminal
disposition (answer, insufficient_evidence, no_action_needed, refusal; clarification is not
allowed for HARE tasks); a concise conclusion; and claims whose evidence_id citations map to
records the session actually returned.

Seal, then reveal. `seal` hashes every final record and call history; after it no step is
accepted, and only then can the gold be revealed. Replay recomputes every output from the
fixtures, checks it against what was delivered, and keeps a trace only if it passes gold with
zero blocked or duplicate calls, its citations were returned, its disposition agrees with its
claims and it matches its session. Correction is off: a fallback rescue can never be kept.
"""
from __future__ import annotations

import argparse
import collections
import datetime
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
from common import agent, contract  # noqa: E402

SCHEMA = "haven-weights-astra-stepwise-1"
MAX_BATCH = 50
MAX_CALLS = agent.MAX_ROUNDS - 1
PLACEHOLDER = "{proposal_id}"
DISPOSITIONS = ("answer", "insufficient_evidence", "no_action_needed", "refusal", "clarification")
ALLOWED_DISPOSITIONS = DISPOSITIONS[:4]          # no HARE task allows clarification
REPLY_SCHEMA = {
    "format": "JSONL, one line per open id per round",
    "call": {"schema": SCHEMA, "batch": "<batch>", "id": "<id>", "round": "<number of calls you have made so far>",
             "action": "call", "call": {"name": "<tool>", "arguments": {}}},
    "final": {"schema": SCHEMA, "batch": "<batch>", "id": "<id>", "action": "final",
              "final": {"tool_calls": "every call you made, in order, exactly as sent",
                        "disposition": " | ".join(ALLOWED_DISPOSITIONS),
                        "conclusion": "concise plain-language answer to the user",
                        "claims": "the claims list defined in the user turn; evidence_id must be a record a call in "
                                  "this session returned; write a proposal id as {proposal_id}"}},
    "rules": [f"At most {MAX_CALLS} calls per id, one per round.",
              "Plain answers only: no hidden reasoning, no commentary on the plan, reserves or other episodes.",
              "Answer in a clean context without reserves, gold, seeds, the generator or audit material.",
              "Use 'unavailable' / 'unknown' claims and disposition insufficient_evidence when the evidence returned "
              "does not settle the question."],
}


def tool_versions() -> dict:
    hare = next(s for s in common.SPEC["sources"] if s["name"] == "hare-s0")
    return {"schema": SCHEMA, "tool_catalogue_sha256": common.sha256_bytes(common.canonical(contract.TOOL_SCHEMAS)),
            "harness_sha256": {n.rsplit("/", 1)[-1]: h for n, h in hare["files"].items() if n.endswith(".py")},
            "mechanisms": common.REPLAY}


# ------------------------------------------------------------------ the stepwise oracle (frozen fixtures)
class _NeedNext(Exception):
    pass


class _Prefix:
    """Emits the calls made so far, one per round, then stops the loop to read the last observation."""

    def __init__(self, calls):
        self.calls = [dict(c) for c in calls]

    def step(self, messages, tools):
        if self.calls:
            c = self.calls.pop(0)
            return {"content": "", "tool_calls": [{"name": c["name"], "arguments": dict(c["arguments"])}]}
        raise _NeedNext()


def opening(episode: dict) -> list[dict]:
    """The system and user messages the 4B gets in the full harness (request note included)."""
    return common.run_harness(_Prefix([]), episode, common.REPLAY)["messages"][:2]


def observe(episode: dict, calls: list[dict]) -> str:
    """The tool message the harness returns for the last call, given the calls before it."""
    rec = common.run_harness(_Prefix(calls), episode, common.REPLAY)
    return [m for m in rec["messages"] if m["role"] == "tool"][-1]["content"]


# ------------------------------------------------------------------ private state
def _paths(priv, label):
    names = ("gold.json", "salt.json", "session.json", "seal.json", "public.json")
    return {n.split(".")[0]: pathlib.Path(priv) / f"{label}.{n}" for n in names}


def _load(p):
    return json.loads(pathlib.Path(p).read_text())


def _save(p, obj):
    pathlib.Path(p).write_text(json.dumps(obj, sort_keys=True, indent=1) + "\n")


# ------------------------------------------------------------------ export
def select(episodes, n, rng, ids=None):
    if ids is not None:
        chosen = [e for e in episodes if e["id"] in ids]
        if set(ids) - {e["id"] for e in chosen}:
            raise SystemExit("some requested ids are not in the episode file")
        if len(chosen) > n:
            raise SystemExit(f"{len(chosen)} ids requested; a batch holds at most {n}")
        return chosen
    by = collections.defaultdict(list)
    for e in episodes:
        by[e["family"]].append(e)
    for v in by.values():
        rng.shuffle(v)
    chosen = []
    while len(chosen) < n and any(by.values()):
        for f in sorted(by):
            if by[f] and len(chosen) < n:
                chosen.append(by[f].pop())
    return chosen


def export_batch(episodes, label, n=MAX_BATCH, ids=None, seed_commitment=None):
    """(round0 records, gold, salt, gold commitment, session)."""
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
    records, gold_records, session = [], [], {}
    for e in chosen:
        rid = "a-" + common.sha256_bytes(bytes.fromhex(salt) + e["id"].encode())[:12]
        sys_msg, user_msg = opening(e)
        records.append({"schema": SCHEMA, "batch": label, "id": rid, "system": sys_msg["content"],
                        "user": user_msg["content"], "tools": contract.TOOL_SCHEMAS, "initial_observations": [],
                        "max_tool_calls": MAX_CALLS, "reply_schema": REPLY_SCHEMA})
        gold_records.append({"id": rid, "episode": e})
        session[rid] = {"calls": [], "observations": [], "final": None, "rejected": None}
    gold = {"schema": SCHEMA + "-gold", "batch": label, "generator_seed_commitment": seed_commitment,
            "versions": tool_versions(), "records": gold_records}
    return records, gold, salt, common.commit(salt, gold), session


def cmd_export(args):
    priv = common.private_dir(args.private_dir)
    paths = _paths(priv, args.label)
    common.refuse_overwrite(args.out, *paths.values())
    ids = set(pathlib.Path(args.ids).read_text().split()) if args.ids else None
    seed_commitment = None
    for f in sorted(priv.glob("*.seed.json")):
        seed_commitment = _load(f)["commitment"]
    records, gold, salt, digest, session = export_batch(common.read_jsonl(args.episodes), args.label, args.n, ids,
                                                        seed_commitment)
    common.write_jsonl(args.out, records)
    _save(paths["gold"], gold)
    _save(paths["salt"], {"salt": salt, "commitment": digest})
    _save(paths["session"], session)
    public = {"schema": SCHEMA, "batch": args.label, "episodes": len(records),
              "round0_sha256": common.sha256_file(args.out), "versions": tool_versions(),
              "gold_commitment": digest, "commitment_rule": common.COMMITMENT_RULE,
              "code_sha256": common.code_hashes(["astra_batch.py", "common.py", "dedupe.py"])}
    _save(paths["public"], public)
    print(json.dumps(public, indent=2))


# ------------------------------------------------------------------ step
def step(gold: dict, session: dict, replies: list) -> tuple[list[dict], dict]:
    """Apply one round of replies. Returns (observations to send, per-id status)."""
    episodes = {r["id"]: r["episode"] for r in gold["records"]}
    counts = collections.Counter(r.get("id") for r in replies if isinstance(r, dict))
    out, status = [], {}
    for r in replies:
        rid = r.get("id") if isinstance(r, dict) else None
        if rid not in session:
            status[str(rid)] = "unknown id"
            continue
        s = session[rid]
        if s["final"] is not None or s["rejected"]:
            status[rid] = "closed"
            continue
        problem = None
        if counts[rid] > 1:
            problem = "more than one line for this id in one round"
        elif r.get("schema") != SCHEMA or r.get("batch") != gold["batch"]:
            problem = "wrong schema or batch"
        elif r.get("action") == "call":
            c = r.get("call")
            if r.get("round") != len(s["calls"]):
                problem = f"round {r.get('round')} but {len(s['calls'])} calls made"
            elif len(s["calls"]) >= MAX_CALLS:
                problem = f"more than {MAX_CALLS} calls"
            elif not (isinstance(c, dict) and c.get("name") in contract.TOOL_NAMES and isinstance(c.get("arguments"), dict)):
                problem = "illegal call: unknown tool or non-object arguments"
        elif r.get("action") == "final":
            if not isinstance(r.get("final"), dict):
                problem = "final record missing"
        else:
            problem = "action must be call or final"
        if problem:
            s["rejected"] = problem
            status[rid] = "rejected: " + problem
            continue
        if r["action"] == "final":
            s["final"] = r["final"]
            status[rid] = "final received"
            continue
        call = {"name": r["call"]["name"], "arguments": r["call"]["arguments"]}
        s["calls"].append(call)
        obs = observe(episodes[rid], s["calls"])
        s["observations"].append(obs)
        out.append({"schema": SCHEMA, "batch": gold["batch"], "id": rid, "round": len(s["calls"]) - 1,
                    "call": call, "result": obs})
        status[rid] = "observation sent"
    return out, status


def cmd_step(args):
    paths = _paths(args.private_dir, args.label)
    if paths["seal"].exists():
        raise SystemExit("batch is sealed; no further steps")
    gold, session = _load(paths["gold"]), _load(paths["session"])
    common.refuse_overwrite(args.out)
    obs, status = step(gold, session, common.read_jsonl(args.reply))
    _save(paths["session"], session)
    common.write_jsonl(args.out, obs)
    open_ids = [k for k, v in session.items() if v["final"] is None and not v["rejected"]]
    print(json.dumps({"observations": len(obs), "open": len(open_ids),
                      "status": dict(collections.Counter(v.split(":")[0] for v in status.values()))}, indent=2))


# ------------------------------------------------------------------ seal
def _seal_binding(gold, session, public=None) -> dict:
    """Deterministic batch/session binding. Refuse open, duplicate, foreign or contradictory terminal state."""
    if public is None:
        public = {"schema": SCHEMA, "batch": gold.get("batch"), "versions": gold.get("versions"),
                  "round0_sha256": None, "gold_commitment": None}
    gold_ids = [row.get("id") for row in gold.get("records", []) if isinstance(row, dict)]
    if (not gold_ids or len(gold_ids) != len(set(gold_ids))
            or set(gold_ids) != set(session)
            or gold.get("batch") != public.get("batch")
            or public.get("schema") != SCHEMA
            or gold.get("versions") != public.get("versions")):
        raise ValueError("batch/session/public identity mismatch")
    payload = {}
    finals = rejected = 0
    for rid in sorted(gold_ids):
        state = session.get(rid)
        if not isinstance(state, dict):
            raise ValueError("malformed session state")
        has_final = state.get("final") is not None
        has_rejection = bool(state.get("rejected"))
        if has_final == has_rejection:  # neither terminal, or contradictory double-terminal
            raise ValueError(f"session id {rid} is not exactly one terminal state")
        finals += has_final
        rejected += has_rejection
        payload[rid] = {"calls": state.get("calls") or [], "final": state.get("final"),
                        "rejected": state.get("rejected")}
    return {
        "schema": SCHEMA + "-seal",
        "batch": gold["batch"],
        "assigned": len(gold_ids),
        "finals": finals,
        "rejected_in_session": rejected,
        "open": 0,
        "assigned_ids_sha256": common.sha256_bytes(common.canonical(sorted(gold_ids))),
        "answers_sha256": common.sha256_bytes(common.canonical(payload)),
        "session_sha256": common.sha256_bytes(common.canonical(session)),
        "round0_sha256": public.get("round0_sha256"),
        "gold_commitment": public.get("gold_commitment"),
        "versions_sha256": common.sha256_bytes(common.canonical(public.get("versions"))),
    }


def seal_record(gold, session, public=None) -> dict:
    rec = _seal_binding(gold, session, public)
    rec["sealed_utc"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return rec


def validate_seal(gold, session, public, seal) -> list[str]:
    problems = []
    try:
        current = _seal_binding(gold, session, public)
    except (TypeError, ValueError) as exc:
        return [str(exc)]
    if not isinstance(seal, dict):
        return ["seal is not an object"]
    for key, value in current.items():
        if seal.get(key) != value:
            problems.append(f"seal mismatch: {key}")
    return problems


def cmd_seal(args):
    paths = _paths(args.private_dir, args.label)
    common.refuse_overwrite(paths["seal"])
    gold, session, public = _load(paths["gold"]), _load(paths["session"]), _load(paths["public"])
    try:
        rec = seal_record(gold, session, public)
    except ValueError as exc:
        raise SystemExit(f"refusing to seal: {exc}") from exc
    _save(paths["seal"], rec)
    print(json.dumps(rec, indent=2))


# ------------------------------------------------------------------ replay
class AnswerBackend:
    """Replays a sealed session: its calls one per round, then the conclusion and claims."""

    def __init__(self, calls, final):
        self.calls = [dict(c) for c in calls]
        self.final = final

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
        text = self.final["conclusion"].strip() + "\n" + json.dumps({"claims": self.final["claims"]})
        return {"content": text.replace(PLACEHOLDER, pid) if pid else text, "tool_calls": []}


def validate_final(final, calls) -> str | None:
    if not isinstance(final, dict):
        return "final record is not an object"
    if final.get("tool_calls") != calls:
        return "final tool_calls differ from the calls made in the session"
    if final.get("disposition") not in DISPOSITIONS:
        return "unknown disposition"
    if final["disposition"] not in ALLOWED_DISPOSITIONS:
        return "disposition not allowed for this task (clarification)"
    if not isinstance(final.get("conclusion"), str) or not final["conclusion"].strip():
        return "conclusion missing"
    claims = final.get("claims")
    if not isinstance(claims, list) or not claims or not all(isinstance(c, dict) for c in claims):
        return "claims must be a non-empty list of objects"
    return None


def disposition_problem(final, trace) -> str | None:
    """Disposition must agree with the claims and the executed trace."""
    st = [c.get("status") for c in final["claims"]]
    d = final["disposition"]
    proposed = any(t["name"] == "haven_propose_action" and (t.get("output") or {}).get("ok") for t in trace)
    if ("refused" in st) != (d == "refusal"):
        return "refusal disposition and refused claim must go together"
    if d == "insufficient_evidence" and (not any(s in ("unavailable", "unknown") for s in st) or "proposed" in st):
        return "insufficient_evidence needs an unavailable/unknown claim and no proposal"
    if d == "no_action_needed" and (proposed or "proposed" in st):
        return "no_action_needed with a proposal"
    if d == "answer" and not any(s in ("supported", "conflicting", "direct", "proposed") for s in st):
        return "answer disposition without an asserted claim"
    return None


def unreturned_citations(final, trace) -> list[str]:
    """Citations must name records this session's executed calls returned (no future or unreturned ids)."""
    seen = set(common.adjudicator.evidence_map(trace))
    return [str(c["evidence_id"]) for c in final["claims"]
            if c.get("evidence_id") not in (None, "", PLACEHOLDER) and c.get("evidence_id") not in seen]


def replay(gold: dict, session: dict, seal: dict | None, teacher: str) -> dict:
    if seal is None or seal.get("answers_sha256") != seal_record(gold, session)["answers_sha256"]:
        raise SystemExit("session is not sealed, or changed after sealing")
    episodes = {r["id"]: r["episode"] for r in gold["records"]}
    rows, results = [], []
    for rid, s in sorted(session.items()):
        e = episodes[rid]
        base = {"id": rid, "episode": e["id"], "family": e["family"], "keep": False}
        if s["rejected"]:
            results.append(dict(base, status="rejected_in_session", problem=s["rejected"]))
            continue
        if s["final"] is None:
            results.append(dict(base, status="no_answer"))
            continue
        problem = validate_final(s["final"], s["calls"])
        if problem:
            results.append(dict(base, status="malformed", problem=problem))
            continue
        if [observe(e, s["calls"][:i + 1]) for i in range(len(s["calls"]))] != s["observations"]:
            results.append(dict(base, status="fixture_mismatch", problem="recomputed observations differ from delivered"))
            continue
        rec = common.run_harness(AnswerBackend(s["calls"], s["final"]), e, common.REPLAY)
        m = common.judge(rec, e)
        cites = unreturned_citations(s["final"], rec["trace"])
        disp = disposition_problem(s["final"], rec["trace"])
        keep = bool(m["keep"] and m["views"]["model_clean"] and not cites and not disp)
        results.append(dict(base, status="replayed", keep=keep, adjudicator_pass=m["pass"], views=m["views"],
                            blocked=m["blocked_any"],
                            blocked_policies=sorted({x["policy"] for x in rec["attempts"] if not x["executed"]}),
                            violations=m["violations"], unreturned_citations=cites, disposition_problem=disp,
                            disposition=s["final"]["disposition"], verifier=rec.get("raw_problems")))
        if keep:
            rows += sft.rows_from_record(rec, source="teacher", arm="B", teacher=teacher, episode_id=e["id"])
    fam = collections.defaultdict(lambda: {"offered": 0, "accepted": 0, "zero_pass": 0})
    for r in results:
        f = fam[r["family"]]
        f["offered"] += 1
        f["accepted"] += r["keep"]
        f["zero_pass"] += not r["keep"]
    kept = sum(r["keep"] for r in results)
    return {"rows": sft.apply_episode_weights(rows), "results": results,
            "summary": {"batch": gold["batch"], "teacher": teacher, "offered": len(results), "accepted": kept,
                        "zero_pass": len(results) - kept,
                        "status": dict(collections.Counter(r["status"] for r in results)),
                        "by_family": dict(sorted(fam.items())), "rows": len(rows),
                        "seal_answers_sha256": seal["answers_sha256"]}}


def cmd_replay(args):
    paths = _paths(args.private_dir, args.label)
    if not paths["seal"].exists():
        raise SystemExit("seal the batch first")
    gold, session, public, seal = (_load(paths["gold"]), _load(paths["session"]),
                                   _load(paths["public"]), _load(paths["seal"]))
    problems = validate_seal(gold, session, public, seal)
    if problems:
        raise SystemExit("sealed session no longer validates: " + "; ".join(problems))
    out = pathlib.Path(args.out_dir)
    files = {k: out / f"{args.label}.{k}" for k in ("kept-rows.jsonl", "results.jsonl", "summary.json")}
    common.refuse_overwrite(*files.values())
    res = replay(gold, session, seal, args.teacher)
    common.write_jsonl(files["kept-rows.jsonl"], res["rows"])
    common.write_jsonl(files["results.jsonl"], res["results"])
    res["summary"]["kept_rows_sha256"] = common.sha256_file(files["kept-rows.jsonl"])
    files["summary.json"].write_text(json.dumps(res["summary"], indent=2) + "\n")
    print(json.dumps(res["summary"], indent=2))


# ------------------------------------------------------------------ reveal, verify, audit
def cmd_reveal(args):
    paths = _paths(args.private_dir, args.label)
    if not paths["seal"].exists():
        raise SystemExit("answers must be sealed before the gold commitment is opened")
    gold, salt = _load(paths["gold"]), _load(paths["salt"])
    session, public, seal = _load(paths["session"]), _load(paths["public"]), _load(paths["seal"])
    if not common.check_commitment(salt["salt"], gold, salt["commitment"]):
        raise SystemExit("stored gold does not match its commitment")
    if public.get("gold_commitment") != salt.get("commitment"):
        raise SystemExit("public batch commitment does not match stored gold commitment")
    problems = validate_seal(gold, session, public, seal)
    if problems:
        raise SystemExit("sealed session no longer validates: " + "; ".join(problems))
    common.refuse_overwrite(args.out)
    pathlib.Path(args.out).write_text(json.dumps({"salt": salt["salt"], "commitment": salt["commitment"],
                                                  "seal": seal, "gold": gold},
                                                 sort_keys=True, indent=1) + "\n")
    print(f"{args.out}: commitment {salt['commitment']} and current seal verify")


def cmd_verify(args):
    obj = _load(args.gold)
    ok = common.check_commitment(obj["salt"], obj["gold"], args.commitment)
    print(json.dumps({"commitment": args.commitment, "verifies": ok}))
    if not ok:
        raise SystemExit(1)


def audit_sample(kept_rows_path, n=50) -> dict:
    """Up to n kept traces without replacement, drawn by an RNG keyed to the fixed kept-rows bytes, so
    the sample is decided by the manifest, not by whoever runs the draw."""
    digest = common.sha256_file(kept_rows_path)
    traces = sorted({(r["episode"], r["teacher"]) for r in common.read_jsonl(kept_rows_path)})
    chosen = random.Random(digest).sample(traces, min(n, len(traces)))
    return {"kept_rows_sha256": digest, "traces": len(traces), "sampled": len(chosen),
            "sample": [{"episode": e, "teacher": t} for e, t in sorted(chosen)]}


def cmd_audit(args):
    print(json.dumps(audit_sample(args.kept, args.n), indent=2))


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
    s = sub.add_parser("step")
    s.add_argument("--private-dir", required=True)
    s.add_argument("--label", required=True)
    s.add_argument("--reply", required=True)
    s.add_argument("--out", required=True)
    z = sub.add_parser("seal")
    z.add_argument("--private-dir", required=True)
    z.add_argument("--label", required=True)
    r = sub.add_parser("replay")
    r.add_argument("--private-dir", required=True)
    r.add_argument("--label", required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--teacher", default="astra-6.2")
    v = sub.add_parser("reveal")
    v.add_argument("--private-dir", required=True)
    v.add_argument("--label", required=True)
    v.add_argument("--out", required=True)
    c = sub.add_parser("verify")
    c.add_argument("--gold", required=True)
    c.add_argument("--commitment", required=True)
    a = sub.add_parser("audit-sample")
    a.add_argument("--kept", required=True)
    a.add_argument("--n", type=int, default=50)
    args = ap.parse_args(argv)
    {"export": cmd_export, "step": cmd_step, "seal": cmd_seal, "replay": cmd_replay, "reveal": cmd_reveal,
     "verify": cmd_verify, "audit-sample": cmd_audit}[args.cmd](args)


if __name__ == "__main__":
    main()
