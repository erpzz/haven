"""Native launcher regressions using only temporary, benign owned children.

These tests never execute Lab/Strata applications, load models, or download data.
All HTTP listeners are test-owned literal loopback endpoints on ephemeral ports.
"""
import ctypes
from ctypes import wintypes as W
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import launcher
from labcore import OwnedEngine, ROOT, atomic_json


FAKE_HTTP = '''from http.server import BaseHTTPRequestHandler, HTTPServer
import sys
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_POST(self):
        self.send_response(200 if self.path == '/unload' else 404)
        self.send_header('Content-Length', '2')
        self.end_headers()
        self.wfile.write(b'{}')
server = HTTPServer(('127.0.0.1', int(sys.argv[1])), Handler)
print('ready: http://127.0.0.1:8080/v1', flush=True)
server.serve_forever()
'''

SUPERVISOR = '''import sys
from pathlib import Path
sys.path.insert(0, sys.argv[3])
import launcher
from labcore import OwnedEngine
launcher.ROOT = Path(sys.argv[1])
launcher.PORTS['strata'] = int(sys.argv[2])
original = OwnedEngine.launch
child = "import os,sys,time;from pathlib import Path;Path(sys.argv[1]).write_text(str(os.getpid()),encoding='utf-8');time.sleep(30)"
def launch(self, argv, cwd, *, label, env=None):
    return original(self, [sys.executable, '-c', child, str(launcher.ROOT / 'child.pid')],
                    cwd, label='BENIGN LAUNCHER FIXTURE', env=env)
OwnedEngine.launch = launch
launcher.run('strata', False)
'''


def free_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


def wait_for(predicate):
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        try:
            value = predicate()
            if value:
                return value
        except (FileNotFoundError, PermissionError, ValueError):
            pass  # Windows may briefly deny reads while a marker is replaced.
        time.sleep(.01)
    raise AssertionError('Benign launcher fixture did not settle within bound')


def control_request(port, token, *, origin=None, host=None):
    headers = {'X-Lab-Token': token}
    if origin is not None:
        headers['Origin'] = origin
    if host is not None:
        headers['Host'] = host
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    try:
        connection.request('POST', '/stop', '{}', headers)
        response = connection.getresponse()
        response.read()
        return response.status
    finally:
        connection.close()


