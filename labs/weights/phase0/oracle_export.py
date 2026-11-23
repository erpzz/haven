#!/usr/bin/env python3
"""Arm O (oracle control): scripted correct trajectories from the generator's own solver.

  oracle_export.py hare  --episodes TRAIN.jsonl --out O.jsonl [--match KEPT.jsonl]
  oracle_export.py query --questions TRAIN_Q.jsonl --out OQ.jsonl [--match KEPT.jsonl]

HARE: each episode's scripted plan runs through the *full* harness (advisory checks, gateway,
verifier, correction), so the rows carry exactly the annotated messages the 4B sees in
production. An episode is exported only if the run passes gold with zero blocked calls and
the verifier accepts the first answer; anything else aborts, because a failing oracle means
the generator or the harness is wrong.

Query tasks: the reference Cypher in the cypher arm's reply format (TYPE line, cypher block),
after the system prompt and question that arm sends.

--match restricts the export to the episode ids in a kept-rows or kept-records file, so arm O
can be trained on exactly the episodes another arm solved (PR #45's matched control).
Training-pool episodes only: ids must start with "train-", and dedupe is re-run first.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import dedupe  # noqa: E402
import sft  # noqa: E402


def _match_ids(path):
    if not path:
        return None
    return {r.get("episode") or r.get("id") for r in common.read_jsonl(path)}


def _training_only(ids):
    bad = [i for i in ids if not str(i).startswith("train-")]
    if bad:
        raise SystemExit(f"{len(bad)} ids are not training-pool episodes (e.g. {bad[0]}); refusing.")


def export_hare(episodes, match=None) -> tuple[list[dict], dict]:
    episodes = [e for e in episodes if match is None or e["id"] in match]
    _training_only([e["id"] for e in episodes])
    rep = dedupe.check_items([dedupe.hare_item(e) for e in episodes], dedupe.load_fingerprint())
    if rep["rejected"]:
        raise SystemExit(f"dedupe rejected {len(rep['rejected'])} episodes; refusing to export.")
    rows, failures = [], []
    for e in episodes:
        rec = common.run_harness(common.Oracle(e), e, common.FULL)
        m = common.judge(rec, e)
        if not m["keep"] or m["outcome"] != "accepted_raw":
            failures.append((e["id"], m["violations"], m["outcome"]))
            continue
        rows += sft.rows_from_record(rec, source="oracle", arm="O", teacher="oracle")
    if failures:
        raise SystemExit(f"oracle failed on {len(failures)} episodes, e.g. {failures[0]}; the generator or "
                         f"harness is wrong. Nothing exported.")
    return rows, {"episodes": len(episodes), "rows": len(rows), "dedupe_fingerprint": rep["fingerprint_sha256"],
                  "per_family": dict(collections.Counter(e["family"] for e in episodes))}


def export_query(rows_in, match=None) -> tuple[list[dict], dict]:
    import gen_query
    rows_in = [r for r in rows_in if match is None or r["question"]["id"] in match]
    _training_only([r["question"]["id"] for r in rows_in])
    rep = dedupe.check_items([dedupe.query_item(r["question"], r["tenant"]) for r in rows_in],
                             dedupe.load_fingerprint())
    if rep["rejected"]:
        raise SystemExit(f"dedupe rejected {len(rep['rejected'])} questions; refusing to export.")
    check = gen_query.oracle_check(rows_in)
    if check["mismatches"]:
        raise SystemExit(f"reference Cypher disagrees with gold on {check['mismatches'][:3]}; nothing exported.")
    out = [sft.query_row(r["question"], gen_query.QRUN.CYPHER_SYSTEM, gen_query.oracle_reply(r["question"]),
                         source="oracle", arm="O", teacher="oracle") for r in rows_in]
    return out, {"questions": len(rows_in), "rows": len(out), "kuzu_check": check["executed"],
                 "dedupe_fingerprint": rep["fingerprint_sha256"]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="kind", required=True)
    h = sub.add_parser("hare")
    h.add_argument("--episodes", required=True)
    q = sub.add_parser("query")
    q.add_argument("--questions", required=True)
    for p in (h, q):
        p.add_argument("--out", required=True)
        p.add_argument("--match")
    args = ap.parse_args(argv)
    common.refuse_overwrite(args.out)
    match = _match_ids(args.match)
    if args.kind == "hare":
        rows, meta = export_hare(common.read_jsonl(args.episodes), match)
        src = args.episodes
    else:
        rows, meta = export_query(common.read_jsonl(args.questions), match)
        src = args.questions
    common.write_jsonl(args.out, rows)
    meta.update({"schema": "haven-weights-arm-o-1", "input_sha256": common.sha256_file(src),
                 "out_sha256": common.sha256_file(args.out), "matched": args.match is not None,
                 "code_sha256": common.code_hashes(["oracle_export.py", "sft.py", "common.py"])})
    pathlib.Path(args.out).with_suffix(".manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
