"""Freeze splits, evaluate backends, collect verified teacher data, build SFT sets.

  freeze   write the frozen train/dev/held-out episodes (synthetic, checked in)
  eval     run a backend over dev, held-out and/or the legacy 8-task benchmark
  collect  run the teacher over training episodes until a deadline (resumable)
  build    verified teacher trajectories -> per-turn SFT rows (+ matched oracle control)
  compare  paired before/after comparison of two eval receipts
  rescore  re-verify saved eval records with the current checks (no inference)
  oracle-data  exploratory: oracle trajectories for every training episode

Raw transcripts and API keys never belong in Git; write outputs to a private
directory. Inference endpoints must be literal loopback addresses.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agent  # noqa: E402
import world  # noqa: E402

FROZEN = HERE / "frozen"
LEGACY_TASKS = agent.BAKEOFF / "tasks.json"
SIZES = {"train": 40, "dev": 4, "heldout_paraphrase": 6, "heldout_composition": 10}


def read_jsonl(path):
    return [json.loads(line) for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]


def write_jsonl(path, rows, mode="w"):
    with pathlib.Path(path).open(mode, encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def load_split(name):
    return read_jsonl(FROZEN / f"{name}.jsonl")


def cmd_freeze(args):
    FROZEN.mkdir(exist_ok=True)
    splits = {
        "train": world.make_split("train", SIZES["train"]),
        "dev": world.make_split("dev", SIZES["dev"]),
        "heldout": (world.make_split("heldout", SIZES["heldout_paraphrase"], world.TRAIN_FAMILIES)
                    + world.make_split("heldout", SIZES["heldout_composition"],
                                       world.COMPOSITION_FAMILIES)),
    }
    hashes = {}
    for name, episodes in splits.items():
        path = FROZEN / f"{name}.jsonl"
        if path.exists() and not args.force:
            raise SystemExit(f"{path} exists; frozen splits are never silently regenerated.")
        write_jsonl(path, episodes)
        hashes[f"frozen/{name}.jsonl"] = world.file_sha256(path)
    hashes["../../tasks.json"] = world.file_sha256(LEGACY_TASKS)
    print(json.dumps({k: len(v) for k, v in splits.items()}), json.dumps(hashes, indent=2))


def _api_key(path):
    if not path:
        return None
    return pathlib.Path(path).expanduser().read_text(encoding="utf-8").strip()


def make_backend(args):
    if args.backend == "openai":
        return agent.OpenAIBackend(args.base_url, args.model, _api_key(args.api_key_file),
                                   temperature=args.temperature, max_tokens=args.max_tokens,
                                   seed=args.seed)
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
    if not torch.cuda.is_available():
        raise SystemExit("A CUDA GPU is required for the local student; no CPU fallback.")
    set_seed(42)
    options = {"revision": args.revision, "trust_remote_code": False, "local_files_only": True}
    tok = AutoTokenizer.from_pretrained(args.model, **options)
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.float16,
                                                 use_safetensors=True, **options)
    if args.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, str(args.adapter), is_trainable=False)
    model.to("cuda").eval()
    return agent.HFBackend(model, tok, max_new_tokens=args.max_tokens)


def score_records(records, version=world.VERIFIER_VERSION):
    episodes = {}
    for name in ("train", "dev", "heldout"):
        if (FROZEN / f"{name}.jsonl").exists():
            episodes.update({e["id"]: e for e in load_split(name)})
    legacy = {"legacy-" + t["id"]: t for t in json.loads(LEGACY_TASKS.read_text(encoding="utf-8"))}
    scores = []
    for record in records:
        if record["episode"] in legacy:
            scores.append(agent.score_legacy(legacy[record["episode"]], record))
        else:
            scores.append(world.verify(episodes[record["episode"]], record, version))
    return scores


def summarize(scores, records):
    def rate(rows, key="pass"):
        return {"passed": sum(bool(r[key]) for r in rows), "total": len(rows),
                "rate": round(sum(bool(r[key]) for r in rows) / len(rows), 4) if rows else None}
    by_track = collections.defaultdict(list)
    by_family = collections.defaultdict(list)
    for s in scores:
        by_track[s["track"]].append(s)
        by_family[f"{s['track']}/{s['family']}"].append(s)
    heldout = by_track["paraphrase"] + by_track["composition"]
    violations = collections.Counter(v for s in scores for v in s["violations"])
    flags = collections.Counter(f for s in scores for f in s["flags"])
    seconds = [r.get("elapsed_seconds", 0) for r in records]
    return {
        "pass_by_track": {k: rate(v) for k, v in sorted(by_track.items())},
        "pass_heldout_pooled": rate(heldout),
        "tool_ok_heldout_pooled": rate(heldout, "tool_ok"),
        "answer_ok_heldout_pooled": rate(heldout, "answer_ok"),
        "pass_by_family": {k: rate(v) for k, v in sorted(by_family.items())},
        "violations": dict(violations), "answer_flags": dict(flags),
        "format_error_episodes": sum(not s["format_ok"] for s in scores),
        "transport_failures": sum(not s["transport"] for s in scores),
        "mean_episode_seconds": round(sum(seconds) / len(seconds), 3) if seconds else None,
        "mean_calls": round(sum(s["calls"] for s in scores) / len(scores), 3) if scores else None,
    }


def _episodes_for(sets):
    items = []
    for name in sets:
        if name == "legacy":
            items += [("legacy", t) for t in json.loads(LEGACY_TASKS.read_text(encoding="utf-8"))]
        else:
            items += [("world", e) for e in load_split(name)]
    return items


def cmd_eval(args):
    out = pathlib.Path(args.out)
    summary_path = out.with_suffix(".summary.json")
    if out.exists() or summary_path.exists():
        raise SystemExit("Refusing to overwrite an evaluation receipt.")
    os.umask(0o077)
    items = _episodes_for(args.sets.split(","))
    if args.limit:
        items = items[:args.limit]
    backend = make_backend(args)
    started = time.monotonic()
    records = []
    deadline = started + args.deadline_minutes * 60 if args.deadline_minutes else None
    for kind, item in items:
        if deadline and time.monotonic() > deadline:
            print("DEADLINE reached; the summary covers completed episodes only.", flush=True)
            break
        record = (agent.run_legacy_task(backend, item) if kind == "legacy"
                  else agent.run_world_episode(backend, item))
        record["label"] = args.label
        records.append(record)
        write_jsonl(out, [record], mode="a")
        print(record["episode"], "ok" if record["ok_transport"] else record.get("error"), flush=True)
    scores = score_records(records)
    report = {"schema": "haven-tool-sft-eval-1", "label": args.label, "backend": args.backend,
              "model": args.model, "revision": getattr(args, "revision", None),
              "adapter": bool(getattr(args, "adapter", None)), "sets": args.sets,
              "temperature": args.temperature, "max_tokens": args.max_tokens,
              "frozen_sha256": {p.name: world.file_sha256(p) for p in sorted(FROZEN.glob("*.jsonl"))},
              "wall_seconds": round(time.monotonic() - started, 1),
              "episodes_planned": len(items), "episodes_completed": len(records),
              "verifier_version": world.VERIFIER_VERSION,
              "summary": summarize(scores, records), "scores": scores}
    if args.backend == "hf":
        import torch
        report["peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
    summary_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


def cmd_collect(args):
    os.umask(0o077)
    out = pathlib.Path(args.out)
    done = {r["episode"] for r in read_jsonl(out)} if out.exists() else set()
    episodes = [e for e in load_split("train") if e["id"] not in done]
    backend = make_backend(args)
    deadline = time.monotonic() + args.deadline_minutes * 60
    counts = collections.Counter()
    for episode in episodes:
        if time.monotonic() > deadline:
            print("DEADLINE reached; collection is resumable.", flush=True)
            break
        record = agent.run_world_episode(backend, episode)
        verdict = world.verify(episode, record)
        record.update({"label": args.label, "verdict": verdict, "temperature": args.temperature})
        write_jsonl(out, [record], mode="a")
        counts["pass" if verdict["pass"] else "fail"] += 1
        print(episode["id"], "PASS" if verdict["pass"] else "FAIL", verdict["violations"],
              verdict["flags"], round(record.get("elapsed_seconds", 0), 1), flush=True)
    print(json.dumps(dict(counts)))


def sft_rows(record, source):
    """One row per assistant turn: the prefix is everything before that turn."""
    rows = []
    messages = record["messages"]
    for i, message in enumerate(messages):
        if message["role"] == "assistant":
            rows.append({"episode": record["episode"], "family": record["family"],
                         "source": source, "turn": i, "messages": messages[:i + 1]})
    return rows


def cmd_build(args):
    train = {e["id"]: e for e in load_split("train")}
    teacher, seen = [], set()
    for record in read_jsonl(args.teacher):
        episode = train.get(record["episode"])
        if episode is None:
            raise SystemExit(f"{record['episode']} is not a training episode; refusing to build.")
        verdict = world.verify(episode, record)  # re-verify; never trust stored verdicts
        if verdict["pass"] and record["episode"] not in seen:
            seen.add(record["episode"])
            teacher.append(record)
    oracle = [agent.run_world_episode(agent.OracleBackend(train[r["episode"]]), train[r["episode"]])
              for r in teacher]
    out = pathlib.Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    datasets = {"teacher_sft.jsonl": [row for r in teacher for row in sft_rows(r, "teacher")],
                "oracle_sft.jsonl": [row for r in oracle for row in sft_rows(r, "oracle")]}
    for name, rows in datasets.items():
        path = out / name
        if path.exists():
            raise SystemExit(f"{path} exists; refusing to overwrite.")
        write_jsonl(path, rows)
    manifest = {"schema": "haven-tool-sft-data-1", "verified_teacher_episodes": len(teacher),
                "teacher_records_read": len(read_jsonl(args.teacher)),
                "families": dict(collections.Counter(r["family"] for r in teacher)),
                "rows": {k: len(v) for k, v in datasets.items()},
                "sha256": {k: world.file_sha256(out / k) for k in datasets},
                "train_sha256": world.file_sha256(FROZEN / "train.jsonl"),
                "note": "Oracle control uses the identical episode instances the teacher solved."}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2))


def cmd_oracle_data(args):
    """Exploratory: scripted trajectories for every training episode (full coverage)."""
    out = pathlib.Path(args.output)
    if out.exists():
        raise SystemExit(f"{out} exists; refusing to overwrite.")
    episodes = load_split("train")
    write_jsonl(out, [row for e in episodes
                      for row in sft_rows(agent.run_world_episode(agent.OracleBackend(e), e), "oracle")])
    print(json.dumps({"episodes": len(episodes), "sha256": world.file_sha256(out)}))


def cmd_rescore(args):
    out = pathlib.Path(args.out)
    if out.exists():
        raise SystemExit("Refusing to overwrite a receipt.")
    previous = json.loads(pathlib.Path(args.records).with_suffix(".summary.json").read_text())
    records = read_jsonl(args.records)
    scores = score_records(records, args.verifier_version)
    report = {k: v for k, v in previous.items() if k not in ("summary", "scores")}
    report.update({"rescored_from": previous["frozen_sha256"],
                   "verifier_version": args.verifier_version,
                   "frozen_sha256": {p.name: world.file_sha256(p) for p in sorted(FROZEN.glob("*.jsonl"))},
                   "summary": summarize(scores, records), "scores": scores})
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


def cmd_compare(args):
    before = json.loads(pathlib.Path(args.before).read_text())
    after = json.loads(pathlib.Path(args.after).read_text())
    b = {s["episode"]: s for s in before["scores"]}
    a = {s["episode"]: s for s in after["scores"]}
    shared = sorted(set(a) & set(b))
    tracks = collections.defaultdict(lambda: collections.Counter())
    for key in shared:
        track = a[key]["track"]
        tracks[track][("both" if a[key]["pass"] and b[key]["pass"] else
                       "gained" if a[key]["pass"] else "lost" if b[key]["pass"] else "neither")] += 1
    print(json.dumps({"before": before["label"], "after": after["label"], "paired": len(shared),
                      "by_track": {k: dict(v) for k, v in sorted(tracks.items())}}, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("freeze")
    p.add_argument("--force", action="store_true")
    for name in ("eval", "collect"):
        p = sub.add_parser(name)
        p.add_argument("--backend", choices=("openai", "hf"), required=True)
        p.add_argument("--model", required=True)
        p.add_argument("--label", required=True)
        p.add_argument("--out", required=True)
        p.add_argument("--base-url")
        p.add_argument("--api-key-file", help="Read a loopback API key from a private file.")
        p.add_argument("--revision")
        p.add_argument("--adapter", type=pathlib.Path)
        p.add_argument("--temperature", type=float, default=0.0)
        p.add_argument("--max-tokens", type=int, default=256)
        p.add_argument("--seed", type=int)
        p.add_argument("--deadline-minutes", type=float, default=None if name == "eval" else 60)
        if name == "eval":
            p.add_argument("--sets", default="heldout,legacy")
            p.add_argument("--limit", type=int)
    p = sub.add_parser("build")
    p.add_argument("--teacher", required=True)
    p.add_argument("--output", required=True)
    p = sub.add_parser("oracle-data")
    p.add_argument("--output", required=True)
    p = sub.add_parser("rescore")
    p.add_argument("--records", required=True)
    p.add_argument("--verifier-version", type=int, choices=(1, 2, 3), default=world.VERIFIER_VERSION)
    p.add_argument("--out", required=True)
    p = sub.add_parser("compare")
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    args = parser.parse_args(argv)
    {"freeze": cmd_freeze, "eval": cmd_eval, "collect": cmd_collect, "build": cmd_build,
     "compare": cmd_compare, "rescore": cmd_rescore,
     "oracle-data": cmd_oracle_data}[args.command](args)


if __name__ == "__main__":
    main()
