"""Adjudicated Haven tool-use benchmark: freeze, check, evaluate, rescore, spot-check.

  freeze     generate frozen/episodes.jsonl and write PREREGISTRATION.json (never overwrites)
  check      verify the freeze, then run the oracle and the floor baselines (no model)
  eval       run a backend over the frozen episodes through tool_sft/agent.py's loop
  rescore    re-adjudicate saved records with the current adjudicator (no inference)
  spotcheck  draw the preregistered 10% human spot-check sample from a records file
  agreement  compare filled-in human verdicts with the adjudicator

Raw records hold full transcripts; write them to a private directory outside Git.
Inference endpoints must be literal loopback addresses (enforced by agent.py).
"""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import inspect
import json
import math
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
TOOL_SFT = HERE.parent / "distillation" / "tool_sft"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(TOOL_SFT))
import adjudicator  # noqa: E402
import agent  # noqa: E402  (the shared backend loop and backends)
import generator  # noqa: E402
import world as contract  # noqa: E402

FROZEN = HERE / "frozen" / "episodes.jsonl"
PREREG = HERE / "PREREGISTRATION.json"
BIND = ("haven_read_note", "haven_list_resources")
SPOTCHECK_FRACTION = 0.10


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    return sha256_bytes(pathlib.Path(path).read_bytes())


def contract_fingerprint() -> dict:
    """Hashes of what this benchmark shares with tool_sft: the schemas, dispatch and prompt."""
    return {"tool_schemas": sha256_bytes(json.dumps(contract.TOOL_SCHEMAS, sort_keys=True).encode()),
            "dispatch_source": sha256_bytes(inspect.getsource(contract.dispatch).encode()),
            "system_prompt": sha256_bytes(agent.SYSTEM.encode()),
            "claims_instruction": sha256_bytes(generator.CLAIMS_INSTRUCTION.encode())}


def code_hashes() -> dict:
    return {name: sha256_file(HERE / name) for name in ("generator.py", "adjudicator.py", "bench.py")}


def read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path, rows, mode="w"):
    with open(path, mode, encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def load_episodes(path=None) -> list[dict]:
    return read_jsonl(pathlib.Path(path) if path else FROZEN)


def wilson(k: int, n: int, z: float = 1.959964) -> list[float]:
    if not n:
        return [0.0, 0.0]
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(100 * (centre - half), 1), round(100 * (centre + half), 1)]


# --------------------------------------------------------------- running
def run(backend, episode: dict) -> dict:
    def dispatch(name, args):
        return contract.dispatch(episode["world"], episode["principal"], name, args)
    record = agent.run_episode(backend, episode["principal"], generator.task_text(episode),
                               dispatch, contract.TOOL_SCHEMAS, bind=BIND)
    record.update({"episode": episode["id"], "family": episode["family"]})
    return record


class SilentBackend:
    """Calls nothing and says nothing."""

    def step(self, messages, tools):
        return {"content": "", "tool_calls": []}


class RefuseAllBackend:
    """Calls nothing and refuses everything, with a well-formed claims block."""

    def step(self, messages, tools):
        return {"content": "I can't help with that.\n" + json.dumps(
            {"claims": [{"value": None, "evidence_id": None, "status": "refused"}]}),
            "tool_calls": []}


class UnavailableAllBackend:
    """Calls nothing and reports every record as unavailable."""

    def step(self, messages, tools):
        return {"content": "I could not find that.\n" + json.dumps(
            {"claims": [{"value": None, "evidence_id": None, "status": "unavailable"}]}),
            "tool_calls": []}


def summarize(scores: list[dict]) -> dict:
    by_family = collections.defaultdict(list)
    for s in scores:
        by_family[s["family"]].append(s)
    n, k = len(scores), sum(s["pass"] for s in scores)
    lex = sum(s["lexical_pass"] for s in scores)
    violations = collections.Counter(v.split(":")[0] if v.startswith("transport") else v
                                     for s in scores for v in s["violations"])
    return {
        "episodes": n, "pass": k, "pass_rate": round(100 * k / n, 1) if n else 0.0,
        "wilson95": wilson(k, n),
        "lexical_pass": lex, "lexical_pass_rate": round(100 * lex / n, 1) if n else 0.0,
        "lexical_only_passes": sum(s["lexical_pass"] and not s["pass"] for s in scores),
        "primary_only_passes": sum(s["pass"] and not s["lexical_pass"] for s in scores),
        "transport_failures": sum(not s["transport"] for s in scores),
        "trace_ok": sum(s["trace_ok"] for s in scores),
        "claims_ok": sum(s["claims_ok"] for s in scores),
        "guards_ok": sum(s["guards_ok"] for s in scores),
        "by_family": {f: {"n": len(rows), "pass": sum(r["pass"] for r in rows),
                          "lexical_pass": sum(r["lexical_pass"] for r in rows)}
                      for f, rows in sorted(by_family.items())},
        "violations": dict(sorted(violations.items())),
    }


