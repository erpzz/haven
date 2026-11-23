#!/usr/bin/env python3
"""Build w1_phase1_kaggle.ipynb: the W1 Phase 1 pilot notebook. Building is not running.

  python3 kaggle/build_w1_phase1.py        # from labs/weights/phase0/, after fetch_deps.py

The notebook embeds this directory's Phase 0 code and the hash-pinned _deps/ files as one
tarball, checked by sha256 in the notebook before use. Main-branch files come from a clone at
the pinned main commit. The training episodes are NOT embedded: they hold gold, so they are
generated privately (gen_hare.py) and attached as a private Kaggle dataset; the notebook
refuses a file whose sha256 differs from the one posted on #123.
"""
import base64
import gzip
import hashlib
import io
import json
import pathlib
import tarfile

HERE = pathlib.Path(__file__).resolve().parents[1]
CODE = ["common.py", "dedupe.py", "gen_hare.py", "sft.py", "pools.py", "flip_pairs.py", "deps.json", "fetch_deps.py",
        "kaggle/w1_phase1.py", "tests/test_phase0.py", "oracle_export.py", "astra_batch.py", "gen_query.py",
        "rule8/evidence_flip_pairs.jsonl", "pools/dev_manifest.jsonl", "regression/config.json",
        "regression/mmlu_pro_subset.json"]
MAIN_COMMIT = json.loads((HERE / "deps.json").read_text())["main"]["commit"]
MODEL_4B = {"repo": "unsloth/Qwen3.5-4B-GGUF", "revision": "e87f176479d0855a907a41277aca2f8ee7a09523",
            "file": "Qwen3.5-4B-Q4_K_M.gguf", "sha256": "00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4"}
OUT = HERE / "kaggle" / "w1_phase1_kaggle.ipynb"


def md(s):
    return {"cell_type": "markdown", "metadata": {}, "source": s}


def code(s):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s}


def bundle() -> bytes:
    buf = io.BytesIO()
    spec = json.loads((HERE / "deps.json").read_text())
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz, tarfile.open(fileobj=gz, mode="w") as tar:
        def add(path, arc):
            info = tar.gettarinfo(str(path), arcname=arc)
            info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""
            with open(path, "rb") as f:
                tar.addfile(info, f)
        for f in CODE:
            add(HERE / f, "phase0/" + f)
        for src in spec["sources"]:
            for path in src["files"]:
                add(HERE / "_deps" / path, "phase0/_deps/" + path)
    return buf.getvalue()


