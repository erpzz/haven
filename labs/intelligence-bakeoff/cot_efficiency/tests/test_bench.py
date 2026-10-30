import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import bench  # noqa: E402


def row(prompt, sha, n=100, wall=10.0, draft=None, acc=None, tps=12.0):
    return {'prompt': prompt, 'sha256': sha, 'predicted_n': n, 'wall_s': wall, 'draft_n': draft,
            'draft_accepted': acc, 'decode_tps': tps}


class CompareTests(unittest.TestCase):
    def test_speedup_identity_and_acceptance(self):
        results = [
            {'arm': 'A0', 'status': 'OK', 'rows': [row('p1', 'a'), row('p2', 'b')]},
            {'arm': 'A3', 'status': 'OK', 'rows': [row('p1', 'a', wall=5.0, draft=60, acc=45), row('p2', 'x', wall=5.0, draft=40, acc=25)]},
            {'arm': 'A9', 'status': 'SKIPPED_MODEL_MISSING', 'rows': []},
        ]
        t = {r['arm']: r for r in bench.compare(results, 'A0')}
        self.assertEqual(t['A0']['speedup_vs_baseline'], 1.0)
        self.assertEqual(t['A3']['speedup_vs_baseline'], 2.0)
        self.assertEqual(t['A3']['identical_to_baseline'], '1/2')   # a divergence is counted, not hidden
        self.assertEqual(t['A3']['draft_acceptance'], 0.7)
        self.assertIsNone(t['A9']['speedup_vs_baseline'])


if __name__ == '__main__':
    unittest.main()
