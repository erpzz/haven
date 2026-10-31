"""No-spend, opt-in placement preflight for Qwythos v2.

This refuses to infer actual shard memory from the number of layers. Its role is
strict admission of possible monolithic hosts vs appropriately qualified sharding.
No nodes are contacted and no payment or model downloads are performed.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

MODEL='empero-ai/Qwythos-9B-v2'
WEIGHTS_GIB={'Q5_K_M':6.08,'Q6_K':6.95,'Q8_0':8.87,'BF16':16.69}

@dataclass(frozen=True)
class Worker:
    id: str
    available_vram_gib: float
    available_ram_gib: float
    hourly_usd: float
    opted_in: bool
    consented_for_model: bool
    verified_hardware: bool
    supports_qwen35_hybrid: bool
    model_weights_verified: bool
    network_rtt_ms: float = 0.0
    # Unauthenticated advertisements cannot be used for execution.

    def valid(self):
        if not self.id or any(not math.isfinite(v) or v < 0 for v in (
                self.available_vram_gib,self.available_ram_gib,self.hourly_usd,self.network_rtt_ms)):
            raise ValueError('Invalid worker metadata')


def preflight(workers: list[Worker], *, precision='Q8_0', observed_model_vram_gib:float|None=None,
              max_hourly_usd=0.0, allow_remote=False, model_id=MODEL) -> dict:
    """Returns eligible *single-device* candidates; sharding is not established.

    Admission requires a measured VRAM peak for the exact model/engine/context.
    The published weight file size alone is insufficient for runtime admission.
    """
    if model_id != MODEL or precision not in WEIGHTS_GIB:
        raise ValueError('Only published higher-than-Q4 Qwythos v2 variants supported')
    if not math.isfinite(max_hourly_usd) or max_hourly_usd < 0:
        raise ValueError('Invalid budget')
    if observed_model_vram_gib is None or not math.isfinite(observed_model_vram_gib) or observed_model_vram_gib < WEIGHTS_GIB[precision]:
        return {'status':'NEEDS_REAL_MODEL_RUNTIME_MEMORY_MEASUREMENT','eligible':[],
                'note':'Weights sizes cannot be substituted for measured VRAM incl. KV/state/buffers.'}
    results=[]
    for node in workers:
        node.valid()
        reasons=[]
        if not (node.opted_in and node.consented_for_model):reasons.append('NOT_AUTHORIZED')
        if not node.verified_hardware:reasons.append('UNVERIFIED_HARDWARE')
        if not node.supports_qwen35_hybrid:reasons.append('INCOMPATIBLE_RUNTIME')
        if not node.model_weights_verified:reasons.append('WEIGHTS_NOT_VERIFIED')
        if node.available_vram_gib < observed_model_vram_gib:reasons.append('INSUFFICIENT_MEASURED_VRAM')
        if node.hourly_usd > max_hourly_usd:reasons.append('OVER_BUDGET')
        if node.network_rtt_ms > 0 and not allow_remote:reasons.append('REMOTE_NOT_AUTHORIZED')
        results.append({'id':node.id,'eligible':not reasons,'reasons':reasons,
                        'advertised_hourly_usd':node.hourly_usd})
    return {'status':'PREFLIGHT_ONLY_NO_RUNTIME_RESERVED', 'eligible':[r for r in results if r['eligible']],
            'rejected':[r for r in results if not r['eligible']],
            'note':'Do not equate one-device eligibility with measured inference speed.'}
