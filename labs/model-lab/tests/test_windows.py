"""Benign native containment checks; no model or GPU work."""
import ctypes
from ctypes import wintypes as W
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from labcore import OwnedEngine, ROOT
from winjob import WindowsJob


@unittest.skipUnless(os.name == 'nt', 'Native Windows Job Object qualification')
class WindowsContainmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='haven-native-')
        self.directory = Path(self.tmp.name)
        self.engine = OwnedEngine(self.directory)
        self.handles = []
        self.k = ctypes.WinDLL('kernel32', use_last_error=True)
        self.k.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
        self.k.OpenProcess.restype = W.HANDLE
        self.k.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
        self.k.WaitForSingleObject.restype = W.DWORD
        self.k.CloseHandle.argtypes = [W.HANDLE]
        self.k.CloseHandle.restype = W.BOOL

    def tearDown(self):
        try:
            self.engine.stop()
        finally:
            for handle in self.handles:
                self.k.CloseHandle(handle)
            self.tmp.cleanup()

    def wait_marker(self, marker):
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(marker.exists(), 'Owned child did not publish marker within bound')

    def alive_handle(self, marker):
        handle = self.k.OpenProcess(0x100000, False, int(marker.read_text('utf-8')))
        self.assertTrue(handle, 'Cannot observe exact owned descendant')
        self.handles.append(handle)
        self.assertEqual(self.k.WaitForSingleObject(handle, 0), 258)
        return handle

    @staticmethod
    def descendant_code(wait=False):
        return (
            'import subprocess,sys;from pathlib import Path;'
            "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);"
            'Path(sys.argv[1]).write_text(str(p.pid),encoding="utf-8");'
            + ('import time;time.sleep(30)' if wait else '')
        )

    def test_exited_gate_retains_descendant_until_confirmed_stop(self):
        marker = self.directory / 'descendant.pid'
        self.engine.launch([sys.executable, '-c', self.descendant_code(), str(marker)],
                           self.directory, label='BENIGN DESCENDANT')
        self.wait_marker(marker)
        handle = self.alive_handle(marker)
        self.engine.proc.wait(timeout=5)
        self.assertGreaterEqual(self.engine.job.active_count(), 1)
        self.assertEqual(self.engine.stop()['state'], 'STOPPED')
        self.assertEqual(self.k.WaitForSingleObject(handle, 3000), 0)

    def test_assignment_failure_never_releases_payload(self):
        marker = self.directory / 'must-not-run'
        code = 'from pathlib import Path;import sys;Path(sys.argv[1]).write_text("bad")'
        with patch.object(WindowsJob, 'assign', side_effect=OSError('synthetic assignment failure')):
            with self.assertRaisesRegex(OSError, 'synthetic assignment failure'):
                self.engine.launch([sys.executable, '-c', code, str(marker)],
                                   self.directory, label='BENIGN ASSIGN FAIL')
        self.assertFalse(marker.exists())
        self.assertIsNone(self.engine.proc)
        self.assertIsNone(self.engine.job)

    def test_unconfirmed_stop_blocks_new_launch(self):
        self.engine.launch([sys.executable, '-c', 'import time;time.sleep(30)'],
                           self.directory, label='BENIGN STOP GUARD')
        with patch.object(self.engine.job, 'active_count', return_value=1):
            self.assertEqual(self.engine.stop()['state'], 'STOP_UNCONFIRMED')
        with self.assertRaises(ValueError):
            self.engine.launch([sys.executable, '-c', 'pass'], self.directory, label='BLOCKED')
        self.assertEqual(self.engine.stop()['state'], 'STOPPED')

    def test_supervisor_crash_kills_owned_descendant(self):
        marker = self.directory / 'crash-descendant.pid'
        code = (
            'import os,sys;from pathlib import Path;from labcore import OwnedEngine;'
            'e=OwnedEngine(Path(sys.argv[1]));'
            f'e.launch([sys.executable,"-c",{self.descendant_code(True)!r},sys.argv[2]],'
            'Path(sys.argv[1]),label="BENIGN CRASH");'
            'sys.stdin.readline();os._exit(0)'
        )
        supervisor = subprocess.Popen([sys.executable, '-c', code, str(self.directory), str(marker)],
                                      cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True)
        try:
            self.wait_marker(marker)
            handle = self.alive_handle(marker)
            supervisor.stdin.write('exit\n'); supervisor.stdin.flush()
            supervisor.wait(timeout=5)
            self.assertEqual(supervisor.returncode, 0)
            self.assertEqual(self.k.WaitForSingleObject(handle, 3000), 0)
        finally:
            if supervisor.poll() is None:
                supervisor.kill(); supervisor.wait(timeout=5)
            for stream in (supervisor.stdin, supervisor.stdout, supervisor.stderr):
                stream.close()


if __name__ == '__main__':
    unittest.main()
