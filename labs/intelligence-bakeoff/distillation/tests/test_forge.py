"""Forge invariants: teacher traces are grounded and leak-free, splits never share a repository, self-play is
graded by recorded ground truth, and the loop only promotes on a real, non-noisy improvement."""
import json
import pathlib
import sys
import tempfile
import time
import unittest

FORGE = pathlib.Path(__file__).resolve().parents[1] / 'secpatch' / 'forge'
sys.path.insert(0, str(FORGE))
import evalrun  # noqa: E402
import mix  # noqa: E402
import teach  # noqa: E402

SYSTEM = {'role': 'system', 'content': 'You are a reviewer.'}
VULN = "```python\n   10 | def load(p):\n   11 |     return open(base + p).read()\n```"
FIXED = ("```python\n   10 | def load(p):\n   11 |     safe = os.path.normpath(p)\n"
         "   12 |     return open(base + safe).read()\n```")


def row(task, label, user, target, key='K1', repo='o/r', split='train', rid=None):
    return {'id': rid or f'{key}-{task}-{label}', 'key': key, 'task': task, 'label': label, 'split': split,
            'source': {'repo': repo, 'function': 'load', 'advisories': [{'id': 'GHSA-x'}]},
            'messages': [SYSTEM, {'role': 'user', 'content': user}, {'role': 'assistant', 'content': target}]}


def detect_pair(key='K1', repo='o/r', split='train'):
    v = row('detect', 'vulnerable', 'Review.\n' + VULN, json.dumps(
        {'verdict': 'vulnerable', 'function': 'load', 'cwe': ['CWE-22'], 'evidence_lines': [11], 'issue': 'adv'}),
        key, repo, split)
    f = row('detect', 'not_vulnerable', 'Review.\n' + FIXED, json.dumps(
        {'verdict': 'not_vulnerable', 'function': 'load', 'cwe': [], 'evidence_lines': [], 'issue': 'none'}),
        key, repo, split)
    return v, f


