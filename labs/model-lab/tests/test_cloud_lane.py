"""STATIC_TEST: the cloud lane end to end with fake official CLIs. No model, network or plan usage.

The fake executables replay the event shapes recorded from real Claude Code 2.1.310 and
Codex 0.142.3 runs, including hostile variants (tools, API-key auth, paid overage).
"""
import http.client
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
from labcore import Lab
from providers import Registry

spec = importlib.util.spec_from_file_location('cloud_worker', HERE.parents[3] / 'ops/haven-core/cloud-worker.py')
cw = importlib.util.module_from_spec(spec); spec.loader.exec_module(cw)

KEY = 'c' * 48
CLAUDE_OK = [
    {'type': 'system', 'subtype': 'init', 'tools': [], 'mcp_servers': [], 'apiKeySource': 'none', 'model': 'claude-sonnet-5-5'},
    {'type': 'stream_event', 'event': {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}}},
    {'type': 'stream_event', 'event': {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'TEST_DOUBLE '}}},
    {'type': 'stream_event', 'event': {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'cloud answer'}}},
    {'type': 'rate_limit_event', 'rate_limit_info': {'status': 'allowed', 'isUsingOverage': False}},
    {'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'TEST_DOUBLE cloud answer',
     'usage': {'input_tokens': 2, 'cache_read_input_tokens': 10, 'output_tokens': 4}},
]
CODEX_OK = [
    {'type': 'thread.started', 'thread_id': 't'},
    {'type': 'item.completed', 'item': {'id': 'item_0', 'type': 'error', 'message': 'Model metadata not found; using fallback.'}},
    {'type': 'turn.started'},
    {'type': 'item.completed', 'item': {'id': 'i0', 'type': 'reasoning', 'text': 'private'}},
    {'type': 'item.completed', 'item': {'id': 'i1', 'type': 'agent_message', 'text': 'TEST_DOUBLE codex answer'}},
    {'type': 'turn.completed', 'usage': {'input_tokens': 9, 'output_tokens': 5}},
]


def fake_cli(folder, name, events, sleep=0.0):
    """An executable that records argv/env/stdin, then replays events."""
    path = Path(folder) / name
    path.write_text(textwrap.dedent(f'''\
        #!{sys.executable}
        import json, os, sys, time
        prompt = sys.stdin.read()
        with open({str(Path(folder) / (name + '.seen'))!r}, 'w') as f:
            json.dump({{'argv': sys.argv, 'env': dict(os.environ), 'stdin': prompt, 'pid': os.getpid()}}, f)
        for e in json.loads({json.dumps(events)!r}):
            print(json.dumps(e), flush=True)
        time.sleep({sleep})
        '''))
    path.chmod(0o700)
    return str(path)


