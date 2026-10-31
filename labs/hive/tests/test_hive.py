"""Actual subprocess + HTTP transport integration, plus defensive negatives."""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

# From any working directory, use the intended independently installable lab.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hive.cluster import Cluster
from hive.model import Endpoints, Segment, Spec, baseline
from hive.wire import PeerError, decode, encode, load_secret, peer_url, request

import torch


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class HiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.key_file = Path(self.temp.name) / 'key'
        self.key_file.write_text('q' * 48 + '\n')
        os.chmod(self.key_file, 0o600)
        self.key = load_secret(str(self.key_file))
        self.spec = Spec(layers=4, dim=32, heads=4, context=32)
        self.procs = []
        self.addCleanup(self.terminate_all)

    def terminate_all(self):
        for p in self.procs:
            if p.poll() is None:
                p.terminate()
        for p in self.procs:
            try:
                p.communicate(timeout=4)
            except subprocess.TimeoutExpired:
                p.kill()
                p.communicate(timeout=3)

    def worker(self, start, stop, *, seed=None):
        port = free_port()
        p = subprocess.Popen([sys.executable, '-m', 'hive', 'worker',
                              '--secret-file', str(self.key_file), '--port', str(port),
                              '--start', str(start), '--stop', str(stop),
                              '--layers', str(self.spec.layers), '--dim', str(self.spec.dim),
                              '--heads', str(self.spec.heads), '--context', str(self.spec.context),
                              '--seed', str(self.spec.seed if seed is None else seed)],
                             cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        self.procs.append(p)
        peer = f'127.0.0.1:{port}'
        for _ in range(120):
            if p.poll() is not None:
                raise AssertionError('Worker process exited early: ' + (p.stderr.read() or '')[-1000:])
            try:
                request(peer, self.key, '/meta', timeout=0.3)
                return peer
            except PeerError:
                time.sleep(0.05)
        raise AssertionError('Worker did not bind within 6s')

    def test_true_cross_process_partition_equals_monolith(self):
        a = self.worker(0, 2)
        b = self.worker(2, 4)
        distributed = Cluster(self.spec, [b, a], self.key).generate(b'Hive', 4)
        mono = baseline(self.spec, b'Hive', 4)
        self.assertEqual(distributed['tokens'], mono)
        self.assertEqual(distributed['status'], 'COMPLETED')
        self.assertEqual(len(distributed['hops']), 4)
        self.assertEqual(len(distributed['hops'][0]), 2)
        self.assertGreater(distributed['application_bytes'], 0)
        self.assertEqual([n['range'] for n in distributed['nodes']], [[0, 2], [2, 4]])
        self.assertEqual(request(a, self.key, '/meta')['completed_forwards'], 4)
        self.assertEqual(request(b, self.key, '/meta')['completed_forwards'], 4)

    def test_reject_gap_and_overlap(self):
        a = self.worker(0, 2)
        c = self.worker(3, 4)
        with self.assertRaisesRegex(PeerError, 'coverage'):
            Cluster(self.spec, [a, c], self.key)
        b = self.worker(1, 4)
        with self.assertRaisesRegex(PeerError, 'coverage'):
            Cluster(self.spec, [a, b], self.key)

    def test_reject_wrong_model_version(self):
        a = self.worker(0, 2)
        b = self.worker(2, 4, seed=self.spec.seed + 1)
        with self.assertRaisesRegex(PeerError, 'mismatch'):
            Cluster(self.spec, [a, b], self.key)

    def test_deny_unauthorized(self):
        a = self.worker(0, 4)
        with self.assertRaises(PeerError):
            request(a, 'wrong-secret', '/meta')
        with self.assertRaises(PeerError):
            request(a, '', '/forward', {'bogus': 1})
        self.assertEqual(request(a, self.key, '/meta')['completed_forwards'], 0)

    def test_peer_loss_fails_closed(self):
        a = self.worker(0, 2)
        b = self.worker(2, 4)
        cluster = Cluster(self.spec, [a, b], self.key, timeout=0.3)
        self.procs[-1].terminate()
        self.procs[-1].wait(timeout=3)
        with self.assertRaises(PeerError):
            cluster.generate(b'x', 1)

    def test_tensor_validation(self):
        obj = encode(torch.zeros((3, self.spec.dim), dtype=torch.float32))
        self.assertEqual(tuple(decode(obj, self.spec.dim, 10).shape), (3, self.spec.dim))
        obj['shape'] = [4, self.spec.dim]
        with self.assertRaises(ValueError):
            decode(obj, self.spec.dim, 10)
        with self.assertRaises(ValueError):
            encode(torch.zeros((1, self.spec.dim), dtype=torch.float64))

    def test_endpoint_isolation(self):
        for invalid in ['example.com:1000', '192.168.1.1:2000', 'https://127.0.0.1:1234',
                        'http://127.0.0.1:8888/other', '127.0.0.1:0',
                        'http://user:password@127.0.0.1:1234']:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                peer_url(invalid)
        self.assertEqual(peer_url('127.0.0.1:3100'), 'http://127.0.0.1:3100')

    def test_private_secret_permissions(self):
        os.chmod(self.key_file, 0o644)
        with self.assertRaises(ValueError):
            load_secret(str(self.key_file))

    def test_coordinator_keeps_only_endpoints(self):
        model = Endpoints(self.spec)
        keys = list(model.state_dict())
        self.assertTrue(keys)
        self.assertFalse(any('layers' in x for x in keys))
        self.assertEqual(len(Segment(self.spec, 0, 2).layers), 2)


if __name__ == '__main__':
    unittest.main()
