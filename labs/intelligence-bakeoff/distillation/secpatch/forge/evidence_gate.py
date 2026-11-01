"""Fail-closed evidence admission before forge model promotion.

Never select a model from a successful subset of a failed or incomplete evaluation.
Expected row IDs and attributes come from the frozen cycle dataset, not the model's
output files. No external services, GPU, or model weights are needed to verify coverage.
"""
from __future__ import annotations

import hashlib
import json
import pathlib


class EvidenceError(ValueError):
    """Missing, inconsistent, or unverifiable model-promotion evidence."""


def _records(path: pathlib.Path, *, measured: bool) -> dict:
    if not path.is_file():
        raise EvidenceError(f'missing evidence file: {path}')
    out = {}
    with path.open(encoding='utf-8') as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except (ValueError, TypeError) as exc:
                raise EvidenceError(f'invalid JSON in {path.name}:{line_no}') from exc
            if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k]
                                               for k in ('id', 'key', 'task', 'label')):
                raise EvidenceError(f'invalid row identity in {path.name}:{line_no}')
            rid = row['id']
            if rid in out:
                raise EvidenceError(f'duplicate result ID in {path.name}: {rid}')
            if measured:
                score = row.get('score')
                if type(score) not in (int, float) or score not in (0, 1):
                    raise EvidenceError(f'invalid score for {rid}')
                if row.get('error'):
                    raise EvidenceError(f'evaluation error for {rid}')
                if row['task'] == 'detect' and type(row.get('false_positive')) is not bool:
                    raise EvidenceError(f'missing detection FPR field for {rid}')
            out[rid] = row
    if not out:
        raise EvidenceError(f'empty evidence file: {path}')
    return out


def _verify_manifest(data: pathlib.Path):
    try:
        manifest = json.loads((data / 'manifest.json').read_text(encoding='utf-8'))
        hashes = manifest['sha256']
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise EvidenceError('missing/invalid frozen data manifest') from exc
    for name in ('gate.jsonl', 'eval-heldout.jsonl'):
        path = data / name
        if not path.is_file() or not isinstance(hashes.get(name), str):
            raise EvidenceError(f'missing expected split hash: {name}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[name]:
            raise EvidenceError(f'frozen split hash mismatch: {name}')


def verify_complete(cycle_dir: pathlib.Path, rival: str, *, cycle: int) -> tuple[dict, dict]:
    """Return (student, rival) only after checking both complete frozen eval sets.

    The kernel receipt must certify successful training, conversion and each required
    evaluation stage; all rows must match the immutable per-cycle split manifest.
    """
    if rival not in ('base', 'champion'):
        raise EvidenceError(f'invalid rival arm: {rival}')
    data = pathlib.Path(cycle_dir) / 'data'
    train = pathlib.Path(cycle_dir) / 'train'
    try:
        receipt = json.loads((train / 'receipt.json').read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError) as exc:
        raise EvidenceError('missing/invalid CUDA training receipt') from exc
    if not isinstance(receipt, dict) or receipt.get('cycle') != cycle or not receipt.get('finished'):
        raise EvidenceError('wrong or unfinished training cycle')
    if not isinstance(receipt.get('gpus'), list) or not any(receipt['gpus']):
        raise EvidenceError('missing CUDA GPU evidence')
    stages = receipt.get('stages')
    required = ('setup', 'train', 'merge_convert', 'eval_student', 'eval_' + rival)
    if not isinstance(stages, dict) or any(not isinstance(stages.get(k), dict) or stages[k].get('ok') is not True
                                           or stages[k].get('skipped') for k in required):
        raise EvidenceError('missing/failed mandatory train/evaluation stage')
    if any(not isinstance(v, dict) or v.get('ok') is not True for v in stages.values()):
        raise EvidenceError('failed stage in CUDA training receipt')
    _verify_manifest(data)

    student, baseline = {}, {}
    for split in ('gate', 'eval-heldout'):
        expected = _records(data / (split + '.jsonl'), measured=False)
        observed = []
        for arm in ('student', rival):
            actual = _records(train / 'eval' / arm / split / 'items.jsonl', measured=True)
            if set(actual) != set(expected):
                missing = len(set(expected) - set(actual))
                extra = len(set(actual) - set(expected))
                raise EvidenceError(f'incomplete {arm}/{split} coverage (missing={missing}, extra={extra})')
            for rid in expected:
                if any(actual[rid][k] != expected[rid][k] for k in ('key', 'task', 'label')):
                    raise EvidenceError(f'identity mismatch in {arm}/{split}: {rid}')
            observed.append(actual)
        if any(set(observed[0]) & set(previous) for previous in (student, baseline)):
            raise EvidenceError('duplicate IDs across evaluation splits')
        student.update(observed[0]); baseline.update(observed[1])
    return student, baseline