class TeachTests(unittest.TestCase):
    def setUp(self):
        self.v, self.f = detect_pair()
        teach.VERSIONS.clear()
        teach.index_versions([self.v, self.f])

    def answer(self, analysis, verdict='vulnerable'):
        return analysis + '\n{"verdict": "%s", "function": "load", "cwe": ["CWE-22"], "evidence_lines": [11], ' \
                          '"issue": "Unsanitized path joined to base."}' % verdict

    def test_reference_carries_patch_diff(self):
        ref = teach.reference(self.v)
        self.assertIn('- ', ref)
        self.assertIn('normpath', ref)

    def test_grounded_trace_kept_with_recorded_verdict(self):
        out, why = teach.verify(self.v, self.answer(
            'The function load concatenates the caller supplied p onto base on line 11 and opens it directly, '
            'so a value containing dot dot segments escapes the base directory and reads arbitrary files.'))
        self.assertEqual(why, 'ok')
        final = out['messages'][-1]['content']
        self.assertTrue(final.split('\n\n')[-1].startswith('{"verdict": "vulnerable"'))
        self.assertEqual(json.loads(final.split('\n\n')[-1])['cwe'], ['CWE-22'])  # ground truth, not teacher's
        self.assertEqual(out['origin'], 'teacher_verified')

    def test_rejections(self):
        base = ('The function load concatenates the caller supplied p onto base on line 11 and opens it directly, '
                'so a value containing dot dot segments escapes the base directory and reads arbitrary files.')
        cases = {
            'wrong_verdict': self.answer(base, 'not_vulnerable'),
            'bad_citation': self.answer(base.replace('line 11', 'line 99')),
            'leak': self.answer(base + ' The advisory confirms it.'),
            'future_leak': self.answer(base + ' The patch later fixed it.'),
            'no_json': self.answer(base + ' Like {x}.'),  # a stray brace is rejected before the brace check
            'unseen_identifier': self.answer(base + ' It should call `normpath`.'),
            'too_short': self.answer('Bad on line 11.'),
        }
        for want, text in cases.items():
            self.assertEqual(teach.verify(self.v, text)[1], want, want)

    def test_ungrounded_when_changed_identifiers_missing(self):
        # The patched version is shown: `safe`/`normpath` are visible and changed, so one must be named.
        text = ('The function load on line 12 reads a file relative to base after the earlier line 11 assignment; '
                'it looks fine and contains no dangerous construct worth flagging in this review at all.')
        ans = text + '\n{"verdict": "not_vulnerable", "function": "load", "cwe": [], "evidence_lines": [], "issue": "ok"}'
        self.assertEqual(teach.verify(self.f, ans)[1], 'ungrounded')

    def test_teacher_refuses_eval_rows(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 'x.jsonl'
            p.write_text(json.dumps({**self.v, 'split': 'heldout'}) + '\n')
            with self.assertRaises(SystemExit):
                teach.main(['--rows', str(p), '--out', str(pathlib.Path(d) / 'o.jsonl'), '--base-url', 'http://x'])


class MixTests(unittest.TestCase):
    def build(self, d):
        d = pathlib.Path(d)
        train = list(detect_pair('A', 'o/train'))
        # find one dev repo per half
        repos = [f'o/dev{i}' for i in range(20)]
        gate_repo = next(r for r in repos if mix.repo_half(r) == 1)
        pool_repo = next(r for r in repos if mix.repo_half(r) == 0)
        dev = list(detect_pair('B', pool_repo, 'dev')) + list(detect_pair('C', gate_repo, 'dev'))
        train += list(detect_pair('D', gate_repo))  # pre-cutoff fix from a gate repository
        ev = [{**r, 'grader': {}, 'messages': r['messages'][:-1]} for r in dev]
        for name, rows in (('train', train), ('dev', dev), ('eval-dev', ev), ('eval-heldout', [])):
            (d / f'{name}.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
        (d / 'manifest.json').write_text('{}')
        return d, gate_repo

    def test_gate_repositories_never_in_pool(self):
        with tempfile.TemporaryDirectory() as d:
            data, gate_repo = self.build(d)
            m = mix.main(['--data', str(data), '--out', str(data / 'out')])
            pool = [json.loads(x) for x in (data / 'out/sft.jsonl').read_text().splitlines()]
            gate = [json.loads(x) for x in (data / 'out/gate.jsonl').read_text().splitlines()]
            self.assertTrue(gate and all(r['source']['repo'] == gate_repo for r in gate))
            self.assertFalse({r['source']['repo'] for r in pool} & {gate_repo})
            self.assertEqual(m['pool_fixes'], 2)  # A and B; D left with its gate repository

    def trace(self, data, analysis):
        rid = 'A-detect-vulnerable'
        target = analysis + '\n\n{"verdict": "vulnerable", "function": "load", "cwe": ["CWE-22"], "evidence_lines": [11], "issue": "x"}'
        v = detect_pair('A', 'o/train')[0]
        sft = {**v, 'messages': v['messages'][:-1] + [{'role': 'assistant', 'content': target}], 'origin': 'teacher_verified'}
        t = data / 'traces.jsonl'
        t.write_text(json.dumps({'id': rid, 'sft': sft}) + '\n')
        return rid, t

    def test_verified_traces_replace_targets(self):
        with tempfile.TemporaryDirectory() as d:
            data, _ = self.build(d)
            rid, t = self.trace(data, 'The function load concatenates the caller supplied p onto base on line 11 and '
                                      'opens it directly, so dot dot segments escape the base directory.')
            mix.main(['--data', str(data), '--out', str(data / 'out'), '--traces', str(t)])
            rows = {json.loads(x)['id']: json.loads(x) for x in (data / 'out/sft.jsonl').read_text().splitlines()}
            self.assertEqual(rows[rid]['origin'], 'teacher_verified')
            recorded = [json.loads(x) for x in (data / 'out/pool.jsonl').read_text().splitlines()]
            self.assertTrue(all(r['messages'][-1]['role'] == 'assistant' and 'origin' not in r for r in recorded))

    def test_stored_trace_failing_current_rules_is_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            data, _ = self.build(d)
            rid, t = self.trace(data, 'The function load concatenates p onto base on line 11 and the patch later '
                                      'added normalization, so dot dot segments escape the base directory.')
            m = mix.main(['--data', str(data), '--out', str(data / 'out'), '--traces', str(t)])
            rows = {json.loads(x)['id']: json.loads(x) for x in (data / 'out/sft.jsonl').read_text().splitlines()}
            self.assertEqual(rows[rid]['origin'], 'recorded')
            self.assertEqual(m['traces_rejected_on_reverify'], {'future_leak': 1})


    def test_miscalibrated_critic_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            data, _ = self.build(d)
            rid, t = self.trace(data, 'The function load concatenates the caller supplied p onto base on line 11 and '
                                      'opens it directly, so dot dot segments escape the base directory.')
            key = mix.trace_key(json.loads(t.read_text()))
            c = data / 'critic.jsonl'
            c.write_text(json.dumps({'key': key, 'sound': False, 'problem': 'x'}) + '\n')  # 100% rejected
            m = mix.main(['--data', str(data), '--out', str(data / 'out'), '--traces', str(t), '--critic', str(c)])
            rows = {json.loads(x)['id']: json.loads(x) for x in (data / 'out/sft.jsonl').read_text().splitlines()}
            self.assertEqual(rows[rid]['origin'], 'teacher_verified')
            self.assertEqual(m['critic_files_ignored_as_miscalibrated'], {'critic.jsonl': 1.0})
            m = mix.main(['--data', str(data), '--out', str(data / 'out'), '--traces', str(t), '--critic', str(c),
                          '--critic-max-reject', '1.0'])
            rows = {json.loads(x)['id']: json.loads(x) for x in (data / 'out/sft.jsonl').read_text().splitlines()}
            self.assertEqual(rows[rid]['origin'], 'recorded')


class PairBalanceTests(unittest.TestCase):
    """Preference pairs push equally toward each answer on yes/no tasks, or they skew the false-positive rate."""

    def test_detect_and_finding_support_are_balanced(self):
        mk = lambda i, task, chosen: {'id': f'{task}-{i}', 'task': task, 'chosen': chosen, 'rejected': 'x', 'prompt': []}
        pairs = ([mk(i, 'detect', '{"verdict": "vulnerable"}') for i in range(9)]
                 + [mk(i + 9, 'detect', '{"verdict": "not_vulnerable"}') for i in range(4)]
                 + [mk(i, 'finding_support', '{"supported": true}') for i in range(5)]
                 + [mk(i + 5, 'finding_support', '{"supported": false}') for i in range(3)]
                 + [mk(i, 'remediate', 'patched code') for i in range(6)])
        out, counts = mix.balance_pairs(pairs)
        by = lambda t, v: sum(1 for p in out if p['task'] == t and v in p['chosen'])
        self.assertEqual((by('detect', '"vulnerable"'), by('detect', 'not_vulnerable')), (4, 4))
        self.assertEqual((by('finding_support', 'true'), by('finding_support', 'false')), (3, 3))
        self.assertEqual(by('remediate', 'patched'), 6)
        self.assertEqual(counts['detect:vulnerable'], '4/9')
        self.assertEqual({p['id'] for p in out}, {p['id'] for p in mix.balance_pairs(list(reversed(pairs)))[0]})  # order-free


class SelfPlayGraderTests(unittest.TestCase):
    def test_gold_grader_matches_recorded_target(self):
        v, f = detect_pair()
        item = evalrun.as_item(v)
        self.assertEqual(item['grader']['changed_lines'], [11])
        self.assertEqual(item['messages'][-1]['role'], 'user')
        ev = evalrun.ev
        good = 'line 11\n{"verdict": "vulnerable", "function": "load", "cwe": ["CWE-22"], "evidence_lines": [11]}'
        self.assertEqual(ev.grade(item, good, 'bandit')['score'], 1)
        self.assertEqual(ev.grade(evalrun.as_item(f), good, 'bandit')['false_positive'], True)

    def test_remediate_grader_strips_gutter(self):
        r = row('remediate', 'fix', 'Rewrite.\n' + VULN, '```python\ndef load(p):\n    return open(base + os.path.normpath(p)).read()\n```')
        g = evalrun.gold_grader(r)
        self.assertTrue(g['vulnerable'].startswith('def load(p):'))


class GateTests(unittest.TestCase):
    def run_gate(self, student_detect_scores):
        import importlib, os
        with tempfile.TemporaryDirectory() as d:
            os.environ['FORGE_STATE'] = d
            import loop
            importlib.reload(loop)
            ev = pathlib.Path(d) / 'cycles/c000/train/eval'
            for arm, det, other in (('student', student_detect_scores, 1), ('base', (1, 0), 0)):
                for name in ('gate', 'eval-heldout'):
                    rows = []
                    for k in range(30):
                        key = f'{name}-K{k}'
                        for label, sc in zip(('vulnerable', 'not_vulnerable'), det):
                            rows.append({'id': f'{key}-{label}', 'key': key, 'task': 'detect', 'label': label,
                                         'score': sc, 'false_positive': label == 'not_vulnerable' and not sc})
                        rows.append({'id': f'{key}-fs', 'key': key, 'task': 'finding_support', 'label': 'stale',
                                     'score': other, 'false_positive': False})
                    out = ev / arm / name
                    out.mkdir(parents=True)
                    (out / 'items.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
            # Frozen evaluator inputs and a successful CUDA receipt are mandatory for promotion.
            import hashlib
            data = ev.parents[1] / 'data'
            data.mkdir()
            hashes = {}
            for name in ('gate', 'eval-heldout'):
                observed = [json.loads(x) for x in (ev / 'student' / name / 'items.jsonl').read_text().splitlines()]
                expected = [{k: r[k] for k in ('id', 'key', 'task', 'label')} for r in observed]
                p = data / (name + '.jsonl')
                p.write_text(''.join(json.dumps(r) + '\n' for r in expected))
                hashes[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
            (data / 'manifest.json').write_text(json.dumps({'sha256': hashes}))
            receipt = {'cycle': 0, 'finished': '2026-10-30T00:00:00Z', 'gpus': ['NVIDIA T4'],
                       'stages': {step: {'ok': True} for step in
                                  ('setup', 'train', 'merge_convert', 'eval_student', 'eval_base')}}
            (ev.parent / 'receipt.json').write_text(json.dumps(receipt))
            s = {'cycle': 0, 'history': []}
            nxt = loop.step_gate(s, loop.config())
            del os.environ['FORGE_STATE']
            return nxt, s['history'][-1]

    def test_collapsed_student_is_not_promoted(self):
        nxt, v = self.run_gate((0, 1))  # always "not vulnerable": recall 0, wins on finding_support
        self.assertTrue(v['diff'] > 0 and v['degenerate'])
        self.assertEqual(nxt, 'next')

    def test_discriminating_student_is_promoted(self):
        nxt, v = self.run_gate((1, 1))  # gets both versions of every fix right
        self.assertFalse(v['degenerate'])
        self.assertEqual(nxt, 'promote')


class TrainerEncodingTests(unittest.TestCase):
    """SFT rows are tokenized exactly as served: generation prompt (empty think block) + answer + the turn end,
    whether or not the chat template renders that think block for a finished answer (Qwythos-9B-v2 does not)."""

    class Tok:
        def __init__(self, think_in_history):
            self.h = think_in_history

        def apply_chat_template(self, msgs, tools=None, tokenize=False, add_generation_prompt=False, enable_thinking=True):
            out = ''
            for m in msgs:
                if m['role'] == 'assistant':
                    body = m['content'].strip() + ''.join(f'<tc>{c["function"]["name"]}</tc>' for c in m.get('tool_calls', []))
                    out += '<a>\n' + ('<t></t>' if self.h else '') + body + '</e>\n'
                else:
                    out += f'<{m["role"]}>{m["content"]}</e>\n'
            return out + ('<a>\n<t></t>' if add_generation_prompt else '')

        def __call__(self, text, add_special_tokens=False):
            return {'input_ids': [ord(c) for c in text]}

    def encode(self, think_in_history, last=None):
        import ast
        import os
        src = (FORGE / 'kernels' / 'train.py').read_text()
        trainer = next(ast.literal_eval(n.value) for n in ast.parse(src).body
                       if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == 'TRAINER')
        last = last or {'role': 'assistant', 'content': '{"verdict": "safe"}  \n'}
        ns = {'tok': self.Tok(think_in_history), 'cfg': {'max_length': 4096}, 'os': os,
              'rows': [{'messages': [SYSTEM, {'role': 'user', 'content': 'Review.'}, last], 'tools': [{'type': 'function'}]}]}
        exec(trainer[trainer.index('enc, skipped = [], 0'):trainer.index('class DS')], ns)
        e = ns['enc'][0]
        k = e['labels'].count(-100)
        return ''.join(map(chr, e['input_ids'][:k])), ''.join(map(chr, e['input_ids'][k:]))

    def test_same_tokens_with_or_without_think_block_in_history(self):
        stock, qwythos = self.encode(True), self.encode(False)
        self.assertEqual(stock, qwythos)
        self.assertTrue(stock[0].endswith('<a>\n<t></t>'))
        self.assertEqual(stock[1], '{"verdict": "safe"}</e>')

    def test_tool_call_turn_with_empty_content_is_the_target(self):
        call = {'role': 'assistant', 'content': '', 'tool_calls': [{'function': {'name': 'entra_ca_assess', 'arguments': {}}}]}
        for h in (True, False):
            prefix, target = self.encode(h, call)
            self.assertTrue(prefix.endswith('<a>\n<t></t>'))
            self.assertEqual(target, '<tc>entra_ca_assess</tc></e>')


class BackupSelectionTests(unittest.TestCase):
    """Off-box backup: settled data and trained artifacts go up once; secrets, scratch and re-downloadables never."""

    def setUp(self):
        import os
        import backup
        self.b = backup
        self.root = pathlib.Path(tempfile.mkdtemp())
        files = {'state.json': '{}', 'cycles/c000/train/student-Q4_K_M.gguf': 'g', 'cycles/c000/train/adapter/a.json': 'a',
                 'cycles/c000/train/merged/model.safetensors': 'm', 'cycles/c000/student-f16.gguf': 'f',
                 'runs/x/hf_token': 't', 'models/stock.gguf': 's', 'kaggle/staged.jsonl': 'k', 'cycles/c001/new.jsonl': 'n'}
        old = time.time() - 3600
        for rel, text in files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
            if rel != 'cycles/c001/new.jsonl':
                os.utime(p, (old, old))

    def select(self, **kw):
        skipped = []
        got = list(self.b.candidates(self.root, 'forge/', ['state.json', 'cycles', 'runs'], time.time(), skipped=skipped, **kw))
        return sorted(f[0] for f in got), skipped

    def test_selects_settled_artifacts_only(self):
        got, skipped = self.select()
        self.assertEqual(got, ['forge/cycles/c000/train/adapter/a.json', 'forge/cycles/c000/train/student-Q4_K_M.gguf',
                               'forge/state.json'])
        self.assertEqual(skipped, ['forge/runs/x/hf_token'])

    def test_freshly_pulled_run_skips_settle_wait(self):
        got, _ = self.select(fresh_ok=frozenset([self.root / 'cycles/c001']))
        self.assertIn('forge/cycles/c001/new.jsonl', got)

    def test_only_changed_files_are_resent(self):
        files = list(self.b.candidates(self.root, 'forge/', ['state.json'], time.time()))
        manifest = {f[0]: [f[2], f[3]] for f in files}
        self.assertEqual(self.b.changed(files, manifest), [])
        (self.root / 'state.json').write_text('{"cycle": 1}')
        files = list(self.b.candidates(self.root, 'forge/', ['state.json'], time.time() + 3600))
        self.assertEqual([f[0] for f in self.b.changed(files, manifest)], ['forge/state.json'])

    def test_batches_respect_file_and_byte_limits(self):
        files = [(f'p{i}', None, 3 * 2**30, 0) for i in range(3)]
        self.assertEqual([len(b) for b in self.b.batches(files)], [1, 1, 1])


class GpuWantedTests(unittest.TestCase):
    """Model Lab contract: gpu-wanted exists (0600, fresh) only while local training waits for the GPU."""

    def setUp(self):
        import local_train
        self.lt = local_train
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.orig = local_train.GPU_WANTED, local_train.PREEMPT_REQUEST
        local_train.GPU_WANTED = self.tmp / 'gpu-wanted'
        local_train.PREEMPT_REQUEST = self.tmp / 'gpu-preempt-request'

    def tearDown(self):
        self.lt.GPU_WANTED, self.lt.PREEMPT_REQUEST = self.orig

    def wait(self, busy_checks):
        """Run wait_for_quiet_gpu with the GPU busy for `busy_checks` polls; returns gpu-wanted states seen at each sleep."""
        from unittest import mock
        seen, calls = [], {'smi': 0}

        def fake_run(cmd, **kw):
            out = ''
            if cmd[0] == 'nvidia-smi':
                calls['smi'] += 1
                out = '4242\n' if calls['smi'] <= busy_checks else ''
            return mock.Mock(stdout=out, returncode=0)

        def fake_sleep(_):
            w = self.lt.GPU_WANTED
            seen.append(oct(w.stat().st_mode & 0o777) if w.exists() else None)
        with mock.patch.object(self.lt.subprocess, 'run', fake_run), mock.patch.object(self.lt.time, 'sleep', fake_sleep):
            self.lt.wait_for_quiet_gpu(self.tmp, self.tmp / 'log')
        return seen

    def test_written_while_waiting_and_removed_once_gpu_is_held(self):
        self.assertEqual(self.wait(busy_checks=2), ['0o600', '0o600'])
        self.assertFalse(self.lt.GPU_WANTED.exists())

    def test_never_written_when_gpu_is_free(self):
        self.assertEqual(self.wait(busy_checks=0), [])
        self.assertFalse(self.lt.GPU_WANTED.exists())

    def test_refuses_to_follow_a_symlink(self):
        target = self.tmp / 'elsewhere'
        self.lt.GPU_WANTED.symlink_to(target)
        with self.assertRaises(OSError):
            self.lt.want_gpu(True)
        self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
