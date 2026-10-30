#!/usr/bin/env python3
"""Train an abstaining task-family router on real Haven pull requests.

This is a research-only classifier: it NEVER chooses privileged actions, GPU leases,
security target scopes, or paid cloud providers. Labels identify which subsystem
should review a PR, not success outcomes or executable instructions.

Requires PyTorch for training; prediction uses the Python standard library.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys

LABELS = ('inference', 'training', 'orchestration')
VERSION = 'haven-pr-router-1'


def features(title: str) -> set[str]:
    tokens = re.findall(r'[a-z0-9]+', title.lower())
    words = ['w:' + w for w in tokens if len(w) > 1]
    bigrams = ['b:' + tokens[i] + '_' + tokens[i + 1] for i in range(len(tokens) - 1)]
    return set(words + bigrams)


def load_rows(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    ids = [x['pr'] for x in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate source PR')
    if not rows or set(x['split'] for x in rows) != {'train', 'validation', 'test'}:
        raise ValueError('missing required split')
    if any(r['route'] not in LABELS or r['split'] not in ('train', 'validation', 'test') for r in rows):
        raise ValueError('unrecognized label or split')
    if any(r['source'] != f"https://github.com/erpzz/haven/pull/{r['pr']}" for r in rows):
        raise ValueError('invalid provenance link')
    if any(not isinstance(r['title'], str) or not r['title'].strip() for r in rows):
        raise ValueError('empty title')
    if any(r['pr'] >= 74 and r['split'] != 'test' for r in rows):
        raise ValueError('time-held-out PR appears in train or validation')
    train_labels = {r['route'] for r in rows if r['split'] == 'train'}
    if train_labels != set(LABELS):
        raise ValueError('training split must contain every class')
    return rows


def vocabulary(train: list[dict]) -> list[str]:
    counts = Counter(f for r in train for f in features(r['title']))
    return sorted(counts, key=lambda f: (-counts[f], f))[:900]


def vector(title: str, vocab: list[str]) -> list[float]:
    ff = features(title)
    return [1.0 if term in ff else 0.0 for term in vocab]


def softmax(values: list[float]) -> list[float]:
    hi = max(values)
    e = [math.exp(x - hi) for x in values]
    den = sum(e)
    return [x / den for x in e]


def predict_one(model: dict, title: str, threshold: float = 0.55) -> dict:
    if not 0 < threshold < 1:
        raise ValueError('threshold must be in (0,1)')
    vocab = model['vocabulary']
    fv = vector(title, vocab)
    active = sum(fv)
    scores = [sum(w * v for w, v in zip(weight, fv)) + bias
              for weight, bias in zip(model['weights'], model['bias'])]
    probabilities = softmax(scores)
    best = max(range(len(LABELS)), key=probabilities.__getitem__)
    abstain = active == 0 or probabilities[best] < threshold
    return {'recommendation': 'ABSTAIN' if abstain else LABELS[best],
            'top_class': LABELS[best], 'confidence': round(probabilities[best], 5),
            'known_features': active, 'probabilities': dict(zip(LABELS, [round(p, 5) for p in probabilities]))}


def baseline(title: str) -> str:
    """Deterministic, not trained, comparison classifier; never dispatches jobs."""
    t = title.lower()
    if any(x in t for x in ('distill', 'sft', 'lora', 'fine-tun', 'bake-off', 'evaluator', 'secpatch', 'adjudicat')):
        return 'training'
    if any(x in t for x in ('tsz', 'fleet', 'schedul', 'executor', 'tunnel', 'worker', 'bootstrap', 'placement', 'engineer')):
        return 'orchestration'
    return 'inference'


def score(rows: list[dict], model: dict, threshold: float) -> dict:
    report = []
    for row in rows:
        p = predict_one(model, row['title'], threshold)
        rule = baseline(row['title'])
        report.append({'pr': row['pr'], 'actual': row['route'], 'model': p['top_class'],
                       'recommendation': p['recommendation'], 'confidence': p['confidence'],
                       'rule': rule, 'model_correct': p['top_class'] == row['route'],
                       'rule_correct': rule == row['route']})
    correct = sum(r['model_correct'] for r in report)
    rule_correct = sum(r['rule_correct'] for r in report)
    accepted = [r for r in report if r['recommendation'] != 'ABSTAIN']
    return {'n': len(report), 'model_top1_correct': correct,
            'model_top1_accuracy': round(correct / len(report), 4) if report else None,
            'rule_correct': rule_correct,
            'rule_accuracy': round(rule_correct / len(report), 4) if report else None,
            'accepted': len(accepted), 'accepted_correct': sum(r['model_correct'] for r in accepted),
            'abstained': len(report) - len(accepted), 'cases': report}


def train(args):
    try:
        import torch
    except ImportError as exc:
        raise SystemExit('Install PyTorch to train; stdlib is sufficient for prediction.') from exc
    if args.device == 'cuda' and not torch.cuda.is_available():
        raise SystemExit('REFUSED: CUDA requested but no NVIDIA GPU is available. No training performed.')
    torch.set_num_threads(1)
    torch.manual_seed(args.seed)
    device = torch.device(args.device)
    path = Path(args.data)
    rows = load_rows(path)
    train_rows = [r for r in rows if r['split'] == 'train']
    val_rows = [r for r in rows if r['split'] == 'validation']
    test_rows = [r for r in rows if r['split'] == 'test']
    vocab = vocabulary(train_rows)
    x = torch.tensor([vector(r['title'], vocab) for r in train_rows], dtype=torch.float32, device=device)
    y = torch.tensor([LABELS.index(r['route']) for r in train_rows], dtype=torch.long, device=device)
    if args.epochs < 1 or args.epochs > 2000:
        raise ValueError('epochs must be 1..2000')
    classifier = torch.nn.Linear(len(vocab), len(LABELS)).to(device)
    counts = Counter(r['route'] for r in train_rows)
    cw = torch.tensor([len(train_rows)/(len(LABELS)*counts[lab]) for lab in LABELS], dtype=torch.float32, device=device)
    optim = torch.optim.AdamW(classifier.parameters(), lr=args.lr, weight_decay=0.03)
    start = None
    for i in range(args.epochs):
        optim.zero_grad()
        loss = torch.nn.functional.cross_entropy(classifier(x), y, weight=cw)
        if start is None:
            start = float(loss.item())
        loss.backward()
        optim.step()
    final = float(torch.nn.functional.cross_entropy(classifier(x), y, weight=cw).item())
    with torch.no_grad():
        model = {'schema': VERSION, 'labels': list(LABELS), 'vocabulary': vocab,
                 'weights': classifier.weight.detach().cpu().tolist(),
                 'bias': classifier.bias.detach().cpu().tolist(),
                 'seed': args.seed, 'epochs': args.epochs, 'learning_rate': args.lr,
                 'trained_on': [r['pr'] for r in train_rows],
                 'data_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                 'device': str(device), 'initial_train_loss': round(start, 6),
                 'final_train_loss': round(final, 6)}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(model, sort_keys=True, separators=(',', ':')) + '\n')
    report = {'schema': VERSION + '-report', 'training_device': str(device),
              'train_rows': len(train_rows), 'validation_rows': len(val_rows),
              'test_rows': len(test_rows), 'vocabulary_size': len(vocab),
              'initial_train_loss': round(start, 6), 'final_train_loss': round(final, 6),
              'artifact_sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
              'validation': score(val_rows, model, args.threshold),
              'test': score(test_rows, model, args.threshold),
              'limitations': ['Tiny nonrepresentative public PR dataset; do not auto-promote or dispatch.',
                              'Chronological held-out test has no orchestration cases.',
                              'No GPU training if training_device is cpu.',
                              'No human-vetted task outcomes or security-tool traces are modeled.',
                              'Confidence is uncalibrated; abstention is heuristic.']}
    result = Path(args.report)
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'output': str(out), 'report': str(result), 'trained_on': len(train_rows),
                      'device': str(device), 'start_loss': round(start, 5), 'final_loss': round(final, 5),
                      'test': {k: v for k, v in report['test'].items() if k != 'cases'},
                      'validation': {k: v for k, v in report['validation'].items() if k != 'cases'}}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    t = sub.add_parser('train', help='opt-in training; never executes external tools')
    t.add_argument('--data', required=True)
    t.add_argument('--output', required=True)
    t.add_argument('--report', required=True)
    t.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    t.add_argument('--epochs', type=int, default=350)
    t.add_argument('--seed', type=int, default=1729)
    t.add_argument('--lr', type=float, default=0.08)
    t.add_argument('--threshold', type=float, default=0.55)
    p = sub.add_parser('predict', help='offline prediction; no execution permissions')
    p.add_argument('--model', required=True)
    p.add_argument('text', nargs='+')
    p.add_argument('--threshold', type=float, default=0.55)
    args = parser.parse_args()
    if args.command == 'train':
        train(args)
    else:
        model = json.loads(Path(args.model).read_text())
        if model.get('schema') != VERSION or tuple(model.get('labels', [])) != LABELS:
            raise ValueError('unsupported model artifact')
        print(json.dumps(predict_one(model, ' '.join(args.text), args.threshold), indent=2))


if __name__ == '__main__':
    main()
