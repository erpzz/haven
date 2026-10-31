"""Constrained synchronous distributed inference coordinator."""
from __future__ import annotations

import json
import time

import torch

from .model import Endpoints, Spec, validate_prompt
from .wire import PeerError, decode, encode, request, peer_url


class Cluster:
    def __init__(self, spec: Spec, peers: list[str], secret: str, timeout=4.0):
        spec.validate()
        if not peers or len(peers) > spec.layers:
            raise ValueError('Use 1..number-of-layers workers.')
        self.spec, self.peers, self.secret, self.timeout = spec, [peer_url(p) for p in peers], secret, timeout
        if len(set(self.peers)) != len(self.peers):
            raise ValueError('Duplicate peer endpoint.')
        self.ends = Endpoints(spec)
        self.layout = self.preflight()

    def preflight(self):
        layout = []
        for peer in self.peers:
            m = request(peer, self.secret, '/meta', timeout=self.timeout)
            if not isinstance(m, dict) or m.get('protocol') != 1 or m.get('model_id') != self.spec.identity or m.get('dtype') != 'float32':
                raise PeerError('Peer model/protocol mismatch.')
            start, stop = m.get('start'), m.get('stop')
            if type(start) is not int or type(stop) is not int or not (0 <= start < stop <= self.spec.layers):
                raise PeerError('Peer reported invalid layer range.')
            layout.append((start, stop, peer))
        layout.sort()
        if layout[0][0] != 0 or layout[-1][1] != self.spec.layers or any(a[1] != b[0] for a, b in zip(layout, layout[1:])):
            raise PeerError('Shard coverage must be exact, contiguous, nonoverlapping.')
        return layout

    @torch.inference_mode()
    def generate(self, prompt: bytes, count: int):
        validate_prompt(self.spec, prompt, count)
        ids = list(prompt)
        generated = []
        timings = []
        traffic = 0
        started = time.monotonic()
        for _ in range(count):
            x = self.ends.embed(ids).to(torch.float32)
            hops = []
            for start, stop, peer in self.layout:
                data = {'model_id': self.spec.identity, 'start': start, 'stop': stop, 'activation': encode(x)}
                # Estimate JSON payload+response bytes for application-level traffic, not IP overhead.
                out_bytes = len(json.dumps(data, separators=(',', ':')).encode())
                tick = time.monotonic()
                response = request(peer, self.secret, '/forward', data, timeout=self.timeout)
                elapsed = (time.monotonic() - tick) * 1000
                if not isinstance(response, dict) or response.get('model_id') != self.spec.identity or response.get('start') != start or response.get('stop') != stop:
                    raise PeerError('Peer returned incorrect model or range.')
                x = decode(response.get('activation'), self.spec.dim, self.spec.context)
                in_bytes = len(json.dumps(response, separators=(',', ':')).encode())
                traffic += out_bytes + in_bytes
                hops.append({'range': [start, stop], 'roundtrip_ms': round(elapsed, 3),
                             'worker_compute_ms': response.get('compute_ms'),
                             'application_bytes': out_bytes + in_bytes})
            next_id = self.ends.predict(x)
            ids.append(next_id)
            generated.append(next_id)
            timings.append(hops)
        elapsed = (time.monotonic() - started) * 1000
        return {'status': 'COMPLETED', 'model_kind': 'random_initialized_transformer_not_a_trained_llm',
                'model_id': self.spec.identity, 'prompt_bytes': len(prompt), 'tokens': generated,
                'output_hex': bytes(generated).hex(), 'elapsed_ms': round(elapsed, 3),
                'tokens_per_second': round(len(generated) / (elapsed / 1000), 3) if elapsed else None,
                'application_bytes': traffic, 'hops': timings,
                'nodes': [{'range': [a, b], 'peer': p} for a, b, p in self.layout]}
