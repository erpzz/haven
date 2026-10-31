"""Fail-closed route qualification for HIVE.

This is a real scheduler *decision gate*, not a Qwythos executor. Only matching
observed workload/model/precision, trusted, fresh measurements may pass. A route
can regress after qualification; operational monitoring must still trip fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import statistics
import time
from typing import Iterable


@dataclass(frozen=True)
class Observation:
    route: str
    model_id: str
    weights_sha256: str
    precision: str
    workload_id: str
    ttft_ms: tuple[float, ...]
    request_ms: tuple[float, ...]
    output_tokens: int
    measured_at_unix: float
    provenance: str = 'UNVERIFIED'  # VERIFIED_RUNTIME needs independent attestation, not self-report
    environment: str = 'unknown'
    output_matches: bool = False
    dollars_per_request: float = 0.0
    verified_worker_ids: tuple[str, ...] = ()

    def validate(self):
        if (not self.route or not self.model_id or len(self.weights_sha256) != 64 or
            any(c not in '0123456789abcdef' for c in self.weights_sha256) or
            not self.workload_id or not self.precision or not self.environment):
            raise ValueError('Unidentified candidate or digest')
        if (not isinstance(self.output_tokens, int) or self.output_tokens <= 0 or
            len(self.ttft_ms) != len(self.request_ms) or not self.request_ms or
            any(not math.isfinite(x) or x <= 0 for x in self.ttft_ms + self.request_ms) or
            any(t > total for t, total in zip(self.ttft_ms, self.request_ms))):
            raise ValueError('Incomplete or invalid measurements')
        if (not math.isfinite(self.measured_at_unix) or
            not math.isfinite(self.dollars_per_request) or self.dollars_per_request < 0):
            raise ValueError('Invalid time or cost')
        if len(set(self.verified_worker_ids)) != len(self.verified_worker_ids):
            raise ValueError('Repeated worker identity')

    @property
    def median_ms(self):
        return statistics.median(self.request_ms)

    @property
    def p95_ms(self):
        ordered = sorted(self.request_ms)
        return ordered[math.ceil(.95 * len(ordered)) - 1]

    @property
    def ttft_p95_ms(self):
        ordered = sorted(self.ttft_ms)
        return ordered[math.ceil(.95 * len(ordered)) - 1]


@dataclass(frozen=True)
class Policy:
    min_samples: int = 5
    max_age_seconds: int = 3600
    relative_speed_slack: float = 0.0  # 0 = no measured regression permitted
    max_dollars_per_request: float = 0.0 # free-only until explicit operator override


def qualify(baseline: Observation, candidates: Iterable[Observation], policy: Policy = Policy(), *,
            now: float | None = None) -> dict:
    """Only select proven non-regressing routes; otherwise retain the baseline.

    Requires same workload/model/hash/precision/environment. Performance comparisons
    across different quantizations are NOT meaningful for preserving quality.
    Do not interpret a pass as a hard latency SLA or as cryptographic proof.
    """
    if policy.min_samples < 2 or policy.max_age_seconds <= 0 or not (0 <= policy.relative_speed_slack < 1):
        raise ValueError('Invalid policy')
    baseline.validate()
    now = time.time() if now is None else now
    failures = {}
    if baseline.provenance != 'VERIFIED_RUNTIME' or not baseline.output_matches:
        return {'selected': 'NONE', 'reason': 'NO_VERIFIED_BASELINE', 'rejected': {}}
    if len(baseline.request_ms) < policy.min_samples or not (0 <= now - baseline.measured_at_unix <= policy.max_age_seconds):
        return {'selected': baseline.route, 'reason': 'BASELINE_UNQUALIFIED_FOR_COMPARISON', 'rejected': {}}
    accepted = []
    for candidate in candidates:
        candidate.validate()
        issues = []
        if candidate.route == baseline.route:
            issues.append('DUPLICATE_BASELINE')
        if (candidate.model_id, candidate.weights_sha256, candidate.precision, candidate.workload_id, candidate.environment) != (baseline.model_id, baseline.weights_sha256, baseline.precision, baseline.workload_id, baseline.environment):
            issues.append('NOT_COMPARABLE')
        if candidate.provenance != 'VERIFIED_RUNTIME' or not candidate.output_matches or not candidate.verified_worker_ids:
            issues.append('UNVERIFIED_EXECUTION')
        if not (0 <= now - candidate.measured_at_unix <= policy.max_age_seconds):
            issues.append('STALE_OR_FUTURE')
        if len(candidate.request_ms) < policy.min_samples:
            issues.append('INSUFFICIENT_SAMPLES')
        if candidate.dollars_per_request > policy.max_dollars_per_request:
            issues.append('OVER_BUDGET')
        # Both tail request latency and first-token latency matter to responsiveness.
        if candidate.p95_ms > baseline.p95_ms * (1 + policy.relative_speed_slack):
            issues.append('SLOWER_P95')
        if candidate.ttft_p95_ms > baseline.ttft_p95_ms * (1 + policy.relative_speed_slack):
            issues.append('SLOWER_TTFT')
        if candidate.median_ms > baseline.median_ms * (1 + policy.relative_speed_slack):
            issues.append('SLOWER_MEDIAN')
        if issues:
            failures[candidate.route] = issues
        else:
            accepted.append(candidate)
    best = min(accepted, key=lambda r: (r.p95_ms, r.median_ms, r.dollars_per_request), default=None)
    if best is None:
        return {'selected': baseline.route, 'reason': 'ALL_REMOTE_CANDIDATES_REJECTED', 'rejected': failures}
    return {'selected': best.route, 'reason': 'MEASURED_NON_REGRESSION', 'rejected': failures,
            'p95_ms': best.p95_ms, 'baseline_p95_ms': baseline.p95_ms}
