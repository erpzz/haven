"""Static boundary/lifecycle checks. Fake inference is never a real-model receipt."""
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

if sys.platform == 'win32':
    raise unittest.SkipTest('Linux-only host diagnostics and flock admission.')

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import diagnostics as d
import gpu_lease
import haven_runtime as runtime
from labcore import Job, Lab
from server import Server


class EvidenceTests(unittest.TestCase):
    def test_model_cannot_supply_command_or_path(self):
        with patch.object(d, 'run') as command:
            for name, arguments in [('bash', {}), ('haven_storage', {'command': 'id'}),
                                    ('haven_strata_history', {'path': '/etc/shadow'})]:
                with self.assertRaises(ValueError): d.dispatch(name, arguments)
            command.assert_not_called()

    def test_evidence_digest_covers_the_actual_data(self):
        with patch.object(d, 'storage', return_value={'observed': 480}):
            evidence = d.dispatch('haven_storage', {})
        content = {k: v for k, v in evidence.items() if k not in ('sha256', 'evidence_id')}
        self.assertEqual(evidence['sha256'], hashlib.sha256(d.canonical(content)).hexdigest())
        content['data']['observed'] = 10000
        self.assertNotEqual(evidence['sha256'], hashlib.sha256(d.canonical(content)).hexdigest())

    def test_forged_citation_is_a_warning_not_accepted_ground_truth(self):
        trace = [{'evidence': {'evidence_id': 'D-123456789abc'}}]
        with patch.object(d, 'dispatch') as execution:
            report = d.citation_report('Observed D-123456789abc; invented D-deadbeef0000', trace, True)
            self.assertEqual(report['unknown'], ['D-deadbeef0000'])
            self.assertTrue(report['warnings'])
            self.assertTrue(d.citation_report('An unsupported answer.', [], True)['warnings'])
            execution.assert_not_called()

    def test_history_keeps_wall_cpu_and_expert_rates_distinct(self):
        messages = [(0, 'Starting haven-strata.service - Haven'),
                    (1, 'Started haven-strata.service - Haven'),
                    (863, '[strata] experts loaded: 33.02 GiB at 0.04 GiB/s (836 s so far)'),
                    (868, 'ready: http://127.0.0.1:8880/v1'),
                    (879, 'haven-strata.service: Consumed 1min 27.292s CPU time, 54.0G memory peak, 0B memory swap peak.')]
        lines = '\n'.join(json.dumps({'__REALTIME_TIMESTAMP': str(at * 1000000), 'MESSAGE': text}) for at, text in messages)
        with patch.object(d, 'run', return_value=lines): report = d.strata_history([])['runs'][0]
        self.assertEqual(report['service_start_to_ready_seconds'], 868)
        self.assertEqual(report['whole_service_cpu_seconds'], 87.292)
        self.assertEqual(report['whole_service_swap_peak_bytes'], 0)
        self.assertAlmostEqual(report['effective_expert_mib_s'], 40.445, places=2)

    def test_restart_preserves_results_and_interrupts_without_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            store = d.Store(folder)
            one, two = 'a' * 24, 'b' * 24
            store.save({'id': one, 'state': 'COMPLETED', 'text': 'saved diagnosis'})
            store.save({'id': two, 'state': 'RUNNING'})
            reopened = d.Store(folder)
            self.assertEqual(reopened.get(one)['text'], 'saved diagnosis')
            self.assertEqual(reopened.get(two)['state'], 'INTERRUPTED')
            self.assertIsNone(reopened.get('../other-file'))
            if os.name != 'nt': self.assertEqual((store.path / (one + '.json')).stat().st_mode & 0o777, 0o600)


