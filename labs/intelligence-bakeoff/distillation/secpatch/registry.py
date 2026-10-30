"""Versioned adapter registry with gated promotion and one-step rollback.

registry.json (private, next to the adapters) records every adapter with its
training receipt digest and evaluation summaries. Promotion requires a
held-out evaluation of the adapter *and* of its base on the same eval file
digest, with the adapter ahead on the primary metric and not worse on false
positives or detection recall. `rollback` restores the previously promoted
adapter (or none).
Nothing here loads a model or deploys a runtime; the gateway reads `promoted`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import time

PRIMARY = 'score'           # evaluate.py summary: mean task score over held-out items
GUARD = 'false_positive_rate'
RECALL = 'detection_recall'
DETECTION_COUNTS = ('detection_positive_n', 'detection_negative_n')


def passes_quality_gate(mine: dict, base: dict) -> bool:
    """Compare complete paired detection evidence; refuse missing or invalid metrics."""
    for label, summary in (('adapter', mine), ('base', base)):
        for metric in (PRIMARY, GUARD, RECALL):
            value = summary.get(metric)
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f'{label} evaluation lacks a valid {metric}; re-evaluate before promotion.')
        n = summary.get('n')
        counts = [summary.get(k) for k in DETECTION_COUNTS]
        by_task = summary.get('by_task')
        detect = by_task.get('detect') if isinstance(by_task, dict) else None
        detect_n = detect.get('n') if isinstance(detect, dict) else None
        if (type(n) is not int or n <= 0 or any(type(x) is not int or x <= 0 for x in counts)
                or type(detect_n) is not int or sum(counts) != detect_n or detect_n > n):
            raise ValueError(f'{label} evaluation needs positive and negative detection examples; '
                             're-evaluate before promotion.')
    if mine['n'] != base['n'] or any(mine[k] != base[k] for k in DETECTION_COUNTS):
        raise ValueError('Adapter and base evaluation counts do not match.')
    return mine[PRIMARY] > base[PRIMARY] and mine[GUARD] <= base[GUARD] and mine[RECALL] >= base[RECALL]


def load(root: pathlib.Path) -> dict:
    path = root / 'registry.json'
    return json.loads(path.read_text()) if path.exists() else {'adapters': {}, 'promoted': None, 'history': []}


def save(root: pathlib.Path, reg: dict):
    root.mkdir(parents=True, exist_ok=True)
    tmp = root / 'registry.json.tmp'
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(reg, f, indent=1)
    os.replace(tmp, root / 'registry.json')


def verify_training_artifacts(run_dir: pathlib.Path, receipt: dict) -> dict:
    """Verify CUDA receipt consistency and exact adapter bytes before registration.

    This is a provenance check, NOT an independent hardware attestation: a
    maliciously fabricated receipt remains possible. Verified model quality
    still requires the independent held-out evaluation gate.
    """
    if receipt.get('classification') != 'GPU_TRAINING_RUN' or receipt.get('device') != 'cuda':
        raise ValueError('Only actual CUDA-training receipts are registrable.')
    if receipt.get('execute') is not True:
        raise ValueError('Dry runs cannot be registered.')
    gpu = receipt.get('cuda_evidence')
    if not isinstance(gpu, dict):
        raise ValueError('Missing CUDA runtime evidence.')
    steps = receipt.get('optimizer_steps')
    if type(steps) is not int or steps < 1 or gpu.get('optimizer_steps') != steps:
        raise ValueError('CUDA training must complete verifiable optimizer steps.')
    for field in ('total_memory_bytes', 'peak_allocated_bytes', 'trainable_cuda_parameters'):
        value = gpu.get(field)
        if type(value) is not int or value <= 0:
            raise ValueError(f'Invalid CUDA {field} in receipt.')
    if not isinstance(gpu.get('device_name'), str) or not gpu['device_name'].strip():
        raise ValueError('CUDA device name is missing.')
    try:
        loss = float(receipt['train_loss'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Training loss missing or invalid.') from exc
    if not math.isfinite(loss):
        raise ValueError('Training loss must be finite.')
    adapter = run_dir / 'adapter'
    if adapter.is_symlink() or not (adapter / 'adapter_config.json').is_file():
        raise ValueError('Adapter config is missing or unsafe.')
    expected = receipt.get('adapter_weights_sha256')
    if not isinstance(expected, dict) or len(expected) != 1:
        raise ValueError('Exactly one hashed adapter weights file is required.')
    name, checksum = next(iter(expected.items()))
    if name not in ('adapter_model.safetensors', 'adapter_model.bin'):
        raise ValueError('Unexpected adapter weight format.')
    path = adapter / name
    if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
        raise ValueError('Adapter weights are absent, empty, or symlinked.')
    if not isinstance(checksum, str) or len(checksum) != 64 or any(x not in '0123456789abcdef' for x in checksum):
        raise ValueError('Invalid adapter weights checksum.')
    digest = hashlib.sha256()
    with path.open('rb') as reader:
        for block in iter(lambda: reader.read(1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != checksum:
        raise ValueError('Adapter weights do not match the recorded SHA-256.')
    return {'weight_file': name, 'weight_sha256': checksum, 'weight_bytes': path.stat().st_size,
            'cuda_device': gpu['device_name'], 'optimizer_steps': steps}


def register(root: pathlib.Path, run_dir: pathlib.Path, name: str) -> dict:
    receipt_path = run_dir / 'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    evidence = verify_training_artifacts(run_dir, receipt)
    reg = load(root)
    if name in reg['adapters']:
        raise ValueError('Adapter names are immutable; choose a new version name.')
    reg['adapters'][name] = {'path': str(run_dir / 'adapter'), 'base_model': receipt['base_model'],
                             'base_revision': receipt['base_revision'], 'data_sha256': receipt['data_sha256'],
                             'receipt_sha256': hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                             'registered_at': time.time(), 'evals': {}, 'gpu_receipt': evidence}
    save(root, reg)
    return reg['adapters'][name]


def attach_eval(root: pathlib.Path, name: str, summary_path: pathlib.Path) -> dict:
    reg = load(root)
    summary = json.loads(summary_path.read_text())
    target = reg['adapters'].get(name) if name != 'base' else reg.setdefault('base_evals', {})
    if target is None:
        raise ValueError('Unknown adapter.')
    evals = target if name == 'base' else target['evals']
    evals[summary['eval_sha256']] = {k: summary[k] for k in
                                    (PRIMARY, GUARD, RECALL, *DETECTION_COUNTS, 'n', 'model', 'by_task')
                                    if k in summary}
    save(root, reg)
    return evals[summary['eval_sha256']]


def promote(root: pathlib.Path, name: str, eval_sha256: str, force: bool = False) -> dict:
    reg = load(root)
    entry = reg['adapters'].get(name)
    if not entry:
        raise ValueError('Unknown adapter.')
    mine, base = entry['evals'].get(eval_sha256), reg.get('base_evals', {}).get(eval_sha256)
    if not force:
        if not mine or not base:
            raise ValueError('Promotion needs adapter and base evaluations on the same held-out file.')
        if not passes_quality_gate(mine, base):
            raise ValueError(f"Gate failed: score {mine[PRIMARY]} vs base {base[PRIMARY]}, "
                             f"FPR {mine[GUARD]} vs {base[GUARD]}, "
                             f"recall {mine[RECALL]} vs {base[RECALL]}. Not promoted.")
    reg['history'].append({'at': time.time(), 'from': reg['promoted'], 'to': name, 'eval_sha256': eval_sha256, 'forced': force})
    reg['promoted'] = name
    save(root, reg)
    return {'promoted': name}


def rollback(root: pathlib.Path) -> dict:
    reg = load(root)
    if not reg['history']:
        raise ValueError('Nothing to roll back.')
    last = reg['history'][-1]
    reg['history'].append({'at': time.time(), 'from': reg['promoted'], 'to': last['from'], 'rollback': True})
    reg['promoted'] = last['from']
    save(root, reg)
    return {'promoted': reg['promoted']}


def card(root: pathlib.Path, manifest: pathlib.Path | None = None) -> dict:
    """Read-only metadata for the Haven gateway: what is promoted, from what base and data, with which results.

    The gateway lists a specialist only when a card says one is promoted; it never reads adapters or data itself."""
    reg = load(root)
    name = reg['promoted']
    out = {'schema': 'haven-specialist-card-v1', 'specialization': 'secpatch: authorized security review and remediation',
           'promoted': name, 'generated_at': time.time()}
    if name:
        entry = reg['adapters'][name]
        out.update({k: entry[k] for k in ('base_model', 'base_revision', 'data_sha256', 'receipt_sha256')},
                   evals=entry['evals'], base_evals=reg.get('base_evals', {}),
                   serving='LoRA adapter on the base model; GGUF conversion (llama.cpp convert_lora_to_gguf.py) '
                           'and llama-server --lora are required before the gateway can route to it.')
    if manifest and manifest.exists():
        m = json.loads(manifest.read_text())
        out['dataset'] = {k: m.get(k) for k in ('built_at', 'cutoff', 'osv_archive_sha256', 'items_by_split', 'code_licenses')}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=pathlib.Path, required=True)
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('register'); r.add_argument('run_dir', type=pathlib.Path); r.add_argument('name')
    e = sub.add_parser('attach-eval'); e.add_argument('name'); e.add_argument('summary', type=pathlib.Path)
    p = sub.add_parser('promote'); p.add_argument('name'); p.add_argument('eval_sha256'); p.add_argument('--force', action='store_true')
    sub.add_parser('rollback'); sub.add_parser('show')
    c = sub.add_parser('card'); c.add_argument('--manifest', type=pathlib.Path); c.add_argument('--out', type=pathlib.Path)
    args = ap.parse_args(argv)
    if args.cmd == 'register':
        out = register(args.root, args.run_dir, args.name)
    elif args.cmd == 'attach-eval':
        out = attach_eval(args.root, args.name, args.summary)
    elif args.cmd == 'promote':
        out = promote(args.root, args.name, args.eval_sha256, args.force)
    elif args.cmd == 'rollback':
        out = rollback(args.root)
    elif args.cmd == 'card':
        out = card(args.root, args.manifest)
        if args.out:
            args.out.write_text(json.dumps(out, indent=1) + '\n')
    else:
        out = load(args.root)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
