#!/usr/bin/env python3
"""Kaggle 2xT4 launcher for the frozen Qwen3.6-35B W2 teacher lane.

This script is execution support only.  It downloads the exact pinned GGUF revision,
starts one literal-loopback llama.cpp b11146 server with the preregistered settings,
and delegates terminal-grid semantics to w2_local_teacher.py.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
PHASE0 = HERE.parent
sys.path.insert(0, str(PHASE0))

import w2_local_teacher as w2  # noqa: E402


def healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def download_model(cache_dir):
    from huggingface_hub import hf_hub_download
    return pathlib.Path(hf_hub_download(repo_id=w2.MODEL_REPO, filename=w2.MODEL_FILE,
                                        revision=w2.MODEL_REVISION, cache_dir=cache_dir))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--episodes", required=True)
    ap.add_argument("--membership", required=True)
    ap.add_argument("--runtime", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--llama-server", required=True)
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--port", type=int, default=8096)
    args = ap.parse_args(argv)
    engine = pathlib.Path(args.llama_server).resolve()
    if not engine.is_file():
        raise SystemExit("llama-server binary is missing")
    model = download_model(args.cache_dir)
    # Hash binding happens inside `run` before the first chat-completion request.
    cmd = [str(engine), "-m", str(model), "--host", "127.0.0.1", "--port", str(args.port),
           "--alias", w2.TEACHER, "-ngl", "999", "-np", "8", "-c", "65536",
           "--jinja", "--flash-attn", "on"]
    log = pathlib.Path(args.run_dir) / "llama-server.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost")
    with log.open("ab") as output:
        proc = subprocess.Popen(cmd, stdout=output, stderr=subprocess.STDOUT, env=env)
    try:
        for _ in range(600):
            if healthy(args.port):
                break
            if proc.poll() is not None:
                raise SystemExit(f"llama-server exited {proc.returncode}")
            time.sleep(2)
        else:
            raise SystemExit("llama-server did not become healthy")
        rc = w2.main(["run", "--episodes", args.episodes, "--membership", args.membership,
                      "--runtime", args.runtime, "--run-dir", args.run_dir,
                      "--model-file", str(model), "--engine-binary", str(engine),
                      "--base-url", f"http://127.0.0.1:{args.port}/v1"])
        print(json.dumps({"runner_returncode": rc, "server_command": cmd}, indent=2))
        return rc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
