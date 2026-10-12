"""Frozen, synthetic skill-vs-knowledge probes for local chat-completions models.

Run unchanged against baseline and candidate. Compare per-group pass rates;
no invented benchmark claims. Never promote only from one synthetic suite.
"""
from __future__ import annotations
import argparse
import json
import os
import pathlib
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_PROBES = HERE / "fixtures" / "evaluation_probes.json"


def normalize(value):
    return re.sub(r"[\s.!?]+$", "", str(value).strip()).casefold()


def load_probes(path=DEFAULT_PROBES):
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("No probes.")
    ids = set()
    for row in data:
        if (not all(isinstance(row.get(k), str) and row[k]
                    for k in ("id", "group", "prompt", "expected"))
                or row["id"] in ids):
            raise ValueError("Duplicate or incomplete probe.")
        ids.add(row["id"])
    return data


def score(probe, answer, ok_transport=True):
    return bool(ok_transport) and normalize(answer) == normalize(probe["expected"])


def summarize(probes, results):
    gold = {p["id"]: p for p in probes}
    seen, groups = set(), defaultdict(lambda: {"total": 0, "passed": 0, "transport_failures": 0})
    for result in results:
        key = result.get("id")
        if key not in gold or key in seen:
            raise ValueError("Unknown or duplicate evaluation ID.")
        seen.add(key)
        group = groups[gold[key]["group"]]
        group["total"] += 1
        passed = score(gold[key], result.get("answer", ""),
                       result.get("ok_transport") is True)
        group["passed"] += int(passed)
        group["transport_failures"] += int(result.get("ok_transport") is not True)
    if seen != set(gold):
        raise ValueError("Missing probes; partial benchmarks are not comparable.")
    return {name: dict(values, pass_rate=values["passed"] / values["total"])
            for name, values in sorted(groups.items())}


def run(base_url, model, probes, api_key=None):
    target = urllib.parse.urlparse(base_url)
    if target.scheme != "http" or target.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Only loopback HTTP inference is supported.")
    endpoint = base_url.rstrip("/") + "/chat/completions"
    results = []
    for probe in probes:
        started = time.monotonic()
        payload = {"model": model, "temperature": 0, "max_tokens": 80, "stream": False,
                   "messages": [
                       {"role": "system",
                        "content": "You are taking a synthetic diagnostic. Reply with exactly "
                                   "the requested token, nothing else. If a catalog code was "
                                   "not provided or learned, reply UNKNOWN; never guess."},
                       {"role": "user", "content": probe["prompt"]},
                   ]}
        req = urllib.request.Request(
            endpoint, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     **({"Authorization": "Bearer " + api_key} if api_key else {})},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
            answer = data["choices"][0]["message"].get("content") or ""
            result = {"id": probe["id"], "answer": answer,
                      "ok_transport": True, "elapsed_seconds": round(time.monotonic()-started, 3)}
        except Exception as exc:
            result = {"id": probe["id"], "answer": "", "ok_transport": False,
                      "error": f"{type(exc).__name__}: {exc}"}
        results.append(result)
        print(probe["id"], "PASS" if score(probe, result["answer"], result["ok_transport"]) else "FAIL")
    return results


def write_results(path, results):
    dest = pathlib.Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def read_results(path):
    return [json.loads(line) for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    p_run = sub.add_parser("run")
    p_run.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    p_run.add_argument("--model", required=True)
    p_run.add_argument("--output", type=pathlib.Path, required=True)
    p_run.add_argument("--api-key-env", default="HAVEN_BAKEOFF_API_KEY")
    p_compare = sub.add_parser("compare")
    p_compare.add_argument("--before", required=True)
    p_compare.add_argument("--after", required=True)
    ap.add_argument("--probes", type=pathlib.Path, default=DEFAULT_PROBES)
    args = ap.parse_args(argv)
    probes = load_probes(args.probes)
    if args.command == "run":
        results = run(args.base_url, args.model, probes, os.environ.get(args.api_key_env))
        write_results(args.output, results)
        print(json.dumps(summarize(probes, results), indent=2))
    else:
        before, after = (summarize(probes, read_results(p))
                         for p in (args.before, args.after))
        report = {
            group: {"before": before[group]["pass_rate"],
                    "after": after[group]["pass_rate"],
                    "delta": round(after[group]["pass_rate"] - before[group]["pass_rate"], 5),
                    "sample_size": before[group]["total"]}
            for group in before}
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
