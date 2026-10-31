from __future__ import annotations
from dataclasses import replace
import sys
from pathlib import Path
import time
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from hive.performance_gate import Observation, Policy, qualify

NOW=1782936000.0
DIGEST='b'*64


def o(route='local',dur=100,ttft=10,**kwargs):
    fields=dict(route=route,model_id='empero-ai/Qwythos-9B-v2',weights_sha256=DIGEST,precision='Q8_0',workload_id='test-set-hash',ttft_ms=(ttft,)*6,request_ms=(dur,)*6,output_tokens=128,measured_at_unix=NOW,provenance='VERIFIED_RUNTIME',environment='actual-2-host-gpu',output_matches=True,dollars_per_request=0.,verified_worker_ids=('worker1',))
    fields.update(kwargs)
    return Observation(**fields)

class PerfTests(unittest.TestCase):
    def test_improved_candidate_selected(self):
        self.assertEqual(qualify(o(),[o('remote',80,8,verified_worker_ids=('a','b'))],now=NOW)['selected'],'remote')
    def test_slow_remote_rejected(self):
        r=qualify(o(),[o('slow',110,8)],now=NOW)
        self.assertEqual(r['selected'],'local')
        self.assertIn('SLOWER_P95',r['rejected']['slow'])
    def test_ttft_regression_rejected(self):
        r=qualify(o(),[o('slowfirst',80,12)],now=NOW)
        self.assertEqual(r['selected'],'local')
        self.assertIn('SLOWER_TTFT',r['rejected']['slowfirst'])
    def test_precision_or_model_drift_rejected(self):
        r=qualify(o(),[o('wrong',80,8,precision='Q4_K_M')],now=NOW)
        self.assertIn('NOT_COMPARABLE',r['rejected']['wrong'])
    def test_cost_guard(self):
        r=qualify(o(),[o('paid',80,8,dollars_per_request=.01)],now=NOW)
        self.assertIn('OVER_BUDGET',r['rejected']['paid'])
    def test_self_report_rejected(self):
        r=qualify(o(),[o('untrusted',80,8,provenance='UNVERIFIED')],now=NOW)
        self.assertIn('UNVERIFIED_EXECUTION',r['rejected']['untrusted'])
    def test_stale_and_future_rejected(self):
        for stamp in (NOW-5000,NOW+10):
            r=qualify(o(),[o('stale',80,8,measured_at_unix=stamp)],now=NOW)
            self.assertIn('STALE_OR_FUTURE',r['rejected']['stale'])
    def test_insufficient_samples(self):
        r=qualify(o(),[o('few',80,8,ttft_ms=(8.,),request_ms=(80.,))],now=NOW)
        self.assertIn('INSUFFICIENT_SAMPLES',r['rejected']['few'])
    def test_missing_baseline_fails_closed(self):
        self.assertEqual(qualify(o(provenance='UNVERIFIED'),[o('remote',80,8)],now=NOW)['selected'],'NONE')
    def test_reject_invalid_observations(self):
        with self.assertRaises(ValueError):qualify(o(),[o('x',80,8,request_ms=(float('nan'),))],now=NOW)
        with self.assertRaises(ValueError):qualify(o(),[o('x',80,8,verified_worker_ids=('a','a'))],now=NOW)
    def test_monolithic_reference_insufficient_samples(self):
        r=qualify(o(request_ms=(100.,),ttft_ms=(10.,)),[o('remote',80,8)],now=NOW)
        self.assertEqual(r['selected'],'local')

if __name__=='__main__':unittest.main()
