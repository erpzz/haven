import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.parse import urlencode

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from labcore import Lab
from lan_auth import AuthStore
from server import Server, _is_private_address


class AddressBoundaryTests(unittest.TestCase):
    def test_only_loopback_and_rfc1918_ipv4(self):
        for value in ('127.0.0.1', '10.0.0.7', '172.16.4.2', '172.31.255.254', '192.168.1.50'):
            with self.subTest(value=value):
                self.assertTrue(_is_private_address(value))
        for value in ('8.8.8.8', '172.32.0.1', '169.254.2.1', '203.0.113.5', '::1'):
            with self.subTest(value=value):
                self.assertFalse(_is_private_address(value))


class AuthStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = AuthStore(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_owner_then_invite_member(self):
        owner = self.store.create_owner('eric', 'correct horse battery staple')
        self.assertEqual(owner['role'], 'admin')
        invite = self.store.create_invite(owner['id'])
        member = self.store.accept_invite(invite, 'guest.one', 'another correct horse battery')
        self.assertEqual(member['role'], 'member')
        with self.assertRaises(ValueError):
            self.store.accept_invite(invite, 'guest.two', 'yet another correct horse battery')

    def test_password_and_session(self):
        owner = self.store.create_owner('owner', 'correct horse battery staple')
        self.assertIsNone(self.store.authenticate('owner', 'wrong password value'))
        logged = self.store.authenticate('owner', 'correct horse battery staple')
        self.assertEqual(logged['id'], owner['id'])
        token, csrf = self.store.create_session(owner['id'])
        current = self.store.session(token)
        self.assertEqual(current['csrf'], csrf)
        self.store.logout(token)
        self.assertIsNone(self.store.session(token))

    def test_disable_revokes_sessions(self):
        owner = self.store.create_owner('owner', 'correct horse battery staple')
        invite = self.store.create_invite(owner['id'])
        member = self.store.accept_invite(invite, 'member', 'another correct horse battery')
        token, _ = self.store.create_session(member['id'])
        self.assertIsNotNone(self.store.session(token))
        self.store.set_disabled(owner['id'], member['id'], True)
        self.assertIsNone(self.store.session(token))


class LanHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lab = Lab(Path(self.tmp.name))
        self.server = Server(('127.0.0.1', 0), self.lab, lan_mode=True, control_token='control-secret')
        self.bootstrap = self.server.bootstrap_token
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.lab.shutdown()
        self.tmp.cleanup()

    def request(self, path, method='GET', body=None, headers=None):
        headers = dict(headers or {})
        headers.setdefault('Host', f'127.0.0.1:{self.server.server_port}')
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        if isinstance(body, dict):
            body = json.dumps(body)
            headers.setdefault('Content-Type', 'application/json')
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        out = (response.status, json.loads(raw) if raw else {}, dict(response.getheaders()))
        conn.close()
        return out

    def bootstrap_owner(self):
        status, payload, headers = self.request('/api/auth/bootstrap', 'POST', {
            'token': self.bootstrap,
            'username': 'owner',
            'password': 'correct horse battery staple',
        })
        self.assertEqual(status, 200, payload)
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        return cookie, payload['csrf'], payload['user']

    def test_static_public_api_private(self):
        self.assertEqual(self.request('/')[0], 200)
        self.assertEqual(self.request('/api/auth/status')[0], 200)
        self.assertEqual(self.request('/api/state')[0], 401)

    def test_owner_bootstrap_is_one_time(self):
        self.bootstrap_owner()
        status, payload, _ = self.request('/api/auth/bootstrap', 'POST', {
            'token': self.bootstrap,
            'username': 'second',
            'password': 'correct horse battery staple two',
        })
        self.assertIn(status, (400, 403))

    def test_csrf_required(self):
        cookie, _, _ = self.bootstrap_owner()
        self.assertEqual(self.request('/api/disconnect', 'POST', {}, {'Cookie': cookie})[0], 403)

    def test_invited_member_can_sign_in_but_not_administer(self):
        cookie, csrf, owner = self.bootstrap_owner()
        status, payload, _ = self.request('/api/auth/invites', 'POST', {'role': 'member'}, {
            'Cookie': cookie, 'X-CSRF-Token': csrf,
        })
        self.assertEqual(status, 200, payload)
        invite = payload['token']
        status, payload, member_headers = self.request('/api/auth/accept-invite', 'POST', {
            'token': invite,
            'username': 'phoneuser',
            'password': 'another correct horse battery',
        })
        self.assertEqual(status, 200, payload)
        member_cookie = member_headers['Set-Cookie'].split(';', 1)[0]
        member_csrf = payload['csrf']
        self.assertEqual(payload['user']['role'], 'member')
        self.assertEqual(self.request('/api/state', headers={'Cookie': member_cookie})[0], 200)
        self.assertEqual(self.request('/api/engine/stop', 'POST', {}, {
            'Cookie': member_cookie, 'X-CSRF-Token': member_csrf,
        })[0], 403)
        self.assertEqual(self.request('/api/auth/users', headers={'Cookie': member_cookie})[0], 403)

    def test_cross_origin_denied(self):
        self.assertEqual(self.request('/api/auth/status', headers={
            'Origin': 'https://evil.example',
        })[0], 403)

    def test_private_shutdown_requires_loopback_control_token(self):
        self.assertEqual(self.request('/api/private/shutdown', 'POST', {},
            {'X-Haven-Control': 'wrong'})[0], 403)


if __name__ == '__main__':
    unittest.main()
