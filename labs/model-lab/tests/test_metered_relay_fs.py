"""Security regressions for the owner-run metered relay (no provider calls).

Tests operate only in disposable local directories and Unix sockets.  They do
not enroll lanes, contact a cloud provider, or touch the running Model Lab.
"""
import importlib.util
import os
from pathlib import Path
import socket
import stat
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve()
SPEC = importlib.util.spec_from_file_location(
    'metered_relay_fs_test', HERE.parents[3] / 'ops/haven-core/metered-relay.py')
relay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(relay)


@unittest.skipUnless(hasattr(socket, 'AF_UNIX') and os.name == 'posix',
                     'Unix-domain socket security is POSIX-specific')
class RelayFilesystemTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'private'
        self.root.mkdir(mode=0o700)
        state_patch = patch.object(relay, 'STATE', self.root)
        state_patch.start()
        self.addCleanup(state_patch.stop)

    def test_private_write_is_atomic_and_owner_only(self):
        path = self.root / 'lanes' / 'test.json'
        relay.private_write(path, 'before')
        self.assertEqual(path.read_text(), 'before')
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        relay.private_write(path, 'after')
        self.assertEqual(path.read_text(), 'after')
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        self.assertFalse(list(path.parent.glob('*.tmp')))

    def test_private_write_rejects_symlink_without_truncating_target(self):
        victim = self.root / 'victim'
        victim.write_text('DO NOT TOUCH')
        path = self.root / 'lanes' / 'test.json'
        path.parent.mkdir(mode=0o700)
        path.symlink_to(victim)
        with self.assertRaises(relay.RelayError):
            relay.private_write(path, 'malicious')
        self.assertTrue(path.is_symlink())
        self.assertEqual(victim.read_text(), 'DO NOT TOUCH')

    def test_private_write_rejects_insecure_existing_file_and_parent(self):
        path = self.root / 'lanes' / 'test.json'
        path.parent.mkdir(mode=0o700)
        path.write_text('preserve')
        path.chmod(0o644)
        with self.assertRaises(relay.RelayError):
            relay.private_write(path, 'replace')
        self.assertEqual(path.read_text(), 'preserve')
        path.chmod(0o600)
        path.parent.chmod(0o755)
        with self.assertRaises(relay.RelayError):
            relay.private_write(path, 'replace')
        self.assertEqual(path.read_text(), 'preserve')

    def test_private_write_replace_failure_preserves_old_data(self):
        path = self.root / 'lanes' / 'test.json'
        relay.private_write(path, 'old')
        with patch.object(relay.os, 'replace', side_effect=OSError('simulated rename failure')):
            with self.assertRaises(OSError):
                relay.private_write(path, 'new')
        self.assertEqual(path.read_text(), 'old')
        self.assertEqual([p.name for p in path.parent.iterdir()], ['test.json'])

    def test_receipt_does_not_follow_symlink(self):
        victim = self.root / 'victim'
        victim.write_text('preserve')
        (self.root / 'requests.jsonl').symlink_to(victim)
        with self.assertRaises(OSError):
            relay.receipt({'outcome': 'test'})
        self.assertEqual(victim.read_text(), 'preserve')

    def test_active_socket_is_not_unlinked(self):
        target = self.root / 'sockets' / 'lane.sock'
        target.parent.mkdir(mode=0o700)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(target))
            target.chmod(0o600)
            listener.listen(1)
            before = target.lstat().st_ino
            with self.assertRaisesRegex(relay.RelayError, 'already listening'):
                relay.prepare_socket(target)
            self.assertEqual(target.lstat().st_ino, before)
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                probe.connect(str(target))

    def test_regular_file_symlink_and_insecure_socket_are_never_unlinked(self):
        target = self.root / 'sockets' / 'lane.sock'
        target.parent.mkdir(mode=0o700)
        target.write_text('not a socket')
        with self.assertRaises(relay.RelayError):
            relay.prepare_socket(target)
        self.assertEqual(target.read_text(), 'not a socket')
        target.unlink()
        victim = self.root / 'victim'
        victim.write_text('safe')
        target.symlink_to(victim)
        with self.assertRaises(relay.RelayError):
            relay.prepare_socket(target)
        self.assertEqual(victim.read_text(), 'safe')
        target.unlink()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(target))
            target.chmod(0o666)
            with self.assertRaises(relay.RelayError):
                relay.prepare_socket(target)
            self.assertTrue(target.exists())

    def test_stale_owned_socket_can_be_removed(self):
        target = self.root / 'sockets' / 'lane.sock'
        target.parent.mkdir(mode=0o700)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(target))
            target.chmod(0o600)
        self.assertTrue(target.exists())
        relay.prepare_socket(target)
        self.assertFalse(target.exists())

    def test_cleanup_refuses_socket_replaced_by_another_process(self):
        target = self.root / 'sockets' / 'lane.sock'
        target.parent.mkdir(mode=0o700)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(target))
            target.chmod(0o600)
            original = target.lstat()
        target.unlink()
        target.write_text('foreign replacement')
        with self.assertRaises(relay.RelayError):
            relay.remove_owned_socket(target, original)
        self.assertEqual(target.read_text(), 'foreign replacement')

    def test_server_has_bounded_request_slots(self):
        self.assertEqual(relay.MeteredUnixServer.max_active_requests, 4)
        # Exercise the actual nonblocking rejection path without starting a server.
        server = object.__new__(relay.MeteredUnixServer)
        server._slots = relay.threading.BoundedSemaphore(4)
        for _ in range(4):
            self.assertTrue(server._slots.acquire(blocking=False))
        rejected = []
        with patch.object(server, 'shutdown_request', side_effect=lambda req: rejected.append(req)):
            server.process_request('fifth-request', None)
        self.assertEqual(rejected, ['fifth-request'])
        for _ in range(4):
            server._slots.release()


if __name__ == '__main__':
    unittest.main()
