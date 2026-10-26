#!/usr/bin/env python3
"""One bounded Strata teacher session: start, collect, measure the ceiling, stop.

Requires the prepared `haven-strata` user unit and an idle GPU. It never
installs, downloads or tunes anything, and it always stops only that unit.
All transcripts and receipts go to a private output directory.
"""
import argparse
import datetime
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
KEY = pathlib.Path.home() / ".local/state/haven-strata/api-key"
BASE = "http://127.0.0.1:8880/v1"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def models():
    request = urllib.request.Request(BASE + "/models",
                                     headers={"Authorization": "Bearer " + KEY.read_text().strip()})
    with OPENER.open(request, timeout=10) as response:
        return json.load(response)


def gpu_used_mib():
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True, check=True).stdout
    return int(out.split()[0])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--collect-minutes", type=float, default=80)
    ap.add_argument("--ceiling-minutes", type=float, default=35)
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    if not args.execute:
        print("DRY RUN: start haven-strata, collect training trajectories, run held-out ceiling, stop.")
        return 0
    os.umask(0o077)
    args.out.mkdir(parents=True, exist_ok=True, mode=0o700)
    receipt_path = args.out / "teacher-session.json"
    receipt = {"started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "phase": "CHECK"}

    def save(phase, **extra):
        receipt.update(phase=phase, **extra)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
        print("teacher session:", phase, flush=True)

    started = False
    try:
        if gpu_used_mib() > 512:
            raise RuntimeError("The GPU is in use; one owner at a time.")
        save("START_STRATA")
        t0 = time.monotonic()
        subprocess.run(["systemctl", "--user", "start", "haven-strata"], check=True, timeout=30)
        started = True
        deadline = time.monotonic() + 1500
        model = None
        while time.monotonic() < deadline:
            if subprocess.run(["systemctl", "--user", "is-active", "--quiet", "haven-strata"]).returncode:
                raise RuntimeError("haven-strata exited during startup; inspect its journal.")
            try:
                data = models().get("data") or []
                if data:
                    model = data[0]["id"]
                    break
            except urllib.error.HTTPError as error:
                if error.code in (401, 403):
                    raise RuntimeError("Strata rejected its private credential.") from None
            except (OSError, ValueError):
                pass
            time.sleep(10)
        if not model:
            raise TimeoutError("Strata was not ready within 25 minutes.")
        save("READY", ready_seconds=round(time.monotonic() - t0, 1), model=model)
        common = [sys.executable, str(HERE / "run.py")]
        endpoint = ["--backend", "openai", "--base-url", BASE, "--model", model,
                    "--api-key-file", str(KEY), "--temperature", "0"]
        t1 = time.monotonic()
        subprocess.run(common + ["collect", *endpoint, "--label", "teacher-strata",
                                 "--out", str(args.out / "teacher-train.jsonl"),
                                 "--deadline-minutes", str(args.collect_minutes)], check=True)
        save("COLLECTED", collect_seconds=round(time.monotonic() - t1, 1))
        t2 = time.monotonic()
        subprocess.run(common + ["eval", *endpoint, "--label", "ceiling-strata",
                                 "--sets", "heldout,legacy",
                                 "--out", str(args.out / "eval-teacher.jsonl"),
                                 "--deadline-minutes", str(args.ceiling_minutes)], check=True)
        save("CEILING_DONE", ceiling_seconds=round(time.monotonic() - t2, 1), status="COMPLETED")
    except Exception as error:
        receipt["status"] = "FAILED"
        receipt["error"] = f"{type(error).__name__}: {str(error)[:500]}"
    finally:
        if started:
            subprocess.run(["systemctl", "--user", "stop", "haven-strata"], timeout=60, check=False)
            receipt["strata_stopped"] = subprocess.run(
                ["systemctl", "--user", "is-active", "--quiet", "haven-strata"]).returncode != 0
        save("FINISHED")
    return 0 if receipt.get("status") == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
