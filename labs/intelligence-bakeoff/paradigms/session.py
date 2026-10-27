#!/usr/bin/env python3
"""One bounded cross-paradigm GPU session on the Linux host.

  1. wait until the Model Lab has no RUNNING job, disconnect it from Strata,
     stop the prepared Strata unit and take the cooperative GPU lease;
  2. for each preregistered model: start its own llama-server on a loopback port
     with a private API key, record load time and buffer sizes, run the
     performance and long-context probes, run the frozen tool benchmark, stop;
  3. always restore: release the lease, start Strata, and reconnect the Lab
     (`labctl.py strata`) once Strata reports a model, even after a failure.

Every record stays in the private output directory. Nothing is installed.

  session.py --out DIR --models-dir DIR [--prereg FILE] [--only id,..] [--budget-minutes 180] --execute

A preregistration with an "independent" benchmark also runs the adjudicated
suite (adjudicated/bench.py eval) on the same server after the tool benchmark.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import re
import secrets
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
TOOL_SFT = HERE.parent / "distillation" / "tool_sft"
ADJUDICATED = HERE.parent / "adjudicated"
PREREG = HERE / "PREREGISTRATION.json"
HOME = pathlib.Path.home()
REPO = HOME / "projects/haven"
ENGINE = HOME / ".local/share/haven-model-lab/engines/b11146/llama-b11146/llama-server"
LAB_MODELS = HOME / ".local/share/haven-model-lab/models"
LABCTL = REPO / "ops/haven-core/labctl.py"
LAUNCH_FILE = HOME / ".local/state/haven-model-lab/launch-url"
STRATA_KEY = HOME / ".local/state/haven-strata/api-key"
STRATA_BASE = "http://127.0.0.1:8880/v1"
PORT = 18931
RESERVED_PORTS = {8877, 8878, 8880}
LONG_CTX, SHORT_CTX = 33280, 8192
PROBE_DEPTHS = (1024, 2048, 8192, 32768)
PROBE_PREDICT = 128
FILLER = ("The household ledger lists lamps, heaters, thermostats and garden valves. "
          "Each device reports its state, battery level and last maintenance date. ")
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def http_json(url, data=None, key=None, timeout=30, headers=None):
    hdrs = dict(headers or {})
    if key:
        hdrs["Authorization"] = "Bearer " + key
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        hdrs["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=hdrs)
    with OPENER.open(request, timeout=timeout) as response:
        return json.load(response)


# ------------------------------------------------------------- server command
def server_args(model, model_path, ctx, port, key_file, log_file, threads=10):
    """The preregistered llama-server command; loopback only, never a Lab port."""
    if port in RESERVED_PORTS or not 1024 < port < 65536:
        raise ValueError("refusing a reserved or privileged port")
    args = [str(ENGINE), "-m", str(model_path), "--host", "127.0.0.1", "--port", str(port),
            "--api-key-file", str(key_file), "--log-file", str(log_file),
            "-c", str(ctx), "-ngl", "99", "--jinja", "-np", "1", "-fa", "auto", "--fit", "off",
            "-t", str(threads), "-cram", "0", "--no-webui", "--metrics", "-lv", "4"]
    if model.get("offload") == "cpu-moe":
        args.append("--cpu-moe")
    return args


_BUFFER = re.compile(r"(llama_kv_cache|llama_memory_recurrent|load_tensors|llama_context|sched_reserve|"
                     r"graph_reserve)\S*:\s+(\S+)\s+(?:KV|RS|model|compute|output)?\s*buffer size\s*=\s*([\d.]+) MiB")
_KV_TOTAL = re.compile(r"(llama_kv_cache|llama_memory_recurrent)\S*: size =\s+([\d.]+) MiB")


def parse_buffers(log_text):
    """Sum llama.cpp's reported buffer sizes per (component, device)."""
    out = {}
    for kind, device, mib in _BUFFER.findall(log_text):
        key = f"{kind}:{device}"
        out[key] = round(out.get(key, 0.0) + float(mib), 2)
    for kind, mib in _KV_TOTAL.findall(log_text):
        key = f"{kind}:total"
        out[key] = round(out.get(key, 0.0) + float(mib), 2)
    return out