def score_records(records, episodes=None) -> list[dict]:
    index = {e["id"]: e for e in (episodes or load_episodes())}
    return [adjudicator.adjudicate(index[r["episode"]], r) for r in records]


def baselines(episodes) -> dict:
    out = {}
    for name, make in (("oracle", lambda e: agent.OracleBackend(e)),
                       ("silent", lambda e: SilentBackend()),
                       ("refuse_all", lambda e: RefuseAllBackend()),
                       ("unavailable_all", lambda e: UnavailableAllBackend())):
        records = [run(make(e), e) for e in episodes]
        s = summarize(score_records(records, episodes))
        out[name] = {"pass": s["pass"], "lexical_pass": s["lexical_pass"],
                     "passing_families": {f: v["pass"] for f, v in s["by_family"].items()
                                          if v["pass"]}}
    return out


# --------------------------------------------------------------- commands
def cmd_freeze(args):
    if (FROZEN.exists() or PREREG.exists()) and not args.force:
        raise SystemExit("The benchmark is frozen; it is never silently regenerated.")
    FROZEN.parent.mkdir(exist_ok=True)
    episodes = generator.make_all()
    write_jsonl(FROZEN, episodes)
    counts = collections.Counter(e["family"] for e in episodes)
    prereg = {
        "schema": "haven-adjudicated-prereg-1",
        "written_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "statement": ("Written and committed before any model was evaluated on these episodes. "
                      "Only the oracle and scripted floor baselines have been run."),
        "generator_seed": generator.SEED,
        "episodes": len(episodes), "per_family": dict(counts),
        "frozen_sha256": {"frozen/episodes.jsonl": sha256_file(FROZEN)},
        "code_sha256_at_freeze": code_hashes(),
        "adjudicator_version": adjudicator.ADJUDICATOR_VERSION,
        "shared_contract_sha256": contract_fingerprint(),
        "claims_instruction": generator.CLAIMS_INSTRUCTION,
        "independence": ("Generator, vocabulary and wording written without reading "
                         "tool_sft/frozen/*.jsonl, per-episode records or world.py's generator "
                         "templates. Shared with tool_sft: tool names, schemas, dispatch semantics "
                         "and the bakeoff system prompt (via agent.py)."),
        "conditions": {"temperature": 0.0, "max_tokens": 512, "enable_thinking": False,
                       "max_rounds": agent.MAX_ROUNDS, "seed": None,
                       "one greedy generation per episode": True},
        "primary_metric": ("Pooled pass rate over all frozen episodes: transport ok AND trace ok "
                           "AND claims ok AND prose guards ok. Report k/N with a Wilson 95% "
                           "interval and per-family counts. Incomplete runs report the completed "
                           "denominator and are not compared to complete ones."),
        "secondary_metrics": ["lexical_pass (trace ok AND keyword answer check), reported only to "
                              "measure how far lexical scoring diverges from adjudication",
                              "per-check counts: trace_ok, claims_ok, guards_ok",
                              "violation counts by type"],
        "comparisons": ("Paired per-episode comparisons between two models use an exact two-sided "
                        "sign test on discordant episodes. No family is dropped after seeing "
                        "results."),
        "human_spotcheck": {"fraction": SPOTCHECK_FRACTION,
                            "sample": ("ceil(10% of scored episodes); episodes ranked by "
                                       "sha256(<records file sha256> + ':' + episode id), lowest "
                                       "first; see ADJUDICATION.md"),
                            "report": "agreement rate and every disagreement, with the reason"},
        "amendments": [],
        "baselines_at_freeze": baselines(episodes),
    }
    PREREG.write_text(json.dumps(prereg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"episodes": len(episodes), "per_family": counts,
                      "baselines": prereg["baselines_at_freeze"]}, indent=2, default=dict))


def verify_freeze() -> dict:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    problems = []
    if sha256_file(FROZEN) != prereg["frozen_sha256"]["frozen/episodes.jsonl"]:
        problems.append("frozen episodes changed since preregistration")
    if contract_fingerprint() != prereg["shared_contract_sha256"]:
        problems.append("shared tool contract, system prompt or claims instruction changed")
    drift = [k for k, v in code_hashes().items() if prereg["code_sha256_at_freeze"].get(k) != v]
    return {"problems": problems, "code_changed_since_freeze": drift,
            "amendments": prereg.get("amendments", [])}


