"""STATIC_TEST: actual HTTP/auth/routing with a fake inference backend, no model."""
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from labcore import Lab
from providers import Registry
from server import Server


class WorkerFixture:
    def __enter__(self):
        self.calls = []
        calls = self.calls
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                calls.append(('GET', self.path, self.headers.get('Authorization')))
                code = 200 if self.headers.get('Authorization') == 'Bearer ' + 'k' * 48 else 401
                data = json.dumps({'data': [{'id': 'TEST_DOUBLE-worker'}]}).encode()
                self.send_response(code); self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append(('POST', self.path, self.headers.get('Authorization'), body))
                self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.end_headers()
                chunks = [{'choices': [{'delta': {'content': 'TEST_DOUBLE response'}, 'finish_reason': None}]},
                          {'choices': [{'delta': {}, 'finish_reason': 'stop'}], 'usage': {'completion_tokens': 3, 'prompt_tokens': 8}}]
                for obj in chunks: self.wfile.write(('data: ' + json.dumps(obj) + '\n\n').encode())
                self.wfile.write(b'data: [DONE]\n\n')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Backend)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        return self
    def __exit__(self, *args):
        self.server.shutdown(); self.server.server_close(); self.thread.join(3)
    def enrollment(self, directory, **changes):
        row = {'id': 'test-worker', 'label': 'Synthetic worker', 'node_id': 'synthetic-node',
               'base': f'http://127.0.0.1:{self.server.server_port}/v1', 'key': 'k' * 48,
               'model': 'TEST_DOUBLE-worker', 'display_model': 'TEST_DOUBLE', 'kind': 'llama',
               'compute': 'cpu', 'model_sha256': 'a' * 64, 'max_context_tokens': 2048,
               'trust': 'OWNER_ENROLLED_SSH', 'allowed_roles': ['admin'], 'enrolled_at': 123}
        row.update(changes)
        path = Path(directory) / 'providers'; path.mkdir(mode=0o700, exist_ok=True)
        file = path / 'test-worker.json'; file.write_text(json.dumps(row)); file.chmod(0o600)
        return row, file


