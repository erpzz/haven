"""Deterministic evaluation of a student, adapter or served model on secpatch eval items.

Backends: `hf` (transformers on CPU/CUDA, optional PEFT adapter) and `openai`
(any OpenAI-compatible endpoint: llama-server, the Haven gateway). Graders use
only recorded ground truth (advisory CWE, fix-changed lines, executed Bandit
results) and re-run Bandit on generated patches; no model grades a model.

Per-item fields: score (0/1), invalid_json, false_positive, unsupported
(an answer that cites a function or line not in the code shown), latency,
completion tokens. The summary adds Wilson intervals, paired detection
accuracy (both versions of one fix right), and peak memory.
"""
from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import json
import math
import pathlib
import platform
import re
import resource
import subprocess
import sys
import tempfile
import textwrap
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from harvest import normalize  # noqa: E402

# Budgets leave room for the requested JSON plus a short reason; a smoke run truncated 160-token answers mid-JSON.
MAX_NEW = {'detect': 400, 'root_cause': 512, 'remediate': 1536, 'tool_select': 256, 'finding_support': 400}


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    if not n:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0, c - h), 4), round(min(1, c + h), 4)]


def parse_json(text: str):
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.S)
    i = text.find('{')
    while i != -1:
        try:
            value, _ = json.JSONDecoder().raw_decode(text[i:])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            pass
        i = text.find('{', i + 1)
    return None


GUTTER = re.compile(r'^\s*\d+ \| ?')


def cwe_ids(values) -> set[str]:
    """CWE identifiers in a model's cwe list. The prompt asks for strings, so "CWE-22: Path Traversal",
    "cwe-22" and "CWE-22" all name the same weakness."""
    if isinstance(values, str):
        values = [values]
    return {f'CWE-{m}' for v in values or [] for m in re.findall(r'(?i)\bCWE[-_ ]?(\d+)', str(v))}


def code_block(text: str) -> str | None:
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.S)
    m = re.search(r'```(?:python|py)?\s*\n(.*?)```', text, re.S)
    return strip_gutter(m.group(1))[0] if m else None


def strip_gutter(code: str) -> tuple[str, bool]:
    """Remove the `  123 | ` line-number gutter the prompt shows, when the model copied it onto every line."""
    lines = [l for l in code.splitlines() if l.strip()]
    if lines and all(GUTTER.match(l) for l in lines):
        return '\n'.join(GUTTER.sub('', l, count=1) for l in code.splitlines()), True
    return code, False


