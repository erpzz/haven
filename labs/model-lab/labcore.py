"""Haven Model Lab: local-only inference control, streaming and measurements.

No pip dependencies. No downloads on import/startup. No cloud inference. External
Strata servers are attached, NEVER owned or killed by this process.
"""
from __future__ import annotations
import csv
import ctypes
import hashlib
import http.client
import io
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

VERSION = '0.1.0'
GIB = 1024 ** 3
MIB = 1024 ** 2
MAX_JSON = 1024 ** 2
ROOT = Path(__file__).resolve().parent

def read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text('utf-8'))
    except FileNotFoundError:
        return fallback

def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + secrets.token_hex(4) + '.tmp')
    try:
        with temp.open('w', encoding='utf-8') as f:
            json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 * MIB), b''):
            h.update(block)
    return h.hexdigest()

def bounded_int(value, low: int, high: int, name: str) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name} must be an integer from {low} to {high}.')
    return value

def finite_float(value, low: float, high: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name} must be between {low} and {high}.')
    return float(value)

def endpoint(value: str) -> tuple[str, int]:
    """Literal loopback only: no DNS rebinding, proxy, URL credentials or LAN URL."""
    if not isinstance(value, str):
        raise ValueError('Local endpoint required.')
    p = urllib.parse.urlsplit(value)
    if p.scheme != 'http' or p.hostname != '127.0.0.1' or p.username or p.password or p.query or p.fragment:
        raise ValueError('Use http://127.0.0.1:PORT/v1. Remote hosts are not permitted.')
    if p.path.rstrip('/') not in ('', '/v1'):
        raise ValueError('Endpoint path must be /v1 or empty.')
    port = p.port or 80
    bounded_int(port, 1024, 65535, 'Port')
    return '127.0.0.1', port

def local_json(base: str, path: str, key: str = '', timeout: float = 3):
    host, port = endpoint(base)
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        headers = {'Authorization': 'Bearer ' + key} if key else {}
        conn.request('GET', path, headers=headers)
        r = conn.getresponse()
        raw = r.read(MAX_JSON + 1)
        if r.status != 200:
            raise ValueError(f'Local server returned HTTP {r.status}.')
        if len(raw) > MAX_JSON:
            raise ValueError('Response exceeds local metadata limit.')
        return json.loads(raw)
    finally:
        conn.close()

def parse_smi(text: str) -> list[dict]:
    names = ['index', 'name', 'memory_total_mib', 'memory_used_mib', 'memory_free_mib', 'utilization_pct', 'temperature_c', 'power_w', 'driver']
    rows = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) != len(names):
            continue
        out = dict(zip(names, [s.strip() for s in row]))
        for k in names[2:-1]:
            try:
                number = float(out[k])
                out[k] = number if math.isfinite(number) else None
            except ValueError:
                out[k] = None
        try:
            out['index'] = int(out['index'])
        except ValueError:
            continue
        rows.append(out)
    return rows

