from __future__ import annotations
from contextlib import contextmanager
import json
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from registry.core import MODEL, Registry, RegistrationError
from registry.http import Server
from hive.qwythos_plan import plan

ADMIN = 'test_owner_key_not_to_be_used_for_real_workers_at_all'
DECL = dict(consent=True, public=True, model=MODEL, backend='cuda', vram_gib=8, roles=['layer_inference'])

@contextmanager
def serving(registry):
    with Server(('127.0.0.1', 0), registry) as server:
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try: yield f'http://127.0.0.1:{server.server_port}'
        finally:
            server.shutdown(); t.join(timeout=2)

def http(url, path, *, data=None, token=None, host=None):
    raw = None if data is None else json.dumps(data).encode()
    req = Request(url+path, data=raw, headers={**({'Content-Type':'application/json'} if data is not None else {}), **({'Authorization':'Bearer '+token} if token else {}), **({'Host':host} if host else {})})
    try:
        with urlopen(req, timeout=2) as r: return r.status, json.loads(r.read())
    except HTTPError as e: return e.code, json.loads(e.read())

class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.clock = [1000.0]
        self.r = Registry(ADMIN, clock=lambda: self.clock[0])

    def enroll(self, **overrides):
        invite = self.r.invite(ADMIN)
        return self.r.join(invite, {**DECL, **overrides})

    def test_private_by_default_and_opt_in_public(self):
        node = self.enroll(public=False)
        self.r.heartbeat(node['node_id'], node['node_token'], available=True)
        self.assertEqual(self.r.public_nodes()['nodes'], [])
        node2 = self.enroll()
        self.r.heartbeat(node2['node_id'], node2['node_token'], available=True)
        self.assertEqual(len(self.r.public_nodes()['nodes']), 1)
        self.assertNotIn('node_token', str(self.r.public_nodes()))
        self.assertNotIn('127.0', str(self.r.public_nodes()))

    def test_expiry_and_no_stale_node(self):
        node = self.enroll()
        self.assertEqual(self.r.public_nodes()['nodes'], [])
        self.r.heartbeat(node['node_id'], node['node_token'], available=False)
        self.clock[0] += 91
        self.assertEqual(self.r.public_nodes()['nodes'], [])

    def test_one_time_invite_and_missing_consent(self):
        invite = self.r.invite(ADMIN)
        with self.assertRaises(RegistrationError):
            self.r.join(invite, {**DECL, 'consent':False})
        self.r.join(invite, DECL)
        with self.assertRaises(PermissionError): self.r.join(invite, DECL)

    def test_invite_expires_and_admin_denied(self):
        with self.assertRaises(PermissionError): self.r.invite('nope')
        invite = self.r.invite(ADMIN, ttl_seconds=30)
        self.clock[0] += 31
        with self.assertRaises(PermissionError): self.r.join(invite, DECL)

    def test_whitelist_denies_machine_information(self):
        with self.assertRaises(RegistrationError):
            self.enroll(ip='10.0.0.1')

    def test_credential_and_revoke(self):
        node = self.enroll()
        with self.assertRaises(PermissionError):
            self.r.heartbeat(node['node_id'], 'wrong', available=True)
        self.r.heartbeat(node['node_id'], node['node_token'], available=True)
        self.r.revoke(node['node_id'], node['node_token'])
        self.assertEqual(self.r.public_nodes()['nodes'], [])
        with self.assertRaises(PermissionError):
            self.r.heartbeat(node['node_id'], node['node_token'], available=True)

    def test_http_auth_and_listing(self):
        with serving(self.r) as u:
            self.assertEqual(http(u, '/v1/invites', data={'ttl_seconds':60})[0], 403)
            status, response = http(u, '/v1/invites', data={'ttl_seconds':60}, token=ADMIN)
            self.assertEqual(status, 200)
            status, node = http(u, '/v1/join', data={'invite':response['invite'], 'declaration':DECL})
            self.assertEqual(status, 200)
            self.assertEqual(http(u, f"/v1/nodes/{node['node_id']}/heartbeat", data={'available':True}, token=node['node_token'])[0], 200)
            status, public = http(u, '/v1/nodes')
            self.assertEqual(status, 200)
            self.assertEqual(len(public['nodes']), 1)
            self.assertNotIn(node['node_token'], json.dumps(public))
            self.assertEqual(http(u, '/v1/nodes', host='malicious.example')[0], 403)
            self.assertEqual(http(u, f"/v1/nodes/{node['node_id']}/revoke", data={}, token=node['node_token'])[0], 200)
            self.assertEqual(http(u, '/v1/nodes')[1]['nodes'], [])

    def test_no_public_bind(self):
        with self.assertRaises(ValueError): Server(('0.0.0.0',0), self.r)

    def test_qwythos_partition_coverage(self):
        for n in (1,2,3,4,7,32):
            shards = plan(n)['shards']
            self.assertEqual(sum(s['layers'] for s in shards),32)
            self.assertEqual(shards[0]['layer_range'][0],0)
            self.assertEqual(shards[-1]['layer_range'][1],32)
            self.assertTrue(all(a['layer_range'][1]==b['layer_range'][0] for a,b in zip(shards,shards[1:])))
        self.assertFalse(plan(4)['weights_loaded'])
        with self.assertRaises(ValueError): plan(0)

if __name__ == '__main__': unittest.main()
