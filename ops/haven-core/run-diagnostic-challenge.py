#!/usr/bin/env python3
"""One actual Mac -> SSH-tunnel -> Lab -> 4B comparison, with private receipts.

No new models, server restarts, repeated prompts, automatic retries or scoring by
another model. Run once only after the peer explicitly releases the GPU and the
prepared fast 4B is ready. --retrieve-only performs GETs, never inference.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'labs/model-lab'))
from diagnostics import QUESTION


def save(path, obj):
    fd, name = tempfile.mkstemp(prefix='.challenge-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(obj, f, indent=2, sort_keys=True, allow_nan=False)
            f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-after-peer-release', action='store_true')
    parser.add_argument('--retrieve-only', action='store_true')
    args = parser.parse_args()
    if args.run_after_peer_release == args.retrieve_only:
        parser.error('Choose exactly one action.')
    os.umask(0o077)
    directory = Path.home() / '.local/state/haven-admin/diagnostic-challenge-20261026'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    manifest_path = directory / 'manifest.json'
    url = urllib.parse.urlsplit((directory.parent / 'haven-launch-url').read_text().strip())
    if url.scheme != 'http' or url.netloc != '127.0.0.1:8877' or url.path != '/':
        raise ValueError('The launcher must name the fixed private Mac tunnel.')
    token = urllib.parse.parse_qs(url.fragment)['token'][0]
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def request(path, data=None):
        headers = {'X-Lab-Token': token}
        if data is not None:
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request('http://127.0.0.1:8877' + path,
                                     data=json.dumps(data).encode() if data is not None else None, headers=headers)
        with opener.open(req, timeout=12) as response:
            return json.load(response)
    if args.retrieve_only:
        manifest = json.loads(manifest_path.read_text())
        rows = []
        for arm in manifest['arms']:
            saved = json.loads((directory / (arm['name'] + '.json')).read_text())
            retrieved = request('/api/diagnostics/' + arm['job_id'])
            rows.append({'arm': arm['name'], 'identical': saved == retrieved, 'state': retrieved['state'],
                         'job_id': arm['job_id'], 'model_requests_replayed': 0})
        save(directory / 'reconnection.json', rows)
        print(json.dumps(rows))
        return 0 if all(r['identical'] for r in rows) else 1
    if manifest_path.exists():
        raise ValueError('This comparison was already started. Retrieve its saved jobs; do not regenerate prompts.')
    state = request('/api/state')
    if state.get('prepared_runtime', {}).get('peer_busy', True) or state.get('engine', {}).get('state') != 'READY':
        raise ValueError('Explicit peer release and a ready prepared fast 4B are required.')
    manifest = {'classification': 'REAL_END_TO_END', 'began_at_epoch': time.time(),
                'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'question': QUESTION, 'question_sha256': hashlib.sha256(QUESTION.encode()).hexdigest(),
                'connection': {k: v for k, v in (state.get('connection') or {}).items() if k not in ('key', 'api_key')},
                'budget': {'arms': 2, 'tools_enabled': [False, True], 'deadline_seconds_per_arm': 180,
                           'max_calls_per_arm': 4, 'max_turns_per_arm': 5, 'automatic_retries': 0}, 'arms': []}
    save(manifest_path, manifest)
    for name, enabled in [('no_tools', False), ('real_tools', True)]:
        accepted = request('/api/diagnostics', {'question': QUESTION, 'tools_enabled': enabled, 'deadline_seconds': 180})
        arm = {'name': name, 'tools_enabled': enabled, 'job_id': accepted['job_id']}
        manifest['arms'].append(arm)
        save(manifest_path, manifest)
        deadline = time.monotonic() + 200
        while True:
            job = request('/api/diagnostics/' + arm['job_id'])
            save(directory / (name + '.json'), job)
            if job['state'] != 'RUNNING':
                break
            if time.monotonic() > deadline:
                raise TimeoutError('The job remains inspectable; no request was repeated or cancelled implicitly.')
            time.sleep(2)
        arm.update(state=job['state'], elapsed_seconds=job.get('elapsed_seconds'),
                   observed_tool_count=len(job.get('trace', [])), model_turns=len(job.get('turns', [])),
                   receipt_sha256=hashlib.sha256((directory / (name + '.json')).read_bytes()).hexdigest())
        save(manifest_path, manifest)
        print(json.dumps(arm), flush=True)
    manifest['completed_at_epoch'] = time.time()
    save(manifest_path, manifest)
    return 0 if all(a.get('state') == 'COMPLETED' for a in manifest['arms']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
