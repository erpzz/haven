#!/usr/bin/env python3
"""Owner-run relay for metered free-allowance inference lanes.

Why a relay instead of calling the provider from the Lab: the Model Lab makes no
outbound requests and holds no provider keys. This process is the only thing that
talks to the provider, and it is reached exactly the way the Claude Code and Codex
lanes are reached -- the enrollment directory's private Unix socket. From the Lab's
side a metered lane is indistinguishable from any other enrolled worker.

What this is not: it does not enroll itself. The owner writes the enrollment file and
the key file. A model cannot create either (see labs/model-lab/providers.py).

Vendors are keyed APIs with a published free allowance. The relay refuses to retry a
429 or an allowance-exhausted response: it reports the refusal upward so the Lab shows
it, because silently retrying a rate limit is how a free allowance becomes a bill.

  metered-relay.py configure --lane cf-workers-ai --vendor cloudflare \
      --model @cf/meta/llama-3.1-8b-instruct --account-ref cf-account
  metered-relay.py serve --lane cf-workers-ai

Key material lives in <STATE>/keys/<name> (0600, owner-owned) and is read at dispatch,
never logged, never echoed into a receipt or an error body.
"""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import socket
import socketserver
import stat
import sys
import threading
import time
import urllib.error
import urllib.request
import http.server

STATE = Path(os.environ.get('HAVEN_METERED_STATE', Path.home() / '.haven' / 'metered'))

# Each vendor: how to build the upstream request and how to read its stream.
# `allowance` is descriptive only -- the authoritative remaining allowance is whatever
# the provider reports, and neither value is a licence to exceed it.
VENDORS = {
    'cloudflare': {
        'route_class': 'CLOUDFLARE_WORKERS_AI_FREE',
        'vendor': 'Cloudflare',
        'allowance': 'daily Neuron allocation; over-limit requests fail on the Workers Free plan',
        'url': lambda cfg: (f"https://api.cloudflare.com/client/v4/accounts/{cfg['account']}"
                            f"/ai/run/{cfg['model']}"),
        # Workers AI has no free listing endpoint, so verification runs the configured
        # model once with a minimal output bound. That consumes a few Neurons of the
        # daily allocation; `verify` says so before it sends.
        'probe': lambda cfg: ('POST', f"https://api.cloudflare.com/client/v4/accounts/{cfg['account']}"
                                      f"/ai/run/{cfg['model']}",
                              {'messages': [{'role': 'user', 'content': 'ping'}], 'max_tokens': 1}),
        'probe_cost': 'consumes a few Neurons of today\'s allocation',
    },
    'groq': {
        'route_class': 'GROQ_FREE',
        'vendor': 'Groq',
        'allowance': 'per-organisation rate limits; exhaustion returns 429',
        'url': lambda cfg: 'https://api.groq.com/openai/v1/chat/completions',
        # Groq lists models for free, so verification spends nothing.
        'probe': lambda cfg: ('GET', 'https://api.groq.com/openai/v1/models', None),
        'probe_cost': 'spends nothing; the model listing is not metered',
    },
}


class RelayError(Exception):
    def __init__(self, status, message, outcome):
        super().__init__(message)
        self.status, self.message, self.outcome = status, message, outcome


def private_read(path):
    """Read an owner-private file, refusing anything group/world readable."""
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as f:
        info = os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 8192 or (
                os.name != 'nt' and (info.st_uid != os.getuid() or info.st_mode & 0o077)):
            raise RelayError(500, 'Relay key material is not owner-private.', 'REFUSED_500')
        return f.read().decode().strip()


def private_directory(path):
    """Require an owner-only real directory, with no symlinked ancestors.

    The directory must be private *before* we create or replace files/sockets.
    """
    path = Path(path)
    for ancestor in (path, *path.parents):
        try:
            info = ancestor.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            raise RelayError(500, 'Relay state directory must not be a symlink.', 'REFUSED_500')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise RelayError(500, 'Relay state directory must be owner-private.', 'REFUSED_500')


