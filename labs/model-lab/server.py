"""Run: python server.py --open. Development UI only; loopback, no CORS."""
from __future__ import annotations
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import threading
import time
import webbrowser
from labcore import Lab, ROOT, VERSION, MAX_JSON

ASSETS = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'application/javascript; charset=utf-8'),
          '/style.css': ('style.css', 'text/css; charset=utf-8'), '/favicon.svg': ('favicon.svg', 'image/svg+xml')}

class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False
    def __init__(self, address, lab):
        self.lab = lab
        super().__init__(address, Handler)

class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def setup(self):
        super().setup(); self.connection.settimeout(15)
    def log_message(self, *args):
        pass  # Never log tokens, prompts, URLs or request bodies.
    def send(self, code: int, body: bytes, content_type='application/json; charset=utf-8'):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True
        try: self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError): pass
    def json(self, code: int, value):
        self.send(code, json.dumps(value, ensure_ascii=False, allow_nan=False).encode())
    def guard(self, token=True):
        expected = f'127.0.0.1:{self.server.server_port}'
        if self.headers.get('Host') != expected:
            self.json(403, {'error': 'Unapproved Host. Open the printed 127.0.0.1 address.'}); return False
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + expected:
            self.json(403, {'error': 'Cross-origin request denied.'}); return False
        if token and not hmac.compare_digest(self.headers.get('X-Lab-Token', ''), self.server.lab.token):
            self.json(401, {'error': 'Open the private launch link from the console; the local session expired.'}); return False
        return True
    def do_GET(self):
        if not self.guard(token=self.path.startswith('/api/') and self.path != '/api/health'): return
        try:
            if self.path in ASSETS:
                name, mime = ASSETS[self.path]
                self.send(200, (ROOT / 'static' / name).read_bytes(), mime)
            elif self.path == '/api/health': self.json(200, {'app': 'Haven Model Lab', 'version': VERSION})
            elif self.path == '/api/state': self.json(200, self.server.lab.public_state())
            elif self.path == '/api/hardware': self.json(200, self.server.lab.get_hardware())
            elif self.path.startswith('/api/jobs/'):
                job = self.server.lab.jobs.get(self.path.rsplit('/', 1)[-1])
                self.json(200 if job else 404, job.snapshot() if job else {'error': 'Unknown job.'})
            elif self.path == '/api/log':
                p = self.server.lab.data / 'engine.log'
                if p.exists():
                    with p.open('rb') as f:
                        f.seek(max(0, p.stat().st_size - 24000)); text = f.read().decode('utf-8', 'replace')
                else: text = 'No managed engine has run in this lab yet.'
                self.json(200, {'text': text})
            elif self.path == '/api/benchmarks':
                p = self.server.lab.data / 'benchmarks.jsonl'
                rows = []
                if p.exists():
                    with p.open(encoding='utf-8') as f:
                        for line in f:
                            try: rows.append(json.loads(line))
                            except ValueError: pass
                            if len(rows) > 1000: rows.pop(0)
                self.json(200, {'rows': rows})
            elif self.path == '/api/research': self.json(200, {'text': (ROOT / 'docs' / 'EFFICIENCY.md').read_text('utf-8')})
            else: self.json(404, {'error': 'Not found.'})
        except Exception as e:
            self.json(500, {'error': str(e)[:300]})
    def do_POST(self):
        if not self.guard(): return
        if self.headers.get('Transfer-Encoding'):
            self.json(400, {'error': 'Chunked request bodies are not supported.'}); return
        try:
            n = int(self.headers.get('Content-Length', '0'))
            if not 0 < n <= MAX_JSON: raise ValueError('Request too large or empty.')
            if self.headers.get_content_type() != 'application/json': raise ValueError('JSON required.')
            data = json.loads(self.rfile.read(n), parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Non-finite JSON number.')))
            if not isinstance(data, dict): raise ValueError('JSON object required.')
            lab = self.server.lab
            if self.path == '/api/connect': out = lab.connect(data.get('base', ''), data.get('key', ''), data.get('kind', 'strata'))
            elif self.path == '/api/disconnect': out = lab.disconnect()
            elif self.path == '/api/engine/install':
                if data.get('confirmed') is not True: raise ValueError('Download confirmation required.')
                out = {'job_id': lab.install_llama()}
            elif self.path == '/api/model/download':
                if data.get('confirmed') is not True: raise ValueError('Download confirmation required.')
                out = {'job_id': lab.download_model(data.get('id', ''))}
            elif self.path == '/api/model/import': out = lab.import_model(data.get('path', ''))
            elif self.path == '/api/engine/start': out = {'job_id': lab.start_llama(data.get('id', ''), data.get('preset', 'balanced'), data.get('overrides'), data.get('allow_tight') is True)}
            elif self.path == '/api/engine/stop': out = lab.stop_engine()
            elif self.path == '/api/generate': out = {'job_id': lab.generate(data)}
            elif self.path == '/api/cancel':
                job = lab.jobs.get(data.get('id', ''))
                if not job: raise ValueError('Unknown job.')
                job.cancel(); out = job.snapshot()
            elif self.path == '/api/shutdown':
                self.json(200, {'state': 'SHUTTING_DOWN', 'external_strata_stopped': False})
                threading.Thread(target=self.server.shutdown, daemon=True).start(); return
            else:
                self.json(404, {'error': 'Not found.'}); return
            self.json(200, out)
        except (ValueError, TypeError, KeyError, FileNotFoundError, OSError) as e:
            self.json(400, {'error': str(e)[:400]})
        except Exception as e:
            self.json(500, {'error': f'{type(e).__name__}: {str(e)[:300]}'})
    def do_OPTIONS(self):
        self.json(403, {'error': 'Cross-origin access disabled.'})

def main():
    ap = argparse.ArgumentParser(description='Haven Model Lab — Strata + llama.cpp')
    ap.add_argument('--port', type=int, default=8787)
    ap.add_argument('--data-dir', type=Path, default=ROOT / '.local')
    ap.add_argument('--open', action='store_true')
    args = ap.parse_args()
    if not 1024 <= args.port <= 65535: ap.error('Use an unprivileged local port.')
    lab = Lab(args.data_dir)
    try: server = Server(('127.0.0.1', args.port), lab)
    except OSError as e: raise SystemExit(f'Cannot bind local UI: {e}. Another lab may already be open. Nothing was killed.')
    url = f'http://127.0.0.1:{server.server_port}/#token={lab.token}'
    print('\nHaven Model Lab — local development preview\n', flush=True)
    print(url, flush=True)
    print('\nKeep this window open. Ctrl+C or the UI Exit button stops owned engines.\nExternal Strata stays in its own console. No models/downloads start automatically.\n', flush=True)
    if args.open: webbrowser.open(url)
    def stop_signal(*_): threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop_signal)
    try: server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt: pass
    finally:
        try: print('Cleanup:', lab.shutdown(), flush=True)
        finally: server.server_close()

if __name__ == '__main__': main()
