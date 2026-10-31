from __future__ import annotations
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hive.placement_guard import Worker, preflight


def worker(**kwargs):
    defaults=dict(id='local',available_vram_gib=24,available_ram_gib=30,hourly_usd=0,
        opted_in=True,consented_for_model=True,verified_hardware=True,
        supports_qwen35_hybrid=True,model_weights_verified=True,network_rtt_ms=0)
    defaults.update(kwargs)
    return Worker(**defaults)

class PlacementTests(unittest.TestCase):
    def test_measured_peak_required(self):
        r=preflight([worker()],precision='BF16')
        self.assertEqual(r['status'],'NEEDS_REAL_MODEL_RUNTIME_MEMORY_MEASUREMENT')
    def test_real_peak_can_admit(self):
        r=preflight([worker()],precision='BF16',observed_model_vram_gib=19)
        self.assertEqual([n['id'] for n in r['eligible']],['local'])
    def test_gpu_must_fit_peak(self):
        r=preflight([worker(available_vram_gib=18)],precision='BF16',observed_model_vram_gib=19)
        self.assertIn('INSUFFICIENT_MEASURED_VRAM',r['rejected'][0]['reasons'])
    def test_opt_in_and_weights_proof_mandatory(self):
        r=preflight([worker(opted_in=False,model_weights_verified=False)],precision='Q8_0',observed_model_vram_gib=10)
        self.assertEqual(r['eligible'],[])
        self.assertIn('NOT_AUTHORIZED',r['rejected'][0]['reasons'])
    def test_paid_rejected_by_default(self):
        r=preflight([worker(hourly_usd=.2)],precision='Q8_0',observed_model_vram_gib=10)
        self.assertIn('OVER_BUDGET',r['rejected'][0]['reasons'])
    def test_remote_requires_explicit_allow(self):
        r=preflight([worker(network_rtt_ms=12)],precision='Q8_0',observed_model_vram_gib=10)
        self.assertIn('REMOTE_NOT_AUTHORIZED',r['rejected'][0]['reasons'])
    def test_unmeasured_fake_peak_rejected(self):
        self.assertEqual(preflight([],precision='BF16',observed_model_vram_gib=1)['eligible'],[])
    def test_zero_cost_remote_possible_preflight_not_execution(self):
        r=preflight([worker(network_rtt_ms=12)],precision='Q8_0',observed_model_vram_gib=10,allow_remote=True)
        self.assertEqual(r['status'],'PREFLIGHT_ONLY_NO_RUNTIME_RESERVED')
        self.assertEqual(len(r['eligible']),1)

if __name__=='__main__':unittest.main()
