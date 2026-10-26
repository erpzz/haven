"""Aggregate private eval receipts into a sanitized, publishable result.

Only counts, rates, flags, timings and hashes are emitted: no prompts, answers,
transcripts, keys or host paths. Arms are compared only on identical episode IDs.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run  # noqa: E402


def load(path, version):
    report = json.loads(pathlib.Path(path).with_suffix(".summary.json").read_text())
    scores = run.score_records(run.read_jsonl(path), version)
    return report, {s["episode"]: s for s in scores}


def arm_summary(report, scores, ids):
    rows = [scores[i] for i in ids]
    def rate(sel):
        sel = list(sel)
        return {"passed": sum(s["pass"] for s in sel), "total": len(sel)}
    tracks = collections.defaultdict(list)
    families = collections.defaultdict(list)
    for s in rows:
        tracks[s["track"]].append(s)
        families[f"{s['track']}/{s['family']}"].append(s)
    heldout = tracks["paraphrase"] + tracks["composition"]
    return {
        "label": report["label"], "model": report["model"], "adapter": report.get("adapter"),
        "heldout_pooled": rate(heldout), "by_track": {k: rate(v) for k, v in sorted(tracks.items())},
        "by_family": {k: rate(v) for k, v in sorted(families.items())},
        "heldout_violations": dict(collections.Counter(v for s in heldout for v in s["violations"])),
        "heldout_answer_flags": dict(collections.Counter(f for s in heldout for f in s["flags"])),
        "format_error_episodes": sum(not s["format_ok"] for s in rows),
        "transport_failures": sum(not s["transport"] for s in rows),
        "mean_episode_seconds": report["summary"].get("mean_episode_seconds"),
        "peak_allocated_bytes": report.get("peak_allocated_bytes"),
    }


def paired(a, b, ids):
    out = collections.Counter()
    for i in ids:
        out[("both" if a[i]["pass"] and b[i]["pass"] else "gained" if b[i]["pass"]
             else "lost" if a[i]["pass"] else "neither")] += 1
    return dict(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arm", action="append", required=True, help="name=path/to/eval.jsonl")
    ap.add_argument("--baseline", required=True, help="arm name used for paired comparisons")
    ap.add_argument("--verifier-version", type=int, default=3)
    args = ap.parse_args(argv)
    arms = {}
    for item in args.arm:
        name, path = item.split("=", 1)
        arms[name] = load(path, args.verifier_version)
    heldout_ids = {e["id"] for e in run.load_split("heldout")}
    legacy_ids = {"legacy-" + t["id"] for t in json.loads(run.LEGACY_TASKS.read_text())}
    out = {"schema": "haven-tool-sft-result-1", "verifier_version": args.verifier_version,
           "frozen_sha256": arms[args.baseline][0]["frozen_sha256"], "arms": {}, "paired_vs_baseline": {}}
    base = arms[args.baseline][1]
    for name, (report, scores) in arms.items():
        ids = sorted(heldout_ids | legacy_ids | ({i for i in scores if i.startswith("dev-")}))
        missing = [i for i in heldout_ids | legacy_ids if i not in scores]
        if missing:
            raise SystemExit(f"{name}: {len(missing)} held-out/legacy IDs missing; no partial comparisons.")
        out["arms"][name] = arm_summary(report, scores, [i for i in ids if i in scores])
        if name != args.baseline:
            out["paired_vs_baseline"][name] = {
                "heldout": paired(base, scores, sorted(heldout_ids)),
                "legacy": paired(base, scores, sorted(legacy_ids))}
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
