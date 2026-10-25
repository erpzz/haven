"""A real stdlib HTTP process; no model, GPU, browser or package downloads."""
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(os.name == 'nt', 'Linux supervised launch and SIGTERM qualification')
class HeadlessLaunchTests(unittest.TestCase):
    def test_private_launch_file_preserves_authentication_without_logging_token(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            link = directory / 'state' / 'launch-url'
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0))
                port = listener.getsockname()[1]
            with (directory / 'server.log').open('w+') as log:
                process = subprocess.Popen([
                    sys.executable, str(ROOT / 'server.py'), '--port', str(port),
                    '--data-dir', str(directory / 'data'), '--launch-file', str(link),
                ], stdout=log, stderr=subprocess.STDOUT)
                try:
                    deadline = time.monotonic() + 8
                    while not link.exists() and process.poll() is None and time.monotonic() < deadline:
                        time.sleep(.05)
                    self.assertTrue(link.exists(), 'server did not publish its private launch file')
                    url = urlsplit(link.read_text().strip())
                    self.assertEqual(url.hostname, '127.0.0.1')
                    token = parse_qs(url.fragment)['token'][0]
                    if os.name != 'nt':
                        self.assertEqual(link.stat().st_mode & 0o077, 0)
                    for headers, expected in (({}, 401), ({'X-Lab-Token': token}, 200)):
                        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=4)
                        try:
                            connection.request('GET', '/api/state', headers=headers)
                            response = connection.getresponse()
                            data = json.loads(response.read())
                            self.assertEqual(response.status, expected)
                            if expected == 200:
                                self.assertEqual(data['jobs'], [])
                                self.assertFalse(data['connection'].get('base'))
                        finally:
                            connection.close()
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=3)
                self.assertEqual(process.returncode, 0)
                log.seek(0)
                output = log.read()
                self.assertNotIn(token, output)
                self.assertNotIn('#token=', output)


if __name__ == '__main__':
    unittest.main()
