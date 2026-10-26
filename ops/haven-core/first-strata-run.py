#!/usr/bin/env python3
"""One bounded, real Strata response, then restore the fast GGUF workspace.

Run only after the separate model preparation succeeded. No installs, downloads,
training, cloud calls, retries of generation or public listeners are created.
All detailed results stay in a new private receipt.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parent
HOME = Path.home()
STATE = HOME / '.local/state/haven-strata'
DATA = HOME / '.local/share/haven-strata'
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(url, headers, data=None):
    body = None if data is None else json.dumps(data).encode()
    with OPENER.open(urllib.request.Request(url, data=body, headers=headers), timeout=10) as response:
        return json.load(response)


def lab_request(path, data=None):
    link = urllib.parse.urlsplit((HOME / '.local/state/haven-model-lab/launch-url').read_text().strip())
    if link.scheme != 'http' or link.netloc != '127.0.0.1:8877':
        raise RuntimeError('Unexpected private Lab endpoint.')
    token = urllib.parse.parse_qs(link.fragment)['token'][0]
    return request('http://127.0.0.1:8877' + path,
                   {'X-Lab-Token': token, 'Content-Type': 'application/json'}, data)


def control(*args):
    result = subprocess.run(['/usr/bin/python3', str(ROOT / 'labctl.py'), *args],
                            capture_output=True, text=True, timeout=400)
    if result.returncode:
        raise RuntimeError('Lab action failed: ' + result.stdout[:600])
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        print('DRY RUN: verify prepared pins/profile; start authenticated loopback Strata; '
              'send one short request; disconnect; stop Strata; restore the existing 4B model.')
        return
    os.umask(0o077)
    report_dir = HOME / '.local/state/haven-admin'
    report_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    receipt = report_dir / ('strata-first-response-' + stamp + '.json')
    if receipt.exists():
        raise SystemExit('Refusing to overwrite an existing receipt.')
    report = {'status': 'RUNNING', 'started_at': stamp, 'phase': 'PREPARATION',
              'scope': 'One short synthetic prompt; no general model qualification.'}
    started = False
    attached = False

    def save(phase):
        report['phase'] = phase
        temporary = receipt.with_suffix('.tmp')
        temporary.write_text(json.dumps(report, indent=2) + '\n')
        temporary.replace(receipt)
        print('Haven first Strata run:', phase, flush=True)

    save('VERIFY_PREPARED_FILES')
    try:
        native = DATA / 'install/strata-iq2_xs.json'
        config = json.loads(native.read_text())
        pins = json.loads((ROOT / 'strata-linux-pins.json').read_text())
        for pin in pins['model']:
            name = urllib.parse.urlsplit(pin['url']).path.rsplit('/', 1)[-1]
            model = DATA / 'data/models/IQ2_XS' / name
            mark = model.with_name(name + '.done')
            if model.stat().st_size != pin['size_bytes'] or ('sha256 ' + pin['sha256']) not in mark.read_text():
                raise RuntimeError('The preparer has not verified the pinned model bytes.')
        if config.get('exe') != 'component:strata-engine' or any(
                config.get(key) for key in ('vision', 'images', 'mcp_servers', 'before_load', 'api_key')):
            raise RuntimeError('Review the native config; the initial text-only service contract was not met.')
        state = lab_request('/api/state')
        if state['connection'] or any(job['state'] == 'RUNNING' for job in state['jobs']):
            raise RuntimeError('The Lab is in use. Its current work was preserved.')
        STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
        (STATE / 'run-profile.json').write_text(json.dumps(config, indent=2) + '\n')
        save('START_STRATA')
        subprocess.run(['systemctl', '--user', 'start', 'haven-strata'], check=True, timeout=30)
        started = True
        save('WAIT_FOR_AUTHENTICATED_API')
        deadline = time.monotonic() + 1200
        attempts = 0
        while time.monotonic() < deadline:
            if subprocess.run(['systemctl', '--user', 'is-active', '--quiet', 'haven-strata']).returncode:
                raise RuntimeError('The Strata service exited; inspect its retained journal.')
            try:
                key = (STATE / 'api-key').read_text().strip()
                models = request('http://127.0.0.1:8880/v1/models', {'Authorization': 'Bearer ' + key})
                if models.get('data'):
                    break
            except urllib.error.HTTPError as error:
                if error.code in (401, 403):
                    raise RuntimeError('The native API rejected its private credential.') from None
                if error.code != 503:
                    raise RuntimeError('Unexpected native API readiness status: ' + str(error.code)) from None
            except (OSError, ValueError, urllib.error.URLError):
                pass
            attempts += 1
            time.sleep(min(30, 2 * attempts))
        else:
            raise TimeoutError('Strata did not become ready within twenty minutes.')
        save('CHECK_API_AUTHENTICATION')
        try:
            request('http://127.0.0.1:8880/v1/chat/completions', {'Content-Type': 'application/json'},
                    {'model': models['data'][0]['id'], 'messages': [{'role': 'user', 'content': 'Reply READY.'}],
                     'max_tokens': 16, 'stream': False})
        except urllib.error.HTTPError as error:
            if error.code not in (401, 403):
                raise RuntimeError('Unexpected unauthenticated API status.') from None
            report['unauthenticated_chat_status'] = error.code
        else:
            raise RuntimeError('Unauthenticated chat was accepted; do not use this service.')
        save('ATTACH_AND_GENERATE')
        report['connection'] = control('strata')
        attached = True
        report['generation'] = control('chat', 'Introduce Haven Core as a local assistant in one short sentence.',
                                       '--max-tokens', '48', '--wait', '--timeout', '300')
        if not report['generation'].get('text', '').strip():
            raise RuntimeError('The generation completed without a visible answer.')
        save('CHECK_EXTERNAL_OWNERSHIP')
        report['disconnect'] = lab_request('/api/disconnect', {})
        attached = False
        report['external_service_after_disconnect'] = subprocess.run(
            ['systemctl', '--user', 'is-active', '--quiet', 'haven-strata']).returncode == 0
        if not report['external_service_after_disconnect']:
            raise RuntimeError('The external service did not remain active after disconnect.')
        report['response_status'] = 'COMPLETED'
    except Exception as error:
        report['status'] = 'FAILED'
        report['error'] = type(error).__name__ + ': ' + str(error)[:700]
    finally:
        if started:
            if attached:
                try:
                    lab_request('/api/disconnect', {})
                except Exception:
                    pass
            save('STOP_OWNED_STRATA_SERVICE')
            subprocess.run(['systemctl', '--user', 'stop', 'haven-strata'], timeout=35, check=False)
            try:
                report['fast_model_restore'] = control('load', 'qwen35-4b', '--wait', '--timeout', '180')
            except Exception as error:
                report['restore_error'] = str(error)[:700]
        if report.get('response_status') == 'COMPLETED':
            report['status'] = 'FAILED' if report.get('restore_error') else 'COMPLETED'
        save('FINISHED')
    return 0 if report['status'] == 'COMPLETED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