# ----------------------------------------------------------------- telemetry
def gpu_used_by_pid():
    out = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory",
                          "--format=csv,noheader,nounits"], capture_output=True, text=True,
                         timeout=10, check=True).stdout
    used = {}
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            used[int(parts[0])] = int(parts[1])
    return used


def gpu_total_used_mib():
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True, timeout=10, check=True).stdout
    return int(out.split()[0])


def proc_status_kib(pid, field):
    try:
        for line in pathlib.Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith(field + ":"):
                return int(line.split()[1])
    except OSError:
        return None
    return None


class Sampler(threading.Thread):
    """Peak GPU MiB of one process, plus its peak resident RAM (VmHWM)."""

    def __init__(self, pid, every=1.0):
        super().__init__(daemon=True)
        self.pid, self.every = pid, every
        self.peak_gpu_mib = 0
        self.peak_rss_kib = 0
        self.stop_event = threading.Event()

    def sample(self):
        try:
            self.peak_gpu_mib = max(self.peak_gpu_mib, gpu_used_by_pid().get(self.pid, 0))
        except (subprocess.SubprocessError, OSError, ValueError):
            pass
        self.peak_rss_kib = max(self.peak_rss_kib, proc_status_kib(self.pid, "VmHWM") or 0)

    def run(self):
        while not self.stop_event.wait(self.every):
            self.sample()

    def snapshot(self):
        self.sample()
        return {"peak_gpu_mib": self.peak_gpu_mib, "peak_rss_mib": round(self.peak_rss_kib / 1024)}


# ---------------------------------------------------------------- the server
class Server:
    def __init__(self, model, model_path, ctx, out_dir, key_file, key):
        self.model, self.ctx, self.key = model, ctx, key
        self.log_file = out_dir / f"server-ctx{ctx}.log"
        self.base = f"http://127.0.0.1:{PORT}"
        self.argv = server_args(model, model_path, ctx, PORT, key_file, self.log_file)
        self.proc = None
        self.sampler = None

    def start(self, timeout):
        t0 = time.monotonic()
        self.proc = subprocess.Popen(self.argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     start_new_session=True)
        self.sampler = Sampler(self.proc.pid)
        self.sampler.start()
        while time.monotonic() - t0 < timeout:
            if self.proc.poll() is not None:
                return {"ready": False, "exit_code": self.proc.returncode,
                        "seconds": round(time.monotonic() - t0, 1)}
            try:
                if http_json(self.base + "/health", timeout=5).get("status") == "ok":
                    return {"ready": True, "seconds": round(time.monotonic() - t0, 1)}
            except (urllib.error.URLError, OSError, ValueError):
                pass
            time.sleep(1)
        return {"ready": False, "timeout": True, "seconds": round(time.monotonic() - t0, 1)}

    def log_text(self):
        try:
            return self.log_file.read_text(errors="replace")
        except OSError:
            return ""

    def stop(self):
        if self.sampler:
            self.sampler.stop_event.set()
        if self.proc and self.proc.poll() is None:
            os.killpg(self.proc.pid, signal.SIGTERM)
            try:
                self.proc.wait(30)
            except subprocess.TimeoutExpired:
                os.killpg(self.proc.pid, signal.SIGKILL)
                self.proc.wait(10)

    def completion(self, tokens, n_predict):
        body = {"prompt": tokens, "n_predict": n_predict, "temperature": 0, "cache_prompt": False,
                "ignore_eos": True, "stream": False}
        return http_json(self.base + "/completion", body, key=self.key, timeout=900)

    def tokenize(self, text):
        return http_json(self.base + "/tokenize", {"content": text}, key=self.key)["tokens"]


def probe_tokens(base_tokens, n):
    """An exact-length synthetic prompt made by tiling a tokenized filler."""
    if not base_tokens:
        raise ValueError("empty filler tokenization")
    reps = n // len(base_tokens) + 1
    return (base_tokens * reps)[:n]


