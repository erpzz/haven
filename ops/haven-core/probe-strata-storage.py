#!/usr/bin/env python3
"""One bounded O_DIRECT read of an existing model file; no raw disks or writes.

Run on Slink only after the peer explicitly releases the GPU/host. This does not
load Strata, evict caches, mount a filesystem, or change a device setting. The
receipt is private; publish only a deliberately sanitized numerical summary.
"""
import argparse
import datetime
import hashlib
import json
import mmap
import os
from pathlib import Path
import signal
import stat
import sys
import tempfile
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'labs/model-lab'))


def save(path, value):
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.io-receipt-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(value, f, sort_keys=True, indent=2, allow_nan=False)
            f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def lab_pid():
    link = Path.home() / '.local/state/haven-model-lab/launch-url'
    url = urllib.parse.urlsplit(link.read_text().strip())
    if url.scheme != 'http' or url.netloc != '127.0.0.1:8877' or url.path != '/':
        raise ValueError('Unexpected prepared Lab endpoint.')
    token = urllib.parse.parse_qs(url.fragment)['token'][0]
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request('http://127.0.0.1:8877/api/state', headers={'X-Lab-Token': token})
    with opener.open(request, timeout=8) as response:
        state = json.load(response)
    if any(j.get('state') == 'RUNNING' for j in state.get('jobs', [])):
        raise ValueError('A Lab job is running; the storage probe is deferred.')
    connection = state.get('connection') or {}
    if connection and connection.get('ownership') != 'OWNED':
        raise ValueError('An external backend is connected; the probe is deferred.')
    return state.get('engine', {}).get('pid') if connection else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-after-peer-release', action='store_true',
                        help='Operator has independently observed the peer release checkpoint.')
    args = parser.parse_args()
    if not args.run_after_peer_release or sys.platform != 'linux' or os.getuid() == 0:
        parser.error('Run as the ordinary Linux account after an explicit peer release.')
    os.umask(0o077)
    import gpu_lease
    source = Path.home() / '.local/share/haven-strata/data/models/IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf'
    base = (Path.home() / '.local/share/haven-strata/data/models').resolve()
    if not source.resolve().is_relative_to(base):
        raise ValueError('The prepared file resolved outside the model directory.')
    # Only this prepared ordinary file on the existing root filesystem. Never
    # accept a caller path or open a block device, even for a read-only probe.
    info = source.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_dev != Path('/').stat().st_dev:
        raise ValueError('Expected an existing regular model file on the root filesystem.')
    receipt = {'classification': 'HOST_READ_ONLY', 'captured_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'method': 'O_RDONLY|O_DIRECT|O_NOFOLLOW; aligned anonymous mmap + preadv',
               'cache_notes': 'O_DIRECT bypasses the Linux page cache for these reads. Device/bridge caches are not flushed or controlled.',
               'limits': {'sequential_bytes': 256 * 1024**2, 'sequential_block_bytes': 4 * 1024**2,
                          'spread_reads': 32, 'spread_block_bytes': 4096, 'alarm_seconds': 60},
               'file': {'path': str(source), 'size_bytes': info.st_size, 'mtime_ns': info.st_mtime_ns}, 'phases': []}
    out = Path.home() / '.local/state/haven-admin/overnight-io-probe.json'
    if out.exists():
        raise ValueError('The one-shot receipt already exists; no probe was repeated.')
    lease = gpu_lease.acquire(lab_pid())
    fd = None
    def deadline(_signum, _frame):
        raise TimeoutError('The fixed 60-second read budget expired.')
    old_handler = signal.signal(signal.SIGALRM, deadline)
    try:
        if not hasattr(os, 'O_DIRECT') or not hasattr(os, 'preadv'):
            raise ValueError('Direct aligned reads are unavailable; no cached fallback was used.')
        fd = os.open(source, os.O_RDONLY | os.O_DIRECT | os.O_NOFOLLOW)
        if os.fstat(fd).st_ino != info.st_ino:
            raise ValueError('The prepared file changed before open.')
        signal.alarm(60)
        block = 4 * 1024**2
        phases = [('sequential', block, [i * block for i in range(64)]),
                  ('spread_4k', 4096, [((info.st_size // 4096 - 1) * i // 31) * 4096 for i in range(32)])]
        with mmap.mmap(-1, block) as buffer:
            view = memoryview(buffer)
            try:
                for name, length, offsets in phases:
                    row = {'name': name, 'block_bytes': length, 'offsets': offsets, 'actual_bytes': 0, 'read_seconds': []}
                    receipt['phases'].append(row)
                    began, cpu = time.monotonic(), time.process_time()
                    for offset in offsets:
                        at = time.monotonic()
                        n = os.preadv(fd, [view[:length]], offset)
                        row['read_seconds'].append(round(time.monotonic() - at, 6))
                        row['actual_bytes'] += n
                        if n != length:
                            raise ValueError('A direct read was short; the probe is incomplete.')
                    row['elapsed_seconds'] = round(time.monotonic() - began, 6)
                    row['cpu_seconds'] = round(time.process_time() - cpu, 6)
                    row['effective_mib_s'] = round(row['actual_bytes'] / 1024**2 / row['elapsed_seconds'], 4)
            finally:
                view.release()
        receipt['state'] = 'COMPLETED'
    except Exception as error:
        receipt.update(state='BLOCKED_OR_INCOMPLETE', error=str(error))
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        if fd is not None:
            os.close(fd)
        lease.close()
        save(out, receipt)
    print(json.dumps({'state': receipt['state'], 'phases': [{k: v for k, v in p.items() if k != 'offsets' and k != 'read_seconds'} for p in receipt['phases']],
                      'error': receipt.get('error'), 'receipt_sha256': hashlib.sha256(out.read_bytes()).hexdigest()}))
    return 0 if receipt['state'] == 'COMPLETED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