class CloudWorker:
    """The real cloud-worker HTTP handler on an ephemeral loopback port."""
    def __init__(self, folder, lanes, cap=50):
        self.folder = Path(folder)
        self.state = self.folder / 'state'; self.state.mkdir(mode=0o700)
        self.patch = patch.object(cw, 'STATE', self.state); self.patch.start()
        handler = cw.make_handler({'lanes': lanes, 'daily_cap': cap}, KEY, cw.Usage(cap), threading.Lock())
        self.server = cw.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
    def close(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(3); self.patch.stop()
    def enroll(self, ident='cloud-claude-code', model='haven-claude-code', route='CLAUDE_CODE_PLAN', **changes):
        row = {'id': ident, 'label': 'Cloud · Claude Code', 'node_id': 'synthetic-node',
               'base': f'http://127.0.0.1:{self.server.server_port}/v1', 'key': KEY, 'model': model,
               'display_model': 'TEST_DOUBLE cloud', 'kind': 'cloud', 'compute': 'hosted', 'route_class': route,
               'egress': 'HOSTED_SUBSCRIPTION', 'max_context_tokens': 32768, 'trust': 'OWNER_ENROLLED_SSH',
               'allowed_roles': ['admin'], 'enrolled_at': 123}
        row.update(changes)
        path = self.folder / 'providers'; path.mkdir(mode=0o700, exist_ok=True)
        file = path / (ident + '.json'); file.write_text(json.dumps(row)); file.chmod(0o600)
        return row
    def receipts(self):
        # The Lab finishes on [DONE]; the worker then writes its receipt and removes the turn directory.
        path, end = self.state / 'requests.jsonl', time.monotonic() + 5
        while (not path.exists() or any(p.name.startswith('turn-') for p in self.state.iterdir())) and time.monotonic() < end:
            time.sleep(.02)
        return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []


def run_job(lab, provider, content='Synthetic fixture only.', **extra):
    jid = lab.generate({'provider_id': provider, 'max_tokens': 2048,
                        'messages': [{'role': 'user', 'content': content}], **extra})
    end = time.monotonic() + 10
    while lab.jobs[jid].snapshot()['state'] == 'RUNNING' and time.monotonic() < end: time.sleep(.02)
    return lab.jobs[jid].snapshot()


class RegistryTests(unittest.TestCase):
    def test_cloud_is_labelled_hosted_and_never_automatic(self):
        with tempfile.TemporaryDirectory() as folder:
            worker = CloudWorker(folder, {'haven-claude-code': {'exe': fake_cli(folder, 'claude', CLAUDE_OK)}})
            try:
                worker.enroll(); registry = Registry(folder)
                row = registry.snapshot()[0]
                self.assertEqual((row['locality'], row['automatic'], row['vendor']), ('HOSTED_SUBSCRIPTION', False, 'Anthropic'))
                self.assertNotIn(KEY, json.dumps(registry.snapshot()))
                self.assertEqual(registry.probe('cloud-claude-code')['state'], 'READY')
                with self.assertRaisesRegex(ValueError, 'No eligible ready private'):
                    registry.choose('auto', {}, managed_ready=False)
                self.assertEqual(worker.receipts(), [], 'Automatic must never send a turn to the cloud.')
                conn = registry.choose('cloud-claude-code', {}, managed_ready=False)
                self.assertIn('left the house to Anthropic', conn['route_reason'])
                self.assertEqual(conn['profile']['max_output_tokens'], 4096)
            finally: worker.close()

    def test_cloud_enrollment_must_declare_egress(self):
        with tempfile.TemporaryDirectory() as folder:
            worker = CloudWorker(folder, {})
            try:
                for bad in ({'route_class': 'ANTHROPIC_API'}, {'egress': None}, {'compute': 'cuda'},
                            {'model_sha256': 'a' * 64}, {'allowed_roles': ['admin', 'member']}):
                    worker.enroll(**bad)
                    with self.assertRaises(ValueError, msg=bad): Registry(folder)
            finally: worker.close()


class LaneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.folder = self.tmp.name
    def tearDown(self):
        self.tmp.cleanup()
    def lab_with(self, events, cli='claude', sleep=0.0, cap=50, **enroll):
        lane = 'haven-claude-code' if cli == 'claude' else 'haven-codex-cli'
        self.worker = CloudWorker(self.folder, {lane: {'exe': fake_cli(self.folder, cli, events, sleep)}}, cap)
        ident = self.worker.enroll(ident='cloud-' + lane[6:], model=lane,
                                   route='CLAUDE_CODE_PLAN' if cli == 'claude' else 'CHATGPT_PLAN', **enroll)['id']
        self.lab = Lab(Path(self.folder))
        self.addCleanup(self.worker.close); self.addCleanup(self.lab.shutdown)
        return ident
    def seen(self, cli='claude'):
        return json.loads((Path(self.folder) / (cli + '.seen')).read_text())

    def test_claude_turn_streams_through_the_lab_with_tools_off_and_prompt_off_argv(self):
        ident = self.lab_with(CLAUDE_OK)
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'must-not-leak', 'OPENAI_API_KEY': 'must-not-leak'}):
            result = run_job(self.lab, ident, 'PRIVATE_PROMPT_MARKER')
        self.assertEqual(result['state'], 'COMPLETED', result)
        self.assertEqual(result['text'], 'TEST_DOUBLE cloud answer')
        self.assertEqual(result['metrics']['completion_tokens'], 4)
        self.assertIn('left the house', result['route_reason'])
        seen = self.seen()
        argv = seen['argv']
        self.assertEqual(argv[argv.index('--tools') + 1], '')
        for flag in ('--restricted', '--strict-mcp-config', '--disable-slash-commands', '--no-session-persistence'):
            self.assertIn(flag, argv)
        self.assertNotIn('PRIVATE_PROMPT_MARKER', json.dumps(argv), 'Prompts must not be visible in ps.')
        self.assertIn('PRIVATE_PROMPT_MARKER', seen['stdin'])
        self.assertFalse([k for k in seen['env'] if k.startswith(('ANTHROPIC_', 'OPENAI_'))])
        self.assertEqual(Path(seen['env']['TMPDIR']).parent, self.worker.state)
        receipt = self.worker.receipts()[-1]
        self.assertEqual(receipt['outcome'], 'COMPLETED')
        self.assertNotIn('PRIVATE_PROMPT_MARKER', json.dumps(self.worker.receipts()))
        self.assertFalse([p for p in self.worker.state.iterdir() if p.name.startswith('turn-')], 'Turn directory must be removed.')

    def test_history_is_quoted_and_system_text_goes_to_a_file(self):
        ident = self.lab_with(CLAUDE_OK)
        jid = self.lab.generate({'provider_id': ident, 'max_tokens': 256, 'messages': [
            {'role': 'system', 'content': 'SYSTEM_MARKER'}, {'role': 'user', 'content': 'first'},
            {'role': 'assistant', 'content': 'reply'}, {'role': 'user', 'content': 'second'}]})
        end = time.monotonic() + 10
        while self.lab.jobs[jid].snapshot()['state'] == 'RUNNING' and time.monotonic() < end: time.sleep(.02)
        seen = self.seen()
        self.assertIn('User: first\n\nAssistant: reply\n\nUser: second', seen['stdin'])
        self.assertNotIn('SYSTEM_MARKER', json.dumps(seen['argv']))
        self.assertIn('--system-prompt-file', seen['argv'])

    def test_contract_violations_stop_the_turn(self):
        cases = [
            ({'tools': ['Bash']}, 'attempted a tool or reported an error', 'REFUSED_502'),
            ({'mcp_servers': [{'name': 'x'}]}, 'attempted a tool or reported an error', 'REFUSED_502'),
            ({'apiKeySource': 'ANTHROPIC_API_KEY'}, 'bill an API key', 'REFUSED_402'),
        ]
        for change, message, outcome in cases:
            with self.subTest(change=change):
                self.tearDown(); self.setUp()
                ident = self.lab_with([{**CLAUDE_OK[0], **change}, *CLAUDE_OK[1:]])
                result = run_job(self.lab, ident)
                self.assertEqual(result['state'], 'FAILED', result)
                self.assertIn(message, result['error'])
                self.assertEqual(result['text'], '')
                self.assertEqual(self.worker.receipts()[-1]['outcome'], outcome)
                self.worker.close(); self.lab.shutdown()

    def test_paid_overage_or_limit_is_refused(self):
        ident = self.lab_with([CLAUDE_OK[0], {'type': 'rate_limit_event',
                               'rate_limit_info': {'status': 'allowed', 'isUsingOverage': True}}, *CLAUDE_OK[2:]])
        result = run_job(self.lab, ident)
        self.assertIn('plan limit', result['error'])
        self.assertEqual(self.worker.receipts()[-1]['outcome'], 'REFUSED_429')

    def test_tool_call_mid_stream_stops_and_keeps_partial(self):
        ident = self.lab_with([*CLAUDE_OK[:3], {'type': 'stream_event', 'event': {'type': 'content_block_start',
                               'content_block': {'type': 'tool_use', 'name': 'Bash'}}}, *CLAUDE_OK[3:]])
        result = run_job(self.lab, ident)
        self.assertEqual(result['state'], 'FAILED')
        self.assertIn('stopped the turn', result['error'])
        self.assertEqual(result['text'], 'TEST_DOUBLE ')

    def test_codex_lane_and_its_command_refusal(self):
        ident = self.lab_with(CODEX_OK, cli='codex')
        result = run_job(self.lab, ident)
        self.assertEqual((result['state'], result['text']), ('COMPLETED', 'TEST_DOUBLE codex answer'), result)
        argv = self.seen('codex')['argv']
        for feature in ('shell_tool', 'unified_exec', 'apps', 'plugins'):
            self.assertIn(feature, argv)
        self.assertEqual(argv[argv.index('-s') + 1], 'read-only')
        self.assertIn('--ignore-user-config', argv)
        self.tearDown(); self.setUp()
        ident = self.lab_with([*CODEX_OK[:3], {'type': 'item.started', 'item': {'type': 'command_execution', 'command': 'cat ~/.ssh/id'}},
                               *CODEX_OK[3:]], cli='codex')
        self.assertIn('attempted a tool', run_job(self.lab, ident)['error'])

    def test_codex_usage_limit_is_a_plan_refusal(self):
        ident = self.lab_with([CODEX_OK[0], {'type': 'turn.failed', 'error': {'message': "You've hit your usage limit."}}], cli='codex')
        self.assertIn('plan limit', run_job(self.lab, ident)['error'])
        self.assertEqual(self.worker.receipts()[-1]['outcome'], 'REFUSED_429')

    def test_codex_too_old_for_model_is_named(self):
        ident = self.lab_with([CODEX_OK[0], {'type': 'turn.failed', 'error': {'message':
            '{"status":400,"error":{"message":"The \'gpt-x\' model requires a newer version of Codex."}}'}}], cli='codex')
        run_job(self.lab, ident)
        self.assertIn('upgrade it', self.worker.receipts()[-1]['reason'])

    def test_daily_cap_refuses_without_running_the_cli(self):
        ident = self.lab_with(CLAUDE_OK, cap=1)
        self.assertEqual(run_job(self.lab, ident)['state'], 'COMPLETED')
        (Path(self.folder) / 'claude.seen').unlink()
        result = run_job(self.lab, ident)
        self.assertIn('daily cap', result['error'])
        self.assertFalse((Path(self.folder) / 'claude.seen').exists())

    def test_lab_cancel_kills_the_cli(self):
        ident = self.lab_with(CLAUDE_OK[:3], sleep=30)
        jid = self.lab.generate({'provider_id': ident, 'max_tokens': 256, 'messages': [{'role': 'user', 'content': 'x'}]})
        end = time.monotonic() + 10
        while not self.lab.jobs[jid].snapshot().get('text') and time.monotonic() < end: time.sleep(.02)
        pid = self.seen()['pid']
        self.lab.jobs[jid].cancel()  # What /api/cancel calls.
        end = time.monotonic() + 5
        while time.monotonic() < end:
            try: os.kill(pid, 0); time.sleep(.05)
            except ProcessLookupError: break
        else: self.fail('The fake CLI survived a Lab cancellation.')
        self.assertEqual(self.worker.receipts()[-1]['outcome'], 'CLIENT_CLOSED')

    def test_shim_rejects_bad_auth_and_non_streaming(self):
        self.lab_with(CLAUDE_OK)
        def post(headers, body):
            c = http.client.HTTPConnection('127.0.0.1', self.worker.server.server_port, timeout=5)
            c.request('POST', '/v1/chat/completions', json.dumps(body), headers); r = c.getresponse(); r.read(); c.close()
            return r.status
        body = {'model': 'haven-claude-code', 'stream': True, 'messages': [{'role': 'user', 'content': 'x'}]}
        self.assertEqual(post({'Authorization': 'Bearer wrong'}, body), 401)
        self.assertEqual(post({'Authorization': 'Bearer ' + KEY}, {**body, 'stream': False}), 400)
        self.assertEqual(post({'Authorization': 'Bearer ' + KEY}, {**body, 'model': 'other'}), 404)
        self.assertEqual(post({'Authorization': 'Bearer ' + KEY}, {**body, 'messages': [{'role': 'assistant', 'content': 'x'}]}), 400)
        self.assertFalse((Path(self.folder) / 'claude.seen').exists())


if __name__ == '__main__': unittest.main()
