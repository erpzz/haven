#!/usr/bin/env python3
"""Run the separately prepared Strata Linux backend on authenticated loopback.

No installation, model download, update, tuning or public listener is started.
The native foreground server stays inside the user service's process group.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import secrets
import stat
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'linux' or platform.machine() not in ('x86_64', 'amd64') or os.getuid() == 0:
        parser.error('Use the ordinary Linux x86-64 account that prepared this backend.')
    os.umask(0o077)
    state = Path.home() / '.local/state/haven-strata'
    data = Path.home() / '.local/share/haven-strata'
    profile = state / 'run-profile.json'
    cli = data / 'bin/strata'
    if not profile.is_file() or not cli.is_file():
        parser.error('The prepared private run profile or pinned Strata Terminal is missing. No download was attempted.')
    config = json.loads(profile.read_text())
    if config.get('mcp_servers') or config.get('before_load') or config.get('images') or config.get('vision'):
        parser.error('This text-only service requires a profile without MCP, startup hooks or image components.')
    if config.get('exe') != 'component:strata-engine':
        parser.error('Use the signed engine component, not a profile-selected executable.')
    if config.get('api_key'):
        parser.error('Move credentials out of the profile into the private key file.')
    key_path = state / 'api-key'
    if not args.plan and not key_path.exists():
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as handle:
            handle.write(secrets.token_urlsafe(48) + '\n')
    env = dict(os.environ)
    if key_path.exists():
        info = key_path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            parser.error('The API key must be an owned, private regular file.')
        env['STRATA_API_KEY'] = key_path.read_text().strip()
    elif not args.plan:
        parser.error('The private API key is unavailable.')
    env.update(STRATA_HOME=str(state), STRATA_COMPONENTS_DIR=str(data / 'components'),
               STRATA_UPDATE_FEED='https://github.com/Niko1221/Strata/releases/download/v0.2.6',
               STRATA_ENGINE_BACKEND='cuda', HF_HUB_OFFLINE='1',
               HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1')
    # A cold start reads a 33 GiB expert arena; over a USB 2 root link (about 40 MiB/s) that alone
    # takes about 14 minutes, so Strata's 900 s default fails after anything evicts the page cache.
    env.setdefault('STRATA_ENGINE_READY_S', '2400')
    command = [str(cli), 'serve', '--profile', str(profile), '--engine', 'strata',
               '--host', '127.0.0.1', '--port', '8880', '--max-queue', '1',
               '--queue-timeout', '30', '--offline', '--shutdown-timeout', '15']
    if args.plan:
        command += ['--plan']
    os.execve(cli, command, env)


if __name__ == '__main__':
    main()
