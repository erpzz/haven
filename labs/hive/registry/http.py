"""Private loopback registration API. Never expose directly to the public Internet."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from urllib.parse import urlsplit
from .core import Registry, RegistrationError

MAX_BODY = 4096

class Server(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, addr, registry: Registry):
        if addr[0] != '127.0.0.1':
            raise ValueError('Pilot binds loopback only; use a reviewed authenticated gateway for publication')
        self.registry = registry
        super().__init__(addr, Handler)

class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *_):
        pass
    def reply(self, status, data):
        body = json.dumps(data, separators=(',', ':'), allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True
        self.wfile.write(body)
    def guard(self):
        if self.client_address[0] != '127.0.0.1' or self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}':
            self.reply(403, {'error': 'Private loopback endpoint only'})
            return False
        origin = self.headers.get('Origin')
        if origin:
            self.reply(403, {'error': 'Browser origins are not accepted'})
            return False
        return True
    def auth(self):
        v = self.headers.get('Authorization', '')
        return v[7:] if v.startswith('Bearer ') else ''
    def body(self):
        if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type') != 'application/json':
            raise RegistrationError('JSON content type required; chunked bodies unsupported')
        length = int(self.headers.get('Content-Length', '0'))
        if not (0 < length <= MAX_BODY):
            raise RegistrationError('Invalid body size')
        v = json.loads(self.rfile.read(length), parse_constant=lambda x: (_ for _ in ()).throw(RegistrationError('Invalid number')))
        if not isinstance(v, dict):
            raise RegistrationError('JSON object required')
        return v
    def do_GET(self):
        if not self.guard(): return
        if self.path == '/v1/nodes':
            self.reply(200, self.server.registry.public_nodes())
        else:
            self.reply(404, {'error': 'Not found'})
    def do_POST(self):
        if not self.guard(): return
        try:
            path = urlsplit(self.path).path
            if path == '/v1/invites':
                data = self.body()
                if set(data) != {'ttl_seconds'}:
                    raise RegistrationError('Invalid invite request')
                result = {'invite': self.server.registry.invite(self.auth(), ttl_seconds=data['ttl_seconds'])}
            elif path == '/v1/join':
                data = self.body()
                if set(data) != {'invite', 'declaration'}:
                    raise RegistrationError('Invalid join request')
                result = self.server.registry.join(data['invite'], data['declaration'])
            elif path.startswith('/v1/nodes/') and path.endswith('/heartbeat'):
                node_id = path.split('/')[3]
                data = self.body()
                if set(data) != {'available'}:
                    raise RegistrationError('Invalid heartbeat')
                result = self.server.registry.heartbeat(node_id, self.auth(), available=data['available'])
            elif path.startswith('/v1/nodes/') and path.endswith('/revoke'):
                node_id = path.split('/')[3]
                data = self.body()
                if data:
                    raise RegistrationError('Revoke body must be empty object')
                result = self.server.registry.revoke(node_id, self.auth())
            else:
                self.reply(404, {'error':'Not found'}); return
            self.reply(200, result)
        except (RegistrationError, ValueError, TypeError, json.JSONDecodeError, KeyError):
            self.reply(400, {'error': 'Invalid request'})
        except PermissionError:
            self.reply(403, {'error': 'Not authorized'})
