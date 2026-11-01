"""Verified tool-use trajectories for a Qwythos agent-reliability adapter (Haven cyber lab, condition C/D format).

Every trajectory is built from a freshly generated task whose ground truth comes from the lab's deterministic tools,
never from the evaluation set:
  ca      a new synthetic tenant snapshot (own names, own UUIDv5 namespace) -> entra_ca_assess -> rule statuses
  rbac    a new role/assignment/group/deny set                                 -> azure_rbac_check -> allowed or not
  host    a new authorized lab host with recorded read-only command outputs    -> run_command -> listening ports
The assistant turns call the right tool with thinking off, read the real ToolEnv result (including errors such as
`command not found` or `not_applicable`, which are recovered from), and finish with only the requested JSON. Each
final answer must pass the lab's own grader (haven_cyber.eval.grade) against the generated ground truth, and each
row is screened against the evaluation set (canary, scenario ids, UUIDs, documentation IPs, distinctive names).

Output, one SFT row per assistant step (the forge trainer's format plus `tools`); a step that is a deliberate wrong
first move (a non-applicable tool, a missing program) only appears as history, never as a training target:
  agentgen.py --cyber-root ~/.local/state/haven-cyber/code --out DIR --n-ca 500 --n-rbac 500 --n-host 400 --seed 1
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import sys
import uuid

NS = uuid.UUID('3a7d5e2c-9b14-4f0a-8c61-5f0e2b7d4a90')  # not the fixtures' namespace: no id can collide with eval artifacts
FIRST = ['amara', 'bo', 'chen', 'dmitri', 'esi', 'farah', 'goran', 'hiro', 'ines', 'jonas', 'kaveh', 'lena', 'malik',
         'nia', 'oskar', 'priya', 'quinn', 'rafa', 'sven', 'tala', 'uma', 'vik', 'wren', 'yusuf', 'zoe']
ORGS = ['northwind', 'tailspin', 'woodgrove', 'litware', 'adatum', 'proseware', 'wingtip', 'lucerne', 'alpine', 'fourthcoffee']


def oid(*parts) -> str:
    return str(uuid.uuid5(NS, ':'.join(map(str, parts))))


# ---------------------------------------------------------------- Conditional Access tenants
def ca_task(rng: random.Random, i: int, B) -> tuple[dict, dict]:
    org = rng.choice(ORGS)
    dom = f'{org}{i}.example'
    names = rng.sample(FIRST, rng.randint(6, 10))
    users = {n: {'id': oid(org, i, 'user', n), 'userPrincipalName': f'{n}@{dom}', 'userType': 'Member', 'accountEnabled': True}
             for n in names}
    admins, rest = names[:2], names[2:]
    em_names = [f'breakglass{k}' for k in (1, 2)]
    for n in em_names:
        users[n] = {'id': oid(org, i, 'user', n), 'userPrincipalName': f'{n}@{dom}', 'userType': 'Member', 'accountEnabled': True}
    g_em = {'id': oid(org, i, 'group', 'em'), 'displayName': f'{org}-break-glass', 'members': [users[n]['id'] for n in em_names]}
    g_staff = {'id': oid(org, i, 'group', 'staff'), 'displayName': f'{org}-field-staff', 'members': [users[n]['id'] for n in rest]}
    roles = [{'roleTemplateId': B.GA, 'principalId': users[n]['id']} for n in admins + em_names]
    hard = rng.random() < 0.2  # a well-configured tenant: every rule passes, so the right answer is "no gaps"
    has = lambda p: hard or rng.random() < p  # policy present
    gap = lambda p: not hard and rng.random() < p  # a misconfiguration
    state = lambda *bad: 'enabled' if hard else rng.choice(['enabled', 'enabled', *bad])
    em_ex = not gap(0.25)  # emergency accounts excluded from enforcing policies?
    ex = [g_em['id']] if em_ex else []

    def pol(label, **kw):
        p = B.policy(label, **kw)
        p['id'] = oid(org, i, 'policy', label)
        return p
    pols = []
    tag = lambda k: f'P{k:02d} '
    if has(0.8):
        pols.append(pol(tag(1) + 'Block legacy auth', include_users=['All'], exclude_groups=ex + ([g_staff['id']] if gap(0.25) else []),
                        clients=['exchangeActiveSync', 'other'], controls=['block'], state=state('enabled', 'disabled')))
    if has(0.85):
        pols.append(pol(tag(2) + 'Admins require MFA', include_roles=[B.GA, B.PRA, B.SECADM],
                        exclude_users=[users[admins[1]]['id']] if gap(0.3) else [], exclude_groups=ex, controls=['mfa']))
    if has(0.8):
        pols.append(pol(tag(3) + 'All users require MFA', include_users=['All'], exclude_groups=ex, controls=['mfa'],
                        state=state('enabledForReportingButNotEnforced', 'disabled')))
    if has(0.5):
        pols.append(pol(tag(4) + 'Phishing-resistant MFA for admins', include_roles=[B.GA, B.PRA, B.SECADM] if hard else [B.GA],
                        exclude_groups=ex, strength=B.PHISH, state=state('disabled')))
    if has(0.6):
        pols.append(pol(tag(5) + 'Block risky sign-ins', include_users=['All'], exclude_groups=ex,
                        sign_in_risk=rng.choice([['high'], ['high', 'medium']]), controls=['block']))
    if has(0.45):
        pols.append(pol(tag(6) + 'Block device code flow', include_users=['All'], exclude_groups=ex, controls=['block'],
                        flows=['deviceCodeFlow']))
    if not hard and rng.random() < 0.3:
        pols.append(pol(tag(7) + 'Staff MFA or compliant device', include_groups=[g_staff['id']],
                        exclude_users=[oid(org, i, 'user', 'removed-account')] if rng.random() < 0.6 else [],
                        controls=['mfa', 'compliantDevice']))
    snap = B.snapshot(f'{org}{i}', pols, users, {'em': g_em, 'staff': g_staff}, roles, [users[n]['id'] for n in em_names])
    snap['tenant'] = {'id': oid(org, i, 'tenant'), 'displayName': f'{org.title()} {i} (synthetic)'}
    from haven_cyber.tools.entra_ca import assess_dict
    status = {}
    for f in assess_dict(snap).findings:  # several findings per rule are possible: any fail wins
        status[f.source_check_id] = 'fail' if 'fail' in (status.get(f.source_check_id), f.status) else f.status
    kind = rng.choice(['failing', 'rule', 'rule', 'mfa_all'])
    if kind == 'failing':
        failing = sorted(r for r, s in status.items() if s == 'fail')
        q = 'Assess this tenant snapshot against the Haven Conditional Access rules and list every rule that fails.'
        fmt = {'failing_rules': 'list of rule ids like HCA-001'}
        answer = {'failing_rules': failing}
        checks = [{'field': 'failing_rules', 'op': 'contains_all', 'value': failing},
                  {'field': 'failing_rules', 'op': 'contains_none', 'value': sorted(set(status) - set(failing))}]
    elif kind == 'rule':
        rule = rng.choice(sorted(status))
        q = f'Using the tenant snapshot, what is the status of Haven Conditional Access rule {rule}?'
        fmt = {'rule': rule, 'status': ['pass', 'fail', 'manual']}
        answer = {'rule': rule, 'status': status[rule]}
        checks = [{'field': 'status', 'op': 'equals', 'value': status[rule]}]
    else:
        st = status.get('HCA-003', 'fail')
        q = 'Is multifactor authentication actually enforced for all users in this tenant (not report-only, not disabled)?'
        fmt = {'mfa_enforced_for_all_users': ['yes', 'no'], 'rule': 'HCA-003'}
        answer = {'mfa_enforced_for_all_users': 'yes' if st == 'pass' else 'no', 'rule': 'HCA-003'}
        checks = [{'field': 'mfa_enforced_for_all_users', 'op': 'equals', 'value': answer['mfa_enforced_for_all_users']}]
    task = {'id': f'gen-ca-{i}', 'category': 'ca', 'question': q, 'artifacts': {'tenant_snapshot': snap}, 'answer_format': fmt}
    label = f'{kind}:{answer.get("status") or answer.get("mfa_enforced_for_all_users") or min(len(answer.get("failing_rules", [])), 3)}'
    return task, {'answer': answer, 'truth': {'checks': checks}, 'plan': [('entra_ca_assess', {})], 'label': label}


# ---------------------------------------------------------------- Azure RBAC
OPS = ['Microsoft.Compute/virtualMachines/start/action', 'Microsoft.Compute/virtualMachines/delete',
       'Microsoft.Storage/storageAccounts/listKeys/action', 'Microsoft.KeyVault/vaults/write',
       'Microsoft.Authorization/roleAssignments/write', 'Microsoft.Network/networkSecurityGroups/write',
       'Microsoft.Resources/subscriptions/resourceGroups/read', 'Microsoft.Web/sites/restart/action']
DATA_OPS = ['Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read',
            'Microsoft.KeyVault/vaults/secrets/getSecret/action']


def rbac_task(rng: random.Random, i: int, B) -> tuple[dict, dict]:
    org = rng.choice(ORGS)
    sub = f'/subscriptions/{oid(org, i, "sub")}'
    rgs = [f'{sub}/resourceGroups/rg-{w}-{i}' for w in rng.sample(['app', 'data', 'ops', 'web', 'shared', 'ml'], 3)]
    people = rng.sample(FIRST, 4)
    pid = {p: oid(org, i, 'principal', p) for p in people}
    grp = oid(org, i, 'group', 'ops')
    data_action = rng.random() < 0.25
    op = rng.choice(DATA_OPS if data_action else OPS)
    prov = op.split('/')[0]
    defs = [
        {'id': oid(org, i, 'role', 'wide'), 'roleName': f'{org}-{prov.split(".")[1].lower()}-operator',
         'actions': [] if data_action else [f'{prov}/*'], 'notActions': [] if data_action else ([op] if rng.random() < 0.35 else []),
         'dataActions': [f'{prov}/*'] if data_action else [], 'notDataActions': [op] if data_action and rng.random() < 0.35 else []},
        {'id': oid(org, i, 'role', 'reader'), 'roleName': f'{org}-reader', 'actions': ['*/read'], 'notActions': [],
         'dataActions': [], 'notDataActions': []},
        {'id': oid(org, i, 'role', 'narrow'), 'roleName': f'{org}-limited-{rng.choice(["ops", "support", "deploy"])}',
         'actions': [] if data_action else [op if rng.random() < 0.4 else rng.choice(OPS)], 'notActions': [],
         'dataActions': [op] if data_action and rng.random() < 0.4 else [], 'notDataActions': []},
    ]
    who = people[0]
    assigns = []
    for k in range(rng.randint(2, 4)):
        assigns.append({'id': oid(org, i, 'assign', k), 'principalId': rng.choice([pid[who], grp] + [pid[p] for p in people[1:]]),
                        'roleDefinitionId': rng.choice(defs)['id'], 'scope': rng.choice([sub] + rgs)})
    denies = []
    if rng.random() < 0.25:
        denies.append({'id': oid(org, i, 'deny'), 'name': f'{org}-protect-{rng.choice(["prod", "keys", "network"])}',
                       'scope': rng.choice([sub] + rgs), 'principals': ['everyone'],
                       'excludePrincipals': [pid[people[1]]] if rng.random() < 0.5 else [],
                       'actions' if not data_action else 'dataActions': [op]})
    data = {'roleDefinitions': defs, 'roleAssignments': assigns, 'denyAssignments': denies,
            'groups': {grp: [pid[who]] if rng.random() < 0.6 else [pid[people[2]]]}}
    scope = rng.choice(rgs) + rng.choice(['', f'/providers/{prov}/item-{i}'])
    from haven_cyber.tools import azure_rbac
    res = azure_rbac.check(data, pid[who], op, scope, data_action)
    roles = sorted({g['role'] for g in res['granted_by']}) if res['allowed'] else []
    q = (f'Can principal {pid[who]} perform {op} at scope {scope}'
         + (' (a data-plane operation)' if data_action else '') + '? Use the exported Azure RBAC data.')
    fmt = {'allowed': ['yes', 'no'], 'granting_roles': 'list of role names (empty if not allowed)',
           'blocked_by_deny_assignment': ['yes', 'no']}
    answer = {'allowed': 'yes' if res['allowed'] else 'no', 'granting_roles': roles,
              'blocked_by_deny_assignment': 'yes' if res['denied_by'] else 'no'}
    checks = [{'field': 'allowed', 'op': 'equals', 'value': answer['allowed']},
              {'field': 'blocked_by_deny_assignment', 'op': 'equals', 'value': answer['blocked_by_deny_assignment']}]
    if roles:
        checks.append({'field': 'granting_roles', 'op': 'contains_all', 'value': roles})
    task = {'id': f'gen-rbac-{i}', 'category': 'rbac', 'question': q, 'artifacts': {'azure_rbac': data}, 'answer_format': fmt}
    args = {'principal': pid[who], 'operation': op, 'scope': scope, **({'data_action': True} if data_action else {})}
    plan = [('azure_rbac_check', args)]
    if rng.random() < 0.15:  # recover from a non-applicable first move
        plan.insert(0, ('entra_ca_assess', {}))
    return task, {'answer': answer, 'truth': {'checks': checks}, 'plan': plan, 'label': f'allowed:{answer["allowed"]}'}


# ---------------------------------------------------------------- authorized lab hosts
SERVICES = [(22, 'sshd'), (80, 'nginx'), (443, 'nginx'), (5432, 'postgres'), (6379, 'redis-server'), (3306, 'mysqld'),
            (8080, 'java'), (9100, 'node_exporter'), (25, 'master'), (8443, 'caddy'), (9090, 'prometheus'), (5000, 'gunicorn'),
            (27017, 'mongod'), (11211, 'memcached'), (2049, 'rpc.nfsd'), (631, 'cupsd')]


def host_task(rng: random.Random, i: int, B) -> tuple[dict, dict]:
    name = f'lab-{rng.choice(["alder", "birch", "cedar", "elm", "fir", "hazel", "larch", "maple", "oak", "rowan"])}-{i % 997:03d}'
    svcs = rng.sample(SERVICES, rng.randint(3, 7))
    rows = []
    for k, (port, proc) in enumerate(sorted(svcs)):
        addr = rng.choice(['0.0.0.0', '0.0.0.0', '127.0.0.1', '[::]', f'10.{rng.randint(1, 250)}.{rng.randint(0, 255)}.{rng.randint(2, 254)}'])
        rows.append((addr, port, proc, 1000 + 37 * k + rng.randint(0, 30)))
    ss = 'State  Recv-Q Send-Q Local Address:Port Peer Address:Port Process\n' + ''.join(
        f'LISTEN 0      {rng.choice([128, 511, 4096])}    {a}:{p}    {"[::]:*" if a.startswith("[") else "0.0.0.0:*"}    users:(("{n}",pid={pid},fd={rng.randint(3, 12)}))\n'
        for a, p, n, pid in rows)
    netstat = 'Active Internet connections (only servers)\nProto Recv-Q Send-Q Local Address Foreign Address State PID/Program name\n' + ''.join(
        f'tcp{"6" if a.startswith("[") else ""}   0      0 {a.strip("[]") if not a.startswith("[") else ":::"}{"" if a.startswith("[") else ":"}{p}   {"::" if a.startswith("[") else "0.0.0.0"}:*   LISTEN   {pid}/{n}\n'
        for a, p, n, pid in rows)
    missing = ['netstat'] if rng.random() < 0.5 else []
    host = {'name': name, 'commands': {'ss -tlnp': ss, **({} if missing else {'netstat -tlnp': netstat})}, 'missing': missing}
    exposed = sorted(p for a, p, _, _ in rows if not a.startswith('127.'))
    kind = rng.choice(['exposed', 'exposed', 'owner'])
    if kind == 'exposed':
        q = f'On the authorized lab host {name}, which TCP ports are listening on a non-loopback address? Check the host; do not guess.'
        fmt = {'host': name, 'ports': 'sorted list of port numbers'}
        answer = {'host': name, 'ports': exposed}
        checks = [{'field': 'ports', 'op': 'contains_all', 'value': exposed},
                  {'field': 'ports', 'op': 'contains_none', 'value': sorted({p for _, p, _, _ in rows} - set(exposed))}]
    else:
        a, p, n, _ = rng.choice(rows)
        q = f'Which process is listening on TCP port {p} on the authorized lab host {name}, and on which address?'
        fmt = {'process': 'process name', 'address': 'listen address as shown'}
        answer = {'process': n, 'address': a}
        checks = [{'field': 'process', 'op': 'equals', 'value': n}]
    plan = [('run_command', {'command': 'ss -tlnp'})]
    if missing or rng.random() < 0.3:  # an operator reaching for netstat first; recover when it is absent
        plan.insert(0, ('run_command', {'command': 'netstat -tlnp'}))
        if not missing:
            plan.pop()  # netstat works here: its output is enough
    task = {'id': f'gen-host-{i}', 'category': 'os', 'question': q, 'artifacts': {}, 'host': host, 'answer_format': fmt}
    return task, {'answer': answer, 'truth': {'checks': checks}, 'plan': plan, 'label': f'{kind}:recover={len(plan) > 1}'}


# ---------------------------------------------------------------- trajectories, grading, leakage screen
def eval_markers(cyber: pathlib.Path) -> tuple[list[str], set[str]]:
    sc = json.loads((cyber / 'eval' / 'scenarios' / 'v1.json').read_text())
    blob = json.dumps(sc['scenarios'])
    exact = {sc['canary']} | {s['id'] for s in sc['scenarios']}
    builtin = {'62e90394-69f5-4237-9190-012177145e10', 'e8611ab8-c189-46e8-94e1-60213ab1f814', '194ae4cb-b126-40b2-bd5b-6091b380977d',
               '00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000004'}
    exact |= set(re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', blob)) - builtin
    exact |= set(re.findall(r'\d+\.\d+p\d+-\S+|ubuntu0\.\d+|198\.51\.100\.\d+|203\.0\.113\.\d+|192\.0\.2\.\d+', blob))
    generic = {'Global Administrator', 'Privileged Role Administrator', 'Security Administrator', 'Multifactor authentication',
               'Phishing-resistant MFA', 'Contractors', 'custom'}
    for s in sc['scenarios']:
        generic |= {p['displayName'] for p in (s['artifacts'].get('tenant_snapshot') or {}).get('conditionalAccessPolicies', [])}
        exact |= {n for n in re.findall(r'"(?:clientDisplayName|displayName)": "([^"]{6,})"', json.dumps(s['artifacts']))
                  if n not in generic}
        if s.get('host'):
            exact.add(s['host']['name'])
    ids = re.compile(r'\b(?:' + '|'.join(re.escape(s['id']) for s in sc['scenarios']) + r')\b')
    return sorted(x for x in exact if len(x) >= 6), {'ids': ids}


def leaks(text: str, exact: list[str], rx: dict) -> str | None:
    low = text.lower()
    for x in exact:
        if x.lower() in low:
            return x
    m = rx['ids'].search(text)
    return m.group(0) if m else None


def trajectory(task: dict, spec: dict, kb, H) -> tuple[list[dict], list[int], dict]:
    """Messages exactly as the harness builds them for condition C, the planned tool calls run through the real
    ToolEnv, then the final JSON. Returns (messages, indexes of assistant turns to train on, grade)."""
    from haven_cyber.eval.grade import grade
    from haven_cyber.eval.toolenv import ToolEnv
    refs, _ = kb.retrieve(task['question'], k=3, max_chars=4500)
    msgs = [{'role': 'system', 'content': H.SYSTEM + H.TOOL_SYSTEM}, {'role': 'user', 'content': H.user_prompt(task, refs, True)}]
    env, train_on = ToolEnv(task, kb), []
    for k, (name, args) in enumerate(spec['plan']):
        out = env.call(name, args)
        if 'error' not in out and out.get('exit_code', 0) == 0:  # a wrong first move stays history, never a target
            train_on.append(len(msgs))
        msgs.append({'role': 'assistant', 'content': '', 'tool_calls': [
            {'id': f'call_{k + 1}', 'type': 'function', 'function': {'name': name, 'arguments': args}}]})
        msgs.append({'role': 'tool', 'tool_call_id': f'call_{k + 1}', 'content': json.dumps(out, default=str)[:12000]})
    final = json.dumps(spec['answer'])
    train_on.append(len(msgs))
    msgs.append({'role': 'assistant', 'content': final})
    return msgs, train_on, grade(final, spec['truth'])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cyber-root', type=pathlib.Path, required=True, help='labs/cyber checkout (haven_cyber, fixtures, eval)')
    ap.add_argument('--out', type=pathlib.Path, required=True)
    ap.add_argument('--n-ca', type=int, default=500)
    ap.add_argument('--n-rbac', type=int, default=500)
    ap.add_argument('--n-host', type=int, default=400)
    ap.add_argument('--seed', type=int, default=1)
    args = ap.parse_args(argv)
    cyber = args.cyber_root.expanduser().resolve()
    sys.path[:0] = [str(cyber), str(cyber / 'fixtures' / 'tenants')]
    import build as B  # fixtures/tenants/build.py: schema helpers only; ids are re-derived in our namespace
    from haven_cyber.eval import harness as H
    from haven_cyber.eval.toolenv import TOOLS
    from haven_cyber.kb import KB
    kb = KB()
    exact, rx = eval_markers(cyber)
    rng = random.Random(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    stats = {'tasks': 0, 'kept': 0, 'grade_failed': 0, 'leak_rejected': 0, 'rows': 0, 'by_family': {}, 'leaks': {}}
    with (args.out / 'trajectories.jsonl').open('w') as ft, (args.out / 'sft.jsonl').open('w') as fs:
        for fam, n, fn in (('ca', args.n_ca, ca_task), ('rbac', args.n_rbac, rbac_task), ('host', args.n_host, host_task)):
            seen, i = {}, 0
            while sum(seen.values()) < n and i < 50 * n:
                task, spec = fn(rng, args.seed * 100000 + i, B)
                i += 1
                stats['tasks'] += 1
                # Balance answers: no label may run far ahead of the others (an RBAC set that is 80% "no" teaches "no").
                if seen.get(spec['label'], 0) > min(seen.values(), default=0) + max(3, n // 25) and len(seen) > 1:
                    continue
                msgs, train_on, g = trajectory(task, spec, kb, H)
                if not g['pass']:
                    stats['grade_failed'] += 1
                    continue
                hit = leaks(json.dumps(msgs), exact, rx)
                if hit:
                    stats['leak_rejected'] += 1
                    stats['leaks'][hit] = stats['leaks'].get(hit, 0) + 1
                    continue
                stats['kept'] += 1
                seen[spec['label']] = seen.get(spec['label'], 0) + 1
                stats['by_family'][fam] = stats['by_family'].get(fam, 0) + 1
                stats.setdefault('labels', {})[f'{fam} {spec["label"]}'] = seen[spec['label']]
                ft.write(json.dumps({'id': task['id'], 'family': fam, 'messages': msgs, 'tools': TOOLS, 'train_on': train_on}) + '\n')
                for j in train_on:  # one row per trained assistant step: prefix + that turn, as served
                    fs.write(json.dumps({'id': f'{task["id"]}-s{j}', 'key': task['id'], 'task': f'agent-{fam}',
                                         'messages': msgs[:j + 1], 'tools': TOOLS}) + '\n')
                    stats['rows'] += 1
    (args.out / 'manifest.json').write_text(json.dumps({**stats, 'seed': args.seed, 'generator': 'agentgen v1'}, indent=1))
    print(json.dumps(stats, indent=1))


if __name__ == '__main__':
    main()
