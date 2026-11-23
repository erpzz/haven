"""Kaggle job: the preregistered Purple Copilot head-to-head (see eval/PREREGISTRATION.md).

Kaggle T4 GPUs, internet on, datasets haven-llama-b11146-cuda13-sm75 and haven-purple-h2h.
Push with OWNER in kernel-metadata.json replaced by the Kaggle account, for example:
  sed "s/OWNER/$KAGGLE_USER/g" kernel-metadata.json > /tmp/push/kernel-metadata.json
Writes /kaggle/working/h2h-results.jsonl after every run.
"""
import glob, hashlib, json, os, re, shutil, subprocess, sys, time

HAVEN_COMMIT = "6d62b1032f602efcb994b24e9d3760b69f940087"
HERMES_REF = "v2026.9.24"
RUNS = [  # model spec, alias, repetitions
    ({"repo": "unsloth/Qwen3.5-4B-GGUF", "revision": "e87f176479d0855a907a41277aca2f8ee7a09523",
      "file": "Qwen3.5-4B-Q4_K_M.gguf", "sha256": "00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4"},
     "qwen3.5-4b", 3),
    ({"repo": "unsloth/Qwen3.6-35B-A3B-GGUF", "revision": "a483e9e6cbd595906af30beda3187c2663a1118c",
      "file": "Qwen3.6-35B-A3B-UD-Q4_K_M.gguf", "sha256": "ac0e2c1189e055faa36eff361580e79c5bd6f8e76bffb4ce547f167d53e31a61"},
     "qwen3.6-35b-a3b", 1),
]
OUT = "/kaggle/working/h2h-results.jsonl"  # round 2
MODELS = "/tmp/models"
os.makedirs(MODELS, exist_ok=True)


def sh(cmd, check=True):
    print("$", cmd, flush=True)
    r = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    print((r.stdout or "")[-3000:], (r.stderr or "")[-3000:], flush=True)
    if check and r.returncode:
        raise SystemExit(f"failed: {cmd}")
    return r.stdout


def stream(cmd):
    print("$", cmd, flush=True)
    p = subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout:
        print(line, end="", flush=True)
    return p.wait()


sh("nvidia-smi --query-gpu=name,memory.total --format=csv; nproc; free -g | head -2; df -h /tmp | tail -1")
STUB_DEB = ("https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-driver-dev-13-0_13.0.88-1_amd64.deb",
            "3ffcc3fc69aa914629a97839aaf2b624508fbae9d87f187231795745a6be2550")
def find_libcuda():
    # every libcuda.so* the loader cache, nvidia-smi's own libraries or common driver dirs know about
    sh("echo LD_LIBRARY_PATH=$LD_LIBRARY_PATH; ldd $(command -v nvidia-smi) 2>/dev/null | grep -i nvidia", check=False)
    out = sh("ldconfig -p | grep -o '/[^ ]*libcuda[.]so[.0-9]*' ; "
             "for d in $(ldd $(command -v nvidia-smi) 2>/dev/null | grep -o '/[^ ]*libnvidia-ml[^ ]*' | xargs -r -n1 dirname); do ls $d/libcuda.so* 2>/dev/null; done; "
             "find /usr/local/nvidia /usr/lib64-nvidia /usr/local/cuda /usr/local/cuda-13.0 /usr/lib /usr/lib64 /opt "
             "-name 'libcuda.so*' 2>/dev/null | head -40", check=False)
    found = {p.strip() for p in out.split() if os.path.basename(p.strip()).startswith("libcuda.so") and os.path.exists(p.strip())}
    if not [p for p in found if os.path.getsize(os.path.realpath(p)) > 5_000_000]:
        out = sh("timeout 180 find / -path /proc -prune -o -path /sys -prune -o -path /kaggle/input -prune -o "
                 "-name 'libcuda.so*' -print 2>/dev/null | head -20", check=False)
        found |= {p.strip() for p in out.split() if os.path.basename(p.strip()).startswith("libcuda.so") and os.path.exists(p.strip())}
    return sorted(found)
def is_real_driver(p):
    # the driver library is tens of MB; NVIDIA's link stub (and our renamed copies of it) is tiny.
    # cuda-*/compat holds a forward-compatibility libcuda for OLDER host drivers: loading it on a newer
    # host driver fails with "unsupported display driver / cuda driver combination", so never use it.
    return os.path.getsize(os.path.realpath(p)) > 5_000_000 and "/compat/" not in p
