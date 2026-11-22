#!/usr/bin/env python3
"""Rebuild hare_s0_kaggle.ipynb with the current system0 files embedded (hash-checked).

  python3 kaggle/build_notebook.py      # run from system0/
"""
import base64
import hashlib
import io
import json
import pathlib
import tarfile

HERE = pathlib.Path(__file__).resolve().parents[1]
FILES = ["checks.py", "bench_s0.py", "run_arms.py", "PREREGISTRATION_S0.json", "fresh-s0-20261121.jsonl",
         "enforce.py", "bench_x.py", "run_extension.py", "PREREGISTRATION_S0X.json", "fresh-x-untouched.jsonl",
         "d1_probe.py", "README.md", "README_EXTENSION.md", "tests/test_checks.py", "tests/test_enforce.py"]
HAVEN_COMMIT = "53387e74a0ad90786ac3ea16753c8ad99142e9df"
LIQUID = {"llama_tag": "b12620",
          "d1": {"repo": "LiquidAI/d1-2B-GGUF", "revision": "4a181094d1b6addfaa3a0956f78e7ab2aa406a0c",
                 "file": "d1-2B-Q4_K_M.gguf", "sha256": "adca5789ad30ae6027e8e936749bb9f19673097492ab26fa1c5b69643ca50b4b"}}


def md(s):
    return {"cell_type": "markdown", "metadata": {}, "source": s}


def code(s):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s}


