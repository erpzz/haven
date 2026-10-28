"""Gateway contract: principal binding, routing policy, context limits, streaming, cancel, consent.
Uses the local FakeBackend TEST DOUBLE; no model or GPU is touched."""
import http.client
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from labcore import Lab
from server import Server
import base64
import hashlib
import hmac
from gateway import Gateway, CONSENT_COMMAND, JWT_SECRET_FILE
from fake_backend import FakeBackend

FAKE_TEXT = 'This is a local TEST DOUBLE response. Unicode: café ✓.'


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        data = Path(self.tmp.name)
        self.frontend = Gateway.issue_key(data, 'open-webui', 'frontend')
        self.owner = Gateway.issue_key(data, 'owner-cli', 'owner')
        self.member = Gateway.issue_key(data, 'kid-cli', 'member')
        # Production frontends always have an identity-signing secret.
        self.jwt_secret = b't' * 48
        (data / JWT_SECRET_FILE).write_bytes(self.jwt_secret)
        (data / JWT_SECRET_FILE).chmod(0o600)
        self.lab = Lab(data)
        self.backend = FakeBackend()
        self.lab.connect(self.backend.base, kind='llama')
        self.lab.connection['profile'] = {'context': 32768}
        self.server = Server(('127.0.0.1', 0), self.lab)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.backend.close(); self.tmp.cleanup()

    def headers(self, key, **extra):
        h = {'Host': f'127.0.0.1:{self.server.server_port}', 'Authorization': 'Bearer ' + key,
             'Content-Type': 'application/json'}
        h.update(extra)
        return h

    def owui(self, role='admin', uid='u-1', **extra):
        return self.headers(self.frontend, **{
            'X-OpenWebUI-User-Jwt': self.jwt(self.jwt_secret, sub=uid, role=role, name='Test'), **extra})

    def call(self, method, path, headers, body=None):
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=15)
        c.request(method, path, body=None if body is None else json.dumps(body).encode(), headers=headers)
        r = c.getresponse(); raw = r.read(); c.close()
        return r.status, raw

    def chat(self, headers, stream=False, **body):
        body.setdefault('model', 'haven-slink')
        body.setdefault('messages', [{'role': 'user', 'content': 'hello'}])
        status, raw = self.call('POST', '/v1/chat/completions', headers, {**body, 'stream': stream})
        if stream and status == 200:
            events = [json.loads(line[6:]) for line in raw.decode().splitlines()
                      if line.startswith('data: ') and line != 'data: [DONE]']
            self.assertTrue(raw.decode().rstrip().endswith('data: [DONE]'))
            return status, events
        return status, json.loads(raw)

    def settle(self):
        end = time.monotonic() + 8
        while self.lab.generation.locked() and time.monotonic() < end:
            time.sleep(.02)

    # -- authentication --------------------------------------------------
    def test_key_required(self):
        h = self.headers('nope'); h.pop('Authorization')
        self.assertEqual(self.call('GET', '/v1/models', h)[0], 401)
        self.assertEqual(self.call('GET', '/v1/models', self.headers('hvn-wrong'))[0], 401)

    def test_frontend_must_identify_approved_user(self):
        self.assertEqual(self.call('GET', '/v1/models', self.headers(self.frontend))[0], 403)
        self.assertEqual(self.call('GET', '/v1/models', self.owui(role='pending'))[0], 403)

    def jwt(self, secret, **claims):
        enc = lambda v: base64.urlsafe_b64encode(json.dumps(v).encode()).rstrip(b'=').decode()
        body = {'sub': 'u-9', 'role': 'admin', 'name': 'Owner', 'iss': 'open-webui', 'exp': time.time() + 60, **claims}
        head = enc({'alg': 'HS256', 'typ': 'JWT'}) + '.' + enc(body)
        sig = hmac.new(secret, head.encode(), hashlib.sha256).digest()
        return head + '.' + base64.urlsafe_b64encode(sig).rstrip(b'=').decode()

    def test_signed_identity_replaces_plain_headers(self):
        secret = b's' * 48
        path = Path(self.tmp.name) / JWT_SECRET_FILE
        path.write_bytes(secret); path.chmod(0o600)
        signed = self.headers(self.frontend, **{'X-OpenWebUI-User-Jwt': self.jwt(secret, role='user')})
        self.assertEqual(self.call('GET', '/v1/models', signed)[0], 200)
        self.assertEqual(self.chat(signed, model='haven-auto')[0], 403)
        self.assertEqual(self.chat(signed)[0], 200)
        # Plain role headers never grant anything, even if the key is otherwise valid.
        plain = self.headers(self.frontend, **{'X-OpenWebUI-User-Role': 'admin', 'X-OpenWebUI-User-Id': 'u-1'})
        self.assertEqual(self.call('GET', '/v1/models', plain)[0], 403)
        for bad in (self.jwt(b'x' * 48), self.jwt(secret, exp=time.time() - 1), self.jwt(secret, iss='other'),
                    self.jwt(secret)[:-3] + 'abc', 'not.a.jwt'):
            with self.subTest(bad=bad[-12:]):
                h = self.headers(self.frontend, **{'X-OpenWebUI-User-Jwt': bad})
                self.assertEqual(self.call('GET', '/v1/models', h)[0], 403)
        path.chmod(0o644)
        h = self.headers(self.frontend, **{'X-OpenWebUI-User-Jwt': self.jwt(secret)})
        self.assertEqual(self.call('GET', '/v1/models', h)[0], 503)

    def test_missing_identity_secret_fails_closed(self):
        self.assertEqual(self.call('GET', '/v1/models', self.owui())[0], 200)
        (Path(self.tmp.name) / JWT_SECRET_FILE).unlink()
        # Frontend must not silently fall back to spoofable X-OpenWebUI-User-Role.
        self.assertEqual(self.call('GET', '/v1/models', self.owui())[0], 503)
        plain = self.headers(self.frontend, **{'X-OpenWebUI-User-Id': 'u-1',
                                               'X-OpenWebUI-User-Role': 'admin'})
        self.assertEqual(self.call('GET', '/v1/models', plain)[0], 503)
        # Direct owner keys are independently bound and do not need frontend JWTs.
        self.assertEqual(self.call('GET', '/v1/models', self.headers(self.owner))[0], 200)

    def test_browser_origin_refused(self):
        self.assertEqual(self.call('GET', '/v1/models', self.owui(Origin='http://evil.example'))[0], 403)

    def test_lab_token_does_not_open_gateway(self):
        h = self.headers('x'); h.pop('Authorization'); h['X-Lab-Token'] = self.lab.token
        self.assertEqual(self.call('GET', '/v1/models', h)[0], 401)

    def test_keys_stored_as_digests_only(self):
        raw = (Path(self.tmp.name) / 'gateway-keys.json').read_text()
        self.assertNotIn(self.owner, raw); self.assertNotIn(self.frontend, raw)
        self.assertEqual((Path(self.tmp.name) / 'gateway-keys.json').stat().st_mode & 0o777, 0o600)

    # -- discovery and policy --------------------------------------------
    def test_member_sees_only_slink(self):
        status, raw = self.call('GET', '/v1/models', self.headers(self.member))
        self.assertEqual(status, 200)
        self.assertEqual([m['id'] for m in json.loads(raw)['data']], ['haven-slink'])
        status, raw = self.call('GET', '/v1/models', self.owui())
        self.assertEqual([m['id'] for m in json.loads(raw)['data']][:2], ['haven-slink', 'haven-auto'])

    def test_frontend_listing_is_stable_but_dispatch_is_role_checked(self):
        # Open WebUI caches one list for all accounts; who refreshed it must not change it.
        member_view = json.loads(self.call('GET', '/v1/models', self.owui(role='user'))[1])['data']
        owner_view = json.loads(self.call('GET', '/v1/models', self.owui())[1])['data']
        self.assertEqual(member_view, owner_view)
        self.assertEqual(self.chat(self.owui(role='user'), model='haven-auto')[0], 403)

    def test_model_name_reports_identity_and_context(self):
        rows = json.loads(self.call('GET', '/v1/models', self.headers(self.owner))[1])['data']
        self.assertEqual(rows[0]['haven']['context'], 32768)
        self.assertIn('TEST_DOUBLE', rows[0]['name'])
        self.assertEqual(rows[0]['haven']['route_type'], 'managed_alias')
        self.assertEqual(rows[1]['haven']['route_type'], 'automatic_alias')

    def test_member_cannot_route_to_auto(self):
        status, body = self.chat(self.owui(role='user'), model='haven-auto')
        self.assertEqual(status, 403); self.assertEqual(self.backend.requests, [])

    def test_status_is_role_filtered(self):
        owner = json.loads(self.call('GET', '/v1/haven/status', self.headers(self.owner))[1])
        member = json.loads(self.call('GET', '/v1/haven/status', self.headers(self.member))[1])
        self.assertIn('workers', owner); self.assertNotIn('workers', member)
        self.assertEqual(member['slink']['context'], 32768)

    # -- generation --------------------------------------------------------
    def test_streaming_relays_text_and_usage(self):
        status, events = self.chat(self.owui(), stream=True)
        self.assertEqual(status, 200)
        text = ''.join(e['choices'][0]['delta'].get('content', '') for e in events if e.get('choices'))
        self.assertEqual(text, FAKE_TEXT)
        self.assertEqual(events[-1]['choices'][0]['finish_reason'], 'stop')
        self.assertEqual(events[-1]['usage']['completion_tokens'], 12)
        trace = events[-1]['haven']['routing']
        self.assertEqual(trace['requested']['selector'], 'haven-slink')
        self.assertEqual(trace['resolved']['provider_id'], 'managed')
        self.assertEqual(trace['identity_attestation'], 'NOT_VERIFIED')

    def test_non_stream_and_receipt_without_content(self):
        status, body = self.chat(self.owui(), messages=[{'role': 'user', 'content': 'secret-prompt-text'}])
        self.assertEqual(status, 200)
        self.assertEqual(body['choices'][0]['message']['content'], FAKE_TEXT)
        self.assertEqual(body['haven']['provider_id'], 'managed')
        route = body['haven']['routing']
        self.assertEqual(route['requested'], {'selector': 'haven-slink', 'provider_id': 'managed'})
        self.assertEqual(route['resolved']['provider_id'], 'managed')
        self.assertEqual(route['fallback'], 'UNDETERMINED')
        receipts = (Path(self.tmp.name) / 'gateway-receipts.jsonl').read_text()
        self.assertNotIn('secret-prompt-text', receipts); self.assertNotIn(FAKE_TEXT, receipts)
        row = json.loads(receipts.splitlines()[-1])
        self.assertEqual((row['state'], row['role'], row['egress']), ('COMPLETED', 'owner', 'NONE'))
        self.assertEqual(row['requested_model_id'], 'haven-slink')

    def test_open_webui_multipart_text_is_flattened(self):
        msg = {'role': 'user', 'content': [{'type': 'text', 'text': 'a'}, {'type': 'text', 'text': 'b'}]}
        self.assertEqual(self.chat(self.owui(), messages=[msg])[0], 200)
        self.assertEqual(self.backend.requests[-1]['messages'][-1]['content'], 'a\nb')

    def test_images_refused_not_dropped(self):
        msg = {'role': 'user', 'content': [{'type': 'image_url', 'image_url': {'url': 'data:x'}}]}
        self.assertEqual(self.chat(self.owui(), messages=[msg])[0], 400)
        self.assertEqual(self.backend.requests, [])

    def test_legacy_functions_refused_explicitly(self):
        status, body = self.chat(self.owui(), functions=[{'name': 'x'}])
        self.assertEqual(status, 400); self.assertIn('tools', body['error']['message'])

    # -- structured tool calls -------------------------------------------
    TOOLS = [{'type': 'function', 'function': {'name': 'get_current_timestamp', 'parameters': {'type': 'object'}}}]

    def test_tool_calls_are_relayed_as_structured_deltas(self):
        self.backend.tool_call = True
        status, events = self.chat(self.owui(), stream=True, tools=self.TOOLS)
        self.assertEqual(status, 200)
        self.assertEqual(self.backend.requests[-1]['tools'], self.TOOLS)
        parts = [c for e in events if e.get('choices') for c in e['choices'][0]['delta'].get('tool_calls', [])]
        self.assertEqual(parts[0]['id'], 'call_1'); self.assertEqual(parts[0]['function']['name'], 'get_current_timestamp')
        self.assertEqual(''.join(c['function'].get('arguments', '') for c in parts), '{"tz": "UTC"}')
        self.assertEqual(events[-1]['choices'][0]['finish_reason'], 'tool_calls')
        row = json.loads((Path(self.tmp.name) / 'gateway-receipts.jsonl').read_text().splitlines()[-1])
        self.assertEqual((row['tool_calls'], row['tools_offered']), (['get_current_timestamp'], 1))
        self.assertNotIn('UTC', json.dumps(row))

    def test_tool_calls_non_stream(self):
        self.backend.tool_call = True
        status, body = self.chat(self.owui(), tools=self.TOOLS)
        msg = body['choices'][0]['message']
        self.assertEqual(msg['tool_calls'][0]['function']['arguments'], '{"tz": "UTC"}')
        self.assertEqual(body['choices'][0]['finish_reason'], 'tool_calls')

    def test_tool_result_turn_reaches_backend(self):
        msgs = [{'role': 'user', 'content': 'time?'},
                {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'call_1', 'type': 'function',
                 'function': {'name': 'get_current_timestamp', 'arguments': '{}'}}]},
                {'role': 'tool', 'tool_call_id': 'call_1', 'content': '2026-10-28T00:00:00Z'}]
        self.assertEqual(self.chat(self.owui(), messages=msgs, tools=self.TOOLS)[0], 200)
        sent = self.backend.requests[-1]['messages']
        self.assertEqual(sent[1]['tool_calls'][0]['id'], 'call_1')
        self.assertEqual((sent[2]['role'], sent[2]['tool_call_id']), ('tool', 'call_1'))

    def test_tools_dropped_not_sent_on_unverified_lane(self):
        self.lab.connection['kind'] = 'strata'
        self.assertEqual(self.chat(self.owui(), tools=self.TOOLS)[0], 200)
        self.assertNotIn('tools', self.backend.requests[-1])
        row = json.loads((Path(self.tmp.name) / 'gateway-receipts.jsonl').read_text().splitlines()[-1])
        self.assertTrue(row['tools_dropped'])
        msgs = [{'role': 'user', 'content': 'x'}, {'role': 'tool', 'tool_call_id': 'c', 'content': 'r'}]
        status, body = self.chat(self.owui(), messages=msgs, tools=self.TOOLS)
        self.assertEqual(status, 400); self.assertIn('verified only', body['error']['message'])

    def test_status_command_answers_locally(self):
        status, body = self.chat(self.owui(), messages=[{'role': 'user', 'content': '/haven status'}])
        text = body['choices'][0]['message']['content']
        self.assertIn('TEST_DOUBLE', text); self.assertIn('32,768-token context', text)
        self.assertEqual(self.backend.requests, [])

    # -- context-aware output limits (#72) --------------------------------
    def test_output_above_4096_allowed_when_context_permits(self):
        self.assertEqual(self.chat(self.owui(), max_tokens=12000)[0], 200)
        self.assertEqual(self.backend.requests[-1]['max_tokens'], 12000)

    def test_default_output_fills_remaining_context(self):
        self.lab.connection['profile'] = {'context': 4096}
        self.assertEqual(self.chat(self.owui())[0], 200)
        sent = self.backend.requests[-1]['max_tokens']
        self.assertTrue(3500 < sent < 4096, sent)

    def test_output_beyond_context_rejected_before_send(self):
        self.lab.connection['profile'] = {'context': 4096}
        status, body = self.chat(self.owui(), max_tokens=8000)
        self.assertEqual(status, 400); self.assertIn('4096-token context', body['error']['message'])
        self.assertEqual(self.backend.requests, [])

    def test_long_history_near_context_edge_reports_actionable_error(self):
        self.lab.connection['profile'] = {'context': 4096}
        history = [{'role': 'user', 'content': 'x' * 11800}]
        status, body = self.chat(self.owui(), messages=history)
        self.assertEqual(status, 400); self.assertIn('Start a new chat', body['error']['message'])
        self.assertEqual(self.backend.requests, [])

    def test_unknown_context_keeps_conservative_ceiling(self):
        self.lab.connection.pop('profile')
        status, body = self.chat(self.owui(), max_tokens=8000)
        self.assertEqual(status, 400); self.assertIn('did not report its context', body['error']['message'])
        self.assertEqual(self.chat(self.owui())[0], 200)
        self.assertEqual(self.backend.requests[-1]['max_tokens'], 2048)

    def test_lab_api_accepts_above_4096_with_context(self):
        jid = self.lab.generate({'messages': [{'role': 'user', 'content': 'x'}], 'max_tokens': 8192})
        self.settle(); self.assertEqual(self.lab.jobs[jid].snapshot()['state'], 'COMPLETED')

    # -- cancellation and queueing ----------------------------------------
    def test_client_disconnect_cancels_generation(self):
        self.backend.slow = True
        s = socket.create_connection(('127.0.0.1', self.server.server_port))
        body = json.dumps({'model': 'haven-slink', 'stream': True, 'messages': [{'role': 'user', 'content': 'hi'}]}).encode()
        head = ''.join(f'{k}: {v}\r\n' for k, v in self.owui().items())
        s.sendall(f'POST /v1/chat/completions HTTP/1.1\r\n{head}Content-Length: {len(body)}\r\n\r\n'.encode() + body)
        got = b''
        while b'content' not in got:
            got += s.recv(4096)
        s.close()
        self.settle()
        self.assertFalse(self.lab.generation.locked())
        job = [j.snapshot() for j in self.lab.jobs.values() if j.kind == 'generation'][-1]
        self.assertEqual(job['state'], 'CANCELLED')
        self.assertLess(len(job['text']), len(FAKE_TEXT))
        end = time.monotonic() + 12
        path = Path(self.tmp.name) / 'gateway-receipts.jsonl'
        while not path.exists() and time.monotonic() < end:
            time.sleep(.05)
        row = json.loads(path.read_text().splitlines()[-1])
        self.assertEqual(row['state'], 'CANCELLED')  # not the transient RUNNING seen before the fix
        self.assertIsNotNone(row['metrics'])

    def test_concurrent_requests_queue_for_the_gpu_slot(self):
        self.backend.slow = True
        results = []
        def go(uid):
            results.append(self.chat(self.owui(uid=uid))[0])
        threads = [threading.Thread(target=go, args=(f'u{i}',)) for i in range(2)]
        for t in threads: t.start()
        for t in threads: t.join(30)
        self.assertEqual(results, [200, 200])

    def test_backend_failure_is_reported_in_stream(self):
        self.backend.fail_status = 500
        status, events = self.chat(self.owui(), stream=True)
        self.assertEqual(status, 200)
        self.assertIn('Backend HTTP 500', events[-1]['error']['message'])
        self.assertFalse(self.lab.generation.locked())

    # -- hosted egress consent ---------------------------------------------
    def cloud_lane(self):
        row = {'id': 'cloud-test', 'label': 'Cloud · Test', 'display_model': 'Hosted Test', 'kind': 'cloud',
               'compute': 'hosted', 'max_context_tokens': 32768, 'locality': 'HOSTED_SUBSCRIPTION',
               'vendor': 'Anthropic', 'route_class': 'CLAUDE_CODE_PLAN', 'model_sha256': None,
               'observed': {'state': 'READY'}}
        conn = {'base': self.backend.base, 'key': '', 'model': 'haven-claude-code', 'display_model': 'Hosted Test',
                'kind': 'cloud', 'ownership': 'EXTERNAL', 'provider_id': 'cloud-test', 'worker_label': 'Cloud · Test',
                'compute': 'hosted', 'route_class': 'CLAUDE_CODE_PLAN', 'connected_at': 1,
                'profile': {'context': 32768, 'max_output_tokens': 4096, 'max_messages': 40}, 'route_reason': 'test'}
        return (patch.object(self.lab.providers, 'snapshot', return_value=[row]),
                patch.object(self.lab.providers, 'connection', return_value=conn))

    def test_hosted_lane_needs_per_chat_consent(self):
        snap, conn = self.cloud_lane()
        with snap, conn:
            members = json.loads(self.call('GET', '/v1/models', self.headers(self.member))[1])['data']
            self.assertNotIn('haven-cloud-test', [m['id'] for m in members])
            member_chat = self.owui(role='user', **{'X-OpenWebUI-Chat-Id': 'chat-m'})
            self.assertEqual(self.chat(member_chat, model='haven-cloud-test')[0], 403)
            self.assertEqual(self.chat(member_chat, model='haven-cloud-test',
                                       messages=[{'role': 'user', 'content': CONSENT_COMMAND}])[0], 403)
            chat = self.owui(**{'X-OpenWebUI-Chat-Id': 'chat-1'})
            status, body = self.chat(chat, model='haven-cloud-test')
            self.assertEqual(status, 200); self.assertIn('Nothing was sent', body['choices'][0]['message']['content'])
            self.assertEqual(self.backend.requests, [])
            consent = [{'role': 'user', 'content': CONSENT_COMMAND}]
            status, body = self.chat(chat, model='haven-cloud-test', messages=consent)
            self.assertIn('Consent recorded', body['choices'][0]['message']['content'])
            self.assertEqual(self.backend.requests, [])
            msgs = consent + [{'role': 'assistant', 'content': 'ok'}, {'role': 'user', 'content': 'go'}]
            self.assertEqual(self.chat(chat, model='haven-cloud-test', messages=msgs, max_tokens=512)[0], 200)
            sent = self.backend.requests[-1]['messages']
            self.assertNotIn(CONSENT_COMMAND, json.dumps(sent))
            other = self.owui(**{'X-OpenWebUI-Chat-Id': 'chat-2'})
            status, body = self.chat(other, model='haven-cloud-test')
            self.assertIn('Nothing was sent', body['choices'][0]['message']['content'])
            self.assertEqual(len(self.backend.requests), 1)


if __name__ == '__main__':
    unittest.main()