class AdmissionTests(unittest.TestCase):
    def test_real_flock_rejects_second_owner_and_releases(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(Path, 'home', return_value=Path(folder)), \
                patch.object(gpu_lease, 'peer_busy', return_value=[]), patch.object(gpu_lease, 'compute_pids', return_value=set()):
            first = gpu_lease.acquire()
            try:
                with self.assertRaisesRegex(ValueError, 'lease'): gpu_lease.acquire()
            finally: first.close()
            gpu_lease.acquire().close()

    def test_peer_or_unknown_process_blocks_without_stopping_it(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(Path, 'home', return_value=Path(folder)), \
                patch.object(gpu_lease, 'peer_busy', return_value=['teacher']), \
                patch.object(gpu_lease, 'systemctl') as control:
            with self.assertRaisesRegex(ValueError, 'Claude'): gpu_lease.acquire()
            control.assert_not_called()
        with tempfile.TemporaryDirectory() as folder, patch.object(Path, 'home', return_value=Path(folder)), \
                patch.object(gpu_lease, 'peer_busy', return_value=[]), patch.object(gpu_lease, 'compute_pids', return_value={222}):
            with self.assertRaisesRegex(ValueError, 'unowned'): gpu_lease.acquire(111)


class RuntimeTests(unittest.TestCase):
    def fake_lab(self):
        lab = Mock()
        lab.engine.proc = None
        lab.connection = None
        lab.lock = threading.RLock()
        lab.shutting_down = False
        return lab

    def test_cancel_stops_only_strata_started_by_this_switch(self):
        for initially_active in (False, True):
            with self.subTest(initially_active=initially_active):
                lab = self.fake_lab(); job = Job('runtime-switch'); state = {'active': initially_active}
                def change(action): state['active'] = action == 'start'
                def not_ready(**kwargs): job.cancel(); raise OSError('not ready')
                lab.connect_haven_strata.side_effect = not_ready
                with patch.object(gpu_lease, 'unit_state', side_effect=lambda unit: 'active' if state['active'] else 'inactive'), \
                        patch.object(gpu_lease, 'compute_pids', return_value=set()), patch.object(runtime, 'change_unit', side_effect=change) as changes:
                    lease = io.StringIO(); runtime.worker(lab, job, 'strata', lease, False)
                self.assertEqual(job.snapshot()['state'], 'CANCELLED')
                self.assertTrue(lease.closed)
                self.assertEqual(state['active'], initially_active)
                self.assertEqual(changes.call_count, 0 if initially_active else 2)

    def test_switch_rejects_extra_commands_before_admission(self):
        with patch.object(gpu_lease, 'acquire') as lease:
            with self.assertRaises(ValueError): runtime.start(self.fake_lab(), {'target': 'strata', 'command': 'anything'})
            lease.assert_not_called()


class DiagnosticTransportTests(unittest.TestCase):
    def test_native_tool_roundtrip_and_authenticated_disk_reconnect(self):
        calls = []
        class Backend(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                tools = [m for m in body['messages'] if m['role'] == 'tool']
                calls.append(body)
                if len(tools) < 2:
                    name = ('haven_storage', 'haven_strata_history')[len(tools)]
                    message = {'role': 'assistant', 'content': None, 'tool_calls': [
                        {'id': 'test-' + str(len(tools)), 'type': 'function',
                         'function': {'name': name, 'arguments': '{}'}}]}
                else:
                    ids = [json.loads(t['content'])['evidence_id'] for t in tools]
                    message = {'role': 'assistant', 'content': 'TEST_DOUBLE observed sources ' + ' '.join(ids)}
                data = json.dumps({'choices': [{'message': message, 'finish_reason': 'stop'}]}).encode()
                self.send_response(200); self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
        backend = ThreadingHTTPServer(('127.0.0.1', 0), Backend)
        bt = threading.Thread(target=backend.serve_forever, daemon=True); bt.start()
        with tempfile.TemporaryDirectory() as folder:
            lab = Lab(Path(folder))
            lab.connection = {'kind': 'llama', 'ownership': 'OWNED', 'model': 'TEST_DOUBLE',
                              'base': f'http://127.0.0.1:{backend.server_port}/v1', 'key': 'test-only'}
            server = Server(('127.0.0.1', 0), lab)
            st = threading.Thread(target=server.serve_forever, daemon=True); st.start()
            def request(path, body=None, token=True):
                c = http.client.HTTPConnection('127.0.0.1', server.server_port)
                headers = {'Host': f'127.0.0.1:{server.server_port}', 'Content-Type': 'application/json'}
                if token: headers['X-Lab-Token'] = lab.token
                c.request('POST' if body is not None else 'GET', path,
                          json.dumps(body) if body is not None else None, headers)
                r = c.getresponse(); data = json.loads(r.read()); code = r.status; c.close(); return code, data
            try:
                with patch.object(d.sys, 'platform', 'linux'), \
                        patch.object(lab.engine, 'status', return_value={'state': 'READY', 'pid': 123}), \
                        patch.object(gpu_lease, 'acquire', return_value=io.StringIO()), \
                        patch.object(d, 'storage', return_value={'classification': 'TEST_DOUBLE', 'link': 480}), \
                        patch.object(d, 'strata_history', return_value={'classification': 'TEST_DOUBLE', 'seconds': 868}):
                    code, value = request('/api/diagnostics', {'question': 'Test actual HTTP tool dispatch.'})
                    self.assertEqual(code, 200, value); jid = value['job_id']
                    end = time.monotonic() + 5
                    while lab.jobs[jid].snapshot()['state'] == 'RUNNING' and time.monotonic() < end: time.sleep(.01)
                    result = lab.jobs[jid].snapshot()
                    self.assertEqual(result['state'], 'COMPLETED', result)
                    self.assertEqual(len(result['trace']), 2)
                    self.assertEqual(result['citation_check']['unknown'], [])
                    self.assertEqual(len(calls), 3)
                    lab.jobs.clear()
                    self.assertEqual(request('/api/diagnostics/' + jid, token=False)[0], 401)
                    code, saved = request('/api/diagnostics/' + jid)
                    self.assertEqual(code, 200); self.assertEqual(saved['text'], result['text'])
                    self.assertEqual(len(calls), 3, 'Reading a durable receipt must not rerun inference.')
            finally:
                server.shutdown(); server.server_close(); st.join(3); lab.shutdown()
        backend.shutdown(); backend.server_close(); bt.join(3)


@unittest.skipUnless(hasattr(hashlib, 'scrypt'), 'Run real account-role checks on Ubuntu Python with scrypt.')
class HttpBoundaryTests(unittest.TestCase):
    def test_real_http_role_auth_and_saved_receipt_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            lab = Lab(Path(folder)); server = Server(('127.0.0.1', 0), lab, lan_mode=True)
            owner = server.auth.create_owner('owner', 'synthetic test password only')
            invitation = server.auth.create_invite(owner['id'])
            member = server.auth.accept_invite(invitation, 'member', 'another synthetic test password')
            owner_token, owner_csrf = server.auth.create_session(owner['id'])
            member_token, member_csrf = server.auth.create_session(member['id'])
            job = lab.new_job('diagnostic'); job.update(state='COMPLETED', question='PRIVATE QUESTION', trace=[{'private': 'HOST EVIDENCE'}])
            lab.diagnostic_store.save(job.snapshot())
            # Defense in depth even if a future caller assigns this job to a member.
            server.own_job(job.id, member['id'])
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            def request(path, token=None, post=None, csrf=None):
                connection = http.client.HTTPConnection('127.0.0.1', server.server_port)
                headers = {'Host': f'127.0.0.1:{server.server_port}'}
                if token: headers['Cookie'] = 'haven_session=' + token
                if csrf: headers['X-CSRF-Token'] = csrf
                if post is not None: headers['Content-Type'] = 'application/json'
                connection.request('POST' if post is not None else 'GET', path,
                                   json.dumps(post) if post is not None else None, headers)
                response = connection.getresponse(); raw = response.read().decode(); code = response.status
                connection.close(); return code, raw
            try:
                path = '/api/diagnostics/' + job.id
                self.assertEqual(request(path)[0], 401)
                self.assertEqual(request(path, member_token)[0], 403)
                self.assertEqual(request('/api/jobs/' + job.id, member_token)[0], 403)
                self.assertEqual(request('/api/diagnostics', member_token, {}, member_csrf)[0], 403)
                self.assertEqual(request('/api/runtime/switch', member_token, {'target': 'strata'}, member_csrf)[0], 403)
                self.assertNotIn('HOST EVIDENCE', request('/api/state', member_token)[1])
                self.assertNotIn('PRIVATE QUESTION', request('/api/state', member_token)[1])
                self.assertIn('HOST EVIDENCE', request(path, owner_token)[1])
                lab.jobs.clear()  # A reconnect retrieves disk evidence, without a model request.
                self.assertIn('HOST EVIDENCE', request(path, owner_token)[1])
            finally:
                server.shutdown(); server.server_close(); thread.join(3); lab.shutdown()


if __name__ == '__main__': unittest.main()
