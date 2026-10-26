#!/usr/bin/env python3
"""Small local administrative snapshot; no inference, repairs or remote calls."""
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def command(argv):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=8)
        return {'returncode': result.returncode, 'output': result.stdout.strip()[:4000]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'returncode': -1, 'error': type(exc).__name__}


def main():
    os.umask(0o077)
    state = Path.home() / '.local/state/haven-admin'
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    disk = shutil.disk_usage('/')
    report = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'disk_free_bytes': disk.free, 'warnings': []}
    if disk.free < max(10 * 2**30, disk.total * .05):
        report['warnings'].append('LOW_ROOT_DISK_SPACE')
    report['ssh_socket'] = command(['systemctl', 'is-active', 'ssh.socket'])
    report['model_lab'] = command(['systemctl', '--user', 'is-active', 'haven-model-lab'])
    report['strata_optional'] = command(['systemctl', '--user', 'is-active', 'haven-strata'])
    for key in ('ssh_socket', 'model_lab'):
        if report[key]['returncode']:
            report['warnings'].append(key.upper() + '_NOT_ACTIVE')
    report['package_audit'] = command(['dpkg', '--audit'])
    if report['package_audit']['returncode'] or report['package_audit'].get('output'):
        report['warnings'].append('PACKAGE_AUDIT_REQUIRES_REVIEW')
    report['gpu'] = command(['nvidia-smi', '--query-gpu=memory.used,memory.total,temperature.gpu',
                             '--format=csv,noheader,nounits'])
    if report['gpu']['returncode']:
        report['warnings'].append('GPU_QUERY_FAILED')
    fd, temporary = tempfile.mkstemp(prefix='.health-', dir=state)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(report, handle, indent=2)
            handle.write('\n')
        os.replace(temporary, state / 'health.json')
    finally:
        Path(temporary).unlink(missing_ok=True)
    print('Haven health:', ', '.join(report['warnings']) if report['warnings'] else 'OK',
          '(private snapshot saved)')
    return 1 if report['warnings'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