def host_drivers(found):
    real = [p for p in found if is_real_driver(p)]
    return sorted(real, key=lambda p: (not p.startswith("/usr/local/nvidia"), p))
def find_libcuda_runtime():
    real = host_drivers(find_libcuda())
    if real:  # host driver directory first, ahead of anything else on the path
        os.environ["LD_LIBRARY_PATH"] = os.path.dirname(real[0]) + ":" + os.environ.get("LD_LIBRARY_PATH", "")
def libcuda_for_link():
    found = find_libcuda()
    print("libcuda candidates:", found)
    real = host_drivers(found)
    if real:  # make sure the server loads the host driver at run time, not a compat copy
        d = os.path.dirname(real[0])
        os.environ["LD_LIBRARY_PATH"] = d + ":" + os.environ.get("LD_LIBRARY_PATH", "")
    stubs = [p for p in found if os.path.getsize(os.path.realpath(p)) <= 5_000_000 and "/libcuda-link" not in p]
    if stubs:
        stub = stubs[0]
    else:
        deb = "/tmp/cuda-driver-dev.deb"
        sh(f"curl -sSL --retry 5 -o {deb} '{STUB_DEB[0]}'")
        assert hashlib.sha256(open(deb, "rb").read()).hexdigest() == STUB_DEB[1], "stub package hash mismatch"
        sh(f"rm -rf /tmp/cuda-stub && dpkg-deb -x {deb} /tmp/cuda-stub")
        stub = sh("find /tmp/cuda-stub -name libcuda.so | head -1").strip()
        assert stub, "no libcuda.so in the stub package"
    # the linker resolves the dependency by its soname (libcuda.so.1); give it both names in one writable dir
    sh(f"rm -rf /tmp/libcuda-link && mkdir -p /tmp/libcuda-link && cp {stub} /tmp/libcuda-link/libcuda.so "
       "&& ln -s libcuda.so /tmp/libcuda-link/libcuda.so.1")
    return "/tmp/libcuda-link/libcuda.so"
def cached_build(tag):
    # a private Kaggle dataset holding a prebuilt llama-server (+ libs) and a sha256 manifest
    import glob
    for man in glob.glob(f"/kaggle/input/**/haven-llama-{tag}-cuda13-sm75/manifest.json", recursive=True):
        root = os.path.dirname(man)
        files = json.load(open(man))["files"]
        if all(hashlib.sha256(open(os.path.join(root, f), "rb").read()).hexdigest() == h for f, h in files.items()):
            return root
        print("cached build failed its hash check, ignoring:", root)
    return None
def build_llama(tag, prefix):
    engine = f"{prefix}/build/bin/llama-server"
    cache = cached_build(tag) if not os.path.exists(engine) else None
    if cache:
        sh(f"mkdir -p {prefix}/build/bin && cp -a {cache}/bin/. {prefix}/build/bin/ && chmod +x {engine}")
        print("using cached build from", cache)
        os.environ["LD_LIBRARY_PATH"] = (f"{prefix}/build/bin:/usr/local/cuda/lib64:/usr/local/cuda/targets/x86_64-linux/lib:"
                                         + os.environ.get("LD_LIBRARY_PATH", ""))
        find_libcuda_runtime()
    if not os.path.exists(engine):
        sh(f"git clone -q --depth 1 --branch {tag} https://github.com/ggml-org/llama.cpp {prefix}")
        t0 = time.time()
        drv_lib = libcuda_for_link()
        link = f"-Wl,-rpath-link,{os.path.dirname(drv_lib)}"
        flags = (f"-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75 -DCUDA_cuda_driver_LIBRARY={drv_lib} "
                 f"'-DCMAKE_EXE_LINKER_FLAGS={link}' '-DCMAKE_SHARED_LINKER_FLAGS={link}' -DLLAMA_CURL=OFF "
                 "-DLLAMA_USE_PREBUILT_UI=OFF -DLLAMA_BUILD_UI=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF")
        cmake = "cmake"
        sh(f"cd {prefix} && {cmake} -S . -B build {flags} > /tmp/cmake.log 2>&1 || (tail -40 /tmp/cmake.log; false)")
        sh(f"cd {prefix} && {cmake} --build build --target llama-server -j4 > /tmp/build.log 2>&1 || (tail -60 /tmp/build.log; false)")
        print(f"{tag} build minutes: {(time.time()-t0)/60:.1f}")
    sh("nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1", check=False)
    sh(f"ldd {os.path.dirname(engine)}/libggml-cuda.so | grep -E 'libcuda|libcudart|libcublas'", check=False)
    out = sh(f"{engine} --list-devices 2>&1", check=False)
    import re as _re
    if "failed to initialize CUDA" in out or not _re.search(r"^\s*CUDA\d+:", out, _re.M):
        raise SystemExit("llama-server cannot use the GPUs (see the libcuda lines above); stopping instead of running on CPU")
    return engine
