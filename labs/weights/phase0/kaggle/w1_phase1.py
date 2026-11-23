#!/usr/bin/env python3
"""W1 Phase 1 pilot: rejection sampling of the stock 4B inside the full harness. NOT RUN.

  w1_phase1.py --engine llama-server --model Qwen3.5-4B-Q4_K_M.gguf --episodes w1-pilot.episodes.jsonl \
      --episodes-sha256 HEX --out DIR [--gpus 0,1] [--attempts 8] [--temperature 0.7] [--deadline-minutes 600]

PLAN.md, W1 Stage A steps 1-4 and the Phase 1 gate:
  * every episode is attempted ATTEMPTS times at TEMPERATURE through enforce.run_episode_x with
    advisory checks, gateway, verifier and one correction (the run-1 "full" arm);
  * an attempt is kept only if the adjudicator passes it against gold with zero blocked or
    duplicate calls; at most 2 per episode, verifier-accepted first answers preferred;
  * episodes with no kept attempt are W2's hard episodes;
  * gate G1: the share of passing attempts must fall in [15%, 85%]. This script reports the
    number; the decision is recorded on #123.
Amendment 1, section 6: the summary publishes measured throughput (attempts and completion tokens
per wall-hour), peak VRAM per GPU, the accelerator count, wall-hours and device-hours, and
per-episode coverage; section 1: every attempt is scored in the model-clean, corrected-model and
final-system views. No training happens in Phase 1. Transcripts and kept rows stay in DIR
(private); only summary.json is meant to leave the session. Re-running with the same DIR resumes.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import json
import os
import pathlib
import subprocess
import sys
import threading
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import common  # noqa: E402
import dedupe  # noqa: E402
import gen_hare  # noqa: E402
import sft  # noqa: E402
from common import agent  # noqa: E402

SERVER_ARGS = ["-c", "33280", "-ngl", "99", "--jinja", "-np", "1", "-fa", "auto", "--fit", "off", "-cram", "0",
               "--no-webui", "--metrics"]       # identical to HARE-S0-1/2 (run 1)
G1 = (0.15, 0.85)
KEEP_PER_EPISODE = 2
TEACHER = "qwen35-4b-self"


def start_server(engine, model, gpu, port, log):
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu))
    proc = subprocess.Popen([engine, "-m", str(model), "--host", "127.0.0.1", "--port", str(port), *SERVER_ARGS],
                            stdout=open(log, "w"), stderr=subprocess.STDOUT, env=env)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(600):
        if proc.poll() is not None:
            raise SystemExit(f"llama-server exited; see {log}")
        try:
            with opener.open(f"http://127.0.0.1:{port}/health", timeout=5) as r:
                if r.status == 200:
                    return proc
        except Exception:
            time.sleep(3)
    raise SystemExit("llama-server did not become healthy in 30 minutes")


class VramSampler(threading.Thread):
    """Peak memory.used per GPU from nvidia-smi every `every` seconds (absent on CPU: records nothing)."""

    def __init__(self, every=20):
        super().__init__(daemon=True)
        self.every, self.peak, self.stop = every, {}, threading.Event()

    def run(self):
        while not self.stop.is_set():
            try:
                out = subprocess.run(["nvidia-smi", "--query-gpu=index,memory.used", "--format=csv,noheader,nounits"],
                                     capture_output=True, text=True, timeout=10).stdout
                for line in out.strip().splitlines():
                    i, mb = [x.strip() for x in line.split(",")]
                    self.peak[i] = max(self.peak.get(i, 0), int(mb))
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
            self.stop.wait(self.every)


def select_kept(rows):
    """At most KEEP_PER_EPISODE kept attempts, verifier-accepted first answers first."""
    ok = [r for r in rows if r["keep"]]
    ok.sort(key=lambda r: (r["outcome"] != "accepted_raw", r["attempt"]))
    return ok[:KEEP_PER_EPISODE]


def summarize(episodes, metrics, attempts):
    by_ep = collections.defaultdict(list)
    for m in metrics:
        by_ep[m["episode"]].append(m)
    n_att = len(metrics)
    passing = sum(m["keep"] for m in metrics)
    rate = passing / n_att if n_att else 0.0
    fam = collections.defaultdict(lambda: {"episodes": 0, "attempts": 0, "kept_attempts": 0, "solved": 0})
    for e in episodes:
        rows = by_ep.get(e["id"], [])
        f = fam[e["family"]]
        f["episodes"] += 1
        f["attempts"] += len(rows)
        f["kept_attempts"] += sum(r["keep"] for r in rows)
        f["solved"] += any(r["keep"] for r in rows)
    complete = [e for e in episodes if len(by_ep.get(e["id"], [])) == attempts]
    return {"episodes": len(episodes), "episodes_complete": len(complete), "attempts": n_att,
            "passing_attempts": passing, "passing_rate": round(rate, 4),
            "gate_G1": {"band": list(G1), "in_band": G1[0] <= rate <= G1[1] if n_att else None,
                        "decision": "recorded on #123, not here"},
            "solved_episodes": sum(any(r["keep"] for r in by_ep.get(e["id"], [])) for e in complete),
            "hard_episodes": sum(not any(r["keep"] for r in by_ep.get(e["id"], [])) for e in complete),
            "blocked_attempts": sum(m["blocked_any"] > 0 for m in metrics),
            "views_over_attempts": {v: sum(m["views"][v] for m in metrics)
                                    for v in ("model_clean", "corrected_model", "final_system")},
            "coverage_kept_attempts_per_episode": dict(sorted(collections.Counter(
                sum(r["keep"] for r in by_ep.get(e["id"], [])) for e in complete).items())),
            "outcomes": dict(collections.Counter(m["outcome"] for m in metrics)),
            "transport_failures": sum(not m["transport_ok"] for m in metrics),
            "mean_attempt_seconds": round(sum(m["seconds"] for m in metrics) / max(n_att, 1), 2),
            "by_family": dict(sorted(fam.items()))}


def telemetry(records, run_seconds, gpus, peak, new_attempts):
    """Amendment 1, section 6. Throughput counts this session's attempts only (resumed runs add up)."""
    tokens = sum((st.get("usage") or {}).get("completion_tokens", 0) for r in records for st in r.get("steps", []))
    hours = run_seconds / 3600
    return {"accelerators": len(gpus), "wall_hours_this_session": round(hours, 3),
            "device_hours_this_session": round(hours * len(gpus), 3),
            "attempts_this_session": new_attempts,
            "attempts_per_wall_hour": round(new_attempts / hours, 1) if hours > 0 else None,
            "completion_tokens_all_records": tokens,
            "peak_vram_mib_by_gpu": peak or None}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--model-sha256", default="00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4")
    ap.add_argument("--episodes", required=True)
    ap.add_argument("--episodes-sha256", required=True, help="from the generator manifest posted on #123")
    ap.add_argument("--out", required=True)
    ap.add_argument("--gpus", default="0")
    ap.add_argument("--attempts", type=int, default=8)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--deadline-minutes", type=float, default=600)
    ap.add_argument("--hardware", default="unspecified")
    args = ap.parse_args(argv)
    started = time.monotonic()
    if common.sha256_file(args.episodes) != args.episodes_sha256:
        raise SystemExit("episode file does not match the posted sha256; refusing to run")
    if common.sha256_file(args.model) != args.model_sha256:
        raise SystemExit("model file does not match its pinned sha256")
    episodes = common.read_jsonl(args.episodes)
    if any(not e["id"].startswith("train-") for e in episodes):
        raise SystemExit("only training-pool episodes may be sampled")
    rep = dedupe.check_items([dedupe.hare_item(e) for e in episodes], dedupe.load_fingerprint())
    if rep["rejected"]:
        raise SystemExit(f"dedupe rejected {len(rep['rejected'])} episodes; refusing to run")
    gold_bad = gen_hare.oracle_gate(episodes)
    if gold_bad:
        raise SystemExit(f"scripted oracle fails on {len(gold_bad)} episodes; the generator or harness is wrong")
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    os.umask(0o077)
    records_path, metrics_path = out / "attempts.jsonl", out / "metrics.jsonl"
    done = {(m["episode"], m["attempt"]) for m in common.read_jsonl(metrics_path)} if metrics_path.exists() else set()
    index = {e["id"]: e for e in episodes}
    gpus = [g for g in args.gpus.split(",") if g != ""]
    procs = [start_server(args.engine, args.model, g, 18950 + i, out / f"server-{i}.log") for i, g in enumerate(gpus)]
    vram = VramSampler()
    vram.start()
    run_started = time.monotonic()
    lock = threading.Lock()
    deadline = started + args.deadline_minutes * 60
    jobs = [(e["id"], k) for k in range(args.attempts) for e in episodes if (e["id"], k) not in done]

    def work(job, slot):
        eid, k = job
        if time.monotonic() > deadline:
            return None
        backend = agent.OpenAIBackend(f"http://127.0.0.1:{18950 + slot}/v1", "qwen35-4b", None,
                                      temperature=args.temperature, max_tokens=args.max_tokens, seed=k)
        rec = common.run_harness(backend, index[eid], common.FULL)
        m = common.judge(rec, index[eid])
        m.update({"attempt": k, "seed": k, "temperature": args.temperature})
        rec.update({"attempt": k})
        with lock:
            common.write_jsonl(records_path, [rec], mode="a")
            common.write_jsonl(metrics_path, [m], mode="a")
        return m

    try:
        with cf.ThreadPoolExecutor(max_workers=len(procs)) as pool:
            futures = [pool.submit(work, job, i % len(procs)) for i, job in enumerate(jobs)]
            for n, f in enumerate(cf.as_completed(futures), 1):
                m = f.result()
                if m and n % 25 == 0:
                    print(f"{n}/{len(jobs)} attempts, last {m['episode']}#{m['attempt']} keep={m['keep']}", flush=True)
    finally:
        vram.stop.set()
        for p in procs:
            p.terminate()
    run_seconds = time.monotonic() - run_started
    metrics = common.read_jsonl(metrics_path)
    records = {(r["episode"], r["attempt"]): r for r in common.read_jsonl(records_path)}
    by_ep = collections.defaultdict(list)
    for m in metrics:
        by_ep[m["episode"]].append(m)
    rows, hard = [], []
    for e in episodes:
        ms = by_ep.get(e["id"], [])
        kept = select_kept(ms)
        if len(ms) == args.attempts and not kept:
            hard.append(e["id"])
        for m in kept:
            rows += sft.rows_from_record(records[(e["id"], m["attempt"])], source="w1", arm="A", teacher=TEACHER)
    rows = sft.apply_episode_weights(rows)
    common.write_jsonl(out / "kept-rows.jsonl", rows)
    (out / "hard-episodes.txt").write_text("\n".join(hard) + ("\n" if hard else ""))
    summary = {"schema": "haven-weights-w1-phase1-1", "status": "EXECUTED" if all(len(by_ep.get(e["id"], [])) == args.attempts for e in episodes) else "PARTIAL",
               "hardware": args.hardware, "settings": {"attempts": args.attempts, "temperature": args.temperature,
                                                       "max_tokens": args.max_tokens, "mechanisms": common.FULL,
                                                       "server_args": SERVER_ARGS, "gpus": gpus},
               "episodes_sha256": args.episodes_sha256, "model_sha256": args.model_sha256,
               "dedupe_fingerprint": rep["fingerprint_sha256"],
               "code_sha256": {**common.code_hashes(["common.py", "sft.py", "dedupe.py", "gen_hare.py"]),
                               "kaggle/w1_phase1.py": common.sha256_file(__file__)},
               "summary": summarize(episodes, metrics, args.attempts), "kept_rows": len(rows),
               "kept_rows_sha256": common.sha256_file(out / "kept-rows.jsonl"),
               "hard_episodes_sha256": common.sha256_file(out / "hard-episodes.txt"),
               "wall_seconds": round(time.monotonic() - started, 1),
               "telemetry": telemetry(records.values(), run_seconds, gpus, vram.peak, new_attempts=len(jobs))}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["summary"], indent=2))


if __name__ == "__main__":
    main()
