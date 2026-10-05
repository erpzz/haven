"""Haven Model Lab HTTP server.

Default mode remains loopback-only with the private launch token.
--lan opts into home-LAN access protected by invite-only accounts.
"""
from __future__ import annotations

import argparse
from http.cookies import SimpleCookie
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path
import signal
import socket
import threading
import time
import urllib.parse
import webbrowser

from labcore import Lab, ROOT, VERSION, MAX_JSON

ASSETS = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/app.js': ('app.js', 'application/javascript; charset=utf-8'),
    '/style.css': ('style.css', 'text/css; charset=utf-8'),
    '/favicon.svg': ('favicon.svg', 'image/svg+xml'),
}
COOKIE_NAME = 'haven_session'
ADMIN_POSTS = {
    '/api/connect', '/api/disconnect', '/api/engine/install', '/api/model/download',
    '/api/model/import', '/api/engine/start', '/api/engine/stop', '/api/shutdown',
}
ADMIN_GETS = {'/api/log', '/api/benchmarks', '/api/auth/users'}


def _is_private_address(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value.split('%', 1)[0])
        return ip.is_private or ip.is_loopback
    except ValueError:
        return False


def _host_allowed(host_header: str, port: int) -> bool:
    if not host_header or any(ch in host_header for ch in '\r\n'):
        return False
    try:
        parsed = urllib.parse.urlsplit('//' + host_header)
        host = parsed.hostname
        got_port = parsed.port or 80
    except ValueError:
        return False
    if got_port != port or not host:
        return False
    if host == 'localhost':
        return True
    return _is_private_address(host)