def hardware(data_dir: Path) -> dict:
    info = {'gpus': [], 'gpu_status': 'UNAVAILABLE', 'cpu_logical_threads': os.cpu_count(),
            'ram_total_gib': None, 'ram_available_gib': None, 'disk_free_gib': shutil.disk_usage(data_dir).free / GIB,
            'platform': sys.platform, 'sampled_at': time.time()}
    smi = shutil.which('nvidia-smi')
    if os.name == 'nt' and not smi:
        for p in [Path(os.environ.get('WINDIR', 'C:/Windows')) / 'System32/nvidia-smi.exe',
                  Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'NVIDIA Corporation/NVSMI/nvidia-smi.exe']:
            if p.is_file():
                smi = str(p)
                break
    if smi:
        try:
            p = subprocess.run([smi, '--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw,driver_version',
                '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=4,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if p.returncode == 0:
                info['gpus'] = parse_smi(p.stdout)
                info['gpu_status'] = 'OBSERVED' if info['gpus'] else 'UNPARSEABLE'
            else:
                info['gpu_status'] = 'DRIVER_QUERY_FAILED'
        except (OSError, subprocess.TimeoutExpired):
            info['gpu_status'] = 'QUERY_FAILED'
    if os.name == 'nt':
        class Memory(ctypes.Structure):
            _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(k, ctypes.c_ulonglong) for k in
                ('total', 'available', 'total_page', 'available_page', 'total_virtual', 'available_virtual', 'extended')]
        m = Memory(); m.length = ctypes.sizeof(m)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
            info.update(ram_total_gib=m.total / GIB, ram_available_gib=m.available / GIB)
    else:
        try:
            mem = {a: int(b.split()[0]) * 1024 for a, b in [line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines()]}
            info.update(ram_total_gib=mem['MemTotal'] / GIB, ram_available_gib=mem['MemAvailable'] / GIB)
        except (OSError, ValueError, KeyError):
            pass
    return info

PRESETS = {
    'balanced': {'label': 'Desktop-friendly CUDA', 'context': 4096, 'threads': 6, 'batch': 256, 'ubatch': 128, 'kv': 'f16', 'flash': 'auto'},
    'gpu': {'label': 'GPU-first CUDA', 'context': 4096, 'threads': 8, 'batch': 512, 'ubatch': 256, 'kv': 'f16', 'flash': 'auto'},
    'memory': {'label': 'Quantized KV experiment', 'context': 8192, 'threads': 8, 'batch': 256, 'ubatch': 128, 'kv': 'q8_0', 'flash': 'on'},
}

def llama_command(exe: Path, model: Path, port: int, key_file: Path, profile: dict, gpu: int = 0) -> list[str]:
    context = bounded_int(profile.get('context', 4096), 512, 32768, 'Context')
    threads = bounded_int(profile.get('threads', 8), 1, 24, 'Threads')
    batch = bounded_int(profile.get('batch', 512), 32, 2048, 'Batch')
    ubatch = bounded_int(profile.get('ubatch', 256), 32, batch, 'Microbatch')
    kv = profile.get('kv', 'f16'); flash = profile.get('flash', 'auto')
    if kv not in ('f16', 'q8_0') or flash not in ('auto', 'on', 'off'):
        raise ValueError('Unsupported cache or flash attention option.')
    if kv != 'f16' and flash != 'on':
        raise ValueError('The quantized KV experiment requires flash attention on.')
    bounded_int(gpu, 0, 15, 'GPU index'); bounded_int(port, 1024, 65535, 'Port')
    return [str(exe), '--model', str(model), '--host', '127.0.0.1', '--port', str(port),
            '--api-key-file', str(key_file), '--alias', 'haven-local', '--n-gpu-layers', '999',
            '--device', f'CUDA{gpu}', '--ctx-size', str(context), '--parallel', '1', '--threads', str(threads),
            '--threads-batch', str(threads), '--batch-size', str(batch), '--ubatch-size', str(ubatch),
            '--flash-attn', flash, '--cache-type-k', kv, '--cache-type-v', kv, '--jinja', '--metrics',
            '--log-verbosity', '4']

def estimate_fit(model_bytes: int, free_mib: float | None, context: int) -> dict:
    # Not a GGUF architecture parser. Explicitly a conservative planning heuristic.
    overhead = 1200 + context * .09
    required = model_bytes / MIB + overhead + 700
    return {'estimated_required_mib': round(required), 'free_mib': free_mib,
            'status': 'UNKNOWN' if free_mib is None else ('LIKELY_FITS' if required <= free_mib else 'TIGHT_OR_TOO_LARGE'),
            'basis': 'Heuristic: file size + scratch/KV allowance + 700 MiB desktop reserve; not measured allocation.'}

class OwnedEngine:
    def __init__(self, data: Path):
        self.data = data
        self.lock = threading.RLock()
        self.proc = None
        self.job = None
        self.log = None
        self.record = {'state': 'STOPPED', 'ownership': 'NONE'}
    def launch(self, argv: list[str], cwd: Path, *, label: str, env: dict | None = None) -> dict:
        with self.lock:
            if self.proc is not None:
                # Includes a wrapper that exited while descendants may remain.
                raise ValueError('Unload the previous owned engine before launching another.')
            self.data.mkdir(parents=True, exist_ok=True)
            job = None; p = None
            log = (self.data / 'engine.log').open('wb')
            try:
                if os.name == 'nt':
                    from winjob import WindowsJob
                    job = WindowsJob()
                p = subprocess.Popen([sys.executable, str(ROOT / 'process_gate.py')], cwd=cwd, env=env,
                    stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, close_fds=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                    start_new_session=os.name != 'nt')
                if job:
                    job.assign(int(p._handle))
                # No engine exists before this point.
                p.stdin.write((json.dumps({'go': True, 'argv': argv}) + '\n').encode())
                p.stdin.flush(); p.stdin.close()
                self.proc, self.job, self.log = p, job, log
                self.record = {'state': 'STARTING', 'ownership': 'OWNED', 'pid': p.pid, 'label': label,
                    'started_at': time.time(), 'argv': argv, 'containment': 'WINDOWS_JOB' if job else 'POSIX_PROCESS_GROUP'}
                return dict(self.record)
            except Exception:
                if job:
                    job.close()
                if p:
                    if p.stdin and not p.stdin.closed: p.stdin.close()
                    if os.name != 'nt':
                        try: os.killpg(p.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
                    else: p.kill()
                    p.wait(timeout=5)
                log.close()
                raise
    def status(self) -> dict:
        with self.lock:
            rec = dict(self.record)
            if self.proc and self.proc.poll() is not None:
                rec.update(state='PROCESS_EXITED', exit_code=self.proc.returncode)
            return rec
    def stop(self, expected=None) -> dict:
        with self.lock:
            if expected is not None and self.proc is not expected:
                return {'state': 'NOT_CURRENT_OWNER', 'stopped': False}
            if not self.proc:
                return self.status()
            p = self.proc
            stopped = False
            try:
                if self.job:
                    self.job.terminate()
                else:
                    try: os.killpg(p.pid, signal.SIGTERM)
                    except ProcessLookupError: pass
                try: p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    if self.job: self.job.terminate()
                    else:
                        try: os.killpg(p.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
                    p.wait(timeout=3)
                if self.job:
                    deadline = time.monotonic() + 3
                    while self.job.active_count() and time.monotonic() < deadline:
                        time.sleep(.05)
                    stopped = self.job.active_count() == 0
                else:
                    # Ensure all remaining group members receive termination even if gate exited first.
                    try: os.killpg(p.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    stopped = True  # local group signal + reaped owned root; no host-wide claim
                self.record.update(state='STOPPED' if stopped else 'STOP_UNCONFIRMED', stopped_at=time.time(),
                    observation='Job active count zero' if self.job and stopped else 'Owned process group signalled; root reaped')
                return dict(self.record)
            finally:
                if stopped:
                    if self.job: self.job.close()
                    if self.log: self.log.close()
                    self.proc = self.job = self.log = None
                else:
                    # Keep the ownership guard and job handle. An uncertain stop
                    # is not permission to start another GPU workload.
                    self.record.update(state='STOP_UNCONFIRMED', observation='Owned termination not established; new launch blocked.')

class Job:
    def __init__(self, kind: str):
        self.id = secrets.token_hex(12)
        self.kind = kind
        self.lock = threading.RLock()
        self.cancelled = threading.Event()
        self.sock = None
        self.data = {'id': self.id, 'kind': kind, 'state': 'RUNNING', 'text': '', 'reasoning': '', 'created_at': time.time(), 'progress': None}
    def update(self, **items):
        with self.lock: self.data.update(items)
    def snapshot(self):
        with self.lock: return dict(self.data)
    def cancel(self):
        self.cancelled.set()
        with self.lock:
            if self.data['state'] == 'RUNNING': self.data['cancel_requested'] = True
            sock = self.sock
        if sock:
            try: sock.shutdown(socket.SHUT_RDWR)
            except OSError: pass

class ExternalRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        p = urllib.parse.urlsplit(newurl)
        allowed = ('github.com', 'githubusercontent.com', 'huggingface.co', 'hf.co', 'xethub.hf.co')
        if p.scheme != 'https' or not p.hostname or not any(p.hostname == s or p.hostname.endswith('.' + s) for s in allowed):
            raise ValueError('Unexpected download redirect; stopped.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def download_verified(url: str, dest: Path, digest: str, size: int | None, job: Job,
                      opener=None, free_bytes=None) -> None:
    if not re.fullmatch(r'[0-9a-f]{64}', digest):
        raise ValueError('A pinned SHA-256 is required before downloading.')
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or p.hostname not in ('huggingface.co', 'github.com') or p.username or p.password:
        raise ValueError('Unapproved download source.')
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + '.part')
    if dest.exists():
        if sha256_file(dest) == digest:
            job.update(progress=1, message='Existing file verified.')
            return
        raise ValueError('An existing file has the wrong checksum; it was not overwritten.')
    offset = part.stat().st_size if part.exists() else 0
    if size and offset > size:
        raise ValueError('Partial file is larger than the pinned artifact; remove it manually.')
    needed = max(0, (size or 0) - offset) + 2 * GIB
    free = shutil.disk_usage(dest.parent).free if free_bytes is None else free_bytes
    if free < needed:
        raise ValueError('Not enough free disk for this download plus 2 GiB reserve.')
    op = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), ExternalRedirect())
    req = urllib.request.Request(url, headers={'User-Agent': 'HavenModelLab/0.1', **({'Range': f'bytes={offset}-'} if offset else {})})
    if size and offset == size:
        response = None
    else:
        response = op.open(req, timeout=30)
    if response:
        with response as r:
            if offset and r.status != 206:
                offset = 0
            if r.status == 206 and not r.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                raise ValueError('Invalid resume response.')
            length = int(r.headers.get('Content-Length') or 0)
            total = size or (offset + length if length else None)
            if offset == 0 and free < (total or 0) + 2 * GIB:
                raise ValueError('Download does not fit available disk.')
            received = offset
            with part.open('ab' if offset else 'wb') as f:
                while True:
                    if job.cancelled.is_set():
                        raise InterruptedError('Download paused; partial file retained for resume.')
                    chunk = r.read(MIB)
                    if not chunk: break
                    received += len(chunk)
                    if received > (size or 20 * GIB):
                        raise ValueError('Download exceeded declared size limit.')
                    f.write(chunk)
                    job.update(downloaded_bytes=received, total_bytes=total, progress=received / total if total else None)
    if job.cancelled.is_set(): raise InterruptedError('Download paused.')
    job.update(message='Verifying SHA-256; this can take a moment.', progress=None)
    if (size and part.stat().st_size != size) or sha256_file(part) != digest:
        raise ValueError('Checksum/size mismatch. Partial file kept; it will NOT be installed.')
    os.replace(part, dest)
    job.update(message='Checksum verified.', progress=1)

def safe_extract(path: Path, target: Path, max_bytes: int = 3 * GIB) -> None:
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as z:
        if sum(i.file_size for i in z.infolist()) > max_bytes:
            raise ValueError('Archive exceeds extraction limit.')
        for i in z.infolist():
            name = i.filename.replace('\\', '/')
            out = (target / name).resolve()
            if ':' in name or not out.is_relative_to(target.resolve()) or ((i.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError('Unsafe archive member.')
        z.extractall(target)

class Lab:
    def __init__(self, data: Path, catalog: dict | None = None):
        self.data = data.resolve(); self.data.mkdir(parents=True, exist_ok=True)
        self.catalog = catalog or read_json(ROOT / 'catalog.json', {})
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.jobs = {}
        self.generation = threading.Lock()
        self.download_lock = threading.Lock()
        self.engine = OwnedEngine(self.data)
        self.connection = None
        self.shutting_down = False
        self.settings = read_json(self.data / 'settings.json', {'models': {}})
        self.hw = hardware(self.data)
        self.hw_at = time.monotonic()
    def new_job(self, kind: str) -> Job:
        with self.lock:
            if self.shutting_down: raise ValueError('Lab is shutting down.')
            if len(self.jobs) >= 32:
                old = next((k for k, j in self.jobs.items() if j.snapshot()['state'] != 'RUNNING'), None)
                if old: del self.jobs[old]
                else: raise ValueError('Too many active jobs.')
            j = Job(kind); self.jobs[j.id] = j; return j
    def get_hardware(self):
        with self.lock:
            if time.monotonic() - self.hw_at > 3:
                self.hw = hardware(self.data); self.hw_at = time.monotonic()
            return dict(self.hw)
    def public_state(self):
        with self.lock:
            models = []
            for item in self.catalog.get('models', []):
                m = dict(item)
                registered = self.settings['models'].get(item['id'])
                m['downloaded'] = bool(registered and Path(registered['path']).is_file())
                models.append(m)
            known = {m['id'] for m in models}
            for k, v in self.settings['models'].items():
                if k not in known:
                    models.append({'id': k, 'name': v['name'], 'filename': Path(v['path']).name,
                        'size_bytes': v['size_bytes'], 'downloaded': Path(v['path']).is_file(), 'imported': True,
                        'description': 'User-selected local GGUF. Compatibility and license are not verified by the catalog.'})
            conn = {k: v for k, v in (self.connection or {}).items() if k != 'key'}
            return {'version': VERSION, 'connection': conn, 'engine': self.engine.status(), 'models': models,
                    'presets': PRESETS, 'hardware': self.get_hardware(), 'llama_installed': self.llama_exe() is not None,
                    'jobs': [{k:v for k,v in j.snapshot().items() if k not in ('text','reasoning')} for j in self.jobs.values()], 'data_dir': str(self.data)}
    def llama_exe(self) -> Path | None:
        expected = self.data / 'engines' / self.catalog.get('llama_tag', 'b11146')
        for name in ('llama-server.exe', 'llama-server'):
            found = list(expected.rglob(name)) if expected.exists() else []
            if found: return found[0]
        return None
    def _run_download(self, j: Job, fn):
        try:
            fn()
            j.update(state='COMPLETED', completed_at=time.time())
        except InterruptedError as e:
            j.update(state='CANCELLED', error=str(e))
        except Exception as e:
            j.update(state='FAILED', error=str(e)[:500])
        finally:
            self.download_lock.release()
    def download_model(self, model_id: str) -> str:
        m = next((m for m in self.catalog['models'] if m['id'] == model_id), None)
        if not m: raise ValueError('Model is not in the pinned download catalog. Use local GGUF import.')
        if not self.download_lock.acquire(False): raise ValueError('Another download/install is running.')
        j = self.new_job('model-download')
        def work():
            dest = self.data / 'models' / m['filename']
            download_verified(m['url'], dest, m['sha256'], m.get('size_bytes'), j)
            with self.lock:
                self.settings['models'][model_id] = {'name': m['name'], 'path': str(dest), 'size_bytes': dest.stat().st_size, 'sha256': m['sha256']}
                atomic_json(self.data / 'settings.json', self.settings)
        threading.Thread(target=self._run_download, args=(j, work), daemon=True).start()
        return j.id
    def install_llama(self) -> str:
        if os.name != 'nt': raise ValueError('Automatic CUDA installation is Windows-only. Attach an existing local backend on this OS.')
        if self.engine.proc is not None: raise ValueError('Unload the owned engine before installing.')
        if not self.download_lock.acquire(False): raise ValueError('Another download/install is running.')
        j = self.new_job('engine-install')
        def work():
            target = self.data / 'engines' / self.catalog['llama_tag']
            stage = self.data / 'engines' / (self.catalog['llama_tag'] + '.staging')
            if target.exists(): raise ValueError('Engine directory already exists; nothing was replaced.')
            if stage.exists(): raise ValueError('An engine staging directory exists; inspect the retained install before retrying.')
            for asset in self.catalog['llama_assets']:
                j.update(message='Downloading ' + asset['name'])
                dest = self.data / 'downloads' / asset['name']
                download_verified(asset['url'], dest, asset['sha256'], asset['size_bytes'], j)
                safe_extract(dest, stage)
            # Release assets can have different top-level folders: put runtime DLLs next to the executable.
            executables = list(stage.rglob('llama-server.exe'))
            if len(executables) != 1: raise ValueError('Expected one llama-server.exe in official archive.')
            bin_dir = executables[0].parent
            for dll in list(stage.rglob('*.dll')):
                dest = bin_dir / dll.name
                if dll != dest:
                    if dest.exists() and sha256_file(dest) != sha256_file(dll):
                        raise ValueError('Conflicting runtime DLLs; refusing installation.')
                    if not dest.exists(): shutil.copy2(dll, dest)
            atomic_json(stage / 'install-receipt.json', {'tag': self.catalog['llama_tag'], 'assets': self.catalog['llama_assets'], 'at': time.time()})
            os.replace(stage, target)
            j.update(message='CUDA runtime installed. No driver/toolkit was changed.', progress=1)
        threading.Thread(target=self._run_download, args=(j, work), daemon=True).start()
        return j.id
    def import_model(self, value: str) -> dict:
        if not isinstance(value, str) or len(value) > 2048: raise ValueError('Invalid model path.')
        p = Path(value.strip().strip('"')).expanduser().resolve(strict=True)
        if p.suffix.lower() != '.gguf' or not p.is_file(): raise ValueError('Choose an existing .gguf file.')
        with p.open('rb') as f:
            if f.read(4) != b'GGUF': raise ValueError('This file does not have a GGUF header.')
        mid = 'local-' + hashlib.sha256(str(p).encode()).hexdigest()[:12]
        with self.lock:
            self.settings['models'][mid] = {'path': str(p), 'name': p.stem, 'size_bytes': p.stat().st_size, 'sha256': None}
            atomic_json(self.data / 'settings.json', self.settings)
        return {'id': mid, 'name': p.stem}
    def connect(self, base: str, key: str = '', kind: str = 'strata') -> dict:
        endpoint(base)
        if kind not in ('strata', 'llama', 'other'): raise ValueError('Invalid backend type.')
        if not isinstance(key, str) or len(key) > 4096 or '\r' in key or '\n' in key: raise ValueError('Invalid API key.')
        if self.engine.proc is not None: raise ValueError('Unload the managed engine before attaching another backend.')
        if self.generation.locked(): raise ValueError('Finish or cancel the active request before reconnecting.')
        models = local_json(base, '/v1/models', key)
        data = models.get('data', [])
        if not data or not isinstance(data[0].get('id'), str): raise ValueError('No model was reported by the local backend.')
        conn = {'base': base.rstrip('/'), 'key': key, 'model': data[0]['id'], 'kind': kind, 'ownership': 'EXTERNAL', 'connected_at': time.time()}
        with self.lock:
            if self.generation.locked() or self.engine.proc is not None:
                raise ValueError('Backend ownership changed while connecting; finish or unload it first.')
            self.connection = conn
        return {k: v for k, v in conn.items() if k != 'key'}
    def start_llama(self, model_id: str, preset: str, overrides=None, allow_tight: bool = False) -> str:
        with self.lock:
            if self.connection and self.connection.get('ownership') == 'EXTERNAL':
                raise ValueError('Disconnect and stop the external backend first; the lab will not kill it.')
            if not self.generation.acquire(False): raise ValueError('A request is active.')
            self.generation.release()
            exe = self.llama_exe()
            if not exe: raise ValueError('Install the CUDA engine first.')
            item = self.settings['models'].get(model_id)
            if not item or not Path(item['path']).is_file(): raise ValueError('Download or import the model first.')
            if preset not in PRESETS: raise ValueError('Unknown preset.')
            profile = dict(PRESETS[preset]); profile.update(overrides or {})
            gpu = 0
            self.hw_at = 0  # A just-unloaded model must not leave the fit gate using cached VRAM.
            hw = self.get_hardware()
            if not hw['gpus']: raise ValueError('NVIDIA GPU was not detected. Check your driver; CPU fallback is not silently enabled.')
            first = hw['gpus'][0]; gpu = first['index']
            fit = estimate_fit(item['size_bytes'], first['memory_free_mib'], profile['context'])
            if fit['status'] != 'LIKELY_FITS' and not allow_tight:
                raise ValueError('This configuration is tight for current free VRAM. Try a 4B model/shorter context, or explicitly enable the memory-risk experiment.')
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
            key = secrets.token_urlsafe(32); key_file = self.data / 'engine-key.txt'
            key_file.write_text(key, encoding='utf-8')
            try: key_file.chmod(0o600)
            except OSError: pass
            argv = llama_command(exe, Path(item['path']), port, key_file, profile, gpu)
            env = dict(os.environ)
            # Avoid loading unrequested user overrides or inherited cloud credentials into the engine.
            for k in list(env):
                if k.startswith(('LLAMA_ARG_', 'OPENAI_', 'ANTHROPIC_', 'TYPESAFE_')) or k in ('HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN'):
                    env.pop(k, None)
            self.engine.launch(argv, exe.parent, label=item['name'], env=env)
            owned_proc = self.engine.proc
            try:
                j = self.new_job('engine-start')
            except Exception:
                self.engine.stop(expected=owned_proc)
                raise
            def wait_ready():
                try:
                    deadline = time.monotonic() + 180
                    base = f'http://127.0.0.1:{port}/v1'
                    while time.monotonic() < deadline:
                        if j.cancelled.is_set(): raise InterruptedError('Load cancelled.')
                        if self.engine.status()['state'] == 'PROCESS_EXITED':
                            raise ValueError('Engine exited. Inspect the runtime log; no CPU fallback or hidden retry was performed.')
                        result = None
                        try:
                            result = local_json(base, '/v1/models', key, timeout=1)
                        except (OSError, ValueError, http.client.HTTPException):
                            pass
                        if result and result.get('data') and result['data'][0]['id'] == 'haven-local':
                            # A stopped/replaced startup must never publish a connection or
                            # later stop a newer process. Check under the same ownership lock.
                            with self.lock, self.engine.lock:
                                if j.cancelled.is_set() or self.engine.proc is not owned_proc or owned_proc.poll() is not None:
                                    raise InterruptedError('Startup was cancelled or its owner changed.')
                                self.connection = {'base': base, 'key': key, 'model': 'haven-local', 'kind': 'llama', 'ownership': 'OWNED',
                                    'display_model': item['name'], 'profile': profile, 'model_sha256': item.get('sha256'), 'connected_at': time.time()}
                                self.engine.record['state'] = 'READY'
                                j.update(state='COMPLETED', message='Engine ready; inspect log and live GPU telemetry to verify offload.')
                            return
                        time.sleep(.5)
                    raise TimeoutError('Engine did not become ready within 180 seconds.')
                except Exception as e:
                    # Cleanup does not depend on writing a receipt.
                    stopped = self.engine.stop(expected=owned_proc)
                    j.update(state='CANCELLED' if j.cancelled.is_set() else 'FAILED', error=str(e), cleanup=stopped)
            threading.Thread(target=wait_ready, daemon=True).start()
            return j.id
    def stop_engine(self):
        with self.lock:
            for j in list(self.jobs.values()):
                if j.kind in ('generation', 'engine-start') and j.snapshot()['state'] == 'RUNNING': j.cancel()
            result = self.engine.stop()
            if self.connection and self.connection['ownership'] == 'OWNED': self.connection = None
            return result
    def disconnect(self):
        with self.lock:
            if self.engine.proc is not None: raise ValueError('Use Unload for an owned engine.')
            if self.generation.locked(): raise ValueError('Cancel the current request before disconnecting.')
            self.connection = None
        return {'state': 'DISCONNECTED', 'external_server_stopped': False}
    def validate_generation(self, req: dict) -> dict:
        messages = req.get('messages')
        if not isinstance(messages, list) or not 1 <= len(messages) <= 100: raise ValueError('Supply 1–100 messages.')
        clean = []
        for m in messages:
            if not isinstance(m, dict) or m.get('role') not in ('system', 'user', 'assistant') or not isinstance(m.get('content'), str):
                raise ValueError('This first release supports text messages only.')
            clean.append({'role': m['role'], 'content': m['content']})
        if sum(len(m['content']) for m in clean) > 100000: raise ValueError('Conversation too large; start a new chat.')
        effort = req.get('reasoning', 'none')
        if effort not in ('none', 'low', 'medium', 'high'): raise ValueError('Invalid reasoning effort.')
        return {'messages': clean, 'max_tokens': bounded_int(req.get('max_tokens', 2048), 16, 4096, 'Max output tokens'),
                'temperature': finite_float(req.get('temperature', .7), 0, 2, 'Temperature'),
                'top_p': finite_float(req.get('top_p', .8), .01, 1, 'Top-p'),
                'seed': bounded_int(req.get('seed', 42), 0, 2**31-1, 'Seed'), 'reasoning': effort,
                'benchmark': req.get('benchmark') is True, 'label': str(req.get('label', 'interactive'))[:80],
                'expected_connected_at': None if req.get('expected_connected_at') is None else
                    finite_float(req['expected_connected_at'], 0, 1e12, 'Expected connection identity')}
    def generate(self, request: dict) -> str:
        args = self.validate_generation(request)
        with self.lock:
            conn = dict(self.connection or {})
            if not conn: raise ValueError('Connect or load a model first.')
            if args['benchmark'] and args['expected_connected_at'] is not None and args['expected_connected_at'] != conn['connected_at']:
                raise ValueError('Benchmark backend changed. Start a new experiment for this connection.')
            if not self.generation.acquire(False): raise ValueError('One request at a time on this GPU. Cancel or wait for the active request.')
            try: j = self.new_job('generation')
            except Exception:
                self.generation.release(); raise
        threading.Thread(target=self._generate_worker, args=(j, conn, args), daemon=True).start()
        return j.id
    def _generate_worker(self, job: Job, backend: dict, args: dict):
        start = time.monotonic(); first = None; last = None; chunks = 0; usage = {}; timings = {}; finished = False; finish_reason = None
        conn = None; sock = None; final_state = 'FAILED'
        body = {'model': backend['model'], 'messages': args['messages'], 'stream': True,
                'stream_options': {'include_usage': True}, 'temperature': args['temperature'], 'top_p': args['top_p'],
                'max_tokens': args['max_tokens'], 'seed': args['seed']}
        if backend['kind'] == 'strata': body['reasoning_effort'] = args['reasoning']
        elif backend['kind'] == 'llama': body['chat_template_kwargs'] = {'enable_thinking': args['reasoning'] != 'none'}
        if args['benchmark'] and backend['kind'] == 'llama': body['cache_prompt'] = False
        watchdog_done = threading.Event()
        def watchdog():
            if not watchdog_done.wait(240):
                job.update(deadline_exceeded=True)
                job.cancel()
        threading.Thread(target=watchdog, daemon=True).start()
        job.update(backend=backend['kind'], model=backend.get('display_model', backend['model']), sent=False)
        try:
            if job.cancelled.is_set(): raise InterruptedError('Cancelled before send.')
            host, port = endpoint(backend['base'])
            conn = http.client.HTTPConnection(host, port, timeout=240)
            conn.connect(); sock = conn.sock
            with job.lock: job.sock = sock
            if job.cancelled.is_set(): raise InterruptedError('Cancelled before send.')
            headers = {'Content-Type': 'application/json', 'Accept': 'text/event-stream'}
            if backend.get('key'): headers['Authorization'] = 'Bearer ' + backend['key']
            job.update(sent=True)
            conn.request('POST', '/v1/chat/completions', body=json.dumps(body).encode(), headers=headers)
            r = conn.getresponse()
            if r.status != 200:
                # Keep backend-generated bodies out of logs; error text could contain prompts/secrets.
                raise ValueError(f'Backend HTTP {r.status}. Check the backend console and context settings. No automatic retry.')
            if 'text/event-stream' not in r.getheader('Content-Type', ''):
                raise ValueError('Backend did not return an SSE stream.')
            buffer = []; total = 0
            while not job.cancelled.is_set():
                raw = r.readline(262145)
                if len(raw) > 262144: raise ValueError('Oversized SSE line.')
                if not raw: break
                total += len(raw)
                if total > 8 * MIB: raise ValueError('Stream exceeded output limit.')
                line = raw.decode('utf-8').rstrip('\r\n')
                if line.startswith('data:'): buffer.append(line[5:].lstrip())
                if line or not buffer: continue
                payload = '\n'.join(buffer); buffer.clear()
                if payload == '[DONE]': finished = True; break
                obj = json.loads(payload)
                if obj.get('error'): raise ValueError('Backend reported a stream error.')
                if isinstance(obj.get('usage'), dict): usage = obj['usage']
                if isinstance(obj.get('timings'), dict): timings = obj['timings']
                choices = obj.get('choices') or []
                if choices:
                    delta = choices[0].get('delta') or {}
                    text = delta.get('content') or ''
                    reasoning = delta.get('reasoning_content') or delta.get('reasoning') or ''
                    if not isinstance(text, str) or not isinstance(reasoning, str): raise ValueError('Unsupported stream delta.')
                    if text or reasoning:
                        now = time.monotonic(); first = first or now; last = now; chunks += 1
                        with job.lock:
                            job.data['text'] += text; job.data['reasoning'] += reasoning
                        job.update(ttft_seconds=first - start)
                    reason = choices[0].get('finish_reason')
                    if reason:
                        finish_reason = str(reason)[:80]
                        finished = True
                        job.update(finish_reason=finish_reason)
            elapsed = time.monotonic() - start
            if job.cancelled.is_set():
                final_state = 'CANCELLED'
                job.update(backend_cessation='UNKNOWN: HTTP stream closed; unload owned engine for confirmed process stop.')
            elif not finished:
                raise ValueError('Stream ended without a completion marker; partial output retained.')
            else:
                final_state = 'OUTPUT_LIMIT' if finish_reason == 'length' else 'COMPLETED'
        except Exception as e:
            final_state = 'CANCELLED' if job.cancelled.is_set() else 'FAILED'
            job.update(error=str(e)[:500],
                backend_cessation='UNKNOWN' if job.snapshot().get('sent') else 'NOT_SENT')
        finally:
            watchdog_done.set()
            if conn: conn.close()
            with job.lock: job.sock = None
            elapsed = time.monotonic() - start
            n = usage.get('completion_tokens')
            if type(n) is not int or not 0 <= n <= args['max_tokens']: n = None
            speed = timings.get('predicted_per_second')
            if type(speed) not in (int, float) or not math.isfinite(speed) or speed <= 0: speed = None
            def timing_seconds(key):
                value = timings.get(key)
                return round(value / 1000, 4) if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None
            metric = {'elapsed_seconds': round(elapsed, 4), 'ttft_seconds': round(first-start, 4) if first else None,
                'completion_tokens': n, 'prompt_tokens': usage.get('prompt_tokens'), 'backend_decode_tps': speed,
                'backend_prompt_seconds': timing_seconds('prompt_ms'),
                'backend_decode_seconds': timing_seconds('predicted_ms'),
                'end_to_end_tps': round(n / elapsed, 3) if n is not None and elapsed > 0 else None,
                'stream_chunks': chunks, 'usage_source': 'BACKEND_REPORTED' if usage else 'UNAVAILABLE',
                'timings_source': 'BACKEND_REPORTED' if timings else 'UNAVAILABLE',
                'note': 'Stream chunks are NOT tokens. End-to-end throughput includes prefill; decode rate is separate.'}
            job.update(metrics=metric, finish_reason=finish_reason, completed_at=time.time())
            if args['benchmark']:
                try:
                    observed_hardware = self.get_hardware()
                except Exception:
                    observed_hardware = {'status': 'UNAVAILABLE'}
                record = {'at': time.time(), 'job': job.id, 'state': final_state, 'finish_reason': finish_reason, 'label': args['label'],
                    'backend': backend['kind'], 'model': backend.get('display_model', backend['model']),
                    'model_sha256': backend.get('model_sha256'), 'profile': backend.get('profile'),
                    'settings': {k: v for k, v in args.items() if k not in ('messages',)},
                    'prompt_sha256': hashlib.sha256(json.dumps(args['messages'], sort_keys=True).encode()).hexdigest(),
                    'metrics': metric, 'hardware': observed_hardware,
                    'test_double': str(backend.get('model', '')).startswith('TEST_DOUBLE')}
                try:
                    with self.lock:
                        with (self.data / 'benchmarks.jsonl').open('a', encoding='utf-8') as f: f.write(json.dumps(record) + '\n')
                except OSError:
                    job.update(receipt_error='Benchmark could not be saved. Result not discarded.')
            self.generation.release()
            # Publish terminal status LAST: metrics/receipts and the concurrency slot
            # must be ready before the UI can dispatch the next benchmark request.
            job.update(state=final_state)
    def shutdown(self):
        self.shutting_down = True
        for j in list(self.jobs.values()): j.cancel()
        return self.stop_engine()
