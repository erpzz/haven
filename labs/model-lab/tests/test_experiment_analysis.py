"""Offline tests: synthetic receipts only; never start models or access Slink."""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from experiment_analysis import summarize, _number


PROMPT_A = 'a' * 64
PROMPT_B = 'b' * 64


def row(model, *, prompt=PROMPT_A, seed=42, state='COMPLETED', at=1, decode=30, worker='Slink'):
    return {
        'prompt_sha256': prompt,
        'model': model, 'model_sha256': ('c' if model == 'A' else 'd') * 64,
        'provider_id': 'managed', 'worker_label': worker, 'compute': 'gpu',
        'settings': {'max_tokens': 256, 'temperature': 0.2, 'top_p': 0.8, 'seed': seed, 'reasoning': 'none'},
        'metrics': {'ttft_seconds': 0.5, 'backend_decode_tps': decode, 'end_to_end_tps': 21},
        'state': state, 'at': at, 'test_double': False,
    }


class ExperimentAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.tmp.name) / 'benchmarks.jsonl'

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, *items):
        with self.path.open('wb') as stream:
            for obj in items:
                stream.write((json.dumps(obj) if isinstance(obj, dict) else obj).encode() + b'\n')

    def test_nonexistent_history_is_empty_and_not_fake(self):
        result = summarize(self.path)
        self.assertEqual(result['groups'], [])
        self.assertFalse(result['quality_evaluated'])
        self.assertFalse(result['hardware_equivalence_verified'])

    def test_same_prompt_settings_compare_real_models_with_medians(self):
        self.write(row('A', at=1, decode=10), row('A', at=2, decode=30),
                   row('B', at=3, decode=60))
        result = summarize(self.path)
        self.assertEqual(result['records_examined'], 3)
        self.assertEqual(result['total_groups'], 1)
        group = result['groups'][0]
        self.assertTrue(group['eligible_for_cross_model_comparison'])
        variants = {m['model']: m for m in group['models']}
        self.assertEqual(variants['A']['median_decode_tps'], 20)
        self.assertEqual(variants['A']['runs'], 2)
        self.assertEqual(variants['B']['median_decode_tps'], 60)
        self.assertEqual(group['prompt_sha256'], PROMPT_A)

    def test_refuse_unsafe_cross_case_comparisons(self):
        self.write(row('A', prompt=PROMPT_A), row('B', prompt=PROMPT_B),
                   row('C', prompt=PROMPT_A, seed=43))
        result = summarize(self.path)
        self.assertEqual(result['total_groups'], 3)
        self.assertFalse(any(g['eligible_for_cross_model_comparison'] for g in result['groups']))

    def test_exclude_test_doubles_missing_digests_and_bad_numbers(self):
        dummy = row('D')
        dummy['test_double'] = True
        unnamed = row('B')
        unnamed.pop('prompt_sha256')
        bad = row('A', decode=-9)
        incomplete = row('B', state='FAILED')
        self.write(dummy, unnamed, bad, incomplete, 'not valid json')
        result = summarize(self.path)
        self.assertEqual(result['records_excluded'], 2)
        variants = {m['model']: m for m in result['groups'][0]['models']}
        self.assertIsNone(variants['A']['median_decode_tps'])
        self.assertEqual(variants['B']['completed'], 0)
        self.assertEqual(variants['B']['incomplete'], 1)
        self.assertFalse(result['groups'][0]['eligible_for_cross_model_comparison'])
        self.assertIsNone(_number(float('nan')))

    def test_malformed_metric_objects_and_timestamps_are_ignored(self):
        malformed = row('A', at=1)
        malformed['metrics'] = 'not-a-dict'
        malformed['at'] = float('nan')
        bad_field = row('B', at=2)
        bad_field['metrics']['backend_decode_tps'] = 'not-a-number'
        self.write(malformed, bad_field)
        result = summarize(self.path)
        self.assertEqual(result['total_groups'], 1)
        models = {v['model']: v for v in result['groups'][0]['models']}
        self.assertIsNone(models['A']['median_decode_tps'])
        self.assertIsNone(models['B']['median_decode_tps'])
        self.assertEqual(result['groups'][0]['latest_at'], 2)

    def test_partial_tail_is_not_processed(self):
        self.path.write_bytes((json.dumps(row('A')) + '\n' + json.dumps(row('B'))[:21]).encode())
        result = summarize(self.path)
        self.assertEqual(result['records_examined'], 1)
        self.assertEqual(result['groups'][0]['models'][0]['model'], 'A')


if __name__ == '__main__':
    unittest.main()