class RegistryTests(unittest.TestCase):
    def test_enrollment_is_private_loopback_and_never_key_material_in_snapshot(self):
        with tempfile.TemporaryDirectory() as folder, WorkerFixture() as worker:
            _, path = worker.enrollment(folder)
            registry = Registry(folder)
            self.assertEqual(registry.snapshot()[0]['observed']['state'], 'UNKNOWN')
            self.assertEqual(worker.calls, [], 'Loading enrollment must not perform network or inference.')
            self.assertEqual(registry.probe('test-worker')['state'], 'READY')
            self.assertNotIn('k' * 48, json.dumps(registry.snapshot()))
            self.assertNotIn('base', registry.snapshot()[0])
            for base in ('http://192.168.1.1:8888/v1', 'https://example.com/v1', 'http://localhost:8888/v1',
                         'http://127.0.0.1:8888/v1?url=http://example.com'):
                worker.enrollment(folder, base=base)
                with self.assertRaises(ValueError): registry.reload()
            worker.enrollment(folder)
            if os.name != 'nt':
                path.chmod(0o644)
                with self.assertRaises(ValueError): Registry(folder)

    def test_explicit_offline_or_bad_auth_does_not_fallback(self):
        with tempfile.TemporaryDirectory() as folder, WorkerFixture() as worker:
            worker.enrollment(folder, key='wrong-key-' + 'x' * 40)
            registry = Registry(folder)
            with self.assertRaisesRegex(ValueError, 'AUTH_REJECTED'):
                registry.choose('test-worker', {'kind': 'llama'}, managed_ready=True)
            self.assertEqual([c[0] for c in worker.calls], ['GET'])
            self.assertNotIn('POST', [c[0] for c in worker.calls])

    def test_real_http_generation_keeps_managed_engine_and_records_worker(self):
        with tempfile.TemporaryDirectory() as folder, WorkerFixture() as worker:
            worker.enrollment(folder)
            lab = Lab(Path(folder)); managed = {'base': 'http://127.0.0.1:19999/v1', 'kind': 'llama',
                'ownership': 'OWNED', 'model': 'MANAGED_NOT_USED', 'key': 'other-key', 'connected_at': 1}
            lab.connection = managed
            try:
                jid = lab.generate({'provider_id': 'test-worker', 'max_tokens': 64,
                                    'messages': [{'role': 'user', 'content': 'Synthetic fixture only.'}]})
                end = time.monotonic() + 5
                while lab.jobs[jid].snapshot()['state'] == 'RUNNING' and time.monotonic() < end: time.sleep(.01)
                result = lab.jobs[jid].snapshot()
                self.assertEqual(result['state'], 'COMPLETED', result)
                self.assertEqual(result['provider_id'], 'test-worker')
                self.assertEqual(result['worker_label'], 'Synthetic worker')
                self.assertEqual(lab.connection, managed)
                self.assertEqual([c[0] for c in worker.calls], ['GET', 'POST'])
                self.assertEqual(worker.calls[-1][2], 'Bearer ' + 'k' * 48)
                self.assertNotIn('key', result)
                self.assertEqual(result['metrics']['completion_tokens'], 3)
            finally: lab.shutdown()

    def test_automatic_routing_never_loads_a_model_or_uses_hosted_endpoint(self):
        with tempfile.TemporaryDirectory() as folder, WorkerFixture() as worker:
            worker.enrollment(folder); registry = Registry(folder)
            conn = registry.choose('auto', {}, managed_ready=False)
            self.assertEqual(conn['provider_id'], 'test-worker')
            self.assertEqual([c[0] for c in worker.calls], ['GET'])
            self.assertEqual(registry.choose('auto', {'kind': 'llama', 'model': 'ready'}, managed_ready=True)['provider_id'], 'managed')


@unittest.skipUnless(hasattr(hashlib, 'scrypt'), 'Real LAN role fixture requires Ubuntu Python scrypt.')
class RoleTests(unittest.TestCase):
    def test_member_cannot_route_to_owner_worker_or_read_its_inventory(self):
        with tempfile.TemporaryDirectory() as folder, WorkerFixture() as worker:
            worker.enrollment(folder); lab = Lab(Path(folder)); server = Server(('127.0.0.1', 0), lab, lan_mode=True)
            owner = server.auth.create_owner('owner', 'synthetic password only')
            invite = server.auth.create_invite(owner['id'])
            member = server.auth.accept_invite(invite, 'member', 'another synthetic password')
            token, csrf = server.auth.create_session(member['id'])
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            def request(path, body=None):
                c = http.client.HTTPConnection('127.0.0.1', server.server_port)
                headers = {'Host': f'127.0.0.1:{server.server_port}', 'Cookie': 'haven_session=' + token,
                           'X-CSRF-Token': csrf, 'Content-Type': 'application/json'}
                c.request('POST' if body is not None else 'GET', path, json.dumps(body) if body is not None else None, headers)
                r = c.getresponse(); result = (r.status, r.read().decode()); c.close(); return result
            try:
                for provider in ('test-worker', 'auto'):
                    self.assertEqual(request('/api/generate', {'provider_id': provider, 'messages': []})[0], 403)
                self.assertEqual(request('/api/providers')[0], 403)
                self.assertEqual(request('/api/providers/reload', {})[0], 403)
                self.assertEqual(request('/api/providers/probe', {})[0], 403)
                self.assertNotIn('synthetic-node', request('/api/state')[1])
                self.assertNotIn('test-worker', request('/api/state')[1])
                self.assertEqual(worker.calls, [])
            finally:
                server.shutdown(); server.server_close(); thread.join(3); lab.shutdown()


if __name__ == '__main__': unittest.main()
