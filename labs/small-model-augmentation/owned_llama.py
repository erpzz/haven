"""Launcher-owned llama-server process lease and guarded command runner.

This module closes the gap between "a loopback endpoint looks right" and "the
validated endpoint belongs to the server process this launcher just started".

It deliberately fails closed if the requested port is already occupied or if
the listener PID cannot be proven. Production PID ownership uses lsof; tests
may inject an owner probe.

The model and server files are SHA-256 checked before launch and their file
identity is checked again while the lease is active. This is not protection
against a malicious same-user actor racing path replacement; see README.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import observe_llama
import preflight

HEX64 = re.compile(r"[0-9a-f]{64}\Z")
MAX_ARG = 4096
DEFAULT_START_TIMEOUT = 120.0
DEFAULT_GUARD_INTERVAL = 0.5
DEFAULT_STOP_TIMEOUT = 5.0


class LeaseError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def receipt(errors, *, server_started=False, owner_verified=False,
            model_file_verified=False, server_file_verified=False,
            endpoint_verified=False, guarded_command_started=False,
            guarded_command_exit=None):
    return {
        "schema": "haven.owned-llama-lease.v1",
        "status": "block" if errors else "pass",
        "errors": list(errors),
        "server_started": bool(server_started),
        "listener_owner_verified": bool(owner_verified),
        "model_file_verified": bool(model_file_verified),
        "server_file_verified": bool(server_file_verified),
        "live_endpoint_verified": bool(endpoint_verified),
        "guarded_command_started": bool(guarded_command_started),
        "guarded_command_exit": guarded_command_exit,
    }


def _valid_hash(value):
    return type(value) is str and HEX64.fullmatch(value) is not None


def _hash_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        while True:
            block = fh.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _file_identity(path):
    st = Path(path).stat()
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)


def verify_file(path, expected_sha256, *, executable=False):
    if type(path) is not str or not path or len(path) > MAX_ARG or "\x00" in path:
        raise LeaseError("INVALID_FILE_PATH")
    if not _valid_hash(expected_sha256):
        raise LeaseError("INVALID_EXPECTED_HASH")
    p = Path(path)
    try:
        if not p.is_file():
            raise LeaseError("FILE_NOT_FOUND")
        if executable and not os.access(p, os.X_OK):
            raise LeaseError("SERVER_NOT_EXECUTABLE")
        before = _file_identity(p)
        digest = _hash_file(p)
        after = _file_identity(p)
    except LeaseError:
        raise
    except OSError:
        raise LeaseError("FILE_CHECK_FAILED") from None
    if before != after:
        raise LeaseError("FILE_CHANGED_DURING_HASH")
    if digest != expected_sha256:
        raise LeaseError("FILE_HASH_MISMATCH")
    return p.resolve(), after


def port_is_free(port):
    if type(port) is not int or type(port) is bool or not 1 <= port <= 65535:
        raise LeaseError("INVALID_PORT")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.2)
    try:
        return s.connect_ex(("127.0.0.1", port)) != 0
    finally:
        s.close()


def listener_pids_lsof(port, expected_pid=None):
    lsof = shutil.which("lsof")
    if not lsof:
        raise LeaseError("PORT_OWNER_TOOL_MISSING")
    try:
        cp = subprocess.run(
            [lsof, "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            text=True, capture_output=True, timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise LeaseError("PORT_OWNER_CHECK_FAILED") from None
    if cp.returncode not in (0, 1):
        raise LeaseError("PORT_OWNER_CHECK_FAILED")
    pids = set()
    for raw in cp.stdout.split():
        if not raw.isdigit():
            raise LeaseError("PORT_OWNER_CHECK_FAILED")
        pids.add(int(raw))
    return pids


def _safe_server_args(values):
    if type(values) is not list:
        raise LeaseError("INVALID_SERVER_ARGS")
    # Strict profile: arbitrary llama-server flags can override security-critical
    # -m/host/port/context/alias settings after they have been hash/admission checked.
    # Add explicit typed launcher options later instead of accepting a raw argv tail.
    if values:
        raise LeaseError("SERVER_EXTRA_ARGS_NOT_ALLOWED")
    return []


def _terminate_group(process, timeout=2.0):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            process.terminate()
        except OSError:
            pass
    try:
        process.wait(timeout=timeout)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass


@dataclass
class Lease:
    process: subprocess.Popen
    port: int
    expected_model: str
    requested_model: str
    context_tokens: int
    server_path: Path
    model_path: Path
    server_identity: tuple
    model_identity: tuple
    owner_probe: object
    endpoint_verified: bool = True
    owner_verified: bool = True

    def guard(self):
        if self.process.poll() is not None:
            raise LeaseError("SERVER_EXITED")
        try:
            if _file_identity(self.server_path) != self.server_identity:
                raise LeaseError("SERVER_FILE_CHANGED")
            if _file_identity(self.model_path) != self.model_identity:
                raise LeaseError("MODEL_FILE_CHANGED")
        except LeaseError:
            raise
        except OSError:
            raise LeaseError("LEASE_FILE_CHECK_FAILED") from None
        pids = self.owner_probe(self.port, self.process.pid)
        if pids != {self.process.pid}:
            raise LeaseError("LISTENER_OWNER_CHANGED")
        runtime = observe_llama.check_runtime(
            self.expected_model, self.requested_model,
            f"http://127.0.0.1:{self.port}",
        )
        if runtime["status"] != "pass":
            raise LeaseError("RUNTIME_REVALIDATION_FAILED")
        return True

    def stop(self, timeout=DEFAULT_STOP_TIMEOUT):
        _terminate_group(self.process, timeout=timeout)


def launch(server, server_sha256, model, model_sha256, *,
           alias, port, context_tokens=65536, log_path=None,
           extra_args=None, start_timeout=DEFAULT_START_TIMEOUT,
           owner_probe=None):
    if owner_probe is None:
        owner_probe = listener_pids_lsof
    if not preflight.valid_id(alias):
        raise LeaseError("INVALID_ALIAS")
    if (type(context_tokens) is not int or type(context_tokens) is bool
            or context_tokens < preflight.MIN_CONTEXT):
        raise LeaseError("INVALID_CONTEXT")
    if (type(start_timeout) not in (int, float) or type(start_timeout) is bool
            or not 0.1 <= float(start_timeout) <= 600):
        raise LeaseError("INVALID_START_TIMEOUT")
    if not port_is_free(port):
        raise LeaseError("PORT_ALREADY_IN_USE")

    server_path, server_identity = verify_file(server, server_sha256, executable=True)
    model_path, model_identity = verify_file(model, model_sha256, executable=False)
    args = [
        str(server_path), "-m", str(model_path),
        "--host", "127.0.0.1", "--port", str(port),
        "-c", str(context_tokens), "-np", "1",
        "--jinja", "--alias", alias,
    ] + _safe_server_args(extra_args or [])

    sink = subprocess.DEVNULL
    log_fh = None
    if log_path is not None:
        if type(log_path) is not str or not log_path or len(log_path) > MAX_ARG or "\x00" in log_path:
            raise LeaseError("INVALID_LOG_PATH")
        try:
            lp = Path(log_path)
            lp.parent.mkdir(parents=True, exist_ok=True)
            log_fh = lp.open("ab")
            sink = log_fh
        except OSError:
            raise LeaseError("LOG_OPEN_FAILED") from None
    try:
        proc = subprocess.Popen(
            args, stdin=subprocess.DEVNULL, stdout=sink, stderr=sink,
            start_new_session=True,
        )
    except OSError:
        if log_fh:
            log_fh.close()
        raise LeaseError("SERVER_EXEC_FAILED") from None

    lease = Lease(
        proc, port, alias, alias, context_tokens,
        server_path, model_path, server_identity, model_identity, owner_probe,
        endpoint_verified=False, owner_verified=False,
    )
    deadline = time.monotonic() + float(start_timeout)
    retryable = {"MODELS_OBSERVATION_FAILED", "PROPS_OBSERVATION_FAILED"}
    try:
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise LeaseError("SERVER_EXITED_DURING_START")
            runtime = observe_llama.check_runtime(alias, alias, f"http://127.0.0.1:{port}")
            if runtime["status"] == "pass":
                lease.endpoint_verified = True
                break
            if not set(runtime["errors"]) <= retryable:
                raise LeaseError("RUNTIME_ADMISSION_FAILED")
            time.sleep(0.1)
        else:
            raise LeaseError("SERVER_START_TIMEOUT")

        pids = owner_probe(port, proc.pid)
        if pids != {proc.pid}:
            raise LeaseError("LISTENER_OWNER_MISMATCH")
        lease.owner_verified = True
        lease.guard()
        return lease
    except Exception:
        lease.stop()
        raise
    finally:
        if log_fh:
            log_fh.close()


def run_guarded(lease, command, *, cwd=None, env=None,
                guard_interval=DEFAULT_GUARD_INTERVAL):
    if not isinstance(lease, Lease):
        return None, "INVALID_LEASE"
    # run_guarded consumes a valid lease: every validation/launch/guard outcome
    # after this point stops the dedicated server before returning.
    if (type(command) is not list or not command
            or any(type(x) is not str or not x or len(x) > MAX_ARG or "\x00" in x
                   for x in command)):
        lease.stop()
        return None, "INVALID_COMMAND"
    if (type(guard_interval) not in (int, float) or type(guard_interval) is bool
            or not 0.05 <= float(guard_interval) <= 30):
        lease.stop()
        return None, "INVALID_GUARD_INTERVAL"
    if cwd is not None and not Path(cwd).is_dir():
        lease.stop()
        return None, "INVALID_WORKING_DIRECTORY"
    try:
        lease.guard()
    except LeaseError as exc:
        lease.stop()
        return None, exc.code
    try:
        child = subprocess.Popen(command, cwd=cwd, env=env, start_new_session=True)
    except OSError:
        lease.stop()
        return None, "GUARDED_COMMAND_EXEC_FAILED"
    error = None
    try:
        while child.poll() is None:
            time.sleep(float(guard_interval))
            try:
                lease.guard()
            except LeaseError as exc:
                error = exc.code
                _terminate_group(child, timeout=2)
                break
        rc = child.poll()
        if error is None:
            try:
                lease.guard()
            except LeaseError as exc:
                error = exc.code
                _terminate_group(child, timeout=2)
        return rc, error
    finally:
        lease.stop()


def main(argv=None):
    p = argparse.ArgumentParser(description="Launch and guard a hash-checked dedicated llama-server")
    p.add_argument("--server", required=True)
    p.add_argument("--server-sha256", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--model-sha256", required=True)
    p.add_argument("--alias", required=True)
    p.add_argument("--port", required=True, type=int)
    p.add_argument("--context", type=int, default=65536)
    p.add_argument("--log")
    p.add_argument("--start-timeout", type=float, default=DEFAULT_START_TIMEOUT)
    p.add_argument("--server-extra", action="append", default=[])
    p.add_argument("command", nargs=argparse.REMAINDER)
    args = p.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    started = owner = endpoint = False
    model_ok = server_ok = False
    try:
        # Hash checks happen inside launch; these booleans are deliberately only
        # set after launch returns, so a failed launch never claims verification.
        lease = launch(
            args.server, args.server_sha256, args.model, args.model_sha256,
            alias=args.alias, port=args.port, context_tokens=args.context,
            log_path=args.log, extra_args=args.server_extra,
            start_timeout=args.start_timeout,
        )
        started = owner = endpoint = model_ok = server_ok = True
    except LeaseError as exc:
        out = receipt([exc.code], server_started=started, owner_verified=owner,
                      model_file_verified=model_ok, server_file_verified=server_ok,
                      endpoint_verified=endpoint)
        print(json.dumps(out, sort_keys=True))
        return 2

    if not command:
        lease.stop()
        out = receipt([], server_started=True, owner_verified=True,
                      model_file_verified=True, server_file_verified=True,
                      endpoint_verified=True)
        print(json.dumps(out, sort_keys=True))
        return 0

    rc, guard_error = run_guarded(lease, command)
    errors = [guard_error] if guard_error else []
    out = receipt(errors, server_started=True, owner_verified=True,
                  model_file_verified=True, server_file_verified=True,
                  endpoint_verified=True, guarded_command_started=True,
                  guarded_command_exit=rc)
    print(json.dumps(out, sort_keys=True), file=sys.stderr if command else sys.stdout)
    if errors:
        return 2
    return rc if isinstance(rc, int) else 2


if __name__ == "__main__":
    raise SystemExit(main())
