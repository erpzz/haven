import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import realworld as rw  # noqa: E402


def rows(**arms):
    return {a: {i: {'correct': c, 'wall_s': t, 'key': k} for i, (c, t, k) in items.items()} for a, items in arms.items()}


def test_agree_escalates_only_on_disagreement_and_charges_all_arms():
    r = rows(T={'x': (1, 100, 'v'), 'y': (1, 100, 'v')},
             L={'x': (1, 2, 'v'), 'y': (0, 2, 'n')},
             N={'x': (1, 10, 'v'), 'y': (1, 10, 'v')})
    sim = rw.simulate({'kind': 'agree', 'first': ['L', 'N'], 'escalate': 'T'}, r, ['x', 'y'])
    assert sim['x'] == (1, 12, False)
    assert sim['y'] == (1, 112, True)


def test_agree_never_accepts_an_unreadable_answer():
    r = rows(T={'x': (1, 100, None)}, L={'x': (0, 2, None)}, N={'x': (0, 10, None)})
    sim = rw.simulate({'kind': 'agree', 'first': ['L', 'N'], 'escalate': 'T'}, r, ['x'])
    assert sim['x'] == (1, 112, True)


def test_score_policy_counts_paired_wins_losses_and_speedup():
    r = rows(T={'x': (1, 100, 'v'), 'y': (0, 100, 'v')}, N={'x': (0, 10, 'n'), 'y': (1, 10, 'v')})
    s = rw.score_policy('N', {'kind': 'single', 'arm': 'N'}, r, ['x', 'y'], 'T')
    assert (s['correct'], s['baseline_correct'], s['wins'], s['losses'], s['speedup']) == (1, 1, 1, 1, 10.0)
    assert s['non_inferior'] and s['mcnemar_p'] == 1.0


def test_answer_keys_come_from_output_only():
    assert rw.answer_key_secpatch('detect', '{"verdict": "vulnerable"}') == 'vulnerable'
    assert rw.answer_key_secpatch('root_cause', '{"cwe": ["CWE-79", "CWE-20"]}') == ('CWE-20', 'CWE-79')
    assert rw.answer_key_secpatch('remediate', '```python\nx\n```') is None
    rec = {'ok_transport': True, 'answer': 'Done.\n{"claims": [{"value": 3, "evidence_id": "e1", "status": "supported"}]}',
           'trace': [{'name': 'haven_read_note'}]}
    assert rw.answer_key_adjudicated(rec) == rw.answer_key_adjudicated(
        {**rec, 'answer': 'Other words.\n{ "claims": [{"value": 3, "evidence_id": "e9", "status": "supported"}]}'})
    assert rw.answer_key_adjudicated({**rec, 'ok_transport': False}) is None


def test_exact_mcnemar():
    assert rw.exact_mcnemar(0, 0) == 1.0
    assert round(rw.exact_mcnemar(0, 6), 4) == 0.0312


def test_route_uses_each_kinds_own_policy():
    r = rows(T={'s': (1, 100, 'v'), 'a': (1, 50, 'v')}, D={'s': (1, 30, 'v')}, N={'s': (0, 5, 'n'), 'a': (1, 5, 'v')})
    for arm in r.values():
        for i, row in arm.items():
            row['kind'] = 'secpatch' if i == 's' else 'adjudicated'
    policies = {'D': {'kind': 'single', 'arm': 'D'}, 'N': {'kind': 'single', 'arm': 'N'},
                'route_D_N': {'kind': 'route', 'route': {'secpatch': 'D', 'adjudicated': 'N'}}}
    pol = rw.resolve(policies['route_D_N'], policies)
    assert rw.arms_of(pol) == {'D', 'N'}
    sim = rw.simulate(pol, r, ['s', 'a'])
    assert sim == {'s': (1, 30, False), 'a': (1, 5, False)}


def test_draft_is_appended_to_the_last_user_turn_and_marked_unverified():
    msgs = [{'role': 'system', 'content': 'sys'}, {'role': 'user', 'content': 'code'}]
    out = rw.with_draft(msgs, '  thoughts  ')
    assert msgs[1]['content'] == 'code'
    assert out[1]['content'].startswith('code\n\nA faster assistant') and '<draft>\nthoughts\n</draft>' in out[1]['content']


def test_route_by_task_before_kind():
    r = rows(T={'rc': (1, 100, 'v'), 'd': (0, 100, 'v')}, N={'rc': (0, 5, 'n'), 'd': (1, 5, 'v')})
    for arm in r.values():
        arm['rc'].update(kind='secpatch', task='root_cause')
        arm['d'].update(kind='secpatch', task='detect')
    pol = {'kind': 'route', 'route': {'root_cause': {'kind': 'single', 'arm': 'T'}, 'secpatch': {'kind': 'single', 'arm': 'N'}}}
    assert rw.simulate(pol, r, ['rc', 'd']) == {'rc': (1, 100, False), 'd': (1, 5, False)}