def run_probes(server, ctx):
    base = server.tokenize(FILLER * 8)
    rows = []
    for depth in PROBE_DEPTHS:
        if depth + PROBE_PREDICT > ctx:
            rows.append({"prompt_tokens": depth, "status": "DOES_NOT_FIT_CTX", "ctx": ctx})
            continue
        try:
            t0 = time.monotonic()
            result = server.completion(probe_tokens(base, depth), PROBE_PREDICT)
            timings = result.get("timings") or {}
            rows.append({"prompt_tokens": depth, "status": "OK",
                         "prompt_n": timings.get("prompt_n"),
                         "prompt_tok_s": round(timings.get("prompt_per_second") or 0, 2),
                         "predicted_n": timings.get("predicted_n"),
                         "decode_tok_s": round(timings.get("predicted_per_second") or 0, 2),
                         "wall_seconds": round(time.monotonic() - t0, 2),
                         "after": server.sampler.snapshot()})
        except Exception as error:  # a failed probe is a recorded outcome
            rows.append({"prompt_tokens": depth, "status": "FAILED",
                         "error": f"{type(error).__name__}: {str(error)[:200]}"})
    return rows


def run_eval(model, out_dir, key_file, deadline_minutes):
    cmd = [sys.executable, str(TOOL_SFT / "run.py"), "eval", "--backend", "openai",
           "--base-url", f"http://127.0.0.1:{PORT}/v1", "--model", model["id"],
           "--api-key-file", str(key_file), "--label", "paradigm-" + model["id"],
           "--sets", "heldout,legacy", "--max-tokens", "1024", "--temperature", "0",
           "--deadline-minutes", str(round(deadline_minutes, 1)), "--out", str(out_dir / "eval.jsonl")]
    t0 = time.monotonic()
    with open(out_dir / "eval.stdout", "w") as log:
        code = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=False).returncode
    return {"exit_code": code, "seconds": round(time.monotonic() - t0, 1)}


def run_adjudicated(model, out_dir, key_file, deadline_minutes):
    cmd = [sys.executable, str(ADJUDICATED / "bench.py"), "eval", "--backend", "openai",
           "--base-url", f"http://127.0.0.1:{PORT}/v1", "--model", model["id"],
           "--api-key-file", str(key_file), "--label", "paradigm-adj-" + model["id"],
           "--max-tokens", "1024", "--temperature", "0",
           "--deadline-minutes", str(round(deadline_minutes, 1)), "--out", str(out_dir / "adjudicated.jsonl")]
    t0 = time.monotonic()
    with open(out_dir / "adjudicated.stdout", "w") as log:
        code = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=False).returncode
    return {"exit_code": code, "seconds": round(time.monotonic() - t0, 1)}


def model_path(model, models_dir):
    if model.get("source", "").startswith("already on host"):
        return LAB_MODELS / model["file"]
    return pathlib.Path(models_dir) / model["file"]


def run_model(model, models_dir, out_root, key_file, key, eval_minutes, adjudicated=False):
    out_dir = out_root / model["id"]
    out_dir.mkdir(mode=0o700, exist_ok=True)
    receipt = {"id": model["id"], "started_utc": now(), "attempts": []}
    path = model_path(model, models_dir)
    if not path.exists():
        receipt["status"] = "MODEL_FILE_MISSING"
        return receipt
    # A file not yet in the page cache is a cold load over the slow root disk.
    receipt["file_bytes"] = path.stat().st_size
    for ctx in (LONG_CTX, SHORT_CTX):
        server = Server(model, path, ctx, out_dir, key_file, key)
        try:
            start = server.start(timeout=1500)
            attempt = {"ctx": ctx, **start, "buffers_mib": parse_buffers(server.log_text())}
            receipt["attempts"].append(attempt)
            if not start["ready"]:
                continue
            attempt["at_ready"] = server.sampler.snapshot()
            attempt["probes"] = run_probes(server, ctx)
            attempt["eval"] = run_eval(model, out_dir, key_file, eval_minutes)
            if adjudicated:
                attempt["adjudicated_eval"] = run_adjudicated(model, out_dir, key_file, eval_minutes)
            attempt["final"] = server.sampler.snapshot()
            receipt["status"] = "COMPLETED"
            receipt["ctx"] = ctx
            return receipt
        finally:
            server.stop()
            receipt["completed_utc"] = now()
    receipt["status"] = "DID_NOT_LOAD"
    return receipt