def _lan_urls(port: int) -> list[str]:
    found = set()
    try:
        for row in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET, socket.SOCK_STREAM):
            host = row[4][0]
            if _is_private_address(host) and not ipaddress.ip_address(host).is_loopback:
                found.add(host)
    except OSError:
        pass
    return [f'http://{host}:{port}/' for host in sorted(found)]


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, address, lab, lan_mode=False, control_token=''):
        self.lab = lab
        self.lan_mode = bool(lan_mode)
        self.control_token = control_token
        self.job_owners = {}
        self.job_lock = threading.RLock()
        self.login_failures = {}
        self.login_lock = threading.RLock()
        self.auth = None
        self.bootstrap_token = None
        if self.lan_mode:
            from lan_auth import AuthStore
            self.auth = AuthStore(lab.data)
            if self.auth.setup_required():
                self.bootstrap_token = os.environ.pop('HAVEN_BOOTSTRAP_TOKEN', '') or __import__('secrets').token_urlsafe(32)
        super().__init__(address, Handler)

    def own_job(self, job_id: str, user_id: int):
        with self.job_lock:
            self.job_owners[job_id] = int(user_id)

    def owns_job(self, job_id: str, user_id: int) -> bool:
        with self.job_lock:
            return self.job_owners.get(job_id) == int(user_id)

    def filtered_state(self, user: dict) -> dict:
        state = self.lab.public_state()
        if not self.lan_mode:
            return state
        uid = int(user['id'])
        state['jobs'] = [j for j in state.get('jobs', []) if self.owns_job(j.get('id', ''), uid)]
        state['user'] = {k: user[k] for k in ('id', 'username', 'role')}
        if user['role'] != 'admin':
            state.pop('data_dir', None)
            engine = state.get('engine') or {}
            state['engine'] = {k: engine.get(k) for k in ('state', 'ownership', 'label', 'started_at', 'stopped_at') if k in engine}
        return state

    def login_allowed(self, peer: str) -> bool:
        now = time.time()
        with self.login_lock:
            rows = [x for x in self.login_failures.get(peer, []) if now - x < 300]
            self.login_failures[peer] = rows
            return len(rows) < 5

    def login_failed(self, peer: str):
        with self.login_lock:
            self.login_failures.setdefault(peer, []).append(time.time())

    def login_succeeded(self, peer: str):
        with self.login_lock:
            self.login_failures.pop(peer, None)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, *args):
        pass  # Never log tokens, prompts, URLs or request bodies.

    def send(self, code: int, body: bytes, content_type='application/json; charset=utf-8', headers=None):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        self.send_header('Connection', 'close')
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.close_connection = True
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def json(self, code: int, value, headers=None):
        self.send(code, json.dumps(value, ensure_ascii=False, allow_nan=False).encode(), headers=headers)

    def _host_origin_guard(self) -> bool:
        if not self.server.lan_mode:
            expected = f'127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host') != expected:
                self.json(403, {'error': 'Unapproved Host. Open the printed 127.0.0.1 address.'})
                return False
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + expected:
                self.json(403, {'error': 'Cross-origin request denied.'})
                return False
            return True
        peer = self.client_address[0]
        if not _is_private_address(peer):
            self.json(403, {'error': 'LAN access is limited to private or loopback source addresses.'})
            return False
        host = self.headers.get('Host', '')
        if not _host_allowed(host, self.server.server_port):
            self.json(403, {'error': 'Use the private-IP URL printed by OPEN-LAN.'})
            return False
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + host:
            self.json(403, {'error': 'Cross-origin request denied.'})
            return False
        return True

    def _session_token(self) -> str:
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
        except Exception:
            return ''
        morsel = cookie.get(COOKIE_NAME)
        return morsel.value if morsel else ''

    def _user(self, *, admin=False, csrf=False):
        if not self._host_origin_guard():
            return None
        if not self.server.lan_mode:
            if not hmac.compare_digest(self.headers.get('X-Lab-Token', ''), self.server.lab.token):
                self.json(401, {'error': 'Open the private launch link from the console; the local session expired.'})
                return None
            return {'id': 0, 'username': 'local-owner', 'role': 'admin', 'csrf': ''}
        token = self._session_token()
        user = self.server.auth.session(token)
        if not user:
            self.json(401, {'error': 'Sign in to Haven Model Lab.'})
            return None
        if admin and user['role'] != 'admin':
            self.json(403, {'error': 'Administrator access required.'})
            return None
        if csrf and not hmac.compare_digest(self.headers.get('X-CSRF-Token', ''), user['csrf']):
            self.json(403, {'error': 'Session verification failed. Reload and try again.'})
            return None
        return user

    def _read_json(self) -> dict:
        if self.headers.get('Transfer-Encoding'):
            raise ValueError('Chunked request bodies are not supported.')
        n = int(self.headers.get('Content-Length', '0'))
        if not 0 < n <= MAX_JSON:
            raise ValueError('Request too large or empty.')
        if self.headers.get_content_type() != 'application/json':
            raise ValueError('JSON required.')
        data = json.loads(
            self.rfile.read(n),
            parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Non-finite JSON number.')),
        )
        if not isinstance(data, dict):
            raise ValueError('JSON object required.')
        return data

    def _cookie_headers(self, token: str | None) -> dict:
        if token:
            value = f'{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={7 * 24 * 60 * 60}'
        else:
            value = f'{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0'
        return {'Set-Cookie': value}

    def _auth_payload(self, user: dict, csrf: str) -> dict:
        return {'user': {k: user[k] for k in ('id', 'username', 'role')}, 'csrf': csrf}

    def _login_user(self, user: dict):
        token, csrf = self.server.auth.create_session(user['id'])
        self.json(200, self._auth_payload(user, csrf), self._cookie_headers(token))

    def _handle_auth_get(self) -> bool:
        if not self.server.lan_mode:
            if self.path == '/api/auth/status':
                if not self._host_origin_guard():
                    return True
                self.json(200, {'enabled': False, 'setup_required': False, 'invite_only': False})
                return True
            return False
        if self.path == '/api/auth/status':
            if not self._host_origin_guard():
                return True
            self.json(200, {'enabled': True, 'setup_required': self.server.auth.setup_required(), 'invite_only': True, 'lan_urls': _lan_urls(self.server.server_port)})
            return True
        if self.path == '/api/auth/me':
            user = self._user()
            if user:
                self.json(200, self._auth_payload(user, user['csrf']))
            return True
        if self.path == '/api/auth/users':
            user = self._user(admin=True)
            if user:
                self.json(200, {'users': self.server.auth.list_users(user['id'])})
            return True
        return False

    def _handle_auth_post(self) -> bool:
        if not self.server.lan_mode:
            return False
        if self.path not in {
            '/api/auth/bootstrap', '/api/auth/login', '/api/auth/accept-invite',
            '/api/auth/logout', '/api/auth/invites', '/api/auth/users/disable',
        }:
            return False
        if not self._host_origin_guard():
            return True
        try:
            data = self._read_json()
            if self.path == '/api/auth/bootstrap':
                if not ipaddress.ip_address(self.client_address[0].split('%', 1)[0]).is_loopback:
                    self.json(403, {'error': 'Initial owner setup must be completed from this Windows PC.'})
                    return True
                supplied = str(data.get('token', ''))
                expected = self.server.bootstrap_token or ''
                if not expected or not hmac.compare_digest(supplied, expected):
                    self.json(403, {'error': 'Owner setup token is invalid or expired.'})
                    return True
                user = self.server.auth.create_owner(data.get('username', ''), data.get('password', ''))
                self.server.bootstrap_token = None
                self._login_user(user)
                return True
            if self.path == '/api/auth/login':
                peer = self.client_address[0]
                if not self.server.login_allowed(peer):
                    self.json(429, {'error': 'Too many failed sign-in attempts. Try again in a few minutes.'})
                    return True
                user = self.server.auth.authenticate(data.get('username', ''), data.get('password', ''))
                if not user:
                    self.server.login_failed(peer)
                    self.json(401, {'error': 'Invalid username or password.'})
                    return True
                self.server.login_succeeded(peer)
                self._login_user(user)
                return True
            if self.path == '/api/auth/accept-invite':
                user = self.server.auth.accept_invite(data.get('token', ''), data.get('username', ''), data.get('password', ''))
                self._login_user(user)
                return True
            user = self._user(admin=self.path in ('/api/auth/invites', '/api/auth/users/disable'), csrf=True)
            if not user:
                return True
            if self.path == '/api/auth/logout':
                self.server.auth.logout(self._session_token())
                self.json(200, {'state': 'SIGNED_OUT'}, self._cookie_headers(None))
            elif self.path == '/api/auth/invites':
                role = data.get('role', 'member')
                token = self.server.auth.create_invite(user['id'], role)
                self.json(200, {'token': token, 'role': role, 'expires_in_seconds': 24 * 60 * 60})
            elif self.path == '/api/auth/users/disable':
                target = self.server.auth.set_disabled(user['id'], int(data.get('user_id')), data.get('disabled') is True)
                self.json(200, {'user': target})
            return True
        except (ValueError, TypeError, KeyError) as exc:
            self.json(400, {'error': str(exc)[:400]})
            return True
        except PermissionError as exc:
            self.json(403, {'error': str(exc)[:300]})
            return True

    def _private_shutdown(self) -> bool:
        if self.path != '/api/private/shutdown':
            return False
        peer = self.client_address[0]
        valid = (
            ipaddress.ip_address(peer.split('%', 1)[0]).is_loopback
            and bool(self.server.control_token)
            and hmac.compare_digest(self.headers.get('X-Haven-Control', ''), self.server.control_token)
        )
        if not valid:
            self.json(403, {'error': 'Denied.'})
            return True
        self.json(200, {'state': 'SHUTTING_DOWN'})
        threading.Thread(target=self.server.shutdown, daemon=True).start()
        return True

    def do_GET(self):
        if self._handle_auth_get():
            return
        if not self._host_origin_guard():
            return
        try:
            if self.path in ASSETS:
                name, mime = ASSETS[self.path]
                self.send(200, (ROOT / 'static' / name).read_bytes(), mime)
                return
            if self.path == '/api/health':
                self.json(200, {'app': 'Haven Model Lab', 'version': VERSION, 'lan_auth': self.server.lan_mode})
                return
            if not self.path.startswith('/api/'):
                self.json(404, {'error': 'Not found.'})
                return
            user = self._user(admin=self.path in ADMIN_GETS)
            if not user:
                return
            if self.path == '/api/state':
                self.json(200, self.server.filtered_state(user))
            elif self.path == '/api/hardware':
                self.json(200, self.server.lab.get_hardware())
            elif self.path.startswith('/api/jobs/'):
                job_id = self.path.rsplit('/', 1)[-1]
                if self.server.lan_mode and not self.server.owns_job(job_id, user['id']):
                    self.json(404, {'error': 'Unknown job.'})
                    return
                job = self.server.lab.jobs.get(job_id)
                self.json(200 if job else 404, job.snapshot() if job else {'error': 'Unknown job.'})
            elif self.path == '/api/log':
                p = self.server.lab.data / 'engine.log'
                if p.exists():
                    with p.open('rb') as f:
                        f.seek(max(0, p.stat().st_size - 24000))
                        text = f.read().decode('utf-8', 'replace')
                else:
                    text = 'No managed engine has run in this lab yet.'
                self.json(200, {'text': text})
            elif self.path == '/api/benchmarks':
                p = self.server.lab.data / 'benchmarks.jsonl'
                rows = []
                if p.exists():
                    with p.open(encoding='utf-8') as f:
                        for line in f:
                            try:
                                rows.append(json.loads(line))
                            except ValueError:
                                pass
                            if len(rows) > 1000:
                                rows.pop(0)
                self.json(200, {'rows': rows})
            elif self.path == '/api/research':
                self.json(200, {'text': (ROOT / 'docs' / 'EFFICIENCY.md').read_text('utf-8')})
            else:
                self.json(404, {'error': 'Not found.'})
        except Exception as exc:
            self.json(500, {'error': str(exc)[:300]})

    def do_POST(self):
        if self._private_shutdown():
            return
        if self._handle_auth_post():
            return
        user = self._user(admin=self.path in ADMIN_POSTS, csrf=self.server.lan_mode)
        if not user:
            return
        try:
            data = self._read_json()
            lab = self.server.lab
            job_id = None
            if self.path == '/api/connect':
                out = lab.connect(data.get('base', ''), data.get('key', ''), data.get('kind', 'strata'))
            elif self.path == '/api/disconnect':
                out = lab.disconnect()
            elif self.path == '/api/engine/install':
                if data.get('confirmed') is not True:
                    raise ValueError('Download confirmation required.')
                job_id = lab.install_llama()
                out = {'job_id': job_id}
            elif self.path == '/api/model/download':
                if data.get('confirmed') is not True:
                    raise ValueError('Download confirmation required.')
                job_id = lab.download_model(data.get('id', ''))
                out = {'job_id': job_id}
            elif self.path == '/api/model/import':
                out = lab.import_model(data.get('path', ''))
            elif self.path == '/api/engine/start':
                job_id = lab.start_llama(data.get('id', ''), data.get('preset', 'balanced'), data.get('overrides'), data.get('allow_tight') is True)
                out = {'job_id': job_id}
            elif self.path == '/api/engine/stop':
                out = lab.stop_engine()
            elif self.path == '/api/generate':
                job_id = lab.generate(data)
                out = {'job_id': job_id}
            elif self.path == '/api/cancel':
                job_id = data.get('id', '')
                if self.server.lan_mode and not self.server.owns_job(job_id, user['id']):
                    raise ValueError('Unknown job.')
                job = lab.jobs.get(job_id)
                if not job:
                    raise ValueError('Unknown job.')
                job.cancel()
                out = job.snapshot()
            elif self.path == '/api/shutdown':
                self.json(200, {'state': 'SHUTTING_DOWN', 'external_strata_stopped': False})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            else:
                self.json(404, {'error': 'Not found.'})
                return
            if job_id and self.server.lan_mode:
                self.server.own_job(job_id, user['id'])
            self.json(200, out)
        except (ValueError, TypeError, KeyError, FileNotFoundError, OSError) as exc:
            self.json(400, {'error': str(exc)[:400]})
        except Exception as exc:
            self.json(500, {'error': f'{type(exc).__name__}: {str(exc)[:300]}'})

    def do_OPTIONS(self):
        self.json(403, {'error': 'Cross-origin access disabled.'})


