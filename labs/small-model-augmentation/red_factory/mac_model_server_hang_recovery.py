#!/usr/bin/env python3
"""Injected owned-server hang recovery qualification for #215 × #223.

Evidence-only development tooling. This closes the stronger recovery case that
mac_model_request_recovery.py deliberately does not claim.

The probe:
1. launches the exact enrolled local model through owned_llama;
2. starts one replay-safe model request and establishes its TCP connection;
3. SIGSTOPs the exact launcher-owned listener PID and proves OS state "T";
4. only then lets the child send the /v1/chat/completions request bytes;
5. proves the request has no response while that owned server remains stopped;
6. proves the checkpoint RunLease still blocks a competing live owner;
7. SIGKILLs the interrupted client and tears down the stopped owned server;
8. proves #223 sees one retryable pending model request and releases the lease;
9. launches the same admitted server/model again, records run_resumed, retries,
   commits the real response hash, and completes the unit/run.

The hang is intentionally injected with SIGSTOP. The receipt may prove an
injected server-side hang; it MUST NOT be described as a naturally occurring
llama.cpp/model hang.
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
import stat
import subprocess
import sys
import time
from typing import Any, Callable

AUG = Path(__file__).resolve().parents[1]
RED = Path(__file__).resolve().parent
if str(AUG) not in sys.path:
    sys.path.insert(0, str(AUG))
if str(RED) not in sys.path:
    sys.path.insert(0, str(RED))

import checkpoint_journal as checkpoint
import mac_case_qualification as mac
import mac_model_request_recovery as recovery
import owned_llama
from local_runner import _write_private_json

SCHEMA = "haven.mac-model-server-hang-recovery.v1"
CHILD_SCHEMA = "haven.mac-model-server-hang-child.v1"
HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


class ServerHangQualificationError(RuntimeError):
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


def _read_private_marker(path: Path) -> dict[str, Any]:
    try:
        return recovery._read_marker(Path(path))
    except recovery.RecoveryQualificationError as exc:
        raise ServerHangQualificationError(exc.code) from exc


def _wait_marker(path: Path, process: subprocess.Popen, timeout: float,
                 code: str) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return _read_private_marker(path)
        if process.poll() is not None:
            raise ServerHangQualificationError(code + "_CHILD_EXITED")
        time.sleep(0.02)
    raise ServerHangQualificationError(code + "_TIMEOUT")


def _wait_for_go(path: Path, timeout: float = 120.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            _read_private_marker(path)
            return
        time.sleep(0.01)
    raise ServerHangQualificationError("GO_MARKER_TIMEOUT")


def _stopped_state(pid: int) -> str:
    try:
        cp = subprocess.run(
            ["ps", "-o", "state=", "-p", str(pid)],
            text=True, capture_output=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ServerHangQualificationError("SERVER_STATE_PROBE_FAILED") from exc
    state = cp.stdout.strip() if cp.returncode == 0 else ""
    if not state or not state.startswith("T"):
        raise ServerHangQualificationError("OWNED_SERVER_NOT_STOPPED")
    return state


def _child_hang_request(*, journal: Path, manifest_sha256: str, port: int,
                        alias: str, ready_marker: Path, go_marker: Path,
                        sent_marker: Path, response_marker: Path,
                        max_tokens: int) -> int:
    body = recovery._request_body(alias, max_tokens)
    j = checkpoint.Journal(
        journal, recovery.RUN_ID, manifest_sha256, fsync=True,
    )
    with j.owned(resume=False):
        j.append("unit_started", recovery.UNIT, 1)
        j.append(
            "model_request_started", recovery.UNIT, 1,
            op_id="model-a1", replay_safe=True,
            payload_sha256=hashlib.sha256(body).hexdigest(),
        )
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
        try:
            # Establish TCP while the admitted server is healthy, but send no
            # HTTP request bytes until the parent has proven SIGSTOP state.
            conn.connect()
            recovery._write_marker(ready_marker, {
                "pid": os.getpid(),
                "request_sha256": hashlib.sha256(body).hexdigest(),
                "connection_established": True,
            })
            _wait_for_go(go_marker)
            conn.putrequest("POST", "/v1/chat/completions")
            conn.putheader("Content-Type", "application/json")
            conn.putheader("Content-Length", str(len(body)))
            conn.endheaders()
            conn.send(body)
            recovery._write_marker(sent_marker, {
                "pid": os.getpid(),
                "request_sha256": hashlib.sha256(body).hexdigest(),
                "bytes_sent": len(body),
            })

            # This call must remain blocked while the exact listener process is
            # stopped. If any response arrives, expose only its hash and fail.
            response = conn.getresponse()
            raw = response.read(8 * 1024 * 1024 + 1)
            recovery._write_marker(response_marker, {
                "http_status": response.status,
                "response_sha256": hashlib.sha256(raw).hexdigest(),
                "response_bytes": len(raw),
            })
            return 92
        finally:
            conn.close()


def _base_env(env: dict[str, str] | None) -> dict[str, str]:
    value = dict(os.environ if env is None else env)
    value.pop("PYTHONPATH", None)
    value.pop("PYTHONHOME", None)
    value["PYTHONNOUSERSITE"] = "1"
    value["NO_PROXY"] = "127.0.0.1,localhost"
    value["no_proxy"] = "127.0.0.1,localhost"
    return value


def _spawn(argv: list[str], env: dict[str, str]) -> subprocess.Popen:
    try:
        return subprocess.Popen(
            argv, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=env, start_new_session=True,
        )
    except OSError as exc:
        raise ServerHangQualificationError("CHILD_START_FAILED") from exc


def _kill_process_group(proc: subprocess.Popen) -> int:
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except OSError:
                pass
    try:
        return proc.wait(timeout=5)
    except subprocess.TimeoutExpired as exc:
        raise ServerHangQualificationError("CHILD_KILL_TIMEOUT") from exc


def run_server_hang_recovery_qualification(
    *,
    enrollment_path: Path,
    server: Path,
    server_sha256: str,
    model: Path,
    model_sha256: str,
    alias: str,
    out_dir: Path,
    port: int = 0,
    context: int = 65536,
    start_timeout: float = 120.0,
    request_timeout: float = 120.0,
    hang_observation_seconds: float = 0.5,
    interrupt_max_tokens: int = 64,
    resume_max_tokens: int = 16,
    env: dict[str, str] | None = None,
    require_apfs: bool = True,
    owner_probe: Callable[[int, int | None], set[int]] | None = None,
) -> dict[str, Any]:
    if not isinstance(server_sha256, str) or HEX64.fullmatch(server_sha256) is None:
        raise ServerHangQualificationError("INVALID_SERVER_HASH")
    if not isinstance(model_sha256, str) or HEX64.fullmatch(model_sha256) is None:
        raise ServerHangQualificationError("INVALID_MODEL_HASH")
    if not isinstance(alias, str) or not alias or len(alias) > 256:
        raise ServerHangQualificationError("INVALID_ALIAS")
    if isinstance(context, bool) or not isinstance(context, int) or context < 64000:
        raise ServerHangQualificationError("INVALID_CONTEXT")
    if (
        isinstance(hang_observation_seconds, bool)
        or not isinstance(hang_observation_seconds, (int, float))
        or not 0.1 <= float(hang_observation_seconds) <= 10.0
    ):
        raise ServerHangQualificationError("INVALID_HANG_OBSERVATION")
    for value in (interrupt_max_tokens, resume_max_tokens):
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 4096:
            raise ServerHangQualificationError("INVALID_MAX_TOKENS")

    out_dir = Path(out_dir).expanduser().resolve()
    if out_dir.exists():
        raise ServerHangQualificationError("OUTPUT_DIR_EXISTS")
    out_dir.mkdir(mode=0o700, parents=False)
    if stat.S_IMODE(out_dir.stat().st_mode) != 0o700:
        raise ServerHangQualificationError("OUTPUT_DIR_MODE_INVALID")

    platform = (
        recovery._require_apfs(out_dir)
        if require_apfs
        else {
            "platform": sys.platform, "filesystem": "not-qualified",
            "device": "", "diskutil_sha256": "",
        }
    )
    enrollment, tool_impl_sha, qualification_source_sha, source_hashes = (
        mac._load_enrollment(Path(enrollment_path))
    )
    enrollment_sha = hashlib.sha256(_canon(enrollment)).hexdigest()

    checkpoint_sha = _sha_file(AUG / "checkpoint_journal.py")
    base_probe_sha = _sha_file(RED / "mac_model_request_recovery.py")
    hang_probe_sha = _sha_file(Path(__file__).resolve())
    owned_llama_sha = _sha_file(AUG / "owned_llama.py")
    recovery_impl_sha = _sha_obj({
        "mac_tool_implementation_sha256": tool_impl_sha,
        "checkpoint_journal_sha256": checkpoint_sha,
        "base_recovery_probe_sha256": base_probe_sha,
        "server_hang_probe_sha256": hang_probe_sha,
        "owned_llama_sha256": owned_llama_sha,
    })
    manifest_value = {
        "schema": "haven.mac-model-server-hang-recovery-manifest.v1",
        "enrollment_sha256": enrollment_sha,
        "qualification_source_sha256": qualification_source_sha,
        "recovery_implementation_sha256": recovery_impl_sha,
        "server_sha256": server_sha256,
        "model_artifact_sha256": model_sha256,
        "model_alias": alias,
        "context_tokens": context,
        "hang_injection": "SIGSTOP",
    }
    manifest_sha = _sha_obj(manifest_value)

    selected_port = recovery._select_port(port)
    journal = out_dir / "checkpoint.jsonl"
    ready_marker = out_dir / "request-ready.json"
    go_marker = out_dir / "request-go.json"
    sent_marker = out_dir / "request-sent.json"
    response_marker = out_dir / "unexpected-response.json"
    resume_result = out_dir / "resume-result.json"
    base_env = _base_env(env)

    lease = None
    child = None
    first_child_rc = None
    stopped_state = None
    request_sent = None
    competing_owner_blocked = False
    try:
        lease = owned_llama.launch(
            str(server), server_sha256, str(model), model_sha256,
            alias=alias, port=selected_port, context_tokens=context,
            log_path=str(out_dir / "llama-stopped.log"),
            start_timeout=start_timeout, owner_probe=owner_probe,
        )
        child = _spawn([
            sys.executable, str(Path(__file__).resolve()),
            "--child-phase", "hang-request",
            "--journal", str(journal),
            "--manifest-sha256", manifest_sha,
            "--port", str(selected_port),
            "--alias", alias,
            "--ready-marker", str(ready_marker),
            "--go-marker", str(go_marker),
            "--sent-marker", str(sent_marker),
            "--response-marker", str(response_marker),
            "--max-tokens", str(interrupt_max_tokens),
        ], base_env)

        ready = _wait_marker(
            ready_marker, child, float(request_timeout), "REQUEST_READY"
        )
        if ready.get("connection_established") is not True:
            raise ServerHangQualificationError("REQUEST_CONNECTION_NOT_ESTABLISHED")

        # The lease PID is the exact owned/listening server process.
        lease.guard()
        os.kill(lease.process.pid, signal.SIGSTOP)
        stopped_state = _stopped_state(lease.process.pid)

        recovery._write_marker(go_marker, {"server_stopped": True})
        request_sent = _wait_marker(
            sent_marker, child, float(request_timeout), "REQUEST_SENT"
        )
        if (
            request_sent.get("request_sha256") != ready.get("request_sha256")
            or not isinstance(request_sent.get("bytes_sent"), int)
            or request_sent["bytes_sent"] <= 0
        ):
            raise ServerHangQualificationError("REQUEST_SENT_MARKER_INVALID")

        # Re-prove the server is still stopped *after* request bytes were sent.
        _stopped_state(lease.process.pid)
        time.sleep(float(hang_observation_seconds))
        if child.poll() is not None:
            raise ServerHangQualificationError("REQUEST_DID_NOT_BLOCK_ON_STOPPED_SERVER")
        if response_marker.exists():
            raise ServerHangQualificationError("RESPONSE_ARRIVED_WHILE_SERVER_STOPPED")

        try:
            with checkpoint.RunLease(journal):
                pass
        except RuntimeError as exc:
            if "live owner" in str(exc):
                competing_owner_blocked = True
        if not competing_owner_blocked:
            raise ServerHangQualificationError("COMPETING_OWNER_NOT_BLOCKED")

        first_child_rc = _kill_process_group(child)
        child = None
        if first_child_rc == 0:
            raise ServerHangQualificationError("INTERRUPTED_CHILD_EXITED_ZERO")

        lease.stop(timeout=1.0)
        lease = None
    finally:
        if child is not None and child.poll() is None:
            _kill_process_group(child)
        if lease is not None:
            lease.stop(timeout=1.0)

    if not recovery._wait_port_free(selected_port):
        raise ServerHangQualificationError("STOPPED_SERVER_NOT_CLEANED")

    interrupted_scan = checkpoint.scan(journal)
    if not interrupted_scan.ok or interrupted_scan.torn_tail:
        raise ServerHangQualificationError("INTERRUPTED_JOURNAL_INVALID")
    interrupted_state = checkpoint.resume_plan(interrupted_scan.events)
    expected_retry = [{
        "unit": recovery.UNIT,
        "next_attempt": 2,
        "pending_model_requests": 1,
        "uncertain_replay_safe_tools": 0,
    }]
    if (
        interrupted_state.get("retryable_units") != expected_retry
        or interrupted_state.get("blocked_units") != []
    ):
        raise ServerHangQualificationError("INTERRUPTED_STATE_NOT_RETRYABLE")

    try:
        with checkpoint.RunLease(journal):
            lease_reacquired = True
    except RuntimeError as exc:
        raise ServerHangQualificationError("LEASE_NOT_RELEASED_AFTER_HANG") from exc

    second_lease = None
    try:
        second_lease = owned_llama.launch(
            str(server), server_sha256, str(model), model_sha256,
            alias=alias, port=selected_port, context_tokens=context,
            log_path=str(out_dir / "llama-resume.log"),
            start_timeout=start_timeout, owner_probe=owner_probe,
        )
        resume_child = _spawn([
            sys.executable, str(RED / "mac_model_request_recovery.py"),
            "--child-phase", "resume",
            "--journal", str(journal),
            "--manifest-sha256", manifest_sha,
            "--port", str(selected_port),
            "--alias", alias,
            "--result", str(resume_result),
            "--max-tokens", str(resume_max_tokens),
        ], base_env)
        try:
            second_rc = resume_child.wait(
                timeout=max(180.0, float(request_timeout) + 60.0)
            )
        except subprocess.TimeoutExpired as exc:
            _kill_process_group(resume_child)
            raise ServerHangQualificationError("RESUME_CHILD_TIMEOUT") from exc
        if second_rc != 0:
            raise ServerHangQualificationError("RESUME_CHILD_NONZERO")
        second_lease.guard()
    finally:
        if second_lease is not None:
            second_lease.stop(timeout=2.0)

    if not recovery._wait_port_free(selected_port):
        raise ServerHangQualificationError("RESUME_SERVER_NOT_CLEANED")
    if not resume_result.is_file():
        raise ServerHangQualificationError("RESUME_RESULT_MISSING")
    child_result = mac._read_private_json(
        resume_result, recovery.CHILD_RESULT_SCHEMA
    )

    final_scan = checkpoint.scan(journal)
    if not final_scan.ok or final_scan.torn_tail:
        raise ServerHangQualificationError("FINAL_JOURNAL_INVALID")
    final_state = checkpoint.resume_plan(final_scan.events)
    if (
        final_state.get("run_completed") is not True
        or final_state.get("completed_units") != [recovery.UNIT]
        or final_state.get("retryable_units") != []
        or final_state.get("blocked_units") != []
        or final_state.get("failed_units") != []
    ):
        raise ServerHangQualificationError("FINAL_STATE_INVALID")

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
        "base_recovery_probe_sha256": base_probe_sha,
        "server_hang_probe_sha256": hang_probe_sha,
        "owned_llama_sha256": owned_llama_sha,
        "recovery_implementation_sha256": recovery_impl_sha,
        "source_hashes": source_hashes,
        "manifest_sha256": manifest_sha,
        "server_sha256": server_sha256,
        "model_artifact_sha256": model_sha256,
        "model_alias": alias,
        "context_tokens": context,
        "loopback_port": selected_port,
        "hang_injection": "SIGSTOP",
        "server_side_hang_proven": True,
        "natural_server_hang_proven": False,
        "owned_listener_stopped_state": stopped_state,
        "connection_established_before_stop": True,
        "request_sent_while_server_stopped": True,
        "request_sha256": request_sent.get("request_sha256"),
        "response_absent_during_stop_observation": True,
        "hang_observation_seconds": float(hang_observation_seconds),
        "first_child_exit": first_child_rc,
        "competing_owner_blocked": competing_owner_blocked,
        "lease_reacquired_after_hang": lease_reacquired,
        "interrupted_state_sha256": recovery._state_hash(interrupted_state),
        "interrupted_state": interrupted_state,
        "second_child_exit": second_rc,
        "response_sha256": child_result.get("response_sha256"),
        "final_state": final_state,
        "journal_sha256": _sha_file(journal),
    }
    receipt["receipt_sha256"] = _sha_obj(receipt)
    _write_private_json(out_dir / "server-hang-recovery.json", receipt)
    return receipt


def _child_main(args: argparse.Namespace) -> int:
    if args.child_phase != "hang-request":
        raise ServerHangQualificationError("INVALID_CHILD_PHASE")
    return _child_hang_request(
        journal=args.journal,
        manifest_sha256=args.manifest_sha256,
        port=args.port,
        alias=args.alias,
        ready_marker=args.ready_marker,
        go_marker=args.go_marker,
        sent_marker=args.sent_marker,
        response_marker=args.response_marker,
        max_tokens=args.max_tokens,
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--child-phase", choices=["hang-request"])
    p.add_argument("--journal", type=Path)
    p.add_argument("--manifest-sha256")
    p.add_argument("--ready-marker", type=Path)
    p.add_argument("--go-marker", type=Path)
    p.add_argument("--sent-marker", type=Path)
    p.add_argument("--response-marker", type=Path)
    p.add_argument("--max-tokens", type=int, default=64)

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
    p.add_argument("--hang-observation-seconds", type=float, default=0.5)
    args = p.parse_args(argv)

    if args.child_phase:
        required = {
            "journal": args.journal,
            "manifest_sha256": args.manifest_sha256,
            "alias": args.alias,
            "ready_marker": args.ready_marker,
            "go_marker": args.go_marker,
            "sent_marker": args.sent_marker,
            "response_marker": args.response_marker,
        }
        missing = [k for k, v in required.items() if v is None]
        if missing:
            p.error("missing child arguments: " + ",".join(missing))
        if not isinstance(args.manifest_sha256, str) or HEX64.fullmatch(args.manifest_sha256) is None:
            p.error("invalid --manifest-sha256")
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
    missing = [k for k, v in required.items() if v is None]
    if missing:
        p.error("missing required arguments: " + ",".join(missing))

    result = run_server_hang_recovery_qualification(
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
        hang_observation_seconds=args.hang_observation_seconds,
    )
    print(json.dumps({
        "schema": result["schema"],
        "status": result["status"],
        "receipt_sha256": result["receipt_sha256"],
        "hang_injection": result["hang_injection"],
        "server_side_hang_proven": result["server_side_hang_proven"],
        "natural_server_hang_proven": result["natural_server_hang_proven"],
        "request_sent_while_server_stopped": result[
            "request_sent_while_server_stopped"
        ],
        "lease_reacquired_after_hang": result["lease_reacquired_after_hang"],
        "out_dir": str(args.out_dir),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
