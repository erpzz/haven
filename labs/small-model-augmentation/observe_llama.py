"""Fail-closed runtime observations for a dedicated loopback llama-server.

The observer reads only the local server's model inventory and effective context.
It never trusts model-generated text and never follows redirects.
"""
import argparse
import json
import socket
import urllib.error
import urllib.parse
import urllib.request

import preflight

MAX_RESPONSE_BYTES = 65_536
TIMEOUT_SECONDS = 2.0


class ObservationError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def canonical_base_url(value):
    if type(value) is not str:
        raise ObservationError("INVALID_BASE_URL")
    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
    except ValueError:
        raise ObservationError("INVALID_BASE_URL") from None
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or port is None
            or not 1 <= port <= 65535 or parsed.username is not None or parsed.password is not None
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        raise ObservationError("INVALID_BASE_URL")
    return f"http://127.0.0.1:{port}"


def _read_json(url, error_code):
    request = urllib.request.Request(url, headers={"Accept": "application/json", "Connection": "close"})
    try:
        with OPENER.open(request, timeout=TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise ObservationError(error_code)
            length = response.headers.get("Content-Length")
            if length is not None:
                try:
                    if int(length) > MAX_RESPONSE_BYTES:
                        raise ObservationError(error_code)
                except ValueError:
                    raise ObservationError(error_code) from None
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except ObservationError:
        raise
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, socket.timeout, OSError, ValueError):
        raise ObservationError(error_code) from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ObservationError(error_code)
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=preflight.unique_object)
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise ObservationError(error_code) from None
    if type(value) is not dict:
        raise ObservationError(error_code)
    return value


def _model_ids(base):
    payload = _read_json(base + "/v1/models", "MODELS_OBSERVATION_FAILED")
    data = payload.get("data")
    if type(data) is not list or not data:
        raise ObservationError("MODELS_SCHEMA_INVALID")
    ids = []
    for item in data:
        if type(item) is not dict or not preflight.valid_id(item.get("id")):
            raise ObservationError("MODELS_SCHEMA_INVALID")
        ids.append(item["id"])
    return ids


def _context(base):
    payload = _read_json(base + "/props", "PROPS_OBSERVATION_FAILED")
    settings = payload.get("default_generation_settings")
    if type(settings) is not dict:
        raise ObservationError("PROPS_SCHEMA_INVALID")
    n_ctx = settings.get("n_ctx")
    if type(n_ctx) is not int or n_ctx <= 0:
        raise ObservationError("PROPS_SCHEMA_INVALID")
    return n_ctx


def observe(base_url):
    base = canonical_base_url(base_url)
    before = _model_ids(base)
    context = _context(base)
    after = _model_ids(base)
    if before != after:
        raise ObservationError("SERVER_CHANGED_DURING_CHECK")
    return before, context


def check_runtime(expected_model, requested_model, base_url):
    if not preflight.valid_id(expected_model):
        return preflight.receipt(["INVALID_EXPECTED_MODEL"])
    if not preflight.valid_id(requested_model):
        return preflight.receipt(["INVALID_REQUESTED_MODEL"])
    try:
        model_ids, context = observe(base_url)
    except ObservationError as exc:
        return preflight.receipt([exc.code])
    result = preflight.check({"expected_model": expected_model,
                              "requested_model": requested_model,
                              "observed_model_ids": model_ids,
                              "observed_context_tokens": context})
    result["live_endpoint_verified"] = result["status"] == "pass"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fail-closed admission check for a loopback llama-server")
    parser.add_argument("--expected-model", required=True)
    parser.add_argument("--requested-model", required=True)
    parser.add_argument("--base-url", required=True, help="root URL only, e.g. http://127.0.0.1:8091")
    args = parser.parse_args(argv)
    result = check_runtime(args.expected_model, args.requested_model, args.base_url)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