@unittest.skipUnless(os.name == 'nt', 'Native Windows launcher/Job Object qualification')
class LauncherTests(unittest.TestCase):
    def fixture_root(self, directory):
        root = Path(directory).resolve()
        source = root / '.local' / 'Strata'
        source.mkdir(parents=True)
        (source / 'strata-iq2_xs.json').write_text('{}', encoding='utf-8')
        return root

    def assert_port_free(self, port):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))

    def threaded_fixture(self, mode):
        with tempfile.TemporaryDirectory(prefix='haven-launcher-test-') as directory:
            root = self.fixture_root(directory)
            port, api = free_port(), free_port()
            receipt = root / '.local' / 'launch-strata.json'
            owners, errors, calls = [], [], []
            original_launch, original_post = OwnedEngine.launch, launcher.post

            def launch(owner, argv, cwd, *, label, env=None):
                owners.append(owner)
                if mode == 'launch-failure':
                    raise OSError('synthetic launch failure')
                code = FAKE_HTTP if mode == 'ready' else 'import time;time.sleep(30)'
                return original_launch(owner, [sys.executable, '-c', code, str(api)],
                                       cwd, label='BENIGN LAUNCHER FIXTURE', env=env)

            def post(port, path, *args, **kwargs):
                calls.append((port, path))
                return original_post(api if port == 8080 else port, path, *args, **kwargs)

            def save(path, value):
                if mode == 'receipt-failure' and path.name == 'last-stop.json':
                    raise OSError('synthetic last-stop write failure')
                return atomic_json(path, value)

            def run():
                try:
                    launcher.run('strata', False)
                except Exception as error:
                    errors.append(error)

            with patch.object(launcher, 'ROOT', root), patch.dict(launcher.PORTS, {'strata': port}), \
                    patch.object(OwnedEngine, 'launch', launch), patch.object(launcher, 'post', post), \
                    patch.object(launcher, 'atomic_json', save):
                worker = threading.Thread(target=run, daemon=True)
                worker.start()
                try:
                    if mode != 'launch-failure':
                        launch_receipt = wait_for(lambda: json.loads(receipt.read_text('utf-8')))
                        token = launch_receipt['control_token']
                        if mode == 'ready':
                            wait_for(lambda: 'url' in json.loads(receipt.read_text('utf-8')))
                            self.assertEqual(control_request(port, 'wrong'), 403)
                            self.assertEqual(control_request(port, token, origin='https://evil.example'), 403)
                            self.assertEqual(control_request(port, token, host='evil.example'), 403)
                            self.assertTrue(worker.is_alive())
                            self.assertIsNone(owners[0].proc.poll())
                        self.assertEqual(control_request(port, token, origin=f'http://127.0.0.1:{port}'), 200)
                    worker.join(8)
                    self.assertFalse(worker.is_alive(), 'Launcher did not finish after bounded stop')
                    self.assertFalse(receipt.exists())
                    self.assertIsNone(owners[0].proc)
                    self.assert_port_free(port)
                    if mode in ('launch-failure', 'receipt-failure'):
                        self.assertEqual(len(errors), 1)
                        self.assertIsInstance(errors[0], OSError)
                    else:
                        self.assertFalse(errors)
                        stop = json.loads((root / '.local/launcher-strata/last-stop.json').read_text('utf-8'))
                        self.assertEqual(stop['result']['state'], 'STOPPED')
                        self.assertEqual(stop['graceful_api'], mode == 'ready')
                    self.assertEqual(calls, [(8080, '/unload')] if mode == 'ready' else [])
                finally:
                    # Only this fixture's controller and exact owner are touched.
                    if worker.is_alive() and receipt.exists():
                        token = json.loads(receipt.read_text('utf-8'))['control_token']
                        try:
                            control_request(port, token)
                        except OSError:
                            pass
                        worker.join(8)
                    for owner in owners:
                        if owner.proc is not None:
                            owner.stop()
                    worker.join(2)

    def test_authorized_native_stop_and_exception_cleanup(self):
        for mode in ('ready', 'no-url', 'launch-failure', 'receipt-failure'):
            with self.subTest(mode=mode):
                self.threaded_fixture(mode)

    def test_receipt_refusal_preserves_busy_service_and_releases_lock(self):
        for mode in ('busy', 'mismatched', 'malformed'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix='haven-receipt-test-') as directory:
                root = self.fixture_root(directory)
                port = free_port()
                receipt = root / '.local/launch-strata.json'
                raw = 'not-json' if mode == 'malformed' else json.dumps({
                    'kind': 'lab' if mode == 'mismatched' else 'strata',
                    'control_port': port, 'control_token': 'fixture'})
                receipt.write_text(raw, encoding='utf-8')
                busy = socket.socket() if mode == 'busy' else None
                try:
                    if busy:
                        busy.bind(('127.0.0.1', port)); busy.listen()
                    with patch.object(launcher, 'ROOT', root), patch.dict(launcher.PORTS, {'strata': port}), \
                            patch.object(OwnedEngine, 'launch') as launch:
                        with self.assertRaises(OSError if mode == 'busy' else ValueError):
                            launcher.run('strata', False)
                        launch.assert_not_called()
                        self.assertEqual(receipt.read_text('utf-8'), raw)
                        if busy:
                            self.assertEqual(busy.getsockname()[1], port)
                        else:
                            self.assert_port_free(port)
                        # Failed startup released the exclusive OS lock as well.
                        with patch.object(launcher, 'run_locked', return_value='lock released'):
                            self.assertEqual(launcher.run('strata', False), 'lock released')
                finally:
                    if busy:
                        busy.close()

    def test_supervisor_crash_releases_lock_kills_child_and_allows_stale_reopen(self):
        with tempfile.TemporaryDirectory(prefix='haven-crash-test-') as directory:
            root = self.fixture_root(directory)
            port = free_port()
            receipt = root / '.local/launch-strata.json'
            argv = [sys.executable, '-c', SUPERVISOR, str(root), str(port), str(ROOT)]
            processes, handle = [], None
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
            kernel.OpenProcess.restype = W.HANDLE
            kernel.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
            kernel.WaitForSingleObject.restype = W.DWORD
            kernel.CloseHandle.argtypes = [W.HANDLE]
            kernel.CloseHandle.restype = W.BOOL
            try:
                first = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                processes.append(first)
                old = wait_for(lambda: json.loads(receipt.read_text('utf-8')))
                self.assertEqual(old['supervisor_pid'], first.pid)
                pid = wait_for(lambda: int((root / 'child.pid').read_text('utf-8')))
                handle = kernel.OpenProcess(0x100000, False, pid)
                self.assertTrue(handle)
                self.assertEqual(kernel.WaitForSingleObject(handle, 0), 258)
                duplicate = subprocess.run(argv, capture_output=True, timeout=6)
                self.assertNotEqual(duplicate.returncode, 0)
                self.assertEqual(json.loads(receipt.read_text('utf-8')), old)
                first.kill(); first.wait(timeout=5)
                self.assertEqual(kernel.WaitForSingleObject(handle, 5000), 0)
                self.assertTrue(receipt.exists())
                kernel.CloseHandle(handle); handle = None
                second = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                processes.append(second)

                def new_receipt():
                    current = json.loads(receipt.read_text('utf-8'))
                    return current if current['control_token'] != old['control_token'] else None

                fresh = wait_for(new_receipt)
                self.assertEqual(fresh['supervisor_pid'], second.pid)
                wait_for(lambda: int((root / 'child.pid').read_text('utf-8')) != pid)
                self.assertIsNone(second.poll())
                self.assertEqual(control_request(port, fresh['control_token']), 200)
                second.wait(timeout=6)
                self.assertEqual(second.returncode, 0)
                self.assertFalse(receipt.exists())
                self.assert_port_free(port)
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill(); process.wait(timeout=5)
                    process.stdout.close(); process.stderr.close()
                if handle:
                    kernel.CloseHandle(handle)


if __name__ == '__main__':
    unittest.main()
