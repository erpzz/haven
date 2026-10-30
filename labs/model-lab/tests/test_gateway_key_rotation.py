"""Regression tests for Haven gateway key rotation (no live services required)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gateway import Gateway, GatewayError


class GatewayKeyRotationTests(unittest.TestCase):
    def test_replaced_key_is_rejected_without_server_restart(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            initial = Gateway.issue_key(directory, 'test-operator', 'owner')
            gateway = Gateway(object(), directory)
            old_auth = {'Authorization': 'Bearer ' + initial}
            self.assertEqual(gateway.authenticate(old_auth)['role'], 'owner')

            replacement = Gateway.issue_key(directory, 'test-operator', 'owner')
            with self.assertRaises(GatewayError) as ctx:
                gateway.authenticate(old_auth)
            self.assertEqual(ctx.exception.status, 401)
            self.assertEqual(gateway.authenticate(
                {'Authorization': 'Bearer ' + replacement})['role'], 'owner')

    def test_deleted_registry_revokes_existing_key(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            key = Gateway.issue_key(directory, 'test-operator', 'owner')
            gateway = Gateway(object(), directory)
            auth = {'Authorization': 'Bearer ' + key}
            self.assertEqual(gateway.authenticate(auth)['role'], 'owner')
            (directory / 'gateway-keys.json').unlink()
            with self.assertRaises(GatewayError) as ctx:
                gateway.authenticate(auth)
            self.assertEqual(ctx.exception.status, 401)


if __name__ == '__main__':
    unittest.main()
