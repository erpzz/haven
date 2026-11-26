#!/usr/bin/env python3
"""Target-Mac model-request interruption/recovery qualification for #215 × #218.

This is development evidence tooling. It uses the reviewed #215 enrollment and
the exact #127 owned llama launcher, plus #218's checkpoint journal.

Phase 1:
- start the enrolled server/model through owned_llama.py;
- acquire the checkpoint RunLease;
- record unit_started + model_request_started;
- send the actual /v1/chat/completions request bytes;
- signal the parent, then wait without committing a response;
- parent proves a competing RunLease is refused and SIGKILLs that child.

Phase 2:
- prove the lease was released and the owned server port was cleaned up;
- restart the same enrolled server/model;
- open(resume=True), start attempt 2, send/read a real model request,
  commit only its SHA-256, complete the unit and run.

This proves client/process interruption around a real admitted model request.
It does NOT by itself prove the model server was internally hung.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
import subprocess
import sys
import time
from typing import Any

AUG = Path(__file__).resolve().parents[1]
RED = Path(__file__).resolve().parent
if str(AUG) not in sys.path:
    sys.path.insert(0, str(AUG))
if str(RED) not in sys.path:
    sys.path.insert(0, str(RED))

import checkpoint_journal as checkpoint
import mac_case_qualification as mac
import owned_llama
from local_runner import _write_private_json

SCHEMA = "haven.mac-model-request-recovery.v1"
CHILD_RESULT_SCHEMA = "haven.mac-model-request-recovery-child.v1"
UNIT = "model-request"
RUN_ID = "mac-model-request-recovery"
HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


class RecoveryQualificationError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha_obj(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _write_marker(path: Path, value: Any) -> None:
    raw = _canon(value) + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)


def _read_marker(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024:
        raise RecoveryQualificationError("MARKER_INVALID")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryQualificationError("MARKER_INVALID") from exc
    if not isinstance(value, dict):
        raise RecoveryQualificationError("MARKER_INVALID")
    return value


def _select_port(port: int) -> int:
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise RecoveryQualificationError("INVALID_PORT")
    if port:
        return port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


def _require_apfs(path: Path) -> dict[str, str]:
    if sys.platform != "darwin":
        raise RecoveryQualificationError("MACOS_REQUIRED")
    try:
        df = subprocess.run(
            ["df", "-P", str(path)],
            text=True, capture_output=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RecoveryQualificationError("FILESYSTEM_PROBE_FAILED") from exc
    if df.returncode != 0:
        raise RecoveryQualificationError("FILESYSTEM_PROBE_FAILED")
    lines = [line for line in df.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        raise RecoveryQualificationError("FILESYSTEM_PROBE_FAILED")
    device = lines[-1].split()[0]
    try:
        info = subprocess.run(
            ["diskutil", "info", device],
            text=True, capture_output=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RecoveryQualificationError("FILESYSTEM_PROBE_FAILED") from exc
    if info.returncode != 0:
        raise RecoveryQualificationError("FILESYSTEM_PROBE_FAILED")
    text = info.stdout.lower()
    if (
        "file system personality:" not in text
        or "apfs" not in text
    ):
        raise RecoveryQualificationError("APFS_REQUIRED")
    return {
        "platform": "darwin",
        "filesystem": "apfs",
        "device": device,
        "diskutil_sha256": hashlib.sha256(info.stdout.encode()).hexdigest(),
    }


def _request_body(alias: str, max_tokens: int) -> bytes:
    return json.dumps({
        "model": alias,
        "messages": [{
            "role": "user",
            "content": "Reply with a short confirmation that this synthetic recovery probe was received.",
        }],
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "stream": False,
    }, separators=(",", ":")).encode("utf-8")


def _send_without_reading(port: int, body: bytes) -> http.client.HTTPConnection:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    conn.putrequest("POST", "/v1/chat/completions")
    conn.putheader("Content-Type", "application/json")
    conn.putheader("Content-Length", str(len(body)))
    conn.endheaders()
    conn.send(body)
    return conn


def _send_and_read(port: int, body: bytes) -> tuple[bytes, int]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=180)
    try:
        conn.request(
            "POST", "/v1/chat/completions",
            body=body, headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        raw = response.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise RecoveryQualificationError("MODEL_RESPONSE_TOO_LARGE")
        if response.status < 200 or response.status >= 300:
            raise RecoveryQualificationError("MODEL_RESPONSE_HTTP_ERROR")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RecoveryQualificationError("MODEL_RESPONSE_INVALID_JSON") from exc
        if not isinstance(value, dict) or not isinstance(value.get("choices"), list):
            raise RecoveryQualificationError("MODEL_RESPONSE_INVALID_SHAPE")
        return raw, response.status
    finally:
        conn.close()


def _child_interrupt(*, journal: Path, manifest_sha256: str, port: int,
                     alias: str, pid_marker: Path, sent_marker: Path,
                     max_tokens: int) -> int:
    body = _request_body(alias, max_tokens)
    _write_marker(pid_marker, {"pid": os.getpid()})
    j = checkpoint.Journal(journal, RUN_ID, manifest_sha256, fsync=True)
    with j.owned(resume=False):
        j.append("unit_started", UNIT, 1)
        j.append(
            "model_request_started", UNIT, 1,
            op_id="model-a1", replay_safe=True,
            payload_sha256=hashlib.sha256(body).hexdigest(),
        )
        conn = _send_without_reading(port, body)
        try:
            _write_marker(sent_marker, {
                "pid": os.getpid(),
                "request_sha256": hashlib.sha256(body).hexdigest(),
                "bytes_sent": len(body),
            })
            # The parent is expected to SIGKILL this process. If it does not,
            # fail rather than silently turning this into a normal completion.
            time.sleep(600)
            return 91
        finally:
            conn.close()


def _child_resume(*, journal: Path, manifest_sha256: str, port: int,
                  alias: str, result_path: Path, max_tokens: int) -> int:
    body = _request_body(alias, max_tokens)
    j = checkpoint.Journal(journal, RUN_ID, manifest_sha256, fsync=True)
    with j.owned(resume=True):
        j.append("unit_started", UNIT, 2)
        j.append(
            "model_request_started", UNIT, 2,
            op_id="model-a2", replay_safe=True,
            payload_sha256=hashlib.sha256(body).hexdigest(),
        )
        raw, status = _send_and_read(port, body)
        response_sha = hashlib.sha256(raw).hexdigest()
        j.append(
            "model_response_committed", UNIT, 2,
            op_id="model-a2", replay_safe=False,
            payload_sha256=response_sha,
        )
        j.append(
            "unit_completed", UNIT, 2,
            payload_sha256=response_sha,
        )
        j.append("run_completed")
    _write_private_json(result_path, {
        "schema": CHILD_RESULT_SCHEMA,
        "status": "pass",
        "http_status": status,
        "response_sha256": response_sha,
        "response_bytes": len(raw),
    })
    return 0


def _wait_marker(path: Path, process: subprocess.Popen, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return _read_marker(path)
        if process.poll() is not None:
            raise RecoveryQualificationError("FIRST_OWNED_EXITED_BEFORE_REQUEST_SENT")
        time.sleep(0.05)
    raise RecoveryQualificationError("REQUEST_SENT_TIMEOUT")


def _verify_direct_child(child_pid: int, owned_pid: int) -> None:
    try:
        cp = subprocess.run(
            ["ps", "-o", "ppid=", "-p", str(child_pid)],
            text=True, capture_output=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RecoveryQualificationError("CHILD_PID_PROBE_FAILED") from exc
    if cp.returncode != 0:
        raise RecoveryQualificationError("CHILD_PID_PROBE_FAILED")
    try:
        ppid = int(cp.stdout.strip())
    except ValueError as exc:
        raise RecoveryQualificationError("CHILD_PID_PROBE_FAILED") from exc
    if ppid != owned_pid:
        raise RecoveryQualificationError("CHILD_PID_PARENT_MISMATCH")


def _owned_command(*, server: Path, server_sha256: str, model: Path,
                   model_sha256: str, alias: str, port: int, context: int,
                   log_path: Path, child_command: list[str]) -> list[str]:
    return [
        sys.executable, str(AUG / "owned_llama.py"),
        "--server", str(server),
        "--server-sha256", server_sha256,
        "--model", str(model),
        "--model-sha256", model_sha256,
        "--alias", alias,
        "--port", str(port),
        "--context", str(context),
        "--log", str(log_path),
        "--",
        *child_command,
    ]


def _start_owned(command: list[str], stdout_path: Path, stderr_path: Path,
                 env: dict[str, str]) -> tuple[subprocess.Popen, Any, Any]:
    out_fd = os.open(
        stdout_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
        0o600,
    )
    err_fd = os.open(
        stderr_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
        0o600,
    )
    out = os.fdopen(out_fd, "wb", closefd=True)
    err = os.fdopen(err_fd, "wb", closefd=True)
    try:
        proc = subprocess.Popen(
            command, stdout=out, stderr=err,
            stdin=subprocess.DEVNULL, env=env,
        )
    except Exception:
        out.close()
        err.close()
        raise
    return proc, out, err


def _wait_port_free(port: int, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if owned_llama.port_is_free(port):
                return True
        except Exception:
            pass
        time.sleep(0.1)
    return False


def _state_hash(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def run_recovery_qualification(*, enrollment_path: Path, server: Path,
                               server_sha256: str, model: Path,
                               model_sha256: str, alias: str,
                               out_dir: Path, port: int = 0,
                               context: int = 65536,
                               start_timeout: float = 120.0,
                               request_timeout: float = 120.0,
                               interrupt_max_tokens: int = 256,
                               resume_max_tokens: int = 32,
                               env: dict[str, str] | None = None,
                               require_apfs: bool = True) -> dict[str, Any]:
    if not isinstance(server_sha256, str) or HEX64.fullmatch(server_sha256) is None:
        raise RecoveryQualificationError("INVALID_SERVER_HASH")
    if not isinstance(model_sha256, str) or HEX64.fullmatch(model_sha256) is None:
        raise RecoveryQualificationError("INVALID_MODEL_HASH")
    if not isinstance(alias, str) or not alias or len(alias) > 256:
        raise RecoveryQualificationError("INVALID_ALIAS")
    if isinstance(context, bool) or not isinstance(context, int) or context < 64000:
        raise RecoveryQualificationError("INVALID_CONTEXT")
    if (
        isinstance(interrupt_max_tokens, bool)
        or not isinstance(interrupt_max_tokens, int)
        or not 1 <= interrupt_max_tokens <= 4096
        or isinstance(resume_max_tokens, bool)
        or not isinstance(resume_max_tokens, int)
        or not 1 <= resume_max_tokens <= 4096
    ):
        raise RecoveryQualificationError("INVALID_MAX_TOKENS")

    out_dir = Path(out_dir).expanduser().resolve()
    if out_dir.exists():
        raise RecoveryQualificationError("OUTPUT_DIR_EXISTS")
    out_dir.mkdir(mode=0o700, parents=False)
    if stat.S_IMODE(out_dir.stat().st_mode) != 0o700:
        raise RecoveryQualificationError("OUTPUT_DIR_MODE_INVALID")

    platform = (
        _require_apfs(out_dir)
        if require_apfs
        else {"platform": sys.platform, "filesystem": "not-qualified", "device": "", "diskutil_sha256": ""}
    )

    enrollment, tool_impl_sha, qualification_source_sha, source_hashes = (
        mac._load_enrollment(Path(enrollment_path))
    )
    enrollment_sha = hashlib.sha256(_canon(enrollment)).hexdigest()
    checkpoint_sha = _sha_file(AUG / "checkpoint_journal.py")
    probe_sha = _sha_file(Path(__file__).resolve())
    recovery_impl_sha = _sha_obj({
        "mac_tool_implementation_sha256": tool_impl_sha,
        "checkpoint_journal_sha256": checkpoint_sha,
        "recovery_probe_sha256": probe_sha,
    })
    manifest_value = {
        "schema": "haven.mac-model-request-recovery-manifest.v1",
        "enrollment_sha256": enrollment_sha,
        "qualification_source_sha256": qualification_source_sha,
        "recovery_implementation_sha256": recovery_impl_sha,
        "server_sha256": server_sha256,
        "model_artifact_sha256": model_sha256,
        "model_alias": alias,
        "context_tokens": context,
    }
    manifest_sha = _sha_obj(manifest_value)

    selected_port = _select_port(port)
    journal = out_dir / "checkpoint.jsonl"
    pid_marker = out_dir / "interrupt-child.json"
    sent_marker = out_dir / "request-sent.json"
    resume_result = out_dir / "resume-result.json"
    base_env = dict(os.environ if env is None else env)
    base_env.pop("PYTHONPATH", None)
    base_env.pop("PYTHONHOME", None)
    base_env["PYTHONNOUSERSITE"] = "1"
    base_env["NO_PROXY"] = "127.0.0.1,localhost"
    base_env["no_proxy"] = "127.0.0.1,localhost"

    first_child = [
        sys.executable, str(Path(__file__).resolve()),
        "--child-phase", "interrupt",
        "--journal", str(journal),
        "--manifest-sha256", manifest_sha,
        "--port", str(selected_port),
        "--alias", alias,
        "--pid-marker", str(pid_marker),
        "--sent-marker", str(sent_marker),
        "--max-tokens", str(interrupt_max_tokens),
    ]
    first_cmd = _owned_command(
        server=Path(server), server_sha256=server_sha256,
        model=Path(model), model_sha256=model_sha256,
        alias=alias, port=selected_port, context=context,
        log_path=out_dir / "llama-first.log",
        child_command=first_child,
    )
    first, first_out, first_err = _start_owned(
        first_cmd, out_dir / "owned-first.stdout",
        out_dir / "owned-first.stderr", base_env,
    )
    try:
        sent = _wait_marker(sent_marker, first, float(request_timeout))
        pid_value = _read_marker(pid_marker).get("pid")
        if (
            isinstance(pid_value, bool)
            or not isinstance(pid_value, int)
            or pid_value <= 1
            or sent.get("pid") != pid_value
        ):
            raise RecoveryQualificationError("CHILD_PID_INVALID")
        _verify_direct_child(pid_value, first.pid)

        competing_owner_blocked = False
        try:
            with checkpoint.RunLease(journal):
                pass
        except RuntimeError as exc:
            if "live owner" in str(exc):
                competing_owner_blocked = True
        if not competing_owner_blocked:
            raise RecoveryQualificationError("COMPETING_OWNER_NOT_BLOCKED")

        os.kill(pid_value, signal.SIGKILL)
        try:
            first_rc = first.wait(timeout=30)
        except subprocess.TimeoutExpired as exc:
            first.kill()
            first.wait(timeout=5)
            raise RecoveryQualificationError("FIRST_OWNED_DID_NOT_EXIT") from exc
    finally:
        first_out.close()
        first_err.close()

    if first_rc == 0:
        raise RecoveryQualificationError("INTERRUPTED_CHILD_EXITED_ZERO")
    if not _wait_port_free(selected_port):
        raise RecoveryQualificationError("FIRST_SERVER_NOT_CLEANED")

    interrupted_scan = checkpoint.scan(journal)
    if not interrupted_scan.ok:
        raise RecoveryQualificationError("INTERRUPTED_JOURNAL_INVALID")
    interrupted_state = checkpoint.resume_plan(interrupted_scan.events)
    expected_retry = [{
        "unit": UNIT,
        "next_attempt": 2,
        "pending_model_requests": 1,
        "uncertain_replay_safe_tools": 0,
    }]
    if (
        interrupted_state.get("retryable_units") != expected_retry
        or interrupted_state.get("blocked_units") != []
    ):
        raise RecoveryQualificationError("INTERRUPTED_STATE_NOT_RETRYABLE")

    try:
        with checkpoint.RunLease(journal):
            lease_reacquired = True
    except RuntimeError as exc:
        raise RecoveryQualificationError("LEASE_NOT_RELEASED_AFTER_KILL") from exc

    second_child = [
        sys.executable, str(Path(__file__).resolve()),
        "--child-phase", "resume",
        "--journal", str(journal),
        "--manifest-sha256", manifest_sha,
        "--port", str(selected_port),
        "--alias", alias,
        "--result", str(resume_result),
        "--max-tokens", str(resume_max_tokens),
    ]
    second_cmd = _owned_command(
        server=Path(server), server_sha256=server_sha256,
        model=Path(model), model_sha256=model_sha256,
        alias=alias, port=selected_port, context=context,
        log_path=out_dir / "llama-resume.log",
        child_command=second_child,
    )
    second, second_out, second_err = _start_owned(
        second_cmd, out_dir / "owned-resume.stdout",
        out_dir / "owned-resume.stderr", base_env,
    )
    try:
        try:
            second_rc = second.wait(timeout=max(180.0, float(request_timeout) + 60.0))
        except subprocess.TimeoutExpired as exc:
            second.kill()
            second.wait(timeout=5)
            raise RecoveryQualificationError("RESUME_OWNED_TIMEOUT") from exc
    finally:
        second_out.close()
        second_err.close()
    if second_rc != 0:
        raise RecoveryQualificationError("RESUME_OWNED_NONZERO")
    if not _wait_port_free(selected_port):
        raise RecoveryQualificationError("RESUME_SERVER_NOT_CLEANED")
    if not resume_result.is_file():
        raise RecoveryQualificationError("RESUME_RESULT_MISSING")

    child_result = mac._read_private_json(resume_result, CHILD_RESULT_SCHEMA)
    final_scan = checkpoint.scan(journal)
    if not final_scan.ok or final_scan.torn_tail:
        raise RecoveryQualificationError("FINAL_JOURNAL_INVALID")
    final_state = checkpoint.resume_plan(final_scan.events)
    if (
        final_state.get("run_completed") is not True
        or final_state.get("completed_units") != [UNIT]
        or final_state.get("retryable_units") != []
        or final_state.get("blocked_units") != []
        or final_state.get("failed_units") != []
    ):
        raise RecoveryQualificationError("FINAL_STATE_INVALID")

    receipt = {
        "schema": SCHEMA,
        "classification": "development",
        "status": "pass",
        "errors": [],
        "platform": platform,
        "enrollment_sha256": enrollment_sha,
        "tool_implementation_sha256": tool_impl_sha,
        "qualification_source_sha256": qualification_source_sha,
        "checkpoint_journal_sha256": checkpoint_sha,
        "recovery_probe_sha256": probe_sha,
        "recovery_implementation_sha256": recovery_impl_sha,
        "source_hashes": source_hashes,
        "manifest_sha256": manifest_sha,
        "server_sha256": server_sha256,
        "model_artifact_sha256": model_sha256,
        "model_alias": alias,
        "context_tokens": context,
        "loopback_port": selected_port,
        "request_sent_before_kill": True,
        "request_sha256": sent.get("request_sha256"),
        "first_owned_exit": first_rc,
        "sigkill_sent": True,
        "competing_owner_blocked": competing_owner_blocked,
        "lease_reacquired_after_kill": lease_reacquired,
        "interrupted_state_sha256": _state_hash(interrupted_state),
        "interrupted_state": interrupted_state,
        "second_owned_exit": second_rc,
        "response_sha256": child_result.get("response_sha256"),
        "final_state": final_state,
        "journal_sha256": _sha_file(journal),
        "server_side_hang_proven": False,
    }
    receipt["receipt_sha256"] = _sha_obj(receipt)
    _write_private_json(out_dir / "recovery-qualification.json", receipt)
    return receipt


def _child_main(args) -> int:
    if args.child_phase == "interrupt":
        return _child_interrupt(
            journal=args.journal,
            manifest_sha256=args.manifest_sha256,
            port=args.port,
            alias=args.alias,
            pid_marker=args.pid_marker,
            sent_marker=args.sent_marker,
            max_tokens=args.max_tokens,
        )
    if args.child_phase == "resume":
        return _child_resume(
            journal=args.journal,
            manifest_sha256=args.manifest_sha256,
            port=args.port,
            alias=args.alias,
            result_path=args.result,
            max_tokens=args.max_tokens,
        )
    raise RecoveryQualificationError("INVALID_CHILD_PHASE")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--child-phase", choices=["interrupt", "resume"])
    p.add_argument("--journal", type=Path)
    p.add_argument("--manifest-sha256")
    p.add_argument("--pid-marker", type=Path)
    p.add_argument("--sent-marker", type=Path)
    p.add_argument("--result", type=Path)
    p.add_argument("--max-tokens", type=int, default=32)

    p.add_argument("--enrollment", type=Path)
    p.add_argument("--server", type=Path)
    p.add_argument("--server-sha256")
    p.add_argument("--model", type=Path)
    p.add_argument("--model-sha256")
    p.add_argument("--alias")
    p.add_argument("--port", type=int, default=0)
    p.add_argument("--context", type=int, default=65536)
    p.add_argument("--out-dir", type=Path)
    p.add_argument("--start-timeout", type=float, default=120.0)
    p.add_argument("--request-timeout", type=float, default=120.0)
    args = p.parse_args(argv)

    if args.child_phase:
        for name in ("journal", "manifest_sha256", "alias"):
            if getattr(args, name) is None:
                p.error(f"--{name.replace('_','-')} is required in child mode")
        if not isinstance(args.manifest_sha256, str) or HEX64.fullmatch(args.manifest_sha256) is None:
            p.error("invalid --manifest-sha256")
        if args.child_phase == "interrupt" and (
            args.pid_marker is None or args.sent_marker is None
        ):
            p.error("--pid-marker and --sent-marker are required")
        if args.child_phase == "resume" and args.result is None:
            p.error("--result is required")
        return _child_main(args)

    required = {
        "enrollment": args.enrollment,
        "server": args.server,
        "server_sha256": args.server_sha256,
        "model": args.model,
        "model_sha256": args.model_sha256,
        "alias": args.alias,
        "out_dir": args.out_dir,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        p.error("missing required arguments: " + ",".join(missing))

    result = run_recovery_qualification(
        enrollment_path=args.enrollment,
        server=args.server,
        server_sha256=args.server_sha256,
        model=args.model,
        model_sha256=args.model_sha256,
        alias=args.alias,
        out_dir=args.out_dir,
        port=args.port,
        context=args.context,
        start_timeout=args.start_timeout,
        request_timeout=args.request_timeout,
    )
    print(json.dumps({
        "schema": result["schema"],
        "status": result["status"],
        "receipt_sha256": result["receipt_sha256"],
        "request_sent_before_kill": result["request_sent_before_kill"],
        "competing_owner_blocked": result["competing_owner_blocked"],
        "lease_reacquired_after_kill": result["lease_reacquired_after_kill"],
        "server_side_hang_proven": result["server_side_hang_proven"],
        "out_dir": str(args.out_dir),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
