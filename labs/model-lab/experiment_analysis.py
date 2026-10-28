"""Read-only aggregation of real Haven benchmark receipts.

Never grades model quality, starts inference, reads prompts or assumes equal hardware.
Scans at most the tail of a local JSONL receipt file; ignores malformed rows.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics

MAX_SCAN_BYTES = 8 * 1024 * 1024
MAX_LINE_BYTES = 100_000
MAX_ROWS = 2000
MAX_GROUPS = 80
COMPARABLE_SETTINGS = ('max_tokens', 'temperature', 'top_p', 'seed', 'reasoning')


def _number(value):
    if type(value) not in (float, int):
        return None
    result = float(value)
    return round(result, 3) if math.isfinite(result) and result >= 0 else None


def _median(rows, field):
    values = [_number((r.get('metrics') or {}).get(field)) for r in rows]
    good = [x for x in values if x is not None]
    return round(statistics.median(good), 3) if good else None


def _receipt_tail(path: Path):
    if not path.is_file():
        return [], False
    size = path.stat().st_size
    offset = max(0, size - MAX_SCAN_BYTES)
    with path.open('rb') as stream:
        stream.seek(offset)
        if offset:
            stream.readline()  # discard the first potentially partial line
        data = stream.read(MAX_SCAN_BYTES)
    # If the last line is partially written by a running benchmark, skip it.
    if data and not data.endswith(b'\n'):
        data = data.rsplit(b'\n', 1)[0] if b'\n' in data else b''
    records = []
    for raw in data.splitlines()[-MAX_ROWS:]:
        if len(raw) > MAX_LINE_BYTES:
            continue
        try:
            row = json.loads(raw)
        except (ValueError, UnicodeError):
            continue
        if isinstance(row, dict):
            records.append(row)
    return records, bool(offset)


def summarize(path: Path) -> dict:
    """Compare model variants only within identical prompt/config fingerprints.

    Prompt digests are identifiers, not performance or content guarantees.
    No benchmark is launched; all observations are from saved receipts.
    """
    records, truncated = _receipt_tail(path)
    by_suite = defaultdict(list)
    ignored = 0
    for row in records:
        prompt = row.get('prompt_sha256')
        settings = row.get('settings')
        if (not isinstance(prompt, str) or len(prompt) != 64
                or not all(c in '0123456789abcdef' for c in prompt)
                or not isinstance(settings, dict)
                or not isinstance(row.get('model'), str) or not row['model']
                or row.get('test_double')):
            ignored += 1
            continue
        canonical = {field: settings.get(field) for field in COMPARABLE_SETTINGS}
        if canonical['max_tokens'] is None:
            ignored += 1
            continue
        try:
            serialized = json.dumps(canonical, sort_keys=True, separators=(',', ':'), allow_nan=False)
        except (ValueError, TypeError):
            ignored += 1
            continue
        key = (prompt, hashlib.sha256(serialized.encode()).hexdigest()[:16])
        by_suite[key].append(row)
    groups = []
    for (prompt, config_id), suite in by_suite.items():
        by_variant = defaultdict(list)
        for row in suite:
            key = (row.get('model'), row.get('model_sha256'),
                   row.get('provider_id'), row.get('compute'), row.get('worker_label'))
            by_variant[key].append(row)
        variants = []
        for (model, sha, provider, compute, worker), rows in by_variant.items():
            completed = [r for r in rows if r.get('state') == 'COMPLETED']
            variants.append({
                'model': model, 'model_sha256': sha, 'provider_id': provider,
                'compute': compute, 'worker': worker, 'runs': len(rows),
                'completed': len(completed), 'incomplete': len(rows) - len(completed),
                'median_ttft_s': _median(completed, 'ttft_seconds'),
                'median_decode_tps': _median(completed, 'backend_decode_tps'),
                'median_end_to_end_tps': _median(completed, 'end_to_end_tps'),
            })
        variants.sort(key=lambda v: (-v['completed'], v['model'], str(v['provider_id'])))
        newest = max(float(r.get('at') or 0) for r in suite if type(r.get('at')) in (int, float)) if any(type(r.get('at')) in (int, float) for r in suite) else 0
        groups.append({'prompt_sha256': prompt, 'config_fingerprint': config_id,
                       'latest_at': newest, 'total_runs': len(suite), 'models': variants,
                       'eligible_for_cross_model_comparison': sum(v['completed'] > 0 for v in variants) >= 2})
    groups.sort(key=lambda g: (-int(g['eligible_for_cross_model_comparison']), -g['latest_at']))
    return {
        'schema': 'haven-experiment-summary-1',
        'scope': 'SAME_PROMPT_DIGEST_AND_GENERATION_SETTINGS',
        'quality_evaluated': False,
        'hardware_equivalence_verified': False,
        'history_truncated': truncated or len(records) >= MAX_ROWS,
        'records_examined': len(records), 'records_excluded': ignored,
        'total_groups': len(groups), 'groups': groups[:MAX_GROUPS],
        'note': 'Historical measurements only. Matching prompts/settings do not ensure identical hardware, model revisions or output quality.',
    }