# --------------------------------------------------------- Lab and Strata
class Lab:
    """Minimal client for the local Model Lab; the bearer token never leaves this process."""

    def __init__(self, launch_file=LAUNCH_FILE):
        parsed = urllib.parse.urlsplit(pathlib.Path(launch_file).read_text().strip())
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1":
            raise ValueError("The launch file does not name a literal loopback service.")
        self.token = urllib.parse.parse_qs(parsed.fragment).get("token", [""])[0]
        if not self.token:
            raise ValueError("The launch file has no session token.")
        self.origin = f"http://127.0.0.1:{parsed.port}"

    def call(self, path, data=None):
        return http_json(self.origin + path, data, headers={"X-Lab-Token": self.token}, timeout=15)

    def state(self):
        return self.call("/api/state")

    def disconnect(self):
        return self.call("/api/disconnect", {})


def lab_busy(state):
    """Return a reason the Lab must not be interrupted, or None."""
    for job in state.get("jobs") or []:
        if job.get("state") == "RUNNING":
            return f"{job.get('kind', 'job')} RUNNING"
    if (state.get("prepared_runtime") or {}).get("switch_job"):
        return "runtime switch active"
    engine = state.get("engine") or {}
    if engine.get("state") not in (None, "STOPPED"):
        # An idle owned CPU engine holds no GPU memory; it is left running untouched.
        if not (engine.get("state") == "READY" and engine.get("compute") == "cpu"):
            return "Lab-owned engine " + str(engine.get("state"))
    return None


def systemctl(*args, timeout=60):
    return subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True,
                          timeout=timeout, check=False)


def strata_active():
    return systemctl("is-active", "--quiet", "haven-strata").returncode == 0


