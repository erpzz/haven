#!/usr/bin/env python3
"""E5 on Slink: hold the cooperative GPU lease, serve Qwen3.5-4B on CUDA, run the bench, always clean up.

  e5_slink.py smoke | run
"""
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

HOME = pathlib.Path.home()
B = HOME / ".local/share/haven-engineer-bench"
ENG = B / "src/labs/engineer"
RES = HOME / ".local/state/haven-engineer/research"
KEY = HOME / ".local/state/haven-engineer/llm-key"
EXE = HOME / ".local/share/haven-model-lab/engines/b11146/llama-b11146/llama-server"
MODEL = HOME / ".local/share/haven-model-lab/models/Qwen3.5-4B-Q4_K_M.gguf"
TASKS = "e5d-csvline-pytest,e5f-semver-node,e5a-invoice-pytest-src,e5e-toposort-pytest-class,e5h-ratelimit-pytest-src,e5g-layers-unittest"
sys.path.insert(0, str(HOME / "projects/haven/labs/model-lab"))
import gpu_lease  # noqa: E402


def ready():
    req = urllib.request.Request("http://127.0.0.1:8892/v1/models", headers={"Authorization": "Bearer " + KEY.read_text().strip()})
    try:
        return urllib.request.urlopen(req, timeout=3).status == 200
    except Exception:
        return False


def main(mode):
    lease = gpu_lease.acquire()
    print("lease acquired", flush=True)
    env = dict(os.environ, LD_LIBRARY_PATH=str(EXE.parent))
    log = open(RES / "llm-qwen35-4b-slink.log", "ab")
    server = subprocess.Popen([str(EXE), "--model", str(MODEL), "--host", "127.0.0.1", "--port", "8892",
                               "--api-key-file", str(KEY), "--alias", "qwen35-4b", "--n-gpu-layers", "999",
                               "--ctx-size", "32768", "--parallel", "1", "--jinja", "--flash-attn", "auto",
                               "--no-webui", "--metrics"], stdout=log, stderr=subprocess.STDOUT, env=env)
    bench = None
    try:
        for _ in range(180):
            if server.poll() is not None or ready():
                break
            time.sleep(1)
        if server.poll() is not None or not ready():
            raise SystemExit("model server did not come up")
        print("server ready", flush=True)
        if mode == "probe":
            import json
            for th in (True, False):
                body = {"model": "qwen35-4b", "max_tokens": 60, "messages": [{"role": "user", "content": "What is 17*23? Answer briefly."}],
                        "chat_template_kwargs": {"enable_thinking": th}}
                req = urllib.request.Request("http://127.0.0.1:8892/v1/chat/completions", data=json.dumps(body).encode(),
                                             headers={"Authorization": "Bearer " + KEY.read_text().strip(), "Content-Type": "application/json"})
                c = json.load(urllib.request.urlopen(req, timeout=120))["choices"][0]
                print("thinking", th, c["finish_reason"], repr(c["message"].get("content"))[:60], "reasoning:", repr(c["message"].get("reasoning_content"))[:60], flush=True)
            return
        common = ["--agents", "qwen35-4b-slink", "--temperature", "0.3", "--max-steps", "24"]
        if mode == "smoke":
            args = ["--arms", "controller_recover", "--tasks", "e2c-truncate-node", "--seeds", "1",
                    "--max-steps", "8", "--out", str(RES / "e5-slink-smoke.jsonl")]
        else:
            args = ["--arms", "none,recover,controller,controller_recover", "--tasks", TASKS,
                    "--seeds", "44,55,66", "--out", str(RES / "e5-slink.jsonl")]
        benv = dict(os.environ, PATH=f"{B}/bin:/usr/local/bin:/usr/bin:/bin")
        benv.pop("LD_LIBRARY_PATH", None)
        bench = subprocess.Popen([sys.executable, "bench/run_bench.py", *common, *args], cwd=ENG, env=benv)
        while bench.poll() is None:
            if server.poll() is not None:
                print(f"== model server exited ({server.returncode}); stopping bench", flush=True)
                bench.terminate()
                bench.wait(30)
                raise SystemExit(3)
            time.sleep(2)
        print(f"== bench exited {bench.returncode}", flush=True)
    finally:
        if bench and bench.poll() is None:
            bench.terminate()
        server.terminate()
        try:
            server.wait(30)
        except subprocess.TimeoutExpired:
            server.kill()
        lease.close()
        print("server stopped, lease released", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
