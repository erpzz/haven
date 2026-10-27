#!/usr/bin/env python3
"""Choose and check Slink's Model Lab model from the Mac, without building SSH commands by hand.

  slink-lab status            what is loaded, Strata, jobs, workers
  slink-lab models            downloaded models and their ids
  slink-lab use qwen36-35b-a3b
  slink-lab use qwen35-4b --switch     unload the current Lab model first
  slink-lab unload | strata

Every action runs the deployed labctl.py on Slink over the owner's pinned SSH host `haven`; the Lab's bearer
link never leaves Slink. `use` is idempotent: the model already READY is left alone, a load already STARTING is
followed rather than requested again, and nothing is unloaded or disconnected unless --switch is given.
It never stops or starts the Strata service.
"""
import argparse
import json
import shlex
import subprocess
import sys
import time

SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', 'haven']
LABCTL = 'python3 projects/haven/ops/haven-core/labctl.py'


class LabError(RuntimeError):
    pass


def labctl(*args, check=True):
    proc = subprocess.run([*SSH, LABCTL + ' ' + ' '.join(shlex.quote(a) for a in args)],
                          capture_output=True, text=True, timeout=60)
    out = proc.stdout.strip()
    try:
        data = json.loads(out) if out else {}
    except ValueError:
        data = {'error': out[-400:] or proc.stderr.strip()[-400:]}
    if check and proc.returncode:
        data = data if isinstance(data, dict) else {}
        raise LabError(data.get('error') or proc.stderr.strip()[-400:] or 'labctl failed on Slink')
    return data


def loaded_model(state):
    """Catalog id of the Lab-owned engine, matched by its --model file, or None."""
    argv = (state.get('engine') or {}).get('argv') or []
    path = argv[argv.index('--model') + 1] if '--model' in argv else ''
    for m in state.get('models') or []:
        if m.get('filename') and path.endswith('/' + m['filename']):
            return m['id']
    return None


def describe(state):
    eng, conn = state.get('engine') or {}, state.get('connection') or {}
    runtime = state.get('prepared_runtime') or {}
    if conn.get('ownership') == 'EXTERNAL':
        backend = {'state': 'EXTERNAL_CONNECTED', 'model': conn.get('model'), 'kind': conn.get('kind')}
    elif eng.get('ownership') == 'OWNED':
        backend = {'state': eng.get('state'), 'model': loaded_model(state), 'label': eng.get('label'),
                   'compute': eng.get('compute'), 'since': eng.get('started_at')}
    else:
        backend = {'state': 'NONE'}
    running = [{'id': j['id'], 'kind': j['kind']} for j in state.get('jobs') or [] if j.get('state') == 'RUNNING']
    return {'backend': backend, 'strata_service': runtime.get('strata_state'), 'running_jobs': running}


def status(_):
    state = labctl('state')
    print(json.dumps(describe(state), indent=1))
    workers = labctl('workers')
    print(json.dumps({w['id']: w['state'] for w in workers}, indent=1))


def models(_):
    for m in labctl('state').get('models') or []:
        if m.get('downloaded'):
            print(f"{m['id']:<20} {m.get('name', '')}  ({m.get('download_gb', '?')} GB)")


def wait_ready(model, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = labctl('state')
        backend = describe(state)['backend']
        if backend['state'] == 'READY' and backend.get('model') == model:
            return backend
        failed = [j for j in state.get('jobs') or [] if j.get('kind') == 'engine-start' and j.get('state') in ('FAILED', 'CANCELLED')
                  and j.get('created_at', 0) >= (backend.get('since') or 0) - 5]
        if backend['state'] in ('PROCESS_EXITED', 'STOPPED', 'NONE') or failed:
            raise LabError(f"load of {model} did not complete: engine {backend['state']}"
                           + (f"; job {failed[0]['state']}: {failed[0].get('error', '')}" if failed else ''))
        print(f"  {backend['state']} {model} … {int(time.monotonic() - deadline + timeout)} s", file=sys.stderr, flush=True)
        time.sleep(10)
    raise LabError(f'{model} is still starting after {timeout} s; the load continues on Slink. Run the same command again to keep following it.')


def use(args):
    state = labctl('state')
    known = {m['id'] for m in state.get('models') or [] if m.get('downloaded')}
    if args.model not in known:
        raise LabError(f'{args.model} is not a downloaded model on Slink. See: slink-lab models')
    backend = describe(state)['backend']
    if backend.get('model') == args.model and backend['state'] == 'READY':
        print(json.dumps({'result': 'ALREADY_READY', **backend}, indent=1))
        return
    if backend.get('model') == args.model and backend['state'] == 'STARTING':
        print(f'{args.model} is already starting; following it.', file=sys.stderr)
        print(json.dumps({'result': 'READY', **wait_ready(args.model, args.timeout)}, indent=1))
        return
    if backend['state'] == 'EXTERNAL_CONNECTED':
        if not args.switch:
            raise LabError(f"An external backend ({backend.get('kind')}: {backend.get('model')}) is connected. "
                           'Re-run with --switch to disconnect it (its service keeps running and keeps its GPU memory; '
                           'stop haven-strata yourself first if the new model needs the GPU).')
        labctl('disconnect')
    elif backend['state'] not in ('NONE', 'STOPPED'):
        if not args.switch:
            raise LabError(f"The Lab has {backend.get('model') or backend.get('label')} {backend['state']}. "
                           'Re-run with --switch to unload it and load the new model.')
        labctl('unload')
    started = labctl('load', args.model, '--context', str(args.context))
    print(f"loading {args.model} (job {started.get('job_id')})", file=sys.stderr, flush=True)
    print(json.dumps({'result': 'READY', **wait_ready(args.model, args.timeout)}, indent=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('status'); sub.add_parser('models'); sub.add_parser('unload'); sub.add_parser('strata')
    u = sub.add_parser('use')
    u.add_argument('model')
    u.add_argument('--switch', action='store_true', help='unload or disconnect the current backend first')
    u.add_argument('--context', type=int, default=4096)
    u.add_argument('--timeout', type=int, default=1800, help='seconds to follow a cold load (the 35B took 344 s)')
    args = parser.parse_args()
    try:
        if args.action in ('unload', 'strata'):
            print(json.dumps(labctl(args.action), indent=1))
        else:
            {'status': status, 'models': models, 'use': use}[args.action](args)
    except (LabError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f'slink-lab: {exc}')


if __name__ == '__main__':
    main()
