"""Owner-enrolled private workers. Loopback contracts, no discovery execution.

Registration files are private administrator input, not model output. A model
cannot enroll workers, choose URLs, rotate credentials or widen an audience.

A `cloud` enrollment is the owner's own Claude Code / Codex plan reached through a
loopback tunnel. It is hosted egress: explicit selection only, never Automatic.
"""
import http.client
import json
import os
from pathlib import Path
import re
import stat
import threading
import time

# Hosted route classes. Plan allowance only; a metered API class would be a separate, explicit addition.
ROUTE_CLASSES = {'CLAUDE_CODE_PLAN': 'Anthropic', 'CHATGPT_PLAN': 'OpenAI'}


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
            endpoint(row.get('base', ''))  # Literal IPv4 loopback, no query/redirect/DNS.
            if row.get('trust') != 'OWNER_ENROLLED_SSH' or row.get('allowed_roles') != ['admin']:
                raise ValueError('This first worker slice requires explicit owner-only SSH enrollment.')
            cloud = row.get('kind') == 'cloud'
            if cloud:
                if (row.get('compute') != 'hosted' or row.get('egress') != 'HOSTED_SUBSCRIPTION' or
                        row.get('route_class') not in ROUTE_CLASSES or 'model_sha256' in row):
                    raise ValueError('A cloud lane must declare hosted subscription egress and its route class.')
            elif row.get('kind') != 'llama' or row.get('compute') not in ('metal', 'cpu', 'cuda'):
                raise ValueError('Unsupported worker backend contract.')
            for field in ('label', 'node_id', 'model', 'display_model'):
                if not isinstance(row.get(field), str) or not 1 <= len(row[field]) <= 160 or any(ord(c) < 32 for c in row[field]):
                    raise ValueError('Invalid worker metadata.')
            if not re.fullmatch(r'[A-Za-z0-9_-]{32,256}', row.get('key', '')):
                raise ValueError('A private worker credential is required.')
            if not cloud and not re.fullmatch(r'[0-9a-f]{64}', row.get('model_sha256', '')):
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
        conn = http.client.HTTPConnection(host, port, timeout=2)
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
                cloud = row['kind'] == 'cloud'
                rows.append({k: row.get(k) for k in ('id', 'label', 'node_id', 'model', 'display_model',
                    'kind', 'compute', 'model_sha256', 'max_context_tokens', 'trust', 'allowed_roles', 'route_class')})
                rows[-1].update(observed=seen, locality='HOSTED_SUBSCRIPTION' if cloud else 'PRIVATE_SSH_WORKER',
                                vendor=ROUTE_CLASSES.get(row.get('route_class')), automatic=not cloud,
                                inventory_stage='INSTALLED',
                                qualification='NOT_HAVEN_QUALIFIED', features={'text': True, 'streaming': True,
                                'native_tools': 'DISABLED' if cloud else 'UNVERIFIED', 'vision': False,
                                'cancellation': 'REQUEST_CLOSE_STOPS_CLI' if cloud else 'REQUEST_CLOSE_ONLY'},
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
        cloud = row['kind'] == 'cloud'
        return {'base': row['base'], 'key': row['key'], 'model': row['model'],
                'display_model': row['display_model'], 'kind': row['kind'], 'ownership': 'EXTERNAL',
                'provider_id': ident, 'worker_label': row['label'], 'node_id': row['node_id'],
                'compute': row['compute'], 'model_sha256': row.get('model_sha256'), 'route_class': row.get('route_class'),
                'profile': {'context': row['max_context_tokens'], 'max_output_tokens': 4096 if cloud else 1024,
                            'max_messages': 40 if cloud else 8},
                'connected_at': row.get('enrolled_at', 0),
                'route_reason': (f"Explicit cloud lane: this conversation left the house to {ROUTE_CLASSES[row['route_class']]} "
                                 f"under your own plan ({row['route_class']}). No tools, no API billing; "
                                 'temperature/seed are not applied.') if cloud else
                                'Explicit owner-enrolled private worker; no hosted egress.'}

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
            # Hosted egress is never an automatic choice.
            ids = sorted(i for i, row in self.entries.items() if row.get('kind') != 'cloud')
        for ident in ids:
            try:
                conn = self.connection(ident)
                conn['route_reason'] = 'Automatic: ready owner-enrolled private worker while Slink is unavailable; no cloud fallback.'
                return conn
            except ValueError:
                pass
        raise ValueError('No eligible ready private text worker. Nothing was loaded and no paid fallback was attempted.')
