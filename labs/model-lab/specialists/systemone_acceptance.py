#!/usr/bin/env python3
"""Acceptance workflow for a System One decision specialist (LiquidAI d1-2B).

Question: can a zero-output-token decision model, used zero-shot, route real Haven work
items to the right subsystem as well as the deterministic keyword rules already in
labs/engineer/router_lab, without any training on Haven data?

Input: the 36 public Haven pull-request titles in
labs/engineer/router_lab/data/haven_pr_routes_20261027.jsonl (labels come from changed-file
paths, inspected 2026-10-27; see that README). Title only, the same input #83 used.

The question wording below was fixed from the README's class definitions BEFORE any d1
inference. It is not tuned on these titles; changing it creates a new experiment.

This script only reads the dataset and calls one loopback llama.cpp /v1/systemone server.
It never dispatches work, starts or stops engines, or wires anything into routing. Router
implementation belongs to issue #73's router owner; this is capability evidence only.

    systemone_acceptance.py run --base-url http://127.0.0.1:PORT --api-key-file FILE \
        --data labs/engineer/router_lab/data/haven_pr_routes_20261027.jsonl --out results.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import pathlib
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROUTER = REPO / 'labs' / 'engineer' / 'router_lab' / 'train_router.py'
DATASET_SHA256 = 'ec94c3ecf8be02603a055eafcb31ca7a79bc11aee4f1243f74f122250825e371'
CLASSES = ('inference', 'training', 'orchestration')
THRESHOLD = 0.55  # the abstention threshold #83 reported, reused unchanged

# Frozen before inference (2026-10-30). One typed `choice` question; no examples.
QUESTION = {
    'route': {
        'type': 'choice',
        'instructions': 'This is the title of a pull request in Haven, a private AI platform. '
                        'Which Haven subsystem does the pull request mainly change?',
        'criteria': {
            'inference': 'Serving and using models: the Model Lab app and server, inference engines '
                         'and runtimes, chat frontends, gateways, model catalog and provider lanes.',
            'training': 'Training or evaluating models: datasets, fine-tuning (SFT, LoRA), '
                        'distillation, benchmarks, bake-offs and evaluation harnesses.',
            'orchestration': 'Coordinating work across machines and agents: workers, schedulers, '
                             'executors, fleet, tunnels, bootstrap and task placement.',
        },
    }
}


def question_sha256() -> str:
    return hashlib.sha256(json.dumps(QUESTION, sort_keys=True).encode()).hexdigest()


def load_rules():
    """The repository's own deterministic baseline, imported rather than copied."""
    spec = importlib.util.spec_from_file_location('haven_router_lab', ROUTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.baseline


def read_rows(path: pathlib.Path) -> list[dict]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != DATASET_SHA256:
        raise SystemExit(f'dataset hash {digest} is not the frozen {DATASET_SHA256}')
    rows = [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
    for row in rows:
        if row.get('route') not in CLASSES or not isinstance(row.get('title'), str):
            raise SystemExit(f'malformed row {row.get("pr")}')
    return rows


def ask(base_url: str, key: str, title: str, timeout: float = 120) -> tuple[dict, float]:
    body = json.dumps({'state': title, 'questions': QUESTION}).encode()
    request = urllib.request.Request(base_url.rstrip('/') + '/v1/systemone', data=body,
                                     headers={'Content-Type': 'application/json',
                                              'Authorization': 'Bearer ' + key})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback only
    t0 = time.monotonic()
    with opener.open(request, timeout=timeout) as response:
        payload = json.load(response)
    return payload, time.monotonic() - t0


def parse_answer(payload: dict) -> tuple[str, float, dict]:
    """Validate the typed answer instead of trusting it."""
    answer = (payload.get('answers') or {}).get('route') or {}
    choice, confidence = answer.get('choice'), answer.get('confidence')
    probabilities = answer.get('probabilities') or {}
    if choice not in CLASSES or not isinstance(confidence, (int, float)) or set(probabilities) != set(CLASSES):
        raise ValueError(f'answer outside the declared schema: {answer!r}')
    total = sum(float(p) for p in probabilities.values())
    if not math.isfinite(total) or abs(total - 1.0) > 0.02:
        raise ValueError(f'probabilities do not sum to 1: {total}')
    return choice, float(confidence), {k: round(float(v), 4) for k, v in probabilities.items()}


def sign_test(wins: int, losses: int) -> float:
    """Two-sided exact binomial sign test on discordant pairs."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def summarize(records: list[dict]) -> dict:
    def block(rows):
        d1 = sum(r['d1_correct'] for r in rows)
        rules = sum(r['rules_correct'] for r in rows)
        wins = sum(1 for r in rows if r['d1_correct'] and not r['rules_correct'])
        losses = sum(1 for r in rows if r['rules_correct'] and not r['d1_correct'])
        accepted = [r for r in rows if r['confidence'] >= THRESHOLD]
        return {'n': len(rows), 'd1_correct': d1, 'rules_correct': rules,
                'd1_only_correct': wins, 'rules_only_correct': losses,
                'sign_test_p': round(sign_test(wins, losses), 4),
                f'd1_accepted_at_{THRESHOLD}': len(accepted),
                'd1_accepted_correct': sum(r['d1_correct'] for r in accepted)}
    out = {'all': block(records)}
    for split in ('train', 'validation', 'test'):
        rows = [r for r in records if r['split'] == split]
        if rows:
            out[split] = block(rows)
    per_class = {}
    for c in CLASSES:
        rows = [r for r in records if r['gold'] == c]
        per_class[c] = {'n': len(rows), 'd1_correct': sum(r['d1_correct'] for r in rows),
                        'rules_correct': sum(r['rules_correct'] for r in rows)}
    out['per_gold_class'] = per_class
    latencies = sorted(r['seconds'] for r in records)
    out['latency_seconds'] = {'median': round(latencies[len(latencies) // 2], 3),
                              'max': round(latencies[-1], 3)}
    return out


def cmd_run(args) -> int:
    rows = read_rows(args.data)
    rules = load_rules()
    key = args.api_key_file.read_text().strip()
    records, input_tokens = [], 0
    for row in rows:
        payload, seconds = ask(args.base_url, key, row['title'])
        choice, confidence, probabilities = parse_answer(payload)
        usage = payload.get('usage') or {}
        if usage.get('output_tokens') not in (0, None):
            raise SystemExit('a decision model reported generated tokens; refusing to score')
        input_tokens += int(usage.get('input_tokens') or 0)
        rule = rules(row['title'])
        records.append({'pr': row['pr'], 'split': row['split'], 'gold': row['route'],
                        'd1': choice, 'confidence': round(confidence, 4), 'probabilities': probabilities,
                        'rules': rule, 'd1_correct': choice == row['route'],
                        'rules_correct': rule == row['route'], 'seconds': round(seconds, 3)})
        print(f"#{row['pr']:>3} {row['split']:<10} gold={row['route']:<13} d1={choice:<13} "
              f"p={confidence:.2f} rules={rule:<13} {seconds:.2f}s", flush=True)
    result = {'schema': 'haven.systemone-acceptance/v1',
              'question_sha256': question_sha256(), 'dataset_sha256': DATASET_SHA256,
              'threshold': THRESHOLD, 'input_tokens_total': input_tokens, 'output_tokens_total': 0,
              'environment': args.environment, 'summary': summarize(records), 'records': records}
    args.out.write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(result['summary'], indent=1))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='cmd', required=True)
    run = sub.add_parser('run')
    run.add_argument('--base-url', required=True)
    run.add_argument('--api-key-file', type=pathlib.Path, required=True)
    run.add_argument('--data', type=pathlib.Path, required=True)
    run.add_argument('--out', type=pathlib.Path, required=True)
    run.add_argument('--environment', default='unspecified',
                     help='Where this ran, e.g. "cloud CPU container, not Slink". Recorded verbatim.')
    sub.add_parser('question-hash')
    args = parser.parse_args(argv)
    if args.cmd == 'question-hash':
        print(question_sha256())
        return 0
    if not args.base_url.startswith(('http://127.0.0.1:', 'http://localhost:')):
        parser.error('only a loopback decision server is accepted')
    return cmd_run(args)


if __name__ == '__main__':
    sys.exit(main())
