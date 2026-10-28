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
    },
    'groq': {
        'route_class': 'GROQ_FREE',
        'vendor': 'Groq',
        'allowance': 'per-organisation rate limits; exhaustion returns 429',
        'url': lambda cfg: 'https://api.groq.com/openai/v1/chat/completions',
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


def private_write(path, value):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(value)


def lane_config(lane):
    cfg = json.loads(private_read(STATE / 'lanes' / (lane + '.json')))
    if cfg.get('vendor') not in VENDORS:
        raise RelayError(500, 'Unknown relay vendor.', 'REFUSED_500')
    return cfg


def receipt(row):
    """Append an execution receipt. Never contains prompt or completion text."""
    path = STATE / 'requests.jsonl'
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with open(path, 'a') as f:
        f.write(json.dumps(row) + '\n')


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


def serve(args):
    cfg = lane_config(args.lane)
    key = private_read(STATE / 'keys' / (cfg['lane'] + '.lab'))
    target = Path(args.socket) if args.socket else STATE / 'sockets' / (cfg['lane'] + '.sock')
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.exists():
        target.unlink()

    class Server(socketserver.ThreadingUnixStreamServer):
        daemon_threads = True
        request_queue_size = 16

    old = os.umask(0o077)
    try:
        server = Server(str(target), make_handler(cfg, key))
    finally:
        os.umask(old)
    print(json.dumps({'serving': cfg['lane'], 'socket': str(target),
                      'route_class': VENDORS[cfg['vendor']]['route_class']}))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if target.exists():
            target.unlink()


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

    s = sub.add_parser('serve', help='Serve a configured lane on its private socket.')
    s.add_argument('--lane', required=True)
    s.add_argument('--socket')
    s.set_defaults(func=serve)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except RelayError as exc:
        sys.exit(str(exc))
    return 0


if __name__ == '__main__':
    sys.exit(main())
