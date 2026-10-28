"""STATIC_TEST: the metered free-allowance lane end to end with a fake upstream provider.

No network, no provider account, no key. The upstream is a patched urlopen replaying
the SSE shapes Cloudflare Workers AI and Groq emit, including hostile variants
(rate limit, allowance refusal, credential rejection).
"""
import importlib.util
import json
import os
from pathlib import Path
import socketserver
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
from unittest.mock import patch

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
from labcore import Lab
from providers import PrivateWorkerConnection, Registry

spec = importlib.util.spec_from_file_location('metered_relay', HERE.parents[3] / 'ops/haven-core/metered-relay.py')
relay = importlib.util.module_from_spec(spec); spec.loader.exec_module(relay)

KEY = 'm' * 48
PROVIDER_KEY = 'upstream-secret-must-not-leak'
EVIDENCE = {'doc_url': 'https://developers.example/workers-ai/platform/pricing/',
            'clause': 'free daily allocation; over-limit requests fail on the free plan',
            'retrieved': '2026-10-28'}

CF_STREAM = [b'data: {"response":"TEST_DOUBLE "}\n', b'data: {"response":"metered answer"}\n', b'data: [DONE]\n']
GROQ_STREAM = [
    b'data: {"choices":[{"delta":{"content":"TEST_DOUBLE "}}]}\n',
    b'data: {"choices":[{"delta":{"content":"metered answer"}}]}\n',
    b'data: [DONE]\n',
]


class FakeUpstream:
    """Stands in for urlopen. Records calls so a test can prove no retry happened."""
    def __init__(self, lines=None, error=None, headers=None):
        self.lines, self.error, self.headers = lines or [], error, headers or {}
        self.calls = []

    def __call__(self, request, timeout=None):
        self.calls.append({'url': request.full_url, 'auth': request.headers.get('Authorization'),
                           'body': json.loads(request.data)})
        if self.error:
            raise self.error
        return self

    # Context-manager + iterator protocol of an http response.
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __iter__(self): return iter(self.lines)


def http_error(code):
    return urllib.error.HTTPError('https://upstream.example', code, 'refused', {}, None)


class Relay:
    """The real relay handler, bound on the enrollment directory's private socket."""
    def __init__(self, folder, vendor='cloudflare', model='@cf/test/model', boundary='NOT_CHARGEABLE'):
        self.folder = Path(folder)
        self.state = self.folder / 'state'; self.state.mkdir(mode=0o700)
        self.providers = self.folder / 'providers'; self.providers.mkdir(mode=0o700)
        self.patch = patch.object(relay, 'STATE', self.state); self.patch.start()
        relay.private_write(self.state / 'keys' / 'lane-key', PROVIDER_KEY)
        self.cfg = {'lane': 'metered-test', 'vendor': vendor, 'model': model,
                    'key_ref': 'lane-key', 'cost_boundary': boundary, 'account': 'acct-double'}
        self.handler = relay.make_handler(self.cfg, KEY)
        self.servers = []

    def socket(self, ident):
        path = self.providers / (ident + '.sock')
        if not path.exists():
            server = socketserver.ThreadingUnixStreamServer(str(path), self.handler)
            server.daemon_threads = True
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            self.servers.append((server, thread))
        return path

    def close(self):
        for server, thread in self.servers:
            server.shutdown(); server.server_close(); thread.join(3)
        self.patch.stop()

    def enroll(self, ident='metered-cf', route='CLOUDFLARE_WORKERS_AI_FREE', **changes):
        row = {'id': ident, 'label': 'Metered · Workers AI', 'node_id': 'synthetic-node',
               'base': 'http://127.0.0.1:8893/v1', 'socket_path': str(self.socket(ident)), 'key': KEY,
               'model': self.cfg['model'], 'display_model': 'TEST_DOUBLE metered', 'kind': 'metered',
               'compute': 'hosted', 'route_class': route, 'egress': 'METERED_FREE_ALLOWANCE',
               'cost_boundary': self.cfg['cost_boundary'], 'eligibility_evidence': dict(EVIDENCE),
               'max_context_tokens': 8192, 'trust': 'OWNER_ENROLLED_SSH',
               'allowed_roles': ['admin'], 'enrolled_at': 123}
        row.update(changes)
        file = self.providers / (ident + '.json'); file.write_text(json.dumps(row)); file.chmod(0o600)
        return row

    def receipts(self):
        path, end = self.state / 'requests.jsonl', time.monotonic() + 5
        while not path.exists() and time.monotonic() < end:
            time.sleep(.02)
        return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []


