"""Launch a private registry (with a locally stored secret, never an argv token)."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import secrets
from .core import Registry
from .http import Server

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=['init', 'serve'])
    ap.add_argument('--secret-file', default='.hive-registry-admin')
    ap.add_argument('--port', type=int, default=9191)
    args = ap.parse_args()
    path = Path(args.secret_file)
    if args.command == 'init':
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(secrets.token_urlsafe(40) + '\n')
        print('Owner secret created at', path, '(not printed).')
    else:
        if os.name == 'posix' and path.stat().st_mode & 0o077:
            raise SystemExit('Secret file must be owner-only (mode 0600).')
        token = path.read_text().strip()
        with Server(('127.0.0.1', args.port), Registry(token)) as srv:
            print(f'HIVE private registry listening on 127.0.0.1:{srv.server_port}', flush=True)
            srv.serve_forever(poll_interval=0.1)

if __name__ == '__main__':
    main()