def main():
    ap = argparse.ArgumentParser(description='Haven Model Lab — Strata + llama.cpp')
    ap.add_argument('--port', type=int, default=8787)
    ap.add_argument('--data-dir', type=Path, default=ROOT / '.local')
    ap.add_argument('--open', action='store_true')
    ap.add_argument('--lan', action='store_true', help='Bind the UI to private LAN addresses and require invite-only accounts.')
    args = ap.parse_args()
    if not 1024 <= args.port <= 65535:
        ap.error('Use an unprivileged local port.')
    lab = Lab(args.data_dir)
    control_token = os.environ.pop('HAVEN_CONTROL_TOKEN', '')
    bind = '0.0.0.0' if args.lan else '127.0.0.1'
    try:
        server = Server((bind, args.port), lab, lan_mode=args.lan, control_token=control_token)
    except OSError as exc:
        raise SystemExit(f'Cannot bind local UI: {exc}. Another lab may already be open. Nothing was killed.')

    if args.lan:
        local_url = f'http://127.0.0.1:{server.server_port}/'
        owner_url = local_url + (f'#bootstrap={server.bootstrap_token}' if server.bootstrap_token else '')
        print('\nHaven Model Lab — invite-only home LAN mode\n', flush=True)
        print('Local owner URL:', owner_url, flush=True)
        urls = _lan_urls(server.server_port)
        if urls:
            for url in urls:
                print('LAN access:', url, flush=True)
        else:
            print('LAN access: private IPv4 address not discovered; use ipconfig and port %d.' % server.server_port, flush=True)
        print('\nLAN mode is intended for a trusted home/private network only. It does not provide TLS or internet exposure.\n', flush=True)
        url = owner_url
    else:
        url = f'http://127.0.0.1:{server.server_port}/#token={lab.token}'
        print('\nHaven Model Lab — local development preview\n', flush=True)
        print(url, flush=True)
        print('\nKeep this window open. Ctrl+C or the UI Exit button stops owned engines.\nExternal Strata stays in its own console. No models/downloads start automatically.\n', flush=True)

    if args.open:
        webbrowser.open(url)

    def stop_signal(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop_signal)
    try:
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            print('Cleanup:', lab.shutdown(), flush=True)
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
