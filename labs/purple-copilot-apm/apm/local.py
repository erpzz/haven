"""Loopback-only HTTP. No ambient proxies, cookies or redirects."""
import http.client
import json
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


def request(port, method, path, body=None, headers=None, timeout=90):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        conn.request(method, path, body, headers or {})
        response = conn.getresponse()
        data = response.read()
        if not 200 <= response.status < 300:
            raise RuntimeError(f"{method} {path} returned HTTP {response.status}")
        return json.loads(data) if data else {}
    finally:
        conn.close()
