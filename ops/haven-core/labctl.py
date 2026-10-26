#!/usr/bin/env python3
"""Operate the local Model Lab without printing its private bearer link."""
import argparse
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('state', 'install', 'download', 'load', 'strata', 'chat', 'job', 'cancel', 'unload', 'workers'))
    parser.add_argument('value', nargs='?')
    parser.add_argument('--wait', action='store_true')
    parser.add_argument('--timeout', type=float, default=180)
    parser.add_argument('--max-tokens', type=int, default=256)
    parser.add_argument('--context', type=int, default=4096)
    parser.add_argument('--threads', type=int, default=6)
    parser.add_argument('--provider', default='managed', help='enrolled worker id for chat, e.g. cloud-claude-code')
    parser.add_argument('--launch-file', default=str(Path.home() / '.local/state/haven-model-lab/launch-url'),
                        help='private launch file of the Lab instance to operate')
    args = parser.parse_args()
    if args.timeout <= 0 or args.timeout > 3600:
        parser.error('--timeout must be between 0 and 3600 seconds')
    if args.action in ('download', 'load', 'chat', 'job', 'cancel') and not args.value:
        parser.error('this action requires a model ID, prompt or job ID')
    link = Path(args.launch_file)
    parsed = urllib.parse.urlsplit(link.read_text().strip())
    if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.path != '/' or parsed.username or parsed.password:
        raise SystemExit('The private launch file does not name a literal loopback service.')
    token = urllib.parse.parse_qs(parsed.fragment).get('token', [''])[0]
    if not token:
        raise SystemExit('The private launch file has no session token.')
    origin = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, '', '', ''))
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(path, data=None):
        headers = {'X-Lab-Token': token}
        body = None
        if data is not None:
            body = json.dumps(data).encode()
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(origin + path, data=body, headers=headers)
        try:
            with opener.open(req, timeout=15) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                detail = json.loads(exc.read(4096))
            except (ValueError, OSError):
                detail = {'error': 'The local service rejected this request.'}
            print(json.dumps({'http_status': exc.code, **detail}, ensure_ascii=False))
            raise SystemExit(1) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise SystemExit('The local Model Lab is unavailable. Check systemctl --user status haven-model-lab. No request was retried.') from None

    actions = {
        'state': ('/api/state', None),
        'install': ('/api/engine/install', {'confirmed': True}),
        'strata': ('/api/connect/haven-strata', {}),
        'download': ('/api/model/download', {'id': args.value, 'confirmed': True}),
        'load': ('/api/engine/start', {'id': args.value, 'preset': 'balanced', 'overrides': {'context': args.context, 'threads': args.threads}}),
        'chat': ('/api/generate', {'messages': [{'role': 'user', 'content': args.value}], 'max_tokens': args.max_tokens,
                                 'temperature': 0, 'top_p': .8, 'seed': 42, 'reasoning': 'none', 'provider_id': args.provider}),
        'job': ('/api/jobs/' + urllib.parse.quote(args.value or '', safe=''), None),
        'cancel': ('/api/cancel', {'id': args.value}),
        'unload': ('/api/engine/stop', {}),
    }
    if args.action == 'workers':
        request('/api/providers/reload', {}); request('/api/providers/probe', {})
        rows = request('/api/state').get('providers', [])
        print(json.dumps([{**{k: r.get(k) for k in ('id', 'label', 'kind', 'locality', 'route_class', 'automatic')},
                           'state': r['observed']['state']} for r in rows], indent=2))
        return
    result = request(*actions[args.action])
    if args.wait and result.get('job_id'):
        job_id = result['job_id']
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            result = request('/api/jobs/' + job_id)
            if result['state'] != 'RUNNING':
                break
            time.sleep(.5)
        else:
            print(json.dumps({'job_id': job_id, 'state': 'WAIT_TIMEOUT', 'note': 'Job retained; inspect or cancel explicitly.'}))
            raise SystemExit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get('state') in ('FAILED', 'CANCELLED'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
