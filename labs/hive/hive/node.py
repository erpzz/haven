"""Authenticated, loopback-only transformer layer worker."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time

import torch

from .model import Segment, Spec
from .wire import HEADER, MAX_BODY, decode, encode, secret_matches


class HiveServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, spec: Spec, start: int, stop: int, secret: str, device='cpu'):
        if address[0] not in ('127.0.0.1', '::1'):
            raise ValueError('HIVE never binds to a LAN or public address; use SSH forwarding.')
        self.spec, self.start, self.stop, self.secret = spec, start, stop, secret
        self.segment = Segment(spec, start, stop, device=device)
        self.device = device
        self.compute_lock = threading.Lock()
        self.completed = 0
        super().__init__(address, HiveHandler)

    def metadata(self):
        return {'protocol': 1, 'model_id': self.spec.identity, 'start': self.start,
                'stop': self.stop, 'device': self.device, 'dtype': 'float32',
                'max_context': self.spec.context, 'completed_forwards': self.completed}


class HiveHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *_):
        pass  # No prompt, activation, URL, credential or network-log retention.

    def send_json(self, code, obj):
        body = json.dumps(obj, separators=(',', ':'), allow_nan=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def authorized(self):
        if not secret_matches(self.server.secret, self.headers.get(HEADER, '')):
            self.send_json(403, {'error': 'Access denied'})
            return False
        if self.client_address[0] not in ('127.0.0.1', '::1'):
            self.send_json(403, {'error': 'Loopback only'})
            return False
        if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}', f'[::1]:{self.server.server_port}'):
            self.send_json(403, {'error': 'Invalid host'})
            return False
        return True

    def do_GET(self):
        if not self.authorized():
            return
        if self.path == '/meta':
            self.send_json(200, self.server.metadata())
        else:
            self.send_json(404, {'error': 'Not found'})

    def do_POST(self):
        if not self.authorized():
            return
        if self.path != '/forward':
            self.send_json(404, {'error': 'Not found'})
            return
        try:
            if self.headers.get('Transfer-Encoding'):
                raise ValueError('Transfer encoding not supported.')
            size = int(self.headers.get('Content-Length', '0'))
            if not (0 < size <= MAX_BODY):
                raise ValueError('Request too large or empty.')
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict) or payload.get('model_id') != self.server.spec.identity:
                raise ValueError('Model identity mismatch.')
            if payload.get('start') != self.server.start or payload.get('stop') != self.server.stop:
                raise ValueError('Layer range mismatch.')
            x = decode(payload.get('activation'), self.server.spec.dim, self.server.spec.context)
            with self.server.compute_lock, torch.inference_mode():
                start = time.monotonic()
                output = self.server.segment(x.to(self.server.device))
                compute_ms = (time.monotonic() - start) * 1000
                self.server.completed += 1
            self.send_json(200, {'model_id': self.server.spec.identity, 'start': self.server.start,
                                 'stop': self.server.stop, 'activation': encode(output),
                                 'compute_ms': round(compute_ms, 3)})
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            self.send_json(400, {'error': 'Invalid forward request'})
        except RuntimeError:
            self.send_json(500, {'error': 'Compute failed'})