def build():
    raw = bundle()
    blob, blob_sha = base64.b64encode(raw).decode(), hashlib.sha256(raw).hexdigest()
    llama_cell = (HERE / "kaggle" / "llama_build_cell.py").read_text()
    cells = [
        md("""# Haven W1 Phase 1: the stock Qwen3.5-4B as its own student (rejection sampling, no training)

**Do not run until the gates on #123 are met:** Astra's **DECISION:** sign-off on `labs/weights/PLAN.md` as amended by `AMENDMENT_1.md` and `AMENDMENT_2.md`, and the M4 reserve digest on #119 with its independent human spot-check disposition. Phase 0 built this notebook and did not run it.

What it does (PLAN.md, W1 Stage A, steps 1-4): about 200 training episodes from fresh secret seeds, 8 attempts each at temperature 0.7, inside the full HARE harness (advisory checks, gateway, verifier, one correction). An attempt is kept only if its first answer passes the adjudicator against gold (model-clean) with zero blocked or duplicate calls, at most 2 per episode in attempt order; training rows stop at that first answer (Amendment 2, D1). Each episode's kept traces share a total weight of 1.0. Episodes with no kept attempt go to W2. Gate G1: 15-85% of all attempted rollouts are kept. Every attempt is scored model-clean, corrected-model and final-system (Amendment 1, section 1). The summary publishes throughput, peak VRAM, accelerator count, wall-hours, device-hours and per-episode coverage (section 6).

**Before running:** attach the private dataset holding `w1-pilot.episodes.jsonl` (made by `gen_hare.py generate`) and set `EPISODES_SHA256` below to the value posted on #123. Accelerator **GPU T4 x2**, Internet **On**. Keep the notebook private: `attempts.jsonl` and `kept-rows.jsonl` hold full synthetic transcripts and training gold. Only `summary.json` leaves the session.

Estimated GPU time: about 3 hours (PLAN.md); the run replaces this with a measured number."""),
        code(f"""EPISODES_SHA256 = ""        # REQUIRED: the w1-pilot episodes sha256 posted on #123
EPISODES_NAME = "w1-pilot.episodes.jsonl"
ATTEMPTS = 8
TEMPERATURE = 0.7
MAX_TOKENS = 1024
DEADLINE_MINUTES = 600
MAIN_COMMIT = "{MAIN_COMMIT}"
MODEL = {json.dumps(MODEL_4B)}
WORK = "/kaggle/working/w1-phase1"
MODELS = "/tmp/haven-models"
assert len(EPISODES_SHA256) == 64, "set EPISODES_SHA256 to the value posted on #123"
"""),
        code("""import subprocess, os, sys, shutil, json, hashlib, base64, io, tarfile, pathlib, time, glob
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
sh("nvidia-smi --query-gpu=name,memory.total --format=csv"); sh("nproc; free -g | head -2")
os.makedirs(WORK, exist_ok=True); os.makedirs(MODELS, exist_ok=True)
"""),
        code(f"""if not os.path.isdir("/tmp/haven/.git"):
    sh("git clone -q --filter=blob:none https://github.com/erpzz/haven /tmp/haven")
sh(f"git -C /tmp/haven checkout -q {{MAIN_COMMIT}} && git -C /tmp/haven log -1 --format='%h %s'")
BLOB = "{blob}"
raw = base64.b64decode(BLOB)
assert hashlib.sha256(raw).hexdigest() == "{blob_sha}", "embedded Phase 0 bundle corrupted"
dest = pathlib.Path("/tmp/haven/labs/weights")
dest.mkdir(parents=True, exist_ok=True)
shutil.rmtree(dest / "phase0", ignore_errors=True)
tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz").extractall(dest, filter="data")
P0 = dest / "phase0"
sh(f"cd {{P0}} && python3 fetch_deps.py --verify")
sh(f"cd {{P0}} && python3 -m unittest discover -s tests 2>&1 | tail -4")
"""),
        code(llama_cell + '\nENGINE = build_llama("b11146", "/tmp/llama.cpp")   # the run-1 engine\n'),
        code("""def fetch(spec):
    path = f"{MODELS}/{spec['file']}"
    if not os.path.exists(path):
        url = f"https://huggingface.co/{spec['repo']}/resolve/{spec['revision']}/{spec['file']}"
        sh(f"curl -sSL --retry 5 -o {path}.part '{url}' && mv {path}.part {path}")
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    assert h.hexdigest() == spec["sha256"], f"sha256 mismatch for {spec['file']}"
    return path
M4 = fetch(MODEL)
found = glob.glob(f"/kaggle/input/**/{EPISODES_NAME}", recursive=True)
assert len(found) == 1, f"attach exactly one private dataset holding {EPISODES_NAME} (found {found})"
EPISODES = found[0]
gpus = sh("nvidia-smi --query-gpu=name --format=csv,noheader").strip().splitlines()
GPU_IDS = ",".join(str(i) for i in range(len(gpus)))
HW = f"Kaggle {len(gpus)}x {gpus[0]}; one llama-server per GPU, identical args"
"""),
        code("""stream(f"cd {P0} && python3 kaggle/w1_phase1.py --engine {ENGINE} --model {M4} --episodes {EPISODES} "
       f"--episodes-sha256 {EPISODES_SHA256} --out {WORK} --gpus {GPU_IDS} --attempts {ATTEMPTS} "
       f"--temperature {TEMPERATURE} --max-tokens {MAX_TOKENS} --deadline-minutes {DEADLINE_MINUTES} --hardware '{HW}'")
"""),
        code("""# Only the summary leaves the session. Kept rows and transcripts stay private.
shutil.copy(f"{WORK}/summary.json", "/kaggle/working/w1-phase1-summary.json")
print(json.dumps(json.load(open("/kaggle/working/w1-phase1-summary.json"))["summary"], indent=2))
"""),
    ]
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                       "language_info": {"name": "python"},
                                       "kaggle": {"accelerator": "nvidiaTeslaT4", "isInternetEnabled": True,
                                                  "isGpuEnabled": True}},
          "nbformat": 4, "nbformat_minor": 4}
    OUT.write_text(json.dumps(nb, indent=1) + "\n")
    return {"notebook": str(OUT.relative_to(HERE)), "bundle_bytes": len(raw), "bundle_sha256": blob_sha,
            "notebook_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
