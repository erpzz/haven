"""Offline regression tests for Haven task-family routing research."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'router_lab'))
import train_router as router

DATA = HERE / 'router_lab' / 'data' / 'haven_pr_routes_20261027.jsonl'


class DataTests(unittest.TestCase):
    def test_immutable_historical_split_and_provenance(self):
        rows = router.load_rows(DATA)
        self.assertEqual(len(rows), 36)
        self.assertEqual(len({x['pr'] for x in rows}), len(rows))
        self.assertTrue(all(x['pr'] < 65 for x in rows if x['split'] == 'train'))
        self.assertTrue(all(65 <= x['pr'] < 74 for x in rows if x['split'] == 'validation'))
        self.assertTrue(all(x['pr'] >= 74 for x in rows if x['split'] == 'test'))
        self.assertEqual({x['route'] for x in rows if x['split'] == 'train'}, set(router.LABELS))

    def test_train_vocabulary_ignores_future_prs(self):
        rows = router.load_rows(DATA)
        vocab = router.vocabulary([r for r in rows if r['split'] == 'train'])
        self.assertNotIn('w:secpatch', vocab)
        self.assertNotIn('w:jwt', vocab)
        self.assertIn('w:gpu', vocab)

    def test_refuse_bad_provenance_and_leakage(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'data.jsonl'
            rows = router.load_rows(DATA)
            rows[0]['source'] = 'https://example.net/fake'
            path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
            with self.assertRaisesRegex(ValueError, 'provenance'):
                router.load_rows(path)
            rows[0]['source'] = 'https://github.com/erpzz/haven/pull/25'
            rows[-1]['split'] = 'train'
            path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
            with self.assertRaisesRegex(ValueError, 'held-out'):
                router.load_rows(path)

    def test_rule_baseline_is_separate(self):
        self.assertEqual(router.baseline('LoRA adapter training'), 'training')
        self.assertEqual(router.baseline('TSZ trust and worker scheduling'), 'orchestration')
        self.assertEqual(router.baseline('Gateway chat UI bug'), 'inference')


class InferenceTests(unittest.TestCase):
    def setUp(self):
        self.model = {'schema': router.VERSION, 'labels': list(router.LABELS),
                      'vocabulary': ['w:training', 'w:chat'],
                      'weights': [[-1, 3], [3, -1], [0, 0]], 'bias': [0, 0, 0]}

    def test_unknown_task_abstains(self):
        self.assertEqual(router.predict_one(self.model, 'unknown protocol zzzz')['recommendation'], 'ABSTAIN')

    def test_known_training_task(self):
        self.assertEqual(router.predict_one(self.model, 'training')['recommendation'], 'training')

    def test_no_privileged_dispatch(self):
        p = router.predict_one(self.model, 'training')
        self.assertNotIn('execute', p)
        self.assertNotIn('node', p)
        self.assertNotIn('command', p)

    def test_requested_cuda_mode_fails_closed_without_gpu(self):
        try:
            import torch
        except ImportError:
            self.skipTest('torch not installed in stdlib CI environment')
        if torch.cuda.is_available():
            self.skipTest('CUDA worker can legitimately train')
        with tempfile.TemporaryDirectory() as d:
            done = subprocess.run([sys.executable, str(HERE / 'router_lab' / 'train_router.py'), 'train',
                                   '--device', 'cuda', '--data', str(DATA),
                                   '--output', str(Path(d) / 'weight.json'),
                                   '--report', str(Path(d) / 'report.json')],
                                  capture_output=True, text=True, timeout=15)
            self.assertNotEqual(done.returncode, 0)
            self.assertIn('No training performed', done.stderr)
            self.assertFalse((Path(d) / 'weight.json').exists())


if __name__ == '__main__':
    unittest.main()
