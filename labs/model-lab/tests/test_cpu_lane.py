"""CPU lane admission and command isolation, with no GPU or external model calls.

All mocked launches are STATIC_TEST, not evidence of working inference on Slink.
"""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from labcore import Lab, llama_command, estimate_cpu_fit


class CpuCommandTests(unittest.TestCase):
    def test_explicit_cpu_has_zero_offload_and_no_cuda_device(self):
        args = llama_command(Path('llama-server'), Path('model.gguf'), 8879, Path('key'),
                             {'context': 2048, 'threads': 6}, gpu=None)
        self.assertEqual(args[args.index('--n-gpu-layers') + 1], '0')
        self.assertNotIn('--device', args)
        self.assertIn('--parallel', args)
        self.assertIn('127.0.0.1', args)

    def test_gpu_default_is_unchanged(self):
        args = llama_command(Path('llama-server'), Path('model.gguf'), 8879, Path('key'), {})
        self.assertEqual(args[args.index('--n-gpu-layers') + 1], '999')
        self.assertEqual(args[args.index('--device') + 1], 'CUDA0')

    def test_cpu_fit_reserves_ram_for_other_experiments(self):
        self.assertEqual(estimate_cpu_fit(3 * (1024**3), 48, 2048)['status'], 'LIKELY_FITS')
        self.assertEqual(estimate_cpu_fit(3 * (1024**3), 5, 2048)['status'], 'INSUFFICIENT_HEADROOM')
        self.assertEqual(estimate_cpu_fit(3 * (1024**3), None, 2048)['status'], 'UNKNOWN')


@unittest.skipUnless(sys.platform == 'linux', 'The first CPU lane implementation targets Linux')
class CpuLaneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.lab = Lab(Path(self.temp.name))
        self.model = Path(self.temp.name) / 'tiny-fixture.gguf'
        self.model.write_bytes(b'GGUFfixture')
        self.lab.settings['models']['fixture'] = {
            'name': 'FIXTURE', 'path': str(self.model), 'size_bytes': self.model.stat().st_size
        }

    def tearDown(self):
        # Fake child process in the success test is never a real process group.
        self.lab.engine.proc = None
        self.lab.shutdown()
        self.temp.cleanup()

    def test_cpu_starts_with_no_gpu_and_hidden_cuda_devices(self):
        class FakeProc:
            def poll(self):
                return None

        captured = {}
        def fake_launch(args, cwd, **kwargs):
            captured['args'], captured['env'], captured['cwd'] = args, kwargs['env'], cwd
            self.lab.engine.proc = FakeProc()
            self.lab.engine.record = {'state': 'STARTING', 'ownership': 'OWNED'}

        with patch.object(self.lab, 'llama_exe', return_value=Path('/fake/engine/llama-server')), \
             patch.object(self.lab, 'get_hardware', return_value={'gpus': [], 'ram_available_gib': 48}), \
             patch.object(self.lab.engine, 'launch', side_effect=fake_launch), \
             patch('labcore.local_json', return_value={'data': [{'id': 'haven-local'}]}):
            jid = self.lab.start_llama('fixture', 'cpu', compute='cpu')
            until = time.monotonic() + 3
            while self.lab.jobs[jid].snapshot()['state'] == 'RUNNING' and time.monotonic() < until:
                time.sleep(.01)
            result = self.lab.jobs[jid].snapshot()
            self.assertEqual(result['state'], 'COMPLETED', result)
            self.assertEqual(captured['args'][captured['args'].index('--n-gpu-layers') + 1], '0')
            self.assertNotIn('--device', captured['args'])
            self.assertEqual(captured['env']['CUDA_VISIBLE_DEVICES'], '-1')
            self.assertEqual(self.lab.public_state()['connection']['compute'], 'cpu')
            self.assertEqual(self.lab.public_state()['engine']['compute'], 'cpu')

    def test_low_ram_refused_without_credentials_or_process(self):
        with patch.object(self.lab, 'llama_exe', return_value=Path('/fake/llama-server')), \
             patch.object(self.lab, 'get_hardware', return_value={'gpus': [], 'ram_available_gib': 3}):
            with self.assertRaisesRegex(ValueError, 'Insufficient or unmeasured free RAM'):
                self.lab.start_llama('fixture', 'cpu', compute='cpu')
        self.assertFalse((self.lab.data / 'engine-key.txt').exists())
        self.assertIsNone(self.lab.engine.proc)

    def test_no_implicit_cpu_fallback_when_gpu_absent(self):
        with patch.object(self.lab, 'llama_exe', return_value=Path('/fake/llama-server')), \
             patch.object(self.lab, 'get_hardware', return_value={'gpus': [], 'ram_available_gib': 48}):
            with self.assertRaisesRegex(ValueError, 'explicitly selected'):
                self.lab.start_llama('fixture', 'balanced')
        self.assertIsNone(self.lab.engine.proc)

    def test_cpu_rejects_large_thread_count(self):
        with patch.object(self.lab, 'llama_exe', return_value=Path('/fake/llama-server')), \
             patch.object(self.lab, 'get_hardware', return_value={'gpus': [], 'ram_available_gib': 48}):
            with self.assertRaisesRegex(ValueError, 'CPU threads'):
                self.lab.start_llama('fixture', 'cpu', {'threads': 12}, compute='cpu')

    def test_cpu_rejects_memory_risk_override(self):
        with patch.object(self.lab, 'llama_exe', return_value=Path('/fake/llama-server')), \
             patch.object(self.lab, 'get_hardware', return_value={'gpus': [], 'ram_available_gib': 48}):
            with self.assertRaisesRegex(ValueError, 'override is GPU-only'):
                self.lab.start_llama('fixture', 'cpu', allow_tight=True, compute='cpu')

    def test_wrong_lane_profile_rejected(self):
        with patch.object(self.lab, 'llama_exe', return_value=Path('/fake/llama-server')):
            with self.assertRaisesRegex(ValueError, 'matching'):
                self.lab.start_llama('fixture', 'balanced', compute='cpu')

    def test_unknown_lane_rejected(self):
        with patch.object(self.lab, 'llama_exe', return_value=Path('/fake/llama-server')):
            with self.assertRaisesRegex(ValueError, 'Unknown compute lane'):
                self.lab.start_llama('fixture', 'cpu', compute='untrusted')

    def test_busy_engine_does_not_overwrite_existing_api_key(self):
        keyfile = self.lab.data / 'engine-key.txt'
        keyfile.write_text('existing-secret')
        self.lab.engine.proc = object()  # ownership guard, NOT a spawned process
        with self.assertRaisesRegex(ValueError, 'Unload the current'):
            self.lab.start_llama('fixture', 'cpu', compute='cpu')
        self.assertEqual(keyfile.read_text(), 'existing-secret')


if __name__ == '__main__':
    unittest.main()