ENGINE = build_llama("b11146", "/tmp/llama.cpp")


def fetch(spec):
    path = f"{MODELS}/{spec['file']}"
    if not os.path.exists(path):
        url = f"https://huggingface.co/{spec['repo']}/resolve/{spec['revision']}/{spec['file']}"
        sh(f"curl -sSL --retry 5 -o {path}.part '{url}' && mv {path}.part {path}")
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""):
            h.update(c)
    assert h.hexdigest() == spec["sha256"], f"sha256 mismatch for {spec['file']}"
    return path


# Hermes Agent, the pinned release Haven builds on
# Hermes supports only editable installs (no wheels), as on the local host.
sh("pip install -q uv")
sh(f"git clone -q --depth 1 --branch {HERMES_REF} https://github.com/NousResearch/hermes-agent /tmp/hermes-agent")
sh("cd /tmp/hermes-agent && (uv venv -q .venv --python 3.11 || uv venv -q .venv) && uv pip install -q -p .venv/bin/python -e .")
HERMES = "/tmp/hermes-agent/.venv/bin/hermes"
sh(f"{HERMES} --version")

# Haven at the frozen commit
sh("git clone -q --filter=blob:none https://github.com/erpzz/haven /tmp/haven")
sh(f"git -C /tmp/haven checkout -q {HAVEN_COMMIT} && git -C /tmp/haven log -1 --format='%h %s'")
LAB = "/tmp/haven/labs/purple-copilot-apm"
sh(f"cd {LAB} && python3 -m unittest discover -s tests 2>&1 | tail -3")

# Inputs: Haven's history for the haven arm, the CSV export for the stock-Hermes arm
data = os.path.dirname(glob.glob("/kaggle/input/**/history.sqlite3", recursive=True)[0])
STATE = "/tmp/apm-state"
os.makedirs(STATE, mode=0o700, exist_ok=True)
shutil.copy(f"{data}/history.sqlite3", f"{STATE}/history.sqlite3")
EXPORT = f"{data}/bloodhound_export"
print(open(f"{EXPORT}/manifest.json").read())

for spec, alias, reps in RUNS:
    try:
        path = fetch(spec)
    except Exception as exc:
        print("skipping", alias, exc)
        continue
    # Round 1 lost the 35B: terminating the shell left the 4B server holding the port, and llama.cpp ignores the
    # requested model name. Each server now runs in its own process group, the port must be free before start,
    # and the served alias is checked before any arm runs.
    assert subprocess.run("curl -s http://127.0.0.1:8080/health", shell=True).returncode != 0, "port 8080 still in use"
    log = open(f"/kaggle/working/llama-{alias}.log", "w")
    server = subprocess.Popen([ENGINE, "-m", path, "--host", "127.0.0.1", "--port", "8080", "-c", "65536", "-np", "1",
                               "--jinja", "-ngl", "99", "--alias", alias, "--no-webui"],
                              stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(400):
        time.sleep(3)
        if server.poll() is not None:
            break
        if subprocess.run("curl -s http://127.0.0.1:8080/health | grep -q ok", shell=True).returncode == 0:
            break
    served = subprocess.run("curl -s http://127.0.0.1:8080/v1/models", shell=True, text=True, capture_output=True).stdout
    if server.poll() is not None or f'"{alias}"' not in served:
        print("server for", alias, "is not serving it; skipping. models:", served[:300])
        if server.poll() is None:
            os.killpg(server.pid, 15)
        continue
    try:
        stream(f"cd {LAB} && python3 eval/h2h_run.py --base-url http://127.0.0.1:8080/v1 --model {alias} "
               f"--hermes {HERMES} --lab {LAB} --state {STATE} --export {EXPORT} --stock-dir /tmp/h2h-stock "
               f"--reps {reps} --out {OUT}")
    finally:
        os.killpg(server.pid, 15)
        try:
            server.wait(timeout=60)
        except subprocess.TimeoutExpired:
            os.killpg(server.pid, 9)
            server.wait()
        time.sleep(5)
        os.remove(path)
print("done", sum(1 for _ in open(OUT)) if os.path.exists(OUT) else 0, "runs")
