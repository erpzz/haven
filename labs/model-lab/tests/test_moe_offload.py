"""Catalog-gated MoE expert offload (--cpu-moe), with no GPU or external model calls.

All mocked launches are STATIC_TEST, not evidence of working inference on Slink.
"""
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from labcore import GIB, Lab, MIB, estimate_moe_fit, llama_command, ready_deadline_seconds

CATALOG = {'models': [{'id': 'moe', 'name': 'MOE FIXTURE', 'offload': 'cpu-moe', 'gpu_mib': 3000},
                      {'id': 'dense', 'name': 'DENSE FIXTURE'}]}
GPU = {'index': 0, 'memory_free_mib': 7800}


class MoeCommandTests(unittest.TestCase):
    def test_cpu_moe_flag_only_on_gpu_lane(self):
        gpu = llama_command(Path('e'), Path('m.gguf'), 9000, Path('k'), {'cpu_moe': True}, 0)
        self.assertIn('--cpu-moe', gpu)
        self.assertEqual(gpu[gpu.index('--n-gpu-layers') + 1], '999')
        cpu = llama_command(Path('e'), Path('m.gguf'), 9000, Path('k'), {'cpu_moe': True}, None)
        self.assertNotIn('--cpu-moe', cpu)

    def test_truthy_strings_do_not_enable_offload(self):
        args = llama_command(Path('e'), Path('m.gguf'), 9000, Path('k'), {'cpu_moe': 'yes'}, 0)
        self.assertNotIn('--cpu-moe', args)

    def test_moe_fit_checks_vram_and_ram(self):
        size = 22 * GIB
        self.assertEqual(estimate_moe_fit(size, 3000, 7800, 60, 32768)['status'], 'LIKELY_FITS')
        self.assertEqual(estimate_moe_fit(size, 3000, 3200, 60, 32768)['status'], 'TIGHT_OR_TOO_LARGE')
        # Strata resident (~54 GiB) leaves too little RAM for mmap'd experts.
        self.assertEqual(estimate_moe_fit(size, 3000, 7800, 10, 32768)['status'], 'TIGHT_OR_TOO_LARGE')
        self.assertEqual(estimate_moe_fit(size, 3000, None, 60, 32768)['status'], 'UNKNOWN')

    def test_deadline_grows_with_file_size(self):
        self.assertEqual(ready_deadline_seconds(0), 180)
        self.assertGreater(ready_deadline_seconds(22 * GIB), 180 + 22 * 1024 // 40)
        self.assertLess(ready_deadline_seconds(3 * GIB), 300)


class MoeLaneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.lab = Lab(Path(self.temp.name), catalog=CATALOG)
        model = Path(self.temp.name) / 'fixture.gguf'
        model.write_bytes(b'GGUFfixture')
        for mid, size in (('moe', 22 * GIB), ('dense', 22 * GIB)):
            self.lab.settings['models'][mid] = {'name': mid.upper(), 'path': str(model), 'size_bytes': size}

    def tearDown(self):
        self.lab.engine.proc = None
        self.lab.shutdown()
        self.temp.cleanup()

    def _start(self, model_id, overrides=None):
        class FakeProc:
            def poll(self):
                return None
        captured = {}
        def fake_launch(args, cwd, **kwargs):
            captured['args'] = args
            self.lab.engine.proc = FakeProc()
            self.lab.engine.record = {'state': 'STARTING', 'ownership': 'OWNED'}
        with patch.object(self.lab, 'llama_exe', return_value=Path('/fake/engine/llama-server')), \
             patch.object(self.lab, 'get_hardware', return_value={'gpus': [GPU], 'ram_available_gib': 60}), \
             patch.object(self.lab.engine, 'launch', side_effect=fake_launch), \
             patch('labcore.local_json', return_value={'data': [{'id': 'haven-local'}]}):
            jid = self.lab.start_llama(model_id, 'gpu', overrides)
            until = time.monotonic() + 3
            while self.lab.jobs[jid].snapshot()['state'] == 'RUNNING' and time.monotonic() < until:
                time.sleep(.01)
            self.assertEqual(self.lab.jobs[jid].snapshot()['state'], 'COMPLETED')
        return captured['args']

    def test_catalog_offload_model_admitted_with_cpu_moe(self):
        args = self._start('moe')
        self.assertIn('--cpu-moe', args)
        self.assertTrue(self.lab.public_state()['connection']['profile']['cpu_moe'])

    def test_dense_model_of_same_size_is_refused(self):
        with patch.object(self.lab, 'llama_exe', return_value=Path('/fake/llama-server')), \
             patch.object(self.lab, 'get_hardware', return_value={'gpus': [GPU], 'ram_available_gib': 60}):
            with self.assertRaisesRegex(ValueError, 'tight'):
                self.lab.start_llama('dense', 'gpu')
        self.assertIsNone(self.lab.engine.proc)

    def test_override_cannot_request_offload(self):
        self.lab.settings['models']['dense']['size_bytes'] = 2 * MIB
        args = self._start('dense', {'cpu_moe': True})
        self.assertNotIn('--cpu-moe', args)


if __name__ == '__main__':
    unittest.main()