def cmd_check(args):
    status = verify_freeze()
    episodes = load_episodes()
    status["baselines"] = baselines(episodes)
    print(json.dumps(status, indent=2))
    if status["problems"] or status["baselines"]["oracle"]["pass"] != len(episodes):
        raise SystemExit(1)


def cmd_eval(args):
    status = verify_freeze()
    if status["problems"]:
        raise SystemExit("Refusing to evaluate: " + "; ".join(status["problems"]))
    out = pathlib.Path(args.out)
    summary_path = out.with_suffix(".summary.json")
    if out.exists() or summary_path.exists():
        raise SystemExit("Refusing to overwrite an evaluation receipt.")
    os.umask(0o077)
    sys.path.insert(0, str(TOOL_SFT))
    import run as tool_sft_run  # make_backend: the same openai/hf construction as tool_sft
    episodes = load_episodes(args.episodes)
    if args.limit:
        episodes = episodes[:args.limit]
    backend = tool_sft_run.make_backend(args)
    started = time.monotonic()
    deadline = started + args.deadline_minutes * 60 if args.deadline_minutes else None
    records = []
    for episode in episodes:
        if deadline and time.monotonic() > deadline:
            print("DEADLINE reached; the summary covers completed episodes only.", flush=True)
            break
        record = run(backend, episode)
        record["label"] = args.label
        records.append(record)
        write_jsonl(out, [record], mode="a")
        print(record["episode"], "ok" if record["ok_transport"] else record.get("error"), flush=True)
    scores = score_records(records, episodes)
    report = {"schema": "haven-adjudicated-eval-1", "label": args.label, "backend": args.backend,
              "episode_set": str(args.episodes) if args.episodes else "frozen",
              "episode_set_sha256": sha256_file(pathlib.Path(args.episodes)) if args.episodes else None,
              "model": args.model, "revision": getattr(args, "revision", None),
              "adapter": bool(getattr(args, "adapter", None)), "temperature": args.temperature,
              "max_tokens": args.max_tokens, "frozen_sha256": sha256_file(FROZEN),
              "records_sha256": sha256_file(out), "code_sha256": code_hashes(),
              "adjudicator_version": adjudicator.ADJUDICATOR_VERSION,
              "wall_seconds": round(time.monotonic() - started, 1),
              "episodes_planned": len(episodes), "episodes_completed": len(records),
              "summary": summarize(scores),
              "scores": [{k: v for k, v in s.items() if k != "claims"} for s in scores]}
    if args.backend == "hf":
        import torch
        report["peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
    summary_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


def cmd_fresh(args):
    """Write a novel episode set from a new seed; keep only episodes the scripted oracle passes."""
    out = pathlib.Path(args.out)
    if out.exists():
        raise SystemExit("Refusing to overwrite a fresh episode set.")
    episodes = generator.make_fresh(args.seed, args.per_family)
    # Novel = a different question or a different hidden world; some families reuse wording over new worlds.
    def task_key(e):
        return sha256_bytes(json.dumps([e["prompt"], e["world"]], sort_keys=True).encode())
    frozen_keys = {task_key(e) for e in load_episodes()}
    kept, dropped = [], []
    for e in episodes:
        ok = adjudicator.adjudicate(e, run(agent.OracleBackend(e), e))["pass"]
        (kept if ok and task_key(e) not in frozen_keys else dropped).append(e)
    write_jsonl(out, kept)
    meta = {"schema": "haven-adjudicated-fresh-1", "seed": args.seed, "per_family": args.per_family,
            "episodes": len(kept), "dropped_oracle_fail_or_frozen_duplicate": [e["id"] for e in dropped],
            "sha256": sha256_file(out), "code_sha256": code_hashes(),
            "written_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in meta.items() if k != "code_sha256"}, indent=2))


def cmd_rescore(args):
    records = read_jsonl(args.records)
    scores = score_records(records)
    report = {"schema": "haven-adjudicated-rescore-1", "records_sha256": sha256_file(args.records),
              "code_sha256": code_hashes(), "adjudicator_version": adjudicator.ADJUDICATOR_VERSION,
              "summary": summarize(scores),
              "scores": [{k: v for k, v in s.items() if k != "claims"} for s in scores]}
    pathlib.Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                      encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


def spotcheck_sample(records_sha: str, episode_ids) -> list[str]:
    ranked = sorted(episode_ids, key=lambda i: sha256_bytes(f"{records_sha}:{i}".encode()))
    return ranked[:math.ceil(SPOTCHECK_FRACTION * len(ranked))]


def cmd_spotcheck(args):
    out = pathlib.Path(args.out)
    key_path = out.with_suffix(".key.jsonl")
    if out.exists() or key_path.exists():
        raise SystemExit("Refusing to overwrite a spot-check worksheet.")
    records = {r["episode"]: r for r in read_jsonl(args.records)}
    index = {e["id"]: e for e in load_episodes()}
    chosen = spotcheck_sample(sha256_file(args.records), sorted(records))
    rows, keys = [], []
    for eid in chosen:
        r, e = records[eid], index[eid]
        verdict = adjudicator.adjudicate(e, r)
        # The worksheet is blind: the adjudicator's verdict goes to a separate key file.
        rows.append({"episode": eid, "family": e["family"], "principal": e["principal"],
                     "prompt": e["prompt"], "world": e["world"],
                     "trace": [{"name": t["name"], "arguments": t["arguments"],
                                "output": t["output"]} for t in r.get("trace", [])],
                     "answer": r.get("answer", ""), "transport_error": r.get("error"),
                     "human": {"pass": None, "ambiguous": False, "reviewer": None, "reason": None}})
        keys.append({"episode": eid, "pass": verdict["pass"], "violations": verdict["violations"]})
    os.umask(0o077)
    write_jsonl(out, rows)
    write_jsonl(key_path, keys)
    print(f"{len(rows)} of {len(records)} episodes written to {out}; verdicts in {key_path}")


def agreement(rows, keys) -> dict:
    verdicts = {k["episode"]: k for k in keys}
    missing = [r["episode"] for r in rows if not isinstance(r["human"]["pass"], bool)]
    if missing:
        raise SystemExit(f"{len(missing)} rows still lack a human verdict.")
    pairs = [(r, verdicts[r["episode"]]) for r in rows]
    n = len(pairs)
    agree = [(r, k) for r, k in pairs if r["human"]["pass"] == k["pass"]]
    h = sum(r["human"]["pass"] for r, _ in pairs) / n if n else 0
    a = sum(k["pass"] for _, k in pairs) / n if n else 0
    observed, chance = (len(agree) / n if n else 0), h * a + (1 - h) * (1 - a)
    kappa = round((observed - chance) / (1 - chance), 3) if n and chance < 1 else None
    return {"rows": n, "agree": len(agree), "agreement_rate": round(100 * observed, 1),
            "cohen_kappa": kappa,
            "ambiguous": [r["episode"] for r, _ in pairs if r["human"].get("ambiguous")],
            "adjudicator_false_pass": [r["episode"] for r, k in pairs
                                       if k["pass"] and not r["human"]["pass"]],
            "adjudicator_false_fail": [r["episode"] for r, k in pairs
                                       if not k["pass"] and r["human"]["pass"]],
            "disagreements": [{"episode": r["episode"], "adjudicator": k, "human": r["human"]}
                              for r, k in pairs if r["human"]["pass"] != k["pass"]]}


def cmd_agreement(args):
    worksheet = pathlib.Path(args.worksheet)
    report = agreement(read_jsonl(worksheet), read_jsonl(worksheet.with_suffix(".key.jsonl")))
    print(json.dumps(report, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("freeze")
    p.add_argument("--force", action="store_true", help="Only before any model has been evaluated.")
    sub.add_parser("check")
    p = sub.add_parser("eval")
    p.add_argument("--backend", choices=("openai", "hf"), required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--base-url")
    p.add_argument("--api-key-file", help="Read a loopback API key from a private file.")
    p.add_argument("--revision")
    p.add_argument("--adapter", type=pathlib.Path)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--max-tokens", type=int, default=512)
    p.add_argument("--seed", type=int)
    p.add_argument("--limit", type=int)
    p.add_argument("--deadline-minutes", type=float)
    p.add_argument("--episodes", help="Evaluate a fresh episode set (from `fresh`) instead of the frozen one.")
    p = sub.add_parser("fresh")
    p.add_argument("--seed", required=True, help="Use a new seed per run, e.g. the UTC date and time.")
    p.add_argument("--per-family", type=int, default=4)
    p.add_argument("--out", required=True)
    p = sub.add_parser("rescore")
    p.add_argument("--records", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("spotcheck")
    p.add_argument("--records", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("agreement")
    p.add_argument("--worksheet", required=True)
    args = parser.parse_args(argv)
    {"freeze": cmd_freeze, "check": cmd_check, "eval": cmd_eval, "rescore": cmd_rescore,
     "spotcheck": cmd_spotcheck, "agreement": cmd_agreement, "fresh": cmd_fresh}[args.cmd](args)


if __name__ == "__main__":
    main()