def restore(receipt, reconnect_lab=True, wait_seconds=2700):
    """Start Strata and, if this session disconnected it, reconnect the Lab. Never raises."""
    r = receipt.setdefault("restore", {"started_utc": now()})
    try:
        if not strata_active():
            r["start_rc"] = systemctl("start", "haven-strata", timeout=60).returncode
        t0 = time.monotonic()
        while time.monotonic() - t0 < wait_seconds:
            if not strata_active():
                r["error"] = "haven-strata exited during startup"
                break
            try:
                key = STRATA_KEY.read_text().strip()
                if http_json(STRATA_BASE + "/models", key=key, timeout=10).get("data"):
                    r["strata_ready_seconds"] = round(time.monotonic() - t0, 1)
                    break
            except (urllib.error.URLError, OSError, ValueError):
                pass
            time.sleep(10)
        if "strata_ready_seconds" in r and not reconnect_lab:
            r["lab_connection"] = "LEFT_AS_FOUND"
        elif "strata_ready_seconds" in r:
            done = subprocess.run([sys.executable, str(LABCTL), "strata"], capture_output=True,
                                  text=True, timeout=60, check=False)
            r["labctl_strata_rc"] = done.returncode
            try:
                conn = Lab().state().get("connection") or {}
                r["lab_connection"] = {"kind": conn.get("kind"), "base": conn.get("base")}
            except Exception as error:
                r["lab_state_error"] = type(error).__name__
    except Exception as error:
        r["error"] = f"{type(error).__name__}: {str(error)[:300]}"
    r["completed_utc"] = now()
    if reconnect_lab:
        r["restored"] = bool(r.get("labctl_strata_rc") == 0 and (r.get("lab_connection") or {}).get("kind") == "strata")
    else:
        r["restored"] = "strata_ready_seconds" in r
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--models-dir", type=pathlib.Path, required=True)
    ap.add_argument("--prereg", type=pathlib.Path, default=PREREG)
    ap.add_argument("--only", help="comma-separated model ids, in run order")
    ap.add_argument("--budget-minutes", type=float, default=180)
    ap.add_argument("--eval-minutes", type=float, default=35)
    ap.add_argument("--stretch-min-minutes", type=float, default=45)
    ap.add_argument("--lab-wait-minutes", type=float, default=60)
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args(argv)
    prereg = json.loads(args.prereg.read_text())
    models = {m["id"]: m for m in prereg["models"]}
    adjudicated = bool((prereg.get("benchmarks") or {}).get("independent"))
    order = args.only.split(",") if args.only else list(models)
    unknown = [i for i in order if i not in models]
    if unknown:
        ap.error(f"unknown model ids: {unknown}")
    if not args.execute:
        for i in order:
            print("PLAN", i, " ".join(server_args(models[i], model_path(models[i], args.models_dir),
                                                  LONG_CTX, PORT, "KEYFILE", "LOG")))
        return 0

    os.umask(0o077)
    args.out.mkdir(parents=True, exist_ok=True, mode=0o700)
    receipt_path = args.out / "session.json"
    receipt = {"schema": "haven-paradigm-session-1", "started_utc": now(), "models": [],
               "prereg": args.prereg.name}
    began = time.monotonic()

    def save():
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")

    def on_term(signum, frame):
        raise SystemExit(f"signal {signum}")
    signal.signal(signal.SIGTERM, on_term)

    sys.path.insert(0, str(REPO / "labs/model-lab"))
    import gpu_lease  # the Lab's own cooperative lease

    lease = None
    stopped_strata = False
    try:
        lab = Lab()
        deadline = time.monotonic() + args.lab_wait_minutes * 60
        while (reason := lab_busy(lab.state())) is not None:
            if time.monotonic() > deadline:
                raise RuntimeError("Lab stayed busy: " + reason)
            receipt["waited_for_lab"] = reason
            save()
            time.sleep(15)
        found = lab.state()
        receipt["lab_at_start"] = {"connection": (found.get("connection") or {}).get("kind"),
                                   "connection_compute": (found.get("connection") or {}).get("compute"),
                                   "engine": (found.get("engine") or {}).get("state")}
        if (found.get("connection") or {}).get("kind") == "strata":
            lab.disconnect()
            receipt["lab_disconnected_utc"] = now()
        if strata_active():
            systemctl("stop", "haven-strata")
            stopped_strata = True
        if strata_active():
            raise RuntimeError("haven-strata did not stop")
        receipt["strata_stopped_utc"] = now()
        for _ in range(30):
            if gpu_total_used_mib() < 512:
                break
            time.sleep(2)
        lease = gpu_lease.acquire()
        receipt["gpu_session_started_utc"] = now()
        gpu_t0 = time.monotonic()
        key = secrets.token_urlsafe(32)
        key_file = args.out / "server-key"
        key_file.write_text(key + "\n")
        save()
        for model_id in order:
            used = (time.monotonic() - began) / 60
            left = args.budget_minutes - used - 20  # keep 20 minutes for the Strata restore
            stretch = "stretch" in models[model_id].get("role", "")
            # A stretch model runs two evals when the independent suite is registered.
            need = args.stretch_min_minutes * (2 if adjudicated else 1) if stretch else 10
            if left < need:
                receipt["models"].append({"id": model_id, "status": "SKIPPED_BUDGET",
                                          "minutes_left": round(left, 1)})
                save()
                continue
            try:
                result = run_model(models[model_id], args.models_dir, args.out, key_file, key,
                                   min(args.eval_minutes, max(left - 8, 5)), adjudicated)
            except Exception as error:
                result = {"id": model_id, "status": "FAILED", "error": f"{type(error).__name__}: {str(error)[:300]}"}
            receipt["models"].append(result)
            save()
        receipt["gpu_minutes"] = round((time.monotonic() - gpu_t0) / 60, 1)
        receipt["status"] = "COMPLETED"
    except BaseException as error:
        receipt["status"] = "FAILED"
        receipt["error"] = f"{type(error).__name__}: {str(error)[:300]}"
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)  # the restore must not be interrupted
        if lease is not None:
            lease.close()
        receipt["lease_released_utc"] = now()
        save()
        if stopped_strata or receipt.get("lab_disconnected_utc") or not strata_active():
            restore(receipt, reconnect_lab=bool(receipt.get("lab_disconnected_utc")))
        receipt["total_minutes"] = round((time.monotonic() - began) / 60, 1)
        save()
    return 0 if receipt["status"] == "COMPLETED" and receipt.get("restore", {}).get("restored") else 1


if __name__ == "__main__":
    sys.exit(main())
