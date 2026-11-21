#!/usr/bin/env python3
"""Run HARE-S0-1 end to end on one host: start llama-server, run every arm, compare, stop.

  run_arms.py --engine /path/llama-server --model-4b /path/Qwen3.5-4B-Q4_K_M.gguf --out DIR
              [--model-35b /path/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf] [--hardware "Kaggle 2x T4"]

Arms in order: 4b-plain, 4b-s0 (frozen 180), then 4b-plain, 4b-s0 (fresh 179), then the
optional 35B pair on the frozen set. A finished arm is skipped on rerun, so an interrupted
session resumes. Receipts in DIR: *.jsonl (full transcripts, keep private) and
*.summary.json plus results.json (sanitized, safe to commit).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bench_s0  # noqa: E402

PORT = 18931
FRESH = HERE / "fresh-s0-20261121.jsonl"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def start_server(engine, model, log, extra_env=None, extra_args=()):
    args = [engine, "-m", str(model), "--host", "127.0.0.1", "--port", str(PORT), "-c", "33280",
            "-ngl", "99", "--jinja", "-np", "1", "-fa", "auto", "--fit", "off", "-cram", "0",
            "--no-webui", "--metrics", *extra_args]
    env = dict(os.environ, **(extra_env or {}))
    proc = subprocess.Popen(args, stdout=open(log, "w"), stderr=subprocess.STDOUT, env=env)
    t0 = time.monotonic()
    while time.monotonic() - t0 < 1800:
        if proc.poll() is not None:
            raise SystemExit(f"llama-server exited; see {log}")
        try:
            with OPENER.open(f"http://127.0.0.1:{PORT}/health", timeout=5) as r:
                if json.load(r).get("status") == "ok":
                    return proc, round(time.monotonic() - t0, 1)
        except Exception:
            pass
        time.sleep(3)
    proc.kill()
    raise SystemExit("llama-server did not become healthy in 30 minutes")


def run_arm(arm, label, out_dir, episodes, model_name, hardware, gguf_sha, limit=0):
    out = out_dir / f"{label}.jsonl"
    summary = out.with_suffix(".summary.json")
    if summary.exists():
        print(f"== {label}: already done, skipping", flush=True)
        return json.loads(summary.read_text())
    if out.exists():
        out.unlink()  # an interrupted arm restarts cleanly
    argv = ["eval", "--arm", arm, "--base-url", f"http://127.0.0.1:{PORT}/v1", "--model", model_name,
            "--label", label, "--out", str(out), "--hardware", hardware, "--gguf-sha256", gguf_sha]
    if episodes:
        argv += ["--episodes", str(episodes)]
    if limit:
        argv += ["--limit", str(limit)]
    print(f"== {label}", flush=True)
    bench_s0.main(argv)
    return json.loads(summary.read_text())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--engine", required=True)
    p.add_argument("--model-4b", required=True)
    p.add_argument("--model-35b", default=None)
    p.add_argument("--out", required=True)
    p.add_argument("--hardware", default="unknown")
    p.add_argument("--gpu-4b", default="0", help="CUDA_VISIBLE_DEVICES for the 4B")
    p.add_argument("--skip-fresh", action="store_true")
    p.add_argument("--limit", type=int, default=0, help="smoke test only: first N episodes per arm")
    args = p.parse_args()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    reg = json.loads((HERE / "PREREGISTRATION_S0.json").read_text())
    bench_s0.main(["check"])  # hashes, frozen suite, oracle 180/180 under s0
    results = {"prereg": reg["id"], "hardware": args.hardware, "arms": {}, "comparisons": {}}

    sha4 = sha256(args.model_4b)
    if sha4 != reg["settings"]["4b"]["sha256"]:
        raise SystemExit(f"4B GGUF sha256 mismatch: {sha4}")
    proc, load_s = start_server(args.engine, args.model_4b, out / "server-4b.log",
                                {"CUDA_VISIBLE_DEVICES": args.gpu_4b})
    results["load_seconds_4b"] = load_s
    try:
        arms = [("plain", "4b-plain-frozen", None), ("s0", "4b-s0-frozen", None)]
        if not args.skip_fresh:
            arms += [("plain", "4b-plain-fresh", FRESH), ("s0", "4b-s0-fresh", FRESH)]
        for arm, label, eps in arms:
            results["arms"][label] = run_arm(arm, label, out, eps, "qwen35-4b", args.hardware, sha4, args.limit)["summary"]["pass"]
    finally:
        proc.terminate(); proc.wait(60)

    ref35 = 121
    if args.model_35b:
        sha35 = sha256(args.model_35b)
        if sha35 != reg["settings"]["35b"]["sha256"]:
            raise SystemExit(f"35B GGUF sha256 mismatch: {sha35}")
        proc, load_s = start_server(args.engine, args.model_35b, out / "server-35b.log")
        results["load_seconds_35b"] = load_s
        try:
            for arm, label in (("plain", "35b-plain-frozen"), ("s0", "35b-s0-frozen")):
                results["arms"][label] = run_arm(arm, label, out, None, "qwen36-35b-a3b", args.hardware, sha35, args.limit)["summary"]["pass"]
        finally:
            proc.terminate(); proc.wait(60)
        ref35 = results["arms"]["35b-plain-frozen"]

    def load(label):
        return json.loads((out / f"{label}.summary.json").read_text())

    cmp = bench_s0.compare(load("4b-plain-frozen"), load("4b-s0-frozen"), ref35)
    results["comparisons"]["frozen"] = cmp
    if not args.skip_fresh:
        results["comparisons"]["fresh"] = bench_s0.compare(load("4b-plain-fresh"), load("4b-s0-fresh"))
    harm = {f: v for f, v in cmp["by_family"].items() if v["a"] - v["b"] >= 3}
    s0_secs = cmp["mean_episode_seconds"]["b"]
    big_secs = load("35b-plain-frozen")["mean_episode_seconds"] if args.model_35b else None
    results["verdict"] = {
        "H1_primary": cmp["gained"] > cmp["lost"] and cmp["sign_test_p"] < 0.05,
        "H2_accuracy": cmp["b_pass"] >= ref35 - 10, "H2_reference_35b": ref35,
        "H2_latency": (s0_secs < big_secs) if big_secs else "unmeasured (35B not run on this host)",
        "replication_direction": (results["comparisons"]["fresh"]["gained"] > results["comparisons"]["fresh"]["lost"])
        if not args.skip_fresh else "not run",
        "harm_guard_ok": not harm, "harm_families": harm,
        "calibration_4b_plain_vs_round2_58": cmp["a_pass"] - 58,
    }
    (out / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results["verdict"], indent=2))


if __name__ == "__main__":
    main()
