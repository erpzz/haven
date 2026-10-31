"""Ephemeral opt-in capability registry; heartbeats are NOT computation attestation."""
from __future__ import annotations
import hashlib
import hmac
import secrets
import threading
import time

MODEL = 'empero-ai/Qwythos-9B-v2'
ROLES = {'layer_inference', 'inference_rollout', 'training'}
BACKENDS = {'cuda', 'metal', 'cpu'}
TTL = 90.0

class RegistrationError(ValueError):
    pass


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


class Registry:
    def __init__(self, admin_token: str, *, clock=None):
        if len(admin_token) < 32:
            raise ValueError('Admin token must be at least 32 characters')
        self._admin = _digest(admin_token)
        self._clock = clock or time.monotonic
        self._lock = threading.RLock()
        self._invites = {}
        self._nodes = {}

    def _admin_check(self, token: str):
        if not isinstance(token, str) or not hmac.compare_digest(_digest(token), self._admin):
            raise PermissionError('Owner authorization required')

    def invite(self, admin_token: str, *, ttl_seconds: int = 600) -> str:
        self._admin_check(admin_token)
        if not isinstance(ttl_seconds, int) or not (30 <= ttl_seconds <= 3600):
            raise RegistrationError('Invite lifetime outside approved range')
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._invites[_digest(token)] = self._clock() + ttl_seconds
        return token

    def join(self, invite: str, declaration: dict) -> dict:
        if not isinstance(declaration, dict):
            raise RegistrationError('Invalid declaration')
        # Explicit whitelist prevents accidental publication/storage of IPs, user names,
        # credentials, machine IDs, paths, and arbitrary operator-provided metadata.
        allowed = {'consent', 'public', 'model', 'backend', 'vram_gib', 'roles'}
        if set(declaration) != allowed:
            raise RegistrationError('Declaration keys must match the minimal schema')
        if declaration['consent'] is not True or type(declaration['public']) is not bool:
            raise RegistrationError('Explicit consent and public visibility choice required')
        if declaration['model'] != MODEL or declaration['backend'] not in BACKENDS:
            raise RegistrationError('Unsupported model or backend')
        vram = declaration['vram_gib']
        if type(vram) is not int or not (0 <= vram <= 256):
            raise RegistrationError('Invalid VRAM declaration')
        roles = declaration['roles']
        if not isinstance(roles, list) or not roles or len(roles) > len(ROLES) or set(roles) - ROLES or len(set(roles)) != len(roles):
            raise RegistrationError('Invalid roles')
        if declaration['backend'] == 'cpu' and vram != 0:
            raise RegistrationError('CPU nodes must report zero GPU VRAM')
        if not isinstance(invite, str) or len(invite) > 128:
            raise PermissionError('Invalid invite')
        with self._lock:
            invite_hash = _digest(invite)
            deadline = self._invites.get(invite_hash)
            if deadline is None or deadline <= self._clock():
                raise PermissionError('Invitation invalid or expired')
            del self._invites[invite_hash]  # consume once
            node_id = 'hive_' + secrets.token_hex(12)
            node_token = secrets.token_urlsafe(32)
            self._nodes[node_id] = {
                'id': node_id, 'token_hash': _digest(node_token),
                'model': MODEL, 'backend': declaration['backend'],
                'vram_gib': vram, 'roles': sorted(roles),
                'public': declaration['public'], 'last_heartbeat': None,
                'available': False,
            }
        return {'node_id': node_id, 'node_token': node_token, 'heartbeat_ttl_seconds': TTL}

    def _auth_node(self, node_id: str, token: str) -> dict:
        node = self._nodes.get(node_id)
        if not node or not isinstance(token, str) or not hmac.compare_digest(_digest(token), node['token_hash']):
            raise PermissionError('Invalid worker credential')
        return node

    def heartbeat(self, node_id: str, node_token: str, *, available: bool) -> dict:
        if type(available) is not bool:
            raise RegistrationError('Availability must be boolean')
        with self._lock:
            node = self._auth_node(node_id, node_token)
            node['last_heartbeat'] = self._clock()
            node['available'] = available
        return {'accepted': True, 'node_id': node_id}

    def revoke(self, node_id: str, token: str) -> dict:
        with self._lock:
            self._auth_node(node_id, token)
            del self._nodes[node_id]
        return {'revoked': True, 'node_id': node_id}

    def public_nodes(self) -> dict:
        with self._lock:
            now = self._clock()
            rows = []
            for n in self._nodes.values():
                if not n['public'] or n['last_heartbeat'] is None or now - n['last_heartbeat'] > TTL:
                    continue
                rows.append({k: n[k] for k in ('id', 'model', 'backend', 'vram_gib', 'roles', 'available')})
        # 'available' is a self-reported heartbeat hint, not reserved compute or a verified job.
        return {'schema': 1, 'verification': 'SELF_DECLARED_NOT_ATTESTED', 'nodes': sorted(rows, key=lambda x: x['id'])}
