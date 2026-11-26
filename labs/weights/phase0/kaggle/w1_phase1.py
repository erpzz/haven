#!/usr/bin/env python3
"""W1 Phase 1 pilot: rejection sampling of the stock 4B inside the full harness. NOT RUN.

  w1_phase1.py --engine llama-server --model Qwen3.5-4B-Q4_K_M.gguf --episodes w1-pilot.episodes.jsonl \
      --episodes-sha256 HEX --out DIR [--gpus 0,1] [--attempts 8] [--temperature 0.7] [--deadline-minutes 600]

PLAN.md, W1 Stage A steps 1-4 and the Phase 1 gate:
  * every episode is attempted ATTEMPTS times at TEMPERATURE through enforce.run_episode_x with
    advisory checks, gateway, verifier and one correction (the run-1 "full" arm);
  * an attempt is kept only if its first answer passes the adjudicator against gold (model-clean)
    with zero blocked or duplicate calls; at most 2 per episode, in attempt order (Amendment 2, D1);
  * episodes with no kept attempt are W2's hard episodes;
  * gate G1: the share of passing attempts must fall in [15%, 85%]. This script reports the
    number; the decision is recorded on #123.
Amendment 1, section 6: the summary publishes measured throughput (attempts and completion tokens
per inference wall-hour), peak VRAM per GPU, accelerator count, collector wall/device hours and
per-episode coverage; section 1: every attempt is scored in the model-clean, corrected-model and
final-system views. Allocation fields are explicitly scoped to the collector process; notebook
setup/model download are not silently counted. No training happens in Phase 1. Transcripts,
metrics and kept rows stay private and are hash-bound by the summary; if DIR is under a persisted
private-kernel output path, those files remain private audit artifacts and must not be published.
Re-running with the same DIR resumes.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import json
import os
import pathlib
import queue
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
    """At most KEEP_PER_EPISODE kept (model-clean) attempts, in attempt order. The verifier's verdict
    does not choose between passing attempts (Amendment 2, D1)."""
    return sorted((r for r in rows if r["keep"]), key=lambda r: r["attempt"])[:KEEP_PER_EPISODE]


def summarize(episodes, metrics, attempts, *, grid_complete=False):
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
            "gate_G1": {"band": list(G1), "rate": "model-clean kept attempts / all model-requested terminal rollouts",
                        "eligible": bool(grid_complete),
                        "in_band": (G1[0] <= rate <= G1[1]) if (grid_complete and n_att) else None,
                        "decision": "recorded on #123 only after exact-grid completion"},
            "solved_episodes": sum(any(r["keep"] for r in by_ep.get(e["id"], [])) for e in complete),
            "hard_episodes": sum(not any(r["keep"] for r in by_ep.get(e["id"], [])) for e in complete),
            "blocked_attempts": sum(m["blocked_any"] > 0 for m in metrics),
            "views_over_attempts": {v: sum(m["views"][v] for m in metrics)
                                    for v in ("model_clean", "corrected_model", "final_system")},
            "coverage_kept_attempts_per_episode": dict(sorted(collections.Counter(
                sum(r["keep"] for r in by_ep.get(e["id"], [])) for e in complete).items())),
            "outcomes": dict(collections.Counter(m["outcome"] for m in metrics)),
            "transport_failures": sum(not m["transport_ok"] for m in metrics),
            "timed_out_attempts": sum(m.get("slot_status") == "timed_out" for m in metrics),
            "mean_attempt_seconds": round(sum(m["seconds"] for m in metrics) / max(n_att, 1), 2),
            "by_family": dict(sorted(fam.items()))}


def _run_identity(args, gpus) -> dict:
    engine = pathlib.Path(args.engine)
    engine_path = str(engine.resolve())
    engine_sha = common.sha256_file(engine) if engine.is_file() else None
    return {
        "schema": "haven-weights-w1-phase1-run-identity-1",
        "episodes_sha256": args.episodes_sha256,
        "model_sha256": args.model_sha256,
        "engine": {"path": engine_path, "sha256": engine_sha},
        "settings": {"attempts": args.attempts, "temperature": args.temperature, "max_tokens": args.max_tokens,
                     "deadline_minutes": args.deadline_minutes, "server_args": SERVER_ARGS, "gpus": gpus,
                     "mechanisms": common.FULL},
        "code_sha256": {**common.code_hashes(["common.py", "sft.py", "dedupe.py", "gen_hare.py"]),
                        "kaggle/w1_phase1.py": common.sha256_file(__file__)},
    }


def _freeze_identity(path, identity) -> str:
    run_id = common.sha256_bytes(common.canonical(identity))
    doc = {"run_id": run_id, **identity}
    if path.exists():
        if json.loads(path.read_text()) != doc:
            raise SystemExit("resume identity mismatch: episodes/model/engine/settings/harness/code changed")
    else:
        path.write_text(json.dumps(doc, sort_keys=True, indent=2) + "\n")
    return run_id


def _indexed_receipts(path, *, assigned, run_id, kind):
    rows = common.read_jsonl(path) if path.exists() else []
    out = {}
    for row in rows:
        if not isinstance(row, dict):
            raise SystemExit(f"{kind} receipt is not an object")
        key = (row.get("episode"), row.get("attempt"))
        if key not in assigned:
            raise SystemExit(f"{kind} contains foreign/unassigned slot {key}")
        if key in out:
            raise SystemExit(f"{kind} contains duplicate slot {key}")
        if row.get("run_id") != run_id:
            raise SystemExit(f"{kind} run identity mismatch at {key}")
        out[key] = row
    return out


def _validate_receipts(records_path, metrics_path, assigned, run_id):
    records = _indexed_receipts(records_path, assigned=assigned, run_id=run_id, kind="transcript")
    metrics = _indexed_receipts(metrics_path, assigned=assigned, run_id=run_id, kind="metric")
    if set(records) != set(metrics):
        only_r = sorted(set(records) - set(metrics))
        only_m = sorted(set(metrics) - set(records))
        raise SystemExit(f"resume receipt mismatch: transcript_only={only_r[:3]} metric_only={only_m[:3]}")
    for key in records:
        got = common.sha256_bytes(common.canonical(records[key]))
        if metrics[key].get("record_sha256") != got:
            raise SystemExit(f"metric/transcript hash mismatch at {key}")
    return records, metrics


def _run_server_lanes(jobs, slots, worker, on_complete=None):
    """Run a shared job queue with exactly one worker bound to each server slot.

    Unlike preassigning a slot to every future in a shared ThreadPoolExecutor, this
    guarantees at most one in-flight request per -np 1 llama-server while allowing
    whichever server becomes free first to take the next job.
    """
    slots = list(slots)
    if not slots:
        raise ValueError("at least one server slot is required")
    pending = queue.Queue()
    for job in jobs:
        pending.put(job)
    failed = threading.Event()

    def lane(slot):
        while not failed.is_set():
            try:
                job = pending.get_nowait()
            except queue.Empty:
                return
            try:
                result = worker(job, slot)
                if on_complete is not None:
                    on_complete(result)
            except BaseException:
                failed.set()
                raise
            finally:
                pending.task_done()

    with cf.ThreadPoolExecutor(max_workers=len(slots)) as pool:
        futures = [pool.submit(lane, slot) for slot in slots]
        for future in cf.as_completed(futures):
            future.result()


def telemetry(*, all_records, new_records, allocation_seconds, inference_seconds, gpus, peak,
              counters, prior_sessions):
    """Separate allocation cost from inference throughput and preserve resumed-session accounting."""
    alloc_hours = allocation_seconds / 3600
    infer_hours = inference_seconds / 3600
    tokens_new = sum((st.get("usage") or {}).get("completion_tokens", 0)
                     for r in new_records for st in r.get("steps", []))
    session = {
        "queued": counters["queued"],
        "started": counters["started"],
        "model_requested": counters["model_requested"],
        "terminal": counters["terminal"],
        "skipped_before_start": counters["skipped_before_start"],
        "timed_out": counters["timed_out"],
        "allocation_wall_hours": round(alloc_hours, 6),
        "device_hours": round(alloc_hours * len(gpus), 6),
        "inference_wall_hours": round(infer_hours, 6),
        "terminal_attempts_per_inference_hour": round(counters["terminal"] / infer_hours, 2) if infer_hours > 0 else None,
        "completion_tokens": tokens_new,
        "peak_vram_mib_by_gpu": peak or None,
    }
    sessions = list(prior_sessions)
    if any(session[k] for k in ("queued", "started", "model_requested", "terminal", "skipped_before_start")):
        sessions.append(session)
    return {
        "accelerators": len(gpus),
        "measurement_scope": {
            "allocation_wall_hours": "collector process only; notebook setup/model download are excluded",
            "device_hours": "collector process wall time multiplied by accelerator count",
            "peak_vram_mib_by_gpu": "sampled from before llama-server startup through inference",
        },
        "sessions": sessions,
        "allocation_wall_hours_total": round(sum(x.get("allocation_wall_hours", 0) for x in sessions), 6),
        "device_hours_total": round(sum(x.get("device_hours", 0) for x in sessions), 6),
        "model_requested_total": sum(x.get("model_requested", 0) for x in sessions),
        "terminal_total": sum(x.get("terminal", 0) for x in sessions),
        "skipped_before_start_total": sum(x.get("skipped_before_start", 0) for x in sessions),
        "timed_out_total": sum(x.get("timed_out", 0) for x in sessions),
        "completion_tokens_all_records": sum((st.get("usage") or {}).get("completion_tokens", 0)
                                             for r in all_records for st in r.get("steps", [])),
    }


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
    if len({e["id"] for e in episodes}) != len(episodes):
        raise SystemExit("episode file contains duplicate ids")
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
    summary_path, identity_path = out / "summary.json", out / "run_identity.json"
    gpus = [g for g in args.gpus.split(",") if g != ""]
    if not gpus:
        raise SystemExit("at least one accelerator slot is required")
    assigned_order = [(e["id"], k) for k in range(args.attempts) for e in episodes]
    assigned = set(assigned_order)
    identity = _run_identity(args, gpus)
    if not identity_path.exists() and (records_path.exists() or metrics_path.exists() or summary_path.exists()):
        raise SystemExit("resume artifacts exist without a frozen run_identity.json")
    run_id = _freeze_identity(identity_path, identity)
    record_map, metric_map = _validate_receipts(records_path, metrics_path, assigned, run_id)
    done = set(metric_map)
    jobs = [slot for slot in assigned_order if slot not in done]
    previous = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    prior_sessions = (previous.get("telemetry") or {}).get("sessions") or []
    index = {e["id"]: e for e in episodes}
    counters = collections.Counter(queued=len(jobs))
    lock = threading.Lock()
    deadline = started + args.deadline_minutes * 60
    new_records = []
    procs, vram = [], None
    inference_seconds = 0.0

    def work(job, slot):
        eid, k = job
        with lock:
            counters["started"] += 1
        if time.monotonic() > deadline:
            with lock:
                counters["skipped_before_start"] += 1
            return None
        with lock:
            counters["model_requested"] += 1
        backend = agent.OpenAIBackend(f"http://127.0.0.1:{18950 + slot}/v1", "qwen35-4b", None,
                                      temperature=args.temperature, max_tokens=args.max_tokens, seed=k)
        rec = common.run_harness(backend, index[eid], common.FULL)
        m = common.judge(rec, index[eid], apply_w1_training_guard=True)
        rec.update({"attempt": k, "run_id": run_id})
        error = str(rec.get("error") or "")
        slot_status = "timed_out" if (not rec.get("ok_transport") and "timeout" in error.casefold()) else "terminal"
        m.update({"attempt": k, "seed": k, "temperature": args.temperature, "run_id": run_id,
                  "slot_status": slot_status, "record_sha256": common.sha256_bytes(common.canonical(rec))})
        with lock:
            common.write_jsonl(records_path, [rec], mode="a")
            common.write_jsonl(metrics_path, [m], mode="a")
            new_records.append(rec)
            counters["terminal"] += 1
            counters["timed_out"] += slot_status == "timed_out"
        return m

    if jobs:
        vram = VramSampler()
        vram.start()  # include server/model-load VRAM, not only steady-state inference
        infer_started = None
        try:
            for i, g in enumerate(gpus):
                procs.append(start_server(
                    args.engine, args.model, g, 18950 + i, out / f"server-{i}.log"
                ))
            infer_started = time.monotonic()
            progress = collections.Counter()

            def report_progress(m):
                with lock:
                    progress["completed"] += 1
                    n = progress["completed"]
                    terminal = counters["terminal"]
                    skipped = counters["skipped_before_start"]
                if m and n % 25 == 0:
                    print(f"{n}/{len(jobs)} queued completions; terminal={terminal} "
                          f"skipped={skipped} last={m['episode']}#{m['attempt']} "
                          f"keep={m['keep']}", flush=True)

            _run_server_lanes(
                jobs, range(len(procs)), work, on_complete=report_progress
            )
        finally:
            if infer_started is not None:
                inference_seconds = time.monotonic() - infer_started
            vram.stop.set()
            vram.join(timeout=5)
            for p in procs:
                p.terminate()

    record_map, metric_map = _validate_receipts(records_path, metrics_path, assigned, run_id)
    grid_complete = set(metric_map) == assigned
    metrics = [metric_map[k] for k in assigned_order if k in metric_map]
    records = record_map
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
    allocation_seconds = time.monotonic() - started
    tel = telemetry(all_records=records.values(), new_records=new_records, allocation_seconds=allocation_seconds,
                    inference_seconds=inference_seconds, gpus=gpus, peak=(vram.peak if vram else {}),
                    counters=counters, prior_sessions=prior_sessions)
    summary = {
        "schema": "haven-weights-w1-phase1-3",
        "status": "EXECUTED" if grid_complete else "PARTIAL",
        "run_id": run_id,
        "hardware": args.hardware,
        "settings": identity["settings"],
        "episodes_sha256": args.episodes_sha256,
        "model_sha256": args.model_sha256,
        "dedupe_fingerprint": rep["fingerprint_sha256"],
        "code_sha256": identity["code_sha256"],
        "receipt_grid": {"assigned": len(assigned), "terminal_pairs": len(metric_map),
                         "complete": grid_complete, "pending": len(assigned - set(metric_map))},
        "summary": summarize(episodes, metrics, args.attempts, grid_complete=grid_complete),
        "kept_rows": len(rows),
        "kept_rows_sha256": common.sha256_file(out / "kept-rows.jsonl"),
        "hard_episodes_sha256": common.sha256_file(out / "hard-episodes.txt"),
        "private_receipt_commitments": {
            "run_identity_sha256": common.sha256_file(identity_path),
            "attempts_sha256": common.sha256_file(records_path) if records_path.is_file() else None,
            "metrics_sha256": common.sha256_file(metrics_path) if metrics_path.is_file() else None,
        },
        "wall_seconds_this_invocation": round(allocation_seconds, 1),
        "telemetry": tel,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"receipt_grid": summary["receipt_grid"], "summary": summary["summary"],
                      "telemetry": summary["telemetry"]}, indent=2))


if __name__ == "__main__":
    main()
