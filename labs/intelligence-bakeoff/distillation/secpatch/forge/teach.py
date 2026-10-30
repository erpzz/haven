"""Verified teacher distillation for secpatch training rows (rationalization, STaR-style).

The teacher (default GLM-4.7-Flash behind any OpenAI-compatible endpoint: llama-server on a free Kaggle T4
pair or on Slink, or the HF router when credits exist) sees a training row together with its recorded ground
truth, and writes the short code-grounded analysis a careful engineer would reach from the code alone. A trace
is kept only if
  * the teacher's own JSON agrees with the recorded answer (verdict / supported / CWE overlap),
  * the analysis cites a line number that is actually shown, contains no braces (the evaluator parses the first
    JSON object) and does not mention the hidden reference,
  * it fits the evaluator's generation budget.
The SFT target is then `analysis + recorded JSON`, with the teacher's code-grounded description replacing
advisory boilerplate in the free-text field. Verdicts, CWEs and evidence lines always come from ground truth.

Only `split == train` rows are accepted. Output is append-only and resumable (one JSON line per row id).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import pathlib
import re
import threading
import time
import urllib.request

TASKS = ('detect', 'root_cause', 'finding_support', 'remediate')
HANDBOOK = (pathlib.Path(__file__).resolve().parent / 'handbook.md').read_text(encoding='utf-8')
WORD_LIMIT = {'detect': 90, 'root_cause': 110, 'finding_support': 80, 'remediate': 60}
LEAK = re.compile(r'\b(reference|ground truth|hint|we are told|i was told|the answer|advisory|hidden|provided label|'
                  r'recorded fix|gold)\b', re.I)
GUTTER = re.compile(r'^\s*(\d+) \|', re.M)
# When the code shown is the vulnerable version, the student cannot know about any later patch.
FUTURE = re.compile(r'\b(patch(ed|es)?|the fix|fixed version|earlier (version|form)|previous (version|code)|later '
                    r'(changed|fixed|version)|updated (version|code)|correct (attribute|name|spelling) is|vulnerable version)\b', re.I)


CODE = re.compile(r'```python\n(.*?)```', re.S)
COMMON = {'self', 'return', 'none', 'true', 'false', 'if', 'else', 'elif', 'for', 'in', 'not', 'and', 'or', 'def',
          'is', 'the', 'raise', 'try', 'except', 'with', 'as', 'import', 'from', 'pass', 'str', 'int', 'len', 'dict',
          'list', 'args', 'kwargs', 'value', 'data', 'name', 'result', 'path', 'line', 'lines', 'function', 'code'}
VERSIONS: dict[str, dict[str, list[tuple[int, str]]]] = {}


def numbered(block: str) -> list[tuple[int, str]]:
    out = []
    for raw in block.splitlines():
        m = re.match(r'^\s*(\d+) \| ?(.*)$', raw)
        if m:
            out.append((int(m.group(1)), m.group(2)))
    return out


def index_versions(rows: list[dict]) -> None:
    """Both versions of each fix, recovered from the paired detect rows (vulnerable / patched)."""
    for r in rows:
        if r['task'] == 'detect':
            m = CODE.search(r['messages'][-2]['content'])
            if m:
                kind = 'vulnerable' if r['label'] == 'vulnerable' else 'fixed'
                VERSIONS.setdefault(r['key'], {})[kind] = numbered(m.group(1))


def patch_diff(key: str, limit: int = 40) -> tuple[str, set[str]]:
    """Changed lines (old -> new) with their own line numbers, and the identifiers they touch."""
    import difflib
    v = VERSIONS.get(key, {})
    old, new = v.get('vulnerable'), v.get('fixed')
    if not old or not new:
        return '', set()
    a, b = [t for _, t in old], [t for _, t in new]
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        out += [f'- {old[i][0]:5d} | {a[i]}' for i in range(i1, i2)]
        out += [f'+ {new[j][0]:5d} | {b[j]}' for j in range(j1, j2)]
    words = lambda sign: {w for line in out if line.startswith(sign)
                          for w in re.findall(r'[A-Za-z_][A-Za-z0-9_]{2,}', line[9:]) if w.lower() not in COMMON}
    minus, plus = words('-'), words('+')
    idents = (minus ^ plus) or (minus | plus)  # prefer what the patch actually changed
    if len(out) > limit:
        out = out[:limit] + [f'... ({len(out) - limit} more changed lines)']
    return '\n'.join(out), idents


def shown_lines(text: str) -> set[int]:
    return {int(x) for x in GUTTER.findall(text)}


def target_json(row: dict) -> dict | None:
    try:
        return json.loads(row['messages'][-1]['content'])
    except (ValueError, KeyError):
        return None


def reference(row: dict) -> str | None:
    """The hidden facts the teacher must justify from the code. None = row is not taught (gold kept)."""
    task, label, gold = row['task'], row['label'], target_json(row)
    adv = ' '.join(a.get('id', '') for a in row['source'].get('advisories', []))
    diff, _ = patch_diff(row['key'])
    old_lines = '\n'.join(l for l in diff.splitlines() if l.startswith('-'))
    new_lines = '\n'.join(l for l in diff.splitlines() if l.startswith('+'))
    weak = ('\nThe weakness lies in these lines of the code shown:\n' + old_lines) if old_lines else ''
    safe = ('\nA safe implementation instead does this (NOT visible to the reader; use it only to understand '
            'what control is missing):\n' + new_lines) if new_lines else ''
    guard = ('\nThe protective lines in the code shown are:\n' + new_lines) if new_lines else ''
    before = ('\nAn earlier unsafe form (NOT visible to the reader; never mention it) was:\n' + old_lines) if old_lines else ''
    patch = ('\nThe security-relevant change, for your understanding only (- unsafe, + safe):\n' + diff) if diff else ''
    if task == 'detect':
        if label == 'vulnerable':
            cwe = ', '.join(gold.get('cwe') or []) or 'unclassified'
            return (f"Verdict: vulnerable. Weakness class: {cwe}. Description: {gold.get('issue', '')[:500]}{weak}{safe}"
                    f"\nExplain the concrete weakness in the code shown, as if discovering it yourself.")
        return (f"Verdict: not_vulnerable for this weakness class. Description of the weakness this code defends "
                f"against: {gold.get('issue', '') or adv}{guard}{before}\nExplain which guard in the code shown "
                f"prevents it.")
    if task == 'root_cause':
        return (f"Recorded CWE: {', '.join(gold.get('cwe') or [])}. Advisory summary: {gold.get('root_cause', '')[:600]} "
                f"Fix commit subject: {gold.get('fix', '')[:200]}{patch}")
    if task == 'finding_support':
        if label == 'supported':
            return 'The finding IS supported: the cited lines hold the weakness in the code shown.' + weak + safe
        if label == 'stale':
            return ('The finding is NOT supported: the code shown is the patched version; the cited weakness is '
                    'already defended. Name the guard in the code shown.' + guard + before)
        return None  # nonexistent-function decoys: the recorded reason is already exact
    if task == 'remediate':
        return ('Explain in one or two sentences what must change and why; the corrected lines are below.' + patch)
    return None


INSTRUCTIONS = {
    'detect': ('Write your analysis as a careful security engineer reviewing ONLY the code shown: name the function, '
               'the data flow or missing check, and cite line numbers like "line 42". At most {w} words, plain prose, '
               'no curly braces, and do not mention that you were given any reference. Then on a new line give the '
               'final JSON in exactly the schema the user requested.'),
    'root_cause': ('Write your analysis comparing the two versions: what the vulnerable code allowed, which lines '
                   'changed, and why the fix closes it. At most {w} words, plain prose, no curly braces, do not mention '
                   'any reference. Then on a new line give the final JSON in exactly the requested schema.'),
    'finding_support': ('Write your analysis checking the finding against the code shown, citing line numbers. At most '
                        '{w} words, plain prose, no curly braces, do not mention any reference. Then on a new line give '
                        'the final JSON in exactly the requested schema.'),
    'remediate': ('Write at most {w} words, plain prose, no curly braces, explaining what must change and why, citing '
                  'line numbers of the original. Then stop: do not write code; the code is added separately.'),
}


def teacher_messages(row: dict) -> list[dict] | None:
    ref = reference(row)
    if ref is None:
        return None
    msgs = [dict(m) for m in row['messages'][:-1]]
    if msgs and msgs[0]['role'] == 'system':
        msgs[0] = {'role': 'system', 'content': msgs[0]['content'] + '\n\n' + HANDBOOK}
    msgs[-1]['content'] += ('\n\n---\nPrivate notes for you (the reader never sees them): ' + ref +
                            '\n\n' + INSTRUCTIONS[row['task']].format(w=WORD_LIMIT[row['task']]))
    return msgs


def split_answer(text: str):
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.S).strip()
    i = text.find('{')
    if i == -1:
        return text, None
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[i:])
    except json.JSONDecodeError:
        return text[:i].strip(), None
    return text[:i].strip(), obj if isinstance(obj, dict) else None


def clean_analysis(text: str) -> str:
    text = re.sub(r'^(\*\*)?(analysis|reasoning)(\*\*)?\s*:\s*', '', text.strip(), flags=re.I)
    text = re.sub(r'```(json)?\s*$', '', text).strip()
    return re.sub(r'\n{3,}', '\n\n', text)


def verify(row: dict, text: str) -> tuple[dict | None, str]:
    """Return (sft_row, reason). sft_row is None when the trace is rejected."""
    task, label, gold = row['task'], row['label'], target_json(row)
    prompt = row['messages'][-2]['content']
    if task == 'remediate':
        analysis, obj = text, None
        analysis = clean_analysis(re.split(r'```', analysis)[0])
    else:
        analysis, obj = split_answer(text)
        analysis = clean_analysis(analysis)
        if obj is None:
            return None, 'no_json'
    words = len(analysis.split())
    if not analysis or words < 12:
        return None, 'too_short'
    if words > WORD_LIMIT[task] * 1.35:
        return None, 'too_long'
    if '{' in analysis or '}' in analysis:
        return None, 'braces'
    if LEAK.search(analysis):
        return None, 'leak'
    if task in ('detect', 'finding_support') and FUTURE.search(analysis):
        return None, 'future_leak'
    if task != 'remediate':
        for tick in re.findall(r'`([^`]+)`', analysis):
            for w in re.findall(r'[A-Za-z_][A-Za-z0-9_]{2,}', tick):
                if w not in prompt:
                    return None, 'unseen_identifier'
    diff, idents = patch_diff(row['key'])
    idents = {w for w in idents if re.search(r'\b' + re.escape(w) + r'\b', prompt)}
    changed_lines = {int(m) for m in re.findall(r'^[-+]\s*(\d+) \|', diff, re.M)} & shown_lines(prompt)
    cited_any = {int(x) for x in re.findall(r'\blines?\s+(\d+)', analysis, re.I)}
    if idents:  # a visible changed identifier must be named
        grounded = any(re.search(r'\b' + re.escape(w) + r'\b', analysis) for w in idents)
    else:  # nothing visible changed by name (e.g. only lines were added): cite a changed line instead
        grounded = not changed_lines or bool(cited_any & changed_lines)
    if not grounded:
        ground_fail = 'ungrounded'
    else:
        ground_fail = None
    cited = {int(x) for x in re.findall(r'\blines?\s+(\d+)', analysis, re.I)}
    if task != 'remediate' and label != 'nonexistent':
        if not cited or not cited <= shown_lines(prompt):
            return None, 'bad_citation'
    if ground_fail:
        return None, ground_fail
    if task == 'detect':
        if obj.get('verdict') != gold['verdict']:
            return None, 'wrong_verdict'
        final = dict(gold)
        issue = str(obj.get('issue') or '').strip()
        if issue and '{' not in issue and not LEAK.search(issue) and len(issue.split()) <= 60:
            final['issue'] = issue
    elif task == 'root_cause':
        if not set(obj.get('cwe') or []) & set(gold.get('cwe') or []):
            return None, 'wrong_cwe'
        final = dict(gold)
        rc = str(obj.get('root_cause') or '').strip()
        if rc and not LEAK.search(rc) and len(rc.split()) <= 80:
            final['root_cause'] = rc
        fx = str(obj.get('fix') or '').strip()
        if fx and not LEAK.search(fx) and len(fx.split()) <= 60:
            final['fix'] = fx
    elif task == 'finding_support':
        if obj.get('supported') is not gold['supported']:
            return None, 'wrong_support'
        final = dict(gold)
        reason = str(obj.get('reason') or '').strip()
        if reason and not LEAK.search(reason) and len(reason.split()) <= 60:
            final['reason'] = reason
    if task == 'remediate':
        target = analysis + '\n\n' + row['messages'][-1]['content'].strip()
    else:
        target = analysis + '\n\n' + json.dumps(final, ensure_ascii=False)
    out = {k: row[k] for k in ('id', 'key', 'task', 'label', 'split', 'source')}
    out['messages'] = row['messages'][:-1] + [{'role': 'assistant', 'content': target}]
    out['origin'] = 'teacher_verified'
    return out, 'ok'


class Endpoint:
    def __init__(self, base: str, model: str, key: str = '', timeout: int = 900):
        self.base, self.model, self.key, self.timeout = base.rstrip('/'), model, key, timeout

    def __call__(self, messages, max_tokens, temperature, seed, think=False):
        body = {'model': self.model, 'messages': messages, 'max_tokens': max_tokens, 'temperature': temperature,
                'top_p': 0.95, 'seed': seed, 'chat_template_kwargs': {'enable_thinking': think}}
        headers = {'Content-Type': 'application/json'}
        if self.key:
            headers['Authorization'] = 'Bearer ' + self.key
        req = urllib.request.Request(self.base + '/chat/completions', json.dumps(body).encode(), headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            data = json.loads(r.read())
        return data['choices'][0]['message'].get('content') or '', data.get('usage') or {}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rows', type=pathlib.Path, nargs='+', required=True, help='training-format jsonl')
    ap.add_argument('--out', type=pathlib.Path, required=True, help='append-only traces jsonl')
    ap.add_argument('--base-url', required=True)
    ap.add_argument('--model', default='glm-4.7-flash')
    ap.add_argument('--key-file', type=pathlib.Path)
    ap.add_argument('--attempts', type=int, default=3, help='samples per row until one verifies')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--think-retries', type=int, default=1, help='retries use the teacher reasoning mode')
    ap.add_argument('--deadline', type=float, default=0, help='stop starting new rows after this many seconds')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--shard', default='0-0/1', help='A-B/N: rows whose sha256(id) mod N is in A..B (split lanes)')
    args = ap.parse_args(argv)
    span, mod = args.shard.split('/')
    lo, hi = map(int, span.split('-'))
    in_shard = lambda rid: lo <= int(hashlib.sha256(rid.encode()).hexdigest()[:8], 16) % int(mod) <= hi
    key = args.key_file.read_text().strip() if args.key_file else ''
    ep = Endpoint(args.base_url, args.model, key)
    rows = []
    for path in args.rows:
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get('split') not in ('train', 'dev'):
                    raise SystemExit(f'Refusing {row.get("split")!r} row {row.get("id")}: teacher sees training rows only.')
                if row['task'] in TASKS and row['messages'][-1]['role'] == 'assistant':
                    rows.append(row)
    index_versions(rows)
    done = set()
    if args.out.exists():
        for x in args.out.read_text().splitlines():
            if x.strip():
                rec = json.loads(x)
                # rows that only hit transport errors (server restart, timeout) are retried
                if rec.get('sft') or not all(v.startswith('error:') for v in rec.get('verdicts', [])):
                    done.add(rec['id'])
    todo = [r for r in rows if r['id'] not in done and in_shard(r['id']) and teacher_messages(r) is not None]
    if args.limit:
        todo = todo[:args.limit]
    print(json.dumps({'rows': len(rows), 'already': len(done), 'todo': len(todo)}), flush=True)
    lock, started, stats = threading.Lock(), time.monotonic(), {}

    def work(row):
        if args.deadline and time.monotonic() - started > args.deadline:
            return
        msgs = teacher_messages(row)
        reasons, usage_total = [], {'prompt_tokens': 0, 'completion_tokens': 0}
        kept = None
        for attempt in range(args.attempts):
            try:
                # adaptive compute: a fast answer first; retries reason before answering (reasoning is discarded)
                think = attempt > 0 and args.think_retries
                text, usage = ep(msgs, 4000 if think else 700, 0.3 if attempt == 0 else 0.7, attempt, think)
            except Exception as exc:  # recorded, the row stays untaught (gold target remains)
                reasons.append(f'error:{type(exc).__name__}')
                continue
            for k in usage_total:
                usage_total[k] += int(usage.get(k) or 0)
            kept, why = verify(row, text)
            reasons.append(why)
            if kept:
                break
        rec = {'id': row['id'], 'task': row['task'], 'label': row['label'], 'verdicts': reasons, 'usage': usage_total,
               'sft': kept}
        with lock:
            with args.out.open('a', encoding='utf-8') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            for r in reasons:
                stats[r] = stats.get(r, 0) + 1
    with cf.ThreadPoolExecutor(args.workers) as ex:
        for i, _ in enumerate(ex.map(work, todo), 1):
            if i % 50 == 0:
                print(json.dumps({'done': i, 'of': len(todo), 'elapsed_s': round(time.monotonic() - started),
                                  'verdicts': stats}), flush=True)
    print(json.dumps({'finished': True, 'elapsed_s': round(time.monotonic() - started), 'verdicts': stats}), flush=True)


if __name__ == '__main__':
    main()
