"""Cooperative GPU admission. Never stops a process to obtain a lease."""
import fcntl
import os
from pathlib import Path
import stat
import subprocess

PEER_UNITS = ('haven-toolsft-base.service', 'haven-toolsft-teacher.service',
              'haven-toolsft-arms.service',
              # Research campaigns that run their own llama-server on the GPU.
              'haven-e5.service', 'haven-paradigms-round2.service')
STRATA_UNIT = 'haven-strata.service'


def systemctl(*args, timeout=8):
    return subprocess.run(['systemctl', '--user', *args], capture_output=True,
                          text=True, timeout=timeout, check=False)


def unit_state(unit):
    if unit not in (*PEER_UNITS, STRATA_UNIT):
        raise ValueError('Unknown Haven unit.')
    result = systemctl('show', unit, '--property=ActiveState', '--value')
    value = result.stdout.strip()
    if value in ('active', 'activating', 'deactivating', 'reloading', 'inactive', 'failed'):
        return value
    if result.returncode and ('not found' in result.stderr.lower() or 'not loaded' in result.stderr.lower()):
        return 'inactive'
    raise ValueError('Cannot verify Haven unit state; GPU access is blocked.')


def peer_busy():
    return [unit for unit in PEER_UNITS if unit_state(unit) not in ('inactive', 'failed')]


def compute_pids():
    result = subprocess.run(['nvidia-smi', '--query-compute-apps=pid',
                             '--format=csv,noheader,nounits'], capture_output=True,
                            text=True, timeout=8, check=True)
    return {int(line.strip()) for line in result.stdout.splitlines() if line.strip()}


def strata_pids():
    result = systemctl('show', STRATA_UNIT, '--property=ControlGroup', '--value')
    group = result.stdout.strip()
    if result.returncode or not group.startswith('/') or '..' in group.split('/'):
        raise ValueError('Cannot verify the prepared Strata process group.')
    base = Path('/sys/fs/cgroup').resolve()
    path = (base / group.lstrip('/')).resolve()
    if not path.is_relative_to(base):
        raise ValueError('Invalid Strata process group.')
    return {int(v) for p in path.rglob('cgroup.procs') for v in p.read_text().split()}


def acquire(owned_pid=None, allow_strata=False):
    """Hold this file object across the entire admitted operation."""
    path = Path.home() / '.local/state/haven'
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise ValueError('GPU lease directory must be owned and not writable by others.')
    fd = os.open(path / 'gpu.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    handle = os.fdopen(fd, 'r+')
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('GPU lease must be an owned private regular file.')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another cooperative GPU operation owns the lease.') from None
        if peer_busy():
            raise ValueError('Claude\u2019s experiment is using or reserving the GPU. Wait for its release.')
        allowed = {owned_pid} if owned_pid else set()
        if allow_strata and unit_state(STRATA_UNIT) not in ('inactive', 'failed'):
            allowed |= strata_pids()
        if compute_pids() - allowed:
            raise ValueError('An unowned GPU process is running; nothing was stopped.')
        return handle
    except Exception:
        handle.close()
        raise
