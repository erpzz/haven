"""Staged model admission and the haven.model-capability/v1 contract.

Synthetic GGUF headers only (no weights) and mocked engines. Nothing here downloads,
launches or contacts a model; these are STATIC_TEST results, not inference evidence.
"""
import http.client
import json
from pathlib import Path
import struct
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import model_admission as ma
from labcore import Lab, ROOT
from server import ADMIN_GETS, Server

CATALOG = json.loads((ROOT / 'catalog.json').read_text())
D1 = next(m for m in CATALOG['models'] if m['id'] == 'd1-2b')
CHAT = {'id': 'chat', 'name': 'CHAT FIXTURE', 'sha256': 'a' * 64, 'architecture': 'qwen35'}


def _s(text: str) -> bytes:
    raw = text.encode()
    return struct.pack('<Q', len(raw)) + raw


def gguf(meta: dict, vocab: int = 0) -> bytes:
    """A minimal GGUF v3 header: string/uint32/bool scalars plus an optional big array."""
    body = b''
    for key, value in meta.items():
        body += _s(key)
        if isinstance(value, bool):
            body += struct.pack('<I', 7) + struct.pack('<?', value)
        elif isinstance(value, int):
            body += struct.pack('<I', 4) + struct.pack('<I', value)
        else:
            body += struct.pack('<I', 8) + _s(value)
    pairs = len(meta)
    if vocab:
        body += _s('tokenizer.ggml.tokens') + struct.pack('<I', 9) + struct.pack('<I', 8) + struct.pack('<Q', vocab)
        body += b''.join(_s(f't{i}') for i in range(vocab))
        pairs += 1
    return b'GGUF' + struct.pack('<I', 3) + struct.pack('<Q', 0) + struct.pack('<Q', pairs) + body


D1_HEADER = {'general.architecture': 'lfm3', 'general.license.name': 'lfm1.0',
             'lfm3.context_length': 128000, 'lfm3.decision.type': 'lfm3-d1', 'lfm3.attention.causal': False}


class HeaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, data):
        p = self.dir / name
        p.write_bytes(data)
        return p

    def test_build_number_is_unknown_not_zero(self):
        self.assertEqual(ma.build_number('b11146'), 11146)
        for bad in (None, '', 'main', '11146', 'b11146-cuda'):
            self.assertIsNone(ma.build_number(bad))

    def test_decision_header_facts(self):
        facts = ma.cached_artifact_facts(self.write('d1.gguf', gguf(D1_HEADER, vocab=500)))
        self.assertEqual(facts, {'architecture': 'lfm3', 'decision_type': 'lfm3-d1',
                                 'context_length': 128000, 'license': 'lfm1.0'})

    def test_large_vocabulary_is_skipped_not_kept(self):
        meta = ma.read_gguf_metadata(self.write('v.gguf', gguf({'general.architecture': 'lfm3'}, vocab=5000)))
        self.assertEqual(meta['tokenizer.ggml.tokens'], {'array_of': 5000})

    def test_rejects_non_gguf_and_truncated(self):
        with self.assertRaisesRegex(ma.GGUFHeaderError, 'Not a GGUF'):
            ma.read_gguf_metadata(self.write('x.gguf', b'PK\x03\x04' + b'\0' * 64))
        data = gguf(D1_HEADER)
        with self.assertRaisesRegex(ma.GGUFHeaderError, 'truncated'):
            ma.read_gguf_metadata(self.write('t.gguf', data[:-5]))
        with self.assertRaisesRegex(ma.GGUFHeaderError, 'architecture'):
            ma.artifact_facts({'general.name': 'no arch'})


class LadderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.d1 = self.dir / 'd1.gguf'
        self.d1.write_bytes(gguf(D1_HEADER))
        self.chat = self.dir / 'chat.gguf'
        self.chat.write_bytes(gguf({'general.architecture': 'qwen35'}))

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_stops_at_cataloged(self):
        a = ma.assess(D1, artifact_path=self.dir / 'absent.gguf', engine_tag='b11946', engine_installed=True)
        self.assertEqual((a['stage'], a['blocked']), ('CATALOGED', 'ARTIFACT_MISSING'))

    def test_unreadable_and_mismatched_files(self):
        bad = self.dir / 'bad.gguf'
        bad.write_bytes(b'GGUFjunk')
        a = ma.assess(D1, artifact_path=bad, engine_tag='b11946', engine_installed=True)
        self.assertEqual(a['blocked'], 'ARTIFACT_UNREADABLE')
        a = ma.assess(D1, artifact_path=self.chat, engine_tag='b11946', engine_installed=True)
        self.assertEqual((a['stage'], a['blocked']), ('CATALOGED', 'ARTIFACT_MISMATCH'))

    def test_decision_entry_needs_decision_metadata(self):
        plain = self.dir / 'lfm3-chat.gguf'
        plain.write_bytes(gguf({'general.architecture': 'lfm3'}))
        a = ma.assess(D1, artifact_path=plain, engine_tag='b11946', engine_installed=True)
        self.assertEqual(a['blocked'], 'ARTIFACT_MISMATCH')

    def test_d1_on_slink_pinned_engine_is_unverified_runtime(self):
        a = ma.assess(D1, artifact_path=self.d1, engine_tag='b11146', engine_installed=True)
        self.assertEqual((a['stage'], a['blocked']), ('ARTIFACT_PRESENT', 'UNVERIFIED_MODEL_RUNTIME'))
        self.assertIn('b11945', a['reason'])
        self.assertFalse(a['chat_loadable'])

    def test_d1_on_new_engine_is_compatible_but_never_chat(self):
        a = ma.assess(D1, artifact_path=self.d1, engine_tag='b11946', engine_installed=True,
                      loaded_sha256=D1['sha256'])
        self.assertEqual((a['stage'], a['blocked']), ('RUNTIME_COMPATIBLE', 'NOT_CHAT_MODEL'))
        self.assertFalse(a['chat_loadable'])

    def test_chat_entry_pointing_at_a_decision_file_is_a_mismatch(self):
        a = ma.assess(CHAT | {'architecture': 'lfm3'}, artifact_path=self.d1, engine_tag='b11946',
                      engine_installed=True)
        self.assertEqual((a['stage'], a['blocked']), ('CATALOGED', 'ARTIFACT_MISMATCH'))
        self.assertIn('decision model', a['reason'])

    def test_unknown_engine_tag_is_not_compatible(self):
        a = ma.assess(D1, artifact_path=self.d1, engine_tag='custom', engine_installed=True)
        self.assertEqual(a['blocked'], 'UNVERIFIED_MODEL_RUNTIME')

    def test_engine_missing(self):
        a = ma.assess(CHAT, artifact_path=self.chat, engine_tag='b11146', engine_installed=False)
        self.assertEqual((a['stage'], a['blocked']), ('ARTIFACT_PRESENT', 'ENGINE_NOT_INSTALLED'))

    def test_chat_ladder_needs_loaded_sha_then_a_real_local_receipt(self):
        common = dict(artifact_path=self.chat, engine_tag='b11146', engine_installed=True)
        self.assertEqual(ma.assess(CHAT, **common)['stage'], 'LOADABLE')
        self.assertEqual(ma.assess(CHAT, loaded_sha256='b' * 64, **common)['stage'], 'LOADABLE')
        self.assertEqual(ma.assess(CHAT, loaded_sha256=CHAT['sha256'], **common)['stage'], 'LOADED')
        not_evidence = [
            {'model_sha256': CHAT['sha256'], 'state': 'COMPLETED', 'test_double': True},
            {'model_sha256': CHAT['sha256'], 'state': 'FAILED', 'test_double': False},
            {'model_sha256': CHAT['sha256'], 'state': 'COMPLETED', 'test_double': False, 'provider_id': 'mac-worker'},
            {'model_sha256': 'b' * 64, 'state': 'COMPLETED', 'test_double': False},
            {'model_sha256': CHAT['sha256'], 'state': 'COMPLETED'},  # unknown test_double is not False
        ]
        a = ma.assess(CHAT, loaded_sha256=CHAT['sha256'], receipts=not_evidence, **common)
        self.assertEqual(a['stage'], 'LOADED')
        real = not_evidence + [{'model_sha256': CHAT['sha256'], 'state': 'COMPLETED', 'test_double': False,
                                'provider_id': 'managed'}]
        a = ma.assess(CHAT, loaded_sha256=CHAT['sha256'], receipts=real, **common)
        self.assertEqual(a['stage'], 'VERIFIED_BY_INFERENCE')

    def test_receipt_without_loaded_engine_does_not_skip_stages(self):
        receipts = [{'model_sha256': CHAT['sha256'], 'state': 'COMPLETED', 'test_double': False}]
        a = ma.assess(CHAT, artifact_path=self.chat, engine_tag='b11146', engine_installed=True, receipts=receipts)
        self.assertEqual(a['stage'], 'LOADABLE')

    def test_recorded_off_host_receipts_are_provenance_only(self):
        a = ma.assess(D1, artifact_path=self.dir / 'absent.gguf', engine_tag='b11146', engine_installed=True)
        self.assertEqual(a['stage'], 'CATALOGED')
        self.assertTrue(a['recorded_receipts'])
        self.assertTrue(all('not Slink' in r['where'] for r in a['recorded_receipts']))


