"""Compare one local model with Hermes' deterministic synthetic-policy route.

Explicitly launches one bounded CPU-only llama-server on an owned loopback
port, using an existing GGUF. There is no download or production service change.
Receipts and server logs stay in the operator-supplied owner-only directory.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

LAB = Path(__file__).resolve().parents[1]
PLUGIN = LAB / ".hermes/plugins/haven-forge"
SUITES = {name: Path(__file__).with_name(f"entra-heldout-{name}.json") for name in ("v1", "v2", "v3")}
sys.path.insert(0, str(PLUGIN))
from forge_runtime.entra import fixture, select_policy
from forge_runtime.router import route_synthetic


def ensure_resources():
    if sys.platform != "darwin":
        raise RuntimeError("This bounded protocol is configured for macOS only")
    battery = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5, check=True).stdout
    if "AC Power" not in battery:
        raise RuntimeError("AC power is required")
    pressure = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=5, check=True).stdout
    import re
    match = re.search(r"System-wide memory free percentage:\s*(\d+)%", pressure)
    if not match or int(match.group(1)) < 15:
        raise RuntimeError("Available memory is unknown or below the 15 percent stop threshold")


def save_receipt(path, receipt):
    temp = path.with_suffix(".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    os.replace(temp, path)


def listen_owner(port):
    result = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                            capture_output=True, text=True, timeout=4, check=False)
    return {int(x) for x in result.stdout.splitlines() if x.isdigit()}


def request(opener, host, port, path, body=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://{host}:{port}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    with opener.open(req, timeout=timeout) as response:
        return json.load(response)


def prompt_for(policy, additional_instructions=""):
    facts = {"state": policy["state"], "grantControls": policy["grantControls"]}
    instruction = (
        "Classify a single synthetic Microsoft Entra Conditional Access policy. "
        "Reply with exactly one label: not_enforced_by_policy, mfa_required_by_policy, "
        "mfa_not_required_by_policy, access_blocked_by_policy, or indeterminate. "
        "Disabled and report-only policies are not enforced. An enabled block policy blocks access. "
        "AND requires all grant controls; OR permits any one grant control. Evaluate only this policy. "
        + additional_instructions
    )
    return ("<|im_start|>system\n" + instruction + "<|im_end|>\n"
            "<|im_start|>user\n" + json.dumps(facts, sort_keys=True) + "<|im_end|>\n"
            "<|im_start|>assistant\n<think>\n\n</think>\n\n")


def setup_hermes(home: Path, source: Path):
    if not (source / "model_tools.py").is_file():
        raise ValueError("Expected a Hermes source checkout")
    os.environ["HERMES_HOME"] = str(home)
    os.environ["TERMINAL_CWD"] = str(home)
    shutil.copytree(PLUGIN, home / "plugins/haven-forge", ignore=shutil.ignore_patterns("__pycache__"))
    (home / "config.yaml").write_text("plugins:\n  enabled:\n    - haven-forge\n", encoding="utf-8")
    sys.path.insert(0, str(source))
    import model_tools
    from hermes_cli.plugins import discover_plugins
    discover_plugins(force=True)
    definitions = model_tools.get_tool_definitions(enabled_toolsets=["haven-forge"], quiet_mode=True,
                                                     skip_tool_search_assembly=True)
    names = [item["function"]["name"] for item in definitions]
    if "forge_assess_entra" not in names:
        raise RuntimeError("Hermes did not expose the synthetic assessment tool")
    return model_tools, names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--hermes-source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--suite", choices=tuple(SUITES), default="v1")
    parser.add_argument("--max-wall-seconds", type=int, default=360, choices=range(30, 601))
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_dir() or output.stat().st_mode & 0o077 or any((p / ".git").exists() for p in (output, *output.parents)):
        raise ValueError("Output must be an existing owner-only directory outside a Git checkout")
    receipt_path = output / "benchmark.json"
    if receipt_path.exists():
        raise ValueError("Refusing to overwrite an existing experiment")
    model = args.model.resolve(strict=True)
    server = shutil.which("llama-server")
    # Hugging Face caches commonly expose a .gguf symlink to an extensionless
    # content-addressed blob; validate the supplied name before resolution.
    if not server or not model.is_file() or args.model.suffix.lower() != ".gguf":
        raise ValueError("An existing GGUF and llama-server are required")
    ensure_resources()
    raw_cases = SUITES[args.suite].read_bytes()
    spec = json.loads(raw_cases)
    plugin_files = sorted(p for p in PLUGIN.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    plugin_manifest = {str(path.relative_to(PLUGIN)): hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in plugin_files}
    hermes_revision = subprocess.run(["git", "-C", str(args.hermes_source), "rev-parse", "HEAD"],
                                     capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    version = subprocess.run([server, "--version"], capture_output=True, text=True, timeout=10, check=True)
    receipt = {"status": "PREPARING", "protocol_sha256": hashlib.sha256(raw_cases).hexdigest(),
               "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "plugin_file_sha256": plugin_manifest, "hermes_source_commit": hermes_revision,
               "llama_server_version": (version.stdout + version.stderr).strip(),
               "model_sha256": None, "hardware_scope": "macOS CPU only", "cases": [],
               "model_calls": 0, "external_requests_configured": 0,
               "network_monitoring": "not instrumented; runner configured for a verified loopback server"}
    save_receipt(receipt_path, receipt)
    deadline = time.monotonic() + args.max_wall_seconds
    started = time.monotonic()
    try:
        with model.open("rb") as stream:
            receipt["model_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        receipt["model_hash_seconds"] = round(time.monotonic() - started, 3)
        ensure_resources()
        if time.monotonic() >= deadline:
            raise TimeoutError("Wall budget exhausted while hashing model")
    except BaseException as exc:
        receipt.update(status="FAILED_OR_INTERRUPTED", failure_type=type(exc).__name__, owned_server_stopped=True)
        save_receipt(receipt_path, receipt)
        raise
    addresses = {item[4][0] for item in socket.getaddrinfo("localhost", 0, socket.AF_INET, socket.SOCK_STREAM)}
    if len(addresses) != 1 or not all(ipaddress.ip_address(address).is_loopback for address in addresses):
        raise RuntimeError("localhost did not resolve uniquely to a loopback address")
    host = next(iter(addresses))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reserved:
        reserved.bind((host, 0))
        port = reserved.getsockname()[1]
    # No provider credentials or ambient llama-server overrides reach the child.
    environment = {key: os.environ[key] for key in ("PATH", "HOME", "USER", "LANG", "LC_ALL", "TMPDIR")
                   if key in os.environ}
    command = [server, "--model", str(model), "--host", host, "--port", str(port),
               "--device", "none", "--n-gpu-layers", "0", "--threads", "4", "--threads-batch", "4",
               "--ctx-size", "4096", "--parallel", "1", "--no-webui"]
    log_fd = os.open(output / "llama-server.private.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    process = None
    old_handlers = {}
    try:
        def interrupted(signum, _frame):
            raise InterruptedError(f"interrupted by signal {signum}")
        for signum in (signal.SIGINT, signal.SIGTERM):
            old_handlers[signum] = signal.signal(signum, interrupted)
        with os.fdopen(log_fd, "wb") as log:
            load_started = time.monotonic()
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=environment)
            receipt.update(status="STARTING", own_server_pid=process.pid)
            save_receipt(receipt_path, receipt)
            while time.monotonic() < min(deadline, load_started + 120):
                if process.poll() is not None:
                    raise RuntimeError("Isolated model server exited during startup")
                owners = listen_owner(port)
                if owners and owners != {process.pid}:
                    raise RuntimeError("The selected port is owned by a different process")
                if owners:
                    try:
                        health = request(opener, host, port, "/health", timeout=2)
                        if health.get("status") == "ok":
                            break
                    except (OSError, ValueError, urllib.error.URLError):
                        pass
                time.sleep(1)
            else:
                raise TimeoutError("Isolated model server did not become ready")
            receipt["server_ready_seconds"] = round(time.monotonic() - load_started, 3)
            ensure_resources()
            profile = output / "temporary-hermes-home"
            profile.mkdir(mode=0o700)
            model_tools, enabled = setup_hermes(profile, args.hermes_source.resolve())
            dataset = fixture(spec["fixture"])
            for case in spec["cases"]:
                ensure_resources()
                if time.monotonic() >= deadline:
                    raise TimeoutError("Experiment wall budget exhausted")
                policy = select_policy(dataset, case["policy_id"])["policies"][0]
                model_prompt = prompt_for(policy, spec.get("additional_instructions", ""))
                start = time.perf_counter()
                body = request(opener, host, port, "/completion", {
                    "prompt": model_prompt, "temperature": 0, "seed": 42, "n_predict": 16,
                    "cache_prompt": True, "id_slot": 0, "stop": ["\n", "<|im_end|>"],
                }, timeout=min(90, max(1, deadline - time.monotonic())))
                model_ms = (time.perf_counter() - start) * 1000
                receipt["model_calls"] += 1
                answer = str(body.get("content", "")).strip().lower()
                question = case.get("question", "Does this Entra policy require MFA?")
                def execute(values):
                    return model_tools.handle_function_call(
                        "forge_assess_entra", values, task_id="forge-heldout", session_id="forge-heldout",
                        tool_call_id="forge-" + case["policy_id"], enabled_tools=enabled)
                start = time.perf_counter()
                decision = route_synthetic(question, spec["fixture"], case["policy_id"], execute)
                fast_ms = (time.perf_counter() - start) * 1000
                fast = decision.get("report", {})
                findings = fast.get("findings") or []
                verdict = findings[0].get("verdict") if len(findings) == 1 else None
                receipt["cases"].append({"policy_id": case["policy_id"], "expected": case["expected"],
                                         "model_answer": answer, "model_correct": answer == case["expected"],
                                         "model_wall_ms": model_ms, "model_timings": body.get("timings"),
                                         "routed_answer": verdict, "routed_correct": verdict == case["expected"],
                                         "routed_wall_ms": fast_ms,
                                         "route_status": decision.get("route_status"),
                                         "evidence_verified": fast.get("verification", {}).get("passed") is True})
                receipt["status"] = "IN_PROGRESS"
                save_receipt(receipt_path, receipt)
            receipt["status"] = "COMPLETE"
    except BaseException as exc:
        receipt["status"] = "FAILED_OR_INTERRUPTED"
        receipt["failure_type"] = type(exc).__name__
        raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        receipt["owned_server_stopped"] = process is None or process.poll() is not None
        save_receipt(receipt_path, receipt)
        for signum, handler in old_handlers.items():
            signal.signal(signum, handler)
    print(json.dumps({"status": receipt["status"], "completed_cases": len(receipt["cases"]),
                      "model_calls": receipt["model_calls"], "owned_server_stopped": receipt["owned_server_stopped"]}))


if __name__ == "__main__":
    main()
