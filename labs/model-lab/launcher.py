"""Local launch/stop controls; every child is contained before it can execute."""
from pathlib import Path
import argparse
import hmac
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import secrets
import subprocess
import threading
import time
import webbrowser

from labcore import ROOT, OwnedEngine, atomic_json

PORTS = {'lab': 8788, 'strata': 8081}


def post(port, path, token='', header='X-Lab-Token', timeout=20):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout)
    try:
        connection.request('POST', path, '{}', {'Content-Type': 'application/json', header: token,
                           'Origin': f'http://127.0.0.1:{port}'})
        response = connection.getresponse()
        body = response.read()
        if response.status != 200:
            raise RuntimeError(f'Local control returned HTTP {response.status}.')
        return json.loads(body)
    finally:
        connection.close()


def stop(kind):
    path = ROOT / '.local' / f'launch-{kind}.json'
    if not path.exists():
        print('No active launch receipt.'); return
    receipt = json.loads(path.read_text('utf-8'))
    if receipt.get('kind') != kind or receipt.get('control_port') != PORTS[kind]:
        raise ValueError('Invalid local launch receipt; no process was touched.')
    print(post(PORTS[kind], '/stop', receipt['control_token'], timeout=5)['state'])
    deadline = time.monotonic() + 80
    while path.exists() and time.monotonic() < deadline:
        time.sleep(.2)
    if path.exists():
        raise RuntimeError('Stop not confirmed. Inspect the retained launcher log.')
    print('Owned process tree stopped.')


def run(kind, open_browser=True, lan=False):
    # An OS-held lock survives neither process death nor reboot. A stale receipt
    # may be removed only while this lock is held AND the control port is free.
    lock_path = ROOT / '.local' / f'launch-{kind}.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a+b') as lock:
        if lock.tell() == 0: lock.write(b'0'); lock.flush()
        lock.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            return run_locked(kind, open_browser, lan)
        finally:
            lock.seek(0)
            if os.name == 'nt': msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else: fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def run_locked(kind, open_browser=True, lan=False):
    data = ROOT / '.local' / f'launcher-{kind}'
    data.mkdir(parents=True, exist_ok=True)
    path = ROOT / '.local' / f'launch-{kind}.json'
    token = secrets.token_urlsafe(32)
    stopping = threading.Event()

    class Control(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            valid = (self.path == '/stop' and self.headers.get('Host') == f'127.0.0.1:{PORTS[kind]}'
                     and self.headers.get('Origin') in (None, f'http://127.0.0.1:{PORTS[kind]}')
                     and hmac.compare_digest(self.headers.get('X-Lab-Token', ''), token))
            body = b'{"state":"STOP_REQUESTED"}' if valid else b'{"error":"Denied"}'
            self.send_response(200 if valid else 403)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            try: self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError): pass
            if valid: stopping.set()

    class ControlServer(ThreadingHTTPServer):
        allow_reuse_address = False
        daemon_threads = True
    control = ControlServer(('127.0.0.1', PORTS[kind]), Control)
    try:
        if path.exists():
            previous = json.loads(path.read_text('utf-8'))
            if previous.get('kind') != kind or previous.get('control_port') != PORTS[kind]:
                raise ValueError('Unrecognized launch receipt; nothing was replaced.')
            path.unlink()  # Lock acquired and port bound: the original controller is absent.
    except Exception:
        control.server_close()
        raise
    owner = OwnedEngine(data)
    env = dict(os.environ, PYTHONUTF8='1', HAVEN_CONTROL_TOKEN=token)
    for name in list(env):
        if name.startswith(('STRATA_', 'LLAMA_ARG_', 'OPENAI_', 'ANTHROPIC_')) or name in ('HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN'):
            env.pop(name, None)
    if kind == 'lab':
        cwd = ROOT
        argv = [str(ROOT / '.local/python/python.exe'), '-X', 'utf8', '-E', '-s', str(ROOT / 'server.py')]
        if lan:
            argv.append('--lan')
    else:
        cwd = ROOT / '.local/Strata'
        config = cwd / 'strata-iq2_xs.json'
        if not config.exists():
            control.server_close(); raise RuntimeError('Complete SETUP-STRATA first.')
        argv = [str(cwd / '.venv/Scripts/python.exe'), '-X', 'utf8', str(cwd / 'serve/server.py'),
                '--engine', 'strata', '--config', str(config), '--host', '127.0.0.1', '--port', '8080']
    receipt = {'kind': kind, 'control_port': PORTS[kind], 'control_token': token,
               'supervisor_pid': os.getpid(), 'started_at': time.time(), 'lan': bool(lan)}
    url = None
    control_started = False
    try:
        owner.launch(argv, cwd, label=f'{kind} launcher', env=env)
        atomic_json(path, receipt)
        threading.Thread(target=control.serve_forever, daemon=True).start()
        control_started = True
        while not stopping.wait(.2):
            if owner.proc.poll() is not None: break
            if url is None:
                log = (data / 'engine.log').read_text('utf-8', errors='replace')
                if kind == 'lab':
                    if lan:
                        match = re.search(r'Local owner URL:\s+(http://127\.0\.0\.1:8787/(?:#bootstrap=[A-Za-z0-9_-]+)?)', log)
                        if match:
                            url = match.group(1)
                        lan_urls = sorted(set(re.findall(r'LAN access:\s+(http://[0-9.]+:8787/)', log)))
                        if lan_urls:
                            receipt['lan_urls'] = lan_urls
                    else:
                        match = re.search(r'http://127\.0\.0\.1:8787/#token=[A-Za-z0-9_-]+', log)
                        if match: url = match.group()
                elif 'ready: http://127.0.0.1:8080/v1' in log:
                    url = 'http://127.0.0.1:8080/'
                if url:
                    receipt['url'] = url; atomic_json(path, receipt)
                    if open_browser: webbrowser.open(url)
        graceful = False
        if owner.proc.poll() is None:
            try:
                if kind == 'lab' and url:
                    post(8787, '/api/private/shutdown', token, header='X-Haven-Control')
                    owner.proc.wait(timeout=20)
                    graceful = True
                elif kind == 'strata' and url:
                    post(8080, '/unload', timeout=65)
                    graceful = True
            except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.TimeoutExpired): pass
        result = owner.stop()
        if result.get('state') != 'STOPPED':
            raise RuntimeError('Owned stop was not confirmed; receipt retained.')
        path.unlink()
        atomic_json(data / 'last-stop.json', {'graceful_api': graceful, 'result': result, 'at': time.time()})
    finally:
        if control_started: control.shutdown()
        control.server_close()
        if owner.proc is not None:
            result = owner.stop()
            if result.get('state') == 'STOPPED' and path.exists(): path.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=PORTS)
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--lan', action='store_true')
    args = parser.parse_args()
    if args.lan and args.kind != 'lab':
        parser.error('--lan is valid only for the lab UI.')
    stop(args.kind) if args.stop else run(args.kind, not args.no_browser, args.lan)