def build():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for f in FILES:
            tar.add(HERE / f, arcname="system0/" + f)
    raw = buf.getvalue()
    blob, blob_sha = base64.b64encode(raw).decode(), hashlib.sha256(raw).hexdigest()
    cells = [
        md("""# HARE on Kaggle: System 0, enforcement and verification for Qwen3.5-4B

**Before running:** Settings → Accelerator **GPU T4 x2**, Internet **On** (phone-verified account).
Then **Save Version → Save & Run All (Commit)** and close the tab. Results are written after every episode and every arm, so an interrupted run keeps what finished.

Phases, in order:
1. **registered** (HARE-S0-1, unchanged): 4B plain vs 4B + advisory System 0 on the frozen 180 and the fresh 179.
2. **extension** (HARE-S0-2, registered separately): 4B plain / advisory / enforce / verify / full on 179 untouched episodes. With `RUN_35B`, also the 35B plain and full arms on the same T4s, for the non-inferiority test and the offline cascade.
3. **liquid** (optional probe): builds llama.cpp b12620 and runs Liquid d1-2B against the deterministic rules (accuracy, calibration, latency).

Synthetic data only. No credentials, no paid services. GPU time is roughly 2 h for phase 1, 2.5 h for phase 2 with the 4B only, plus about 1.5 h for the 35B and 30 min for the Liquid probe. Keep the notebook private, because the `*.jsonl` files hold full synthetic transcripts."""),
        code(f"""PHASES = ["registered", "extension"]   # add "liquid" for the d1-2B probe
RUN_35B = False        # True: 35B plain + full on the same T4s (22 GB download)
SKIP_FRESH = False     # registered phase: frozen set only
HAVEN_COMMIT = "{HAVEN_COMMIT}"
WORK = "/kaggle/working/hare"
MODELS = "/tmp/hare-models"
LIQUID = {json.dumps(LIQUID)}
"""),
        code("""import subprocess, os, sys, shutil, json, hashlib, base64, io, tarfile, pathlib, time
def sh(cmd, check=True):
    print("$", cmd, flush=True)
    r = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    print((r.stdout or "")[-3000:], (r.stderr or "")[-3000:], flush=True)
    if check and r.returncode: raise SystemExit(f"failed: {cmd}")
    return r.stdout
def stream(cmd):
    print("$", cmd, flush=True)
    p = subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout: print(line, end="", flush=True)
    assert p.wait() == 0, f"failed: {cmd}"
sh("nvidia-smi --query-gpu=name,memory.total --format=csv"); sh("nvcc --version | tail -2")
sh("nproc; free -g | head -2; df -h /tmp /kaggle/working | tail -2")
os.makedirs(WORK, exist_ok=True); os.makedirs(MODELS, exist_ok=True)
"""),
        code(f"""if not os.path.isdir("/tmp/haven/.git"):
    sh("git clone -q --filter=blob:none https://github.com/erpzz/haven /tmp/haven")
sh(f"git -C /tmp/haven checkout -q {{HAVEN_COMMIT}} && git -C /tmp/haven log -1 --format='%h %s'")
BLOB = "{blob}"
raw = base64.b64decode(BLOB)
assert hashlib.sha256(raw).hexdigest() == "{blob_sha}", "embedded harness corrupted"
dest = pathlib.Path("/tmp/haven/labs/intelligence-bakeoff")
shutil.rmtree(dest / "system0", ignore_errors=True)
tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz").extractall(dest)
S0 = dest / "system0"
sh(f"cd {{dest}} && python3 -m unittest discover -s system0/tests 2>&1 | tail -3")
sh(f"cd {{dest}} && python3 system0/bench_s0.py check")
"""),
        code("""def build_llama(tag, prefix):
    engine = f"{prefix}/build/bin/llama-server"
    if not os.path.exists(engine):
        sh(f"git clone -q --depth 1 --branch {tag} https://github.com/ggml-org/llama.cpp {prefix}")
        t0 = time.time()
        sh(f"cd {prefix} && cmake -S . -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75 -DLLAMA_CURL=OFF "
           "-DLLAMA_USE_PREBUILT_UI=OFF -DLLAMA_BUILD_UI=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF "
           "> /tmp/cmake.log 2>&1 || (tail -40 /tmp/cmake.log; false)")
        sh(f"cd {prefix} && cmake --build build --target llama-server -j4 > /tmp/build.log 2>&1 || (tail -60 /tmp/build.log; false)")
        print(f"{tag} build minutes: {(time.time()-t0)/60:.1f}")
    sh(f"{engine} --version 2>&1 | tail -2")
    return engine
ENGINE = build_llama("b11146", "/tmp/llama.cpp")   # pinned engine for every Qwen arm
"""),
        code("""reg = json.loads((S0 / "PREREGISTRATION_S0.json").read_text())
def fetch(spec):
    path = f"{MODELS}/{spec['file']}"
    if not os.path.exists(path):
        url = f"https://huggingface.co/{spec['repo']}/resolve/{spec['revision']}/{spec['file']}"
        sh(f"curl -sSL --retry 5 -o {path}.part '{url}' && mv {path}.part {path}")
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    assert h.hexdigest() == spec["sha256"], f"sha256 mismatch for {spec['file']}"
    return path
M4 = fetch(reg["settings"]["4b"])
M35 = None
if RUN_35B:
    free_gb = shutil.disk_usage(MODELS).free / 1e9
    M35 = fetch(reg["settings"]["35b"]) if free_gb >= 26 else print(f"Only {free_gb:.0f} GB free: skipping the 35B")
gpus = sh("nvidia-smi --query-gpu=name --format=csv,noheader").strip().splitlines()
HW = f"Kaggle {len(gpus)}x {gpus[0]}; 4B on GPU0; 35B layer-split across all GPUs (Slink used --cpu-moe)"
"""),
        code("""if "registered" in PHASES:
    stream(f"cd {S0} && python3 run_arms.py --engine {ENGINE} --model-4b {M4} --out {WORK}/registered --hardware '{HW}'"
           + (f" --model-35b {M35}" if M35 else "") + (" --skip-fresh" if SKIP_FRESH else ""))
    print(json.dumps(json.loads(pathlib.Path(WORK, "registered", "results.json").read_text())["verdict"], indent=2))
"""),
        code("""if "extension" in PHASES:
    stream(f"cd {S0} && python3 run_extension.py --engine {ENGINE} --model-4b {M4} --out {WORK}/extension --hardware '{HW}'"
           + (f" --model-35b {M35}" if M35 else ""))
"""),
        code("""if "liquid" in PHASES:
    LENGINE = build_llama(LIQUID["llama_tag"], "/tmp/llama-new")
    D1 = fetch(LIQUID["d1"])
    srv = subprocess.Popen(f"CUDA_VISIBLE_DEVICES=0 {LENGINE} -m {D1} --host 127.0.0.1 --port 18940 -c 8192 -b 8192 -ub 8192 -ngl 99 --no-webui",
                           shell=True, stdout=open(f"{WORK}/d1-server.log", "w"), stderr=subprocess.STDOUT)
    for _ in range(200):
        time.sleep(3)
        if subprocess.run("curl -s http://127.0.0.1:18940/health | grep -q ok", shell=True).returncode == 0: break
    try:
        stream(f"cd {dest} && python3 system0/d1_probe.py --url http://127.0.0.1:18940 "
               f"--episodes frozen,system0/fresh-s0-20261121.jsonl --out {WORK}/d1-probe-t4.json")
    finally:
        srv.terminate()
"""),
        code("""# Sanitized bundle to send back: summaries and results, no transcripts
sh(f"cd {WORK} && find . -name '*.summary.json' -o -name 'results*.json' -o -name 'd1-probe-*.json' | tar czf /kaggle/working/hare-results.tgz -T -")
print("Download /kaggle/working/hare-results.tgz from the Output tab and send it back.")
"""),
    ]
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                       "language_info": {"name": "python"},
                                       "kaggle": {"accelerator": "nvidiaTeslaT4", "isInternetEnabled": True, "isGpuEnabled": True}},
          "nbformat": 4, "nbformat_minor": 4}
    out = HERE / "kaggle" / "hare_s0_kaggle.ipynb"
    out.write_text(json.dumps(nb, indent=1))
    print(out, len(raw), blob_sha)


if __name__ == "__main__":
    build()
