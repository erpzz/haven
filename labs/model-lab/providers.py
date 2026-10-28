"""Owner-enrolled private workers. Loopback contracts, no discovery execution.

Registration files are private administrator input, not model output. A model
cannot enroll workers, choose URLs, rotate credentials or widen an audience.

A `cloud` enrollment is the owner's own Claude Code / Codex plan reached through a
loopback tunnel. It is hosted egress: explicit selection only, never Automatic.

A `metered` enrollment is a keyed API with a published free allowance (Cloudflare
Workers AI, Groq) reached the same way: through an owner-run relay on the enrollment
socket, so the key never enters the Lab process and the Lab makes no outbound request.
It is hosted egress too -- explicit selection only, never Automatic -- and it must
record how its spending ceiling is imposed and the provider document that permits
this use.
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

# Hosted route classes. Plan allowance only.
ROUTE_CLASSES = {'CLAUDE_CODE_PLAN': 'Anthropic', 'CHATGPT_PLAN': 'OpenAI'}

# Metered route classes: keyed APIs with a published free allowance, reached through an
# owner-run relay on the enrollment socket (ops/haven-core/metered-relay.py). The key stays
# in the relay; the Lab keeps its no-outbound-egress property. Explicit selection only --
# admitting a metered lane into Automatic is a separate operator decision that is NOT taken
# here; see labs/model-lab/METERED_ROUTE_PROPOSAL.md.
METERED_CLASSES = {'CLOUDFLARE_WORKERS_AI_FREE': 'Cloudflare', 'GROQ_FREE': 'Groq'}

# How a spending ceiling is actually imposed. Only the first two are boundaries: a ceiling
# this process merely believes in cannot stop a charge. Recorded at enrollment by the owner,
# never inferred, and currently advisory -- it is surfaced in the route reason and receipt so
# an operator can see which lanes could bill if their allowance ran out.
COST_BOUNDARIES = ('NOT_CHARGEABLE', 'PROVIDER_HARD_LIMIT', 'PROVIDER_SOFT_ALERT', 'CLIENT_SIDE_ONLY')
ENFORCEABLE_BOUNDARIES = ('NOT_CHARGEABLE', 'PROVIDER_HARD_LIMIT')


def eligibility_evidence(value):
    """Validate the owner's citation that this provider permits this use on this plan.

    A marketing page is not evidence. The owner records the document, the clause they
    relied on and the date they read it; this only checks shape and bounds, because a
    model cannot verify a provider's terms on the owner's behalf.
    """
    if not isinstance(value, dict):
        raise ValueError('A metered lane requires recorded eligibility evidence.')
    url = value.get('doc_url')
    if not isinstance(url, str) or not url.startswith('https://') or len(url) > 300:
        raise ValueError('Eligibility evidence needs an https provider-documentation URL.')
    clause = value.get('clause')
    if not isinstance(clause, str) or not 8 <= len(clause) <= 300 or any(ord(c) < 32 for c in clause):
        raise ValueError('Eligibility evidence needs the clause the owner relied on.')
    if not isinstance(value.get('retrieved'), str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value['retrieved']):
        raise ValueError('Eligibility evidence needs the date the document was read (YYYY-MM-DD).')
    return {'doc_url': url, 'clause': clause, 'retrieved': value['retrieved']}


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


def plan_status(value):
    """Accept only the cloud worker's bounded plan fields; anything else is unknown."""
    plan = {'status': 'UNKNOWN'}
    if not isinstance(value, dict):
        return plan
    for key in ('daily_used', 'daily_cap'):
        if type(value.get(key)) is int and 0 <= value[key] <= 100000:
            plan[key] = value[key]
    if value.get('status') in ('ALLOWED', 'LIMITED', 'UNKNOWN'):
        plan['status'] = value['status']
    if type(value.get('resets_at')) in (int, float) and 0 < value['resets_at'] < 1e11:
        plan['resets_at'] = value['resets_at']
    text = value.get('resets_text')
    if isinstance(text, str) and re.fullmatch(r'[0-9: ]{1,8}[APMapm.]{0,4}', text.strip()):
        plan['resets_text'] = text.strip()
    return plan


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
            cloud = row.get('kind') == 'cloud'
            metered = row.get('kind') == 'metered'
            if cloud:
                if (row.get('compute') != 'hosted' or row.get('egress') != 'HOSTED_SUBSCRIPTION' or
                        row.get('route_class') not in ROUTE_CLASSES or 'model_sha256' in row):
                    raise ValueError('A cloud lane must declare hosted subscription egress and its route class.')
            elif metered:
                if (row.get('compute') != 'hosted' or row.get('egress') != 'METERED_FREE_ALLOWANCE' or
                        row.get('route_class') not in METERED_CLASSES or 'model_sha256' in row):
                    raise ValueError('A metered lane must declare metered free-allowance egress and its route class.')
                if row.get('cost_boundary') not in COST_BOUNDARIES:
                    raise ValueError('A metered lane must record how its spending ceiling is imposed.')
                row['eligibility_evidence'] = eligibility_evidence(row.get('eligibility_evidence'))
            elif row.get('kind') != 'llama' or row.get('compute') not in ('metal', 'cpu', 'cuda'):
                raise ValueError('Unsupported worker backend contract.')
            hosted = cloud or metered
            for field in ('label', 'node_id', 'model', 'display_model'):
                if not isinstance(row.get(field), str) or not 1 <= len(row[field]) <= 160 or any(ord(c) < 32 for c in row[field]):
                    raise ValueError('Invalid worker metadata.')
            if not re.fullmatch(r'[A-Za-z0-9_-]{32,256}', row.get('key', '')):
                raise ValueError('A private worker credential is required.')
            if not hosted and not re.fullmatch(r'[0-9a-f]{64}', row.get('model_sha256', '')):
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
                data = [v for v in json.loads(raw).get('data', []) if isinstance(v, dict)]
                ids = [v.get('id') for v in data]
                if row['kind'] == 'cloud':
                    mine = next((v for v in data if v.get('id') == row['model']), {})
                    observed['plan'] = plan_status(mine.get('haven_plan'))
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
                metered = row['kind'] == 'metered'
                hosted = cloud or metered
                rows.append({k: row.get(k) for k in ('id', 'label', 'node_id', 'model', 'display_model',
                    'kind', 'compute', 'model_sha256', 'max_context_tokens', 'trust', 'allowed_roles', 'route_class')})
                rows[-1].update(observed=seen,
                                locality=('METERED_FREE_ALLOWANCE' if metered else
                                          'HOSTED_SUBSCRIPTION' if cloud else 'PRIVATE_SSH_WORKER'),
                                vendor=(METERED_CLASSES if metered else ROUTE_CLASSES).get(row.get('route_class')),
                                # Hosted egress of either kind is never an automatic choice.
                                automatic=not hosted,
                                inventory_stage='INSTALLED', qualification='NOT_HAVEN_QUALIFIED',
                                digest_provenance='HOSTED_NOT_APPLICABLE' if hosted else 'WORKER_DECLARED',
                                features={'text': True, 'streaming': True,
                                'native_tools': 'DISABLED' if hosted else 'UNVERIFIED', 'vision': False,
                                'cancellation': ('REQUEST_CLOSE_STOPS_UPSTREAM' if metered else
                                                 'REQUEST_CLOSE_STOPS_CLI' if cloud else 'REQUEST_CLOSE_ONLY')},
                                cost_boundary=row.get('cost_boundary') if metered else None,
                                boundary_enforceable=(row.get('cost_boundary') in ENFORCEABLE_BOUNDARIES) if metered else None,
                                eligibility_evidence=row.get('eligibility_evidence') if metered else None,
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
        metered = row['kind'] == 'metered'
        hosted = cloud or metered
        if metered:
            boundary = row['cost_boundary']
            enforceable = boundary in ENFORCEABLE_BOUNDARIES
            evidence = row['eligibility_evidence']
            reason = (f"Explicit metered lane: this conversation left the house to "
                      f"{METERED_CLASSES[row['route_class']]} on its free allowance ({row['route_class']}). "
                      f"Spending ceiling: {boundary}"
                      + ('.' if enforceable else
                         ' -- this is NOT an enforceable boundary; if the allowance is exhausted this lane could bill.')
                      + f" Eligibility recorded {evidence['retrieved']} from {evidence['doc_url']}. "
                      'No tools; temperature/seed are not applied.')
        elif cloud:
            reason = (f"Explicit cloud lane: this conversation left the house to {ROUTE_CLASSES[row['route_class']]} "
                      f"under your own plan ({row['route_class']}). No tools, no API billing; "
                      'temperature/seed are not applied.')
        else:
            reason = 'Explicit owner-enrolled private worker; no hosted egress.'
        return {'base': row['base'], 'key': row['key'], 'model': row['model'],
                'socket_path': row['socket_path'], 'digest_provenance': 'HOSTED_NOT_APPLICABLE' if hosted else 'WORKER_DECLARED',
                'display_model': row['display_model'], 'kind': row['kind'], 'ownership': 'EXTERNAL',
                'provider_id': ident, 'worker_label': row['label'], 'node_id': row['node_id'],
                'compute': row['compute'], 'model_sha256': row.get('model_sha256'), 'route_class': row.get('route_class'),
                'cost_boundary': row.get('cost_boundary'), 'eligibility_evidence': row.get('eligibility_evidence'),
                # A free allowance is consumed per token, so a metered lane gets a tighter
                # output/history bound than a flat-rate plan lane.
                'profile': {'context': row['max_context_tokens'],
                            'max_output_tokens': 2048 if metered else 4096 if cloud else 1024,
                            'max_messages': 24 if metered else 40 if cloud else 8},
                'connected_at': row.get('enrolled_at', 0),
                'route_reason': reason}

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
            # Hosted egress is never an automatic choice -- subscription or metered free
            # allowance alike. Relaxing this for provably non-chargeable lanes is a separate
            # operator decision (METERED_ROUTE_PROPOSAL.md); it is deliberately not taken here.
            ids = sorted(i for i, row in self.entries.items() if row.get('kind') not in ('cloud', 'metered'))
        for ident in ids:
            try:
                conn = self.connection(ident)
                conn['route_reason'] = 'Automatic: ready owner-enrolled private worker while Slink is unavailable; no cloud fallback.'
                return conn
            except ValueError:
                pass
        raise ValueError('No eligible ready private text worker. Nothing was loaded and no paid fallback was attempted.')
