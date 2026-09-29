"""Fixed benign development workload. Never installed as a production route."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from haven.supervisor import read_frame, write_frame, process_birth, boot_id, K
from haven.worker import execute

mode = sys.argv[1]
if mode == "sleeper":
    time.sleep(60)
elif mode == "tree":
    child = subprocess.Popen([sys.executable, "-I", "-B", __file__, "sleeper"],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, creationflags=0x08000000)
    print(json.dumps({"child_pid": child.pid}), flush=True)
    time.sleep(60)
elif mode == "parent":
    from haven.supervisor import OwnedJob, OwnedProcess, private_environment
    root = Path(sys.argv[2])
    job = OwnedJob()
    process = OwnedProcess(job, [sys.executable, "-I", "-B", __file__, "tree"],
                           env=private_environment(root), cwd=root)
    descendant = json.loads(process.stdout.readline())
    (root / "parent-ready.json").write_text(json.dumps({"worker": process.identity,
                                                        "descendant": descendant,
                                                        "observation": job.observation()}))
    time.sleep(60)
else:
    request = read_frame(sys.stdin.buffer)
    if mode == "crash":
        os._exit(17)
    if mode in ("hang", "delay"):
        time.sleep(60 if mode == "hang" else 0.25)
    if mode == "malformed":
        sys.stdout.buffer.write(b"\xff\xff\xff\xff")
        sys.stdout.buffer.flush()
    else:
        if mode == "mock-model-transport":
            # Instrumented benign transport only: absolutely no adapter/network.
            request["job"]["route"] = "deterministic"
        result = execute(request)
        if mode == "mock-model-transport":
            result["usage"] = {"model_calls": 1, "certainty": "BACKEND_REPORTED",
                               "prompt_tokens": 10, "output_tokens": 4, "duration_ns": 100}
        if mode == "stale":
            result["identity"]["lease_fence"] -= 1
        if mode == "bad_hash":
            result["output_digest"] = "wrong"
        write_frame(sys.stdout.buffer, result)
