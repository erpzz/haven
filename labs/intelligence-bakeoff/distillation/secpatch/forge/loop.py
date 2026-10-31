"""secpatch forge: a self-improving training loop that runs unattended on Slink.

Every `tick` (systemd user timer) advances the current cycle by at most one step and returns; all state lives
in ~/.local/state/haven-forge/state.json, so a crash, reboot or exhausted quota only delays the loop.

Cycle N:
  refresh   weekly: fetch the OSV PyPI export, harvest new fix commits (resumable), rebuild the dataset
  mix       pool = recorded rows + verified teacher traces + verified self-play samples from earlier cycles
  teach     GLM-4.7-Flash writes code-grounded analyses for untaught rows, checked against ground truth
            (Kaggle 2x T4, free weekly quota; Slink's own GPU teaches its shard in parallel)
  train     QLoRA SFT of the student, merge, GGUF, then the student, the base and the current champion are
            served and graded on the gate and held-out sets; the student then samples answers to training rows,
            and the ones the graders accept become next cycle's self-play data
  gate      promote only if the student beats the champion on gate+held-out (cluster bootstrap by fix,
            p < max_p_value) without raising the false-positive rate; otherwise keep the champion
  promote   upload the GGUF + adapter to the private HF repo, register the model on Slink, start cycle N+1

No step needs Claude, Codex, the HF router or any paid API. Credits, when present, only add lanes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import random
import shutil
import subprocess
import sys
import time

from evidence_gate import EvidenceError, verify_complete

HERE = pathlib.Path(__file__).resolve().parent
HOME = pathlib.Path.home()
STATE_DIR = pathlib.Path(os.environ.get('FORGE_STATE', HOME / '.local/state/haven-forge'))
SECPATCH_STATE = HOME / '.local/state/haven-secpatch'
VENV = HOME / '.local/share/haven-forge-venv/bin'
KAGGLE = str(VENV / 'kaggle')
STATE = STATE_DIR / 'state.json'
LOG = STATE_DIR / 'logs' / 'loop.jsonl'
ENGINE_DATASET = 'haven-llama-engine'
STALE_KERNEL_S = 13 * 3600


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def log(event: str, **kw):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    rec = {'t': now(), 'event': event, **kw}
    with LOG.open('a') as f:
        f.write(json.dumps(rec, default=str) + '\n')
    print(json.dumps(rec, default=str), flush=True)


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {'cycle': 0, 'step': 'mix', 'champion': None, 'history': []}


def save_state(s: dict):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, indent=1, default=str))
    tmp.replace(STATE)


def config() -> dict:
    cfg = json.loads((HERE / 'config.json').read_text())
    override = STATE_DIR / 'config.override.json'
    if override.exists():
        for k, v in json.loads(override.read_text()).items():
            cfg[k] = {**cfg[k], **v} if isinstance(v, dict) and isinstance(cfg.get(k), dict) else v
    return cfg


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    env = {**os.environ, 'KAGGLE_API_TOKEN': (HOME / '.kaggle/access_token').read_text().strip()}
    return subprocess.run(cmd, capture_output=True, text=True, env=env, **kw)


def cdir(s: dict) -> pathlib.Path:
    return STATE_DIR / 'cycles' / f'c{s["cycle"]:03d}'


def latest_data(cfg: dict | None = None) -> pathlib.Path:
    """Newest dataset among the weekly refreshes and the configured base (other data-* dirs are experiments)."""
    cfg = cfg or {}
    cands = list(SECPATCH_STATE.glob('data-auto-*'))
    if cfg.get('data_dir'):
        cands.append(pathlib.Path(cfg['data_dir']).expanduser())
    if not cands:
        cands = list(SECPATCH_STATE.glob('data-*'))
    dirs = sorted((d for d in cands if (d / 'manifest.json').exists()),
                  key=lambda d: json.loads((d / 'manifest.json').read_text())['built_at'])
    return dirs[-1]


# ---------------------------------------------------------------- steps

def step_refresh(s, cfg):
    """Weekly data refresh with the unchanged secpatch harvest/build pipeline (resumable, CPU + network)."""
    last = s.get('refreshed_at')
    if last and (time.time() - dt.datetime.fromisoformat(last.replace('Z', '+00:00')).timestamp()) < 6 * 86400:
        return 'mix'
    code, S = STATE_DIR / 'code/secpatch', SECPATCH_STATE
    bandit = HOME / '.local/share/haven-secpatch-venv/bin/bandit'
    stamp = dt.date.today().strftime('%Y%m%d')
    cmds = [
        ['curl', '-sfL', '-o', str(S / 'raw/pypi-all.zip'),
         'https://osv-vulnerabilities.storage.googleapis.com/PyPI/all.zip'],
        [sys.executable, str(code / 'osv.py'), '--archive', str(S / 'raw/pypi-all.zip'), '--out', str(S / 'candidates.jsonl')],
        [sys.executable, str(code / 'harvest.py'), '--candidates', str(S / 'candidates.jsonl'), '--out',
         str(S / f'harvest-auto-{stamp}.jsonl'), '--work', str(S / 'git-auto'), '--per-repo', '12',
         '--exclude-repo', 'tensorflow/tensorflow'],
        [sys.executable, str(code / 'harvest.py'), '--rescan', *map(str, sorted(S.glob('harvest*.jsonl'))),
         '--work-dirs', *map(str, sorted(S.glob('git*'))), '--out', str(S / 'scope.jsonl')],
        [sys.executable, str(code / 'build.py'), '--candidates', str(S / 'candidates.jsonl'), '--harvest',
         *map(str, sorted(S.glob('harvest*.jsonl'))), '--scope', str(S / 'scope.jsonl'),
         '--out', str(S / f'data-auto-{stamp}'), '--bandit', str(bandit), '--multi-function'],
    ]
    for cmd in cmds:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=6 * 3600)
        if r.returncode:
            log('refresh_failed', cmd=cmd[:3], stderr=r.stderr[-1500:])
            s['refreshed_at'] = now()  # retry next week; the previous data stays in use
            return 'mix'
    s['refreshed_at'] = now()
    log('refreshed', data=str(S / f'data-auto-{stamp}'))
    return 'mix'


def prior_files(s, pattern: str) -> list[pathlib.Path]:
    return sorted((STATE_DIR / 'cycles').glob(pattern))


def step_mix(s, cfg, data: pathlib.Path | None = None):
    out = cdir(s) / 'data'
    data = data or latest_data(cfg)
    traces = prior_files(s, 'c*/teach/traces*.jsonl')
    selfplay = prior_files(s, 'c*/train/selfplay/selfplay-sft.jsonl')
    pairs = prior_files(s, 'c*/train/selfplay/selfplay-pairs.jsonl')
    drops = prior_files(s, 'c*/review-teach.json') + prior_files(s, 'c*/review-drops*.json')
    r = subprocess.run([sys.executable, str(HERE / 'mix.py'), '--data', str(data), '--out', str(out), '--traces',
                        *map(str, traces), '--selfplay', *map(str, selfplay), '--pairs', *map(str, pairs),
                        '--reviews', *map(str, drops), '--critic', *map(str, prior_files(s, 'c*/teach/critic*.jsonl'))],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])
    s['data'] = str(data)
    log('mixed', cycle=s['cycle'], data=str(data), traces=len(traces), selfplay=len(selfplay))
    return 'teach'


def start_slink_teacher(s, cfg):
    """Slink's own GPU teaches its shard of this cycle's pool (lowest CPU priority; chat keeps the machine)."""
    lane = cfg.get('slink_teacher') or {}
    if not lane.get('enabled', True):
        return
    active = subprocess.run(['systemctl', '--user', 'is-active', 'forge-teach-slink'], capture_output=True, text=True)
    server = subprocess.run(['systemctl', '--user', 'is-active', 'forge-teacher-server'], capture_output=True, text=True)
    if active.stdout.strip() == 'active' or server.stdout.strip() != 'active':
        return
    subprocess.run(['systemctl', '--user', 'reset-failed', 'forge-teach-slink'], capture_output=True)
    out = cdir(s) / 'teach' / 'traces-slink.jsonl'
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(['systemd-run', '--user', '--unit', 'forge-teach-slink', '-p', 'CPUWeight=1', '-p', 'Nice=19',
                        sys.executable, str(HERE / 'teach.py'), '--rows', str(cdir(s) / 'data' / 'pool.jsonl'),
                        '--out', str(out), '--base-url', f'http://127.0.0.1:{lane.get("port", 8093)}/v1',
                        '--model', 'teacher', '--workers', str(lane.get('workers', 2)), '--attempts', '3',
                        '--shard', lane.get('shard', '6-7/8'), '--think-retries', str(lane.get('think_retries', 0))],
                       capture_output=True, text=True)
    log('slink_teacher_started' if r.returncode == 0 else 'slink_teacher_failed', cycle=s['cycle'],
        detail=(r.stdout + r.stderr)[-300:])


def package(s, cfg, kind: str) -> str:
    """Stage the cycle as a private Kaggle dataset (create or new version). Returns its slug."""
    slug = f'haven-forge-c{s["cycle"]:03d}'
    stage = STATE_DIR / 'kaggle' / slug
    if stage.exists():
        shutil.rmtree(stage)
    (stage / 'code/forge').mkdir(parents=True)
    for name in ('sft.jsonl', 'pool.jsonl', 'pairs.jsonl', 'gate.jsonl', 'eval-heldout.jsonl', 'manifest.json'):
        if (cdir(s) / 'data' / name).exists() or name != 'pairs.jsonl':  # pairs are optional (older cycles)
            shutil.copy(cdir(s) / 'data' / name, stage / name)
    for f in [*HERE.glob('*.py'), HERE / 'handbook.md']:
        shutil.copy(f, stage / 'code/forge' / f.name)
    for name in ('evaluate.py', 'harvest.py'):
        shutil.copy(STATE_DIR / 'code/secpatch' / name, stage / 'code' / name)
    if kind == 'teach':  # only the teacher needs earlier traces (to skip taught rows); they make up most of the bytes
        for prev in prior_files(s, 'c*/teach/traces*.jsonl'):
            shutil.copy(prev, stage / f'traces-{prev.parent.parent.name}-{prev.name}')
    (stage / 'config.json').write_text(json.dumps({**cfg, 'cycle': s['cycle'], 'kind': kind}, indent=1))
    (stage / 'dataset-metadata.json').write_text(json.dumps(
        {'title': slug, 'id': f'{cfg["kaggle_owner"]}/{slug}', 'licenses': [{'name': 'other'}], 'isPrivate': True}))
    exists = run([KAGGLE, 'datasets', 'status', f'{cfg["kaggle_owner"]}/{slug}']).returncode == 0
    cmd = ([KAGGLE, 'datasets', 'version', '-p', str(stage), '-m', f'{kind} {now()}', '-r', 'zip', '-d'] if exists
           else [KAGGLE, 'datasets', 'create', '-p', str(stage), '-r', 'zip'])
    r = run(cmd, timeout=3600)
    if r.returncode:
        raise RuntimeError('dataset upload failed: ' + (r.stdout + r.stderr)[-1500:])
    for _ in range(60):  # wait until Kaggle has processed the new version
        st = run([KAGGLE, 'datasets', 'status', f'{cfg["kaggle_owner"]}/{slug}']).stdout
        if 'ready' in st.lower():
            break
        time.sleep(20)
    return slug


def push_kernel(s, cfg, kind: str, code_file: str, sources: list[str]) -> str:
    slug = f'haven-forge-{kind}-c{s["cycle"]:03d}'
    stage = STATE_DIR / 'kaggle' / slug
    stage.mkdir(parents=True, exist_ok=True)
    shutil.copy(HERE / 'kernels' / code_file, stage / code_file)
    meta = {'id': f'{cfg["kaggle_owner"]}/{slug}', 'title': slug, 'code_file': code_file, 'language': 'python',
            'kernel_type': 'script', 'is_private': True, 'enable_gpu': True, 'enable_internet': True,
            'machine_shape': 'NvidiaTeslaT4', 'dataset_sources': [f'{cfg["kaggle_owner"]}/{x}' for x in sources],
            'kernel_sources': [], 'competition_sources': [], 'model_sources': []}
    (stage / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1))
    r = run([KAGGLE, 'kernels', 'push', '-p', str(stage)], timeout=600)
    if r.returncode or 'error' in r.stdout.lower():
        raise RuntimeError('kernel push failed: ' + (r.stdout + r.stderr)[-1500:])
    log('kernel_pushed', kernel=slug, out=r.stdout.strip()[-200:])
    return slug


def kernel_status(cfg, slug: str) -> str:
    out = run([KAGGLE, 'kernels', 'status', f'{cfg["kaggle_owner"]}/{slug}']).stdout
    for st in ('COMPLETE', 'ERROR', 'CANCEL', 'RUNNING', 'QUEUED'):
        if st in out.upper():
            return st
    return 'UNKNOWN:' + out.strip()[-120:]


def pull_kernel(cfg, slug: str, dest: pathlib.Path):
    dest.mkdir(parents=True, exist_ok=True)
    r = run([KAGGLE, 'kernels', 'output', f'{cfg["kaggle_owner"]}/{slug}', '-p', str(dest)], timeout=7200)
    if r.returncode:
        raise RuntimeError('pull failed: ' + (r.stdout + r.stderr)[-800:])


def kernel_step(s, cfg, kind, code_file, next_step, sources_fn):
    """Generic push -> wait -> pull for one Kaggle kernel; returns the next step name or the same step."""
    key = f'{kind}_kernel'
    if not s.get(key):
        sources = sources_fn()
        s[key] = {'slug': push_kernel(s, cfg, kind, code_file, sources), 'pushed': now()}
        return kind
    k = s[key]
    st = kernel_status(cfg, k['slug'])
    if st in ('RUNNING', 'QUEUED') or st.startswith('UNKNOWN'):
        age = time.time() - dt.datetime.fromisoformat(k['pushed'].replace('Z', '+00:00')).timestamp()
        if age > STALE_KERNEL_S:
            log('kernel_stale', kernel=k['slug'], status=st)
            s.pop(key)
        return kind
    dest = cdir(s) / kind
    pull_kernel(cfg, k['slug'], dest)
    receipt = json.loads((dest / 'receipt.json').read_text()) if (dest / 'receipt.json').exists() else {}
    log('kernel_finished', kernel=k['slug'], status=st, receipt_ok=receipt.get('ok'),
        stages={n: v.get('ok') for n, v in receipt.get('stages', {}).items()})
    s.pop(key)
    s.setdefault('attempts', {}).setdefault(kind, 0)
    if st != 'COMPLETE' and not any((dest).glob('traces.jsonl')) and not (dest / 'eval').exists():
        s['attempts'][kind] += 1
        if s['attempts'][kind] >= 3:
            log('kernel_gave_up', kind=kind, cycle=s['cycle'])
            return next_step if kind == 'teach' else 'next'
        return kind
    s['attempts'][kind] = 0
    return next_step


def step_teach(s, cfg):
    if cfg.get('skip_teach'):
        return 'train_mix'

    def sources():
        package(s, cfg, 'teach')
        return [f'haven-forge-c{s["cycle"]:03d}', ENGINE_DATASET]
    nxt = kernel_step(s, cfg, 'teach', 'teach_kernel.py', 'train_mix', sources)
    if nxt == 'train_mix':
        nxt = 'review_teach'
        k = cdir(s) / 'teach'
        n = s.get('teach_pass', 0)
        if (k / 'traces.jsonl').exists():
            (k / 'traces.jsonl').rename(k / f'traces-kaggle-p{n}.jsonl')
        if (k / 'critic.jsonl').exists():
            # enforce: mix drops what it rejects; advisory: its rejections are red flags for the reviewer only
            prefix = 'critic' if cfg['teacher'].get('critic_mode') == 'enforce' else 'advice-critic'
            (k / 'critic.jsonl').rename(k / f'{prefix}-kaggle-p{n}.jsonl')
        # Another pass re-teaches only rows without a trace that passes the CURRENT checks
        # (prompts and rules improve while a cycle runs).
        if n + 1 < cfg.get('teach_passes', 1):
            s['teach_pass'] = n + 1
            log('teach_pass', cycle=s['cycle'], next_pass=n + 1)
            return 'teach'
    return nxt


def step_first_mix(s, cfg):
    nxt = step_mix(s, cfg)
    start_slink_teacher(s, cfg)
    return nxt


def step_review_teach(s, cfg):
    """Hold for a reviewer's sign-off on this cycle's traces; proceed on our own after the timeout.

    The reviewer writes cycles/cNNN/review-teach.json: {"approved": true, "reviewer": "...", "drop_ids": [...],
    "notes": "..."}. drop_ids are excluded from training. Without a reviewer the loop never stalls.
    """
    req = cdir(s) / 'review-request.json'
    if not req.exists():
        r = subprocess.run([sys.executable, str(HERE / 'review.py'), '--cycle', str(cdir(s)), '--samples', '3'],
                           capture_output=True, text=True)
        (cdir(s) / 'review-summary.txt').write_text(r.stdout + r.stderr[-2000:])
        req.write_text(json.dumps({'requested': now(), 'cycle': s['cycle'], 'summary': 'review-summary.txt',
                                   'timeout_hours': cfg.get('review_timeout_hours', 6)}, indent=1))
        log('review_requested', cycle=s['cycle'], summary=str(cdir(s) / 'review-summary.txt'))
    decision = cdir(s) / 'review-teach.json'
    if decision.exists():
        d = json.loads(decision.read_text())
        log('review_decision', cycle=s['cycle'], approved=d.get('approved'), dropped=len(d.get('drop_ids', [])),
            reviewer=d.get('reviewer'))
        return 'train_mix' if d.get('approved', True) else 'teach'
    age_h = (time.time() - dt.datetime.fromisoformat(
        json.loads(req.read_text())['requested'].replace('Z', '+00:00')).timestamp()) / 3600
    if age_h >= cfg.get('review_timeout_hours', 6):
        decision.write_text(json.dumps({'approved': True, 'reviewer': 'timeout', 'drop_ids': [],
                                        'notes': f'no reviewer within {age_h:.1f} h; automatic checks only'}, indent=1))
        log('review_timeout', cycle=s['cycle'])
        return 'train_mix'
    return 'review_teach'


def step_train_mix(s, cfg):
    step_mix(s, cfg, pathlib.Path(s['data']))  # same dataset as this cycle's teacher; adds the new traces
    return 'train'


def step_train(s, cfg):
    def sources():
        package(s, cfg, 'train')
        src = [f'haven-forge-c{s["cycle"]:03d}', ENGINE_DATASET]
        if s.get('champion') and s['champion'].get('kaggle_dataset'):
            src.append(s['champion']['kaggle_dataset'])
        return src
    return kernel_step(s, cfg, 'train', 'train.py', 'gate', sources)


def items(path: pathlib.Path) -> dict:
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                out[r['id']] = r
    return out


def step_gate(s, cfg):
    ev = cdir(s) / 'train' / 'eval'
    # A registered champion must be evaluated: never silently fall back to the base.
    rival = 'champion' if s.get('champion') else 'base'
    try:
        stu, riv = verify_complete(cdir(s), rival, cycle=s['cycle'])
    except EvidenceError as exc:
        log('gate_evidence_rejected', cycle=s['cycle'], error=str(exc))
        return 'next'  # fail closed; keep the previous champion untouched
    shared = sorted(stu)
    if not shared:
        log('gate_no_results', cycle=s['cycle'])
        return 'next'
    by_key = {}
    for i in shared:
        by_key.setdefault(stu[i]['key'], []).append(stu[i]['score'] - riv[i]['score'])
    keys = list(by_key)
    diff = sum(sum(v) for v in by_key.values()) / len(shared)
    rng = random.Random(s['cycle'])
    worse = 0
    g = cfg['gate']
    for _ in range(g['bootstrap_samples']):
        pick = [by_key[rng.choice(keys)] for _ in keys]
        if sum(sum(v) for v in pick) / max(1, sum(len(v) for v in pick)) <= g['min_gain']:
            worse += 1
    p = worse / g['bootstrap_samples']

    def fpr(d):
        neg = [r for r in d.values() if r['task'] == 'detect' and r['label'] == 'not_vulnerable']
        return sum(r['false_positive'] for r in neg) / max(1, len(neg))
    fs, fr = fpr({i: stu[i] for i in shared}), fpr({i: riv[i] for i in shared})

    def recall(d):
        pos = [r for r in d.values() if r['task'] == 'detect' and r['label'] == 'vulnerable']
        return sum(r['score'] for r in pos) / max(1, len(pos))

    def paired(d):
        pairs = {}
        for r in d.values():
            if r['task'] == 'detect':
                pairs.setdefault(r['key'], []).append(r['score'])
        return sum(all(v) and len(v) == 2 for v in pairs.values()) / max(1, len(pairs))
    # Collapse guard: SFT on recorded JSON alone produced students that always answer not_vulnerable (recall 0,
    # FPR 0) and still scored above base. A student must discriminate and must pair-detect better than its rival.
    rs, rr = recall({i: stu[i] for i in shared}), recall({i: riv[i] for i in shared})
    ps, pr = paired({i: stu[i] for i in shared}), paired({i: riv[i] for i in shared})
    # Relative, not absolute: the base 4B's own recall is 0.11-0.14 on this benchmark, so a fixed 0.2 floor would call
    # the rival degenerate too (cycle 0: student recall 0.184 vs base 0.12, paired 0.138 vs 0.066). A student must not
    # detect less than its rival, must keep specificity, and must pair-detect better.
    degenerate = rs < min(0.2, rr) or (1 - fs) < 0.2 or ps <= pr
    held = [i for i in shared if i in items(ev / 'student' / 'eval-heldout' / 'items.jsonl')]
    held_diff = sum(stu[i]['score'] - riv[i]['score'] for i in held) / max(1, len(held))
    promote = (diff > g['min_gain'] and p < g['max_p_value'] and fs <= fr + g['max_fpr_increase']
               and held_diff >= -0.02 and not degenerate)
    verdict = {'cycle': s['cycle'], 'rival': rival, 'items': len(shared), 'fixes': len(keys),
               'student_score': round(sum(stu[i]['score'] for i in shared) / len(shared), 4),
               'rival_score': round(sum(riv[i]['score'] for i in shared) / len(shared), 4),
               'diff': round(diff, 4), 'p_not_better': round(p, 4), 'fpr_student': round(fs, 4),
               'fpr_rival': round(fr, 4), 'recall_student': round(rs, 4), 'recall_rival': round(rr, 4),
               'paired_student': round(ps, 4),
               'paired_rival': round(pr, 4), 'degenerate': degenerate,
               'heldout_diff': round(held_diff, 4), 'promote': promote, 't': now()}
    (cdir(s) / 'gate.json').write_text(json.dumps(verdict, indent=1))
    s['history'].append(verdict)
    log('gate', **verdict)
    return 'promote' if promote else 'next'


def step_promote(s, cfg):
    train = cdir(s) / 'train'
    gguf = next(train.glob('student-*.gguf'))
    name = f'secpatch-c{s["cycle"]:03d}'
    # 1. private HF model repo (free storage; token only needs repo write)
    tok = (HOME / '.config/haven/hf_token').read_text().strip()
    from huggingface_hub import HfApi
    api = HfApi(token=tok)
    api.create_repo(cfg['hf_repo'], private=True, exist_ok=True)
    api.upload_folder(repo_id=cfg['hf_repo'], folder_path=str(train / 'adapter'), path_in_repo=f'{name}/adapter')
    api.upload_file(repo_id=cfg['hf_repo'], path_or_fileobj=str(gguf), path_in_repo=f'{name}/{gguf.name}')
    api.upload_file(repo_id=cfg['hf_repo'], path_or_fileobj=str(cdir(s) / 'gate.json'), path_in_repo=f'{name}/gate.json')
    # 2. Kaggle dataset holding the champion GGUF, so the next cycle grades against it
    slug = 'haven-forge-champion'
    stage = STATE_DIR / 'kaggle' / slug
    shutil.rmtree(stage, ignore_errors=True); stage.mkdir(parents=True)
    shutil.copy(gguf, stage / f'champion-{cfg["quant"]}.gguf')
    (stage / 'dataset-metadata.json').write_text(json.dumps(
        {'title': slug, 'id': f'{cfg["kaggle_owner"]}/{slug}', 'licenses': [{'name': 'other'}], 'isPrivate': True}))
    exists = run([KAGGLE, 'datasets', 'status', f'{cfg["kaggle_owner"]}/{slug}']).returncode == 0
    run([KAGGLE, 'datasets', 'version' if exists else 'create', '-p', str(stage)] +
        (['-m', name] if exists else []), timeout=7200)
    # 3. register locally for Haven (the live chat model is never switched automatically)
    models = HOME / '.local/share/haven-model-lab/models'
    if models.is_dir():
        shutil.copy(gguf, models / f'Haven-{name}-{cfg["quant"]}.gguf')
    s['champion'] = {'cycle': s['cycle'], 'name': name, 'gguf': str(gguf), 'kaggle_dataset': slug,
                     'hf': f'{cfg["hf_repo"]}/{name}', 'promoted': now()}
    log('promoted', **s['champion'])
    return 'next'


def step_next(s, cfg):
    s['cycle'] += 1
    s.pop('attempts', None)
    s.pop('teach_pass', None)
    return 'refresh'


STEPS = {'refresh': step_refresh, 'mix': step_first_mix, 'teach': step_teach, 'review_teach': step_review_teach,
         'train_mix': step_train_mix,
         'train': step_train, 'gate': step_gate, 'promote': step_promote, 'next': step_next}


def tick(max_steps: int = 4):
    lock = STATE_DIR / 'loop.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if time.time() - lock.stat().st_mtime < 4 * 3600:
            return
        lock.unlink()
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        cfg = config()
        for _ in range(max_steps):
            s = load_state()
            step = s['step']
            try:
                nxt = STEPS[step](s, cfg)
            except Exception as exc:
                log('step_error', step=step, cycle=s['cycle'], error=f'{type(exc).__name__}: {str(exc)[:1500]}')
                save_state(s)
                return
            s['step'] = nxt
            save_state(s)
            if nxt == step:  # waiting on a kernel
                return
    finally:
        os.close(fd)
        lock.unlink(missing_ok=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=('tick', 'status'))
    a = ap.parse_args(argv)
    if a.cmd == 'tick':
        tick()
    else:
        print(json.dumps(load_state(), indent=1))


if __name__ == '__main__':
    main()