def private_write(path, value):
    """Atomically replace an owner-private regular file, never following symlinks."""
    path = Path(path)
    private_directory(path.parent)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary = '.' + path.name + '.' + secrets.token_hex(12) + '.tmp'
    try:
        try:
            existing = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None and (
                not stat.S_ISREG(existing.st_mode) or existing.st_uid != os.getuid()
                or existing.st_mode & 0o077):
            raise RelayError(500, 'Existing relay file is not owner-private.', 'REFUSED_500')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory)
        with os.fdopen(fd, 'w') as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path.name, src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        try:
            os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError:
            pass
        os.close(directory)


def lane_config(lane):
    cfg = json.loads(private_read(STATE / 'lanes' / (lane + '.json')))
    if cfg.get('vendor') not in VENDORS:
        raise RelayError(500, 'Unknown relay vendor.', 'REFUSED_500')
    return cfg


def receipt(row):
    """Append a private receipt without following an attacker-planted symlink."""
    path = STATE / 'requests.jsonl'
    private_directory(path.parent)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'ab') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            raise RelayError(500, 'Relay receipt file is not owner-private.', 'REFUSED_500')
        stream.write((json.dumps(row) + '\n').encode())


def upstream_body(cfg, messages, max_tokens):
    body = {'messages': messages, 'stream': True, 'max_tokens': max_tokens}
    if cfg['vendor'] == 'groq':
        body['model'] = cfg['model']
    return body


def read_delta(vendor, payload):
    """Pull the text increment out of one SSE payload, per vendor shape."""
    if vendor == 'cloudflare':
        text = payload.get('response')
        return text if isinstance(text, str) else None
    choices = payload.get('choices') or []
    if choices and isinstance(choices[0], dict):
        text = (choices[0].get('delta') or {}).get('content')
        return text if isinstance(text, str) else None
    return None


def dispatch(cfg, messages, max_tokens, write, closed):
    """Stream one turn from the provider, translating to OpenAI chunks.

    A 429 or allowance refusal is reported, not retried. Retrying an exhausted
    allowance is what turns a free tier into an invoice.
    """
    spec = VENDORS[cfg['vendor']]
    key = private_read(STATE / 'keys' / cfg['key_ref'])
    request = urllib.request.Request(
        spec['url'](cfg),
        data=json.dumps(upstream_body(cfg, messages, max_tokens)).encode(),
        headers={'authorization': 'Bearer ' + key, 'content-type': 'application/json',
                 'accept': 'text/event-stream'},
        method='POST')
    began = time.monotonic()
    sent = 0
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            allowance = {k.lower(): v for k, v in response.headers.items()
                         if k.lower().startswith('x-ratelimit')}
            for raw in response:
                if closed():
                    raise RelayError(499, 'Client closed the stream.', 'CLIENT_CLOSED')
                line = raw.decode('utf-8', 'replace').strip()
                if not line.startswith('data:'):
                    continue
                chunk = line[5:].strip()
                if chunk == '[DONE]':
                    break
                try:
                    payload = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                delta = read_delta(cfg['vendor'], payload)
                if delta:
                    sent += len(delta)
                    write(delta)
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode('utf-8', 'replace')
        if exc.code == 429:
            raise RelayError(429, 'The provider rate-limited this lane; its free allowance may be '
                                  'exhausted. Nothing was retried.', 'REFUSED_429') from exc
        if exc.code in (402, 403):
            raise RelayError(402, 'The provider refused this request as outside the free allowance '
                                  'or not permitted on this plan. Nothing was retried.', 'REFUSED_402') from exc
        if exc.code in (401,):
            raise RelayError(401, 'The provider rejected the lane credential.', 'REFUSED_401') from exc
        raise RelayError(502, f'The provider returned {exc.code}. Detail withheld from the stream.',
                         'REFUSED_502') from exc
    except urllib.error.URLError as exc:
        raise RelayError(504, f'The provider was unreachable: {exc.reason}', 'REFUSED_504') from exc
    receipt({'at': time.time(), 'lane': cfg['lane'], 'route_class': spec['route_class'],
             'cost_boundary': cfg.get('cost_boundary'), 'outcome': 'COMPLETED',
             'characters': sent, 'elapsed_ms': round((time.monotonic() - began) * 1000, 3),
             'allowance_headers': allowance})


