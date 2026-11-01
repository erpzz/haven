"""Hourly off-box backup of everything the forge produced that would be costly to recreate.

Slink's state lives on one USB disk. This mirrors it into one private Hugging Face dataset repo:
- forge state: cycle data, teacher traces and critic files, reviews, training receipts, adapters, evals, trained
  student GGUFs, benchmark tables, and the loop's state and logs;
- secpatch's harvested datasets and earlier runs.
Only files that changed since the last successful upload are sent. Nothing is ever deleted remotely, so a file lost
or overwritten on Slink stays recoverable from the repo history. Re-downloadable inputs are skipped: stock models,
staged Kaggle copies, git clones, and code that lives in git.

One-off Kaggle kernels named in the config (`backup.kaggle_pull`) are pulled into runs/<slug>/<run time>/ as soon as
they finish. Their output then reaches Slink, and the backup, without anyone watching.

  backup.py run        pull finished one-off kernels, then upload what changed
  backup.py plan       list what would be uploaded, upload nothing

Restore: hf download <repo> --repo-type dataset --local-dir <dir>   (forge state under forge/, datasets under secpatch/)
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import io
import json
import pathlib
import sys
import time

import loop

BACKUP_DIR = loop.HOME / '.local/state/haven-forge-backup'
MANIFEST = BACKUP_DIR / 'manifest.json'
LOG = BACKUP_DIR / 'backup.jsonl'
SETTLE_S = 300  # a file modified this recently may still be being written; it goes in the next run
SOURCES = [  # (local root, path prefix in the repo, top-level entries to include)
    (loop.STATE_DIR, 'forge/', ['state.json', 'config.override.json', 'logs', 'bench', 'cycles', 'runs', 'agent']),
    (loop.SECPATCH_STATE, 'secpatch/', ['adapters', 'baseline', 'candidates.jsonl', 'data', 'data-*', 'eval',
                                        'eval-regraded', 'fresh', 'harvest*.jsonl', 'raw', 'runs', 'scope.jsonl', '*.sh']),
]
EXCLUDE = ['*/merged/*', '*/ckpt/*', '*/checkpoints/*', '*/checkpoint-*/*', '*-f16.gguf', '*/__pycache__/*', '*.lock', '*.part', '*.tmp', '*/.cache/*']
SECRET_LIKE = ['*token*', '*secret*', '*credential*', '*.key', '*.pem', '.env', '*.env', '*password*']
BATCH_FILES, BATCH_BYTES = 400, 4 * 2**30


def record(event: str, **kw):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    rec = {'t': loop.now(), 'event': event, **kw}
    with LOG.open('a') as f:
        f.write(json.dumps(rec, default=str) + '\n')
    print(json.dumps(rec, default=str), flush=True)


def candidates(root: pathlib.Path, prefix: str, entries: list[str], now: float, fresh_ok=frozenset(), skipped=None):
    """(repo path, local path, size, mtime_ns) for each settled, non-excluded, non-secret file under the entries."""
    if not root.is_dir():
        return
    for top in sorted(root.iterdir()):
        if not any(fnmatch.fnmatch(top.name, e) for e in entries):
            continue
        for p in ([top] if top.is_file() else sorted(top.rglob('*'))):
            if p.is_symlink() or not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            if any(fnmatch.fnmatch(rel, g) for g in EXCLUDE):
                continue
            if any(fnmatch.fnmatch(p.name.lower(), g) for g in SECRET_LIKE):
                if skipped is not None:
                    skipped.append(prefix + rel)
                continue
            st = p.stat()
            if now - st.st_mtime < SETTLE_S and not any(p.is_relative_to(d) for d in fresh_ok):
                continue
            yield prefix + rel, p, st.st_size, st.st_mtime_ns


def changed(files, manifest: dict) -> list:
    return [f for f in files if manifest.get(f[0]) != [f[2], f[3]]]


def batches(files):
    out, n = [], 0
    for f in files:
        if out and (len(out) >= BATCH_FILES or n + f[2] > BATCH_BYTES):
            yield out
            out, n = [], 0
        out.append(f); n += f[2]
    if out:
        yield out


def pull_finished(cfg: dict) -> list[pathlib.Path]:
    """Pull each listed one-off kernel's latest finished run (COMPLETE or ERROR) once; returns the new run dirs."""
    slugs = cfg.get('backup', {}).get('kaggle_pull', [])
    if not slugs:
        return []
    owner = cfg['kaggle_owner']
    listing = loop.run([loop.KAGGLE, 'kernels', 'list', '--mine', '--csv', '--page-size', '100'], timeout=300)
    runs = {r['ref']: r['lastRunTime'] for r in csv.DictReader(io.StringIO(listing.stdout)) if 'ref' in r}
    new = []
    for slug in slugs:
        ref = f'{owner}/{slug}'
        if ref not in runs:
            continue
        status = loop.run([loop.KAGGLE, 'kernels', 'status', ref], timeout=120).stdout.upper()
        if 'COMPLETE' not in status and 'ERROR' not in status:
            continue
        dest = loop.STATE_DIR / 'runs' / slug / runs[ref].replace(' ', 'T').replace(':', '')[:17]
        if (dest / '.pulled').exists():
            continue
        dest.mkdir(parents=True, exist_ok=True)
        r = loop.run([loop.KAGGLE, 'kernels', 'output', ref, '-p', str(dest)], timeout=7200)
        if r.returncode:
            record('pull_failed', kernel=ref, out=(r.stdout + r.stderr)[-400:])
            continue
        (dest / '.pulled').write_text(loop.now() + '\n')
        record('pulled', kernel=ref, run=runs[ref], dest=str(dest), status=status.strip()[-40:])
        new.append(dest)
    return new


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=['run', 'plan'])
    args = ap.parse_args(argv)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    cfg = loop.config()
    repo = cfg['backup']['hf_repo']
    fresh = pull_finished(cfg) if args.action == 'run' else []
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    t, secret_like = time.time(), []
    todo = changed([f for root, prefix, entries in SOURCES
                    for f in candidates(root, prefix, entries, t, frozenset(fresh), secret_like)], manifest)
    if secret_like:
        record('skipped_secret_like', paths=secret_like[:20], n=len(secret_like))
    if args.action == 'plan':
        for f in todo:
            print(f'{f[2]:>12} {f[0]}')
        print(f'{len(todo)} files, {sum(f[2] for f in todo) / 1e9:.2f} GB')
        return
    if not todo:
        record('up_to_date', files=len(manifest))
        return
    from huggingface_hub import CommitOperationAdd, HfApi
    api = HfApi(token=(loop.HOME / '.config/haven/hf_token').read_text().strip())
    api.create_repo(repo, repo_type='dataset', private=True, exist_ok=True)
    if not api.repo_info(repo, repo_type='dataset').private:
        record('refused_public_repo', repo=repo)
        sys.exit(f'{repo} is public: refusing to upload')
    sent = 0
    for batch in batches(todo):
        api.create_commit(repo, repo_type='dataset', commit_message=f'backup {loop.now()}: {len(batch)} files',
                          operations=[CommitOperationAdd(path_in_repo=f[0], path_or_fileobj=str(f[1])) for f in batch])
        for f in batch:
            manifest[f[0]] = [f[2], f[3]]
        tmp = MANIFEST.with_suffix('.tmp')
        tmp.write_text(json.dumps(manifest))
        tmp.replace(MANIFEST)  # progress survives an interrupted run
        sent += sum(f[2] for f in batch)
    record('uploaded', repo=repo, files=len(todo), gb=round(sent / 1e9, 3), seconds=round(time.time() - t, 1))


if __name__ == '__main__':
    main()