def signature(code: str):
    try:
        tree = ast.parse(textwrap.dedent(code))
    except SyntaxError:
        return None
    fn = next((n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
    return None if fn is None else (fn.name, ast.dump(fn.args))


def bandit_rules(bandit: str, code: str) -> set | None:
    with tempfile.TemporaryDirectory() as tmp:
        f = pathlib.Path(tmp) / 'candidate.py'
        f.write_text(textwrap.dedent(code) + '\n', encoding='utf-8')
        r = subprocess.run([bandit, '-q', '-f', 'json', str(f)], capture_output=True, text=True, timeout=120)
        try:
            report = json.loads(r.stdout)
        except json.JSONDecodeError:
            return None
        return None if report.get('errors') else {x['test_id'] for x in report.get('results', [])}


def bandit_issues(bandit: str, code: str) -> list[dict] | None:
    with tempfile.TemporaryDirectory() as tmp:
        f = pathlib.Path(tmp) / 'candidate.py'
        f.write_text(textwrap.dedent(code) + '\n', encoding='utf-8')
        r = subprocess.run([bandit, '-q', '-f', 'json', str(f)], capture_output=True, text=True, timeout=120)
        try:
            report = json.loads(r.stdout)
        except json.JSONDecodeError:
            return None
        return None if report.get('errors') else report.get('results', [])


def with_tool_evidence(item: dict, bandit: str) -> list[dict]:
    """Tool-augmented arm: run Bandit on the code actually shown and append its real findings."""
    msgs = [dict(m) for m in item['messages']]
    m = re.search(r'```python\n(.*?)```', msgs[-1]['content'], re.S)
    if not m:
        return msgs
    rows = re.findall(r'^\s*(\d+) \| ?(.*)$', m.group(1), re.M)
    if not rows:
        return msgs
    start = int(rows[0][0])
    issues = bandit_issues(bandit, '\n'.join(r[1] for r in rows))
    if issues is None:
        evidence = 'Tool evidence: bandit could not parse this excerpt; no static result.'
    elif not issues:
        evidence = 'Tool evidence: bandit 1.9.4 reported no issues for this code.'
    else:
        evidence = 'Tool evidence (bandit 1.9.4, executed):\n' + '\n'.join(
            f"- {x['test_id']} {x['test_name']} at line {x['line_number'] + start - 1}: {x['issue_text']} "
            f"(severity {x['issue_severity']}, confidence {x['issue_confidence']})" for x in issues)
    msgs[-1]['content'] += '\n\n' + evidence + '\nStatic tools miss many issues and flag safe code; weigh this evidence, do not copy it.'
    return msgs


SHOWN = re.compile(r'```python\n(.*?)```', re.S)


def shown_code(text: str) -> str | None:
    m = SHOWN.search(text)
    return '\n'.join(GUTTER.sub('', l, count=1) for l in m.group(1).splitlines()) if m else None


class CaseIndex:
    """Nearest past fixes from the *training* split, for case-based prompting.

    Training repositories and dates are disjoint from dev/held-out by construction, so a retrieved case is never
    the item itself or from its project."""
    def __init__(self, train_path: pathlib.Path):
        from build import shingles
        self.shingles, self.cases = shingles, []
        for line in train_path.read_text().splitlines():
            row = json.loads(line)
            if row.get('split') != 'train':
                raise ValueError('Cases must come from the training split only.')
            if row['task'] != 'remediate':
                continue
            vuln = shown_code(row['messages'][1]['content'])
            fixed = code_block(row['messages'][-1]['content'])
            if vuln and fixed:
                src = row['source']
                self.cases.append({'repo': src['repo'], 'advisory': (src.get('advisory_ids') or ['?'])[0],
                                   'vulnerable': vuln, 'fixed': fixed, 'sh': shingles(vuln),
                                   'issue': row['messages'][1]['content'].split('\n', 1)[0].removeprefix('Reported issue: ')})

    def nearest(self, code: str, k: int) -> list[dict]:
        from build import jaccard
        sh = self.shingles(code)
        return sorted(self.cases, key=lambda c: -jaccard(sh, c['sh']))[:k]


def with_cases(messages: list[dict], index: 'CaseIndex', k: int) -> list[dict]:
    msgs = [dict(m) for m in messages]
    code = shown_code(msgs[-1]['content'])
    if not code:
        return msgs
    blocks = []
    for c in index.nearest(code, k):
        blocks.append(f"Past fix in {c['repo']} ({c['advisory']}): {c['issue'][:200]}\nBefore:\n```\n{c['vulnerable'][:1500]}\n```\n"
                      f"After:\n```\n{c['fixed'][:1500]}\n```")
    msgs[-1]['content'] += ('\n\nFor reference, similar past security fixes from other projects (they are not the code under '
                            'review; use them only as analogies):\n\n' + '\n\n'.join(blocks))
    return msgs


def shown_span(item: dict) -> tuple[int, int]:
    lines = [int(m) for m in re.findall(r'^\s*(\d+) \|', item['messages'][-1]['content'], re.M)]
    return (min(lines), max(lines)) if lines else (0, 0)


def grade(item: dict, output: str, bandit: str) -> dict:
    g = item['grader']
    task, label = g['task'], g['label']
    res = {'score': 0, 'invalid_json': False, 'false_positive': False, 'unsupported': False}
    if task == 'remediate':
        m = re.search(r'```(?:python|py)?\s*\n(.*?)```', re.sub(r'<think>.*?</think>', '', output, flags=re.S), re.S)
        code, res['gutter_stripped'] = strip_gutter(m.group(1)) if m else ('', False)
        sig_ok = signature(code) is not None and signature(code) == signature(g['vulnerable'])
        changed = bool(code) and normalize(textwrap.dedent(code)) != normalize(textwrap.dedent(g['vulnerable']))
        res.update(parses=signature(code) is not None, same_signature=sig_ok, changed=changed,
                   matches_recorded_fix=bool(code) and normalize(textwrap.dedent(code)) == normalize(textwrap.dedent(g['fixed'])))
        cleared = None
        if g.get('bandit') and sig_ok and changed:
            rules = bandit_rules(bandit, code)
            cleared = rules is not None and g['bandit']['test_id'] not in rules
        res['bandit_cleared'] = cleared
        # Plausible remediation only: repository tests (repo_eval.py) decide whether it really fixes the issue.
        res['score'] = int(sig_ok and changed and cleared is not False)
        return res
    obj = parse_json(output)
    if obj is None:
        res['invalid_json'] = True
        return res
    if task == 'detect':
        verdict = obj.get('verdict')
        res['false_positive'] = label == 'not_vulnerable' and verdict == 'vulnerable'
        res['score'] = int(verdict == label)
        if verdict == 'vulnerable':
            lo, hi = shown_span(item)
            lines = [x for x in obj.get('evidence_lines') or [] if isinstance(x, int)]
            fn = str(obj.get('function', ''))
            res['unsupported'] = (any(not lo <= x <= hi for x in lines) or
                                  (bool(fn) and fn.rsplit('.', 1)[-1] not in item['messages'][-1]['content']))
            if label == 'vulnerable':
                res['cwe_match'] = bool(cwe_ids(obj.get('cwe')) & cwe_ids(g['cwe'])) if g['cwe'] else None
                res['evidence_hit'] = bool(set(lines) & set(g['changed_lines']))
    elif task == 'root_cause':
        res['score'] = int(bool(cwe_ids(obj.get('cwe')) & cwe_ids(g['cwe'])))
    elif task == 'tool_select':
        res['score'] = int(str(obj.get('tool', '')).lower() == 'bandit' and obj.get('rule') == g['bandit']['test_id'])
    elif task == 'finding_support':
        res['score'] = int(obj.get('supported') is (label == 'supported'))
        res['false_positive'] = label != 'supported' and obj.get('supported') is True
    return res


class HF:
    def __init__(self, model: str, revision: str, adapter: str | None, device: str):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        opts = {'revision': revision, 'local_files_only': True, 'trust_remote_code': False}
        self.torch, self.device = torch, device
        self.tok = AutoTokenizer.from_pretrained(model, **opts)
        self.model = AutoModelForCausalLM.from_pretrained(
            model, torch_dtype=torch.float16 if device == 'cuda' else torch.float32, use_safetensors=True, **opts).to(device)
        if adapter:
            from peft import PeftModel
            self.model = PeftModel.from_pretrained(self.model, adapter)
        self.model.eval()
        self.name = f'{model}@{revision[:7]}' + (f'+{pathlib.Path(adapter).parent.name}' if adapter else '')

    def __call__(self, messages, max_new, temperature, seed):
        torch = self.torch
        text = self.tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        ids = self.tok(text, return_tensors='pt').to(self.device)
        torch.manual_seed(seed)
        with torch.no_grad():
            out = self.model.generate(**ids, max_new_tokens=max_new, do_sample=temperature > 0,
                                      temperature=temperature or None, top_p=0.95 if temperature > 0 else None)
        new = out[0][ids['input_ids'].shape[1]:]
        return self.tok.decode(new, skip_special_tokens=True), len(new)


class OpenAI:
    def __init__(self, base: str, model: str, key_file: str | None):
        self.base, self.model = base.rstrip('/'), model
        self.key = pathlib.Path(key_file).read_text().strip() if key_file else ''
        self.name = f'{model}@{base}'

    def __call__(self, messages, max_new, temperature, seed):
        import urllib.request
        body = {'model': self.model, 'messages': messages, 'max_tokens': max_new, 'temperature': temperature,
                'seed': seed, 'chat_template_kwargs': {'enable_thinking': False}}
        req = urllib.request.Request(self.base + '/chat/completions', data=json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json',
                                              **({'Authorization': 'Bearer ' + self.key} if self.key else {})})
        with urllib.request.urlopen(req, timeout=900) as r:
            data = json.loads(r.read())
        return data['choices'][0]['message'].get('content') or '', (data.get('usage') or {}).get('completion_tokens')


def summarize(rows: list[dict], eval_sha: str, model: str) -> dict:
    by = collections.defaultdict(list)
    for r in rows:
        by[r['task']].append(r)
    out = {'model': model, 'eval_sha256': eval_sha, 'n': len(rows),
           'score': round(sum(r['score'] for r in rows) / max(1, len(rows)), 4), 'by_task': {}}
    for task, rs in sorted(by.items()):
        k = sum(r['score'] for r in rs)
        out['by_task'][task] = {'n': len(rs), 'correct': k, 'rate': round(k / len(rs), 4), 'wilson95': wilson(k, len(rs)),
                                'invalid_json': sum(r['invalid_json'] for r in rs)}
    det = by.get('detect', [])
    neg = [r for r in det if r['label'] == 'not_vulnerable']
    pos = [r for r in det if r['label'] == 'vulnerable']
    pairs = collections.defaultdict(list)
    for r in det:
        pairs[(r['key'], r.get('seed'))].append(r['score'])
    out.update(
        false_positive_rate=round(sum(r['false_positive'] for r in neg) / max(1, len(neg)), 4),
        detection_recall=round(sum(r['score'] for r in pos) / max(1, len(pos)), 4),
        paired_detection=round(sum(all(v) and len(v) == 2 for v in pairs.values()) / max(1, len(pairs)), 4),
        cwe_match_when_detected=round(sum(bool(r.get('cwe_match')) for r in pos) / max(1, sum(r['score'] for r in pos)), 4),
        unsupported_rate=round(sum(r['unsupported'] for r in rows) / max(1, len(rows)), 4),
        remediation_bandit_cleared=[sum(r.get('bandit_cleared') is True for r in by.get('remediate', [])),
                                    sum(r.get('bandit_cleared') is not None for r in by.get('remediate', []))],
        latency_mean_s=round(sum(r['latency_s'] for r in rows) / max(1, len(rows)), 3),
        completion_tokens=sum(r['completion_tokens'] or 0 for r in rows),
        peak_rss_gib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if platform.system() == 'Darwin' else 1024) / 2**30, 3))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--eval', type=pathlib.Path, required=True)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    ap.add_argument('--backend', choices=('hf', 'openai'), required=True)
    ap.add_argument('--model', required=True)
    ap.add_argument('--revision', help='hf: exact base revision')
    ap.add_argument('--adapter', help='hf: PEFT adapter directory')
    ap.add_argument('--device', default='cpu')
    ap.add_argument('--base-url', help='openai: e.g. http://127.0.0.1:8877/v1')
    ap.add_argument('--key-file')
    ap.add_argument('--bandit', default='bandit')
    ap.add_argument('--tasks')
    ap.add_argument('--limit', type=int, default=0, help='Use the first N fixes (all of their tasks), not N rows.')
    ap.add_argument('--seeds', default='0')
    ap.add_argument('--temperature', type=float, default=0.0)
    ap.add_argument('--with-tools', action='store_true', help='Tool-augmented arm: executed Bandit evidence in each prompt.')
    ap.add_argument('--cases', type=pathlib.Path, help='Case-based arm: training-split jsonl to retrieve similar past fixes from.')
    ap.add_argument('--k', type=int, default=2, help='Number of retrieved cases.')
    args = ap.parse_args(argv)
    items = [json.loads(x) for x in args.eval.read_text().splitlines() if x.strip()]
    if args.tasks:
        items = [i for i in items if i['task'] in set(args.tasks.split(','))]
    if args.limit:
        keys = list(dict.fromkeys(i['key'] for i in items))[:args.limit]
        items = [i for i in items if i['key'] in set(keys)]
    eval_sha = hashlib.sha256(json.dumps([i['id'] for i in items]).encode()).hexdigest()
    cases = CaseIndex(args.cases) if args.cases else None
    gen = HF(args.model, args.revision, args.adapter, args.device) if args.backend == 'hf' else \
        OpenAI(args.base_url, args.model, args.key_file)
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    with (args.out / 'items.jsonl').open('w', encoding='utf-8') as f:
        for seed in map(int, args.seeds.split(',')):
            for item in items:
                started = time.monotonic()
                try:
                    messages = with_tool_evidence(item, args.bandit) if args.with_tools else item['messages']
                    if cases:
                        messages = with_cases(messages, cases, args.k)
                    text, ntok = gen(messages, MAX_NEW[item['task']], args.temperature, seed)
                    error = None
                except Exception as exc:  # recorded, scored as wrong; never retried silently
                    text, ntok, error = '', 0, f'{type(exc).__name__}: {str(exc)[:200]}'
                row = {'id': item['id'], 'key': item['key'], 'task': item['task'], 'label': item['label'], 'seed': seed,
                       'latency_s': round(time.monotonic() - started, 3), 'completion_tokens': ntok, 'error': error,
                       **grade(item, text, args.bandit), 'output': text[:16000], 'output_chars': len(text)}
                rows.append(row)
                f.write(json.dumps(row, ensure_ascii=False) + '\n'); f.flush()
    summary = summarize(rows, eval_sha, gen.name)
    summary.update(eval_file=str(args.eval), seeds=args.seeds, temperature=args.temperature, backend=args.backend,
                   arm=('tools:bandit' if args.with_tools else 'plain') + (f'+cases{args.k}' if args.cases else '')
                       + ('+adapter' if args.adapter else ''),
                   classification='MEASURED_ON_HELD_OUT' if 'heldout' in args.eval.name else 'MEASURED_ON_DEV')
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps(summary))
    return summary


if __name__ == '__main__':
    main()
