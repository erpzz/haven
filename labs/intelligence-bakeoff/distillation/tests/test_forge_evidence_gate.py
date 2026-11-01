"""Offline regression tests for forge promotion evidence admission."""
import hashlib
import json
import pathlib
import tempfile
import unittest
import sys

FORGE = pathlib.Path(__file__).resolve().parents[1] / 'secpatch' / 'forge'
sys.path.insert(0, str(FORGE))
from evidence_gate import EvidenceError, verify_complete


def jsonl(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')


class EvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cycle = pathlib.Path(self.tmp.name)
        data = self.cycle / 'data'
        self.expected = {}
        hashes = {}
        for split in ('gate', 'eval-heldout'):
            rows = []
            for label in ('vulnerable', 'not_vulnerable'):
                rows.append({'id': f'{split}-{label}', 'key': split, 'task': 'detect', 'label': label})
            self.expected[split] = rows
            p = data / (split + '.jsonl')
            jsonl(p, rows)
            hashes[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
            for arm in ('student', 'base'):
                results = [{**r, 'score': 1, 'false_positive': False} for r in rows]
                jsonl(self.cycle / 'train' / 'eval' / arm / split / 'items.jsonl', results)
        (data / 'manifest.json').write_text(json.dumps({'sha256': hashes}))
        self.receipt = {'cycle': 0, 'finished': '2026-10-30T11:00:00Z', 'gpus': ['NVIDIA T4'],
                        'stages': {s: {'ok': True} for s in ('setup', 'train', 'merge_convert',
                                                           'eval_student', 'eval_base')}}
        self.write_receipt()

    def write_receipt(self):
        (self.cycle / 'train' / 'receipt.json').write_text(json.dumps(self.receipt))

    def test_complete_passes(self):
        student, base = verify_complete(self.cycle, 'base', cycle=0)
        self.assertEqual(len(student), 4)
        self.assertEqual(set(student), set(base))

    def test_missing_heldout_rejected(self):
        (self.cycle / 'train/eval/student/eval-heldout/items.jsonl').unlink()
        with self.assertRaisesRegex(EvidenceError, 'missing evidence file'):
            verify_complete(self.cycle, 'base', cycle=0)

    def test_partial_result_rejected(self):
        p = self.cycle / 'train/eval/student/gate/items.jsonl'
        jsonl(p, [{**self.expected['gate'][0], 'score': 1, 'false_positive': False}])
        with self.assertRaisesRegex(EvidenceError, 'incomplete student/gate'):
            verify_complete(self.cycle, 'base', cycle=0)

    def test_duplicate_id_rejected(self):
        p = self.cycle / 'train/eval/student/gate/items.jsonl'
        p.write_text(p.read_text() + p.read_text().splitlines()[0] + '\n')
        with self.assertRaisesRegex(EvidenceError, 'duplicate result ID'):
            verify_complete(self.cycle, 'base', cycle=0)

    def test_modified_label_rejected(self):
        p = self.cycle / 'train/eval/student/gate/items.jsonl'
        rows = [json.loads(x) for x in p.read_text().splitlines()]
        rows[0]['label'] = 'not_vulnerable'
        jsonl(p, rows)
        with self.assertRaisesRegex(EvidenceError, 'identity mismatch'):
            verify_complete(self.cycle, 'base', cycle=0)

    def test_frozen_split_tamper_rejected(self):
        p = self.cycle / 'data/gate.jsonl'
        p.write_text(p.read_text() + '\n')
        with self.assertRaisesRegex(EvidenceError, 'frozen split hash mismatch'):
            verify_complete(self.cycle, 'base', cycle=0)

    def test_failed_kernel_stage_rejected(self):
        self.receipt['stages']['eval_student']['ok'] = False
        self.write_receipt()
        with self.assertRaisesRegex(EvidenceError, 'missing/failed mandatory'):
            verify_complete(self.cycle, 'base', cycle=0)

    def test_skipped_training_rejected(self):
        self.receipt['stages']['train']['skipped'] = True
        self.write_receipt()
        with self.assertRaisesRegex(EvidenceError, 'missing/failed mandatory'):
            verify_complete(self.cycle, 'base', cycle=0)

    def test_missing_receipt_rejected(self):
        (self.cycle / 'train/receipt.json').unlink()
        with self.assertRaisesRegex(EvidenceError, 'missing/invalid CUDA training receipt'):
            verify_complete(self.cycle, 'base', cycle=0)

    def test_wrong_cycle_rejected(self):
        with self.assertRaisesRegex(EvidenceError, 'wrong or unfinished training cycle'):
            verify_complete(self.cycle, 'base', cycle=1)

    def test_failed_selfplay_stage_rejected(self):
        self.receipt['stages']['selfplay'] = {'ok': False}
        self.write_receipt()
        with self.assertRaisesRegex(EvidenceError, 'failed stage'):
            verify_complete(self.cycle, 'base', cycle=0)

    def test_eval_error_rejected(self):
        p = self.cycle / 'train/eval/base/gate/items.jsonl'
        rows = [json.loads(x) for x in p.read_text().splitlines()]
        rows[0]['error'] = 'TimeoutError'
        jsonl(p, rows)
        with self.assertRaisesRegex(EvidenceError, 'evaluation error'):
            verify_complete(self.cycle, 'base', cycle=0)

    def test_champion_required_if_requested(self):
        with self.assertRaisesRegex(EvidenceError, 'missing/failed mandatory'):
            verify_complete(self.cycle, 'champion', cycle=0)

    def test_empty_heldout_refused(self):
        p = self.cycle / 'data/eval-heldout.jsonl'
        p.write_text('')
        manifest = self.cycle / 'data/manifest.json'
        m = json.loads(manifest.read_text()); m['sha256'][p.name] = hashlib.sha256(b'').hexdigest()
        manifest.write_text(json.dumps(m))
        with self.assertRaisesRegex(EvidenceError, 'empty evidence file'):
            verify_complete(self.cycle, 'base', cycle=0)


if __name__ == '__main__':
    unittest.main()