def make_handler(cfg, key):
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass  # Request lines can carry no useful detail and may carry prompt length.

        def reply(self, status, body):
            raw = json.dumps(body).encode()
            self.send_response(status)
            self.send_header('content-type', 'application/json')
            self.send_header('content-length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def authorized(self):
            return self.headers.get('Authorization') == 'Bearer ' + key

        def do_GET(self):
            if not self.authorized():
                return self.reply(401, {'error': {'message': 'unauthorized'}})
            if self.path != '/v1/models':
                return self.reply(404, {'error': {'message': 'not found'}})
            spec = VENDORS[cfg['vendor']]
            self.reply(200, {'object': 'list', 'data': [{
                'id': cfg['model'], 'object': 'model', 'owned_by': spec['vendor'],
                'haven_allowance': spec['allowance'],
                'haven_cost_boundary': cfg.get('cost_boundary')}]})

        def do_POST(self):
            if not self.authorized():
                return self.reply(401, {'error': {'message': 'unauthorized'}})
            if self.path != '/v1/chat/completions':
                return self.reply(404, {'error': {'message': 'not found'}})
            try:
                length = int(self.headers.get('content-length') or 0)
            except ValueError:
                return self.reply(400, {'error': {'message': 'bad length'}})
            if not 0 < length <= 1048576:
                return self.reply(400, {'error': {'message': 'bad length'}})
            try:
                body = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return self.reply(400, {'error': {'message': 'bad json'}})
            if body.get('stream') is not True:
                return self.reply(400, {'error': {'message': 'this lane streams only'}})
            if body.get('model') != cfg['model']:
                return self.reply(404, {'error': {'message': 'unknown model for this lane'}})
            messages = body.get('messages')
            if (not isinstance(messages, list) or not messages
                    or not all(isinstance(m, dict) and isinstance(m.get('content'), str)
                               and m.get('role') in ('system', 'user', 'assistant') for m in messages)
                    or messages[0]['role'] == 'assistant'):
                return self.reply(400, {'error': {'message': 'bad messages'}})
            max_tokens = body.get('max_tokens')
            if type(max_tokens) is not int or not 1 <= max_tokens <= 2048:
                return self.reply(400, {'error': {'message': 'bad max_tokens'}})

            cid = 'chatcmpl-' + os.urandom(8).hex()
            self.send_response(200)
            self.send_header('content-type', 'text/event-stream')
            self.send_header('cache-control', 'no-store')
            # An event stream has no content length. Close on completion so the client
            # reads to EOF instead of waiting on a keep-alive that will never be reused.
            self.send_header('connection', 'close')
            self.end_headers()
            self.close_connection = True
            closed = {'v': False}

            def send(obj):
                try:
                    self.wfile.write(('data: ' + json.dumps(obj) + '\n\n').encode())
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    closed['v'] = True
                    raise

            def write(delta):
                send({'id': cid, 'object': 'chat.completion.chunk', 'model': cfg['model'],
                      'choices': [{'index': 0, 'delta': {'content': delta}, 'finish_reason': None}]})

            try:
                dispatch(cfg, messages, max_tokens, write, lambda: closed['v'])
                send({'id': cid, 'object': 'chat.completion.chunk', 'model': cfg['model'],
                      'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})
                self.wfile.write(b'data: [DONE]\n\n')
                self.wfile.flush()
            except RelayError as exc:
                receipt({'at': time.time(), 'lane': cfg['lane'], 'outcome': exc.outcome,
                         'reason': exc.message})
                if not closed['v']:
                    try:
                        send({'id': cid, 'object': 'chat.completion.chunk', 'model': cfg['model'],
                              'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'error'}],
                              'haven_error': exc.message})
                        self.wfile.write(b'data: [DONE]\n\n')
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        pass
            except (BrokenPipeError, ConnectionResetError):
                receipt({'at': time.time(), 'lane': cfg['lane'], 'outcome': 'CLIENT_CLOSED'})

    return Handler


def configure(args):
    spec = VENDORS[args.vendor]
    if not re.fullmatch(r'[a-z][a-z0-9-]{2,47}', args.lane):
        sys.exit('Lane identifier must be lowercase, 3-48 characters.')
    cfg = {'lane': args.lane, 'vendor': args.vendor, 'model': args.model,
           'key_ref': args.key_ref or args.lane, 'cost_boundary': args.cost_boundary}
    if args.vendor == 'cloudflare':
        if not args.account_ref:
            sys.exit('Cloudflare needs --account-ref naming the private file holding the account id.')
        cfg['account'] = private_read(STATE / 'keys' / args.account_ref)
    private_write(STATE / 'lanes' / (args.lane + '.json'), json.dumps(cfg, indent=2))
    print(json.dumps({'configured': args.lane, 'vendor': spec['vendor'],
                      'route_class': spec['route_class'], 'cost_boundary': cfg['cost_boundary'],
                      'note': 'Configuration is not enrollment. Write the Lab enrollment file yourself.'}, indent=2))


def verify(args):
    """One deliberate, owner-run authenticated call. Produces a real receipt.

    This is the step a model cannot do for you: it needs your provider credential.
    It is explicitly not part of serve() and never runs unattended -- its whole
    purpose is that a human chose to spend one request to confirm the lane works.
    """
    cfg = lane_config(args.lane)
    spec = VENDORS[cfg['vendor']]
    method, url, body = spec['probe'](cfg)
    if not args.yes:
        print(f"About to make one authenticated {method} to {spec['vendor']} for lane "
              f"{cfg['lane']!r}. This {spec['probe_cost']}.", file=sys.stderr)
        if input('Proceed? [y/N] ').strip().lower() not in ('y', 'yes'):
            sys.exit('Nothing was sent.')
    key = private_read(STATE / 'keys' / cfg['key_ref'])
    request = urllib.request.Request(
        url, data=json.dumps(body).encode() if body is not None else None,
        headers={'authorization': 'Bearer ' + key,
                 **({'content-type': 'application/json'} if body is not None else {})},
        method=method)
    began = time.monotonic()
    result = {'at': time.time(), 'lane': cfg['lane'], 'route_class': spec['route_class'],
              'cost_boundary': cfg.get('cost_boundary'), 'vendor': spec['vendor'],
              'authenticated': True, 'simulated': False}
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read(65536).decode('utf-8', 'replace')
            result.update(outcome='VERIFIED', http_status=response.status,
                          allowance_headers={k.lower(): v for k, v in response.headers.items()
                                             if k.lower().startswith(('x-ratelimit', 'cf-'))},
                          # Bounded excerpt proving a real response arrived; never the key.
                          response_bytes=len(payload))
    except urllib.error.HTTPError as exc:
        detail = exc.read(512).decode('utf-8', 'replace')
        result.update(outcome=f'REFUSED_{exc.code}', http_status=exc.code,
                      reason={429: 'rate-limited or allowance exhausted',
                              402: 'outside the free allowance',
                              403: 'not permitted on this plan',
                              401: 'credential rejected'}.get(exc.code, 'provider error'),
                      detail=detail[:200])
    except urllib.error.URLError as exc:
        result.update(outcome='UNREACHABLE', reason=str(exc.reason))
    result['elapsed_ms'] = round((time.monotonic() - began) * 1000, 3)
    if key in json.dumps(result):  # Defensive: a receipt must never carry the credential.
        sys.exit('Refusing to write a receipt that contains the credential.')
    receipt(result)
    print(json.dumps(result, indent=2))
    return 0 if result['outcome'] == 'VERIFIED' else 1


def remove_owned_socket(target, expected):
    """Never unlink a path replaced by another process after our inode check."""
    try:
        current = target.lstat()
    except FileNotFoundError:
        return
    if (not stat.S_ISSOCK(current.st_mode) or current.st_uid != os.getuid()
            or (current.st_dev, current.st_ino) != (expected.st_dev, expected.st_ino)):
        raise RelayError(500, 'Socket path changed ownership or identity.', 'REFUSED_500')
    target.unlink()


def prepare_socket(target):
    """Refuse live/foreign sockets; clean only an owner-owned, provably stale one."""
    target = Path(target)
    private_directory(target.parent)
    try:
        current = target.lstat()
    except FileNotFoundError:
        return
    if (not stat.S_ISSOCK(current.st_mode) or current.st_uid != os.getuid()
            or current.st_mode & 0o077):
        raise RelayError(409, 'Socket path is not an owner-private Unix socket.', 'REFUSED_409')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.3)
        try:
            probe.connect(str(target))
        except ConnectionRefusedError:
            remove_owned_socket(target, current)
            return
        except OSError as exc:
            raise RelayError(409, 'Cannot prove existing Unix socket is stale.', 'REFUSED_409') from exc
    raise RelayError(409, 'A relay is already listening on this Unix socket.', 'REFUSED_409')


class MeteredUnixServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    request_queue_size = 16
    max_active_requests = 4

    def __init__(self, *args, **kwargs):
        self._slots = threading.BoundedSemaphore(self.max_active_requests)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


def serve(args):
    cfg = lane_config(args.lane)
    key = private_read(STATE / 'keys' / (cfg['lane'] + '.lab'))
    target = Path(args.socket) if args.socket else STATE / 'sockets' / (cfg['lane'] + '.sock')
    prepare_socket(target)
    old = os.umask(0o077)
    try:
        server = MeteredUnixServer(str(target), make_handler(cfg, key))
    finally:
        os.umask(old)
    bound = target.lstat()
    print(json.dumps({'serving': cfg['lane'], 'socket': str(target),
                      'route_class': VENDORS[cfg['vendor']]['route_class']}))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        remove_owned_socket(target, bound)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)

    c = sub.add_parser('configure', help='Record a lane. Does not enroll it with the Lab.')
    c.add_argument('--lane', required=True)
    c.add_argument('--vendor', required=True, choices=sorted(VENDORS))
    c.add_argument('--model', required=True)
    c.add_argument('--key-ref', dest='key_ref')
    c.add_argument('--account-ref', dest='account_ref')
    c.add_argument('--cost-boundary', dest='cost_boundary', required=True,
                   choices=['NOT_CHARGEABLE', 'PROVIDER_HARD_LIMIT', 'PROVIDER_SOFT_ALERT', 'CLIENT_SIDE_ONLY'])
    c.set_defaults(func=configure)

    v = sub.add_parser('verify', help='Make one authenticated call and write a real receipt.')
    v.add_argument('--lane', required=True)
    v.add_argument('--yes', action='store_true', help='Skip the spend confirmation prompt.')
    v.set_defaults(func=verify)

    s = sub.add_parser('serve', help='Serve a configured lane on its private socket.')
    s.add_argument('--lane', required=True)
    s.add_argument('--socket')
    s.set_defaults(func=serve)

    args = parser.parse_args(argv)
    try:
        return args.func(args) or 0
    except RelayError as exc:
        sys.exit(str(exc))


if __name__ == '__main__':
    sys.exit(main())
