"""Principal-bound, OpenAI-compatible inference gateway for chat frontends.

Open WebUI (or any OpenAI client) talks to `/v1/*` on the loopback Lab. The
gateway is a *client of the Lab*: it calls `Lab.generate`, so routing, worker
enrollment, the one-GPU generation slot, hosted-egress acknowledgment, the
context check, cancellation and metrics are the same code the Lab UI uses. It
never opens a backend connection or reads a worker credential itself.

Credentials live in `<data>/gateway-keys.json` (owned, mode 0600), stored only
as SHA-256 digests:
  {"keys": [{"sha256": "...", "principal": "open-webui", "role": "frontend"},
            {"sha256": "...", "principal": "owner-cli",  "role": "owner"}]}
A `frontend` key is a delegated identity: the frontend authenticates its own
users and forwards `X-OpenWebUI-User-*`. Its `admin` users map to Haven
`owner`, its `user` accounts to Haven `member`; anything else is refused. Only
the frontend process holds that key, so a household member cannot forge a role.

Members reach the Slink runtime only. Enrolled workers and hosted lanes are
owner-only; hosted lanes additionally need per-chat consent (`/haven consent`)
before any message leaves the house. Receipts record routing and metrics, never
prompt or response text.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import stat
import threading
import time
import urllib.parse

from labcore import estimate_prompt_tokens

KEYS_FILE = 'gateway-keys.json'
JWT_SECRET_FILE = 'gateway-frontend-jwt.secret'  # Shared with Open WebUI's FORWARD_USER_INFO_HEADER_JWT_SECRET
JWT_HEADER = 'X-OpenWebUI-User-Jwt'
RECEIPTS_FILE = 'gateway-receipts.jsonl'
CONSENT_COMMAND = '/haven consent'
STATUS_COMMAND = '/haven status'
DEFAULT_OUTPUT_CAP = 16384     # Default reply budget when the client sends none.
MIN_OUTPUT = 256               # Below this the chat is too long for the loaded context.
QUEUE_WAIT_S = 180             # One GPU slot; a queued request waits this long, then reports BUSY.
OWUI_ROLES = {'admin': 'owner', 'user': 'member'}
ID_RE = re.compile(r'[A-Za-z0-9_.@:+-]{1,128}')


class GatewayError(Exception):
    def __init__(self, status: int, message: str, code: str = 'haven_policy'):
        super().__init__(message)
        self.status, self.message, self.code = status, message, code

    def body(self) -> dict:
        return {'error': {'message': self.message, 'type': self.code, 'code': self.code}}


def verify_hs256(token: str, secret: bytes) -> dict:
    """Minimal HS256 JWT check (signature, alg, exp, issuer). Raises GatewayError on any doubt."""
    def b64(part):
        return base64.urlsafe_b64decode(part + '=' * (-len(part) % 4))
    try:
        head, body, sig = token.split('.')
        header, claims = json.loads(b64(head)), json.loads(b64(body))
        expected = hmac.new(secret, f'{head}.{body}'.encode(), hashlib.sha256).digest()
        valid = (header.get('alg') == 'HS256' and hmac.compare_digest(expected, b64(sig))
                 and claims.get('iss') == 'open-webui' and type(claims.get('exp')) in (int, float)
                 and claims['exp'] > time.time())
    except (ValueError, TypeError, AttributeError):
        valid = False
    if not valid:
        raise GatewayError(403, 'The frontend identity token is missing, invalid or expired.', 'forbidden')
    return claims


def flatten_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if not isinstance(part, dict) or part.get('type') != 'text' or not isinstance(part.get('text'), str):
                raise GatewayError(400, 'Haven text models accept text only; images and files are not sent. '
                                        'Attach files as text or use a vision-capable worker when one is enrolled.')
            parts.append(part['text'])
        return '\n'.join(parts)
    if content is None:
        return ''
    raise GatewayError(400, 'Unsupported message content.')


def model_id(provider_id: str) -> str:
    return {'managed': 'haven-slink', 'auto': 'haven-auto'}.get(provider_id, 'haven-' + provider_id)


class Gateway:
    def __init__(self, lab, data: Path):
        self.lab = lab
        self.data = Path(data)
        self.lock = threading.RLock()
        self.consent = {}      # (principal_id, chat_id, provider_id) -> granted_at
        self.keys = self._load_keys()

    # ---- credentials -------------------------------------------------------
    def _load_keys(self) -> dict:
        path = self.data / KEYS_FILE
        try:
            fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        except FileNotFoundError:
            return {}
        with os.fdopen(fd) as f:
            info = os.fstat(f.fileno())
            if not stat.S_ISREG(info.st_mode) or (os.name != 'nt' and (info.st_uid != os.getuid() or info.st_mode & 0o077)):
                raise ValueError('gateway-keys.json must be an owned mode-0600 file.')
            rows = json.load(f).get('keys', [])
        keys = {}
        for row in rows:
            digest, role, principal = row.get('sha256', ''), row.get('role'), row.get('principal', '')
            if (not re.fullmatch(r'[0-9a-f]{64}', digest) or role not in ('frontend', 'owner', 'member')
                    or not ID_RE.fullmatch(principal)):
                raise ValueError('Invalid gateway key entry.')
            keys[digest] = {'principal': principal, 'role': role}
        return keys

    @staticmethod
    def issue_key(data: Path, principal: str, role: str) -> str:
        """Create a key, store only its digest, return the secret once."""
        if role not in ('frontend', 'owner', 'member') or not ID_RE.fullmatch(principal):
            raise ValueError('Invalid principal or role.')
        path = Path(data) / KEYS_FILE
        rows = json.loads(path.read_text()).get('keys', []) if path.exists() else []
        rows = [r for r in rows if r.get('principal') != principal]
        key = 'hvn-' + secrets.token_urlsafe(32)
        rows.append({'sha256': hashlib.sha256(key.encode()).hexdigest(), 'principal': principal, 'role': role,
                     'issued_at': time.time()})
        tmp = path.with_suffix('.tmp')
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as f:
            json.dump({'keys': rows}, f, indent=1)
        os.replace(tmp, path)
        return key

    def _lookup(self, digest: str):
        with self.lock:
            return next((v for k, v in self.keys.items() if hmac.compare_digest(k, digest)), None)

    def authenticate(self, headers) -> dict:
        auth = headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            raise GatewayError(401, 'Haven gateway key required.', 'unauthorized')
        digest = hashlib.sha256(auth[7:].strip().encode()).hexdigest()
        # Always consult the current digest registry, even for a previously valid key.
        # Refresh-on-miss alone leaves revoked/rotated keys valid indefinitely.
        # The registry is tiny, private and atomically replaced by issue_key().
        with self.lock:
            self.keys = self._load_keys()
            entry = self._lookup(digest)
        if not entry:
            raise GatewayError(401, 'Unknown Haven gateway key.', 'unauthorized')
        if entry['role'] != 'frontend':
            return {'id': entry['principal'], 'name': entry['principal'], 'role': entry['role'], 'via': 'direct-key'}
        secret = self._jwt_secret()
        if not secret:
            # Never turn loss of the signing secret into authorization by unsigned role headers.
            raise GatewayError(503, 'Frontend identity verification is not configured.', 'unavailable')
        # Signed identity: holding the frontend key alone cannot claim another user's role.
        claims = verify_hs256(headers.get(JWT_HEADER, ''), secret)
        uid, role_name, name = claims.get('sub', ''), claims.get('role', ''), claims.get('name', '')
        role = OWUI_ROLES.get(role_name)
        if not isinstance(uid, str) or not ID_RE.fullmatch(uid) or not role:
            raise GatewayError(403, 'The frontend did not identify an approved user; pending accounts cannot chat.', 'forbidden')
        return {'id': f"{entry['principal']}:{uid}", 'name': str(name)[:80], 'role': role, 'via': entry['principal']}

    def _jwt_secret(self) -> bytes | None:
        path = self.data / JWT_SECRET_FILE
        try:
            fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        except FileNotFoundError:
            return None
        with os.fdopen(fd, 'rb') as f:
            info = os.fstat(f.fileno())
            if not stat.S_ISREG(info.st_mode) or (os.name != 'nt' and (info.st_uid != os.getuid() or info.st_mode & 0o077)):
                raise GatewayError(503, 'The frontend identity secret must be an owned mode-0600 file.', 'unavailable')
            secret = f.read(512).strip()
        if len(secret) < 32:
            raise GatewayError(503, 'The frontend identity secret is too short.', 'unavailable')
        return secret

    # ---- discovery ---------------------------------------------------------
    def _managed(self) -> tuple[dict, str]:
        with self.lab.lock:
            conn = dict(self.lab.connection or {})
            engine = self.lab.engine.status()
        if conn:
            return conn, 'READY' if conn.get('ownership') == 'EXTERNAL' or engine.get('state') == 'READY' else engine.get('state', 'UNKNOWN')
        return conn, engine.get('state', 'STOPPED') if engine.get('state') not in (None, 'STOPPED') else 'NO_MODEL_LOADED'

    def listing(self, principal: dict) -> list[dict]:
        """`/v1/models`. Open WebUI caches one base-model list for every account, so a frontend
        gets the full catalog and hides entries with its own access control; dispatch below is
        still checked against the requesting user's Haven role."""
        if principal['via'] != 'direct-key':
            return self.models({**principal, 'role': 'owner'})
        return self.models(principal)

    def models(self, principal: dict) -> list[dict]:
        conn, state = self._managed()
        context = (conn.get('profile') or {}).get('context')
        label = conn.get('display_model') or conn.get('model') or 'no model loaded'
        rows = [
            {'id': 'haven-slink', 'object': 'model', 'owned_by': 'haven', 'created': 0,
             'name': f'Slink · {label}' + ('' if state == 'READY' else f' · {state}'),
             'haven': {'provider_id': 'managed', 'state': state, 'context': context, 'compute': conn.get('compute'),
                       'egress': 'NONE', 'model_sha256': conn.get('model_sha256'), 'route_type': 'managed_alias'}},
            {'id': 'haven-auto', 'object': 'model', 'owned_by': 'haven', 'created': 0,
             'name': 'Haven · Automatic (private machines only)',
             'haven': {'provider_id': 'auto', 'egress': 'NONE', 'route_type': 'automatic_alias'}},
        ]
        if principal['role'] != 'owner':
            return rows[:1]
        for row in self.lab.providers.snapshot():
            cloud = row['kind'] == 'cloud'
            seen = row['observed'].get('state', 'UNKNOWN')
            rows.append({'id': model_id(row['id']), 'object': 'model', 'owned_by': 'haven', 'created': 0,
                         'name': (f"External · {row['display_model']} (consent required)" if cloud else
                                  f"{row['label']} · {row['display_model']}") + (f' · {seen}' if seen not in ('READY',) else ''),
                         'haven': {'provider_id': row['id'], 'state': seen, 'context': row['max_context_tokens'],
                                   'compute': row['compute'], 'egress': row.get('locality'),
                                   'vendor': row.get('vendor'), 'model_sha256': row.get('model_sha256'),
                                   'route_type': 'provider'}})
        return rows

    def provider_for(self, principal: dict, requested: str) -> str:
        allowed = {m['id']: m['haven']['provider_id'] for m in self.models(principal)}
        if requested not in allowed:
            raise GatewayError(404 if principal['role'] == 'owner' else 403,
                               f'Model {requested!r} is not available to this account.', 'model_not_found')
        return allowed[requested]

    def status(self, principal: dict) -> dict:
        state = self.lab.public_state()
        conn, engine_state = self._managed()
        out = {'principal': {'name': principal['name'], 'role': principal['role']},
               'slink': {'state': engine_state, 'model': conn.get('display_model') or conn.get('model'),
                         'context': (conn.get('profile') or {}).get('context'), 'compute': conn.get('compute'),
                         'generation_busy': self.lab.generation.locked()},
               'hardware': {k: state['hardware'].get(k) for k in ('gpus', 'ram_total_gib', 'ram_available_gib')},
               'gpu_peers': state.get('prepared_runtime', {}).get('peer_units') or [],
               'observed_at': time.time()}
        if principal['role'] == 'owner':
            out['workers'] = [{'id': r['id'], 'label': r['label'], 'model': r['display_model'], 'state': r['observed']['state'],
                               'egress': r['locality']} for r in state.get('providers', [])]
        return out

    # ---- chat --------------------------------------------------------------
    def prepare(self, principal: dict, body: dict, headers) -> dict:
        """Validate an OpenAI request into Lab.generate arguments, or return a local consent reply."""
        if not isinstance(body, dict):
            raise GatewayError(400, 'JSON object required.')
        provider_id = self.provider_for(principal, str(body.get('model', '')))
        if body.get('functions'):
            raise GatewayError(400, 'Legacy `functions` are not supported; send OpenAI `tools`.')
        if body.get('n', 1) != 1:
            raise GatewayError(400, 'Only one completion per request.')
        raw = body.get('messages')
        if not isinstance(raw, list) or not raw:
            raise GatewayError(400, 'Supply messages.')
        messages = []
        for m in raw:
            if not isinstance(m, dict) or m.get('role') not in ('system', 'user', 'assistant', 'tool'):
                raise GatewayError(400, 'Only system, user, assistant and tool messages are accepted.')
            # Tool calls run in the frontend under its own per-user permissions; Haven relays them
            # and their results as structured messages and records the count in the receipt.
            out = {'role': m['role'], 'content': flatten_content(m.get('content'))}
            for key in ('tool_calls', 'tool_call_id'):
                if m.get(key) is not None:
                    out[key] = m[key]
            messages.append(out)
        chat_id = headers.get('X-OpenWebUI-Chat-Id', '')
        last = messages[-1]['content'].strip() if messages[-1]['role'] == 'user' else ''
        if last.lower() == STATUS_COMMAND:
            return {'local_reply': format_status(self.status(principal))}
        provider = None
        if provider_id not in ('managed', 'auto'):
            provider = next((r for r in self.lab.providers.snapshot() if r['id'] == provider_id), None)
        cloud = bool(provider and provider['kind'] == 'cloud')
        if last.lower() == CONSENT_COMMAND:
            if not cloud:
                return {'local_reply': 'This model runs on your own machines; nothing leaves the house, so no consent is needed.'}
            if not ID_RE.fullmatch(chat_id):
                raise GatewayError(400, 'Consent is recorded per chat, and this request carried no chat identity.')
            with self.lock:
                self.consent[(principal['id'], chat_id, provider_id)] = time.time()
            return {'local_reply': (f"Consent recorded for this chat only. Messages in this conversation may now be sent to "
                                    f"{provider.get('vendor')} through your {provider.get('route_class')} lane. "
                                    "Nothing has been sent yet. Ask your question again.")}
        # The consent command itself is a control message, not conversation content.
        messages = [m for m in messages if not (m['role'] == 'user' and m['content'].strip().lower() == CONSENT_COMMAND)]
        egress_ack = None
        if cloud:
            with self.lock:
                granted = ID_RE.fullmatch(chat_id) and (principal['id'], chat_id, provider_id) in self.consent
            if not granted:
                return {'local_reply': (f"This model is hosted by {provider.get('vendor')}. Using it sends this whole "
                                        "conversation outside your house. Nothing was sent. To allow it for this chat only, "
                                        f"send exactly: {CONSENT_COMMAND}")}
            egress_ack = 'HOSTED_SUBSCRIPTION'
        conn, _ = self._managed()
        context = (conn.get('profile') or {}).get('context') if provider_id in ('managed', 'auto') else (provider or {}).get('max_context_tokens')
        tools = body.get('tools') or None
        prompt = estimate_prompt_tokens(messages, tools)
        requested = body.get('max_completion_tokens', body.get('max_tokens'))
        if requested is None:
            room = (context - prompt - 64) if context else 2048
            if room < MIN_OUTPUT:
                raise GatewayError(400, f'This chat (~{prompt} tokens) leaves under {MIN_OUTPUT} tokens of the loaded '
                                        f'{context}-token context. Start a new chat, or load the model with a larger context.')
            requested = min(DEFAULT_OUTPUT_CAP, room)
        effort = body.get('reasoning_effort', 'none')
        if effort not in ('none', 'low', 'medium', 'high'):
            effort = 'none'
        return {'request': {'messages': messages, 'max_tokens': requested,
                            'temperature': body.get('temperature', .7), 'top_p': body.get('top_p', .8),
                            'seed': body.get('seed', secrets.randbelow(2**31)), 'reasoning': effort,
                            'provider_id': provider_id, 'egress_ack': egress_ack, 'label': 'gateway',
                            'tools': tools, 'tools_optional': True},
                'principal': principal, 'chat_id': chat_id, 'prompt_estimate': prompt,
                'requested_model_id': str(body.get('model', ''))}

    def start(self, prepared: dict, cancelled=lambda: False) -> str:
        """Dispatch through the Lab, waiting for the single generation slot."""
        deadline = time.monotonic() + QUEUE_WAIT_S
        while True:
            if cancelled():
                raise GatewayError(499, 'Client closed the request while queued; nothing was sent.', 'cancelled')
            try:
                return self.lab.generate(prepared['request'])
            except ValueError as exc:
                busy = 'One request at a time' in str(exc)
                if not busy:
                    raise GatewayError(400, str(exc)) from None
                if time.monotonic() > deadline:
                    raise GatewayError(429, 'Haven is busy with another request on this GPU; nothing was sent. '
                                            'Try again shortly.', 'busy') from None
            time.sleep(.25)

    def routing_trace(self, prepared: dict, job: dict) -> dict:
        """Observable decision facts only; never claim a model switch or verified weights without evidence.

        The selected OpenAI model id is a route selector, often *not* an artifact.
        The Lab job records the resolved provider and reported model after admission.
        Backend weight identity cannot be independently attested by this gateway.
        """
        return {
            'requested': {'selector': prepared.get('requested_model_id'),
                          'provider_id': prepared['request'].get('provider_id')},
            'resolved': {'provider_id': job.get('provider_id'), 'worker': job.get('worker_label'),
                         'reported_model': job.get('model'), 'model_sha256': job.get('model_sha256'),
                         'digest_provenance': job.get('digest_provenance'), 'compute': job.get('compute'),
                         'egress': job.get('egress')},
            'execution': {'job_id': job.get('id'), 'state': job.get('state'),
                          'finish_reason': job.get('finish_reason'),
                          'tools_dropped': job.get('tools_dropped')},
            'selection_reason': job.get('route_reason'),
            'fallback': 'UNDETERMINED',  # no recorded event chain exists yet
            'identity_attestation': 'NOT_VERIFIED',
        }

    def receipt(self, prepared: dict, job: dict):
        principal = prepared['principal']
        row = {'at': time.time(), 'job': job.get('id'), 'state': job.get('state'),
               'principal': hashlib.sha256(principal['id'].encode()).hexdigest()[:16], 'role': principal['role'],
               'via': principal['via'], 'requested_model_id': prepared.get('requested_model_id'),
               'provider_id': job.get('provider_id'), 'worker': job.get('worker_label'),
               'model': job.get('model'), 'model_sha256': job.get('model_sha256'),
               'compute': job.get('compute'), 'egress': job.get('egress'),
               'finish_reason': job.get('finish_reason'), 'max_tokens': prepared['request']['max_tokens'],
               'prompt_estimate': prepared['prompt_estimate'], 'metrics': job.get('metrics'),
               'error': job.get('error'), 'route_reason': job.get('route_reason'),
               'tools_offered': job.get('tools_offered'), 'tools_dropped': job.get('tools_dropped'),
               'tool_calls': [c['function']['name'] for c in job.get('tool_calls') or []]}
        try:
            with self.lock:
                fd = os.open(self.data / RECEIPTS_FILE, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
                with os.fdopen(fd, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(row) + '\n')
        except OSError:
            pass

    def completion_chunk(self, cid: str, model: str, delta: dict, finish=None) -> dict:
        return {'id': cid, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': model,
                'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}

    def stream(self, job, write, model: str):
        """Relay a Lab job as OpenAI SSE. A failed write cancels the job (browser Stop)."""
        cid = 'chatcmpl-' + job.id
        sent_text = sent_reasoning = 0
        sent_calls = []  # per index: (id/name announced, argument characters sent)
        try:
            while True:
                snap = job.snapshot()
                text, reasoning = snap.get('text', ''), snap.get('reasoning', '')
                delta = {}
                if len(reasoning) > sent_reasoning:
                    delta['reasoning_content'] = reasoning[sent_reasoning:]; sent_reasoning = len(reasoning)
                if len(text) > sent_text:
                    delta['content'] = text[sent_text:]; sent_text = len(text)
                calls = []
                for i, call in enumerate(snap.get('tool_calls') or []):
                    if i == len(sent_calls):
                        if not (call['id'] and call['function']['name']):
                            break  # Announce a call only once its id and name are known.
                        sent_calls.append(0)
                        calls.append({'index': i, 'id': call['id'], 'type': 'function',
                                      'function': {'name': call['function']['name'], 'arguments': ''}})
                    args = call['function']['arguments']
                    if len(args) > sent_calls[i]:
                        part = {'index': i, 'function': {'arguments': args[sent_calls[i]:]}}
                        sent_calls[i] = len(args)
                        if calls and calls[-1]['index'] == i:
                            calls[-1]['function']['arguments'] = part['function']['arguments']
                        else:
                            calls.append(part)
                if calls:
                    delta['tool_calls'] = calls
                if delta:
                    write(self.completion_chunk(cid, model, delta))
                if snap['state'] != 'RUNNING':
                    break
                time.sleep(.05)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            job.cancel()
            raise
        return job.snapshot()

    @staticmethod
    def settle(job, timeout: float = 10) -> dict:
        end = time.monotonic() + timeout
        while job.snapshot()['state'] == 'RUNNING' and time.monotonic() < end:
            time.sleep(.05)
        return job.snapshot()

    def finish_blocking(self, job_id: str) -> dict:
        job = self.lab.jobs[job_id]
        while job.snapshot()['state'] == 'RUNNING':  # The Lab watchdog bounds this wait.
            time.sleep(.1)
        return job.snapshot()


def openai_finish(snap: dict) -> str:
    if snap.get('state') == 'OUTPUT_LIMIT':
        return 'length'
    return 'tool_calls' if snap.get('finish_reason') == 'tool_calls' else 'stop'


def format_status(st: dict) -> str:
    """Plain-text runtime report for `/haven status`; observed values only, unknowns say so."""
    slink, hw = st['slink'], st['hardware']
    lines = [f"**Slink** · {slink['model'] or 'no model loaded'} · {slink['state']}"
             + (f" · {slink['context']:,}-token context" if slink.get('context') else '')
             + (f" · {slink['compute']}" if slink.get('compute') else '')
             + (' · generating now' if slink['generation_busy'] else '')]
    for g in hw.get('gpus') or []:
        lines.append(f"GPU {g.get('name')}: {g.get('memory_used_mib')} / {g.get('memory_total_mib')} MiB, "
                     f"{g.get('utilization_pct')}% busy, {g.get('temperature_c')} °C")
    if hw.get('ram_available_gib') is not None:
        lines.append(f"RAM: {hw['ram_available_gib']:.1f} GiB available of {hw['ram_total_gib']:.1f} GiB")
    if st.get('gpu_peers'):
        lines.append('GPU held by: ' + ', '.join(st['gpu_peers']) + ' (no model loads until it finishes)')
    for w in st.get('workers') or []:
        lines.append(f"Worker {w['label']} · {w['model']} · {w['state']}" + (' · leaves the house' if w['egress'] == 'HOSTED_SUBSCRIPTION' else ''))
    lines.append(f"You are signed in as {st['principal']['name'] or 'this account'} ({st['principal']['role']}).")
    return '\n\n'.join(lines)


def usage(snap: dict) -> dict | None:
    m = snap.get('metrics') or {}
    if m.get('completion_tokens') is None:
        return None
    prompt = m.get('prompt_tokens') if type(m.get('prompt_tokens')) is int else 0
    return {'prompt_tokens': prompt, 'completion_tokens': m['completion_tokens'],
            'total_tokens': prompt + m['completion_tokens']}
