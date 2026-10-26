"""Credential boundaries for the prepared Linux backend; no GPU or network."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from labcore import Lab


@unittest.skipIf(os.name == 'nt', 'POSIX file credential boundary')
class StrataCredentialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.path = self.home / '.local/state/haven-strata/api-key'
        self.path.parent.mkdir(parents=True)
        self.lab = object.__new__(Lab)
        self.lab.connect = Mock(return_value={'state': 'CONNECTED'})
        self.home_patch = patch('labcore.Path.home', return_value=self.home)
        self.platform_patch = patch('labcore.sys.platform', 'linux')
        self.home_patch.start()
        self.platform_patch.start()

    def tearDown(self):
        self.platform_patch.stop()
        self.home_patch.stop()
        self.tmp.cleanup()

    def test_private_file_connects_only_to_fixed_loopback(self):
        self.path.write_text('a' * 48 + '\n')
        self.path.chmod(0o600)
        self.lab.connect_haven_strata()
        self.lab.connect.assert_called_once_with('http://127.0.0.1:8880/v1', 'a' * 48, 'strata')

    def test_public_file_is_not_read_as_a_credential(self):
        self.path.write_text('a' * 48)
        self.path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'mode-0600'):
            self.lab.connect_haven_strata()
        self.lab.connect.assert_not_called()

    def test_symlink_is_not_followed(self):
        target = self.home / 'different-file'
        target.write_text('a' * 48)
        target.chmod(0o600)
        self.path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            self.lab.connect_haven_strata()
        self.lab.connect.assert_not_called()

    def test_invalid_credential_never_reaches_http(self):
        self.path.write_text('unsafe\ncredential')
        self.path.chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'invalid format'):
            self.lab.connect_haven_strata()
        self.lab.connect.assert_not_called()


if __name__ == '__main__':
    unittest.main()
