# Kaggle llama.cpp b11146 CUDA build helpers, copied verbatim from PR #115
# (labs/intelligence-bakeoff/system0/kaggle/build_notebook.py at 7f5af0d), where they built the engine
# for Kaggle run 1. Kept as a separate file so a diff against the source is trivial.
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
