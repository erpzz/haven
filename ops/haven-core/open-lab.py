#!/usr/bin/env python3
"""Open the SSH-protected Linux Model Lab from the administration computer."""
import argparse
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

SOCKET = Path.home() / '.ssh/haven-lab.sock'
RECEIPT = Path.home() / '.local/state/haven-admin/haven-launch-url'
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8']


def run(*args, check=True):
    return subprocess.run(args, check=check, capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', help='Prepare access without opening a browser.')
    parser.add_argument('--close', action='store_true', help='Close only this helper\'s SSH tunnel.')
    args = parser.parse_args()
    check = run(*SSH, '-S', str(SOCKET), '-O', 'check', 'haven', check=False)
    if args.close:
        if check.returncode == 0:
            run(*SSH, '-S', str(SOCKET), '-O', 'exit', 'haven')
        print('Local Haven tunnel closed. The server and its data remain available.')
        return

    run(*SSH, 'haven', 'systemctl --user start haven-model-lab.service')
    if check.returncode != 0:
        if SOCKET.exists():
            metadata = SOCKET.lstat()
            if not stat.S_ISSOCK(metadata.st_mode) or metadata.st_uid != os.getuid():
                raise RuntimeError('The dedicated control-socket path is occupied; nothing was removed.')
            SOCKET.unlink()  # A failed control check proved this owned socket stale.
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', 8877)) == 0:
                raise RuntimeError('Local port 8877 is already occupied by another listener; nothing was stopped.')
        run(*SSH, '-fNT', '-M', '-S', str(SOCKET), '-o', 'ControlPersist=no',
            '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=30',
            '-o', 'ServerAliveCountMax=3', '-L', '127.0.0.1:8877:127.0.0.1:8877', 'haven')

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for attempt in range(15):
        try:
            url = run(*SSH, 'haven', 'cat ~/.local/state/haven-model-lab/launch-url').stdout.strip()
            parsed = urllib.parse.urlsplit(url)
            token = urllib.parse.parse_qs(parsed.fragment).get('token', [''])[0]
            if parsed.scheme != 'http' or parsed.netloc != '127.0.0.1:8877' or parsed.path != '/' or not token:
                raise RuntimeError('Unexpected private launch link; refusing to open it.')
            request = urllib.request.Request('http://127.0.0.1:8877/api/state', headers={'X-Lab-Token': token})
            with opener.open(request, timeout=4) as response:
                json.load(response)
            break
        except (OSError, urllib.error.URLError, subprocess.CalledProcessError):
            if attempt == 14:
                raise
            time.sleep(.2)

    RECEIPT.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.haven-link-', dir=RECEIPT.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(url + '\n')
        os.replace(temporary, RECEIPT)
    finally:
        Path(temporary).unlink(missing_ok=True)
    if args.prepare:
        print('Haven Core is ready through the private SSH tunnel. Launch link saved privately.')
    elif not webbrowser.open(url):
        raise RuntimeError('No browser opened; the private launch link is saved in ' + str(RECEIPT))
    else:
        print('Haven Core opened through the private SSH tunnel.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
