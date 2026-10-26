"""Owner-enrolled private workers. Loopback contracts, no discovery execution.

Registration files are private administrator input, not model output. A model
cannot enroll workers, choose URLs, rotate credentials or widen an audience.
"""
import http.client
import json
import os
from pathlib import Path
import re
import stat
import socket
import threading
import time


class PrivateWorkerConnection(http.client.HTTPConnection):
    """Connect through an owner-private SSH Unix socket, never a reusable TCP port."""
    def __init__(self, path, timeout=2):
        super().__init__('localhost', timeout=timeout)
        self.path = Path(path)

    def connect(self):
        parent = self.path.parent.lstat()
        info = self.path.lstat()
        if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid() or parent.st_mode & 0o077
                or not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid()):
            raise ValueError('Private SSH worker socket ownership is not verified.')
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.timeout)
            sock.connect(str(self.path))
        except Exception:
            sock.close()
            raise
        self.sock = sock


class Registry:
    def __init__(self, data):
        self.path = Path(data) / 'providers'
        self.path.mkdir(mode=0o700, exist_ok=True)
        info = self.path.lstat()
        if not stat.S_ISDIR(info.st_mode) or (os.name != 'nt' and (info.st_uid != os.getuid() or info.st_mode & 0o077)):
            raise ValueError('Worker enrollments require a private owned directory.')
        self.lock = threading.RLock()
        self.entries, self.observed = {}, {}
        self.reload()

    def reload(self):
        from labcore import endpoint
        entries = {}
        for path in sorted(self.path.glob('*.json'))[:8]:
            fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
            with os.fdopen(fd) as f:
                info = os.fstat(f.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size > 32768 or (os.name != 'nt' and (info.st_uid != os.getuid() or info.st_mode & 0o077)):
                    raise ValueError('Invalid private worker enrollment.')
                row = json.load(f)
            ident = row.get('id', '')
            if not isinstance(ident, str) or not re.fullmatch(r'[a-z][a-z0-9-]{2,47}', ident) or ident in ('managed', 'auto') or path.stem != ident:
                raise ValueError('Invalid worker identifier.')
            endpoint(row.get('base', ''))  # Retained API identity; transport is private Unix SSH.
            sock = Path(row.get('socket_path', ''))
            if not sock.is_absolute() or sock.parent.resolve() != self.path.resolve() or sock.name != ident + '.sock':
                raise ValueError('Worker transport must be its private enrollment-directory SSH socket.')
            if row.get('trust') != 'OWNER_ENROLLED_SSH' or row.get('allowed_roles') != ['admin']:
                raise ValueError('This first worker slice requires explicit owner-only SSH enrollment.')
            if row.get('kind') != 'llama' or row.get('compute') not in ('metal', 'cpu', 'cuda'):
                raise ValueError('Unsupported worker backend contract.')
            for field in ('label', 'node_id', 'model', 'display_model'):
                if not isinstance(row.get(field), str) or not 1 <= len(row[field]) <= 160 or any(ord(c) < 32 for c in row[field]):
                    raise ValueError('Invalid worker metadata.')
            if not re.fullmatch(r'[A-Za-z0-9_-]{32,256}', row.get('key', '')):
                raise ValueError('A private worker credential is required.')
            if not re.fullmatch(r'[0-9a-f]{64}', row.get('model_sha256', '')):
                raise ValueError('An exact installed-model digest is required.')
            if type(row.get('max_context_tokens')) is not int or not 512 <= row['max_context_tokens'] <= 32768:
                raise ValueError('A bounded worker context is required.')
            entries[ident] = row
        with self.lock:
            self.entries = entries
            self.observed = {}  # A reload never inherits a stale authentication result.
        return {'registered': len(entries), 'note': 'Enrollment does not prove readiness or inference.'}

    def probe(self, ident):
        from labcore import endpoint
        with self.lock:
            row = dict(self.entries.get(ident) or {})
        if not row:
            raise ValueError('Unknown enrolled worker.')
        host, port = endpoint(row['base'])
        began = time.monotonic()
        conn = PrivateWorkerConnection(row['socket_path'], timeout=2)
        observed = {'checked_at': time.time(), 'state': 'OFFLINE', 'readiness': 'UNKNOWN', 'model_ids': []}
        try:
            conn.request('GET', '/v1/models', headers={'Authorization': 'Bearer ' + row['key']})
            response = conn.getresponse()
            if response.status != 200:
                observed.update(state='AUTH_REJECTED' if response.status in (401, 403) else 'UNAVAILABLE', http_status=response.status)
            else:
                raw = response.read(65537)
                if len(raw) > 65536:
                    raise ValueError('Worker metadata exceeded its bound.')
                ids = [v.get('id') for v in json.loads(raw).get('data', []) if isinstance(v, dict)]
                observed.update(state='READY' if row['model'] in ids else 'MODEL_MISMATCH',
                                readiness='READY' if row['model'] in ids else 'NOT_READY',
                                model_ids=[i for i in ids if isinstance(i, str) and len(i) <= 160][:16])
        except (OSError, ValueError, http.client.HTTPException):
            observed['state'] = 'OFFLINE'
        finally:
            conn.close()
        observed['metadata_roundtrip_ms'] = round((time.monotonic() - began) * 1000, 3)
        with self.lock:
            # A concurrent administrative enrollment reload cannot accept an old probe.
            if self.entries.get(ident) == row:
                self.observed[ident] = observed
        return observed

    def probe_all(self):
        with self.lock:
            ids = list(self.entries)
        return {ident: self.probe(ident) for ident in ids}

    def snapshot(self):
        with self.lock:
            rows = []
            for ident, row in self.entries.items():
                seen = dict(self.observed.get(ident) or {'state': 'UNKNOWN', 'readiness': 'UNKNOWN'})
                # Metadata is deliberately marked stale; GET never runs inference or starts a tunnel.
                if seen.get('checked_at', 0) < time.time() - 30:
                    seen.update(state='STALE' if 'checked_at' in seen else 'UNKNOWN', readiness='UNKNOWN')
                rows.append({k: row[k] for k in ('id', 'label', 'node_id', 'model', 'display_model',
                    'kind', 'compute', 'model_sha256', 'max_context_tokens', 'trust', 'allowed_roles')})
                rows[-1].update(observed=seen, locality='PRIVATE_SSH_WORKER', inventory_stage='INSTALLED',
                                qualification='NOT_HAVEN_QUALIFIED', digest_provenance='WORKER_DECLARED', features={'text': True, 'streaming': True,
                                'native_tools': 'UNVERIFIED', 'vision': False, 'cancellation': 'REQUEST_CLOSE_ONLY'},
                                capabilities=row.get('capabilities', {}), current_resource_usage='UNAVAILABLE')
            return rows

    def connection(self, ident):
        seen = self.probe(ident)  # Fresh authenticated metadata at dispatch, never a cached success.
        if seen['state'] != 'READY':
            raise ValueError('Selected worker is ' + seen['state'] + '; no inference or fallback occurred.')
        with self.lock:
            if self.observed.get(ident) is not seen:
                raise ValueError('Worker enrollment changed during authentication; no request was sent.')
            row = dict(self.entries[ident])
        return {'base': row['base'], 'key': row['key'], 'model': row['model'],
                'socket_path': row['socket_path'], 'digest_provenance': 'WORKER_DECLARED',
                'display_model': row['display_model'], 'kind': row['kind'], 'ownership': 'EXTERNAL',
                'provider_id': ident, 'worker_label': row['label'], 'node_id': row['node_id'],
                'compute': row['compute'], 'model_sha256': row['model_sha256'],
                'profile': {'context': row['max_context_tokens']}, 'connected_at': row.get('enrolled_at', 0),
                'route_reason': 'Explicit owner-enrolled private worker; no hosted egress.'}

    def choose(self, requested, managed, *, managed_ready):
        if requested == 'managed':
            if not managed:
                raise ValueError('No Slink runtime is connected. Select an enrolled worker or load a prepared model.')
            return {**managed, 'provider_id': 'managed', 'worker_label': 'Slink', 'route_reason': 'Explicit Slink runtime.'}
        if requested != 'auto':
            return self.connection(requested)
        if managed and managed_ready and managed.get('kind') == 'llama':
            return {**managed, 'provider_id': 'managed', 'worker_label': 'Slink',
                    'route_reason': 'Automatic: already-ready Slink compact model; no load or external egress.'}
        with self.lock:
            ids = sorted(self.entries)
        for ident in ids:
            try:
                conn = self.connection(ident)
                conn['route_reason'] = 'Automatic: ready owner-enrolled private worker while Slink is unavailable; no cloud fallback.'
                return conn
            except ValueError:
                pass
        raise ValueError('No eligible ready private text worker. Nothing was loaded and no paid fallback was attempted.')