class ContractTests(unittest.TestCase):
    def test_every_catalog_entry_is_valid(self):
        for entry in CATALOG['models']:
            self.assertEqual(ma.validate_entry(entry), [], entry['id'])

    def test_d1_entry_declares_its_real_constraints(self):
        self.assertEqual(D1['interface'], 'systemone')
        self.assertEqual(D1['architecture'], 'lfm3')
        self.assertGreater(D1['runtime']['min_build'], ma.build_number(CATALOG['llama_tag']))
        self.assertEqual(D1['capabilities']['text_generation'], 'not_supported')
        self.assertRegex(D1['sha256'], r'^[0-9a-f]{64}$')
        self.assertTrue(D1['url'].endswith('/' + D1['filename']))
        self.assertIn(D1['revision'], D1['url'])

    def test_malformed_entries_are_reported(self):
        cases = [
            ({'id': 'x', 'interface': 'magic'}, 'interface'),
            ({'id': 'x', 'interface': 'systemone'}, 'declare its runtime'),
            ({'id': 'x', 'interface': 'systemone', 'runtime': {'backend': 'llama.cpp', 'question_types': ['text']}},
             'question_types'),
            ({'id': 'x', 'runtime': {'backend': 'vllm'}}, 'backend'),
            ({'id': 'x', 'runtime': {'backend': 'llama.cpp', 'min_build': '11945'}}, 'integer'),
            ({'id': 'x', 'architecture': 'lfm3', 'roles': ['oracle']}, 'unknown role'),
            ({'id': 'x', 'architecture': 'lfm3', 'capabilities': {'coding': 'trust me'}}, 'unknown evidence'),
            ({'id': 'x', 'roles': ['routing']}, 'architecture'),
            ({'id': 'x', 'verification': [{'where': 'w', 'runtime_build': 'b1', 'evidence': 'vendor_claim'}]},
             'measured'),
            ({'id': 'x', 'explanation': {'why': 'w', 'can': 'c'}}, 'explanation'),
        ]
        for entry, fragment in cases:
            problems = ma.validate_entry(entry)
            self.assertTrue(any(fragment in p for p in problems), (entry, problems))

    def test_router_view_never_trusts_vendor_claims_or_unloaded_models(self):
        view = ma.router_view(D1, {'stage': 'RUNTIME_COMPATIBLE', 'blocked': 'NOT_CHAT_MODEL'})
        self.assertIn('vision', view['untrusted_capabilities'])
        self.assertIn('typed_choice', view['trusted_capabilities'])
        self.assertNotIn('vision', view['trusted_capabilities'])
        self.assertFalse(view['usable_now'])
        self.assertTrue(ma.router_view(CHAT, {'stage': 'LOADED'})['usable_now'])
        self.assertEqual(view['contract'], 'haven.model-capability/v1')


class LabIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lab = Lab(Path(self.tmp.name))

    def tearDown(self):
        self.lab.shutdown()
        self.tmp.cleanup()

    def _register(self, model_id, data):
        p = Path(self.tmp.name) / f'{model_id}.gguf'
        p.write_bytes(data)
        self.lab.settings['models'][model_id] = {'path': str(p), 'name': model_id, 'size_bytes': len(data)}

    def test_start_refuses_decision_model_before_any_side_effect(self):
        self._register('d1-2b', gguf(D1_HEADER))
        launch, peers = MagicMock(), MagicMock(return_value=[])
        with patch.object(self.lab, 'llama_exe', return_value=Path('/fake/llama-server')), \
             patch.object(self.lab.engine, 'launch', launch), patch('gpu_lease.peer_busy', peers):
            with self.assertRaisesRegex(ValueError, 'not a chat model. Nothing was loaded'):
                self.lab.start_llama('d1-2b', 'gpu')
        launch.assert_not_called()
        peers.assert_not_called()
        self.assertIsNone(self.lab.engine.proc)
        self.assertFalse(self.lab.jobs)

    def test_start_refuses_imported_decision_gguf_without_catalog_entry(self):
        self._register('imported-d1', gguf(D1_HEADER))
        launch = MagicMock()
        with patch.object(self.lab, 'llama_exe', return_value=Path('/fake/llama-server')), \
             patch.object(self.lab.engine, 'launch', launch):
            with self.assertRaisesRegex(ValueError, 'lfm3-d1 decision model, not a chat model'):
                self.lab.start_llama('imported-d1', 'gpu')
        launch.assert_not_called()

    def test_unparseable_import_is_not_refused_by_header_check(self):
        p = Path(self.tmp.name) / 'odd.gguf'
        p.write_bytes(b'GGUFtest')
        self.assertIsNone(ma.file_refusal(p))

    def test_start_refuses_chat_model_newer_than_pinned_engine(self):
        self.lab.catalog = {'llama_tag': 'b11146', 'models': [
            {'id': 'lfm3', 'name': 'LFM3 FIXTURE', 'architecture': 'lfm3',
             'runtime': {'backend': 'llama.cpp', 'min_build': 11938}}]}
        self._register('lfm3', gguf({'general.architecture': 'lfm3'}))
        launch = MagicMock()
        with patch.object(self.lab, 'llama_exe', return_value=Path('/fake/llama-server')), \
             patch.object(self.lab.engine, 'launch', launch):
            with self.assertRaisesRegex(ValueError, 'b11938 or newer.*b11146'):
                self.lab.start_llama('lfm3', 'gpu')
        launch.assert_not_called()

    def test_admission_report_for_real_catalog(self):
        self._register('d1-2b', gguf(D1_HEADER))
        with patch.object(self.lab, 'llama_exe', return_value=Path('/fake/llama-server')):
            report = self.lab.model_admission()
        self.assertEqual(report['contract'], 'haven.model-capability/v1')
        self.assertEqual(report['engine'], {'tag': 'b11146', 'installed': True})
        rows = {r['id']: r for r in report['models']}
        self.assertEqual(set(rows), {m['id'] for m in CATALOG['models']})
        d1 = rows['d1-2b']
        self.assertEqual((d1['admission']['stage'], d1['admission']['blocked']),
                         ('ARTIFACT_PRESENT', 'UNVERIFIED_MODEL_RUNTIME'))
        self.assertFalse(d1['router_view']['usable_now'])
        self.assertEqual(rows['qwen35-4b']['admission']['blocked'], 'ARTIFACT_MISSING')
        self.assertTrue(all(r['admission']['contract_problems'] == [] for r in report['models']))

    def test_public_state_marks_decision_models(self):
        state = {m['id']: m for m in self.lab.public_state()['models']}
        self.assertEqual(state['d1-2b']['interface'], 'systemone')
        self.assertIn('cannot', state['d1-2b']['explanation'])


class EndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lab = Lab(Path(self.tmp.name))
        self.server = Server(('127.0.0.1', 0), self.lab)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.lab.shutdown()
        self.tmp.cleanup()

    def get(self, headers=None):
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        c.request('GET', '/api/model-admission', headers=headers or {})
        r = c.getresponse()
        out = (r.status, r.read())
        c.close()
        return out

    def test_admission_endpoint_is_admin_only_and_read_only(self):
        self.assertIn('/api/model-admission', ADMIN_GETS)
        self.assertEqual(self.get()[0], 401)
        status, body = self.get({'X-Lab-Token': self.lab.token})
        self.assertEqual(status, 200)
        report = json.loads(body)
        self.assertEqual(report['contract'], 'haven.model-capability/v1')
        self.assertFalse(self.lab.jobs)
        self.assertIsNone(self.lab.engine.proc)


if __name__ == '__main__':
    unittest.main()
