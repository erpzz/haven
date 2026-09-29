"""New IP-01 Windows laboratory runtime; no SQLite or browser authority.

Windows 10+ JOB_LIST makes membership atomic with CreateProcess. Job handles
are not inherited. Closing the last handle (including parent death) kills the
whole job. This is lifecycle containment, not an adversarial security sandbox.
"""
from __future__ import annotations

import asyncio
import ctypes as C
from ctypes import wintypes as W
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import uuid

MAX_METADATA = 64 * 1024
MAX_OUTPUT = 256 * 1024
MAX_FRAME = 12 * 1024 * 1024
STOP_TARGET_SECONDS = 3.0  # Probe/fault protocol freezes this; never adapt on failure.
JOB_FIELDS = {"job_id", "request_id", "request_digest", "attempt_id", "lease_fence",
              "cancel_epoch", "route", "deadline_utc", "max_elapsed_ms", "reservation_id"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def context_digest(context):
    """APP may carry its digest alongside the sealed context it identifies."""
    actual = digest({k: v for k, v in context.items() if k != "context_digest"})
    if context.get("context_digest", actual) != actual:
        raise ValueError("sealed context digest differs")
    return actual


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def strict_json(data):
    return json.loads(data, object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def read_frame(stream, limit=MAX_FRAME):
    def exact(n):
        parts = bytearray()
        while len(parts) < n:
            block = stream.read(n - len(parts))
            if not block:
                raise EOFError("incomplete IPC")
            parts.extend(block)
        return bytes(parts)
    size = struct.unpack("!I", exact(4))[0]
    if not 0 < size <= limit:
        raise ValueError("IPC size limit")
    value = strict_json(exact(size))
    if not isinstance(value, dict):
        raise ValueError("IPC object required")
    return value


def write_frame(stream, value, limit=MAX_FRAME):
    raw = canonical(value)
    if not 0 < len(raw) <= limit:
        raise ValueError("IPC size limit")
    stream.write(struct.pack("!I", len(raw)) + raw)
    stream.flush()


def private_environment(runtime_dir):
    """Construct from allowlist, never filter a copy of ambient credentials."""
    root = Path(runtime_dir).resolve()
    for name in ("tmp", "home", "cache"):
        (root / name).mkdir(parents=True, exist_ok=True)
    system = os.environ.get("SystemRoot", r"C:\Windows")
    return {"SystemRoot": system, "WINDIR": system,
            "PATH": str(Path(system) / "System32"),
            "TEMP": str(root / "tmp"), "TMP": str(root / "tmp"),
            "HOME": str(root / "home"), "USERPROFILE": str(root / "home"),
            "LOCALAPPDATA": str(root / "home" / "AppData" / "Local"),
            "APPDATA": str(root / "home" / "AppData" / "Roaming"),
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}


if os.name == "nt":
    K = C.WinDLL("kernel32", use_last_error=True)
    SIZE = C.c_size_t

    class SECURITY(C.Structure):
        _fields_ = [("length", W.DWORD), ("descriptor", W.LPVOID), ("inherit", W.BOOL)]

    class STARTUP(C.Structure):
        _fields_ = [("cb", W.DWORD), ("reserved", W.LPWSTR), ("desktop", W.LPWSTR),
                    ("title", W.LPWSTR)] + [(n, W.DWORD) for n in
                    ("x", "y", "cx", "cy", "charsx", "charsy", "fill", "flags")] + [
                    ("show", W.WORD), ("reserved_size", W.WORD), ("reserved_ptr", W.LPVOID),
                    ("stdin", W.HANDLE), ("stdout", W.HANDLE), ("stderr", W.HANDLE)]

    class STARTUPEX(C.Structure):
        _fields_ = [("startup", STARTUP), ("attributes", W.LPVOID)]

    class PROCESS(C.Structure):
        _fields_ = [("process", W.HANDLE), ("thread", W.HANDLE),
                    ("pid", W.DWORD), ("tid", W.DWORD)]

    class BASIC_LIMIT(C.Structure):
        _fields_ = [("per_process_time", C.c_longlong), ("per_job_time", C.c_longlong),
                    ("flags", W.DWORD), ("minimum", SIZE), ("maximum", SIZE),
                    ("active", W.DWORD), ("affinity", SIZE), ("priority", W.DWORD),
                    ("scheduling", W.DWORD)]

    class IO_COUNTERS(C.Structure):
        _fields_ = [(n, C.c_ulonglong) for n in ("read_ops", "write_ops", "other_ops",
                                                  "read_bytes", "write_bytes", "other_bytes")]

    class EXTENDED_LIMIT(C.Structure):
        _fields_ = [("basic", BASIC_LIMIT), ("io", IO_COUNTERS), ("process_memory", SIZE),
                    ("job_memory", SIZE), ("peak_process_memory", SIZE), ("peak_job_memory", SIZE)]

    class ACCOUNTING(C.Structure):
        _fields_ = [(n, C.c_longlong) for n in ("user", "kernel", "period_user", "period_kernel")] + [
                    (n, W.DWORD) for n in ("faults", "total", "active", "terminated")]

    def _api(name, args, restype=W.BOOL):
        fn = getattr(K, name)
        fn.argtypes, fn.restype = args, restype
        return fn

    _api("CreateJobObjectW", [W.LPVOID, W.LPCWSTR], W.HANDLE)
    _api("SetInformationJobObject", [W.HANDLE, C.c_int, W.LPVOID, W.DWORD])
    _api("QueryInformationJobObject", [W.HANDLE, C.c_int, W.LPVOID, W.DWORD, W.LPVOID])
    _api("TerminateJobObject", [W.HANDLE, W.UINT])
    _api("CloseHandle", [W.HANDLE])
    _api("CreatePipe", [C.POINTER(W.HANDLE), C.POINTER(W.HANDLE), C.POINTER(SECURITY), W.DWORD])
    _api("SetHandleInformation", [W.HANDLE, W.DWORD, W.DWORD])
    _api("InitializeProcThreadAttributeList", [W.LPVOID, W.DWORD, W.DWORD, C.POINTER(SIZE)])
    _api("UpdateProcThreadAttribute", [W.LPVOID, W.DWORD, SIZE, W.LPVOID, SIZE, W.LPVOID, W.LPVOID])
    _api("DeleteProcThreadAttributeList", [W.LPVOID], None)
    _api("CreateProcessW", [W.LPCWSTR, W.LPWSTR, W.LPVOID, W.LPVOID, W.BOOL, W.DWORD,
                           W.LPVOID, W.LPCWSTR, W.LPVOID, C.POINTER(PROCESS)])
    _api("WaitForSingleObject", [W.HANDLE, W.DWORD], W.DWORD)
    _api("GetExitCodeProcess", [W.HANDLE, C.POINTER(W.DWORD)])
    _api("GetProcessTimes", [W.HANDLE] + [C.POINTER(W.FILETIME)] * 4)
    _api("OpenProcess", [W.DWORD, W.BOOL, W.DWORD], W.HANDLE)
    _api("GetCurrentProcess", [], W.HANDLE)


def _check(ok):
    if not ok:
        raise C.WinError(C.get_last_error())
    return ok


def boot_id():
    if os.name != "nt":
        raise RuntimeError("Windows runtime required")
    # SYSTEM_BOOT_ENVIRONMENT_INFORMATION begins with the current boot GUID.
    ntdll = C.WinDLL("ntdll")
    fn = ntdll.NtQuerySystemInformation
    fn.argtypes = [C.c_int, W.LPVOID, W.ULONG, W.LPVOID]
    fn.restype = C.c_long
    data = C.create_string_buffer(32)
    if fn(90, data, len(data), None) < 0:
        raise RuntimeError("boot identity unavailable")
    return str(uuid.UUID(bytes_le=data.raw[:16]))


def process_birth(handle):
    stamps = [W.FILETIME() for _ in range(4)]
    _check(K.GetProcessTimes(handle, *(C.byref(x) for x in stamps)))
    return str((stamps[0].dwHighDateTime << 32) | stamps[0].dwLowDateTime)


def identity_alive(identity):
    """Read-only PID lookup plus exact birth/boot match; never used to kill."""
    if identity["boot_id"] != boot_id():
        return False
    h = K.OpenProcess(0x1000 | 0x100000, False, identity["pid"])
    if not h:
        error = C.get_last_error()
        if error == 87:
            return False
        raise OSError(error, "cannot reconcile prior process")
    try:
        return process_birth(h) == identity["process_birth"] and K.WaitForSingleObject(h, 0) == 258
    finally:
        K.CloseHandle(h)


class OwnedJob:
    """Only this exact job handle can be stopped. No name/PID-tree killing."""
    def __init__(self, memory_bytes=12 * 1024**3):
        if os.name != "nt":
            raise RuntimeError("Windows Job Object unavailable")
        self.handle = _check(K.CreateJobObjectW(None, None))
        limits = EXTENDED_LIMIT()
        limits.basic.flags = 0x2000 | 0x200 | 0x8  # kill-on-close, job memory, active-process count
        limits.basic.active = 12
        limits.job_memory = memory_bytes
        try:
            _check(K.SetInformationJobObject(self.handle, 9, C.byref(limits), C.sizeof(limits)))
        except BaseException:
            self.close()
            raise
        self.processes = []

    def observation(self):
        info = ACCOUNTING()
        _check(K.QueryInformationJobObject(self.handle, 1, C.byref(info), C.sizeof(info), None))
        limits = EXTENDED_LIMIT()
        _check(K.QueryInformationJobObject(self.handle, 9, C.byref(limits), C.sizeof(limits), None))
        # Exact process IDs still in this job (for independent observers).
        data = C.create_string_buffer(8 + 128 * C.sizeof(SIZE))
        _check(K.QueryInformationJobObject(self.handle, 3, data, len(data), None))
        count = C.c_ulong.from_buffer(data, 4).value
        pids = [SIZE.from_buffer(data, 8 + i * C.sizeof(SIZE)).value for i in range(count)]
        return {"active_processes": info.active, "total_processes": info.total,
                "terminated_processes": info.terminated, "pids": pids,
                "peak_job_memory_bytes": limits.peak_job_memory}

    def terminate(self):
        _check(K.TerminateJobObject(self.handle, 0xE001))

    async def stop(self, deadline=None):
        deadline = min(deadline if deadline is not None else math.inf,
                       time.monotonic() + STOP_TARGET_SECONDS)
        self.terminate()
        while True:
            observation = self.observation()
            observation["owned_handles_signaled"] = all(p.poll() is not None for p in self.processes)
            if observation["active_processes"] == 0 and observation["owned_handles_signaled"]:
                return {"confirmed": True, **observation}
            if time.monotonic() >= deadline:
                return {"confirmed": False, **observation}
            await asyncio.sleep(0.01)

    def close(self):
        if getattr(self, "handle", None):
            K.CloseHandle(self.handle)
            self.handle = None


class OwnedProcess:
    """CreateProcess with atomic JOB_LIST + explicit inherited pipe handles."""
    def __init__(self, job, argv, *, env, cwd):
        import msvcrt
        self.handle = None
        self.stdin = self.stdout = None
        handles = []
        attr = None
        proc = PROCESS()
        try:
            sa = SECURITY(C.sizeof(SECURITY), None, True)
            r_in, w_in, r_out, w_out = (W.HANDLE() for _ in range(4))
            _check(K.CreatePipe(C.byref(r_in), C.byref(w_in), C.byref(sa), 0))
            handles += [r_in.value, w_in.value]
            _check(K.CreatePipe(C.byref(r_out), C.byref(w_out), C.byref(sa), 0))
            handles += [r_out.value, w_out.value]
            _check(K.SetHandleInformation(w_in, 1, 0))
            _check(K.SetHandleInformation(r_out, 1, 0))
            # stderr is intentionally discarded, avoiding an unbounded third pipe.
            null_file = open(os.devnull, "wb")
            null_handle = msvcrt.get_osfhandle(null_file.fileno())
            os.set_handle_inheritable(null_handle, True)
            try:
                size = SIZE()
                K.InitializeProcThreadAttributeList(None, 2, 0, C.byref(size))
                attr = C.create_string_buffer(size.value)
                _check(K.InitializeProcThreadAttributeList(attr, 2, 0, C.byref(size)))
                job_handles = (W.HANDLE * 1)(job.handle)
                pipe_handles = (W.HANDLE * 3)(r_in.value, w_out.value, null_handle)
                _check(K.UpdateProcThreadAttribute(attr, 0, 0x2000D, job_handles,
                                                   C.sizeof(job_handles), None, None))
                _check(K.UpdateProcThreadAttribute(attr, 0, 0x20002, pipe_handles,
                                                   C.sizeof(pipe_handles), None, None))
                startup = STARTUPEX()
                startup.startup.cb = C.sizeof(startup)
                startup.startup.flags = 0x100 | 1
                startup.startup.show = 0
                startup.startup.stdin, startup.startup.stdout = r_in.value, w_out.value
                startup.startup.stderr = null_handle
                startup.attributes = C.cast(attr, W.LPVOID)
                command = C.create_unicode_buffer(subprocess.list2cmdline([str(x) for x in argv]))
                environment = C.create_unicode_buffer("\0".join(f"{k}={v}" for k, v in sorted(env.items())) + "\0\0")
                _check(K.CreateProcessW(str(argv[0]), command, None, None, True,
                                       0x80000 | 0x400 | 0x08000000, environment,
                                       str(cwd), C.byref(startup), C.byref(proc)))
            finally:
                null_file.close()
            self.handle, self.pid = proc.process, proc.pid
            K.CloseHandle(proc.thread)
            self.identity = {"pid": self.pid, "process_birth": process_birth(self.handle),
                             "boot_id": boot_id()}
            for h in (r_in.value, w_out.value):
                K.CloseHandle(h)
                handles.remove(h)
            self.stdin = os.fdopen(msvcrt.open_osfhandle(w_in.value, 0), "wb", buffering=0)
            handles.remove(w_in.value)
            self.stdout = os.fdopen(msvcrt.open_osfhandle(r_out.value, os.O_RDONLY), "rb", buffering=0)
            handles.remove(r_out.value)
            job.processes.append(self)
        except BaseException:
            if proc.process:
                job.terminate()
                K.WaitForSingleObject(proc.process, int(STOP_TARGET_SECONDS * 1000))
            self.close()
            raise
        finally:
            if attr is not None:
                K.DeleteProcThreadAttributeList(attr)
            for h in handles:
                K.CloseHandle(h)

    def poll(self):
        if K.WaitForSingleObject(self.handle, 0) == 258:
            return None
        code = W.DWORD()
        _check(K.GetExitCodeProcess(self.handle, C.byref(code)))
        return code.value

    def close(self):
        for stream in (self.stdin, self.stdout):
            if stream:
                stream.close()
        if self.handle:
            K.CloseHandle(self.handle)
            self.handle = None


class Supervisor:
    def __init__(self, *, runtime_dir, admit_attempt, on_event, on_result):
        self.runtime_dir = Path(runtime_dir).resolve()
        self.admit_attempt, self.on_event, self.on_result = admit_attempt, on_event, on_result
        self.instance = str(uuid.uuid4())
        self.jobs = {}
        self.queue = asyncio.Queue(maxsize=32)
        self.task = None
        self.closed = False
        self.quarantined = False
        self.seen_prior = set()
        self.journal = None

    async def start(self):
        if self.task:
            return
        if self.closed:
            raise RuntimeError("closed supervisor cannot restart")
        directory = self.runtime_dir / "lifecycle"
        directory.mkdir(parents=True, exist_ok=True)
        # Never resume prior jobs or reuse their ids. Live/uncertain prior parent
        # holds capacity; startup does not acquire termination rights by PID.
        for path in directory.glob("*.jsonl"):
            records = [strict_json(line) for line in path.read_bytes().splitlines()]
            starts = [r for r in records if r.get("kind") == "SUPERVISOR_STARTED"]
            ended = any(r.get("kind") == "SUPERVISOR_CLOSED" and r.get("confirmed") for r in records)
            self.seen_prior.update(r["job_id"] for r in records if r.get("job_id"))
            if starts and not ended:
                try:
                    if identity_alive(starts[-1]["parent"]):
                        self.quarantined = True
                except OSError:
                    self.quarantined = True
        self.journal = open(directory / f"{self.instance}.jsonl", "xb", buffering=0)
        self._append({"kind": "SUPERVISOR_STARTED", "parent": {"pid": os.getpid(),
                      "process_birth": process_birth(K.GetCurrentProcess()), "boot_id": boot_id()},
                      "quarantined": self.quarantined})
        self.task = asyncio.create_task(self._loop(), name="ip01-runtime")

    def _append(self, record):
        self.journal.write(canonical({"observed_at": utc_now(), "supervisor_instance": self.instance,
                                      **record}) + b"\n")
        os.fsync(self.journal.fileno())

    async def _event(self, state, kind, evidence=None):
        event = {**state["identity"], "event_id": str(uuid.uuid4()), "kind": kind,
                 "observed_at": utc_now(), "evidence": evidence or {}}
        self._append(event)
        try:
            await asyncio.wait_for(self.on_event(event), 2)
        except Exception as exc:
            self._append({"kind": "EVENT_CALLBACK_UNKNOWN", "job_id": state["job"]["job_id"],
                          "exception_type": type(exc).__name__})

    async def submit(self, job):
        if not self.task or self.closed:
            raise RuntimeError("supervisor not accepting")
        job = strict_json(canonical(job))
        if set(job) != JOB_FIELDS or len(canonical(job)) > MAX_METADATA:
            raise ValueError("invalid job fields/bounds")
        for key in ("job_id", "request_id", "request_digest", "attempt_id", "reservation_id"):
            if not isinstance(job[key], str) or not 1 <= len(job[key]) <= 256:
                raise ValueError("invalid job identity")
        for key in ("lease_fence", "cancel_epoch", "max_elapsed_ms"):
            if type(job[key]) is not int or job[key] < 0:
                raise ValueError("invalid job bound")
        if job["route"] not in ("deterministic", "model") or not 0 < job["max_elapsed_ms"] <= 600000:
            raise ValueError("invalid route/deadline")
        if job["route"] == "model" and job["max_elapsed_ms"] > 120000:
            raise ValueError("model wall limit")
        deadline = datetime.fromisoformat(job["deadline_utc"].replace("Z", "+00:00"))
        if deadline.tzinfo is None:
            raise ValueError("UTC deadline required")
        remaining = min((deadline - datetime.now(timezone.utc)).total_seconds(), job["max_elapsed_ms"] / 1000)
        key = job["job_id"]
        if key in self.jobs:
            if self.jobs[key]["job"] != job:
                raise ValueError("conflicting duplicate job")
            return await self.snapshot(key)
        if key in self.seen_prior or self.quarantined:
            raise RuntimeError("runtime reconciliation required")
        if self.queue.full():
            raise RuntimeError("runtime queue full")
        state = {"job": job, "compute_state": "NOT_STARTED", "disposition": "QUEUED",
                 "deadline": time.monotonic() + max(0, remaining), "cancel": asyncio.Event(),
                 "identity": {k: job[k] for k in ("job_id", "request_id", "attempt_id", "lease_fence", "cancel_epoch")},
                 "owned_job": None, "process": None, "result_seen": False, "cleanup": None}
        state["identity"].update(worker_instance_id=str(uuid.uuid4()), pid=None, process_birth=None,
                                  boot_id=boot_id(), nonce=uuid.uuid4().hex)
        self.jobs[key] = state
        await self._event(state, "QUEUED")
        self.queue.put_nowait(state)
        return await self.snapshot(key)

    async def cancel(self, job_id, cancel_epoch, reason):
        state = self.jobs[job_id]
        if type(cancel_epoch) is not int or cancel_epoch < state["identity"]["cancel_epoch"]:
            await self._event(state, "STALE_CANCEL_REJECTED")
            return await self.snapshot(job_id)
        state["identity"]["cancel_epoch"] = cancel_epoch
        state["cancel"].set()
        if state["disposition"] == "QUEUED":
            state["disposition"] = "CANCELLED"
        if state["owned_job"] and state["compute_state"] != "STOP_CONFIRMED":
            state["compute_state"] = "STOP_REQUESTED"
            state["owned_job"].terminate()
        await self._event(state, "CANCEL_REQUESTED", {"reason": str(reason)[:160]})
        return await self.snapshot(job_id)

    async def snapshot(self, job_id):
        state = self.jobs[job_id]
        observation = None
        if state["owned_job"] and state["owned_job"].handle:
            observation = state["owned_job"].observation()
        return {"job_id": job_id, "compute_state": state["compute_state"],
                "disposition": state["disposition"], "identity": dict(state["identity"]),
                "cleanup": state["cleanup"], "observation": observation,
                "capacity_held": state["owned_job"] is not None and state["compute_state"] != "STOP_CONFIRMED",
                "runtime_quarantined": self.quarantined}

    async def _loop(self):
        while True:
            state = await self.queue.get()
            try:
                await self._execute(state)
            except Exception as exc:
                state["disposition"] = "INCONCLUSIVE"
                await self._event(state, "RUNTIME_ERROR", {"exception_type": type(exc).__name__})
            finally:
                self.queue.task_done()

    async def _execute(self, state):
        job = state["job"]
        if state["cancel"].is_set() or self.closed:
            state["disposition"] = "CANCELLED"
            await self._event(state, "NEVER_ADMITTED")
            return
        if self.quarantined or time.monotonic() >= state["deadline"]:
            state["disposition"] = "INCONCLUSIVE"
            await self._event(state, "ADMISSION_BLOCKED")
            return
        try:
            admitted = await asyncio.wait_for(self.admit_attempt(job["job_id"], job["attempt_id"],
                                              job["lease_fence"]), min(5, state["deadline"] - time.monotonic()))
        except Exception:
            admitted = {"decision": "UNKNOWN"}
        if admitted.get("decision") != "ADMITTED":
            state["disposition"] = "FAILED" if admitted.get("decision") == "DENIED" else "INCONCLUSIVE"
            await self._event(state, "ADMISSION_DENIED", {"decision": admitted.get("decision", "UNKNOWN")})
            return
        if state["cancel"].is_set() or self.closed or time.monotonic() >= state["deadline"]:
            state["disposition"] = "CANCELLED" if state["cancel"].is_set() else "INCONCLUSIVE"
            await self._event(state, "CANCELLED_BEFORE_SPAWN")
            return
        context = admitted["context"]
        vector = admitted["authority_vector"]
        if len(canonical(vector)) > MAX_METADATA:
            raise ValueError("authority metadata limit")
        if admitted.get("job") != job:
            raise ValueError("admission job differs")
        context_digest(context)
        owned = OwnedJob()
        state["owned_job"] = owned
        io_tasks = []
        try:
            backend = None
            if job["route"] == "model":
                from .model_adapter import ModelAdapter
                adapter = ModelAdapter(self.runtime_dir)
                backend = await adapter.start_for_attempt(owned, admitted, state["deadline"], state["cancel"])
                if state["cancel"].is_set() or self.closed:
                    raise asyncio.CancelledError()
            proc = OwnedProcess(owned, [sys._base_executable, "-I", "-B", str(Path(__file__).with_name("worker.py"))],
                                env=private_environment(self.runtime_dir), cwd=self.runtime_dir)
            state["process"] = proc
            state["identity"].update(proc.identity)
            state["compute_state"] = "RUNNING"
            await self._event(state, "PROCESS_STARTED", {"job_observation": owned.observation()})
            request = {"identity": dict(state["identity"]), "job": job, "context": context,
                       "context_digest": context_digest(context), "model_identity": admitted.get("model_identity"),
                       "backend": backend}
            writer = asyncio.create_task(asyncio.to_thread(write_frame, proc.stdin, request))
            reader = asyncio.create_task(asyncio.to_thread(read_frame, proc.stdout, MAX_OUTPUT + MAX_METADATA))
            io_tasks = [writer, reader]
            while not reader.done():
                if state["cancel"].is_set() or self.closed or time.monotonic() >= state["deadline"]:
                    state["disposition"] = "CANCELLED" if state["cancel"].is_set() else "INCONCLUSIVE"
                    break
                if writer.done() and writer.exception():
                    raise writer.exception()
                await asyncio.sleep(0.01)
            if reader.done():
                candidate = reader.result()
                state["candidate"] = candidate
                state["expected_context"] = context
                state["expected_model"] = admitted.get("model_identity")
        except asyncio.CancelledError:
            state["disposition"] = "CANCELLED"
        except Exception as exc:
            state["disposition"] = "FAILED"
            await self._event(state, "COMPUTE_FAILED", {"exception_type": type(exc).__name__})
        finally:
            if state["cancel"].is_set() or self.closed:
                state["disposition"] = "CANCELLED"
            state["compute_state"] = "STOP_REQUESTED"
            await self._event(state, "STOP_REQUESTED")
            try:
                cleanup = await owned.stop()
            except Exception as exc:
                cleanup = {"confirmed": False, "exception_type": type(exc).__name__}
            state["cleanup"] = cleanup
            state["compute_state"] = "STOP_CONFIRMED" if cleanup["confirmed"] else "UNKNOWN"
            if not cleanup["confirmed"]:
                self.quarantined = True
                state["disposition"] = "INCONCLUSIVE"
            await self._event(state, state["compute_state"], cleanup)
            if cleanup["confirmed"]:
                await asyncio.gather(*io_tasks, return_exceptions=True)
                if getattr(owned, "backend_drain", None):
                    await asyncio.gather(owned.backend_drain, return_exceptions=True)
                for proc in owned.processes:
                    proc.close()
                owned.close()
            if getattr(owned, "model_lease", None):
                owned.model_lease.finish(confirmed=cleanup["confirmed"], outcome=state["disposition"])
        if state.get("candidate"):
            await self._accept_candidate(state, state.pop("candidate"))

    async def _accept_candidate(self, state, candidate):
        """Internal test seam; all identity/hash/citation checks precede callback."""
        required = {"identity", "request_digest", "context_digest", "output_digest", "payload",
                    "source_refs", "model_identity", "outcome", "usage", "certainty"}
        if (not isinstance(candidate, dict) or set(candidate) != required
                or not isinstance(candidate.get("payload"), dict)
                or not isinstance(candidate.get("usage"), dict)
                or candidate.get("outcome") != "COMPLETED" or candidate.get("certainty") != "OBSERVED"):
            await self._event(state, "RESULT_REJECTED_SCHEMA")
            if not state["result_seen"]:
                state["disposition"] = "INCONCLUSIVE"
            return {"disposition": "REJECTED"}
        context = state["expected_context"]
        reject = state["result_seen"] or state["cancel"].is_set() or self.closed or self.quarantined
        reject = reject or time.monotonic() >= state["deadline"]
        reject = reject or candidate.get("identity") != state["identity"]
        reject = reject or candidate.get("request_digest") != state["job"]["request_digest"]
        reject = reject or candidate.get("context_digest") != context_digest(context)
        reject = reject or candidate.get("model_identity") != state["expected_model"]
        payload = candidate.get("payload")
        reject = reject or len(canonical(payload)) > MAX_OUTPUT or candidate.get("output_digest") != digest(payload)
        allowed = {s["id"] for s in context.get("sources", [])}
        refs = candidate.get("source_refs", [])
        reject = reject or not isinstance(refs, list) or any(not isinstance(s, str) or s not in allowed for s in refs)
        if reject:
            await self._event(state, "RESULT_FENCED")
            if not state["result_seen"]:
                state["disposition"] = "CANCELLED" if state["cancel"].is_set() else "INCONCLUSIVE"
            return {"disposition": "FENCED"}
        state["result_seen"] = True
        state["disposition"] = "SUCCEEDED"
        result = {**state["identity"], **{k: candidate[k] for k in
                  ("request_digest", "context_digest", "output_digest", "payload", "source_refs", "model_identity",
                   "outcome", "usage", "certainty")}}
        try:
            disposition = await asyncio.wait_for(self.on_result(result), 5)
        except Exception:
            disposition = {"disposition": "UNKNOWN"}
        await self._event(state, "RESULT_DISPOSITION", {"disposition": disposition.get("disposition", "UNKNOWN")})
        return disposition

    async def close(self, deadline_monotonic):
        self.closed = True
        for state in self.jobs.values():
            if state["disposition"] == "QUEUED" or state["compute_state"] in ("RUNNING", "STOP_REQUESTED"):
                state["cancel"].set()
                if state["owned_job"] and state["owned_job"].handle:
                    state["owned_job"].terminate()
        if self.task:
            try:
                await asyncio.wait_for(self.queue.join(), max(0.001, deadline_monotonic - time.monotonic()))
            except TimeoutError:
                self.quarantined = True
            if self.queue.empty() and all(s["compute_state"] not in ("RUNNING", "STOP_REQUESTED") for s in self.jobs.values()):
                self.task.cancel()
                await asyncio.gather(self.task, return_exceptions=True)
                self.task = None
        confirmed = not self.quarantined and self.task is None
        if self.journal:
            self._append({"kind": "SUPERVISOR_CLOSED", "confirmed": confirmed})
            if self.task is None:
                self.journal.close()
                self.journal = None
        return {"confirmed": confirmed, "runtime_quarantined": self.quarantined}
