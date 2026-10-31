"""Constrained float32 activation transport. Loopback-only by design."""
from __future__ import annotations

import base64
import hmac
import ipaddress
import json
import os
from pathlib import Path
import stat
import struct
import urllib.error
import urllib.parse
import urllib.request

import torch

MAX_BODY = 2 * 1024 * 1024
MAX_ACTIVATION_BYTES = 512 * 512 * 4
HEADER = 'X-Hive-Secret'


class PeerError(RuntimeError):
    pass


def load_secret(path: str) -> str:
    p = Path(path)
    s = p.stat()
    if not stat.S_ISREG(s.st_mode) or (os.name == 'posix' and s.st_mode & 0o077):
        raise ValueError('Secret file must be a regular private mode-0600 file.')
    key = p.read_text(encoding='ascii').strip()
    if len(key) < 32 or len(key) > 256 or not key.isascii():
        raise ValueError('Expected a high-entropy HIVE secret (32-256 ASCII characters).')
    return key


def secret_matches(expected: str, actual: str) -> bool:
    return hmac.compare_digest(expected.encode(), actual.encode())


def peer_url(address: str) -> str:
    # Intentionally disallow remote endpoints, DNS, TLS assumptions and URL paths.
    if '://' not in address:
        address = 'http://' + address
    u = urllib.parse.urlsplit(address)
    if u.scheme != 'http' or u.username or u.password or u.path not in ('', '/') or u.query or u.fragment:
        raise ValueError('Peers must be plain loopback addresses (through SSH forwards).')
    try:
        ip = ipaddress.ip_address(u.hostname or '')
        port = u.port
    except ValueError as exc:
        raise ValueError('Only literal loopback IP peers are permitted.') from exc
    if not ip.is_loopback or not (1 <= (port or 0) <= 65535):
        raise ValueError('Only literal loopback IP peers are permitted.')
    return f'http://{u.netloc}'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise PeerError('Peer redirect denied.')


OPENER = urllib.request.build_opener(NoRedirect(), urllib.request.ProxyHandler({}))


def request(url: str, secret: str, path: str, data: dict | None = None, timeout=4.0):
    url = peer_url(url) + path
    body = None if data is None else json.dumps(data, separators=(',', ':'), allow_nan=False).encode()
    if body is not None and len(body) > MAX_BODY:
        raise PeerError('Activation request too large.')
    req = urllib.request.Request(url, data=body, method='GET' if body is None else 'POST',
                                 headers={HEADER: secret, 'Content-Type': 'application/json'})
    try:
        with OPENER.open(req, timeout=timeout) as reply:
            length = reply.headers.get('Content-Length')
            if length and int(length) > MAX_BODY:
                raise PeerError('Oversized response.')
            raw = reply.read(MAX_BODY + 1)
            if len(raw) > MAX_BODY:
                raise PeerError('Oversized response.')
            return json.loads(raw)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        raise PeerError(f'Peer unavailable or rejected request: {type(exc).__name__}') from exc


def encode(x: torch.Tensor) -> dict:
    if x.ndim != 2 or x.dtype != torch.float32:
        raise ValueError('Expected 2D float32 tensor.')
    rows, cols = x.shape
    if not (1 <= rows <= 512 and 8 <= cols <= 512) or rows * cols * 4 > MAX_ACTIVATION_BYTES:
        raise ValueError('Tensor shape exceeds limit.')
    with torch.no_grad():
        raw = x.detach().to('cpu').contiguous().numpy().tobytes()
    return {'shape': [rows, cols], 'data': base64.b64encode(raw).decode('ascii')}


def decode(obj: object, dim: int, max_context: int) -> torch.Tensor:
    if not isinstance(obj, dict) or not isinstance(obj.get('shape'), list):
        raise ValueError('Missing activation shape.')
    shape = obj['shape']
    if len(shape) != 2 or type(shape[0]) is not int or type(shape[1]) is not int:
        raise ValueError('Invalid shape.')
    if not (1 <= shape[0] <= max_context and shape[1] == dim and shape[0] * dim * 4 <= MAX_ACTIVATION_BYTES):
        raise ValueError('Activation shape mismatch or exceeds bounds.')
    data = obj.get('data')
    if not isinstance(data, str) or len(data) > (MAX_ACTIVATION_BYTES * 4 // 3 + 10):
        raise ValueError('Invalid activation content.')
    try:
        raw = base64.b64decode(data, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError('Invalid base64.') from exc
    if len(raw) != shape[0] * dim * 4:
        raise ValueError('Activation byte size mismatch.')
    result = torch.frombuffer(bytearray(raw), dtype=torch.float32).reshape(shape).clone()
    if not bool(torch.isfinite(result).all()):
        raise ValueError('Nonfinite activations denied.')
    return result
