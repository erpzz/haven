#!/usr/bin/env python3
"""Kaggle 2xT4 launcher for the frozen Qwen3.6-35B W2 teacher lane.

This script is execution support only.  ``bind`` downloads the exact pinned GGUF,
measures the model/engine/2xT4 identity, writes immutable receipts and exits without
starting llama-server.  A later explicit ``run`` verifies that binding before starting
one literal-loopback server and delegates terminal-grid semantics to
``w2_local_teacher.py``.
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


def binding_paths(args):
    root = pathlib.Path(args.run_dir)
    identity = (pathlib.Path(args.bound_identity) if args.bound_identity
                else root / "bound-execution-identity.private.json")
    receipt = (pathlib.Path(args.bound_receipt) if args.bound_receipt
               else root / "bound-pre-run.public.json")
    return identity, receipt


def common_args(parser):
    parser.add_argument("--episodes", required=True)
    parser.add_argument("--membership", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--llama-server", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--bound-identity")
    parser.add_argument("--bound-receipt")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    bind = sub.add_parser("bind", help="download, bind and exit without inference")
    common_args(bind)
    run = sub.add_parser("run", help="verify the prior binding, start server and execute")
    common_args(run)
    run.add_argument("--port", type=int, default=8096)
    args = ap.parse_args(argv)
    engine = pathlib.Path(args.llama_server).resolve()
    if not engine.is_file():
        raise SystemExit("llama-server binary is missing")
    model = download_model(args.cache_dir)
    identity_path, receipt_path = binding_paths(args)
    if args.cmd == "bind":
        return w2.main(["bind", "--episodes", args.episodes, "--membership", args.membership,
                        "--runtime", args.runtime, "--model-file", str(model),
                        "--engine-binary", str(engine), "--bound-identity", str(identity_path),
                        "--bound-receipt", str(receipt_path)])

    # Fail closed against the immutable binding before llama-server is even started.
    runtime = w2.load_json(args.runtime)
    membership = w2.verify_runtime(runtime, args.membership, args.episodes)
    w2.verify_bound_artifacts(runtime, membership, model_file=model, engine_binary=engine,
                              identity_path=identity_path, receipt_path=receipt_path)
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
                      "--bound-identity", str(identity_path), "--bound-receipt", str(receipt_path),
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