def post(socket_path, body, auth='Bearer ' + KEY):
    conn = PrivateWorkerConnection(socket_path, timeout=5)
    try:
        headers = {'Authorization': auth}
        unauthorized = auth != 'Bearer ' + KEY
        conn.request('POST', '/v1/chat/completions', None if unauthorized else json.dumps(body), headers)
        response = conn.getresponse()
        return response.status, response.read().decode('utf-8', 'replace')
    finally:
        conn.close()


TURN = {'model': '@cf/test/model', 'stream': True, 'max_tokens': 256,
        'messages': [{'role': 'user', 'content': 'Synthetic fixture only.'}]}


class RegistryTests(unittest.TestCase):
    def test_metered_is_labelled_and_never_automatic(self):
        with tempfile.TemporaryDirectory() as folder:
            r = Relay(folder)
            try:
                r.enroll(); registry = Registry(folder)
                row = registry.snapshot()[0]
                self.assertEqual((row['locality'], row['automatic'], row['vendor']),
                                 ('METERED_FREE_ALLOWANCE', False, 'Cloudflare'))
                self.assertEqual((row['cost_boundary'], row['boundary_enforceable']),
                                 ('NOT_CHARGEABLE', True))
                self.assertEqual(row['eligibility_evidence']['retrieved'], '2026-10-28')
                self.assertNotIn(KEY, json.dumps(registry.snapshot()))
                self.assertEqual(registry.probe('metered-cf')['state'], 'READY')
                # Automatic must not reach a metered lane, exactly as it must not reach a plan lane.
                with self.assertRaisesRegex(ValueError, 'No eligible ready private'):
                    registry.choose('auto', {}, managed_ready=False)
                self.assertEqual(r.receipts(), [], 'Automatic must never send a turn to a metered provider.')
                conn = registry.choose('metered-cf', {}, managed_ready=False)
                self.assertIn('free allowance', conn['route_reason'])
                self.assertIn('NOT_CHARGEABLE', conn['route_reason'])
                self.assertIn(EVIDENCE['doc_url'], conn['route_reason'])
                self.assertEqual(conn['profile']['max_output_tokens'], 2048)
            finally: r.close()

    def test_unenforceable_boundary_is_named_as_such(self):
        for boundary in ('PROVIDER_SOFT_ALERT', 'CLIENT_SIDE_ONLY'):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as folder:
                r = Relay(folder, boundary=boundary)
                try:
                    r.enroll(cost_boundary=boundary); registry = Registry(folder)
                    self.assertFalse(registry.snapshot()[0]['boundary_enforceable'])
                    reason = registry.choose('metered-cf', {}, managed_ready=False)['route_reason']
                    self.assertIn('NOT an enforceable boundary', reason)
                    self.assertIn('could bill', reason)
                finally: r.close()

    def test_metered_enrollment_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            r = Relay(folder)
            try:
                bad_rows = (
                    {'egress': 'HOSTED_SUBSCRIPTION'},          # a plan ack is not a metered ack
                    {'egress': None},
                    {'route_class': 'CLAUDE_CODE_PLAN'},        # plan class on a metered lane
                    {'route_class': 'ANTHROPIC_API'},           # still-unknown class
                    {'compute': 'cuda'},
                    {'model_sha256': 'a' * 64},                 # hosted lanes have no local digest
                    {'cost_boundary': None},
                    {'cost_boundary': 'PROBABLY_FINE'},
                    {'eligibility_evidence': None},
                    {'eligibility_evidence': {**EVIDENCE, 'doc_url': 'http://insecure.example'}},
                    {'eligibility_evidence': {**EVIDENCE, 'doc_url': 'https://ads.example/pricing-page'} | {'clause': ''}},
                    {'eligibility_evidence': {**EVIDENCE, 'retrieved': 'last tuesday'}},
                    {'allowed_roles': ['admin', 'member']},
                )
                for bad in bad_rows:
                    r.enroll(**bad)
                    with self.assertRaises(ValueError, msg=bad): Registry(folder)
            finally: r.close()


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.folder = self.tmp.name
    def tearDown(self):
        self.tmp.cleanup()

    def test_streams_cloudflare_shape(self):
        r = Relay(self.folder); self.addCleanup(r.close)
        upstream = FakeUpstream(CF_STREAM, headers={'x-ratelimit-remaining': '42'})
        with patch.object(relay.urllib.request, 'urlopen', upstream):
            status, text = post(r.socket('metered-cf'), TURN)
        self.assertEqual(status, 200)
        self.assertIn('TEST_DOUBLE ', text)
        self.assertIn('metered answer', text)
        self.assertIn('data: [DONE]', text)
        self.assertEqual(len(upstream.calls), 1)
        self.assertIn('acct-double', upstream.calls[0]['url'])
        self.assertEqual(r.receipts()[-1]['outcome'], 'COMPLETED')

    def test_streams_groq_shape_and_names_its_model_upstream(self):
        r = Relay(self.folder, vendor='groq', model='llama-test'); self.addCleanup(r.close)
        upstream = FakeUpstream(GROQ_STREAM)
        with patch.object(relay.urllib.request, 'urlopen', upstream):
            status, text = post(r.socket('metered-cf'), {**TURN, 'model': 'llama-test'})
        self.assertEqual(status, 200)
        self.assertIn('metered answer', text)
        self.assertEqual(upstream.calls[0]['body']['model'], 'llama-test')
        self.assertIn('api.groq.com', upstream.calls[0]['url'])

    def test_rate_limit_is_refused_and_never_retried(self):
        r = Relay(self.folder); self.addCleanup(r.close)
        upstream = FakeUpstream(error=http_error(429))
        with patch.object(relay.urllib.request, 'urlopen', upstream):
            status, text = post(r.socket('metered-cf'), TURN)
        self.assertEqual(status, 200)  # stream opened, then carried the refusal
        self.assertIn('rate-limited', text)
        self.assertIn('Nothing was retried', text)
        self.assertEqual(len(upstream.calls), 1, 'A rate limit must not be retried.')
        self.assertEqual(r.receipts()[-1]['outcome'], 'REFUSED_429')

    def test_allowance_refusal_and_credential_rejection_are_distinct(self):
        for code, outcome, phrase in ((402, 'REFUSED_402', 'outside the free allowance'),
                                      (403, 'REFUSED_402', 'outside the free allowance'),
                                      (401, 'REFUSED_401', 'rejected the lane credential')):
            with self.subTest(code=code):
                self.tearDown(); self.setUp()
                r = Relay(self.folder); self.addCleanup(r.close)
                upstream = FakeUpstream(error=http_error(code))
                with patch.object(relay.urllib.request, 'urlopen', upstream):
                    _, text = post(r.socket('metered-cf'), TURN)
                self.assertIn(phrase, text)
                self.assertEqual(len(upstream.calls), 1)
                self.assertEqual(r.receipts()[-1]['outcome'], outcome)

    def test_provider_key_never_leaves_the_relay(self):
        r = Relay(self.folder); self.addCleanup(r.close)
        upstream = FakeUpstream(CF_STREAM)
        with patch.object(relay.urllib.request, 'urlopen', upstream):
            _, text = post(r.socket('metered-cf'), TURN)
        self.assertIn(PROVIDER_KEY, upstream.calls[0]['auth'], 'The relay must authenticate upstream.')
        self.assertNotIn(PROVIDER_KEY, text, 'The provider key must never reach the Lab stream.')
        self.assertNotIn(PROVIDER_KEY, json.dumps(r.receipts()))
        registry = Registry(self.folder) if (r.enroll() or True) else None
        self.assertNotIn(PROVIDER_KEY, json.dumps(registry.snapshot()))

    def test_relay_rejects_bad_auth_model_and_non_streaming(self):
        r = Relay(self.folder); self.addCleanup(r.close)
        sock = r.socket('metered-cf')
        upstream = FakeUpstream(CF_STREAM)
        with patch.object(relay.urllib.request, 'urlopen', upstream):
            self.assertEqual(post(sock, TURN, auth='Bearer wrong')[0], 401)
            self.assertEqual(post(sock, {**TURN, 'stream': False})[0], 400)
            self.assertEqual(post(sock, {**TURN, 'model': 'other'})[0], 404)
            self.assertEqual(post(sock, {**TURN, 'messages': [{'role': 'assistant', 'content': 'x'}]})[0], 400)
            self.assertEqual(post(sock, {**TURN, 'max_tokens': 99999})[0], 400)
        self.assertEqual(upstream.calls, [], 'No rejected request may reach the provider.')


class EgressAckTests(unittest.TestCase):
    def test_metered_turn_needs_its_own_egress_acknowledgment(self):
        with tempfile.TemporaryDirectory() as folder:
            r = Relay(folder)
            lab = None
            try:
                ident = r.enroll()['id']
                lab = Lab(Path(folder))
                upstream = FakeUpstream(CF_STREAM)
                with patch.object(relay.urllib.request, 'urlopen', upstream):
                    # A subscription acknowledgment does not authorise a metered lane.
                    for ack in (None, 'HOSTED_SUBSCRIPTION', 'yes', 'metered_free_allowance'):
                        with self.subTest(ack=ack), self.assertRaisesRegex(ValueError, 'egress acknowledgment'):
                            lab.generate({'provider_id': ident, 'max_tokens': 64, 'egress_ack': ack,
                                          'messages': [{'role': 'user', 'content': 'x'}]})
                    self.assertEqual(upstream.calls, [], 'No turn may be sent without acknowledgment.')
            finally:
                if lab: lab.shutdown()
                r.close()


if __name__ == '__main__':
    unittest.main()
